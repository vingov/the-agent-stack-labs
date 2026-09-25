"""Adversarial controls for the sanitized evidence checker; no OpenCode required."""
import copy
import json
from pathlib import Path
import unittest
from verify_reference import verify

REFERENCE = Path(__file__).resolve().parents[1] / 'reference-results/windows-2026-09-25/receipt.json'


class EvidenceControls(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(REFERENCE.read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertEqual(verify(self.report), [])

    def test_malformed_inputs(self):
        for invalid in [None, {}, [], {'cases': None}, {'schema_version': 1, 'release': None}]:
            with self.subTest(value=invalid):
                self.assertTrue(verify(invalid))

    def test_reject_missing_or_contradictory_evidence(self):
        mutations = {
            'no requests': lambda r: r['cases'][1].pop('requests'),
            'failed CLI': lambda r: r['cases'][1]['calls'][0].update(exit=1),
            'changed session': lambda r: r['cases'][1]['calls'][1].update(session_id='different'),
            'wrong release': lambda r: r.update(release='other'),
            'omitted case': lambda r: r['cases'].pop(),
            'hidden file leaked': lambda r: r['cases'][1]['requests'][0]['messages'][0]['markers'].append('UNREAD_SECRET'),
            'new file claimed stale': lambda r: r['cases'][1]['requests'][2].update(file_markers_at_request=['OLD_FILE']),
            'unchanged disk': lambda r: r['cases'][1]['requests'][2].update(file_sha256_at_request=r['cases'][1]['requests'][0]['file_sha256_at_request']),
            'old context survives': lambda r: r['cases'][1]['requests'][5]['messages'][0]['markers'].append('OLD_FILE'),
            'summary input tail leak': lambda r: r['cases'][1]['requests'][4]['messages'][0]['markers'].append('TAIL_FILE'),
            'mismatched feedback hash': lambda r: next(m for m in r['cases'][1]['requests'][1]['messages'] if m['role'] == 'tool').update(content_sha256='0'*64),
            'missing durable read': lambda r: next(m for m in r['cases'][1]['messages'] if any(p['type'] == 'tool' for p in m['parts'])).update(parts=[]),
            'invented summary success': lambda r: next(m for m in r['cases'][1]['messages'] if m['summary']).update(finish='error'),
            'wrong summary parent': lambda r: next(m for m in r['cases'][1]['messages'] if m['summary']).update(parent_id='wrong'),
            'wrong tail boundary': lambda r: next(p for m in r['cases'][1]['messages'] for p in m['parts'] if p['type'] == 'compaction').update(tail_start_id='wrong'),
            'missing reread': lambda r: r['cases'][1]['requests'].pop(),
            'forged pass': lambda r: (r.update(passed=True), r['cases'][0].update(messages=[])),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(self.report)
                mutation(changed)
                self.assertTrue(verify(changed), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
