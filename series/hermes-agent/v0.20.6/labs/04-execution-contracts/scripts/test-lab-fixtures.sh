#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fixture_root="${1:-$(cd -- "$script_dir/../fixtures/workspace" && pwd)}"
artifact="$fixture_root/input/artifact.txt"
policy="$fixture_root/policy/policy-v2.json"
procedure="$fixture_root/procedures/HERMES-P4-PROCEDURE-V2.md"

for required in "$artifact" "$policy" "$procedure"; do
  [[ -f "$required" ]] || { printf 'Missing fixture: %s\n' "$required" >&2; exit 1; }
done

[[ "$(wc -c < "$artifact" | tr -d ' ')" == "91" ]] || {
  printf 'artifact.txt must remain exactly 91 bytes.\n' >&2
  exit 1
}

python3 - "$artifact" "$policy" <<'PY'
import hashlib, json, pathlib, sys
artifact = pathlib.Path(sys.argv[1])
policy = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
assert policy["required_sha256"] == actual, (policy["required_sha256"], actual)
assert policy["required_procedure"] == "HERMES-P4-PROCEDURE-V2"
assert policy["allowed_output"] == "state/deployed/artifact.txt"
PY

python3 -m py_compile "$script_dir/run_contract.py" "$script_dir/run_controls.py" "$script_dir/verify_operation.py" "$script_dir/seed_goal.py" "$script_dir/render_commands.py" "$script_dir/run_plugin_probe.py"
printf 'Part 4 fixtures: PASS\n'
