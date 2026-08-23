#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
default_root="$(cd "$script_dir/.." && pwd -P)/fixtures"
root="${1:-$default_root}"
expected_hash="c611c2a0487875469ec6524cc04b113bf7202d9663fecd8d89b0de5efda29e3b"

if [[ ! -d "$root" ]]; then
  printf 'Fixture root not found: %s\n' "$root" >&2
  exit 1
fi

task="$root/workspace-a/task.txt"
fresh="$root/workspace-b/README.md"

grep -Fq "HERMES-P1-LAB-2026-08-16-SESSION-CWD" "$task"
grep -Fq "HERMES-P1-FRESH-WORKSPACE" "$fresh"

if command -v sha256sum >/dev/null 2>&1; then
  actual_hash="$(sha256sum "$task" | awk '{print $1}')"
else
  actual_hash="$(shasum -a 256 "$task" | awk '{print $1}')"
fi

if [[ "$actual_hash" != "$expected_hash" ]]; then
  printf 'Unexpected task.txt SHA-256: %s\n' "$actual_hash" >&2
  exit 1
fi

if find "$root" -type f \( -name '.env' -o -name 'auth.json' -o -name 'auth.lock' -o -name 'state.db' \) -print | grep -q .; then
  printf 'Credential or live-state shaped file found in fixtures.\n' >&2
  exit 1
fi

printf 'Part 1 fixture validation passed: %s\n' "$root"
