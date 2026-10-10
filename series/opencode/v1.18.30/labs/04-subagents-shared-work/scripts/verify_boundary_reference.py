"""Portable consistency check of the sanitized historical comparison. Does not run OpenCode."""
import argparse
import json
from pathlib import Path
from boundary_contract import (BINARY_SHA256, CASES, CHANGED, DENIED, PIN, SUCCESS, calls, roles, session_rules, sha)
from contract import expected_files

def need(ok, message):
    if not ok:
        raise ValueError(message)

def verify(receipt):
    need(receipt['schema_version'] == 1 and receipt['release'] == 'v1.18.30' and receipt['commit'] == PIN, 'version mismatch')
    need(receipt['binary_sha256'] == BINARY_SHA256, 'binary mismatch')
    need(receipt['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER' and receipt['model_inference'] is False, 'evidence class')
    need(receipt['platform'] == 'Windows' and receipt['entrypoint'] == 'serve + API session.create + run --attach --session', 'execution scope')
    need(receipt['cases'] == list(CASES) and [r['case'] for r in receipt['results']] == list(CASES), 'matrix incomplete')
    for row in receipt['results']:
        case = row['case']
        child = case not in ('parent-role-direct', 'dispatch')
        changed = case in CHANGED
        need(row['role_configuration'] == roles(case), case + ': role configuration')
        need(set(row['sessions']) == ({'parent', 'child'} if child else {'parent'}), case + ': sessions')
        for owner, session in row['sessions'].items():
            expected = session_rules(case) + ([] if owner == 'parent' else [
                {'permission': 'todowrite', 'pattern': '*', 'action': 'deny'},
                {'permission': 'task', 'pattern': '*', 'action': 'deny'}])
            need(session == {'role': 'coordinator' if owner == 'parent' else 'worker', 'permission': expected,
                             'directory': 'workspace', 'parent': None if owner == 'parent' else 'parent'}, case + ': session policy')
        for owner, name in (('parent', 'coordinator'), ('child', 'worker')):
            rules = row['resolved_relevant_role_rules'][owner]
            need(rules and all(r['permission'] in ('*', 'edit', 'task') for r in rules), case + ': role evidence missing')
            for permission in ('edit', 'task'):
                configured = roles(case)[name]['permission'].get(permission, {})
                for pattern, action in configured.items():
                    matches = [r for r in rules if r['permission'] == permission and r['pattern'] == pattern]
                    need(matches and matches[-1]['action'] == action, case + ': effective target rule')
        need(row['child_count'] == int(child), case + ': child creation')
        planned = calls(case)
        need(len(row['operations']) == len(planned), case + ': operation count')
        expected_evals = []
        for op, (call_id, tool, arguments) in zip(row['operations'], planned):
            denied = (tool == 'edit' and not changed) or case == 'dispatch'
            need(op == {'call_id': call_id, 'tool': tool, 'arguments': arguments, 'status': 'error' if denied else 'completed',
                        'permission_denied': denied, 'owner': 'child' if call_id.startswith('child_') else 'parent'}, case + ': operation differs')
            pattern = 'worker' if tool == 'task' else arguments['filePath']
            expected_evals.append({'permission': tool, 'pattern': pattern, 'rule_permission': tool,
                                   'rule_pattern': pattern, 'action': 'deny' if denied else 'allow'})
        need(row['evaluations'] == expected_evals, case + ': evaluated rules differ')
        need(row['pending_asks'] == 0 and row['runtime'] == 'ai-sdk' and row['cli_exit'] == 0, case + ': execution state')
        for stage in ('before', 'after', 'current'):
            expected = {n: sha(b) for n, b in expected_files(changed and stage != 'before').items()}
            need(row['files'][stage] == expected, case + ': file evidence')
        need(row['changed_files'] == (['labels.mjs'] if changed else []), case + ': changed paths')
        for stage in ('before', 'after'):
            success = changed and stage == 'after'
            need(row['checks'][stage] == {'exit': 0 if success else 1, 'tests': 4, 'pass': 4 if success else 2,
                 'fail': 0 if success else 2, 'cancelled': 0, 'skipped': 0, 'todo': 0}, case + ': test counters')
        requests = row['requests']
        need([q['index'] for q in requests] == list(range(1, len(requests) + 1)), case + ': request sequence')
        expected_count = 6 if child else 4 if case == 'parent-role-direct' else 2
        need(len(requests) == expected_count, case + ': request count')
        seen = []
        for q in requests:
            need(q['owner'] in row['sessions'], case + ': request owner')
            owner_calls = [c for c in planned if c[0].startswith(('parent' if q['owner'] == 'parent' else 'child') + '_')]
            need(q['feedback'] == [c[0] for c in owner_calls[:len(q['feedback'])]], case + ': feedback order')
            if len(q['feedback']) < len(owner_calls):
                proposal = owner_calls[len(q['feedback'])]
                need(proposal[1] in q['tools'], case + ': expected tool not exposed')
                seen.append(proposal)
        need(seen == planned, case + ': proposals mismatch')
        parent_first = requests[0]
        need(parent_first['owner'] == 'parent' and parent_first['markers']['parent'], case + ': missing parent marker')
        if child:
            child_inputs = [q for q in requests if q['owner'] == 'child']
            need(len(child_inputs) == 4 and all(not q['markers']['parent'] and q['markers']['delegated'] for q in child_inputs), case + ': delegation context')
            need(not child_inputs[0]['markers']['observation'] and child_inputs[-1]['markers']['observation'], case + ': observation context')
            need(not requests[-1]['markers']['observation'], case + ': full child trace leaked into parent continuation')
            report = SUCCESS if changed else DENIED
            need(row['selected_report'] == report, case + ': selected report')
            returned = row['task_return']
            need(report in returned and '<child>' in returned and 'task_result' in returned, case + ': return wrapper')
        else:
            need(row['selected_report'] is None, case + ': invented report')
            if case == 'parent-role-direct':
                need(row['task_return'] is None, case + ': invented task return')
            else:
                need('specified a rule' in row['task_return'], case + ': dispatch denial missing')
    return receipt

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    try:
        verify(json.loads(args.receipt.read_text(encoding='utf-8')))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise SystemExit('FAIL: ' + str(exc))
    print('PASS: sanitized six-case receipt is internally consistent. No OpenCode execution performed.')

if __name__ == '__main__':
    main()
