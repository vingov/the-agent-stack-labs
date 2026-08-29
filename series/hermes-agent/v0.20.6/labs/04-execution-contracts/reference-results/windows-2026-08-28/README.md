# Windows reference result: 2026-08-28

## Outcome

The final result was **PASS WITH DOCUMENTED NEGATIVE CONTROLS**. Direct, delegated, persistent-goal, and cron-owned runs all committed the same verified artifact. The fixture's seven deterministic controls passed.

The experiment used Hermes v0.20.6 at tag `v2026.8.27`, commit `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`, with a disposable profile and a real `openai-codex` / `gpt-5.6-sol` provider path.

## Positive runs

| Path | Result | Evidence summary |
| --- | --- | --- |
| Direct | PASS | 4 API calls, 3 tool calls, committed direct receipt |
| Delegated | PASS | Parent 2 API/1 tool; child 4 API/3 terminal calls; 20.38 seconds |
| Persistent goal | PASS | 8 API calls, 4 tool calls, 3/3 turns, gate PASS, final state `done` |
| Cron | PASS | Run ledger completed, 45,407 tokens, 25.9 seconds, local output saved, operation committed |

Every committed operation produced SHA-256 `eb82803246ce25226ea8b769184760cb17df0dac56f3c0fdaed0a444f101f4ad`.

## Negative controls

### Delegation without terminal

The parent exposed only the delegation toolset. The leaf inherited no terminal capability, made zero tool calls, reported itself blocked, and created no receipt. This falsified any interpretation that the child could widen its own authority.

### Goal with a misaligned process directory

The first goal experiment kept the Hermes process in an unchanged Git checkout while its gate verified an absolute workspace elsewhere. After the first missing-receipt failure, the unchanged-workspace optimization fingerprinted the process cwd, reused the stale failure, and exhausted retries even though the agent later created the artifact. The goal paused. A clean session whose actual process directory matched the goal workspace reached `done`.

### Cron prompt punctuation

The first cron prompt wrote each “exact command” as a sentence ending in a period. The model passed `.` as a command-line argument. Hermes recorded the run as `completed` because the agent run itself finished and produced a report, but both fixture commands failed and no operation receipt existed. A delimiter-based prompt removed the ambiguity and committed successfully.

## Focused source tests

- 60 of 60 tests passed across delegation toolset scope, cron execution ledger, cron delivery, plugin runtime disablement, MCP trust gating, and MCP refresh.
- 15 platform-compatible goal-gate tests passed.
- 3 goal-gate tests used POSIX shell commands and failed under native Windows command parsing. They were disclosed and excluded from the portable pass count.

## Gap-closing plugin and lifecycle pass

The follow-up pass used the real pinned `PluginManager` with a synthetic read-only plugin. Discovery, enablement, tool invocation, sanitized post-tool observation, and unload cleanup all passed without contacting a provider or external service. See the [sanitized plugin-host receipt](plugin-probe.json).

A selected 112-test Windows-compatible slice passed across plugin capability consent, verification/approval hooks, abandoned cron ownership, and Kanban worker/claim lifecycle. Two additional orphan-reconciliation cases invoke POSIX `sleep` and `true`; they were disclosed as native-Windows platform exclusions.

Hermes issue [#83736](https://github.com/NousResearch/hermes-agent/issues/83736) remained open on August 29, 2026. Its session-claim/two-writer incident is issue-reported and contributor-reproduced, not reproduced by this lab.

## Evidence boundary

The JSON result publishes sanitized counts, durations, hashes, booleans, and receipt fields. It does not publish credentials, provider bodies, full prompts, absolute paths, raw delegation logs, cron output documents, or session databases.
