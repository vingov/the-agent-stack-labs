# Subagents and shared work

A child session is not a private checkout. This lab follows one real OpenCode task from a parent conversation to a fresh child, an edit of shared files, and a selected report back to the parent.

The central question is observable: **has the shared file already changed before the child returns its report?** The local provider pauses at that boundary so a separate reader can inspect the file.

## Start here

Clone this repository, then run the portable checks from its root. Python 3.12 or newer is sufficient. These commands inspect the supplied receipt and exercise rejection controls. They do not run OpenCode or call a model.

```sh
git clone https://github.com/vingov/the-agent-stack-labs.git
cd the-agent-stack-labs
python series/opencode/v1.18.30/labs/04-subagents-shared-work/scripts/verify_reference.py
python series/opencode/v1.18.30/labs/04-subagents-shared-work/scripts/test_lab.py
```

On macOS or Linux, use `python3` if needed. Expected result: a consistent receipt and passing tests, including 36 deliberately contradictory receipt controls.

Read the [claim matrix](claims.md) and [reference result](reference-results/windows-2026-10-07/README.md). The [sanitized receipt](reference-results/windows-2026-10-07/receipt.json) contains identities, ordered checkpoints, marker-presence booleans, policies, tool arguments, file digests and test counters. It contains no full provider request bodies or system prompts.

## What the trace demonstrates

The fixture exports `formatLabel`. Initially it returns its input unchanged. The task is to trim outer whitespace while preserving repeated interior spaces. The four fixed tests cover outer whitespace, repeated interior spaces, an already normalized label and empty input.

1. The scripted parent issues a real `task` call to `general`, with no previous task ID.
2. OpenCode creates the child and assembles its provider requests.
3. The child reads the helper and the fixed tests, then edits only the helper.
4. When the provider receives the child's completed edit result, it reads the shared file **before sending any part of the final child report**.
5. OpenCode returns selected child text to the parent. The next parent request is captured before any parent file read.
6. The parent runs the fixed test command through OpenCode's `bash` tool, configured to use PowerShell. The external harness independently repeats the same tests and checks current bytes.

The external provider/harness is a separate Python process. OpenCode owns the real task, child session, prompt assembly, permission evaluation, file tools and parent test invocation. The provider prescribes decisions and text. It does not perform the edit. Its filesystem access after fixture preparation is read-only, apart from writing capture files outside the workspace.

| Checkpoint | Observed reference result |
| --- | --- |
| Initial fixture | Two tests pass and two fail |
| Fresh child identity | Distinct ID, with the stored parent link and matching request headers |
| Child input | Delegated marker present, parent-only marker absent |
| Child read feedback | Helper observation marker present |
| Before child report release | Shared helper already contains `return label.trim();` |
| First parent continuation | Selected child report present, child read marker absent |
| Acceptance | Parent and independent external checks both pass all four unchanged tests |
| Changed files | Only `labels.mjs` |

These are marker observations in this controlled configuration, not confidentiality guarantees. Common instructions, files or plugins could supply information by other paths. The report omits the read marker because the prescribed child summary omits it. This tests how OpenCode handles that controlled return, not what a natural model would choose to report.

## Run the real experiment on Windows

The documented execution path requires Windows x64, Python 3.12+, Node.js 24, Git and PowerShell 7. Use the official [OpenCode v1.18.30 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30). The runner refuses a different executable digest or version.

| Identity | Value |
| --- | --- |
| OpenCode tag | `v1.18.30` |
| Actual source commit | `3104c1428ec91f809e5ab86631300de41eb6952e` |
| Windows x64 executable SHA-256 | `c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea` |

From a fresh checkout, replace the example executable path with the location of the official binary:

```powershell
$lab = 'series/opencode/v1.18.30/labs/04-subagents-shared-work'
$privateOutput = Join-Path ([IO.Path]::GetTempPath()) 'opencode-p4-private'
python "$lab/scripts/run_lab.py" --opencode 'C:\Tools\opencode.exe' --node (Get-Command node).Source --shell (Get-Command pwsh).Source --output $privateOutput
```

The runner prints a unique private capture directory. Use that printed path:

```powershell
$run = 'PASTE_PRINTED_CAPTURE_DIRECTORY'
python "$lab/scripts/verify_run.py" $run --receipt (Join-Path $privateOutput 'verified-receipt.json')
python "$lab/scripts/test_raw_evidence.py" $run
```

Expected result: seven provider requests in the reference run, successful independent reconstruction, an accepted unmodified capture copy, and rejection of 15 corrupted private copies. The raw verifier also compares the captured final provider report with the exported child text and checks normal response completion. Auxiliary requests are classified explicitly if they appear. They are not silently counted as child or parent tool requests.

The runner creates a synthetic Git workspace and fresh home, configuration, data, cache, state and temporary directories. It supplies an environment allowlist and selects only a loopback provider with a synthetic credential. It uses `--pure`, disables sharing, updates, model-list fetching, snapshots, formatters and LSP, and leaves experimental background features unset. There is no paid inference. These controls isolate the experiment's inputs. They are not an OS sandbox.

The parent is allowed to delegate only to `general` and run the exact fixed test command. The child is allowed to read the two fixture files and edit the helper. Its effective edit policy denies changing the test file. The captured configuration, role rules, stored session rules, advertised tools and evaluated operations are checked separately. No ask responder or remembered approval is exercised.

The runner also records its source digest, checkout revision and dirty state. The reference was captured during lab development, so its `lab_dirty` value is true. A later clean-checkout execution is verified separately. Windows command-line handling records literal outer quotes around the initial parent prompt in this binary. The raw verifier checks that actual form. The delegated child prompt is checked exactly without those outer quotes.

## Verification and limits

`verify_run.py` derives the receipt from private provider captures, durable parent and child exports, CLI logs, process results, snapshots and current file bytes. It checks the actual tool outputs against what appears in subsequent provider requests. The barrier record must place the independent file read after edit feedback and before child report release and parent continuation.

`verify_reference.py` recomputes expected fixture digests and checks the receipt's relationships. `test_lab.py` corrupts identities, inputs, outputs, policies, barrier order, file evidence and acceptance results to ensure rejection. `test_raw_evidence.py` corrupts temporary copies of the raw captures. None of these consistency checks independently authenticates a historical execution.

Real CLI coverage is Windows x64. CI on Windows, macOS and Ubuntu runs portable receipt/rejection checks and syntax checks, without OpenCode or a live provider. No upstream OpenCode tests were executed. Resume, cancellation, background work, simultaneous writers, isolation against hostile tools, remembered approval and model quality are outside the experiment.

## Try one change

Add the observation marker to the controlled final child summary in a separate copy of the lab. Predict how the first parent continuation changes. The original verifier should reject that altered contract. Inspect the complete capture, then define a new expected contract rather than weakening the original check to accept either outcome.

## Troubleshooting and cleanup

- A digest mismatch means the binary is not the exact tested artifact. Do not bypass the check to report equivalent results.
- A missing child export, failed tool or incomplete provider request is a failed capture, even if the CLI exit is zero. Preserve it and inspect the private logs.
- A timeout or interrupted run leaves its private directory available for inspection. The local provider closes in the runner's cleanup path. Do not infer that a cancelled edit was reversed.
- Never commit raw request bodies, logs, session databases or absolute home paths. Publish only the verified sanitized receipt.
- After inspection, the uniquely printed private run directory can be removed. It is separate from this repository and any existing OpenCode profile.
