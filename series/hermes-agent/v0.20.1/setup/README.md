# Hermes v0.20.1 lab setup

This guide prepares a disposable workspace and profile. It does not modify your
normal Hermes installation.

## 1. Verify the prerequisites

You need Git, the Python version required by the pinned Hermes release, and one
of the supported shells.

macOS or Linux:

~~~bash
bash --version
python3 --version
git --version
~~~

The repository scripts support the Bash 3.2 version included with macOS as well
as current Linux Bash releases.

Windows:

~~~powershell
$PSVersionTable.PSVersion
python --version
git --version
~~~

PowerShell 7 is recommended on Windows.

## 2. Obtain the pinned source

Use the official repository and verify the exact commit.

macOS or Linux:

~~~bash
git clone https://github.com/NousResearch/hermes-agent.git
git -C ./hermes-agent checkout --detach v2026.8.13
git -C ./hermes-agent rev-parse HEAD
~~~

Windows:

~~~powershell
git clone https://github.com/NousResearch/hermes-agent.git
git -C .\hermes-agent checkout --detach v2026.8.13
git -C .\hermes-agent rev-parse HEAD
~~~

Expected commit:

~~~text
f80f453ae0679347e38abc917c7f94f717bf96c5
~~~

Follow the installation instructions from that pinned checkout. Do not silently
substitute a newer release and report it as this pin.

## 3. Create the disposable lab

Run one initializer from the root of this repository.

macOS or Linux:

~~~bash
bash ./series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/initialize-lab.sh
~~~

Windows:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Initialize-Lab.ps1
~~~

Each run creates a uniquely named directory below the operating-system temporary
directory. The command prints the path and the exact commands for entering it.

## 4. Enter the isolated environment

Copy the two commands printed by your initializer. They will resemble these
examples.

macOS or Linux:

~~~bash
export HERMES_HOME='<temporary-lab-path>/profile'
cd '<temporary-lab-path>/workspace'
~~~

Windows:

~~~powershell
$env:HERMES_HOME = '<temporary-lab-path>\profile'
Set-Location '<temporary-lab-path>\workspace'
~~~

Before starting Hermes, confirm that HERMES_HOME points at the disposable
profile directory and not your normal profile.

## 5. Authenticate only for the live track

The reference run used Hermes' supported OpenAI Codex authentication flow:

~~~text
hermes auth login openai-codex
hermes auth status openai-codex
~~~

Those Hermes commands are the same in PowerShell and Bash. Authentication is
optional for Explorer. Never copy an auth file into a result submission.

## 6. Verify the fixtures

macOS or Linux:

~~~bash
bash ./series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/test-lab-fixtures.sh
~~~

Windows:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Test-LabFixtures.ps1
~~~

Then continue with the [Builder track](../labs/02-context-and-compression/builder.md).

## Important installer caution

During the original Windows validation, one pinned config-template stage spawned
a skill-sync child process that did not respect the isolated HERMES_HOME. The
protected normal profile was restored and verified. The public initializers
therefore prepare fixtures only and do not automate the Hermes installer.

This exact installer side effect has not been reproduced on macOS or Linux. On
every platform, fingerprint your normal profile before testing installer
behavior, or use a disposable machine, container, or VM.
