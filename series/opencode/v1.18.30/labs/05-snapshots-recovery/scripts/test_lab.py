"""Portable rejection controls for the sanitized published receipt."""
import copy
import json
import unittest
from verify_reference import REFERENCE, verify

class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads(REFERENCE.read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertTrue(verify(self.receipt))

    def test_contradictions_rejected(self):
        changes = [
            lambda d: d['cases'].pop(),
            lambda d: d['cases'][1]['stages'].pop('r2'),
            lambda d: d['cases'][1]['stages']['r3'].update(display_mode='expanded'),
            lambda d: d['cases'][1]['stages']['r3']['tests'].update(fail=0, **{'pass': 4}),
            lambda d: d['cases'][0].update(selected_paths=['labels.mjs', 'notes.txt']),
            lambda d: d['cases'][0].update(pre_undo_tree=d['cases'][0]['preimage_tree']),
            lambda d: d['cases'][1]['stages']['r4']['files']['labels.mjs'].update(sha256='0' * 64),
            lambda d: d['cases'][0]['provider_requests'].update(recovery=1),
            lambda d: d['runtime'].update(model_inference=True),
            lambda d: d['cases'][1]['continuation'].update(old_messages_after=5),
            lambda d: d['cases'][1]['continuation'].update(marker_after=True),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                value = copy.deepcopy(self.receipt)
                change(value)
                with self.assertRaises((ValueError, KeyError)):
                    verify(value)

if __name__ == '__main__':
    unittest.main()
