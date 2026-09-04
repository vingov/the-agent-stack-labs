# Builder: run the real Hermes terminal boundary

Use a disposable profile and synthetic targets. Run commands from the repository root. These instructions use Git, Python 3.11, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Docker with Linux containers. Native Windows also needs Git Bash, which Hermes uses for local terminal commands.

## 1. Install the recorded release separately

```text
git clone --depth 1 --branch v2026.8.31 https://github.com/NousResearch/hermes-agent.git runs/part5/hermes-source
uv sync --project runs/part5/hermes-source --frozen --extra dev --extra mcp --python 3.11
docker pull python@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534
```

If that clone directory already exists, verify it instead of overwriting it. The runner requires commit `29112bef099274229cadff79cdff7bf7b99c4b77` and rejects tracked source changes. The release contains case-colliding contributor-email metadata on Windows; only that non-code directory is excluded from the dirty-source check.

The reference used the release lockfile in a fresh virtual environment. `uv run` below selects that project's dependencies without modifying an existing Hermes installation.

## 2. Create a new lab

```text
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/initialize_lab.py --destination runs/part5/my-run
```

The initializer refuses an existing destination. It creates a profile, workspace, sibling directory, random harmless markers and a SHA-256 manifest. It does not copy credentials or an existing profile. Keep all generated runs under the ignored `runs/` directory.

## 3. Run three actual tool paths without a model

```text
uv run --project runs/part5/hermes-source --frozen --extra dev --extra mcp python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/run_boundary.py --source runs/part5/hermes-source --lab runs/part5/my-run --backend local --attempt local-tool
uv run --project runs/part5/hermes-source --frozen --extra dev --extra mcp python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/run_boundary.py --source runs/part5/hermes-source --lab runs/part5/my-run --backend docker --attempt docker-tool
uv run --project runs/part5/hermes-source --frozen --extra dev --extra mcp python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/run_boundary.py --source runs/part5/hermes-source --lab runs/part5/my-run --backend docker --attempt mounted-tool --expose-outside
```

Run sequentially: each process configures the same disposable profile. Expect both markers, then inside only, then both markers again. These commands call the real release's `terminal_tool`; there is no provider or model in this step.

The Docker configuration uses a non-root user, network mode `none`, dropped capabilities, `no-new-privileges`, an explicit workspace mount and session-scoped cleanup. The runner also inspects Hermes's additional profile mounts. Only the third case adds the synthetic outside directory read-only. No Docker socket is mounted.

## 4. Optional: put a model in the loop

Authenticate the **disposable** profile through your provider's normal Hermes login flow. Set `HERMES_HOME` to the absolute `runs/part5/my-run/profile` path before authentication. From the isolated release environment, run `hermes model` and select OpenAI Codex; this is the provider setup wizard and can run OAuth. Check the [official CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-model) for provider-specific setup. Other providers can use `--provider` and `--model`.

Repeat the three commands above with new attempt names and add `--live`. For example, change `--attempt local-tool` to `--attempt local-agent --live`.

The agent receives one explicit request to run the probe, with only the terminal toolset enabled and at most six iterations. It must not search for unavailable markers or change configuration. The host retains the provider connection; Docker runs the probe. The probe command and output filename vary by attempt, while its bytes and logical read targets stay fixed.

## 5. Read the result

Each attempt writes a public-shaped receipt under `my-run/receipts/` and the probe writes its target receipt under `workspace/`. The host checks the manifest against returned hashes and verifies the original files are unchanged. Live attempts additionally retain a private conversation for local debugging. **Never copy `*-private.json`, diagnostics, authentication or the full profile into a public result.**

The supplied offline verifier expects the three final live reference filenames. Fresh direct-tool runs use their own host verifier inside `run_boundary.py`; a direct-tool receipt must not be relabeled as a live-model receipt.

## Troubleshooting and recovery

| Symptom | Inspect | Next step |
| --- | --- | --- |
| Docker unavailable | `docker info` and Linux-container mode | Start Docker; use a new attempt name |
| Inside marker unreadable | Mount mapping, UID and host directory permissions | Correct only the disposable directory's permissions; retain the failed receipt |
| Outside unexpectedly readable | Actual `containers[].mounts` | Remove unintended exposure and rerun with a new attempt |
| Provider unavailable | Disposable profile's authentication | Authenticate that profile; direct-tool runs remain available |
| Source revision or dirty check fails | Clone revision and tracked changes | Use a separate clean release clone |
| Cleanup check fails | Docker status for the recorded run | Inspect the specific lab container; never use a blanket Docker prune |

On POSIX hosts, the initializer gives the new lab root mode `0700` and the synthetic workspace `0777` so the container UID can create a receipt through its bind mount. The private parent prevents other host users from traversing that workspace. Bind-mount access still varies across platforms. The recorded live run is Windows-hosted; a different OS result is valuable evidence to report, not something to hide by weakening the checks.

## Challenge

Predict the third result before adding `--expose-outside`. Then explain why a read-only mount still grants read authority. Continue with [Investigator](investigator.md) to examine approval and extension boundaries.
