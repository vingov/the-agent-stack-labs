"""Portable rejection controls for published receipts. Does not execute OpenCode."""
import copy
import json
import unittest
from verify_reference import LAB, verify_report


class ReceiptControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((LAB / 'reference-results/windows-2026-10-04/receipt.json').read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertEqual(verify_report(self.reference), [])

    def test_reject_missing_or_contradictory_evidence(self):
        controls = {
            'missing case': lambda r: r['cases'].pop(),
            'duplicate case': lambda r: r['cases'].__setitem__(3, copy.deepcopy(r['cases'][0])),
            'reused session': lambda r: r['cases'][1].__setitem__('session_id', r['cases'][0]['session_id']),
            'wrong source': lambda r: r.__setitem__('commit', '0' * 40),
            'wrong binary': lambda r: r.__setitem__('binary_sha256', '0' * 64),
            'invented human evidence': lambda r: r.__setitem__('evidence_class', 'HUMAN_APPROVED'),
            'invented reply capture': lambda r: r.__setitem__('permission_reply_capture', 'once observed'),
            'missing condition': lambda r: r['cases'][0].pop('auto'),
            'changed auto flag': lambda r: r['cases'][1].__setitem__('auto', True),
            'different proposal': lambda r: r['cases'][1]['edit_arguments'].__setitem__('newString', 'different'),
            'hidden edit': lambda r: r['cases'][3]['requests'][1].__setitem__('advertised_tools', ['read']),
            'missing evaluation': lambda r: r['cases'][0].pop('evaluated_edit'),
            'wrong evaluation': lambda r: r['cases'][3]['evaluated_edit'].__setitem__('action', 'allow'),
            'wrong agent policy': lambda r: r['cases'][3].__setitem__('agent_target_rule', 'allow'),
            'session override': lambda r: r['cases'][3]['session_permission'].append(
                {'permission': 'edit', 'pattern': '*', 'action': 'allow'}),
            'missing ask': lambda r: r['cases'][2].__setitem__('asking_count', 0),
            'missing CLI warning': lambda r: r['cases'][1].__setitem__('auto_rejection_warning', False),
            'wrong runtime': lambda r: r['cases'][0].__setitem__('runtime', ['native']),
            'invalid read': lambda r: r['cases'][0].__setitem__('read_status', 'error'),
            'unknown refusal': lambda r: r['cases'][3].__setitem__('edit_error_kind', 'other'),
            'status drift': lambda r: r['cases'][3].__setitem__('edit_status', 'completed'),
            'extra mutation tool': lambda r: r['cases'][0]['tool_calls'].append('bash'),
            'missing proposal': lambda r: r['cases'][0]['provider_tool_calls'].pop(),
            'missing feedback': lambda r: r['cases'][3]['requests'][2].__setitem__('tool_result_ids', []),
            'nonstream transport': lambda r: r['cases'][0]['requests'][0].__setitem__('stream', False),
            'unexpected continuation': lambda r: r['cases'][1]['requests'].append(r['cases'][1]['requests'][0]),
            'missing manifest': lambda r: r['cases'][0].pop('before'),
            'bad initial bytes': lambda r: r['cases'][0]['before'].__setitem__('slug.mjs', '0' * 64),
            'changed denied target': lambda r: r['cases'][3]['after'].__setitem__('slug.mjs', r['cases'][0]['after']['slug.mjs']),
            'changed test file': lambda r: r['cases'][0]['after'].__setitem__('slug.test.mjs', '0' * 64),
            'extra fixture effect': lambda r: r['cases'][0]['after'].__setitem__('extra.txt', '0' * 64),
            'false changed-file claim': lambda r: r['cases'][0].__setitem__('changed_files', []),
            'missing test counts': lambda r: r['cases'][0].__setitem__('test_after', {'exit': 0}),
            'tests not run': lambda r: r['cases'][0]['test_after'].__setitem__('skipped', 3),
            'false acceptance': lambda r: r['cases'][1].__setitem__('test_after', r['cases'][0]['test_after']),
            'formatter enabled': lambda r: r['cases'][0].__setitem__('formatter', True),
        }
        for label, change in controls.items():
            with self.subTest(control=label):
                altered = copy.deepcopy(self.reference)
                change(altered)
                self.assertTrue(verify_report(altered), label)
        print(f'Checked {len(controls)} missing/contradictory receipt controls.')


if __name__ == '__main__':
    unittest.main()
