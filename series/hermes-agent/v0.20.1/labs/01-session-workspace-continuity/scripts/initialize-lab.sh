#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [destination]\n' "$0"
  printf 'Creates a disposable Part 1 session/workspace lab.\n'
}

if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then
  usage
  exit 0
fi

if (( $# > 1 )); then
  usage >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
lab_source="$(cd "$script_dir/.." && pwd -P)"
fixtures="$lab_source/fixtures"
home_dir="$(cd "$HOME" && pwd -P)"

if (( $# == 1 )); then
  destination="$1"
  mkdir -p "$destination"
else
  destination="$(mktemp -d "${TMPDIR:-/tmp}/the-agent-stack-hermes-01.XXXXXX")"
fi

destination="$(cd "$destination" && pwd -P)"

case "$destination" in
  /|"$home_dir")
    printf 'Refusing unsafe destination: %s\n' "$destination" >&2
    exit 1
    ;;
esac

if [[ "$destination" == */.hermes || "$destination" == */.hermes/* ]]; then
  printf 'Refusing to use a real Hermes profile path: %s\n' "$destination" >&2
  exit 1
fi

shopt -s nullglob dotglob
destination_entries=("$destination"/*)
shopt -u nullglob dotglob
if (( ${#destination_entries[@]} > 0 )); then
  printf 'Destination must be empty: %s\n' "$destination" >&2
  exit 1
fi

mkdir -p "$destination/profile" "$destination/evidence" "$destination/runs"
cp -R "$fixtures/workspace-a" "$destination/workspace-a"
cp -R "$fixtures/workspace-b" "$destination/workspace-b"

printf 'Disposable Part 1 lab created at:\n  %s\n\n' "$destination"
printf 'Run these commands in this terminal:\n'
printf '  export PART1_LAB_ROOT=%q\n' "$destination"
printf '  export HERMES_HOME=%q\n' "$destination/profile"
printf '  cd %q\n' "$destination/workspace-a"
printf '\nDo not point HERMES_HOME at your real Hermes profile while running the lab.\n'
