"""Portable receipt rejection controls and bounded fixture/harness checks."""
import copy
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from capture import Recorder
from check_receipt import check
from contract import FILES, LAB, fixture, intended_files
from evidence import EvidenceError, acceptance


class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((LAB / 'reference' / 'receipt.json').read_text(encoding='utf-8'))

    def test_reference(self):
        self.assertEqual(check(self.reference), 3)

    def test_semantic_rejection_controls(self):
        mutations = {
            'missing case': lambda r: r['cases'].pop(0),
            'swapped session': lambda r: r['cases'][1].update(session=r['cases'][0]['session']),
            'different pin': lambda r: r.update(source_commit='0' * 40),
            'missing file': lambda r: r['cases'][1]['states']['barrier']['files'].pop('catalogue.json'),
            'false green tests': lambda r: r['cases'][1]['states']['primary']['tests'].update(
                {'manifest identifies the actual catalogue bytes': True}),
            'same count wrong tests': lambda r: r['cases'][2]['states']['reverted'].update(
                tests=r['cases'][2]['states']['initial']['tests']),
            'changed immutable file': lambda r: r['cases'][1]['states']['barrier']['files']['acceptance.test.mjs'].update(sha256='0'*64),
            'missing object': lambda r: r['cases'][2]['trees'].pop(next(iter(r['cases'][2]['trees']))),
            'retrospective object': lambda r: next(iter(r['cases'][2]['trees'].values())).update(first_stage='reverted'),
            'wrong selection': lambda r: r['cases'][2]['selected_earliest_refs'].update({'catalogue.json': '0'*40}),
            'false restoration': lambda r: r['cases'][2].update(restored_baseline=True),
            'hidden coverage gap': lambda r: r['cases'][2].update(unselected_changed_paths=[]),
            'terminal barrier': lambda r: r['cases'][1]['states']['barrier']['tools'][-1].update(status='completed'),
            'misordered intervention': lambda r: r['cases'][1].update(intervention_interval=[0, 1]),
            'missing process': lambda r: r['cases'][1]['process']['immediate'].pop('generator'),
            'false process exit': lambda r: r['cases'][1]['process']['immediate']['generator'].update(alive=False),
            'cleanup attributed to runtime': lambda r: r['cases'][2]['process'].update(generator_exit_observed_before_harness_cleanup=True),
            'premature harness cleanup': lambda r: r['cases'][2]['process'].update(cleanup_start_ns=0),
            'wrong process binary': lambda r: r['cases'][1]['process']['identities']['server'].update(image_sha256='0'*64),
            'unconfirmed child cleanup': lambda r: r['cases'][2]['process']['after_cleanup']['generator'].update(alive=True),
            'missing live read mislabeled': lambda r: r['cases'][2]['states']['primary'].update(remote_read_available=True),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(self.reference)
                mutation(changed)
                with self.assertRaises((EvidenceError, KeyError, ValueError)):
                    check(changed)


class HarnessTests(unittest.TestCase):
    def test_timeout_retains_failure(self):
        with tempfile.TemporaryDirectory(prefix='oc5-timeout-') as directory:
            root = Path(directory)
            recorder = Recorder(root, root, os.environ.copy())
            with self.assertRaises(TimeoutError):
                recorder.command([sys.executable, '-c', 'import time; time.sleep(10)'], 'timeout', timeout=.05)
            record = json.loads((root / 'timeout.process.json').read_text())
            self.assertTrue(record['timed_out'])
            self.assertIsNone(record['returncode'])
            self.assertTrue((root / 'timeout.stderr').exists())

    def test_expired_deadline_launches_nothing(self):
        with tempfile.TemporaryDirectory(prefix='oc5-deadline-') as directory:
            recorder = Recorder(directory, directory, os.environ.copy(), deadline=time.monotonic() - 1)
            with self.assertRaises(TimeoutError):
                recorder.command([sys.executable, '-c', 'raise Exception("must not execute")'], 'forbidden')
            self.assertEqual(list(Path(directory).iterdir()), [])

    @unittest.skipUnless(platform.system() == 'Windows', 'Windows retained process handles only')
    def test_owned_process_handle(self):
        from winprocess import Process
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        observer = None
        try:
            observer = Process.from_popen(child, Path(sys.executable))
            before = observer.observe()
            self.assertTrue(before['alive'])
            result = observer.terminate()
            self.assertFalse(result['after']['alive'])
            self.assertEqual(result['after']['creation_time_100ns'], before['creation_time_100ns'])
            self.assertEqual(result['after']['exit_code'], 87)
            child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
            if observer:
                observer.close()

    def test_generator_release_stop_and_deadline(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the fixture checks')
        for mode, expected_exit in (('release', 0), ('stop', 75), ('deadline', 76)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='oc5-generator-') as directory:
                root = Path(directory)
                workspace, control = root / 'workspace', root / 'control'
                workspace.mkdir()
                control.mkdir()
                for name in FILES:
                    (workspace / name).write_bytes(fixture(name))
                (workspace / 'labels.mjs').write_bytes(intended_files()['labels.mjs'])
                nonce = uuid.uuid4().hex
                env = dict(os.environ, LAB_CONTROL_DIR=str(control), LAB_RUN_NONCE=nonce,
                           LAB_GENERATOR_TIMEOUT_MS='700' if mode == 'deadline' else '5000')
                child = subprocess.Popen([node, './generate-catalogue.mjs'], cwd=workspace, env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    deadline = time.monotonic() + 10
                    while not (control / 'ready.json').exists():
                        self.assertIsNone(child.poll(), 'Generator exited before readiness')
                        self.assertLess(time.monotonic(), deadline, 'Generator readiness timeout')
                        time.sleep(.01)
                    ready = json.loads((control / 'ready.json').read_text())
                    self.assertEqual(ready, {'nonce': nonce, 'pid': child.pid, 'stage': 'catalogue-written'})
                    partial = {name: (workspace / name).read_bytes() for name in FILES}
                    self.assertEqual(acceptance(partial), [True, True, True, True, True, False])
                    if mode != 'deadline':
                        (control / (mode + '.json')).write_text(json.dumps({'nonce': nonce}), encoding='utf-8')
                    out, err = child.communicate(timeout=10)
                    self.assertEqual(child.returncode, expected_exit, err.decode())
                    self.assertEqual(out.count(b'CATALOGUE_WRITTEN'), 1)
                    current = {name: (workspace / name).read_bytes() for name in FILES}
                    self.assertEqual(current, intended_files() if mode == 'release' else partial)
                    test = subprocess.run([node, '--test', '--test-reporter=tap', 'acceptance.test.mjs'],
                                          cwd=workspace, capture_output=True, timeout=10,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    self.assertEqual(test.returncode, 0 if mode == 'release' else 1)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
