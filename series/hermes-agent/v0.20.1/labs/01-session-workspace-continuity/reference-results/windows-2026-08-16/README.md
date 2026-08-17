# Windows reference result

This sanitized result was recorded on August 16, 2026 against the user's
installed Hermes Agent runtime.

## Runtime

- Hermes Agent v0.20.1
- Release label 2026.8.13
- Installed source commit 0c50bdbdea57f3d63571e58ae70b3520c4f8b62e
- Windows, AMD64
- Python 3.11.16
- SQLite schema version 26

The installed source checkout contained unrelated local changes, so the result
records source_worktree_dirty=true. The storage implementation files exercised
by the probe were clean at the installed commit, recorded as
relevant_storage_source_dirty=false.

## Result

All ten checks passed:

- two distinct synthetic session IDs persisted;
- workspace-a and workspace-b remained distinct;
- resume resolution selected the primary session;
- only the primary transcript contained the task marker;
- the installed sessions CLI listed both sessions;
- workspace filtering returned only the primary session;
- a redacted export returned the selected primary transcript.

## Evidence boundary

The probe exercised the installed Hermes storage implementation and sessions
CLI. It did not call a provider, execute a model-tool turn, start a messaging
gateway, test handoff, inject a restart, or test platform delivery.

No state database, credentials, raw export, or absolute path is included. The
machine-readable summary is [result.json](result.json).
