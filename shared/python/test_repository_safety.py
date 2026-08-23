#!/usr/bin/env python3
"""Dependency-free repository safety checks for macOS and Linux contributors."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_NAMES = {".env", "auth.json", "auth.lock", "cookies.json", "state.db"}
TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".ps1",
    ".sh",
    ".py",
    ".toml",
}
PATTERNS = {
    "Private key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "Bearer credential": re.compile(
        r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE
    ),
    "Assigned secret": re.compile(
        r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9._-]{16,}",
        re.IGNORECASE,
    ),
    "Windows home path": re.compile(r"[A-Z]:\\Users\\[^\\\s]+", re.IGNORECASE),
}
REQUIRED_FILES = {
    "README.md",
    "COURSE_MAP.md",
    "SECURITY.md",
    "catalog/labs.yaml",
    "shared/powershell/Test-RepositorySafety.ps1",
    "shared/python/test_repository_safety.py",
    "series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/lab.yaml",
    "series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/initialize-lab.sh",
    "series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/run-storage-probe.py",
    "series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/reference-results/"
    "windows-2026-08-16/result.json",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/lab.yaml",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/Initialize-Lab.ps1",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/initialize-lab.sh",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/test-lab-fixtures.sh",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/new-sha256-manifest.sh",
    "series/hermes-agent/v0.20.1/labs/02-context-and-compression/reference-results/"
    "windows-2026-08-15/result.json",
    "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/lab.yaml",
    "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/Initialize-Lab.ps1",
    "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/initialize-lab.sh",
    "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/test-lab-fixtures.sh",
    "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/reference-results/"
    "windows-2026-08-23/result.json",
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def repository_files() -> list[Path]:
    return sorted(
        path
        for path in REPOSITORY_ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "runs" not in path.relative_to(REPOSITORY_ROOT).parts
    )


def check_local_links(files: list[Path]) -> list[str]:
    findings: list[str] = []
    for file_path in files:
        if file_path.suffix.lower() != ".md":
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for match in MARKDOWN_LINK.finditer(content):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(maxsplit=1)[0].strip("'\"")
            if (
                not target
                or target.startswith(("#", "http://", "https://", "mailto:"))
            ):
                continue
            target = unquote(target.split("#", maxsplit=1)[0])
            resolved = (file_path.parent / target).resolve()
            if not resolved.exists():
                relative = file_path.relative_to(REPOSITORY_ROOT)
                findings.append(f"Broken local link in {relative}: {target}")
    return findings


def main() -> int:
    files = repository_files()
    findings: list[str] = []

    for file_path in files:
        if file_path.name in FORBIDDEN_NAMES:
            findings.append(
                f"Forbidden filename: {file_path.relative_to(REPOSITORY_ROOT)}"
            )

        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PATTERNS.items():
            if pattern.search(content):
                relative = file_path.relative_to(REPOSITORY_ROOT)
                findings.append(f"{name} pattern in {relative}")

    for relative in REQUIRED_FILES:
        if not (REPOSITORY_ROOT / relative).is_file():
            findings.append(f"Required file missing: {relative}")

    result_path = (
        REPOSITORY_ROOT
        / "series/hermes-agent/v0.20.1/labs/02-context-and-compression/"
        "reference-results/windows-2026-08-15/result.json"
    )
    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result.get("lab_id") != "hermes-02-context-compression":
                findings.append("Reference result has an unexpected lab_id.")
            if result.get("contains_credentials") is not False:
                findings.append(
                    "Reference result does not explicitly declare "
                    "contains_credentials=false."
                )
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"Reference result is not valid JSON: {error}")

    part1_result_path = (
        REPOSITORY_ROOT
        / "series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/"
        "reference-results/windows-2026-08-16/result.json"
    )
    if part1_result_path.is_file():
        try:
            part1_result = json.loads(part1_result_path.read_text(encoding="utf-8"))
            if part1_result.get("lab_id") != "hermes-01-session-workspace":
                findings.append("Part 1 reference result has an unexpected lab_id.")
            boundary = part1_result.get("evidence_boundary", {})
            if boundary.get("contains_credentials") is not False:
                findings.append(
                    "Part 1 result does not declare contains_credentials=false."
                )
            if boundary.get("contains_absolute_paths") is not False:
                findings.append(
                    "Part 1 result does not declare contains_absolute_paths=false."
                )
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"Part 1 reference result is not valid JSON: {error}")

    part3_result_path = (
        REPOSITORY_ROOT
        / "series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/"
        "reference-results/windows-2026-08-23/result.json"
    )
    if part3_result_path.is_file():
        try:
            part3_result = json.loads(part3_result_path.read_text(encoding="utf-8"))
            if part3_result.get("lab_id") != "hermes-03-memory-skills-approval":
                findings.append("Part 3 reference result has an unexpected lab_id.")
            boundary = part3_result.get("evidence_boundary", {})
            if boundary.get("contains_credentials") is not False:
                findings.append(
                    "Part 3 result does not declare contains_credentials=false."
                )
            if boundary.get("contains_absolute_paths") is not False:
                findings.append(
                    "Part 3 result does not declare contains_absolute_paths=false."
                )
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"Part 3 reference result is not valid JSON: {error}")

    findings.extend(check_local_links(files))

    if findings:
        for finding in sorted(set(findings)):
            print(f"ERROR: {finding}", file=sys.stderr)
        print(
            f"Repository safety validation failed with {len(set(findings))} "
            "finding(s).",
            file=sys.stderr,
        )
        return 1

    print(
        f"PASS: scanned {len(files)} repository files; no forbidden state, "
        "credential patterns, or broken local links found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
