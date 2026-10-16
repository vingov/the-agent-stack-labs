# Part 5: Snapshots, recovery, and patch verification

Does undo remove the agent's contribution, or restore an earlier version of each selected file?

This lab runs the real OpenCode v1.18.30 runtime against a local scripted provider. OpenCode reads and fixes a label helper. An external writer then changes an unrelated note in both cases and an independent value in the helper in only the treatment case. The same first message-level revert is applied to both completed requests, followed by unrevert.

The observed boundary is the whole selected file. In the treatment, undo replaces both the fix and the later independent setting. The unrelated note survives. Unrevert restores the captured pre-undo versions, including that later setting. No provider request occurs during these recovery operations.

| Checkpoint | Formatting tests, both cases | Control setting | Treatment setting | Note, both cases |
| --- | --- | --- | --- | --- |
| Initial | 2 pass, 2 fail | compact | compact | initial |
| Completed OpenCode edit | 4 pass | compact | compact | initial |
| Later external writes | 4 pass | compact | expanded | later |
| First revert | 2 pass, 2 fail | compact | compact | later |
| Unrevert | 4 pass | compact | expanded | later |

A correct restoration can bring back the original bug. File-version checks and behavioral acceptance answer different questions.

## Inspect the evidence without running OpenCode

Requires Python 3.12 or later. From the repository root:

```sh
python series/opencode/v1.18.30/labs/05-snapshots-recovery/scripts/verify_reference.py
python series/opencode/v1.18.30/labs/05-snapshots-recovery/scripts/test_lab.py
```

Use `python3` if that is your Python command. These portable checks validate the sanitized [reference receipt](reference-results/windows-2026-10-16/receipt.json) and reject missing or contradictory fields. They do not execute OpenCode or independently authenticate the historical run. See the [claim matrix](claims.md) for what each result supports.

## Run a fresh experiment on Windows

Requires Windows x64, PowerShell, Python 3.12+, Node.js 24, Git, and the official [OpenCode v1.18.30 Windows x64 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30). Download and extract `opencode-windows-x64.zip` into a local tools directory. The runner rejects an executable whose SHA-256 differs from the recorded official binary. It does not install software or use provider credentials.

The runtime path below was exercised from a fresh local clone. Replace the executable path with your extracted binary. Run from the cloned repository root:

```powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
Set-Location the-agent-stack-labs
$lab = 'series/opencode/v1.18.30/labs/05-snapshots-recovery'
$captureRoot = Join-Path $env:TEMP 'opencode-recovery-captures'
python "$lab/scripts/run_lab.py" --opencode 'C:\tools\opencode-v1.18.30\opencode.exe' --output $captureRoot
```

The runner prints a new `Private capture: ...` directory. Substitute that exact directory below:

```powershell
$capture = 'C:\path\printed-by-the-runner\recovery-...'
python "$lab/scripts/verify_run.py" $capture --include-continuation --receipt (Join-Path $capture 'receipt.json')
python "$lab/scripts/test_raw_evidence.py" $capture
```

Expected results: the verifier confirms both primary cases and the separate continuation; unmodified evidence copies pass and 14 corrupted copies are rejected. The runner prints only that captures exist. It does not declare its own observations verified.

Each run creates fresh Git workspaces, home/config/data/cache/state/temp directories, and loopback servers. Configuration enables snapshots, disables incidental formatting and language servers, and exposes only the bounded file operations needed by the prescribed sequence. It uses `serve --pure` and `run --attach --session` with the ordinary session API. Only its own server process is terminated. Captures are retained for inspection, including failed runs. Application state isolation is not an operating-system sandbox.

Raw captures contain local paths, provider request bodies, system prompts, and synthetic session state. **Keep the entire capture directory private and outside this checkout.** The runner rejects output beneath its checkout. Publish only a reviewed sanitized summary, never the raw directory or database.

## What the verifier connects

The raw checker verifies the selected binary/version, resolved configuration, actual CLI/API route and identities, real tool inputs and feedback, event ordering, complete fixture bytes, unchanged tests, fresh test output, independent setting output, and stored messages/parts. It reconstructs Git tree and blob identities from captured object bytes. A hash-shaped string or enabled setting alone is insufficient.

It then checks that the post-revert helper equals the actual selected earlier blob, the pre-undo tree equals the files just before revert, and unrevert equals those captured versions. The helper alone belongs to the recorded patch paths. Both cases have the same later note edit; only treatment changes the independent helper value.

The separate treatment follow-on starts after the primary comparison has completed. It reverts again after confirming the marker was cleared, then sends a plain message with `noReply: true`. The old five messages disappear from the active stored branch, one new user message appears, the marker clears, files stay at the reverted versions, and no provider request occurs. This is not a provider-backed continuation test or evidence that every historical object was erased. Run `verify_run.py` without `--include-continuation` to check the primary comparison independently. `run_lab.py --skip-continuation` omits that follow-on.

## Version and scope

- Runtime: official Windows x64 OpenCode v1.18.30.
- Actual tag commit: `3104c1428ec91f809e5ab86631300de41eb6952e`.
- Executable SHA-256: `c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea`.
- Evidence class: `OBSERVED_WITH_SCRIPTED_PROVIDER`. The local provider prescribes reads, an edit, and final text. It performs no model inference.
- Tested files: small existing tracked regular files at the repository root. No concurrent writers during recovery, ignored/untracked-file matrix, symlink matrix, filesystem-metadata guarantee, external-service rollback, crash test, or TUI execution.
- Source continuity: recovery, snapshot, prompt, and processor code was compared with v1.19.2 at actual tag commit `7901b7d325c34852caa84fc2c325f3a08dd7a473` on October 16, 2026 UTC. Those files were unchanged. The runtime observation remains v1.18.30.
- Windows ran the actual CLI. macOS/Linux coverage is limited to portable reference checks in CI.

Unrevert's saved-tree restore can touch more than the selected patch paths. This fixture confirms recovery of its captured existing files with no intervening writer; it does not establish an exact inverse for arbitrary filesystem changes. Sending a new message clears the ordinary marker-based recovery route through cleanup. Preserve needed files and records before continuing.

Start with [the recovery service](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/revert.ts), [snapshot operations](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/snapshot/index.ts), and [new-message cleanup](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/prompt.ts#L1051-L1073).
