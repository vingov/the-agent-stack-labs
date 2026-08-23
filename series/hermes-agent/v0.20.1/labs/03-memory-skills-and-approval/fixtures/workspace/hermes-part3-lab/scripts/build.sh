#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
artifact="$root/artifacts/site.bundle"
temporary="$artifact.tmp"
mkdir -p "$root/artifacts"
{
  printf 'HERMES-P3-SKILL-LOCAL-DEPLOY-V1\n'
  printf 'path=app/index.html\n'
  LC_ALL=C sed 's/[[:space:]]*$//' "$root/app/index.html" |
    awk '{ line[NR]=$0 } END { last=NR; while (last > 0 && line[last] == "") last--; for (i=1; i<=last; i++) print line[i] }'
} > "$temporary"
mv "$temporary" "$artifact"

if command -v sha256sum >/dev/null 2>&1; then
  digest="$(sha256sum "$artifact" | awk '{print $1}')"
else
  digest="$(shasum -a 256 "$artifact" | awk '{print $1}')"
fi
printf '%s\n' "$digest" > "$root/artifacts/site.bundle.sha256"
printf 'artifact=%s\nsha256=%s\n' "$artifact" "$digest"
