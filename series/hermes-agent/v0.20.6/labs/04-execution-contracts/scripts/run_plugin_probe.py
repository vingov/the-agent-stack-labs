#!/usr/bin/env python3
"""Exercise the pinned Hermes PluginManager with a synthetic read-only plugin.

This optional Investigator probe is intentionally local and provider-free. It
creates a disposable Hermes profile inside the lab workspace, discovers an
enabled user plugin through the real PluginManager, invokes its registered
tool and post-tool hook, verifies the sanitized audit event, and confirms that
unloading the manager removes the scoped tool registration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path


EXPECTED_BYTES = 91
EXPECTED_SHA256 = "eb82803246ce25226ea8b769184760cb17df0dac56f3c0fdaed0a444f101f4ad"
PINNED_COMMIT = "5fc308a70719a83cccdbba4c0e39c23f5a8239d5"
PLUGIN_NAME = "fixture_inspector"
TOOL_NAME = "fixture_inspect"


PLUGIN_SOURCE = r'''"""Synthetic read-only plugin for the Part 4 lab."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _inspect(_args, **_kwargs):
    source = Path(os.environ["HERMES_P4_PLUGIN_SOURCE"])
    payload = source.read_bytes()
    return {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _audit(**kwargs):
    audit_path = Path(os.environ["HERMES_P4_PLUGIN_AUDIT"])
    event = {
        "tool_name": kwargs.get("tool_name"),
        "status": kwargs.get("status"),
        "argument_keys": sorted((kwargs.get("args") or {}).keys()),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {"recorded": True}


def register(ctx):
    ctx.register_tool(
        name="fixture_inspect",
        toolset="fixture_inspector",
        schema={
            "name": "fixture_inspect",
            "description": "Return the byte length and SHA-256 of the Part 4 fixture.",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_inspect,
    )
    ctx.register_hook("post_tool_call", _audit)
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Initialized Part 4 lab workspace",
    )
    return parser.parse_args()


def require_fixture(workspace: Path) -> Path:
    source = workspace / "input" / "artifact.txt"
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != EXPECTED_BYTES or digest != EXPECTED_SHA256:
        raise SystemExit(
            "fixture mismatch: initialize a fresh Part 4 workspace before running the probe"
        )
    return source


def write_plugin(home: Path) -> None:
    plugin_dir = home / "plugins" / PLUGIN_NAME
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.yaml").write_text(
        "\n".join(
            [
                f"name: {PLUGIN_NAME}",
                "version: 0.1.0",
                "description: Synthetic read-only Part 4 fixture inspector",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
    (home / "config.yaml").write_text(
        f"plugins:\n  enabled:\n    - {PLUGIN_NAME}\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    source = require_fixture(workspace)
    profile = workspace / "plugin-probe-home"
    audit_path = workspace / "receipts" / "plugin-probe-audit.jsonl"
    result_path = workspace / "receipts" / "plugin-probe.json"

    write_plugin(profile)
    os.environ["HERMES_HOME"] = str(profile)
    os.environ["HERMES_P4_PLUGIN_SOURCE"] = str(source)
    os.environ["HERMES_P4_PLUGIN_AUDIT"] = str(audit_path)

    # Import only after HERMES_HOME is pinned to the disposable profile.
    from hermes_cli.plugins import PluginManager
    from tools.registry import registry

    manager = PluginManager()
    manager.discover_and_load()
    state = manager._plugins.get(PLUGIN_NAME)
    if state is None or not state.enabled or state.error:
        raise SystemExit(f"plugin did not load cleanly: {state!r}")

    entry = registry.get_entry(TOOL_NAME, scope=manager.scope_key)
    if entry is None or entry.toolset != PLUGIN_NAME:
        raise SystemExit("PluginManager did not expose fixture_inspect in the expected toolset")

    tool_result = entry.handler({})
    manager.invoke_hook(
        "post_tool_call",
        tool_name=TOOL_NAME,
        args={},
        result=tool_result,
        status="ok",
    )
    audit_event = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])

    if tool_result != {"bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256}:
        raise SystemExit(f"unexpected plugin tool result: {tool_result!r}")
    expected_audit = {
        "argument_keys": [],
        "status": "ok",
        "tool_name": TOOL_NAME,
    }
    if audit_event != expected_audit:
        raise SystemExit(f"unexpected plugin audit event: {audit_event!r}")

    manager.unload()
    removed_after_unload = registry.get_entry(TOOL_NAME, scope=manager.scope_key) is None
    if not removed_after_unload:
        raise SystemExit("plugin tool remained registered after PluginManager.unload()")

    result = {
        "schema_version": 1,
        "status": "PASS",
        "evidence_class": "OBSERVED_LOCAL_PLUGIN_HOST",
        "hermes_commit": PINNED_COMMIT,
        "python": platform.python_version(),
        "platform": platform.system(),
        "profile_isolated": True,
        "provider_called": False,
        "external_service_called": False,
        "plugin": {
            "name": PLUGIN_NAME,
            "enabled": True,
            "tool_registered": True,
            "toolset": PLUGIN_NAME,
            "post_tool_hook_recorded": True,
            "tool_removed_after_unload": removed_after_unload,
        },
        "tool_result": tool_result,
        "audit_event": audit_event,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
