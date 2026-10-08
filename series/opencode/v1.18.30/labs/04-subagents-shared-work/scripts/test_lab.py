"""Portable rejection controls for the public receipt. No OpenCode execution."""
import copy
import json
import unittest
from contract import LAB
from verify_reference import verify_report

class ReceiptControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((LAB / 'reference-results/windows-2026-10-07/receipt.json').read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertEqual(verify_report(self.reference), [])

    def test_missing_and_contradictory_evidence(self):
        changes = [
            ('missing child request', lambda r: r['requests'].pop(1)),
            ('missing return', lambda r: r.pop('return')),
            ('missing checkpoint', lambda r: r['files'].pop('before_report')),
            ('no child identity', lambda r: r['sessions']['child'].pop('id')),
            ('same session', lambda r: r['sessions']['child'].update(id=r['sessions']['parent']['id'])),
            ('unrelated child', lambda r: r['sessions']['child'].update(parent_id='ses_unrelated')),
            ('private directory', lambda r: r['sessions']['child'].update(directory='private-copy')),
            ('different tool owner', lambda r: r['tools'][1].update(session_id=r['sessions']['parent']['id'])),
            ('failed child edit', lambda r: r['tools'][3].update(status='error')),
            ('different edit', lambda r: r['tools'][3]['arguments'].update(newString='return label;')),
            ('parent marker copied', lambda r: r['requests'][1]['markers'].update(parent=True)),
            ('handoff marker missing', lambda r: r['requests'][1]['markers'].update(delegated=False)),
            ('read marker missing', lambda r: r['requests'][2]['markers'].update(observation=False)),
            ('child history leaked to parent', lambda r: r['requests'][5]['markers'].update(observation=True)),
            ('wrong provider identity', lambda r: r['requests'][1].update(session_id='ses_unrelated')),
            ('wrong provider parent', lambda r: r['requests'][1].update(parent_session_id=None)),
            ('hidden child request', lambda r: r['requests'][2].update(kind='auxiliary')),
            ('missing edit feedback', lambda r: r['requests'][4]['tool_result_ids'].pop()),
            ('checkpoint before edit', lambda r: r['files']['before_report'].update(r['files']['before'])),
            ('test file changed', lambda r: r['files']['after'].update({'labels.test.mjs': '0' * 64})),
            ('missing file', lambda r: r['files']['after'].pop('labels.mjs')),
            ('release before checkpoint', lambda r: r['sequence'][6].update(order=9)),
            ('checkpoint tied to parent', lambda r: r['sequence'][6].update(request=6)),
            ('missing release event', lambda r: r['sequence'].pop(7)),
            ('wrong report', lambda r: r['return'].update(task_output='All tests passed')),
            ('unrecorded parent continuation', lambda r: r['return'].pop('first_parent_tool_result')),
            ('changed parent check', lambda r: r['checks']['parent_after'].update(tests=0)),
            ('failed independent check', lambda r: r['checks']['external_after'].update(exit=1)),
            ('invalid baseline control', lambda r: r['checks']['external_before'].update(fail=0)),
            ('missing policy evaluation', lambda r: r['evaluations'].pop(3)),
            ('policy says deny', lambda r: r['evaluations'][3].update(action='deny')),
            ('broader child authority', lambda r: r['role_rules']['child'].append({'permission': 'edit', 'pattern': '*', 'action': 'allow'})),
            ('missing child read proof', lambda r: r['read_evidence'].update(helper_matches_initial=False)),
            ('background enabled', lambda r: r['configuration']['experimental_environment_keys'].append('OPENCODE_EXPERIMENTAL')),
            ('wrong version', lambda r: r.update(release='1.18.35')),
            ('unsubstantiated runtime platform', lambda r: r.update(platform='Linux')),
        ]
        for label, change in changes:
            with self.subTest(label=label):
                value = copy.deepcopy(self.reference)
                change(value)
                self.assertTrue(verify_report(value), label)

if __name__ == '__main__':
    unittest.main()
