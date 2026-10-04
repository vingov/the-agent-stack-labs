# Part 3: Tool execution and permission boundaries

**Question:** What changes between proposing an edit, asking for approval, and actually writing the file?

This lab sends the same valid `read` and `edit` calls to the real OpenCode CLI in four fresh cases. A local scripted provider supplies the calls over HTTP. No model inference or paid provider is used.

| Target edit policy | CLI mode | Recorded decision path | Target bytes | Independent tests |
| --- | --- | --- | --- | --- |
| allow | ordinary noninteractive | evaluated allow; edit completed | intended replacement | 3/3 pass |
| ask | ordinary noninteractive | evaluated ask; pending request; CLI auto-rejection warning; edit error | unchanged | 1/3 pass |
| ask | `--auto` | evaluated ask; pending request; edit completed | intended replacement | 3/3 pass |
| deny | `--auto` | evaluated deny; edit error | unchanged | 1/3 pass |

The `edit` schema remained advertised in every case. All cases started with the same broken function and the same fixed tests (one passing, two failing). The test file stayed unchanged. All four CLI processes exited zero; the table uses file bytes and independent tests to determine the effect.

The ordinary ask case made two provider requests and stopped after rejection. The other cases made three; the final request included the edit result or denial. These are recorded counts for this controlled sequence, not a general rule for every client or failure.

The logs directly capture permission evaluations and pending requests. The ordinary case also captures the auto-rejection warning. **The stock capture does not contain a complete permission-reply event payload.** The interpretation that auto mode replies `once` comes from the [CLI handler](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/cli/cmd/run.ts#L801-L821), combined with the invocation and outcome. No person approved an operation in these runs.

## Inspect the recorded evidence

From the repository root, with Python 3.12 or later:

```text
python series/opencode/v1.18.30/labs/03-tool-permission-boundaries/scripts/verify_reference.py
python series/opencode/v1.18.30/labs/03-tool-permission-boundaries/scripts/test_lab.py
```

Use `python3` where appropriate. These commands work on Windows, macOS and Linux. They check the [sanitized receipt](reference-results/windows-2026-10-04/receipt.json), bind its hashes to the checked-in fixtures, and exercise 36 missing/contradictory evidence controls. They do **not** execute OpenCode or independently authenticate the recorded run.

Continue with the [claim matrix](claims.md) for the distinction between observations, source analysis and untested behavior.

## Reproduce with the actual CLI

The documented fresh runtime path is **Windows x64**, using Python 3.12+, Node.js, Git and PowerShell 7. The reference used Python 3.12.14 and Node v24.19.0. No global OpenCode installation, authentication or paid provider is required. Portable CI checks only the recorded evidence and rejection controls; it does not establish macOS or Linux runtime behavior.

Obtain `opencode-windows-x64.zip` from the [official v1.18.30 release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30), verify its digest, and extract it to a location you choose:

- ZIP SHA256: `c8c0e0d05ac3dac544a0edfad8de9eb244bf46c6c7a131c38619d40fcf31bd1f`
- Extracted `opencode.exe` SHA256: `c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea`
- Actual tag commit: `3104c1428ec91f809e5ab86631300de41eb6952e`

The runner checks the executable digest before invoking it, then checks `--version`. It deliberately rejects a different release or build. Review version drift separately rather than changing the pin until a test passes.

In PowerShell, starting with a fresh checkout:

```powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
Set-Location the-agent-stack-labs
$lab = 'series/opencode/v1.18.30/labs/03-tool-permission-boundaries'
$cli = (Resolve-Path 'path/to/extracted/opencode.exe').Path
$runParent = Join-Path $env:TEMP 'opencode-permission-lab'
python "$lab/scripts/run_lab.py" --opencode $cli --node (Get-Command node).Source --shell (Get-Command pwsh).Source --output $runParent
```

Replace the executable path with the file you extracted. The runner prints a unique private run directory. Use that printed directory in the next commands:

```powershell
$run = 'path/to/printed/permissions-directory'
python "$lab/scripts/verify_run.py" $run --receipt (Join-Path $run 'receipt.json')
python "$lab/scripts/test_raw_evidence.py" $run
```

A passing run reports agreement among captured provider requests, permission logs, exported tool records, snapshots of actual bytes, and independent fixed tests. The second command tests nine alterations to private evidence copies and confirms the original still verifies. Neither command reruns OpenCode.

## What is controlled

Every case creates a new process, session, Git-rooted synthetic workspace and separate configuration/data/cache/state/home/temp directories. The child environment uses an explicit allowlist; provider credentials and ambient `OPENCODE_PERMISSION` are not inherited. The effective configuration and build-agent policy are captured before the task. Session permissions are checked from the export.

The provider proposes a read and this exact edit:

```json
{
  "filePath": "slug.mjs",
  "oldString": ".replaceAll(' ', '-')",
  "newString": ".replace(/\\s+/g, '-')"
}
```

The edit rule is `{"*":"deny","slug.mjs":"allow"}`, with only its target action changed to `ask` or `deny` for the relevant cases. Keeping the final rule target-specific prevents the blanket-tool filtering branch from removing the schema. Captures verify visibility rather than assuming it. The read rule permits only the fixture target. Other general capabilities are denied.

Comparisons have separate jobs: allow versus ordinary ask changes the target rule; ordinary ask versus auto ask changes the client mode; auto ask versus auto deny changes the target rule under the same mode. Formatting, LSP and snapshots are disabled. Pure mode filters external plugins; it is not relied upon as proof of clean configuration or OS isolation.

The shell is explicitly configured and its initialization logged, but **OpenCode invokes only `read` and `edit` in this lab**. Node acceptance checks are launched independently by the Python runner. This lab does not execute a model-proposed shell command.

## Evidence and limits

- The real runtime uses the AI SDK adapter, confirmed in its logs, and a provider endpoint bound to loopback. Provider decisions and reported token counts are synthetic.
- Permission evaluation, request creation, tool outcome, process exit and file effect are separate evidence fields. No stored `passed: true` flag is accepted as proof.
- Before/after manifests cover the two top-level fixture files. They do not prove an absence of all application or host side effects.
- No autonomous model behavior, human approval click, remembered `always` grant, concurrency race, formatter effect, shell mutation or sandbox property was tested.
- Isolated application state is test hygiene. The process still runs with the host user's authority. The project itself documents [no sandbox](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/SECURITY.md).
- The provider uses no external inference. This does not certify that every OpenCode setup or metadata operation is network-free.

Raw captures remain outside the checkout: provider bodies, full logs, session exports and application state can contain local paths. Publish only a reviewed sanitized receipt. The scripts neither upload raw data nor delete the run directory. After inspection, you may remove the exact disposable run directory that the runner printed.

## Try changing one boundary

On a separate disposable run, replace the final target-specific denial with a catch-all `edit: "deny"`. Predict whether `edit` remains advertised before issuing the same scripted proposal. Inspect the captured schema and error before calling the result a permission-gate denial. The reference verifier should reject this altered comparison because it exercises a different boundary.

## Troubleshooting

If a positive case fails, inspect the private CLI log and exported tool input before changing policy. An invalid replacement, missing schema or wrong runtime is not evidence that the intended permission gate refused the edit. If the runner times out or an export is missing, retain the incomplete capture for diagnosis; the checker must fail. Never manufacture the absent record.

If a receipt fails after a fixture edit, restore or explain the fixture change. The checker intentionally binds acceptance to the same unchanged tests and initial source. If policy logs differ, inspect resolved configuration and agent rules for overrides. Do not disable managed host policy to make the lab pass.
