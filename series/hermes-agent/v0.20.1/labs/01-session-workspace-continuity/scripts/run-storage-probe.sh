#!/usr/bin/env bash
set -euo pipefail

lab_root="${1:-${PART1_LAB_ROOT:-}}"
hermes_source="${2:-}"

if [[ -z "$lab_root" ]]; then
  printf 'Set PART1_LAB_ROOT or pass the disposable lab path.\n' >&2
  exit 2
fi

if [[ -z "$hermes_source" ]]; then
  version_text="$(hermes version)"
  hermes_source="$(printf '%s\n' "$version_text" | sed -n 's/^Install directory:[[:space:]]*//p' | head -n 1)"
fi

if [[ -z "$hermes_source" || ! -d "$hermes_source" ]]; then
  printf 'Could not locate the active Hermes source directory.\n' >&2
  exit 1
fi

python_path=""
for candidate in \
  "$hermes_source/venv/bin/python" \
  "$hermes_source/.venv/bin/python" \
  "$hermes_source/venv/Scripts/python.exe" \
  "$hermes_source/.venv/Scripts/python.exe"; do
  if [[ -x "$candidate" ]]; then
    python_path="$candidate"
    break
  fi
done

if [[ -z "$python_path" ]]; then
  printf 'Could not locate the Python environment for the active Hermes install.\n' >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
output="$lab_root/evidence/storage-result.json"

"$python_path" "$script_dir/run-storage-probe.py" \
  --lab-root "$lab_root" \
  --hermes-source "$hermes_source" \
  --output "$output"

printf 'Sanitized result written to: %s\n' "$output"
