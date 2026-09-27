"""Negative controls for receipt checks, plus an independent execution of the fixture tests."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from run_lab import BUGGY, TEST
from verify_reference import REFERENCE, verify_report


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(REFERENCE.read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertEqual(verify_report(self.report), [])

    def test_corrupted_evidence_rejected_even_with_green_flag(self):
        mutations = {
            'missing case': lambda r: r['cases'].pop(),
            'wrong evidence class': lambda r: r['cases'][1].update(evidence_class='LIVE_MODEL'),
            'CLI failure': lambda r: r['cases'][1].update(cli_exit=1),
            'boolean exit': lambda r: r['cases'][1].update(cli_exit=False),
            'baseline already green': lambda r: r['cases'][1].update(baseline_test_exit=0),
            'control unexpectedly passes': lambda r: r['cases'][0].update(independent_test_exit=0),
            'patch fails independent tests': lambda r: r['cases'][1].update(independent_test_exit=1),
            'unchanged source with change flag': lambda r: r['cases'][1].update(after_sha256=r['cases'][1]['before_sha256']),
            'tests modified': lambda r: r['cases'][1].update(test_after_sha256='f' * 64),
            'different baseline': lambda r: r['cases'][1].update(before_sha256='e' * 64),
            'missing tool result': lambda r: r['cases'][1].update(tool_result_counts=[0, 1, 2, 2]),
            'tool ID mismatch': lambda r: r['cases'][1]['tools_observed'][1].update(call_id='wrong'),
            'tool still running': lambda r: r['cases'][1]['tools_observed'][2].update(status='running'),
            'bash nonzero': lambda r: r['cases'][1]['tools_observed'][2].update(exit=1),
            'extra provider call': lambda r: r['cases'][1].update(provider_requests=5),
            'extra session': lambda r: r['cases'][1].update(session_count=2),
            'missing final text': lambda r: r['cases'][0].update(final_claim_present=False),
            'missing test hash': lambda r: r['cases'][0].pop('test_before_sha256'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                damaged = copy.deepcopy(self.report)
                mutate(damaged)
                self.assertTrue(damaged['passed'])
                self.assertTrue(verify_report(damaged))

    def test_malformed_shapes(self):
        for value in (None, [], {}, {'cases': [None, {}]}):
            with self.subTest(value=value):
                self.assertTrue(verify_report(value))

    def test_cli_rejects_invalid_json_and_false_pass_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / 'receipt.json'
            for contents in ('{', json.dumps({**self.report, 'passed': False})):
                receipt.write_text(contents, encoding='utf-8')
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_reference.py')), str(receipt)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)

    def test_fixture_fails_before_patch_and_passes_after(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node.js is required for the fixture acceptance test')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, tests = root / 'slug.mjs', root / 'slug.test.mjs'
            source.write_text(BUGGY, encoding='utf-8')
            tests.write_text(TEST, encoding='utf-8')
            original_tests = tests.read_bytes()
            before = subprocess.run([node, '--test', str(tests)], capture_output=True, text=True)
            self.assertEqual(before.returncode, 1, before.stdout + before.stderr)
            source.write_text(BUGGY.replace("replaceAll(' ', '-')", "replace(/\\s+/g, '-')"), encoding='utf-8')
            after = subprocess.run([node, '--test', str(tests)], capture_output=True, text=True)
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
            self.assertEqual(tests.read_bytes(), original_tests)


if __name__ == '__main__':
    unittest.main(verbosity=2)
