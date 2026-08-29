#!/usr/bin/env python3
"""Run the network-free Part 4 control matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(script: Path, workspace: Path, *arguments: str) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(script), "--workspace", str(workspace), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"fixture returned no JSON: {process.stderr}")
    receipt = json.loads(lines[-1])
    receipt["exit_code"] = process.returncode
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    script = Path(__file__).with_name("run_contract.py")
    base = ["--execution-mode", "script", "--procedure", "HERMES-P4-PROCEDURE-V2"]

    dry = invoke(
        script,
        workspace,
        "--operation-id",
        "control-success",
        "--attempt-id",
        "control-success-dry",
        *base,
        "--dry-run",
    )
    applied = invoke(
        script,
        workspace,
        "--operation-id",
        "control-success",
        "--attempt-id",
        "control-success-apply",
        *base,
        "--dry-run-receipt",
        "evidence/attempts/control-success-dry.json",
        "--apply",
    )
    primary_path = workspace / "evidence" / "attempts" / "control-success-apply.json"
    primary_before = digest(primary_path)
    duplicate = invoke(
        script,
        workspace,
        "--operation-id",
        "control-success",
        "--attempt-id",
        "control-success-duplicate",
        *base,
        "--dry-run-receipt",
        "evidence/attempts/control-success-dry.json",
        "--apply",
    )
    primary_after = digest(primary_path)
    stale = invoke(
        script,
        workspace,
        "--operation-id",
        "control-stale",
        "--attempt-id",
        "control-stale-dry",
        "--execution-mode",
        "script",
        "--procedure",
        "HERMES-P4-PROCEDURE-V1",
        "--dry-run",
    )
    missing_dry = invoke(
        script,
        workspace,
        "--operation-id",
        "control-missing-dry",
        "--attempt-id",
        "control-missing-dry-apply",
        *base,
        "--apply",
    )
    denied = invoke(
        script,
        workspace,
        "--operation-id",
        "control-denied-path",
        "--attempt-id",
        "control-denied-path-dry",
        *base,
        "--output",
        "state/other/artifact.txt",
        "--dry-run",
    )

    checks = {
        "dry_run_passed": dry["status"] == "dry-run-passed" and dry["exit_code"] == 0,
        "apply_committed": applied["status"] == "committed" and applied["exit_code"] == 0,
        "duplicate_suppressed": duplicate["status"] == "duplicate" and duplicate["exit_code"] == 3,
        "primary_receipt_immutable": primary_before == primary_after,
        "stale_procedure_rejected": stale["status"] == "rejected" and stale["exit_code"] == 2,
        "missing_dry_run_rejected": missing_dry["status"] == "rejected" and missing_dry["exit_code"] == 2,
        "denied_path_rejected": denied["status"] == "rejected" and denied["exit_code"] == 2,
    }
    result = {
        "schema_version": 1,
        "lab_id": "hermes-04-execution-contracts",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "artifact": {
            "bytes": (workspace / "input" / "artifact.txt").stat().st_size,
            "sha256": digest(workspace / "state" / "deployed" / "artifact.txt"),
        },
        "receipts": {
            "successful_operation": "evidence/operations/control-success.json",
            "primary_attempt": "evidence/attempts/control-success-apply.json",
            "duplicate_attempt": "evidence/attempts/control-success-duplicate.json",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
