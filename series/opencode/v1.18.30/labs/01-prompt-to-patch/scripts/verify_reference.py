"""Check a sanitized receipt offline; this checks recorded evidence, not a fresh CLI run."""
import argparse
import json
from pathlib import Path
import re


REFERENCE = Path(__file__).resolve().parents[1] / 'reference-results/windows-2026-09-13/receipt.json'


def verify_report(report):
    """Recompute the comparison without trusting a receipt's declared `passed` field."""
    errors = []

    def expect(actual, expected, label):
        # JSON serialization distinguishes false from 0, including inside tool records.
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            errors.append(label)

    if not isinstance(report, dict):
        return ['receipt must be an object']
    expect(report.get('release'), '1.18.30', 'release')
    expect(report.get('provider'), 'Local deterministic response fixture; no model inference', 'provider evidence class')
    for key in ('os', 'architecture'):
        if not isinstance(report.get(key), str) or not report[key].strip():
            errors.append(key)
    cases = report.get('cases')
    if not isinstance(cases, list) or len(cases) != 2 or not all(isinstance(c, dict) for c in cases):
        return errors + ['exactly two case objects required']
    for i, case in enumerate(cases):
        name = ('answer_only', 'tool_loop')[i]
        expected = {
            'case': name, 'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER',
            'cli_exit': 0, 'baseline_test_exit': 1, 'independent_test_exit': (1, 0)[i],
            'file_changed': bool(i), 'test_file_unchanged': True,
            'provider_requests': (1, 4)[i], 'session_count': 1, 'final_claim_present': True,
            'step_finish_reasons': ['stop'] if i == 0 else ['tool-calls'] * 3 + ['stop'],
            'tool_result_counts': [0] if i == 0 else [0, 1, 2, 3],
            'tool_calls_emitted': [] if i == 0 else [
                {'tool': tool, 'id': f'lab_call_{j}'} for j, tool in enumerate(('read', 'edit', 'bash'))],
            'tools_observed': [] if i == 0 else [
                {'tool': tool, 'call_id': f'lab_call_{j}', 'status': 'completed',
                 'exit': 0 if tool == 'bash' else None} for j, tool in enumerate(('read', 'edit', 'bash'))],
        }
        for key, value in expected.items():
            expect(case.get(key), value, f'{name}: {key}')
        for key in ('before_sha256', 'after_sha256', 'test_before_sha256', 'test_after_sha256'):
            if not isinstance(case.get(key), str) or not re.fullmatch('[0-9a-f]{64}', case[key]):
                errors.append(f'{name}: {key}')
        expect(case.get('before_sha256') != case.get('after_sha256'), bool(i), f'{name}: source hash comparison')
        expect(case.get('test_before_sha256'), case.get('test_after_sha256'), f'{name}: test hash comparison')
    for key in ('before_sha256', 'test_before_sha256'):
        expect(cases[0].get(key), cases[1].get(key), f'identical baseline: {key}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', nargs='?', type=Path, default=REFERENCE)
    args = parser.parse_args()
    try:
        report = json.loads(args.receipt.read_text(encoding='utf-8'))
        errors = verify_report(report)
        if not isinstance(report, dict) or report.get('passed') is not True:
            errors.append('declared passed flag is missing or false')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'FAIL: cannot read receipt: {exc}\n')
    if errors:
        parser.exit(1, 'FAIL: ' + '; '.join(errors) + '\n')
    print('PASS: recorded comparison is consistent. No OpenCode or model was run.')


if __name__ == '__main__':
    main()
