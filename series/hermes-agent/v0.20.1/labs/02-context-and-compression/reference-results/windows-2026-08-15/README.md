# Windows reference result

This is a sanitized summary of the provider-backed reference run performed on August 15, 2026.

## Runtime

- Hermes Agent v0.20.1
- Tag v2026.8.13
- Commit f80f453ae0679347e38abc917c7f94f717bf96c5
- Windows NT 10.0.26200, AMD64
- PowerShell 7.6.3
- Python 3.11.16
- Provider/model: openai-codex / gpt-5.6-sol
- 22 captured provider calls
- 16 completed user turns
- two distinct sessions

## Direct observations

- Baseline prompt: ORBIT, CEDAR, AMBER, JADE, and VIOLET present.
- Baseline prompt: EMBER, COBALT, and INDIGO absent.
- Progressive read: EMBER arrived through the enriched tool result.
- Progressive read: system-prompt SHA256 did not change.
- Ordinary post-edit request: AMBER remained and COBALT was absent.
- Post-compression prompt: COBALT present and AMBER absent.
- Compression: same session ID and in-place mode.
- Full skill load: INDIGO arrived through tool-result history.
- Provider metrics: fresh baselines reported zero cache-read tokens; repeated requests commonly reported 15,872.
- Local inference KV cache: NOT VERIFIED.

## Compression counts

| Stage | Total | Active | Inactive | Compacted |
| --- | ---: | ---: | ---: | ---: |
| Before | 28 | 28 | 0 | 0 |
| Immediately after | 40 | 12 | 28 | 28 |
| After next request | 42 | 14 | 28 | 28 |

TEST_FACT_07 and TEST_FACT_08 survived in the live selected tail and next provider request. Their original SQLite rows remained inactive and compacted rather than active.

## Test receipt

- Accepted targeted result: 83 passed, 1 skipped.
- Six additional Windows tests reached behavioral assertions and failed during SQLite temporary-directory cleanup. They are not counted as TEST-BACKED passes.

The machine-readable form is [result.json](result.json).
