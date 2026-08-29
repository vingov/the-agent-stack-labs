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
| Plugins can register host capabilities but runtime enablement gates their assets | TEST-BACKED + DOC-BACKED | PASS | Focused plugin runtime-disable tests passed at the pin |
| Plugin-to-MCP access is not ambient authority | TEST-BACKED + DOC-BACKED | PASS | MCP trust-gating tests passed; official docs require a per-plugin server allowlist |
| MCP tools can refresh after discovery without silently bypassing trust | TEST-BACKED | PASS | Focused refresh and trust-gating tests passed |
| Kanban project orchestration was reproduced end to end in this lab | NOT VERIFIED | Not claimed | Part 4 describes it only at the documented/code-backed boundary |
| The fixture provides distributed exactly-once execution | NOT VERIFIED | Not claimed | The fixture tests retry-safe single-process evidence, not concurrent writers |
| Plugin or MCP provider behavior was live-tested against a third-party service | NOT VERIFIED | Not claimed | The public reference uses source tests for those boundaries, not an external account |

Primary documentation:

- [Tools and toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/)
- [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins/)
- [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/)
- [Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/)
- [Persistent goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals/)
- [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)
