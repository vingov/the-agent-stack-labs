# Part One: claim-to-evidence map

Read the [lab overview and commands](README.md), then the [sanitized receipt](reference-results/windows-2026-09-13/receipt.json).

| Claim | Evidence | What this does not establish |
| --- | --- | --- |
| Successful CLI exit and a success sentence can coexist with an unchanged, failing workspace. | `answer_only`: CLI exit 0, identical source hashes, independent test exit 1, final sentence present. | The sentence was scripted. This does not measure real-model dishonesty or failure frequency. |
| This OpenCode run executed read, edit, and bash tools and returned tool results on subsequent provider requests. | `tool_loop`: three completed tool records with matching emitted/observed IDs; result counts 0, 1, 2, 3; four provider requests. | Three tools and four requests are properties of this fixture, not universal loop counts. |
| The patch passed these three tests without changing the tests. | Before/after source and test hashes; independent Node test exit changes from 1 to 0. | Three assertions are not exhaustive correctness. The final test runner belongs to this lab, outside OpenCode. |
| The ordinary CLI can enter the application handler through an in-process adapter. | Source inspection of the release's [CLI](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/cli/cmd/run.ts). | The local provider does use a loopback HTTP listener. This is not evidence that every client runs without an OpenCode server listener. |
| The prompt loop and processor organize continuation and tool state. | Source inspection of [prompt.ts](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/prompt.ts) and [processor.ts](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/processor.ts), alongside the observed CLI events. | The lab does not instrument every internal callback, prove exactly-once execution, or test crash recovery. |
| The receipt checker rejects inconsistent evidence. | [18 corruption controls plus malformed-input and fixture tests](scripts/test_lab.py). | A consistent JSON receipt is not authenticated proof of execution. A fresh CLI run is a separate command. |

## Coverage boundaries

- **Observed runtime:** official OpenCode 1.18.30 on Windows AMD64, using a deterministic localhost provider. No language-model inference.
- **Portable checks:** Python receipt verification, corruption controls, and Node fixture acceptance tests on the CI matrix. These do not run OpenCode.
- **Source-backed explanation:** ordinary CLI-to-session path and processor responsibilities at the linked release commit.
- **Not tested:** live-model tool selection, desktop/TUI behavior, parallel sessions, cancellation, recovery, security containment, or general coding quality.

No live-model run is needed for the Part One claim about separating a final answer from execution evidence. A later claim about model choices, planning, or reliability would require a separately labeled live-model experiment and suitable controls.
