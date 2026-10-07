# Claim matrix

The experiment was selected after a complete initial article draft. Its central sentence was: “The child’s edit can change the shared working file before its report returns to the parent.”

| Claim | Evidence class | Evidence and limit |
| --- | --- | --- |
| P4-03: the task creates a separate child conversation | OBSERVED_WITH_SCRIPTED_PROVIDER | Real parent `task` call, distinct exported child ID, stored parent link, task metadata and provider headers agree. No second CLI was used to simulate the child. |
| P4-05/06: supplied input is assembled for the child | OBSERVED_WITH_SCRIPTED_PROVIDER | Complete child requests contain the handoff marker and omit the parent-only marker. Child tool feedback appears in subsequent child requests. This is not a confidentiality claim. |
| P4-08/11: the child edit changes shared files before report return | OBSERVED_WITH_SCRIPTED_PROVIDER | Exported session and assistant directories, real read/edit paths, independent Git root and captured fixture path agree. The file checkpoint occurs after edit-result feedback and before final child response release. |
| P4-24/25: the selected report differs from the complete child record | OBSERVED_WITH_SCRIPTED_PROVIDER | The exported task output and first parent continuation equal the child summary wrapper. They omit the marker present in the child's read result. The scripted summary deliberately excludes that marker. |
| P4-28: acceptance is separately owned | OBSERVED_WITH_SCRIPTED_PROVIDER and recommendation | The parent test tool and independent external test process both pass four fixed tests. Hashes show the test file was unchanged. These checks were deliberately added by the workflow. |
| Task authority and child operation authority are separate | OBSERVED_WITH_SCRIPTED_PROVIDER | Logs record the task allow, two read allows, edit allow and parent test-command allow. Resolved roles and stored session rules are checked. No ask was used. |
| A fresh task does not provision a private checkout | CODE-BACKED, with observed shared-path evidence | [Task creation](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L136-L172), [instance directory](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/session.ts#L667-L689). The lab's development worktree and synthetic fixture directory were created by the external harness. |
| Task input does not pass the full parent transcript | CODE-BACKED, with bounded marker observation | [Child prompt submission](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L200-L212). Shared files, instructions and plugins can still convey information. |
| Task extracts selected returned text | CODE-BACKED, with observed text-only case | [Result extraction](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L213-L224). The error check covers the returned message, not every historical child tool. |
| Resume, foreground cancellation and CLI responder ownership | CODE-BACKED, NOT VERIFIED at runtime here | [Reuse](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L136-L172), [foreground wait/cancel](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/tool/task.ts#L321-L356), [CLI replies](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/cli/cmd/run.ts#L801-L820). No rollback, timing or cross-run responder outcome is asserted. |
| Natural delegation choice, quality, speed or reliability | NOT VERIFIED | Provider decisions and reports are prescribed. There is no live model inference. |

## Version decision

The October 7, 2026 stable-release check found v1.18.35 at actual tag commit `53d1eabb61e21162157817bf677da0a4ad3332e3`. The experiment retains the series baseline v1.18.30 at `3104c1428ec91f809e5ab86631300de41eb6952e`.

A bounded 34-file source comparison found 30 matching source bodies. Task execution, session creation, ordinary CLI routing, permission derivation and file tools matched. Four adjacent files differed: `session/llm/request.ts` adds session-header names, `session/message-v2.ts` changes media handling, `provider/provider.ts` changes Cloudflare timeout handling, and `provider/transform.ts` changes Google model options. This supports retaining the baseline for the selected text-only path. It is not whole-release equivalence, and this lab did not execute the newer binary.

The runner captures the baseline's actual `x-session-id`, `x-session-affinity` and `x-parent-session-id` headers. It does not assume the newer `x-opencode-session-id` names exist.
