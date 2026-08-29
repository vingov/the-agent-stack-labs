#!/usr/bin/env python3
"""Seed a bounded Hermes persistent goal for the Part 4 experiment."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from hermes_cli.goals import GoalContract, GoalManager


def quote(value: str | Path) -> str:
    """Quote one command argument for the current platform's shell."""
    value = str(value)
    if sys.platform == "win32":
        return f'"{value}"'
    return shlex.quote(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--operation-id", default="goal-live-v2")
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--gate-retries", type=int, default=3)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    runner = workspace / "bin" / "run_contract.py"
    verifier = workspace / "bin" / "verify_operation.py"
    dry_receipt = workspace / "evidence" / "attempts" / f"{args.operation_id}-dry.json"

    common = (
        f"{quote(args.python)} {quote(runner)} --workspace {quote(workspace)} "
        f"--operation-id {args.operation_id} --execution-mode goal "
        "--procedure HERMES-P4-PROCEDURE-V2"
    )
    dry = f"{common} --attempt-id {args.operation_id}-dry --dry-run"
    apply = (
        f"{common} --attempt-id {args.operation_id}-apply "
        f"--dry-run-receipt {quote(dry_receipt)} --apply"
    )
    gate = (
        f"{quote(args.python)} {quote(verifier)} --workspace {quote(workspace)} "
        f"--operation-id {args.operation_id} --execution-mode goal"
    )
    goal = "\n".join(
        [
            f"Complete operation {args.operation_id} by executing exactly two commands in order.",
            "Do not include the marker lines or punctuation in either command.",
            "BEGIN DRY COMMAND",
            dry,
            "END DRY COMMAND",
            "BEGIN APPLY COMMAND",
            apply,
            "END APPLY COMMAND",
            "Do not use terminal network commands or modify any other path.",
        ]
    )

    manager = GoalManager(args.session_id)
    manager.set(
        goal,
        max_turns=args.max_turns,
        contract=GoalContract(
            outcome=f"Committed operation {args.operation_id}",
            verification=gate,
            constraints="No network; no writes outside the bounded workspace",
            boundaries=f"Only {workspace}",
            stop_when="The deterministic gate passes or the turn budget pauses",
        ),
    )
    manager.add_gate(gate, timeout_seconds=30, max_retries=args.gate_retries)
    print(manager.status_line())
    print(manager.render_gates())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
