#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
region=""
run_id=""
dry_run=0

while (( $# )); do
  case "$1" in
    --region) region="${2:?missing region}"; shift 2 ;;
    --run-id) run_id="${2:?missing run id}"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

[[ "$region" == "eu-west-2" ]] || { printf 'Region must be eu-west-2.\n' >&2; exit 3; }
[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || { printf 'Invalid or missing run ID.\n' >&2; exit 4; }

artifact="$root/artifacts/site.bundle"
digest_file="$root/artifacts/site.bundle.sha256"
[[ -f "$artifact" && -f "$digest_file" ]] || { printf 'Build the artifact first.\n' >&2; exit 5; }
expected="$(cat "$digest_file")"
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$artifact" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$artifact" | awk '{print $1}')"
fi
[[ "$expected" == "$actual" ]] || { printf 'Artifact digest mismatch.\n' >&2; exit 6; }

mkdir -p "$root/receipts"
mode="deploy"
deployed=false
if (( dry_run == 1 )); then
  mode="dry-run"
else
  [[ -f "$root/receipts/$run_id.dry-run.json" ]] || { printf 'A matching dry-run receipt is required before deployment.\n' >&2; exit 7; }
  mkdir -p "$root/staging/$region"
  cp "$artifact" "$root/staging/$region/site.bundle"
  cp "$digest_file" "$root/staging/$region/site.bundle.sha256"
  deployed=true
fi

python3 - "$root/receipts/$run_id.$mode.json" "$region" "$actual" "$dry_run" "$deployed" "$run_id" <<'PY'
import json
import sys

path, region, digest, dry, deployed, run_id = sys.argv[1:]
receipt = {
    "marker": "HERMES-P3-SKILL-LOCAL-DEPLOY-V1",
    "fact_marker": "HERMES-P3-FACT-EU-WEST-2",
    "preference_marker": "HERMES-P3-PREF-DRY-RUN-FIRST",
    "region": region,
    "artifact_sha256": digest,
    "dry_run": dry == "1",
    "deployed": deployed == "true",
    "run_id": run_id,
    "network_used": False,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(receipt, handle, sort_keys=True, indent=2)
    handle.write("\n")
PY
printf 'receipt=%s\n' "$root/receipts/$run_id.$mode.json"
