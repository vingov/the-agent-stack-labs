# Explorer track

**Time:** 20–30 minutes

**Provider account:** Not required

## Objective

Observe session identity, workspace binding, and transcript isolation through a
disposable Hermes database and the installed sessions CLI.

## 1. Create the lab

Use the macOS/Linux or Windows initializer in the [lab README](README.md), then
run the environment commands it prints.

## 2. Verify the deterministic fixture

The expected task marker is:

~~~text
HERMES-P1-LAB-2026-08-16-SESSION-CWD
~~~

Its SHA-256 digest, including the trailing newline, is:

~~~text
c611c2a0487875469ec6524cc04b113bf7202d9663fecd8d89b0de5efda29e3b
~~~

macOS or Linux:

~~~bash
bash ./series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/test-lab-fixtures.sh
~~~

Windows:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\01-session-workspace-continuity\scripts\Test-LabFixtures.ps1
~~~

## 3. Run the provider-free probe

macOS or Linux:

~~~bash
bash ./series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/run-storage-probe.sh
~~~

Windows:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\01-session-workspace-continuity\scripts\Run-StorageProbe.ps1
~~~

The probe creates two synthetic CLI sessions through the installed Hermes
storage implementation, exercises the installed `hermes sessions list` and
redacted export commands, and writes evidence/storage-result.json.

## 4. Explain the result

Answer these questions from the JSON rather than from a model response:

1. Which object distinguishes the conversations?
2. Which field binds each conversation to its workspace?
3. Which transcript contains the task marker?
4. What evidence proves that workspace filtering is not transcript merging?
5. Which Part 1 boundaries remain untested?

Compare your answers with the [claim matrix](expected/claim-matrix.md).
