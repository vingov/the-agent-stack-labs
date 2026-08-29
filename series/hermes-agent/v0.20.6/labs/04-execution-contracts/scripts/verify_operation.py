#!/usr/bin/env python3
"""Verify a committed Part 4 operation without trusting agent prose."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EXECUTION_MODES = ("script", "direct", "delegated", "goal", "cron")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--execution-mode", required=True, choices=EXECUTION_MODES)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not SAFE_ID.fullmatch(args.operation_id):
        print("invalid operation ID")
        return 2
    operation_path = workspace / "evidence" / "operations" / f"{args.operation_id}.json"
    policy_path = workspace / "policy" / "policy-v2.json"
    if not operation_path.is_file():
        print(f"missing operation receipt: {operation_path}")
        return 2

    operation = json.loads(operation_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    output = (workspace / operation.get("output", "")).resolve()
    try:
        output.relative_to(workspace)
    except ValueError:
        print("operation output escapes the workspace")
        return 2
    checks = {
        "status_committed": operation.get("status") == "committed",
        "mode_matches": operation.get("execution_mode") == args.execution_mode,
        "policy_matches": operation.get("policy_id") == policy.get("policy_id"),
        "procedure_matches": operation.get("procedure") == policy.get("required_procedure"),
        "output_exists": output.is_file(),
        "output_hash_matches": output.is_file()
        and sha256(output) == policy.get("required_sha256") == operation.get("output_sha256"),
    }
    result = {
        "operation_id": args.operation_id,
        "execution_mode": args.execution_mode,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "output_sha256": operation.get("output_sha256"),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
