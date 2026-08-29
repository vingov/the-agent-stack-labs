#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lab_root="$(cd -- "$script_dir/.." && pwd)"
fixture_root="$lab_root/fixtures/workspace"
destination="${1:-${TMPDIR:-/tmp}/hermes-part4-lab-$(date +%s)-$$}"

if [[ -d "$destination" ]] && [[ -n "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  printf 'Destination must be new or empty: %s\n' "$destination" >&2
  exit 1
fi

mkdir -p "$destination"
cp -R "$fixture_root"/. "$destination"/
mkdir -p "$destination/bin"
cp "$script_dir/run_contract.py" "$destination/bin/run_contract.py"
cp "$script_dir/verify_operation.py" "$destination/bin/verify_operation.py"
cp "$script_dir/seed_goal.py" "$destination/bin/seed_goal.py"
cp "$script_dir/render_commands.py" "$destination/bin/render_commands.py"
printf '%s\n' "$(cd -- "$destination" && pwd)"
