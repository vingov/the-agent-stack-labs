"""Portable tests: refuse overwrites and reject misleading evidence."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from initialize_lab import initialize
from verify_reference import verify_receipt, verify_bundle

REFERENCE = Path(__file__).resolve().parents[1] / "reference-results/windows-2026-09-04"


class LabTests(unittest.TestCase):
    def test_initializer_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "lab"
            initialize(target)
            before = (target / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                initialize(target)
            self.assertEqual(before, (target / "manifest.json").read_bytes())

    def test_real_probe_reads_sibling_and_refuses_receipt_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = initialize(Path(directory) / "lab")
            workspace = root / "workspace"
            command = [sys.executable, "canary_probe.py", "--receipt", "attempt.json"]
            result = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((root / "manifest.json").read_text())
            receipt = json.loads((workspace / "attempt.json").read_text())
            for name in ("inside", "outside"):
                self.assertTrue(receipt[name]["readable"])
                self.assertEqual(receipt[name]["sha256"], manifest["canary_hashes"][name])
            before = (workspace / "attempt.json").read_bytes()
            self.assertNotEqual(subprocess.run(command, cwd=workspace, capture_output=True).returncode, 0)
            self.assertEqual(before, (workspace / "attempt.json").read_bytes())

    def test_published_bundle_consistency(self):
        self.assertEqual(verify_bundle(REFERENCE), [])

    def test_pass_flag_cannot_hide_bad_evidence(self):
        manifest = json.loads((REFERENCE / "manifest.json").read_text())
        original = json.loads((REFERENCE / "docker.json").read_text())
        mutations = {
            "visible outside": lambda r: r["probe"]["outside"].update(readable=True),
            "wrong inside bytes": lambda r: r["probe"]["inside"].update(sha256="0" * 64),
            "missing check": lambda r: r["checks"].pop("probe_unchanged"),
            "no tool execution": lambda r: r.update(tool_exit_codes=[]),
            "root execution": lambda r: r["containers"][0].update(user="0"),
            "network enabled": lambda r: r["containers"][0].update(network_mode="bridge"),
            "writable profile": lambda r: next(m for m in r["containers"][0]["mounts"] if m["destination"].endswith("/skills")).update(writable=True),
            "wrong mount source": lambda r: r["containers"][0]["mounts"][0].update(source_matches_disposable_lab=False),
            "different code": lambda r: r.update(source_commit="0" * 40),
            "unverified cleanup": lambda r: r["checks"].update(session_containers_removed=False),
        }
        for label, mutate in mutations.items():
            with self.subTest(label):
                receipt = copy.deepcopy(original)
                mutate(receipt)
                self.assertTrue(receipt["passed"])
                self.assertTrue(verify_receipt(receipt, manifest, "docker", False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
