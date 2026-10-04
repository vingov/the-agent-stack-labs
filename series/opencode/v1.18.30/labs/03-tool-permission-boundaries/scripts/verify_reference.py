"""Check consistency of sanitized evidence. This does not rerun or authenticate OpenCode."""
import argparse
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PIN = '3104c1428ec91f809e5ab86631300de41eb6952e'
EXPECTED = {'allow': ('allow', False, True, 'none'),
            'ask': ('ask', False, False, 'rejected'),
            'ask_auto': ('ask', True, True, 'none'),
            'deny_auto': ('deny', True, False, 'denied')}
EDIT = {'filePath': 'slug.mjs', 'oldString': ".replaceAll(' ', '-')",
        'newString': r".replace(/\s+/g, '-')"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_bytes(name):
    return (LAB / 'fixtures' / name).read_text(encoding='utf-8').encode()


def verify_report(report):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    try:
        require(report['schema_version'] == 1, 'schema version')
        require(report['release'] == '1.18.30' and report['commit'] == PIN, 'implementation pin')
        require(report['platform'] == 'Windows', 'runtime platform')
        require(report['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER', 'evidence class')
        require(report['permission_reply_capture'] == 'not recorded; responder behavior attributed to source',
                'reply evidence qualification')
        require(report['binary_sha256'] == 'c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea',
                'official Windows x64 binary digest')
        require(report['architecture'] == 'AMD64', 'runtime architecture')
        cases = report['cases']
        require(len(cases) == 4 and {c['name'] for c in cases} == set(EXPECTED), 'complete unique case matrix')
        require(len({c['session_id'] for c in cases}) == 4, 'fresh session identities')
        initial = fixture_bytes('slug.mjs')
        changed = initial.decode().replace(EDIT['oldString'], EDIT['newString']).encode()
        test_hash = sha(fixture_bytes('slug.test.mjs'))
        for case in cases:
            name = case['name']
            action, auto, writes, error_kind = EXPECTED[name]
            prefix = name + ': '
            require(case['configured_action'] == action and case['auto'] is auto, prefix + 'case conditions')
            require(case['edit_arguments'] == EDIT, prefix + 'controlled edit arguments')
            require(case['evaluated_edit'] == {'permission': 'edit', 'pattern': 'slug.mjs',
                                               'rule_permission': 'edit', 'rule_pattern': 'slug.mjs',
                                               'action': action}, prefix + 'actual permission evaluation')
            require(case['agent_target_rule'] == action, prefix + 'effective agent policy')
            require(case['session_permission'] == [{'permission': p, 'pattern': '*', 'action': 'deny'}
                                                    for p in ['question', 'plan_enter', 'plan_exit']],
                    prefix + 'session policy')
            require(case['asking_count'] == int(action == 'ask'), prefix + 'pending request evidence')
            require(case['auto_rejection_warning'] is (name == 'ask'), prefix + 'CLI rejection evidence')
            require(case['runtime'] == ['ai-sdk'], prefix + 'runtime selection')
            require(case['read_status'] == 'completed', prefix + 'valid read control')
            require(case['edit_status'] == ('completed' if writes else 'error'), prefix + 'edit outcome')
            require(case['edit_error_kind'] == error_kind, prefix + 'refusal type')
            require(case['cli_exit'] == 0, prefix + 'recorded CLI exit')
            require(case['formatter'] is False and case['lsp'] is False, prefix + 'auxiliary controls')
            require(case['tool_calls'] == ['read', 'edit'], prefix + 'only controlled tool calls')
            require(case['provider_tool_calls'] == [{'id': 'lab_read', 'name': 'read'},
                                                   {'id': 'lab_edit', 'name': 'edit'}], prefix + 'provider proposals')
            requests = case['requests']
            require(len(requests) == (2 if name == 'ask' else 3), prefix + 'recorded continuation')
            for index, request in enumerate(requests):
                require(request['path'] == '/v1/chat/completions' and request['stream'] is True,
                        prefix + 'real provider request shape')
                require({'read', 'edit'} <= set(request['advertised_tools']), prefix + 'tools stay advertised')
                require(request['tool_result_ids'] == ['lab_read', 'lab_edit'][:index], prefix + 'result feedback')
            before, after = case['before'], case['after']
            require(set(before) == set(after) == {'slug.mjs', 'slug.test.mjs'}, prefix + 'bounded fixture manifest')
            require(before['slug.mjs'] == sha(initial), prefix + 'reset initial bytes')
            require(after['slug.mjs'] == sha(changed if writes else initial), prefix + 'actual resulting bytes')
            require(before['slug.test.mjs'] == after['slug.test.mjs'] == test_hash, prefix + 'fixed acceptance tests')
            require(case['changed_files'] == (['slug.mjs'] if writes else []), prefix + 'changed-file correspondence')
            require(case['test_before'] == {'exit': 1, 'tests': 3, 'pass': 1, 'fail': 2,
                                            'cancelled': 0, 'skipped': 0, 'todo': 0}, prefix + 'working baseline tests')
            require(case['test_after'] == {'exit': 0 if writes else 1, 'tests': 3,
                                           'pass': 3 if writes else 1, 'fail': 0 if writes else 2,
                                           'cancelled': 0, 'skipped': 0, 'todo': 0}, prefix + 'independent acceptance')
        # Matched comparisons use identical proposals and fixtures, not just pass flags.
        require(len({json.dumps(c['edit_arguments'], sort_keys=True) for c in cases}) == 1,
                'proposal equality across cases')
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        errors.append('missing or malformed evidence: ' + str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', nargs='?', type=Path,
                        default=LAB / 'reference-results/windows-2026-10-04/receipt.json')
    args = parser.parse_args()
    try:
        errors = verify_report(json.loads(args.receipt.read_text(encoding='utf-8')))
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join('FAIL: ' + e for e in errors))
        raise SystemExit(1)
    print('PASS: four-case receipt is consistent with fixture, policy, runtime and effect evidence. No CLI rerun.')


if __name__ == '__main__':
    main()
