"""Check sanitized receipt consistency. Does not rerun or authenticate OpenCode."""
import argparse
import fnmatch
import json
from pathlib import Path
import re
from contract import BINARY_SHA256, CHECK, EDIT, FILES, LAB, PIN, ROOT_RULES, SUMMARY, TASK, expected_files, policy, sha

CALLS = [('parent_task', 'task', TASK), ('child_read_helper', 'read', {'filePath': 'labels.mjs'}),
         ('child_read_tests', 'read', {'filePath': 'labels.test.mjs'}), ('child_edit', 'edit', EDIT),
         ('parent_check', 'bash', CHECK)]
RESULT_IDS = {'parent': [[], ['parent_task'], ['parent_task', 'parent_check']],
              'child': [[], ['child_read_helper'], ['child_read_helper', 'child_read_tests'],
                        ['child_read_helper', 'child_read_tests', 'child_edit']]}

def counts(passed):
    return {'exit': 0 if passed else 1, 'tests': 4, 'pass': 4 if passed else 2,
            'fail': 0 if passed else 2, 'cancelled': 0, 'skipped': 0, 'todo': 0}

def evaluate(rules, permission, pattern):
    matches = [r for r in rules if fnmatch.fnmatchcase(permission, r['permission'])
               and fnmatch.fnmatchcase(pattern, r['pattern'])]
    return matches[-1] if matches else None

def verify_report(r):
    errors = []
    def need(ok, description):
        if not ok:
            errors.append(description)
    try:
        need(r['schema_version'] == 1, 'schema version')
        need(r['release'] == '1.18.30' and r['commit'] == PIN, 'source pin')
        need(r['platform'] == 'Windows' and r['architecture'] == 'AMD64', 'runtime platform')
        need(r['binary_sha256'] == BINARY_SHA256, 'binary digest')
        need(re.fullmatch(r'[0-9a-f]{40}', r['lab_revision']) is not None and isinstance(r['lab_dirty'], bool), 'lab checkout identity')
        need(re.fullmatch(r'[0-9a-f]{64}', r['runner_sha256']) is not None, 'captured runner identity')
        need(r['shell_version'].startswith('7.') and r['node'].startswith('v24.'), 'reference runtime prerequisites')
        need(r['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER', 'evidence class')
        need(r['not_exercised'] == ['resume', 'cancellation', 'background', 'concurrent_writers', 'ask_responder', 'remembered_approval'],
             'scope qualifications')
        parent, child = r['sessions']['parent'], r['sessions']['child']
        p, c = parent['id'], child['id']
        need(p != c and p.startswith('ses_') and c.startswith('ses_'), 'distinct actual session identities')
        need(parent['parent_id'] is None and child['parent_id'] == p, 'stored parent link')
        need(parent['role'] == 'build' and child['role'] == 'general', 'selected roles')
        need(parent['permission'] == ROOT_RULES, 'parent session rules')
        need(child['permission'] == ROOT_RULES + [{'permission': 'task', 'pattern': '*', 'action': 'deny'}], 'child session rules')
        for session in [parent, child]:
            need(session['directory'] == session['assistant_cwd'] == session['assistant_root'] == 'workspace', 'shared runtime directory')
            need(session['path'] == '' and session['model'] == {'id': 'scripted', 'providerID': 'lab', 'variant': 'default'}, 'session path/model')
        config = r['configuration']
        need(config == {'model': 'lab/scripted', 'small_model': 'lab/scripted', 'enabled_providers': ['lab'],
                        'permission': {'*': 'deny'}, 'agent': policy(), 'snapshot': False, 'lsp': False,
                        'formatter': False, 'share': 'disabled', 'username': 'lab', 'subagent_depth': 1,
                        'pure': True, 'auto': False, 'experimental_environment_keys': []}, 'controlled configuration')
        need(r['worktree_root'] == 'workspace', 'independent worktree root')
        expected = {stage: {n: sha(data) for n, data in expected_files(changed).items()}
                    for stage, changed in [('before', False), ('before_report', True), ('after', True), ('current', True)]}
        need(r['files'] == expected, 'fixture bytes and unchanged tests at every checkpoint')
        need(r['changed_files'] == ['labels.mjs'], 'bounded edit')
        need(r['checks'] == {'external_before': counts(False), 'parent_after': counts(True), 'external_after': counts(True)}, 'fixed acceptance checks')
        need(r['cli_exit'] == 0 and r['runtime'] == ['ai-sdk'], 'recorded CLI/runtime result')
        need(r['pending_asks'] == 0, 'no responder was exercised')
        expected_decisions = [('task', 'general'), ('read', 'labels.mjs'), ('read', 'labels.test.mjs'),
                              ('edit', 'labels.mjs'), ('bash', CHECK['command'])]
        need(r['evaluations'] == [{'permission': name, 'pattern': target, 'rule_permission': name,
                                  'rule_pattern': target, 'action': 'allow'} for name, target in expected_decisions], 'evaluated operations')
        for name, target in expected_decisions:
            owner = 'parent' if name in ['task', 'bash'] else 'child'
            selected = evaluate(r['role_rules'][owner] + r['sessions'][owner]['permission'], name, target)
            need(selected == {'permission': name, 'pattern': target, 'action': 'allow'}, 'resolved authority: ' + name + '/' + target)
        need(evaluate(r['role_rules']['child'], 'edit', 'labels.test.mjs')['action'] == 'deny', 'test-file edit policy')
        records = r['tools']
        need([(x['call_id'], x['name'], x['arguments']) for x in records] == CALLS, 'actual ordered tool operations')
        for rec in records:
            owner = 'parent' if rec['call_id'].startswith('parent_') else 'child'
            need(rec['session_id'] == r['sessions'][owner]['id'] and rec['status'] == 'completed', 'tool ownership/state')
        need(r['read_evidence'] == {'helper_matches_initial': True, 'tests_match_fixed': True, 'observation_marker': True}, 'actual child reads')
        need(r['edit_evidence'] == {'file': 'labels.mjs', 'before': sha(expected_files()['labels.mjs']),
                                   'after': sha(expected_files(True)['labels.mjs']), 'output': 'Edit applied successfully.'}, 'edit evidence')
        result = r['return']
        output = f'<task id="{c}" state="completed">\n<task_result>\n{SUMMARY}\n</task_result>\n</task>'
        need(result == {'child_text': SUMMARY, 'task_output': output, 'parent_session_id': p, 'child_session_id': c,
                        'truncated': False, 'first_parent_tool_result': output,
                        'markers': {'parent': False, 'delegated': False, 'observation': False}}, 'selected return contract')
        requests = r['requests']
        need([q['index'] for q in requests] == list(range(1, len(requests) + 1)), 'complete request sequence')
        need(all(q['kind'] in ['parent', 'child', 'auxiliary'] for q in requests), 'request classification')
        for owner in ['parent', 'child']:
            qs = [q for q in requests if q['kind'] == owner]
            need([q['tool_result_ids'] for q in qs] == RESULT_IDS[owner], owner + ' complete request history')
            for i, q in enumerate(qs):
                need(q['session_id'] == r['sessions'][owner]['id'], owner + ' provider identity')
                need(q['parent_session_id'] == (p if owner == 'child' else None), owner + ' provider parent header')
                need(q['path'] == '/v1/chat/completions' and q['model'] == 'scripted' and q['stream'] is True, 'provider request shape')
                required = {'task', 'bash'} if owner == 'parent' else {'read', 'edit'}
                need(required <= set(q['advertised_tools']), 'available required tools')
                expected_markers = {'parent': owner == 'parent', 'delegated': owner == 'child' or i > 0,
                                    'observation': owner == 'child' and i > 0}
                need(q['markers'] == expected_markers, owner + ' full input marker boundaries')
        for q in [q for q in requests if q['kind'] == 'auxiliary']:
            need(q['advertised_tools'] == [] and q['tool_result_ids'] == [], 'auxiliary calls cannot hide tools')
        child_qs = [q for q in requests if q['kind'] == 'child']
        parent_qs = [q for q in requests if q['kind'] == 'parent']
        need(parent_qs[0]['index'] < child_qs[0]['index'] < child_qs[-1]['index'] < parent_qs[1]['index'], 'actual handoff order')
        seq = r['sequence']
        need([e['order'] for e in seq] == list(range(1, len(seq) + 1)), 'event order continuity')
        need([e['request'] for e in seq if e['kind'] == 'request_received'] == [q['index'] for q in requests], 'requests correspond to event order')
        barrier = [e for e in seq if e['kind'] != 'request_received']
        need([e['kind'] for e in barrier] == ['child_edit_result_received', 'independent_file_checkpoint', 'child_report_release'], 'complete barrier protocol')
        need(all(e['request'] == child_qs[-1]['index'] for e in barrier), 'barrier attached to child edit-result request')
        before_event = next(e['order'] for e in seq if e['kind'] == 'request_received' and e['request'] == child_qs[-1]['index'])
        after_event = next(e['order'] for e in seq if e['kind'] == 'request_received' and e['request'] == parent_qs[1]['index'])
        need(before_event < barrier[0]['order'] < barrier[1]['order'] < barrier[2]['order'] < after_event, 'file checkpoint before report release and parent continuation')
        need(r['root_stdout_tools'] == ['parent_task', 'parent_check'], 'root display is separate from child evidence')
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, StopIteration) as exc:
        errors.append('missing or malformed evidence: ' + str(exc))
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', nargs='?', type=Path, default=LAB / 'reference-results/windows-2026-10-07/receipt.json')
    args = parser.parse_args()
    try:
        errors = verify_report(json.loads(args.receipt.read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join('FAIL: ' + e for e in errors))
        raise SystemExit(1)
    print('PASS: delegation, input, barrier, selected return and fixed checks agree. No CLI rerun.')

if __name__ == '__main__':
    main()
