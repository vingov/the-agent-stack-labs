"""Check the published sanitized summary, without running OpenCode or authenticating history."""
import argparse
import json
from pathlib import Path
from contract import BINARY_SHA256, CASES, FILES, LAB, PIN, STAGES, expected, sha
from verify_run import need, object_id

REFERENCE = LAB / 'reference-results' / 'windows-2026-10-16' / 'receipt.json'

def tree_id(files):
    data = b''.join(b'100644 ' + name.encode() + b'\0' + bytes.fromhex(object_id('blob', content))
                    for name, content in sorted(files.items()))
    return object_id('tree', data)

def check_stage(result, case, stage):
    data = expected(case, stage)
    need(result['files'] == {n: {'sha256': sha(d), 'bytes': len(d)} for n, d in data.items()}, 'reference file evidence differs')
    passed = stage in ('r1', 'r2', 'r4')
    need(result['tests'] == {'tests': 4, 'pass': 4 if passed else 2, 'fail': 0 if passed else 2,
                            'cancelled': 0, 'skipped': 0, 'todo': 0}, 'reference acceptance differs')
    need(result['display_mode'] == ('expanded' if case == 'same-file' and stage in ('r2', 'r4') else 'compact'), 'reference later value differs')

def verify(receipt):
    need(receipt['schema_version'] == 1, 'schema differs')
    runtime = receipt['runtime']
    need(runtime['release'] == 'v1.18.30' and runtime['commit'] == PIN and runtime['binary_sha256'] == BINARY_SHA256, 'version differs')
    need(runtime['platform'] == 'Windows' and runtime['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER'
         and runtime['model_inference'] is False, 'evidence class differs')
    need(runtime['cases'] == list(CASES) and [c['case'] for c in receipt['cases']] == list(CASES), 'case inventory differs')
    need(runtime['continuation'] is True, 'published reference must include the planned continuation')
    for result in receipt['cases']:
        case = result['case']
        need(('continuation' in result) == (case == 'same-file'), 'published continuation missing or attached to wrong case')
        need(set(result['stages']) == set(STAGES), 'missing primary boundary')
        for stage in STAGES:
            check_stage(result['stages'][stage], case, stage)
        need(result['selected_paths'] == ['labels.mjs'], 'selected domain differs')
        need(result['preimage_tree'] == tree_id(expected(case, 'r0')), 'preimage identity differs')
        need(result['pre_undo_tree'] == tree_id(expected(case, 'r2')), 'pre-undo identity differs')
        counts = result['provider_requests']
        need(counts['main'] == 4 and isinstance(counts['auxiliary'], int) and counts['auxiliary'] >= 0
             and counts['recovery'] == 0, 'request evidence differs')
        need(result['original_messages'] == 5 and result['original_parts'] == 14
             and result['stored_records_retained_through_unrevert'] is True, 'record continuity differs')
        if 'continuation' in result:
            need(case == 'same-file', 'continuation belongs to treatment only')
            continuation = result['continuation']
            need(set(continuation['stages']) == {'c0', 'c1'}, 'continuation boundary missing')
            for stage in ('c0', 'c1'):
                check_stage(continuation['stages'][stage], case, stage)
            want = {'old_messages_before': 5, 'old_messages_after': 0, 'new_user_messages': 1,
                    'marker_before': True, 'marker_after': False, 'provider_requests': 0, 'no_reply': True}
            need({k: v for k, v in continuation.items() if k != 'stages'} == want, 'continuation evidence differs')
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path, nargs='?', default=REFERENCE)
    args = parser.parse_args()
    verify(json.loads(args.receipt.read_text(encoding='utf-8')))
    print('Published receipt is internally consistent. This does not rerun OpenCode.')

if __name__ == '__main__':
    main()
