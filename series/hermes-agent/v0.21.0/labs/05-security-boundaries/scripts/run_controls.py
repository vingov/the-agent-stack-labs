#!/usr/bin/env python3
"""Exercise actual Hermes file, approval, MCP and audit-discovery paths.

No model, fake security implementation or real target credentials are used.
The approval callback supplies scripted operator decisions, not UI clicks.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from initialize_lab import initialize
from run_boundary import PIN


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() != PIN:
        parser.error("unexpected Hermes source revision")
    server_path = Path(__file__).with_name("synthetic_mcp.py").resolve()
    root = initialize(args.destination)
    workspace = root / "workspace"
    for key in list(os.environ):
        if key.startswith("TERMINAL_") or key in ("HERMES_YOLO", "HERMES_WRITE_SAFE_ROOT"):
            os.environ.pop(key)
    os.environ["HERMES_HOME"] = str(root / "profile")
    os.environ["HERMES_SINGLE_QUERY_SESSION"] = "1"
    os.environ["HERMES_WRITE_SAFE_ROOT"] = str(workspace)
    os.environ["PART5_AMBIENT_CANARY"] = "synthetic-ambient"
    sys.path.insert(0, str(source))
    import yaml
    config_path = root / "profile/config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["terminal"]["cwd"] = str(workspace)
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    os.chdir(workspace)
    from tools import file_tools, terminal_tool, mcp_tool
    from tools.registry import registry
    checks, observations = {}, {}

    def write(path: Path, content: str, task: str) -> dict:
        return json.loads(file_tools.write_file_tool(str(path), content, task_id=task))

    try:
        allowed = workspace / "allowed.txt"
        allowed_result = write(allowed, "synthetic allowed\n", "p5-allow")
        checks["file_tool_inside_write_succeeded"] = not allowed_result.get("error") and allowed.read_text() == "synthetic allowed\n"
        denied = root / "outside/denied.txt"
        denied_result = write(denied, "synthetic denied\n", "p5-deny")
        checks["file_tool_outside_write_denied"] = bool(denied_result.get("error")) and not denied.exists()
        # A separate inline command demonstrates the unattended approval gate.
        # Do not retry a denied command through an alternate execution path.
        terminal_target = root / "outside/terminal-only.txt"
        code = "from pathlib import Path; Path('../outside/terminal-only.txt').write_text('synthetic terminal\\n')"
        command = shlex.quote(Path(sys.executable).as_posix()) + " -c " + shlex.quote(code)
        terminal_result = json.loads(terminal_tool.terminal_tool(command, task_id="p5-terminal-scope"))
        (root / "receipts/terminal-private.json").write_text(json.dumps(terminal_result, indent=2), encoding="utf-8")
        checks["terminal_inline_command_blocked_without_operator"] = (
            terminal_result.get("status") == "blocked"
            and "single-query" in terminal_result.get("error", "")
            and not terminal_target.exists())
        observations["terminal_approval"] = "inline -c script flagged; single-query deny; no file created; no alternate-path retry"

        instruction = workspace / "AGENTS.md"
        decisions = []
        def decision(value):
            def callback(*_args, **_kwargs):
                decisions.append(value)
                return value
            return callback
        terminal_tool.set_approval_callback(decision("deny"))
        denied_instruction = write(instruction, "Synthetic instruction fixture.\n", "p5-instruction-deny")
        checks["instruction_deny_preserved_absence"] = bool(denied_instruction.get("error")) and not instruction.exists()
        terminal_tool.set_approval_callback(decision("once"))
        approved_instruction = write(instruction, "Synthetic instruction fixture.\n", "p5-instruction-once")
        checks["instruction_once_committed"] = not approved_instruction.get("error") and instruction.read_text() == "Synthetic instruction fixture.\n"
        terminal_tool.set_approval_callback(None)
        repeat_instruction = write(instruction, "Changed synthetic fixture.\n", "p5-instruction-repeat")
        checks["instruction_without_callback_denied"] = bool(repeat_instruction.get("error")) and instruction.read_text() == "Synthetic instruction fixture.\n"
        observations["approval_decisions"] = decisions
        observations["approval_surface"] = "scripted callback; no human UI approval or provider call"

        mcp_tool.register_mcp_servers({"part5": {
            "command": sys.executable, "args": [str(server_path)],
            "env": {"PART5_EXPLICIT_CANARY": "synthetic-explicit"},
            "tools": {"include": ["environment_report"]},
            "connect_timeout": 20, "timeout": 20,
        }})
        selected = mcp_tool.mcp_prefixed_tool_name("part5", "environment_report")
        withheld = mcp_tool.mcp_prefixed_tool_name("part5", "withheld_noop")
        names = registry.get_all_tool_names()
        checks["mcp_selected_tool_registered"] = selected in names
        checks["mcp_withheld_tool_not_registered"] = withheld not in names
        raw = registry.dispatch(selected, {})
        # Preserve only synthetic booleans, regardless of SDK wrapper shape.
        encoded = json.dumps(raw) if not isinstance(raw, str) else raw
        (root / "receipts/mcp-private.json").write_text(encoded, encoding="utf-8")
        decoded = json.loads(encoded)
        if isinstance(decoded, dict) and "structuredContent" in decoded:
            report = decoded["structuredContent"]
        elif isinstance(decoded, dict) and "content" in decoded:
            report = json.loads(next(item["text"] for item in decoded["content"] if item.get("type") == "text"))
        else:
            report = decoded
        # Hermes may flatten the content text into a result field.
        if isinstance(report, dict) and isinstance(report.get("result"), str):
            report = json.loads(report["result"])
        checks["mcp_ambient_canary_absent"] = report.get("ambient_canary_present") is False
        checks["mcp_explicit_canary_present"] = report.get("explicit_canary_present") is True
        observations["mcp_synthetic_environment"] = {k: report.get(k) for k in ("ambient_canary_present", "explicit_canary_present")}

        # Discovery only: these declarations are never installed or executed.
        plugin = root / "profile/plugins/synthetic-audit"
        plugin.mkdir(parents=True)
        (plugin / "requirements.txt").write_text("requests==2.32.5\nFlask\n", encoding="utf-8")
        from hermes_cli.security_audit import _discover_plugins, _extract_mcp_component
        components = _discover_plugins(root / "profile")
        checks["audit_detects_exact_plugin_pin"] = any(c.name == "requests" and c.version == "2.32.5" for c in components)
        checks["audit_skips_unversioned_plugin_requirement"] = not any(c.name.lower() == "flask" for c in components)
        checks["audit_local_mcp_path_unresolved"] = _extract_mcp_component("part5", sys.executable, [str(server_path)]) is None
        observations["audit_scope"] = "actual dependency discovery over synthetic declarations; no OSV query, install, or security certification"
    finally:
        terminal_tool.set_approval_callback(None)
        mcp_tool.shutdown_mcp_servers()
        terminal_tool.cleanup_all_environments()
    result = {"lab_id": "hermes-05-security-boundaries", "source_commit": PIN,
        "execution": "real Hermes runtime paths; provider-free controls",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks, "observations": observations, "passed": all(checks.values())}
    output = root / "receipts/controls.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
