#!/usr/bin/env python3
"""Network-free execution-contract fixture for Hermes Part 4.

The fixture separates a logical operation from its attempts. A committed
operation index is immutable; later duplicate attempts receive their own
receipts without replacing the original success evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EXECUTION_MODES = ("script", "direct", "delegated", "goal", "cron")


class ContractError(RuntimeError):
    """A policy or evidence precondition failed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON object required: {path.name}")
    return value


def atomic_json(path: Path, value: dict[str, Any], *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        raise ContractError(f"immutable evidence already exists: {path.name}")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with source.open("rb") as src, os.fdopen(handle, "wb") as dst:
            for chunk in iter(lambda: src.read(65536), b""):
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def relative_to_workspace(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def validate_id(label: str, value: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ContractError(f"invalid {label}; use 1-128 letters, digits, dot, underscore, or hyphen")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--execution-mode", required=True, choices=EXECUTION_MODES)
    parser.add_argument("--procedure", required=True)
    parser.add_argument("--output", default="state/deployed/artifact.txt")
    parser.add_argument("--dry-run-receipt", type=Path)
    phase = parser.add_mutually_exclusive_group(required=True)
    phase.add_argument("--dry-run", action="store_true")
    phase.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = args.workspace.resolve()
    validate_id("operation ID", args.operation_id)
    validate_id("attempt ID", args.attempt_id)

    source = workspace / "input" / "artifact.txt"
    policy_path = workspace / "policy" / "policy-v2.json"
    attempt_path = workspace / "evidence" / "attempts" / f"{args.attempt_id}.json"
    operation_path = workspace / "evidence" / "operations" / f"{args.operation_id}.json"

    receipt: dict[str, Any] = {
        "schema_version": 1,
        "operation_id": args.operation_id,
        "attempt_id": args.attempt_id,
        "execution_mode": args.execution_mode,
        "phase": "dry-run" if args.dry_run else "apply",
        "created_at": utc_now(),
        "status": "rejected",
        "mutation": "not-run",
        "verification": "not-run",
        "network_used": False,
    }

    try:
        if attempt_path.exists():
            raise ContractError(f"attempt ID already exists: {args.attempt_id}")
        policy = load_json(policy_path)
        receipt["policy_id"] = policy.get("policy_id")
        receipt["required_procedure"] = policy.get("required_procedure")
        receipt["supplied_procedure"] = args.procedure

        if args.procedure != policy.get("required_procedure"):
            raise ContractError("stale or unknown procedure")
        procedure_path = workspace / "procedures" / f"{args.procedure}.md"
        if not procedure_path.is_file():
            raise ContractError("required procedure file is missing")
        if not source.is_file():
            raise ContractError("source artifact is missing")

        source_hash = sha256(source)
        receipt["source_sha256"] = source_hash
        if source_hash != policy.get("required_sha256"):
            raise ContractError("source SHA-256 does not match policy")

        requested_output = (workspace / args.output).resolve()
        allowed_output = (workspace / str(policy.get("allowed_output", ""))).resolve()
        try:
            requested_relative = relative_to_workspace(requested_output, workspace)
        except ValueError as exc:
            raise ContractError("output escapes the workspace") from exc
        receipt["requested_output"] = requested_relative
        receipt["allowed_output"] = relative_to_workspace(allowed_output, workspace)
        if requested_output != allowed_output:
            raise ContractError("output path is not allowed by policy")

        if args.dry_run:
            receipt.update(
                {
                    "status": "dry-run-passed",
                    "dry_run": "passed",
                    "mutation": "not-run",
                    "verification": "passed",
                    "output_sha256": source_hash,
                }
            )
            atomic_json(attempt_path, receipt, immutable=True)
            print(json.dumps(receipt, sort_keys=True))
            return 0

        if policy.get("require_dry_run"):
            if args.dry_run_receipt is None:
                raise ContractError("a successful dry-run receipt is required")
            dry_run_path = args.dry_run_receipt
            if not dry_run_path.is_absolute():
                dry_run_path = workspace / dry_run_path
            dry_run_path = dry_run_path.resolve()
            try:
                dry_run_path.relative_to((workspace / "evidence" / "attempts").resolve())
            except ValueError as exc:
                raise ContractError("dry-run receipt must be inside evidence/attempts") from exc
            dry_run = load_json(dry_run_path)
            required_pairs = {
                "operation_id": args.operation_id,
                "status": "dry-run-passed",
                "execution_mode": args.execution_mode,
                "supplied_procedure": args.procedure,
                "source_sha256": source_hash,
                "requested_output": requested_relative,
            }
            for key, expected in required_pairs.items():
                if dry_run.get(key) != expected:
                    raise ContractError(f"dry-run receipt mismatch: {key}")
            receipt["dry_run_attempt_id"] = dry_run.get("attempt_id")

        if operation_path.exists():
            committed = load_json(operation_path)
            receipt.update(
                {
                    "status": "duplicate",
                    "mutation": "suppressed",
                    "verification": "not-run",
                    "primary_attempt_id": committed.get("primary_attempt_id"),
                    "output_sha256": committed.get("output_sha256"),
                }
            )
            atomic_json(attempt_path, receipt, immutable=True)
            print(json.dumps(receipt, sort_keys=True))
            return 3

        atomic_copy(source, requested_output)
        output_hash = sha256(requested_output)
        if output_hash != source_hash:
            raise ContractError("deployed artifact verification failed")

        receipt.update(
            {
                "status": "committed",
                "dry_run": "passed",
                "mutation": "applied",
                "verification": "passed",
                "output_sha256": output_hash,
            }
        )
        atomic_json(attempt_path, receipt, immutable=True)
        operation = {
            "schema_version": 1,
            "operation_id": args.operation_id,
            "status": "committed",
            "primary_attempt_id": args.attempt_id,
            "execution_mode": args.execution_mode,
            "policy_id": policy.get("policy_id"),
            "procedure": args.procedure,
            "output": requested_relative,
            "output_sha256": output_hash,
            "committed_at": receipt["created_at"],
        }
        atomic_json(operation_path, operation, immutable=True)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except ContractError as exc:
        receipt["reason"] = str(exc)
        if not attempt_path.exists():
            atomic_json(attempt_path, receipt, immutable=True)
        print(json.dumps(receipt, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
