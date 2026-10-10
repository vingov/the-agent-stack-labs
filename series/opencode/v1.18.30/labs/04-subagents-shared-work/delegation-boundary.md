# What crosses the delegation boundary?

Can a coordinator denied an edit delegate that same edit to a permitted worker? In this controlled OpenCode v1.18.30 experiment, yes, when the restriction belongs to the coordinator's role and dispatch to the worker is permitted. Move the target deny into the parent session and it reaches a fresh worker session. The location of the rule changes its scope.

This is a configured division of authority, not a claim of privilege escalation or a built-in Plan-mode bypass. OpenCode's built-in Plan role explicitly denies the General task target. The lab uses custom `coordinator` and `worker` roles.

## Results

The edit is always `return label;` to `return label.trim();` in `labels.mjs`. All cases start with the same two fixture files and four fixed tests, fresh application state and an empty conversation. The coordinator and worker have explicit read permissions for the fixture. A default deny and a final target-specific rule keep the relevant tool advertised while making the target decision observable.

| Case | Location of target restriction | Actual outcome | Child sessions | Changed files | Fixed checks after |
| --- | --- | --- | --- | --- | --- |
| `allowed` | No target deny | Worker edit allowed | 1 | Helper only | 4 pass |
| `parent-role-direct` | Coordinator role | Direct coordinator edit denied | 0 | None | 2 pass, 2 fail |
| `parent-role` | Same coordinator role | Dispatch and worker edit allowed | 1 | Helper only | 4 pass |
| `parent-session` | Parent session | Dispatch allowed, worker edit denied | 1 | None | 2 pass, 2 fail |
| `worker-role` | Worker role | Dispatch allowed, worker edit denied | 1 | None | 2 pass, 2 fail |
| `dispatch` | Coordinator's task-to-worker rule | Delegation denied before child creation | 0 | None | 2 pass, 2 fail |

The direct and delegated coordinator cases use identical role policies. The fixed tests initially report two passes and two failures in every case. Their bytes remain unchanged. Failure of the desired edit in a deny control is the expected observation, not an unsuccessful experiment.

In each created child, captured provider input contains the supplied handoff marker and omits a parent-only conversation marker. The child reads a third marker from the helper. Its prescribed final report omits that marker, and the first parent continuation receives the selected report without the child read history. This establishes a bounded input and return path, not confidentiality or natural model forgetting.

The denied child edits also return an ordinary completed task containing an explicit report of denial. The child tool error remains in the child records. Completion of the child conversation and success of its attempted operation are separate facts, even when the report truthfully explains the denial.

## Check the supplied evidence

From the repository root, with Python 3.12 or newer:

```sh
python series/opencode/v1.18.30/labs/04-subagents-shared-work/scripts/verify_boundary_reference.py series/opencode/v1.18.30/labs/04-subagents-shared-work/reference-results/windows-2026-10-10-boundary/receipt.json
python series/opencode/v1.18.30/labs/04-subagents-shared-work/scripts/test_boundary_evidence.py
```

Use `python3` where appropriate. Expected: a consistent six-case receipt and rejection of 18 contradictory receipt controls. These portable commands do not execute OpenCode. See the [reference result](reference-results/windows-2026-10-10-boundary/README.md) and [sanitized receipt](reference-results/windows-2026-10-10-boundary/receipt.json).

## Run a fresh experiment

Requirements: Windows x64, Python 3.12+, Node.js 24, Git, and the official [OpenCode v1.18.30 binary](https://github.com/anomalyco/opencode/releases/tag/v1.18.30). The runner checks its SHA-256 against `c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea`. Source commit: `3104c1428ec91f809e5ab86631300de41eb6952e`.

```powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
cd the-agent-stack-labs
$lab = 'series/opencode/v1.18.30/labs/04-subagents-shared-work'
$privateOutput = Join-Path ([IO.Path]::GetTempPath()) 'opencode-boundary-private'
python "$lab/scripts/run_boundary_lab.py" --opencode 'C:\Tools\opencode.exe' --node (Get-Command node).Source --output $privateOutput
```

Then use the unique capture path printed by the runner:

```powershell
$run = 'PASTE_PRINTED_CAPTURE_DIRECTORY'
python "$lab/scripts/verify_boundary_run.py" $run --receipt (Join-Path $privateOutput 'boundary-receipt.json')
python "$lab/scripts/test_boundary_evidence.py" --receipt (Join-Path $privateOutput 'boundary-receipt.json') --raw $run
```

Expected: all six cases captured, successful independent reconstruction, and rejection of 18 corrupted private capture copies in addition to the public controls. The unchanged copy must pass first. The checker reads captured provider proposals and reports, exported session/tool state, actual permission evaluation logs, file bytes, test process output and current workspace contents. It does not accept a runner's `passed` flag. These checks establish consistency, not independent authentication of a historical execution.

## Execution path and policy ownership

Each case launches the real CLI's `serve` command on a random loopback port. A supported `POST /session` creates an empty parent with its case-specific session permission list. The CLI then runs `run --attach --session` against that server. All cases use this path, including those whose session list contains no edit deny. This differs from the original October 7 in-process `run` trace and is stated explicitly because project/agent configuration must not be mislabeled as session policy.

The loopback provider scripts tool proposals and final text. OpenCode performs task dispatch, child creation, input assembly, policy evaluation, real reads and edits, and report return. The external harness prepares the fixture, captures evidence and runs the fixed Node tests. It does not perform the requested edit. There is no model inference or paid provider usage.

The harness starts a new server, home, configuration, data, cache and state directory per case. It selects only a synthetic loopback provider, uses `--pure`, and disables sharing, model fetching, auto-updates, snapshots, formatters and LSP. No experimental feature or automatic approval flag is enabled. No `ask` event or remembered grant is exercised. This is input isolation for a synthetic test, not an OS sandbox. Server and provider processes are stopped in cleanup, including on failure. Raw captures remain outside the checkout.

| Boundary | Evidence and scope |
| --- | --- |
| Coordinator role to worker | Runtime: direct deny paired with delegated allow under the same coordinator policy. Source: [permission derivation](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/agent/subagent-permissions.ts#L14-L27) does not copy parent role rules. |
| Parent session to fresh worker | Runtime: the target deny appears in both exported session rule lists and the worker edit is denied. Fresh state only. |
| Worker role to operation | Runtime: the worker's own target deny blocks its edit while dispatch succeeds. |
| Delegation gate | Runtime: task-to-worker denial creates no child and performs no edit. [Dispatch check](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L104-L129). |
| Conversation input and selected return | Runtime markers, exact supplied prompts, child records and parent continuation agree. [Task prompt and return](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L197-L224). |
| Built-in Plan | Source only here: [Plan role](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/agent/agent.ts#L156-L178) denies General delegation. This lab does not run Plan. |

## Limits that matter

The phrase “child authority is broader” would be too broad. One operation denied to this coordinator is permitted to this worker. Their entire capability sets are not proven to form a superset relation.

Session deny propagation is not claimed as an unconditional security ceiling. The inspected evaluator applies ordered rules and remembered grants, and tool exposure is another control. This matrix uses fresh approval state and a specific last target rule to reach the operation gate. It does not exercise remembered grants, alternate mutation tools, hostile plugins or isolation from the host.

Resumed tasks retain existing session state. This fresh-child matrix does not establish a new contract for resume. Cancellation, rollback, background tasks, concurrent writers, merge conflicts, automatic planning quality and performance are also untested. See the [original shared-file trace](README.md) for its separate checkpoint and parent-test evidence.

Keep raw request bodies, logs, databases, system prompts and local paths private. Publish only the sanitized verified receipt. A failed or incomplete capture should be retained for inspection rather than relabeled as an expected result.
