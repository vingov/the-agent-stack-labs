#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
default_root="$(cd "$script_dir/.." && pwd -P)/fixtures"
root="${1:-$default_root}"
workspace="$root/workspace/hermes-part3-lab"

require_marker() {
  local file="$1"
  local marker="$2"
  [[ -f "$file" ]] || { printf 'Missing fixture: %s\n' "$file" >&2; exit 1; }
  grep -Fq "$marker" "$file" || { printf 'Missing marker %s in %s\n' "$marker" "$file" >&2; exit 1; }
}

require_marker "$root/profile/SOUL.md" 'HERMES-P3-SOUL-ISOLATED'
require_marker "$root/profile/config.yaml" 'write_approval: true'
require_marker "$workspace/app/index.html" 'HERMES-P3-SKILL-LOCAL-DEPLOY-V1'
require_marker "$workspace/scripts/deploy-local.sh" 'network_used'

for forbidden in .env auth.json auth.lock cookies.json state.db; do
  if find "$root" -type f -name "$forbidden" -print -quit | grep -q .; then
    printf 'Forbidden fixture file found: %s\n' "$forbidden" >&2
    exit 1
  fi
done

temporary_root="$(mktemp -d "${TMPDIR:-/tmp}/the-agent-stack-hermes-03-test.XXXXXX")"
trap 'rm -rf "$temporary_root"' EXIT
cp -R "$workspace/." "$temporary_root/"

bash "$temporary_root/scripts/test.sh"
bash "$temporary_root/scripts/build.sh"
bash "$temporary_root/scripts/deploy-local.sh" --region eu-west-2 --run-id P3-CI-0001 --dry-run
bash "$temporary_root/scripts/deploy-local.sh" --region eu-west-2 --run-id P3-CI-0001
bash "$temporary_root/scripts/verify.sh" P3-CI-0001

printf 'PASS: fixture checks and the network-free Bash workflow completed.\n'
