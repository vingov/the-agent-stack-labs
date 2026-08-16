# Lab 02: Context files, prompt snapshots, and compression

## Central question

When a durable Hermes file changes, when does that change become visible to the next model request?

## What you will learn

By the end of the lab, you should be able to distinguish:

- a durable source file
- a cached system-prompt snapshot
- a tool-result addition to conversation history
- the live history sent to the next provider request
- the active and compacted views in SQLite
- Hermes prompt reuse from provider-side prompt caching

## Synthetic markers

| Marker | Source | Expected path |
| --- | --- | --- |
| ORBIT | SOUL.md | Prompt snapshot |
| CEDAR | Root AGENTS.md | Startup project context |
| EMBER | backend/AGENTS.md | Progressive tool-result discovery |
| AMBER | Initial USER.md | Original profile snapshot |
| COBALT | Edited USER.md | Refreshed profile after verified compression |
| JADE | MEMORY.md | Prompt snapshot |
| VIOLET | Skill metadata | Skills index |
| INDIGO | Full SKILL.md body | skill_view tool-result history |

## Choose a track

- [Explorer](explorer.md): study the receipts without a provider account.
- [Builder](builder.md): reproduce the workflow through the supported Hermes CLI.
- [Investigator](investigator.md): instrument request and persistence boundaries, vary the experiment, and submit a compatibility result.

## Reference finding

In the Windows reference run for Hermes v0.20.1:

1. The initial provider-bound prompt contained ORBIT, CEDAR, AMBER, JADE, and VIOLET.
2. Reading backend/probe.txt added EMBER through the enriched tool result without changing the system-prompt hash.
3. Editing USER.md from AMBER to COBALT did not change the next ordinary provider-bound prompt.
4. Manual compression rebuilt the prompt with COBALT while preserving the session ID.
5. The selected recent tail survived in live memory and the next provider request.
6. The original selected-tail SQLite rows remained compacted and recoverable rather than active.

The sixth finding is a state-boundary mismatch, not data loss.

## Evidence classes

The reference validation produced 33 PASS, 1 PARTIAL, 0 FAIL, and 0 NOT VERIFIED against the pre-correction article. The PARTIAL result identified an overbroad sentence about protected recent/head boundaries. The corrected article and this lab state the narrower behavior.

## Start here

macOS or Linux:

~~~bash
bash ./scripts/initialize-lab.sh
bash ./scripts/test-lab-fixtures.sh
~~~

Windows with PowerShell 7:

~~~powershell
pwsh .\scripts\Initialize-Lab.ps1
pwsh .\scripts\Test-LabFixtures.ps1
~~~

The initializers print a unique disposable path and platform-appropriate
commands for entering the lab. CI exercises both workflows on Windows, macOS,
and Ubuntu. See the [script reference](scripts/README.md) for the command
mapping, including SHA-256 evidence manifests.

Then follow the selected track.

## Cost and safety

The Explorer track is free. Builder and Investigator provider-backed runs may consume tokens.

Never use a personal workspace, profile, memory file, or session database. Generated runs belong in an untracked runs directory.
