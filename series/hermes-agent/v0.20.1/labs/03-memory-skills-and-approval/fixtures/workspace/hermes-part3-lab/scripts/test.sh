#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
page="$root/app/index.html"

test -f "$page"
grep -Fq 'HERMES-P3-SKILL-LOCAL-DEPLOY-V1' "$page"
grep -Fq '<!doctype html>' "$page"
if grep -Eiq '(https?://|curl |wget |ssh |scp )' "$page"; then
  printf 'Unexpected network-shaped content.\n' >&2
  exit 1
fi

printf 'tests: pass\n'
