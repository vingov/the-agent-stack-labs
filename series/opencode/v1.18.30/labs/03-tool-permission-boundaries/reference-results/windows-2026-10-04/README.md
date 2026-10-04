# Windows reference, October 4, 2026

The [receipt](receipt.json) was reconstructed from real OpenCode CLI runs with a scripted loopback provider. Its fields come from captured provider requests/responses, resolved configuration and build-agent policy, permission logs, CLI events, exported session state, actual file snapshots and independent Node test results.

All four cases began with the same source and unchanged test file. Allow and auto ask produced the intended new bytes and three passing tests. Ordinary ask and auto deny left the original bytes and one passing/two failing tests. Tools remained advertised, and the runtime logged the intended target rule in each case.

Actual permission-reply payloads were not captured. In particular, auto mode's `once` reply is a source-attributed explanation of the observed ask followed by completion, not an invented captured event. CLI exit zero occurred in every case and is not the acceptance criterion.

Public data contains synthetic tool arguments, hashes, tool/status summaries and generated session IDs. Raw logs, request bodies, exported conversation content, absolute local paths and application databases remain private and are not part of this repository.

Runtime execution coverage is Windows x64 only. Portable CI validates receipt consistency and rejection controls on Windows, macOS and Linux. Neither offline validation nor the receipt independently authenticates the original execution.
