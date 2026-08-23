#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
run_id="${1:?usage: verify.sh RUN_ID}"
region="eu-west-2"
artifact="$root/artifacts/site.bundle"
staged="$root/staging/$region/site.bundle"
expected="$(cat "$root/artifacts/site.bundle.sha256")"

digest() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

[[ "$(digest "$artifact")" == "$expected" ]]
[[ "$(digest "$staged")" == "$expected" ]]

python3 - "$root/receipts/$run_id.dry-run.json" "$root/receipts/$run_id.deploy.json" "$expected" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    dry = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    deploy = json.load(handle)
for receipt in (dry, deploy):
    assert receipt["marker"] == "HERMES-P3-SKILL-LOCAL-DEPLOY-V1"
    assert receipt["region"] == "eu-west-2"
    assert receipt["artifact_sha256"] == sys.argv[3]
    assert receipt["network_used"] is False
assert dry["dry_run"] is True and dry["deployed"] is False
assert deploy["dry_run"] is False and deploy["deployed"] is True
PY

printf 'verification: pass\nsha256=%s\n' "$expected"
