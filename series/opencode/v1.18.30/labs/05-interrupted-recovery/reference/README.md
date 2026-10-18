# Windows reference, October 18 2026

The [receipt](receipt.json) is a sanitized projection of private run `interruption-iqlbpa3u`. It contains complete synthetic snapshot bytes, fixture hashes, named acceptance results, selected patch paths, bounded process observations, and source identities. It contains no raw provider transcript, database, credentials, or absolute local path.

- OpenCode: official Windows x64 v1.18.30; actual tag commit `3104c1428ec91f809e5ab86631300de41eb6952e`.
- Binary SHA-256: `c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea`.
- Runtime: Windows x64, Python 3.12.14, Node.js 24.13.0, PowerShell 7.6.6, Git 2.52.0.windows.1.
- Evidence: real CLI/tool execution with prescribed loopback provider choices; no model inference.
- Collector: exact source and fixture bytes were archived at run initialization; their hashes are in `implementation_sha256`. The collection was made during development before the lab's first Git commit. Verification code and documentation were completed afterward. Their current files are not represented as the historical collector.
- Earlier valid pilot: normal/graceful pair `interruption-zqj_60hz`, independently verified before adding the forced comparison. An earlier long-path pilot was invalid and excluded.

All timestamps ending in `_ns` and interval values are readings from one Python process's monotonic performance counter, not Unix timestamps. The first confirmed exit query is an observation bound. It is not the process's exact exit instant. Creation/exit timestamps ending in `_100ns` come from Windows process identity APIs. PIDs alone do not establish identity.

For the forced case, `states.primary.remote_read_available` is false because the server is down. Empty tool/patch arrays at that checkpoint mean unavailable. The subsequent restarted read supplies the stored-record evidence. The helper remains alive through the last pre-cleanup observation, then exits 75 after the harness's stop marker. The receipt distinguishes this from the generator exit observed before harness cleanup in the graceful case.

| Named test | Initial baseline | Partial task | Normal completed | Forced first revert |
| --- | --- | --- | --- | --- |
| Preserves meaningful interior spaces | Pass | Pass | Pass | Pass |
| Trims outer whitespace | Fail | Pass | Pass | Fail |
| Normalizes an all-whitespace label | Fail | Pass | Pass | Fail |
| Preserves the empty label | Pass | Pass | Pass | Pass |
| Catalogue has intended label values | Fail | Pass | Pass | Pass |
| Manifest identifies actual catalogue bytes | Pass | Fail | Pass | Fail |

Normal/graceful first revert exactly match the initial baseline. Every unrevert exactly matches its own pre-undo file set. Restoring baseline and completing the task are distinct outcomes.

The ordinary `SessionPrompt` path was exercised, with native LLM disabled. SDK/API naming does not imply the newer core SessionV2 runtime. Source correspondence was also checked against v1.19.3, actual tag commit `e3c4eb242585dcd77be1a867391b7c25fd47ce52`: the focused cancellation, processor cleanup, snapshot, revert, run-state, and storage mechanisms were unchanged. That later release was not executed. The CLI file has an unrelated session-sharing helper change; the whole CLI file is not claimed identical.

Raw-capture validation passed all three cases and rejected 19 in-memory negative controls. Public consistency checks and fixture/harness tests are separate from live reproduction. The receipt is not a cryptographic attestation by OpenCode or an independent third party.
