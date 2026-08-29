[CmdletBinding()]
param(
    [string]$Destination
)

$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$fixtureRoot = Join-Path $labRoot 'fixtures/workspace'

if (-not $Destination) {
    $Destination = Join-Path ([IO.Path]::GetTempPath()) ("hermes-part4-lab-{0}" -f [guid]::NewGuid().ToString('N'))
}

$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationPath) {
    $existing = Get-ChildItem -LiteralPath $destinationPath -Force -ErrorAction SilentlyContinue
    if ($existing) {
        throw "Destination must be new or empty: $destinationPath"
    }
}

New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
Copy-Item -Path (Join-Path $fixtureRoot '*') -Destination $destinationPath -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $destinationPath 'bin') | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'run_contract.py') -Destination (Join-Path $destinationPath 'bin/run_contract.py')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'verify_operation.py') -Destination (Join-Path $destinationPath 'bin/verify_operation.py')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'seed_goal.py') -Destination (Join-Path $destinationPath 'bin/seed_goal.py')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'render_commands.py') -Destination (Join-Path $destinationPath 'bin/render_commands.py')

Write-Output $destinationPath
