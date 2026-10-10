"""Reconstruct the boundary receipt from private runtime evidence, not runner conclusions."""
import argparse
import json
from pathlib import Path
import re
import shlex
from boundary_contract import (CASES, CHANGED, DENIED, DIRECT_PROMPT, FILES, MARKERS, PARENT_FINAL,
                               PROMPT, SUCCESS, TASK, calls, roles, session_rules, sha)
from contract import expected_files, marker_presence
from verify_run import need, read, snapshot, test_counts

def reconstruct_case(root, case):
    need(not (root / 'provider-errors.json').exists(), 'provider error')
    workspace = (root / 'workspace').resolve()
    ids = read(root / 'identities.json')
    child_expected = case not in ('parent-role-direct', 'dispatch')
    need(set(ids) == ({'parent', 'child'} if child_expected else {'parent'}), 'unexpected sessions')
    children = read(root / 'children.json')
    need([x['id'] for x in children] == ([ids['child']] if child_expected else []), 'child inventory mismatch')
    exports = {owner: read(root / ('export-' + owner + '.json')) for owner in ids}
    config = read(root / 'resolved-config.stdout.txt')
    for role in config['agent'].values():
        need(role.pop('options', {}) == {}, 'unexpected role options')
    selected = ('model', 'small_model', 'default_agent', 'enabled_providers', 'share', 'snapshot', 'lsp',
                'formatter', 'subagent_depth', 'permission', 'agent')
    submitted = read(root / 'opencode.json')
    need(all(config.get(k) == submitted.get(k) for k in selected), 'resolved configuration changed')
    need(config['agent'] == roles(case), 'configured role rules changed')
    need(config['permission'] == {'*': 'deny'}, 'default policy changed')
    need(config['model'] == config['small_model'] == 'lab/scripted' and config['enabled_providers'] == ['lab'], 'provider selection changed')
    need(config['snapshot'] is False and config['lsp'] is False and config['formatter'] is False and config['share'] == 'disabled', 'fixture services changed')
    provider = config['provider']['lab']
    need(provider['npm'] == '@ai-sdk/openai-compatible' and provider['options']['apiKey'] == 'lab', 'provider adapter/key changed')
    need(re.fullmatch(r'http://127\.0\.0\.1:\d+/v1', provider['options']['baseURL']) is not None, 'provider not loopback')
    need(not config.get('experimental'), 'unexpected experimental mode')
    need(not any(k.startswith('OPENCODE_EXPERIMENTAL') for k in read(root / 'environment-keys.json')), 'experimental environment')
    for stage in ('config', 'parent', 'child'):
        need(read(root / ('resolved-' + stage + '.process.json'))['exit'] == 0, 'debug capture failed')
    role_evidence = {}
    for owner, name in (('parent', 'coordinator'), ('child', 'worker')):
        role = read(root / ('resolved-' + owner + '.stdout.txt'))
        need(role['name'] == name, 'resolved role changed')
        role_evidence[owner] = [r for r in role['permission'] if r['permission'] in ('edit', 'task', '*')]
        for permission, patterns in roles(case)[name]['permission'].items():
            actual = [r for r in role['permission'] if r['permission'] == permission]
            for pattern, action in patterns.items():
                matching = [r for r in actual if r['pattern'] == pattern]
                need(matching and matching[-1]['action'] == action, 'resolved target policy differs')
    create = read(root / 'session-create-input.json')
    created = read(root / 'session-created.json')
    need(create['permission'] == session_rules(case) == created['permission'], 'session creation rules differ')
    need(created['id'] == ids['parent'], 'created identity differs')
    expected_child_rules = session_rules(case) + [
        {'permission': 'todowrite', 'pattern': '*', 'action': 'deny'},
        {'permission': 'task', 'pattern': '*', 'action': 'deny'}]
    by_call = {}
    messages = {}
    session_evidence = {}
    for owner, exported in exports.items():
        info = exported['info']
        need(info['version'] == '1.18.30', 'exported runtime version differs')
        need(info['id'] == ids[owner] and Path(info['directory']).resolve() == workspace, 'session identity/directory')
        need(info.get('parentID') == (None if owner == 'parent' else ids['parent']), 'parent relation')
        need(info['agent'] == ('coordinator' if owner == 'parent' else 'worker'), 'session role differs')
        need(info['permission'] == (session_rules(case) if owner == 'parent' else expected_child_rules), 'stored session permissions differ')
        need(info['model']['id'] == 'scripted' and info['model']['providerID'] == 'lab', 'session model differs')
        session_evidence[owner] = {'role': info['agent'], 'permission': info['permission'], 'directory': 'workspace',
                                 'parent': None if owner == 'parent' else 'parent'}
        for message in exported['messages']:
            mi = message['info']
            need(mi['sessionID'] == ids[owner], 'message owner')
            need(all(p['sessionID'] == ids[owner] and p['messageID'] == mi['id'] for p in message['parts']), 'part owner')
            if mi['role'] == 'assistant':
                need(not mi.get('error') and mi['agent'] == info['agent'], 'assistant error or role')
                need(mi['providerID'] == 'lab' and mi['modelID'] == 'scripted', 'assistant model')
            for part in message['parts']:
                if part['type'] == 'tool':
                    need(part['callID'] not in by_call, 'duplicate call')
                    by_call[part['callID']] = part
        user_parts = [p for m in exported['messages'] if m['info']['role'] == 'user' for p in m['parts']]
        prompt = TASK['prompt'] if owner == 'child' else DIRECT_PROMPT if case == 'parent-role-direct' else PROMPT
        need(len(user_parts) == 1 and user_parts[0]['type'] == 'text' and user_parts[0]['text'] in (prompt, json.dumps(prompt)), 'supplied prompt changed')
        texts = [p['text'] for p in exported['messages'][-1]['parts'] if p['type'] == 'text']
        want = (SUCCESS if case in CHANGED else DENIED) if owner == 'child' else PARENT_FINAL
        need(texts == [want], 'final text differs')
        messages[owner] = texts[0]
    expected_calls = calls(case)
    need(set(by_call) == {c[0] for c in expected_calls}, 'missing or extra tool call')
    operations = []
    for call_id, tool, arguments in expected_calls:
        part = by_call[call_id]
        state = part['state']
        need(part['tool'] == tool and state['input'] == arguments, 'actual tool arguments changed')
        denied = (tool == 'edit' and case not in CHANGED) or (tool == 'task' and case == 'dispatch')
        need(state['status'] == ('error' if denied else 'completed'), 'operation status differs')
        if denied:
            need('specified a rule' in state.get('error', '') and '"action":"deny"' in state['error'], 'error not a permission denial')
        if tool == 'read':
            need(state['metadata']['display']['text'] == expected_files()[arguments['filePath']].decode().strip(), 'read contents changed')
        if tool == 'edit' and not denied:
            need('-  return label;\n+  return label.trim();' in state['metadata']['diff'], 'edit diff mismatch')
        operations.append({'call_id': call_id, 'tool': tool, 'arguments': arguments, 'status': state['status'],
                           'permission_denied': denied, 'owner': 'child' if call_id.startswith('child_') else 'parent'})
    requests = []
    proposals, reports = [], {}
    paths = sorted(root.glob('request-*.json'))
    need(len(paths) == len(list(root.glob('response-*.json'))), 'request/response count')
    returned = None
    for index, path in enumerate(paths, 1):
        need(path.name == f'request-{index:02}.json', 'request gap')
        raw = read(path)
        response = read(root / f'response-{index:02}.json')
        body, headers = raw['body'], raw['headers']
        available = sorted(t['function']['name'] for t in body.get('tools', []))
        kind = next((owner for owner, sid in ids.items() if sid == headers.get('x-session-id')), 'auxiliary') if available else 'auxiliary'
        need(response['kind'] == kind and kind != 'auxiliary', 'unexpected provider request class')
        need(headers['x-session-id'] == headers['x-session-affinity'], 'affinity differs')
        if kind == 'child':
            need(headers.get('x-parent-session-id') == ids['parent'], 'provider parent identity')
        need(raw['path'] == '/v1/chat/completions' and body['model'] == 'scripted', 'provider route/model')
        replies = [m for m in body['messages'] if m['role'] == 'tool']
        for reply in replies:
            need(reply['tool_call_id'] in by_call, 'unexpected feedback call')
            state = by_call[reply['tool_call_id']]['state']
            need(reply['content'] == state.get('output', state.get('error')), 'provider feedback differs from export')
            if reply['tool_call_id'] == 'parent_task':
                returned = reply['content']
        for call in response['message'].get('tool_calls', []):
            function = call['function']
            need(function['name'] in available, 'called hidden tool')
            need(response['finish_reason'] == 'tool_calls', 'tool finish marker')
            proposals.append((call['id'], function['name'], json.loads(function['arguments'])))
        if not response['message'].get('tool_calls'):
            need(response['finish_reason'] == 'stop' and response['message']['role'] == 'assistant', 'report abnormal finish')
            reports.setdefault(kind, []).append(response['message']['content'])
        requests.append({'index': index, 'owner': kind, 'tools': available,
                         'feedback': [m['tool_call_id'] for m in replies], 'markers': marker_presence(body)})
    need(proposals == expected_calls, 'scripted proposals and runtime calls differ')
    need(reports == {owner: [text] for owner, text in messages.items()}, 'provider report and exported text differ')
    before, after = snapshot(root / 'before'), snapshot(root / 'after')
    need(before == expected_files() and after == expected_files(case in CHANGED), 'independent file bytes differ')
    current = {p.relative_to(workspace).as_posix(): p.read_bytes() for p in workspace.rglob('*')
               if p.is_file() and '.git' not in p.relative_to(workspace).parts}
    need(current == after, 'current tree differs from snapshot')
    if child_expected:
        need(snapshot(root / 'before-report') == after, 'pre-report checkpoint differs')
        sequence = read(root / 'sequence.json')
        need([e['order'] for e in sequence] == list(range(1, len(sequence) + 1)), 'event sequence differs')
        checkpoints = [e for e in sequence if e['kind'] == 'file_checkpoint_before_report']
        releases = [e for e in sequence if e['kind'] == 'response_release']
        need(len(checkpoints) == 1 and checkpoints[0]['request'] == 5, 'missing pre-report event')
        need([e['request'] for e in releases] == list(range(1, len(requests) + 1)), 'response event gap')
        need(checkpoints[0]['order'] < releases[4]['order'] < releases[5]['order'], 'report ordering differs')
        task = by_call['parent_task']['state']
        need(task['metadata']['sessionId'] == ids['child'] and task['metadata']['parentSessionId'] == ids['parent'], 'task linked session differs')
        need(returned == task['output'] and messages['child'] in returned, 'return path mismatch')
        need(MARKERS['observation'] not in returned and MARKERS['parent'] not in returned, 'unexpected report markers')
        child_inputs = [q for q in requests if q['owner'] == 'child']
        need(all(not q['markers']['parent'] and q['markers']['delegated'] for q in child_inputs), 'input marker boundary changed')
        need(not child_inputs[0]['markers']['observation'] and child_inputs[-1]['markers']['observation'], 'child read marker not observed')
    checks = {}
    for stage in ('before', 'after'):
        process = read(root / f'test-{stage}.process.json')
        need(process['command'][1:] == ['--test', 'labels.test.mjs'], 'fixed test invocation changed')
        counts = test_counts((root / f'test-{stage}.stdout.txt').read_text(encoding='utf-8'), process['exit'])
        success = stage == 'after' and case in CHANGED
        need(counts == {'exit': 0 if success else 1, 'tests': 4, 'pass': 4 if success else 2,
                        'fail': 0 if success else 2, 'cancelled': 0, 'skipped': 0, 'todo': 0}, 'fixed test results differ')
        checks[stage] = counts
    log = (root / 'server.stderr.txt').read_text(encoding='utf-8')
    evaluations = []
    for line in log.splitlines():
        if 'message=evaluated ' in line:
            fields = dict(t.split('=', 1) for t in shlex.split(line.split('message=evaluated ', 1)[1]))
            evaluations.append({'permission': fields['permission'], 'pattern': fields['pattern'],
                                'rule_permission': fields['action.permission'], 'rule_pattern': fields['action.pattern'], 'action': fields['action.action']})
    expected_evals = [{'permission': tool, 'pattern': 'worker' if tool == 'task' else arguments['filePath'],
                      'rule_permission': tool, 'rule_pattern': 'worker' if tool == 'task' else arguments['filePath'],
                      'action': 'deny' if op['permission_denied'] else 'allow'}
                     for (_, tool, arguments), op in zip(expected_calls, operations)]
    need(evaluations == expected_evals, 'runtime evaluations differ')
    need('message=asking ' not in log, 'unexpected pending permission ask')
    need(set(re.findall(r'llm.runtime=(\S+)', log)) == {'ai-sdk'}, 'runtime changed')
    cli = read(root / 'cli.process.json')
    cmd = cli['command']
    need(cli['exit'] == 0 and cmd[1:5] == ['run', '--pure', '--attach', cmd[4]], 'CLI entry path differs')
    need(re.fullmatch(r'http://127\.0\.0\.1:\d+', cmd[4]) is not None, 'CLI not attached to loopback')
    prompt = DIRECT_PROMPT if case == 'parent-role-direct' else PROMPT
    need(cmd[5:] == ['--session', ids['parent'], '--format', 'json', '--model', 'lab/scripted', '--agent', 'coordinator', '--', prompt], 'CLI arguments differ')
    events = [json.loads(line) for line in (root / 'cli.stdout.txt').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
    need(events and not any(e['type'] == 'error' for e in events), 'CLI stream error or missing events')
    public_return = returned
    if returned:
        for owner, sid in ids.items():
            public_return = public_return.replace(sid, '<' + owner + '>')
    return {'case': case, 'role_configuration': roles(case), 'resolved_relevant_role_rules': role_evidence,
            'sessions': session_evidence, 'child_count': len(children), 'operations': operations,
            'evaluations': evaluations, 'pending_asks': 0, 'requests': requests, 'selected_report': messages.get('child'),
            'task_return': public_return, 'files': {stage: {n: sha(b) for n, b in data.items()}
             for stage, data in (('before', before), ('after', after), ('current', current))},
            'changed_files': sorted(n for n in before if before[n] != after[n]), 'checks': checks,
            'cli_exit': cli['exit'], 'runtime': 'ai-sdk'}

def reconstruct(root):
    run = read(root / 'run.json')
    need(run['cases'] == list(CASES), 'complete comparison matrix required')
    return {**run, 'not_exercised': ['real model decisions', 'remembered approvals', 'resume', 'cancellation', 'background', 'concurrent writers'],
            'results': [reconstruct_case(root / case, case) for case in CASES]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    try:
        receipt = reconstruct(args.run_directory)
        from verify_boundary_reference import verify
        verify(receipt)
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        raise SystemExit('FAIL: ' + str(exc))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('PASS: six runtime cases, provider inputs/outputs, exported policy/tools, actual files and fixed checks agree.')
    print('Consistency does not independently authenticate a historical execution.')

if __name__ == '__main__':
    main()
