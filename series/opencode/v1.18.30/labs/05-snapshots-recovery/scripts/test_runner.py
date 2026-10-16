"""Exercise timeout diagnostics with a disposable local child, no OpenCode."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from run_lab import execute


class RunnerFailureTests(unittest.TestCase):
    def test_timeout_keeps_output_and_command(self):
        command = [sys.executable, '-c',
                   "import sys,time; print('partial output',flush=True); "
                   "print('partial error',file=sys.stderr,flush=True); time.sleep(30)"]
        with tempfile.TemporaryDirectory(prefix='recovery-timeout-test-') as temporary:
            root = Path(temporary)
            with self.assertRaises(subprocess.TimeoutExpired):
                execute(command, root, 'timeout', root, os.environ.copy(), timeout=2)
            self.assertEqual((root / 'timeout.stdout.txt').read_text(), 'partial output\n')
            self.assertEqual((root / 'timeout.stderr.txt').read_text(), 'partial error\n')
            record = json.loads((root / 'timeout.process.json').read_text())
            self.assertEqual(record, {'command': command, 'exit': None,
                                     'timed_out': True, 'timeout_seconds': 2})


if __name__ == '__main__':
    unittest.main()
