# Hermes v0.20.6 reference environment

## Source pin

- Project: NousResearch/hermes-agent
- Hermes version: v0.20.6
- Release tag: `v2026.8.27`
- Commit: `5fc308a70719a83cccdbba4c0e39c23f5a8239d5`
- Release date: 2026-08-27

The reference checkout was a detached Git worktree at the exact commit. Runtime imports were pointed at that source tree, and `python -m hermes_cli.main --version` reported v0.20.6.

## Runtime

- Operating system: Windows, AMD64
- Python: 3.11
- Provider: `openai-codex`
- Model: `gpt-5.6-sol`
- Profile: disposable `HERMES_HOME`
- Fixture network: disabled by construction
- Provider network: enabled for live agent paths

The disposable profile reused only provider configuration and authentication from an earlier isolated validation profile. No normal user session database, memories, skills, plugin data, or cron jobs were copied.

## Evidence boundary

Published results contain counts, durations, hashes, booleans, source-test outcomes, and sanitized receipt fields. They exclude raw provider requests, full system prompts, complete session transcripts, absolute user paths, auth files, cookies, and session databases.

The provider-backed reference results are Windows-specific observations. The fixture and CI entry points are native PowerShell and Bash, so macOS and Linux readers can reproduce the deterministic controls and should report their own platform with live results.
