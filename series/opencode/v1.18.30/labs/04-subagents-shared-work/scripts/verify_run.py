"""Reconstruct a sanitized receipt from private requests, exports, logs and file bytes."""
import argparse
import json
from pathlib import Path
import re
import shlex
from contract import CHECK, EDIT, FILES, MARKERS, PROMPT, SUMMARY, TASK, expected_files, marker_presence, policy, sha
from verify_reference import CALLS, verify_report

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def need(ok, message):
    if not ok:
        raise ValueError(message)

def test_counts(text, exit_code):
    pairs = re.findall(r'^(?:#|ℹ) (tests|pass|fail|cancelled|skipped|todo) (\d+)\s*$', text, re.M)
    need(len(pairs) == 6 and len(dict(pairs)) == 6, 'missing or duplicate test counters')
    return {'exit': exit_code, **{key: int(value) for key, value in pairs}}

def snapshot(directory):
    files = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*')
             if p.is_file() and p.name != 'manifest.json' and '.git' not in p.relative_to(directory).parts}
    need(set(files) == set(FILES), 'missing or extra fixture file')
    declared = read(directory / 'manifest.json')
    need(declared == {n: {'sha256': sha(data), 'bytes': len(data)} for n, data in files.items()}, 'snapshot manifest disagrees with actual bytes')
    return files

def reconstruct(root):
    root = root.resolve()
    workspace = root / 'workspace'
    run = read(root / 'run.json')
    need(not (root / 'provider-errors.json').exists(), 'provider failed')
    exports = {k: read(root / ('export-' + k + '.stdout.txt')) for k in ['parent', 'child']}
    need(all(read(root / ('export-' + k + '.process.json'))['exit'] == 0 for k in exports), 'session export failed')
    ids = {k: v['info']['id'] for k, v in exports.items()}
    need(read(root / 'identities.json') == ids, 'provider and exported identities disagree')
    infos = {k: v['info'] for k, v in exports.items()}
    for owner, exported in exports.items():
        need(Path(exported['info']['directory']).resolve() == workspace, 'session directory differs from fixture')
        for message in exported['messages']:
            info = message['info']
            need(info['sessionID'] == ids[owner], 'message session differs')
            need(all(p['sessionID'] == ids[owner] and p['messageID'] == info['id'] for p in message['parts']), 'part ownership differs')
            if info['role'] == 'assistant':
                need(not info.get('error'), 'assistant error')
                need(info['agent'] == ('build' if owner == 'parent' else 'general'), 'assistant role changed')
                need(info['modelID'] == 'scripted' and info['providerID'] == 'lab', 'assistant model changed')
                need(Path(info['path']['cwd']).resolve() == Path(info['path']['root']).resolve() == workspace, 'assistant path metadata differs')
        user_parts = [p for m in exported['messages'] if m['info']['role'] == 'user' for p in m['parts']]
        # This Windows CLI records the quoted command-line argument literally.
        # The child receives the exact task prompt without those outer quotes.
        need(len(user_parts) == 1 and user_parts[0]['type'] == 'text'
             and user_parts[0]['text'] == (json.dumps(PROMPT) if owner == 'parent' else TASK['prompt']), 'supplied user input changed')
    worktree = (root / 'worktree.stdout.txt').read_text(encoding='utf-8').strip()
    need(read(root / 'worktree.process.json')['exit'] == 0 and Path(worktree).resolve() == workspace, 'actual Git worktree root differs')
    config = read(root / 'resolved-config.stdout.txt')
    selected_keys = ['model', 'small_model', 'enabled_providers', 'permission', 'snapshot', 'lsp', 'formatter', 'share', 'username', 'subagent_depth']
    selected = {k: config[k] for k in selected_keys}
    need(config['agent']['build']['permission'] == policy()['build']['permission'] and config['agent']['general']['permission'] == policy()['general']['permission'], 'configured role policies differ')
    need(config['provider']['lab']['npm'] == '@ai-sdk/openai-compatible', 'provider adapter changed')
    need(re.fullmatch(r'http://127\.0\.0\.1:\d+/v1', config['provider']['lab']['options']['baseURL']) is not None, 'provider is not loopback')
    need(config['provider']['lab']['options']['apiKey'] == 'lab' and not config.get('experimental'), 'provider key or experimental configuration differs')
    need(all(read(root / ('resolved-' + k + '.process.json'))['exit'] == 0 for k in ['config', 'parent', 'child']), 'configuration capture failed')
    selected['agent'] = policy()
    process = read(root / 'cli.process.json')
    command = process['command']
    need(command[1:] == ['--print-logs', '--log-level', 'INFO', 'run', '--pure', '--format', 'json', '--model', 'lab/scripted',
                         '--agent', 'build', '--title', 'Synthetic shared work', '--', PROMPT], 'CLI invocation differs from ordinary fresh task')
    selected.update({'pure': '--pure' in command, 'auto': '--auto' in command,
                     'experimental_environment_keys': [k for k in read(root / 'environment-keys.json') if k.startswith('OPENCODE_EXPERIMENTAL')]})
    role_rules = {}
    for owner in exports:
        agent = read(root / ('resolved-' + owner + '.stdout.txt'))
        need(agent['name'] == ('build' if owner == 'parent' else 'general'), 'resolved agent identity differs')
        # Only generated run paths can be sanitized. Reject an unexpected external path.
        rules = []
        for rule in agent['permission']:
            rule = dict(rule)
            if re.match(r'^[A-Za-z]:', rule['pattern']):
                need(rule['pattern'].startswith(str(root)), 'unexpected absolute permission path')
                rule['pattern'] = rule['pattern'].replace(str(root), '<run>').replace('\\', '/')
            rules.append(rule)
        role_rules[owner] = rules
    tools = {k: [p for m in v['messages'] for p in m['parts'] if p['type'] == 'tool'] for k, v in exports.items()}
    need([p['callID'] for p in tools['parent']] == ['parent_task', 'parent_check'] and
         [p['callID'] for p in tools['child']] == ['child_read_helper', 'child_read_tests', 'child_edit'], 'unexpected actual tool sequence')
    by_call = {p['callID']: p for group in tools.values() for p in group}
    records = []
    for call_id, tool_name, arguments in CALLS:
        part = by_call[call_id]
        need(part['tool'] == tool_name and part['state']['input'] == arguments, 'tool arguments differ: ' + call_id)
        records.append({'call_id': call_id, 'name': part['tool'], 'session_id': part['sessionID'],
                        'arguments': part['state']['input'], 'status': part['state']['status']})
    initial = expected_files()
    for call_id, name in [('child_read_helper', 'labels.mjs'), ('child_read_tests', 'labels.test.mjs')]:
        state = by_call[call_id]['state']
        need(state['metadata']['display']['text'] == initial[name].decode().strip(), 'read did not capture initial file')
        need(Path(state['metadata']['display']['path']).resolve() == workspace / name, 'read target differs')
        for line in initial[name].decode().splitlines():
            need(line in state['output'], 'read result omitted file content')
    edit = by_call['child_edit']['state']
    need(Path(edit['metadata']['filediff']['file']).resolve() == workspace / 'labels.mjs', 'edit target differs')
    need('-  return label;\n+  return label.trim();' in edit['metadata']['diff'], 'edit diff lacks intended change')
    task = by_call['parent_task']['state']
    need(task['metadata']['model'] == {'modelID': 'scripted', 'providerID': 'lab'}, 'task model metadata differs')
    child_texts = [p['text'] for p in exports['child']['messages'][-1]['parts'] if p['type'] == 'text']
    need(len(child_texts) == 1 and child_texts[0] == SUMMARY, 'child final text differs')
    requests = []
    raw_requests = {}
    proposals = []
    child_reports = []
    paths = sorted(root.glob('request-*.json'))
    need(len(paths) == len(list(root.glob('response-*.json'))), 'request/response completeness differs')
    for index, path in enumerate(paths, 1):
        need(path.name == f'request-{index:02}.json', 'request capture gap')
        raw = read(path)
        body, headers = raw['body'], raw['headers']
        response = read(root / f'response-{index:02}.json')
        available = sorted(t['function']['name'] for t in body.get('tools', []))
        kind = 'parent' if 'task' in available else 'child' if {'read', 'edit'} <= set(available) else 'auxiliary'
        need(response['kind'] == kind, 'request classification disagrees')
        if kind == 'child' and not response['message'].get('tool_calls'):
            need(response['message']['role'] == 'assistant' and response['finish_reason'] == 'stop',
                 'child report response did not finish normally')
            child_reports.append(response['message']['content'])
        replies = [m for m in body.get('messages', []) if m['role'] == 'tool']
        need(headers['x-session-id'] == headers['x-session-affinity'], 'provider session headers disagree')
        for reply in replies:
            need(reply['tool_call_id'] in by_call, 'unrelated tool result in request')
            need(reply['content'] == by_call[reply['tool_call_id']]['state']['output'], 'provider result differs from exported tool record')
        for call in response['message'].get('tool_calls', []):
            name = call['function']['name']
            need(name in available, 'provider called an unadvertised tool')
            proposals.append((call['id'], name, json.loads(call['function']['arguments'])))
        requests.append({'index': index, 'kind': kind, 'path': raw['path'], 'model': body['model'], 'stream': body.get('stream', False),
                         'session_id': headers['x-session-id'], 'parent_session_id': headers.get('x-parent-session-id'),
                         'advertised_tools': available, 'tool_result_ids': [m['tool_call_id'] for m in replies],
                         'markers': marker_presence(body)})
        raw_requests[index] = raw
    need(proposals == CALLS, 'controlled provider proposals differ from actual sequence')
    need(child_reports == child_texts, 'captured provider report differs from exported child text')
    parent_after = next(q for q in requests if q['kind'] == 'parent' and q['tool_result_ids'] == ['parent_task'])
    returned = next(m['content'] for m in raw_requests[parent_after['index']]['body']['messages'] if m['role'] == 'tool')
    before, checkpoint, after = [snapshot(root / name) for name in ['before', 'before-report', 'after']]
    current = {p.relative_to(workspace).as_posix(): p.read_bytes() for p in workspace.rglob('*')
               if p.is_file() and '.git' not in p.relative_to(workspace).parts}
    need(current == after, 'current file bytes differ from after snapshot')
    checks = {}
    for stage in ['before', 'after']:
        test_process = read(root / f'test-{stage}.process.json')
        need(test_process['command'][1:] == ['--test', 'labels.test.mjs'], 'independent acceptance command differs')
        checks['external_' + stage] = test_counts((root / f'test-{stage}.stdout.txt').read_text(encoding='utf-8'), test_process['exit'])
    parent_check = by_call['parent_check']['state']
    checks['parent_after'] = test_counts(parent_check['output'], parent_check['metadata']['exit'])
    events = [json.loads(line) for line in (root / 'cli.stdout.txt').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
    need(not any(e['type'] == 'error' for e in events), 'top-level CLI error')
    need({e['sessionID'] for e in events} == {ids['parent']}, 'root stdout session differs')
    event_tools = [e['part'] for e in events if e['type'] == 'tool_use']
    need([(p['callID'], p['state']) for p in event_tools] == [(p['callID'], p['state']) for p in tools['parent']], 'root stdout and exported parent tools disagree')
    log = (root / 'cli.stderr.txt').read_text(encoding='utf-8')
    evaluations = []
    for line in log.splitlines():
        if 'message=evaluated ' in line:
            tokens = shlex.split(line.split('message=evaluated ', 1)[1])
            fields = dict(x.split('=', 1) for x in tokens)
            evaluations.append({'permission': fields['permission'], 'pattern': fields['pattern'],
                                'rule_permission': fields['action.permission'], 'rule_pattern': fields['action.pattern'], 'action': fields['action.action']})
    need('message="shell tool using shell"' in log and 'message="all formatters are disabled"' in log, 'tool environment not confirmed')
    return {'schema_version': 1, **run, 'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER',
            'not_exercised': ['resume', 'cancellation', 'background', 'concurrent_writers', 'ask_responder', 'remembered_approval'],
            'sessions': {k: {'id': v['id'], 'parent_id': v.get('parentID'), 'role': v['agent'], 'permission': v['permission'],
                            'directory': 'workspace', 'path': v['path'], 'assistant_cwd': 'workspace', 'assistant_root': 'workspace', 'model': v['model']} for k, v in infos.items()},
            'configuration': selected, 'role_rules': role_rules, 'worktree_root': 'workspace',
            'files': {name: {n: sha(data) for n, data in files.items()} for name, files in [('before', before), ('before_report', checkpoint), ('after', after), ('current', current)]},
            'changed_files': sorted(n for n in before if before[n] != after[n]), 'checks': checks,
            'cli_exit': process['exit'], 'runtime': sorted(set(re.findall(r'message="llm runtime selected" llm.runtime=(\S+)', log))),
            'pending_asks': len(re.findall(r'message=asking ', log)), 'evaluations': evaluations, 'tools': records,
            'read_evidence': {'helper_matches_initial': True, 'tests_match_fixed': True,
                              'observation_marker': MARKERS['observation'] in by_call['child_read_helper']['state']['output']},
            'edit_evidence': {'file': 'labels.mjs', 'before': sha(before['labels.mjs']), 'after': sha(after['labels.mjs']), 'output': edit['output']},
            'return': {'child_text': child_texts[0], 'task_output': task['output'], 'parent_session_id': task['metadata']['parentSessionId'],
                       'child_session_id': task['metadata']['sessionId'], 'truncated': task['metadata']['truncated'],
                       'first_parent_tool_result': returned, 'markers': marker_presence(returned)},
            'requests': requests, 'sequence': read(root / 'sequence.json'), 'root_stdout_tools': [p['callID'] for p in event_tools]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    try:
        result = reconstruct(args.run_directory)
        errors = verify_report(result)
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join('FAIL: ' + e for e in errors))
        raise SystemExit(1)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS: raw requests, exported sessions/tools, barrier, file bytes and fixed checks agree.')
    print('Consistency is not independent authentication of the historical execution.')

if __name__ == '__main__':
    main()
