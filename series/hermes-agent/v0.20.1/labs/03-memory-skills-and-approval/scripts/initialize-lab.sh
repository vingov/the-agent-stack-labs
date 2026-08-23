#!/usr/bin/env bash
set -euo pipefail

if (( $# > 1 )); then
  printf 'Usage: %s [destination]\n' "$0" >&2
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
  destination="$(mktemp -d "${TMPDIR:-/tmp}/the-agent-stack-hermes-03.XXXXXX")"
fi
destination="$(cd "$destination" && pwd -P)"

case "$destination" in
  /|"$home_dir")
    printf 'Refusing unsafe destination: %s\n' "$destination" >&2
    exit 1
    ;;
esac
if [[ "$destination" == */.hermes || "$destination" == */.hermes/* || "$destination" == */hermes || "$destination" == */hermes/* ]]; then
  printf 'Refusing to use a normal Hermes profile path: %s\n' "$destination" >&2
  exit 1
fi

shopt -s nullglob dotglob
entries=("$destination"/*)
shopt -u nullglob dotglob
if (( ${#entries[@]} > 0 )); then
  printf 'Destination must be empty: %s\n' "$destination" >&2
  exit 1
fi

cp -R "$fixtures/workspace" "$destination/"
cp -R "$fixtures/profile" "$destination/"
mkdir -p "$destination/evidence"

workspace="$destination/workspace/hermes-part3-lab"
profile="$destination/profile"
printf 'Hermes Part 3 lab created safely.\n'
printf 'Lab root: %s\nWorkspace: %s\nProfile: %s\n\n' "$destination" "$workspace" "$profile"
printf 'For a provider-backed Builder run, use these commands in the same shell:\n'
printf '  export HERMES_HOME=%q\n' "$profile"
printf '  cd %q\n\n' "$workspace"
printf 'The Explorer track can run the fixture scripts without Hermes or a provider.\n'
