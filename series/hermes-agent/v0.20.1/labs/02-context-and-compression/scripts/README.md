# Lab script reference

The Bash workflow is the primary path for macOS and Linux readers. PowerShell 7
provides the equivalent Windows workflow.

| Task | macOS or Linux | Windows |
| --- | --- | --- |
| Create a disposable lab | initialize-lab.sh | Initialize-Lab.ps1 |
| Validate synthetic fixtures | test-lab-fixtures.sh | Test-LabFixtures.ps1 |
| Create a SHA-256 manifest | new-sha256-manifest.sh | New-SHA256Manifest.ps1 |

Run the scripts from the repository root.

## macOS or Linux

~~~bash
lab=./series/hermes-agent/v0.20.1/labs/02-context-and-compression
bash "$lab/scripts/initialize-lab.sh"
bash "$lab/scripts/test-lab-fixtures.sh"
bash "$lab/scripts/new-sha256-manifest.sh" <evidence-directory>
~~~

The manifest script automatically uses sha256sum on Linux or shasum on macOS.

## Windows

~~~powershell
$lab = '.\series\hermes-agent\v0.20.1\labs\02-context-and-compression'
pwsh "$lab\scripts\Initialize-Lab.ps1"
pwsh "$lab\scripts\Test-LabFixtures.ps1"
pwsh "$lab\scripts\New-SHA256Manifest.ps1" -Root <evidence-directory>
~~~

All initializers refuse broad or real-profile targets, create synthetic data
only, and leave authentication to the user-controlled live track.
