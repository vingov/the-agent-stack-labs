#!/usr/bin/env python3
"""Exercise Hermes session/workspace persistence without calling a provider."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


LAB_ID = "hermes-01-session-workspace"
MARKER = "HERMES-P1-LAB-2026-08-16-SESSION-CWD"
PRIMARY_ID = "part1-cli-primary"
FRESH_ID = "part1-cli-fresh"


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout


def git_output(source: Path, *arguments: str) -> str:
    return run(["git", "-C", str(source), *arguments]).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--hermes-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    root = args.lab_root.resolve()
    source = args.hermes_source.resolve()
    output = args.output.resolve()
    profile = root / "profile"
    workspace_a = root / "workspace-a"
    workspace_b = root / "workspace-b"
    task_path = workspace_a / "task.txt"
    state_db = profile / "state.db"

    for required in (profile, workspace_a, workspace_b, task_path, source):
        if not required.exists():
            raise SystemExit(f"Required path is missing: {required}")

    if state_db.exists():
        raise SystemExit(
            "The disposable profile already contains state.db. "
            "Create a fresh lab before running the probe again."
        )

    forbidden = [
        path
        for path in profile.rglob("*")
        if path.is_file()
        and path.name in {".env", "auth.json", "auth.lock", "cookies.json"}
    ]
    if forbidden:
        raise SystemExit("The disposable profile contains credential-shaped files.")

    hermes_environment = os.environ.copy()
    hermes_environment["HERMES_HOME"] = str(profile)
    os.environ["HERMES_HOME"] = str(profile)
    sys.path.insert(0, str(source))

    version_text = run(["hermes", "version"], env=hermes_environment)
    version_match = re.search(
        r"Hermes Agent v([^\s]+) \(([^)]+)\)", version_text
    )
    install_match = re.search(r"^Install directory:\s*(.+)$", version_text, re.MULTILINE)
    if not version_match or not install_match:
        raise SystemExit("Could not parse the installed Hermes version details.")

    installed_source = Path(install_match.group(1).strip()).resolve()
    if installed_source != source:
        raise SystemExit(
            "The supplied source does not match the active Hermes installation."
        )

    from hermes_state import SessionDB, workspace_key

    marker_text = task_path.read_text(encoding="utf-8").strip()
    task_sha256 = hashlib.sha256(task_path.read_bytes()).hexdigest()
    if marker_text != MARKER:
        raise SystemExit("The primary fixture marker is not the expected value.")

    db = SessionDB(state_db)
    db.create_session(PRIMARY_ID, source="cli", cwd=str(workspace_a))
    db.append_message(
        PRIMARY_ID,
        role="user",
        content="Read task.txt and preserve the synthetic marker.",
    )
    db.append_message(
        PRIMARY_ID,
        role="assistant",
        content=f"{MARKER} sha256={task_sha256}",
    )
    db.create_session(FRESH_ID, source="cli", cwd=str(workspace_b))
    db.append_message(
        FRESH_ID,
        role="user",
        content="This is a fresh session in workspace-b.",
    )

    primary = db.get_session(PRIMARY_ID)
    fresh = db.get_session(FRESH_ID)
    primary_messages = db.get_messages(PRIMARY_ID)
    fresh_messages = db.get_messages(FRESH_ID)

    assert primary is not None and fresh is not None
    assert Path(primary["cwd"]).resolve() == workspace_a
    assert Path(fresh["cwd"]).resolve() == workspace_b
    assert workspace_key(primary) == str(workspace_a)
    assert workspace_key(fresh) == str(workspace_b)
    assert db.resolve_resume_session_id(PRIMARY_ID) == PRIMARY_ID
    assert any(MARKER in str(row.get("content", "")) for row in primary_messages)
    assert not any(MARKER in str(row.get("content", "")) for row in fresh_messages)
    db.close()

    all_sessions = run(
        ["hermes", "sessions", "list", "--source", "cli", "--limit", "10"],
        env=hermes_environment,
    )
    workspace_sessions = run(
        [
            "hermes",
            "sessions",
            "list",
            "--source",
            "cli",
            "--workspace",
            "workspace-a",
            "--limit",
            "10",
        ],
        env=hermes_environment,
    )
    exported = run(
        [
            "hermes",
            "sessions",
            "export",
            "-",
            "--format",
            "jsonl",
            "--session-id",
            PRIMARY_ID,
            "--redact",
        ],
        env=hermes_environment,
    )
    exported_session = json.loads(exported.strip())

    assert PRIMARY_ID in all_sessions and FRESH_ID in all_sessions
    assert PRIMARY_ID in workspace_sessions and FRESH_ID not in workspace_sessions
    assert exported_session["id"] == PRIMARY_ID
    assert any(
        MARKER in str(row.get("content", ""))
        for row in exported_session.get("messages", [])
    )

    with sqlite3.connect(state_db) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        schema_version = connection.execute(
            "SELECT version FROM schema_version"
        ).fetchone()[0]
        session_count = connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]
        message_count = connection.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone()[0]

    commit = git_output(source, "rev-parse", "HEAD")
    source_dirty = bool(git_output(source, "status", "--porcelain"))
    storage_source_dirty = bool(
        git_output(
            source,
            "status",
            "--porcelain",
            "--",
            "hermes_state.py",
            "hermes_state_schema.py",
            "hermes_state_common.py",
        )
    )

    result = {
        "schema_version": 1,
        "lab_id": LAB_ID,
        "recorded_at": datetime.date.today().isoformat(),
        "runtime": {
            "version": version_match.group(1),
            "release": version_match.group(2),
            "commit": commit,
            "python": platform.python_version(),
            "operating_system": platform.system(),
            "architecture": platform.machine(),
            "source_worktree_dirty": source_dirty,
            "relevant_storage_source_dirty": storage_source_dirty,
        },
        "marker": {"value": MARKER, "sha256": task_sha256},
        "checks": {
            "state_db_created": state_db.is_file(),
            "primary_session_persisted": primary["id"] == PRIMARY_ID,
            "primary_workspace_persisted": True,
            "resume_resolves_primary": True,
            "fresh_session_id_is_distinct": PRIMARY_ID != FRESH_ID,
            "fresh_workspace_is_distinct": True,
            "marker_present_in_primary_only": True,
            "cli_lists_both_sessions": True,
            "cli_workspace_filter_isolates_primary": True,
            "cli_redacted_export_contains_primary": True,
        },
        "observations": {
            "primary": {
                "session_id": PRIMARY_ID,
                "source": primary["source"],
                "workspace": "workspace-a",
                "message_roles": [row["role"] for row in primary_messages],
            },
            "fresh": {
                "session_id": FRESH_ID,
                "source": fresh["source"],
                "workspace": "workspace-b",
                "message_roles": [row["role"] for row in fresh_messages],
            },
            "database_schema_version": schema_version,
            "required_tables_present": {
                "sessions": "sessions" in tables,
                "messages": "messages" in tables,
            },
            "session_count": session_count,
            "message_count": message_count,
        },
        "evidence_boundary": {
            "provider_called": False,
            "gateway_started": False,
            "tool_loop_executed": False,
            "storage_api_exercised": True,
            "installed_sessions_cli_exercised": True,
            "contains_credentials": False,
            "contains_absolute_paths": False,
        },
    }

    serialized = json.dumps(result, indent=2) + "\n"
    if str(root) in serialized or str(Path.home()) in serialized:
        raise SystemExit("Refusing to write a result containing an absolute path.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
