# Reference environment

The reference run was performed on August 15, 2026.

This table records the environment that produced the published receipts. The
lab scripts also support macOS and Linux; they do not imply that the exact live
runtime finding has already been reproduced there.

| Item | Value |
| --- | --- |
| Hermes version | 0.20.1 |
| Tag | v2026.8.13 |
| Commit | f80f453ae0679347e38abc917c7f94f717bf96c5 |
| Operating system | Windows NT 10.0.26200 |
| Architecture | AMD64 |
| Shell | PowerShell 7.6.3 |
| Python | 3.11.16 |
| Provider/model | openai-codex / gpt-5.6-sol |
| API mode | codex_responses |
| Context engine | Default built-in context engine |
| Provider calls captured | 22 |
| User turns completed | 16 |
| Distinct sessions | 2 |

## Evidence boundary

The public reference result contains marker presence, hashes, counts, and classifications. It does not contain authentication material, full provider payloads, full system prompts, raw session rows, personal profile content, or absolute paths.

## Windows harness note

Six targeted tests reached their behavioral assertions and later failed during SQLite TemporaryDirectory cleanup on Windows. They are not counted as TEST-BACKED passes. The accepted targeted-test receipt is 83 passed and 1 skipped.
