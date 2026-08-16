#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s ROOT [OUTPUT]\n' "$0"
  printf 'Writes a deterministic SHA-256 manifest for files below ROOT.\n'
}

if (( $# < 1 || $# > 2 )); then
  usage >&2
  exit 2
fi

root="$1"
output="${2:-$root/SHA256SUMS.txt}"

if [[ ! -d "$root" ]]; then
  printf 'Root directory not found: %s\n' "$root" >&2
  exit 1
fi

root="$(cd "$root" && pwd -P)"
home_dir="$(cd "$HOME" && pwd -P)"

case "$root" in
  /|"$home_dir")
    printf 'Refusing unsafe root: %s\n' "$root" >&2
    exit 1
    ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
  hash_file() {
    sha256sum "$1" | awk '{print $1}'
  }
elif command -v shasum >/dev/null 2>&1; then
  hash_file() {
    shasum -a 256 "$1" | awk '{print $1}'
  }
else
  printf 'Install sha256sum (Linux) or shasum (macOS) to create a manifest.\n' >&2
  exit 1
fi

output_dir="$(dirname "$output")"
mkdir -p "$output_dir"
output="$(cd "$output_dir" && pwd -P)/$(basename "$output")"
temporary="$(mktemp "${TMPDIR:-/tmp}/the-agent-stack-sha256.XXXXXX")"
trap 'rm -f "$temporary"' EXIT

output_relative=""
case "$output" in
  "$root"/*)
    output_relative="${output#"$root"/}"
    ;;
esac

: > "$temporary"
while IFS= read -r relative; do
  if [[ -n "$output_relative" && "$relative" == "$output_relative" ]]; then
    continue
  fi
  digest="$(hash_file "$root/$relative")"
  printf '%s\t%s\n' "$digest" "$relative" >> "$temporary"
done < <(
  cd "$root"
  find . -type f -print |
    sed 's#^\./##' |
    LC_ALL=C sort
)

mv "$temporary" "$output"
trap - EXIT
printf 'SHA-256 manifest written to: %s\n' "$output"
