#!/usr/bin/env python3
"""Create a new, synthetic Part 5 lab; never copy an existing Hermes profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path


def initialize(destination: Path | None = None) -> Path:
    if destination is None:
        root = Path(tempfile.mkdtemp(prefix="hermes-part5-"))
    else:
        root = destination.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=False)
    if os.name == "posix":
        root.chmod(0o700)
    for name in ("workspace", "outside", "profile", "receipts"):
        (root / name).mkdir()
    if os.name == "posix":
        # The non-root container needs to create a receipt on this bind mount.
        # The private parent still prevents other host users from traversing it.
        (root / "workspace").chmod(0o777)
    (root / ".part5-lab").write_text("synthetic disposable lab\n", encoding="utf-8")
    (root / "workspace" / ".part5-workspace").write_text("synthetic workspace\n", encoding="utf-8")
    hashes = {}
    for name, relative in (("inside", "workspace/inside.txt"), ("outside", "outside/outside.txt")):
        payload = f"HERMES-P5-{name.upper()}-{uuid.uuid4().hex}\n".encode()
        (root / relative).write_bytes(payload)
        hashes[name] = hashlib.sha256(payload).hexdigest()
    shutil.copy2(Path(__file__).with_name("canary_probe.py"), root / "workspace" / "canary_probe.py")
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": 1, "lab_id": "hermes-05-security-boundaries",
        "canary_hashes": hashes,
        "probe_sha256": hashlib.sha256((root / "workspace/canary_probe.py").read_bytes()).hexdigest(),
        "contains_credentials": False,
    }, indent=2) + "\n", encoding="utf-8")
    (root / "profile/config.yaml").write_text(
        "model:\n  default: gpt-5.6-sol\n  provider: openai-codex\n"
        "terminal:\n  backend: local\n"
        "approvals:\n  mode: manual\n  single_query_mode: deny\n  cron_mode: deny\n"
        "  unattended_mode: deny\n"
        "memory:\n  memory_enabled: false\n  user_profile_enabled: false\n"
        "background_review:\n  enabled: false\n"
        "plugins:\n  enabled: false\n",
        encoding="utf-8",
    )
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    print(initialize(parser.parse_args().destination))
