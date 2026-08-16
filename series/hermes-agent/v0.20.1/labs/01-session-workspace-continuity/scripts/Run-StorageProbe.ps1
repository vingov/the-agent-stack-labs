[CmdletBinding()]
param(
    [string]$LabRoot = $env:PART1_LAB_ROOT,
    [string]$HermesSource,
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($LabRoot)) {
    throw 'Set PART1_LAB_ROOT or pass -LabRoot.'
}

if ([string]::IsNullOrWhiteSpace($HermesSource)) {
    $versionText = (& hermes version 2>&1) -join [Environment]::NewLine
    $installLine = $versionText -split '\r?\n' |
        Where-Object { $_ -match '^Install directory:\s*' } |
        Select-Object -First 1
    if (-not $installLine) {
        throw 'Could not locate the active Hermes source directory.'
    }
    $HermesSource = $installLine -replace '^Install directory:\s*', ''
}

$resolvedSource = [System.IO.Path]::GetFullPath($HermesSource)
$pythonPath = Join-Path $resolvedSource 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    $pythonPath = Join-Path $resolvedSource '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Could not locate the Python environment for: $resolvedSource"
}

$resolvedRoot = [System.IO.Path]::GetFullPath($LabRoot)
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $resolvedRoot 'evidence\storage-result.json'
}

$probeArguments = @(
    (Join-Path $PSScriptRoot 'run-storage-probe.py'),
    '--lab-root',
    $resolvedRoot,
    '--hermes-source',
    $resolvedSource,
    '--output',
    ([System.IO.Path]::GetFullPath($OutputPath))
)
& $pythonPath @probeArguments

if ($LASTEXITCODE -ne 0) {
    throw "The Part 1 storage probe failed with exit code $LASTEXITCODE."
}

Write-Host "Sanitized result written to: $OutputPath"
