# Lab 01: Session identity and workspace continuity

This lab accompanies
[Hermes Agent Architecture Part 1](https://theagentstack.substack.com/p/hermes-agent-architecture-part-1).

## Central question

When two requests use the same Hermes runtime, what makes one a continuation
and the other a separate conversation?

## Why this post needs a lab

Part 1 makes an architectural distinction that is easy to understand in prose
but more useful when observed:

- the session ID owns durable conversation continuity;
- the stored working directory binds that conversation to an execution context;
- a fresh session does not automatically inherit another session's transcript;
- the persistence and CLI surfaces can be verified without trusting a model's
  answer.

The narrow lab tests those boundaries. It does not claim to reproduce every
gateway, delivery-ledger, fallback, or tool-loop behavior discussed in the post.

## Version boundary

The article was researched against Hermes v0.19.1 at commit
cc4cab2. The reference result in this lab uses the locally installed Hermes
v0.20.1 release label 2026.8.13 at commit
0c50bdbdea57f3d63571e58ae70b3520c4f8b62e.

That makes this a version-drift check, not a retroactive claim that the article
was tested on v0.20.1.

## What the reference run established

The provider-free Windows reference run passed all ten storage and CLI checks:

1. Hermes created a disposable state.db.
2. The primary synthetic session persisted.
3. Its workspace-a binding persisted.
4. Resume resolution returned the primary session ID.
5. A fresh session received a different ID.
6. The fresh session retained a different workspace.
7. The task marker appeared only in the primary transcript.
8. The installed sessions CLI listed both sessions.
9. Its workspace filter returned only the primary session.
10. A redacted export returned the selected primary transcript.

The run did not call a provider, execute the model-tool loop, start a gateway,
or test platform delivery.

## Choose a track

- [Explorer](explorer.md): reproduce the storage and CLI evidence without a
  provider account.
- [Builder](builder.md): add a supported live CLI session and explicit resume.
- [Investigator](investigator.md): extend the experiment to a non-production
  gateway, handoff, restart, or delivery boundary.

## Quick start

macOS or Linux:

~~~bash
bash ./series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/initialize-lab.sh
# Run the export commands printed by the initializer.
bash ./series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/run-storage-probe.sh
~~~

Windows with PowerShell 7:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\01-session-workspace-continuity\scripts\Initialize-Lab.ps1
# Run the environment commands printed by the initializer.
pwsh .\series\hermes-agent\v0.20.1\labs\01-session-workspace-continuity\scripts\Run-StorageProbe.ps1
~~~

The probe uses the Python environment belonging to the active Hermes install.
It refuses an existing state.db or credential-shaped files and writes only a
sanitized JSON result under the disposable lab's evidence directory.

## Troubleshooting

If install-directory discovery fails, run `hermes version` and pass the printed
install directory as the second argument to the Bash probe or as
`-HermesSource` in PowerShell.

If the probe reports an existing state.db, create a new disposable lab. Do not
delete or repurpose a real Hermes database.

## Evidence boundary

The probe imports Hermes' versioned storage implementation. That is useful
diagnostic evidence but is not a promise that internal Python APIs are stable.
The Builder track uses the supported Hermes CLI for the end-to-end extension.

Never commit state.db, auth files, exported raw transcripts, or absolute home
paths.
