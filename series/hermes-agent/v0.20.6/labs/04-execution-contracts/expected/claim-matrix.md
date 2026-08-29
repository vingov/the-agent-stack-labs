# Claim matrix

| Claim | Evidence class | Reference status | Boundary |
| --- | --- | --- | --- |
| Direct execution was owned by the current session | OBSERVED | PASS | Session trace: 3 terminal calls; direct receipt committed |
| A leaf child received fresh explicit context | OBSERVED + DOC-BACKED | PASS | Child transcript began with only delegated goal/context plus runtime instructions |
| Delegation inherited rather than widened tool authority | OBSERVED + TEST-BACKED | PASS | Child without parent `terminal` made 0 tool calls and produced no receipt |
| Only the child summary re-entered parent context | OBSERVED + DOC-BACKED | PASS | Parent contained one `delegate_task` result with bounded summary/trace metadata |
| A persistent goal continued without repeated user prompts | OBSERVED | PASS | Goal used 3/3 turns and reached `done` after deterministic verification |
| A deterministic gate ran before the goal judge could declare completion | OBSERVED + TEST-BACKED | PASS | Missing receipt caused continuation; passing verifier allowed the final judge verdict |
| Goal gate retry behavior depends on the process workspace fingerprint | OBSERVED + CODE-BACKED | PASS as negative control | Misaligned cwd reused a stale failing gate result and paused after retries |
| Cron created a fresh agent run with a user-owned model/provider pin | OBSERVED + DOC-BACKED | PASS | Job record, usage audit, output document, and operation receipt agreed |
| Cron ledger completion is not operation success | OBSERVED | PASS as negative control | First cron run was `completed`; both commands failed and no operation record existed |
| Cron execution and delivery are separately tracked | TEST-BACKED + DOC-BACKED | PASS | Focused execution-ledger and created-delivery tests passed; local output was saved |
| Duplicate attempts preserve primary success evidence | OBSERVED | PASS | Duplicate receipt said `suppressed`; primary receipt digest was unchanged |
| Stale procedure, missing dry run, and denied output are rejected pre-mutation | OBSERVED | PASS | Network-free control matrix recorded three rejected attempts and no prohibited output |
| Plugins can register host capabilities but runtime enablement gates their assets | OBSERVED + TEST-BACKED + DOC-BACKED | PASS | Real pinned `PluginManager` discovered the enabled synthetic plugin; capability-consent and runtime-disable tests passed |
| Observational plugin hooks can record sanitized events without becoming the operation verifier | OBSERVED + TEST-BACKED | PASS | Synthetic `post_tool_call` hook recorded only tool name, status, and argument-key names; verification remained independent |
| Plugin unload removes its scoped tool registration | OBSERVED + TEST-BACKED | PASS | `fixture_inspect` was absent after `PluginManager.unload()` |
| Plugin-to-MCP access is not ambient authority | TEST-BACKED + DOC-BACKED | PASS | MCP trust-gating tests passed; official docs require a per-plugin server allowlist |
| MCP tools can refresh after discovery without silently bypassing trust | TEST-BACKED | PASS | Focused refresh and trust-gating tests passed |
| Kanban project orchestration was reproduced end to end in this lab | NOT VERIFIED | Not claimed | Part 4 describes it only at the documented/code-backed boundary |
| Kanban worker and claim lifecycle boundaries have focused regression coverage | TEST-BACKED | PASS | Selected worker-run, orphan-reconciliation, review-lifecycle, and dead-owner tests passed; two POSIX helper cases were excluded on Windows |
| A session-side Kanban claim can outlive its lease without a worker heartbeat and overlap a replacement writer | ISSUE-REPORTED + CONTRIBUTOR-REPRODUCED | Not reproduced in this lab | Open Hermes issue #83736 documents the incident and reproduction; the article must not upgrade it to observed lab evidence |
| The fixture provides distributed exactly-once execution | NOT VERIFIED | Not claimed | The fixture tests retry-safe single-process evidence, not concurrent writers |
| Plugin or MCP provider behavior was live-tested against a third-party service | NOT VERIFIED | Not claimed | The public reference uses source tests for those boundaries, not an external account |

Primary documentation:

- [Tools and toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/)
- [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins/)
- [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/)
- [Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/)
- [Persistent goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals/)
- [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)
