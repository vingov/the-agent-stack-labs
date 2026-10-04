"""Reconstruct sanitized evidence from private captures, independently of the runner's claims."""
import argparse
import json
from pathlib import Path
import re
from verify_reference import EDIT, EXPECTED, fixture_bytes, sha, verify_report


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def manifest(directory):
    files = {p.name: p.read_bytes() for p in directory.iterdir() if p.name != 'manifest.json'}
    declared = read_json(directory / 'manifest.json')
    actual = {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in files.items()}
    need(actual == declared, str(directory.name) + ': manifest disagrees with captured bytes')
    return {name: entry['sha256'] for name, entry in actual.items()}


def test_result(case, stage):
    text = (case / f'test-{stage}.stdout.txt').read_text(encoding='utf-8')
    pairs = re.findall(r'^(?:#|ℹ) (tests|pass|fail|cancelled|skipped|todo) (\d+)\s*$', text, re.M)
    need(len(pairs) == 6, 'missing or duplicate test counters')
    result = {key: int(value) for key, value in pairs}
    process = read_json(case / f'test-{stage}.process.json')
    need(process['command'][1:] == ['--test', 'slug.test.mjs'], 'acceptance command changed')
    result['exit'] = process['exit']
    return result


def error_kind(state):
    if state['status'] == 'completed':
        need(state.get('output') == 'Edit applied successfully.', 'unexpected edit output')
        return 'none'
    error = state.get('error', '')
    if error == 'The user rejected permission to use this specific tool call.':
        return 'rejected'
    if error.startswith('The user has specified a rule which prevents you from using this specific tool call.'):
        return 'denied'
    return 'other'


def reconstruct_case(case):
    meta = read_json(case / 'case.json')
    action, auto, _, _ = EXPECTED[case.name]
    need(meta == {'name': case.name, 'action': action, 'auto': auto}, 'case metadata mismatch')
    config = read_json(case / 'resolved-config.stdout.txt')
    need(config['permission'] == {'*': 'deny', 'read': {'*': 'deny', 'slug.mjs': 'allow'},
                                  'edit': {'*': 'deny', 'slug.mjs': action}}, 'effective configuration changed')
    need(config['model'] == config['small_model'] == 'lab/scripted' and config['enabled_providers'] == ['lab'],
         'provider control changed')
    need(config['snapshot'] is False and config['share'] == 'disabled', 'state controls changed')
    need(config['username'] == 'lab', 'non-synthetic username')
    agent = read_json(case / 'resolved-agent.stdout.txt')
    relevant = [r for r in agent['permission'] if r['permission'] in ['*', 'edit']]
    need(all(r['pattern'] in ['*', 'slug.mjs'] for r in relevant), 'unexpected edit policy pattern')
    need(agent['name'] == 'build', 'wrong agent')
    process = read_json(case / 'cli.process.json')
    command = process['command']
    need(('--auto' in command) is auto, 'CLI responder mode differs from case')
    need(command[1:6] == ['--print-logs', '--log-level', 'INFO', 'run', '--pure'], 'CLI entry path changed')
    need(not any(x in command for x in ['--attach', '--session', '--continue', '--yolo', '--dangerously-skip-permissions']),
         'unexpected invocation flags')
    log = (case / 'cli.stderr.txt').read_text(encoding='utf-8')
    evaluations = re.findall(r'message=evaluated permission=edit pattern=(\S+) '
                             r'action.permission=(\S+) action.pattern=(\S+) action.action=(\S+)', log)
    need(len(evaluations) == 1, 'missing or duplicate edit evaluation')
    pattern, permission, rule_pattern, evaluated = evaluations[0]
    asking = re.findall(r'message=asking .*?permission=edit patterns=', log)
    runtime = sorted(set(re.findall(r'message="llm runtime selected" llm.runtime=(\S+)', log)))
    need('message="shell tool using shell"' in log, 'missing selected-shell initialization evidence')
    need('message="all formatters are disabled"' in log, 'formatter configuration not confirmed in logs')
    events = [json.loads(line) for line in (case / 'cli.stdout.txt').read_text(encoding='utf-8').splitlines()
              if line.startswith('{')]
    need(not any(e['type'] == 'error' for e in events), 'top-level CLI error')
    event_tools = [e['part'] for e in events if e['type'] == 'tool_use']
    exported = read_json(case / 'export.stdout.txt')
    need(read_json(case / 'export.process.json')['exit'] == 0, 'export failed')
    parts = [p for m in exported['messages'] for p in m['parts'] if p['type'] == 'tool']
    need([p['callID'] for p in parts] == ['lab_read', 'lab_edit'], 'unexpected durable tool sequence')
    need([(p['tool'], p['callID'], p['state']) for p in parts] ==
         [(p['tool'], p['callID'], p['state']) for p in event_tools], 'stdout and export tool records disagree')
    need({e['sessionID'] for e in events} == {exported['info']['id']}, 'session identity disagrees')
    read, edit = parts
    need(read['state']['input'] == {'filePath': 'slug.mjs'} and edit['state']['input'] == EDIT,
         'runtime inputs differ from controlled proposal')
    need(fixture_bytes('slug.mjs').decode().strip() in read['state']['output'], 'initial read lacks fixture content')
    requests, proposed = [], []
    request_paths = sorted(case.glob('request-*.json'))
    need(len(request_paths) == len(list(case.glob('response-*.json'))), 'request/response count mismatch')
    for index, path in enumerate(request_paths, 1):
        need(path.name == f'request-{index:02}.json', 'capture sequence gap')
        raw = read_json(path)
        body = raw['body']
        response = read_json(case / f'response-{index:02}.json')
        tools = [t['function']['name'] for t in body.get('tools', [])]
        requests.append({'path': raw['path'], 'stream': body.get('stream', False),
                         'advertised_tools': tools,
                         'tool_result_ids': [m['tool_call_id'] for m in body.get('messages', []) if m['role'] == 'tool']})
        for call in response['message'].get('tool_calls', []):
            name = call['function']['name']
            need(name in tools, 'scripted tool was not advertised')
            arguments = json.loads(call['function']['arguments'])
            need(arguments == (EDIT if name == 'edit' else {'filePath': 'slug.mjs'}), 'provider arguments changed')
            proposed.append({'id': call['id'], 'name': name})
    before, after = manifest(case / 'before'), manifest(case / 'after')
    for name, digest in after.items():
        need(sha((case / 'workspace' / name).read_bytes()) == digest, 'current workspace differs from after capture')
    return {'name': case.name, 'configured_action': action, 'auto': auto,
            'session_id': exported['info']['id'], 'agent_target_rule': relevant[-1]['action'],
            'session_permission': exported['info']['permission'], 'edit_arguments': edit['state']['input'],
            'evaluated_edit': {'permission': 'edit', 'pattern': pattern, 'rule_permission': permission,
                               'rule_pattern': rule_pattern, 'action': evaluated},
            'asking_count': len(asking),
            'auto_rejection_warning': 'permission requested: edit (slug.mjs); auto-rejecting' in log,
            'runtime': runtime, 'formatter': config['formatter'], 'lsp': config['lsp'],
            'read_status': read['state']['status'], 'edit_status': edit['state']['status'],
            'edit_error_kind': error_kind(edit['state']), 'cli_exit': process['exit'],
            'tool_calls': [p['tool'] for p in parts], 'provider_tool_calls': proposed,
            'requests': requests, 'before': before, 'after': after,
            'changed_files': sorted(n for n in before if before[n] != after.get(n)),
            'test_before': test_result(case, 'before'), 'test_after': test_result(case, 'after')}


def reconstruct(root):
    info = read_json(root / 'run.json')
    return {'schema_version': 1, **info, 'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER',
            'permission_reply_capture': 'not recorded; responder behavior attributed to source',
            'cases': [reconstruct_case(root / name) for name in EXPECTED]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--receipt', type=Path, help='Write a sanitized receipt only after verification passes')
    args = parser.parse_args()
    try:
        report = reconstruct(args.run_directory)
        errors = verify_report(report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join('FAIL: ' + e for e in errors))
        raise SystemExit(1)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PASS: raw provider, policy logs, exported tools, fixed tests and file bytes agree in four cases.')
    print('This checks recorded consistency, not independent authentication of execution.')


if __name__ == '__main__':
    main()
