#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
default_root="$(cd "$script_dir/.." && pwd -P)/fixtures"
root="${1:-$default_root}"

if [[ ! -d "$root" ]]; then
  printf 'Fixture root not found: %s\n' "$root" >&2
  exit 1
fi

errors=0

require_marker() {
  local file="$1"
  local marker="$2"

  if [[ ! -f "$file" ]]; then
    printf 'Missing fixture: %s\n' "$file" >&2
    errors=$((errors + 1))
  elif ! grep -Fq "$marker" "$file"; then
    printf 'Missing marker %s in %s\n' "$marker" "$file" >&2
    errors=$((errors + 1))
  fi
}

require_marker "$root/workspace/AGENTS.md" "CEDAR"
require_marker "$root/workspace/backend/AGENTS.md" "EMBER"
require_marker "$root/workspace/backend/probe.txt" "probe"
require_marker "$root/profile/SOUL.md" "ORBIT"
require_marker "$root/profile/memories/USER.md" "AMBER"
require_marker "$root/profile/memories/MEMORY.md" "JADE"
require_marker "$root/profile/skills/context-probe/SKILL.md" "VIOLET"
require_marker "$root/profile/skills/context-probe/SKILL.md" "INDIGO"

while IFS= read -r forbidden; do
  printf 'Forbidden credential-shaped fixture: %s\n' "$forbidden" >&2
  errors=$((errors + 1))
done < <(
  find "$root" -type f \( \
    -name '.env' -o \
    -name 'auth.json' -o \
    -name 'auth.lock' -o \
    -name 'cookies.json' -o \
    -name 'state.db' \
  \) -print
)

if (( errors > 0 )); then
  printf 'Fixture validation failed with %d error(s).\n' "$errors" >&2
  exit 1
fi

printf 'Fixture validation passed: %s\n' "$root"
