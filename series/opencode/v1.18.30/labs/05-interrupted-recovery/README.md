# Part 5: The agent stopped. What state did it leave behind?

This lab compares normal completion, graceful session cancellation, and a separately controlled active-server stop at the same partial-write boundary. It runs the real OpenCode v1.18.30 CLI with a local scripted provider. No model inference, provider account, or paid API call is involved.

The task fixes label normalization, then generates a catalogue and its SHA-256 manifest. A deliberately bounded helper pauses between those two writes. Before intervening, the harness independently reads the changed catalogue, the running tool record, retained Windows process handles, and actual saved Git tree/blob bytes.

The normal and graceful cases record the catalogue in a patch; their first message-level revert restores the baseline. After the active server stop, the old catalogue bytes still exist in a snapshot, but the surviving patch selects only the source file. Revert restores the source and leaves the changed catalogue behind. **A saved version and membership in the selected recovery operation are separate requirements.**

| Observation | Normal release | Graceful abort | Active server stop |
| --- | --- | --- | --- |
| Bytes before intervention | Fixed source, new catalogue, old manifest | Same | Same |
| Catalogue path recorded before intervention | No | No | No |
| Old catalogue bytes independently found before intervention | Yes | Yes | Yes |
| Task acceptance before first revert | 6 pass | 5 pass; manifest mismatch | 5 pass; manifest mismatch |
| Catalogue path recorded after intervention/restart | Yes | Yes | No |
| First revert restores exact baseline | Yes | Yes | No: catalogue remains new |
| Unrevert restores pre-undo bytes | Yes, complete task | Yes, incomplete task | Yes, incomplete task |

Learn to distinguish process lifetime from stored tool status, saved content from selected restore paths, and restoration from task acceptance. The [claim matrix](claims.md) connects each claim to the evidence and its limits. The [reference notes](reference/README.md) explain the exact capture and named tests. The [earlier completed-edit recovery lab](../05-snapshots-recovery/README.md) is retained as a different experiment.

The [article figures](assets/README.md) show the two inputs to recovery and the observed forced-stop sequence, with editable Mermaid, PNG, and SVG copies.

## Check the supplied evidence

Requires Python 3.12+; fixture/harness tests also require Node.js 24 on PATH. From the repository root:

```sh
python series/opencode/v1.18.30/labs/05-interrupted-recovery/scripts/check_receipt.py
python series/opencode/v1.18.30/labs/05-interrupted-recovery/scripts/test_lab.py
```

Use `python3` if that is your command. The checker reconstructs fixture bytes from their hashes, validates actual Git tree/blob contents, independently derives the named acceptance outcomes, and checks restore selection, lifecycle ordering, provider counts, and required provenance entries. The tests include 33 contradictory public-receipt mutations, helper release/stop/deadline cases, command timeouts, and a Windows-only retained-handle check. These portable checks do not run OpenCode or authenticate the historical execution. The live runtime experiment has been exercised on Windows x64 only.

## Collect a fresh private run on Windows

Requires Windows x64, Python 3.12+, Node.js 24, PowerShell 7 (`pwsh`), Git, and the official [OpenCode v1.18.30 Windows x64 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30). Extract `opencode-windows-x64.zip` into a local tools directory. The runner checks the executable digest before launch. It does not install software or read provider credentials.

```powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
Set-Location the-agent-stack-labs
$lab = 'series/opencode/v1.18.30/labs/05-interrupted-recovery'
$captureRoot = Join-Path $env:USERPROFILE 'oc5r'
python "$lab/scripts/run_lab.py" --opencode 'C:\tools\opencode-v1.18.30\opencode.exe' --output $captureRoot
```

Use a short private output root outside the clone. Long Windows paths can break the runtime's snapshot Git directory; the runner rejects paths beyond its conservative limit. It prints a unique `Private capture: ...` path. Substitute that exact path below:

```powershell
$capture = 'C:\path\printed-by-the-runner\interruption-...'
python "$lab/scripts/verify_run.py" $capture --output (Join-Path $capture 'receipt.json')
python "$lab/scripts/negative_controls.py" $capture
```

The default run captures normal and graceful cases. The verifier should confirm both; 26 deliberately contradictory raw-capture controls must be rejected. A collection message says only that observations were retained. It does not declare them verified.

After validating that pair, the additional comparison is available:

```powershell
python "$lab/scripts/run_lab.py" --opencode 'C:\tools\opencode-v1.18.30\opencode.exe' --output $captureRoot --include-forced-stop
```

This creates a new run containing all three cases. Use its newly printed path with the same verifier and negative-control commands. The forced case is admitted only if the catalogue has changed, its old bytes have actually been captured from a snapshot, and its path is not yet in a patch at the barrier. The harness terminates only its owned OpenCode server handle, observes the generator before cleanup, then stops that helper separately. It is an active-process termination experiment, not a power-loss durability test.

Each case uses a fresh Git fixture and home/config/data/cache/state/temp directories, an isolated environment, loopback servers, `serve --pure`, and `run --attach --session`. The built-in `bash` compatibility tool executes the configured PowerShell command. Application-profile isolation is not an operating-system sandbox. The provider prescribes choices; it does not simulate tool effects.

**Keep the entire capture directory private.** It contains absolute local paths, provider request bodies, system prompts, and synthetic session databases. Publish only a reviewed sanitized receipt, never the raw directory. Failed runs are retained. The runner never restores files by hand to make a result pass.

## Read the recovery evidence

The source fix is a completed operation before the generator starts. The helper writes the catalogue, announces readiness outside the snapshot workspace, and waits before its manifest write. Its control files and stop behavior belong to the fixture. They are not OpenCode features.

After graceful abort returned, a retained-handle query still found the generator alive. Later queries observed its exit before harness cleanup. The subsequent tool record was `error` with `Tool execution aborted`. That combination supports a specific ordering observation; it is not a universal cancellation latency guarantee.

After active server termination, the Node generator survived through the primary observation. The harness stopped it explicitly; its exit code 75 identifies that fixture cleanup path. Same-profile restart retained a `running` tool part and no live status entry for the session. The stored part did not mean the generator was still running after cleanup.

First revert targets the sole original user message. The raw verifier derives the earliest selected saved reference for each recorded patch path, reconstructs those blobs, and compares the actual restored files. Unrevert uses the actual pre-undo snapshot, so it can restore an incomplete task just as faithfully as a complete one. No provider request occurs during these recovery operations.

The six fixed tests check interior spaces, outer whitespace, all-whitespace input, empty input, intended catalogue values, and manifest agreement with actual bytes. The baseline and the forced-case first revert both have three passes and three failures, but different tests fail. A matching total is not evidence of matching state.

## Change one thing

Predict the result if the generator is released and allowed to finish before the server is stopped. In a separate experimental copy, move the stop boundary after independently confirming the tool's terminal record and the catalogue/manifest patch membership. Preserve the original reference. Compare actual coverage and file bytes; do not edit expected outcomes to hide a missing record. This tests the recording boundary, not whether the original partial-write fixture is a transactional generator.

## Troubleshooting and scope

- A digest mismatch means the executable does not match the recorded official release. Obtain the named binary instead of bypassing the check.
- A long-path rejection or snapshot error requires a shorter output root and a new run. An earlier development pilot was excluded because Git reported `$GIT_DIR too big` even in the normal control.
- A barrier failure, missing tree, failed API call, timeout, or process-query error makes that run inconclusive. Inspect the retained `collection-error.json`, `server-1.stderr`, relevant operation captures, and `cleanup.json`; preserve the failure.
- Commands, HTTP reads, the generator, and case collection have bounded deadlines. A timed-out command retains stdout/stderr and explicit failure metadata. Only owned process handles and a nonce-bound helper stop marker are used for cleanup.
- Windows process queries use retained handles, creation time, image identity, `WaitForSingleObject`, and `GetProcessTimes`. A failed wait cannot be counted as exit. The observation covers these specific processes, not every possible detached descendant.

No live model choices, concurrent unrelated writer, external service, TUI interruption, provider-consuming continuation, arbitrary daemon family, machine crash, power failure, or exactly-once guarantee was tested. Source-defined continuation behavior is separate from observed recovery. Source pins and capture provenance are in the [reference notes](reference/README.md).
