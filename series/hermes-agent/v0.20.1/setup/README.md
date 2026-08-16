# Hermes v0.20.1 lab setup

This guide prepares a disposable workspace and profile. It does not modify your normal Hermes installation.

## 1. Verify PowerShell and Git

~~~powershell
$PSVersionTable.PSVersion
git --version
~~~

PowerShell 7 is recommended.

## 2. Obtain the pinned source

Use the official repository and verify the exact commit.

~~~powershell
git clone https://github.com/NousResearch/hermes-agent.git
git -C .\hermes-agent checkout --detach v2026.8.13
git -C .\hermes-agent rev-parse HEAD
~~~

Expected commit:

~~~text
f80f453ae0679347e38abc917c7f94f717bf96c5
~~~

Follow the installation instructions from the pinned checkout. Do not silently substitute a newer release and report it as this pin.

## 3. Create the disposable lab

From the root of this repository:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Initialize-Lab.ps1
~~~

The command prints the generated path. The default location is under the operating-system temporary directory.

## 4. Enter the isolated environment

~~~powershell
$labRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'the-agent-stack-hermes-02'
$env:HERMES_HOME = Join-Path $labRoot 'profile'
Set-Location (Join-Path $labRoot 'workspace')
~~~

Confirm that HERMES_HOME points at the disposable lab, not your normal profile.

## 5. Authenticate only for the live track

The reference run used Hermes' supported OpenAI Codex authentication flow:

~~~powershell
hermes auth login openai-codex
hermes auth status openai-codex
~~~

Authentication is optional for Explorer. Never copy an auth file into a result submission.

## 6. Verify the fixtures

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Test-LabFixtures.ps1
~~~

Then continue with the [Builder track](../labs/02-context-and-compression/builder.md).

## Important installer caution

During the original Windows validation, one pinned config-template stage spawned a skill-sync child process that did not respect the isolated HERMES_HOME. The protected normal profile was restored and verified. The public initializer therefore prepares fixtures only and does not automate the Hermes installer.

Fingerprint your normal profile before testing installer behavior, or use a disposable machine or VM.
