# Windows reference result: 2026-08-23

## Outcome

The final provider-backed pass was **PASS**: all 18 declared checks succeeded.

The experiment used Hermes v0.20.1 at tag `v2026.8.13`, commit `f80f453ae0679347e38abc917c7f94f717bf96c5`, with an isolated profile, both write-approval gates enabled, background review disabled, and a real `openai-codex` provider path.

## Observed sequence

1. Hermes proposed the environment fact through the memory tool. The pending record existed while the durable marker was absent. Native approval replay then added it to `MEMORY.md`.
2. The user preference followed the same staged lifecycle but committed to `USER.md`.
3. A rejected memory canary left the memory-tree hash unchanged.
4. An incomplete skill was visible as a full diff, then rejected without changing the skill tree.
5. The first complete skill proposal failed approval because its 152-character description exceeded the pin's 60-character routing budget.
6. A replacement with a 54-character description was approved.
7. A fresh provider-bound prompt contained the fact, preference, and compact skill-index markers. It contained neither rejected canary.
8. The fresh session called `skill_view`, ran the network-free fixture, inspected the dry-run receipt, deployed locally, and verified the artifact.

## Execution note

The skill's first Windows command used a backslash path and reached PowerShell as `.scriptsTest-Lab.ps1`, returning exit 64. Hermes retried with `./scripts/Test-Lab.ps1` and completed the workflow. The published cross-platform skill uses platform-neutral script names and the reader commands use forward slashes.

## Evidence boundary

The JSON result publishes counts, hashes, marker-presence booleans, decisions, and sanitized receipts. It does not publish credentials, raw provider request bodies, full prompts, absolute user paths, or the session database.
