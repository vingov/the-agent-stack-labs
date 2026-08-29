# Lab 04: Capability provenance and execution contracts

## Central question

If the policy, input, and expected artifact stay fixed, what changes when work is executed directly, delegated to a child, continued by a persistent goal, or triggered by cron?

## What you will learn

By the end of this lab, you should be able to distinguish:

- a tool from the toolset that exposes it
- a plugin or MCP server that supplies capability from the agent that invokes it
- direct execution from delegation, persistent continuation, and scheduled execution
- a model's success claim from an immutable attempt receipt and committed-operation record
- scheduler completion from operation success and delivery success
- a logical operation ID from the individual attempt IDs used to achieve it

## The shortest useful model

| Surface | What it changes | Who owns the next model/tool loop | Durability boundary |
| --- | --- | --- | --- |
| Tool | One callable action | Current agent | None by itself |
| Toolset | Which tools are exposed | Current agent | Session/profile configuration |
| Plugin | Host extension and capability provenance | Host process plus current agent | Plugin install/configuration |
| MCP server | External capability transport | MCP server plus current agent | Server/configuration boundary |
| Delegation | Context and execution owner | Child agent; parent receives a summary | Tied to the owning session/process |
| Persistent goal | Continuation policy | Same session, judge, gates, and budget | Goal state in the session database |
| Cron | Trigger and run owner | Scheduler-created run | Job definition, execution ledger, output, and delivery state |

These are not interchangeable abstractions. A plugin can register a tool; a delegated child can invoke it; a goal can keep trying until a gate passes; cron can trigger a fresh run later. Each layer answers a different question.

## The fixture contract

Every path receives the same 91-byte synthetic artifact, policy `P4-POLICY-V2`, procedure `HERMES-P4-PROCEDURE-V2`, and allowed output `state/deployed/artifact.txt`.

The runner requires:

1. an exact source SHA-256;
2. the current procedure;
3. the one allowed output path;
4. a successful dry-run receipt for the same operation and execution mode;
5. a unique attempt ID; and
6. post-write verification.

Each attempt gets an immutable receipt. A successful logical operation also gets one immutable committed-operation record. A later duplicate attempt is suppressed without replacing the primary success receipt.

## Reference finding

The provider-backed reference run used Hermes v0.20.6, tag `v2026.8.27`, commit `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`, on Windows with `openai-codex` and `gpt-5.6-sol`.

| Path | Execution owner | Provider/tool activity | Operation result |
| --- | --- | --- | --- |
| Direct | Current session | 4 API calls, 3 tool calls | Committed |
| Delegated | One leaf child | Parent: 2 API/1 tool; child: 4 API/3 tools | Committed |
| Persistent goal | Same resumed session plus gate/judge | 8 API calls, 4 tool calls, 3/3 goal turns | Goal done; committed |
| Cron | Scheduler-created fresh run | 45,407 tokens; 25.9 seconds | Ledger completed; committed |

All four committed the same SHA-256:

`eb82803246ce25226ea8b769184760cb17df0dac56f3c0fdaed0a444f101f4ad`

Three negative controls exposed the boundary more clearly:

- a delegated child without `terminal` made zero tool calls and produced no receipt;
- a goal whose gate watched an absolute workspace outside the process working directory exhausted its retries because the unchanged-workspace optimization fingerprinted the wrong directory;
- a cron run reached ledger state `completed` while both operation commands failed after sentence punctuation was copied as an argument. No operation receipt existed.

After correcting the boundary or prompt, the goal and cron controls passed. The reference run also passed 75 portable focused Hermes tests. Three additional goal-gate tests use POSIX shell commands (`true`, `sleep`, and `exit`) and were recorded as non-portable on native Windows rather than counted as passes.

An additional provider-free probe used the real pinned `PluginManager` to discover and enable a synthetic read-only plugin, invoke its registered inspection tool and sanitized `post_tool_call` hook, and confirm that unloading removed the scoped tool registration. A focused gap suite for plugin consent/hooks, abandoned cron ownership, and Kanban worker/claim lifecycle passed 112 selected Windows-compatible tests. Two Kanban orphan-reconciliation cases that shell out to POSIX `sleep` and `true` were recorded as platform exclusions.

See the [sanitized reference result](reference-results/windows-2026-08-28/README.md) and [claim matrix](expected/claim-matrix.md).

## Choose a track

- [Explorer](explorer.md): run seven deterministic controls without Hermes or a provider. About 20 minutes.
- [Builder](builder.md): send the same rendered commands through direct and delegated Hermes sessions. Provider optional.
- [Investigator](investigator.md): reproduce the real plugin-host probe, persistent-goal and cron ownership, negative controls, and source-test evidence. The plugin probe is provider-free; the live agent paths require a provider.

## Start here

macOS or Linux:

~~~bash
lab="$(bash ./scripts/initialize-lab.sh)"
bash ./scripts/test-lab-fixtures.sh "$lab"
bash ./scripts/run-controls.sh "$lab"
~~~

Windows with PowerShell 7:

~~~powershell
$lab = ./scripts/Initialize-Lab.ps1
./scripts/Test-LabFixtures.ps1 -FixtureRoot $lab
./scripts/Run-Controls.ps1 -Workspace $lab
~~~

The expected result is seven passing checks: dry run, apply, duplicate suppression, primary-receipt immutability, stale-procedure rejection, missing-dry-run rejection, and denied-output rejection.

## Cost and safety

The Explorer track is free and network-free. Builder and Investigator provider runs consume tokens; the reference provider usage is reported so readers can budget before running.

Use a disposable `HERMES_HOME`. The fixture itself performs no network calls, but a live Hermes model request necessarily contacts the configured provider. Do not publish credentials, raw provider bodies, full prompts, absolute home-directory paths, live session databases, or unsanitized delegation transcripts.

The fixture demonstrates retry-safe evidence in one process. It does not claim distributed exactly-once execution under concurrent writers.
