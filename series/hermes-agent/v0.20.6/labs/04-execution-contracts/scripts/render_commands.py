#!/usr/bin/env python3
"""Render exact, punctuation-free commands for one Part 4 operation."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EXECUTION_MODES = ("script", "direct", "delegated", "goal", "cron")


def shell_join(arguments: list[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--execution-mode", choices=EXECUTION_MODES, required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    if not SAFE_ID.fullmatch(args.operation_id):
        parser.error("invalid operation ID")

    workspace = args.workspace.resolve()
    runner = workspace / "bin" / "run_contract.py"
    verifier = workspace / "bin" / "verify_operation.py"
    dry_id = f"{args.operation_id}-dry"
    apply_id = f"{args.operation_id}-apply"
    dry_receipt = workspace / "evidence" / "attempts" / f"{dry_id}.json"
    common = [
        args.python,
        str(runner),
        "--workspace",
        str(workspace),
        "--operation-id",
        args.operation_id,
        "--execution-mode",
        args.execution_mode,
        "--procedure",
        "HERMES-P4-PROCEDURE-V2",
    ]
    result = {
        "schema_version": 1,
        "workspace": str(workspace),
        "operation_id": args.operation_id,
        "execution_mode": args.execution_mode,
        "dry_run": shell_join(common + ["--attempt-id", dry_id, "--dry-run"]),
        "apply": shell_join(
            common
            + [
                "--attempt-id",
                apply_id,
                "--dry-run-receipt",
                str(dry_receipt),
                "--apply",
            ]
        ),
        "verify": shell_join(
            [
                args.python,
                str(verifier),
                "--workspace",
                str(workspace),
                "--operation-id",
                args.operation_id,
                "--execution-mode",
                args.execution_mode,
            ]
        ),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
