# Builder track

**Time:** 60–90 minutes
**Provider account:** Optional for setup; required for a live model run

## 1. Prepare the disposable lab

From the repository root:

~~~powershell
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Initialize-Lab.ps1
~~~

Set the variables printed by the script:

~~~powershell
$labRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'the-agent-stack-hermes-02'
$env:HERMES_HOME = Join-Path $labRoot 'profile'
Set-Location (Join-Path $labRoot 'workspace')
~~~

Verify that the normal profile is not in scope.

## 2. Record the pin and environment

~~~powershell
hermes --version
python --version
git --version
$PSVersionTable.PSVersion
~~~

If using a pinned checkout:

~~~powershell
git -C <path-to-hermes-source> rev-parse HEAD
~~~

Expected commit:

~~~text
f80f453ae0679347e38abc917c7f94f717bf96c5
~~~

## 3. Capture the baseline

Start a fresh Hermes session in the synthetic workspace. Run:

~~~text
/status
/context
/context all
~~~

Then send:

~~~text
Do not read files, do not call tools, and do not search the filesystem.
Return only synthetic marker words explicitly present in your current context
from this list:
ORBIT, CEDAR, EMBER, AMBER, COBALT, JADE, VIOLET, INDIGO.
If you cannot establish a marker, omit it.
~~~

A model response is supporting evidence only. Record available prompt, request, context-inspector, or session artifacts separately.

## 4. Trigger progressive context discovery

Ask Hermes:

~~~text
Read backend/probe.txt with the read_file tool and report only its file content.
~~~

Inspect the tool result for EMBER. Check whether the system-prompt digest changed.

## 5. Cross the profile snapshot boundary

In another PowerShell window, edit only the disposable profile:

~~~powershell
$profileUser = Join-Path $env:HERMES_HOME 'memories\USER.md'
Set-Content -LiteralPath $profileUser -Value 'COBALT' -Encoding utf8NoBOM
Get-FileHash -Algorithm SHA256 -LiteralPath $profileUser
~~~

Return to the same session and send:

~~~text
Without reading USER.md or using filesystem tools, report only which one of
AMBER or COBALT is currently supplied as user-profile context.
~~~

Do not treat the answer alone as proof. Inspect the prompt or provider-bound request if instrumentation exposes it.

## 6. Load the full skill

Ask Hermes to use skill_view for context-probe. Verify that INDIGO arrives through the tool-result/history path while VIOLET was already present in skill metadata.

## 7. Build bounded synthetic history

Add eight short turns containing TEST_FACT_01 through TEST_FACT_08. Keep the experiment free of private data.

## 8. Compress

Verify the command from the pinned CLI, then run:

~~~text
/compress here 2
~~~

Capture before and after:

- session ID
- prompt digest and marker presence
- live message count
- active and compacted SQLite counts, if safely observable
- next provider request marker presence
- provider cache-read and cache-write metrics, if available

## 9. Compare with the reference

Use [expected/claim-matrix.md](expected/claim-matrix.md).

A different result is valuable. Record the pin, operating system, provider, model, and evidence boundary before opening a Lab result issue.
