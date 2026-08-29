# Investigator track

## Goal

Reproduce the four ownership modes, deliberately cross their boundaries, and publish a sanitized result that separates operation, orchestration, and delivery evidence.

## Minimum experiment matrix

| Experiment | Owner or trigger | Required evidence |
| --- | --- | --- |
| E0 | Pinned source/runtime | version, tag, commit, platform, provider, model |
| E1 | Direct session | session usage plus direct operation receipt |
| E2 | Leaf delegation | parent usage, child usage/tool trace, delegated receipt |
| E2N | Delegation without terminal | zero child tool calls and no receipt |
| E3 | Persistent goal | goal contract, deterministic gate, final `done` state, goal receipt |
| E3N | Misaligned goal workspace | exhausted/paused gate state and explanation of the fingerprint boundary |
| E4 | Cron fresh run | job pin, fire/run ledger, saved output, cron receipt |
| E4N | Cron command contamination | completed run ledger, failed commands, absent operation receipt |
| E5 | Plugin host boundary | real `PluginManager` discovery, tool result, sanitized hook event, unload cleanup |
| E6 | MCP boundary | pinned focused tests or a separately disclosed live integration |

## Real plugin-host probe

The optional probe uses the pinned Hermes `PluginManager`, not a mock host. It creates a synthetic read-only plugin inside the initialized workspace's disposable profile, enables it, discovers it, invokes its registered `fixture_inspect` tool and `post_tool_call` hook, then unloads the manager and verifies that the scoped tool registration disappears.

With the pinned checkout on `PYTHONPATH`:

~~~bash
python ./scripts/run_plugin_probe.py --workspace <INITIALIZED_WORKSPACE>
~~~

Expected evidence is written to `receipts/plugin-probe.json` and `receipts/plugin-probe-audit.jsonl`. The probe calls no model provider or external service. It proves the local plugin-host contract only; it does not prove third-party plugin authority or live MCP behavior.

## Persistent-goal helper

`scripts/seed_goal.py` makes the reference run deterministic by using the v0.20.6 `GoalManager` API directly. Run it only with the Python environment that imports the pinned Hermes checkout and only against a disposable profile.

1. Initialize a fresh workspace and start one Hermes session from that directory.
2. Record the session ID and exit.
3. Seed the goal:

~~~bash
python ./scripts/seed_goal.py \
  --session-id <SESSION_ID> \
  --workspace . \
  --operation-id investigator-goal-v2
~~~

4. Resume from the workspace with `--no-restore-cwd`, enable `terminal`, and send any kickoff message.
5. Capture `/goal status` after the loop stops. The expected positive checkpoint is `Goal done`, a passing gate, and a committed operation.

Why the working directory matters: the unchanged-gate optimization fingerprints the Hermes process working directory. In the negative reference run, the gate checked an absolute workspace elsewhere while the process remained in an unchanged Git checkout. Hermes reused the first failing result and exhausted retries even after the target artifact appeared. Aligning process cwd with the gate workspace fixed the run.

## Cron procedure

1. Initialize a fresh workspace.
2. Render commands with execution mode `cron`.
3. Build a self-contained prompt with separate `BEGIN/END DRY COMMAND` and `BEGIN/END APPLY COMMAND` markers.
4. Create a one-shot job with an explicit absolute `--workdir` and user-owned `--provider` / `--model` pin.
5. Trigger it with `hermes cron run <JOB_ID>`.
6. Compare four records:

   - `hermes cron runs <JOB_ID>`
   - the saved cron output document
   - `cron/usage_audit.jsonl` in the disposable profile
   - the fixture's committed-operation record

The cron command can report `Ran now: succeeded` when the agent run completed even if the operation inside that run failed. Never collapse execution-ledger state, task verification, and delivery state into one `success` boolean.

## Focused source tests

At commit `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`, the reference run executed:

~~~bash
python -m pytest -q \
  tests/tools/test_delegate_toolset_scope.py \
  tests/cron/test_execution_ledger.py \
  tests/cron/test_cron_created_delivery.py \
  tests/hermes_cli/test_plugin_runtime_disable_gate.py \
  tests/tools/test_mcp_trust_gating.py \
  tests/tools/test_refresh_agent_mcp_tools.py
~~~

Those six files produced 60 passes. Fifteen platform-compatible tests in `tests/hermes_cli/test_goal_gates.py` also passed. Three tests in that file embed POSIX shell commands and failed under native Windows command parsing; report them as platform exclusions, not successful evidence.

A later focused gap pass also covered plugin capability consent, verification and approval hooks, abandoned cron ownership, and Kanban worker/claim lifecycle. The selected Windows-compatible slice passed 112 tests. Two additional Kanban orphan-reconciliation cases shell out to POSIX `sleep` and `true`; disclose them as platform exclusions on native Windows rather than feature failures.

The gap slice was assembled from these files plus five targeted real-host discovery and hook-timeout cases in `tests/hermes_cli/test_plugins.py`:

~~~text
tests/hermes_cli/test_plugin_capabilities.py
tests/agent/test_verify_hooks.py
tests/tools/test_approval_plugin_hooks.py
tests/cron/test_dead_owner_claim_reclaim.py
tests/plugins/test_kanban_worker_runs.py
tests/gateway/test_kanban_reconcile_orphans.py
tests/hermes_cli/test_kanban_review_lifecycle_complete.py
~~~

The targeted cases were enabled/disabled portable-plugin discovery, observational-hook timeout isolation, and both fail-closed `pre_tool_call` timeout checks. Exclude only `test_live_worker_pid_defers_reconcile` and `test_dead_worker_pid_orphan_requeued` on native Windows; they launch POSIX helper commands.

## Evidence rules

- A final response is not an operation receipt.
- A committed operation is not proof the scheduler delivered its report.
- A parent summary is not a child tool trace.
- A plugin being installed is not proof it is enabled or trusted.
- An MCP tool being discoverable is not proof it has write authority.
- Report failed attempts and fixes; they are often the clearest architecture evidence.
- Do not publish raw provider requests, full prompts, session databases, credentials, or absolute user paths.

Use the [claim matrix](expected/claim-matrix.md) as the final publication checklist.
