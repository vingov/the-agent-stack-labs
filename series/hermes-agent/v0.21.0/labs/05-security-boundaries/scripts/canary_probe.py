#!/usr/bin/env python3
"""Read two synthetic lab markers and emit a receipt, without network access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path


def inspect(path: Path) -> dict:
    try:
        value = path.read_bytes()
        return {"readable": True, "sha256": hashlib.sha256(value).hexdigest(), "error": None}
    except (FileNotFoundError, PermissionError) as exc:
        return {"readable": False, "sha256": None, "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    if Path(args.receipt).name != args.receipt or not args.receipt.endswith(".json"):
        parser.error("receipt must be a JSON filename in the current workspace")
    workspace = Path.cwd()
    if not (workspace / ".part5-workspace").is_file():
        parser.error("run only inside an initialized Part 5 workspace")
    receipt_path = workspace / args.receipt
    if receipt_path.exists():
        parser.error("receipt already exists; use a fresh attempt name")
    result = {
        "schema_version": 1,
        "requested_paths": {"inside": "inside.txt", "outside": "../outside/outside.txt"},
        "platform": platform.system(),
        "effective_uid": os.geteuid() if hasattr(os, "geteuid") else None,
        "inside": inspect(workspace / "inside.txt"),
        "outside": inspect(workspace / ".." / "outside" / "outside.txt"),
        "network_used": False,
    }
    payload = json.dumps(result, indent=2) + "\n"
    with receipt_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
    print(payload, end="")
    return 0 if result["inside"]["readable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
