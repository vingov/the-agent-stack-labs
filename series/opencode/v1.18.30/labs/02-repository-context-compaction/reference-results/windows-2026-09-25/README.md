# Windows reference

Observed September 25, 2026 with official OpenCode 1.18.30, Windows AMD64 and Python 3.14.2. The source tag is `3104c1428ec91f809e5ab86631300de41eb6952e`. The executable's SHA-256 is included in [receipt.json](receipt.json).

Two cases each execute three `opencode run` invocations in one session, plus three read-only exports. All CLI invocations exit zero. The disabled case makes six provider requests; the enabled case makes eight, including one summary request. Each performs three real read tool calls. The initial text attachment is expanded separately into synthetic user text.

No model inference. Token usage, tool decisions and summary text are scripted. The generated fixtures, configuration and controlled external file change are documented in the [lab README](../../README.md). Pruning is disabled.

The receipt was checked against private raw requests, all final session records, CLI streams and final files. Raw artifacts contain machine paths and full prompts and are intentionally excluded. The offline verifier checks consistency, not historical authenticity. The documented fresh-checkout path was also executed on Windows. CI validates the recorded evidence on Windows, macOS and Ubuntu; macOS/Linux CLI execution is not claimed.
