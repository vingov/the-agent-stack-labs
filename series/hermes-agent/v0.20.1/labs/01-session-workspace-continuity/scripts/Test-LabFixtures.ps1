[CmdletBinding()]
param(
    [string]$FixtureRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'fixtures')
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($FixtureRoot)
$task = Join-Path $root 'workspace-a\task.txt'
$fresh = Join-Path $root 'workspace-b\README.md'
$expectedHash = 'c611c2a0487875469ec6524cc04b113bf7202d9663fecd8d89b0de5efda29e3b'

if (-not (Test-Path -LiteralPath $task -PathType Leaf)) {
    throw "Missing fixture: $task"
}

if (-not (Test-Path -LiteralPath $fresh -PathType Leaf)) {
    throw "Missing fixture: $fresh"
}

if (-not (Get-Content -Raw -LiteralPath $task).Contains('HERMES-P1-LAB-2026-08-16-SESSION-CWD')) {
    throw 'Primary marker is missing from task.txt.'
}

if (-not (Get-Content -Raw -LiteralPath $fresh).Contains('HERMES-P1-FRESH-WORKSPACE')) {
    throw 'Fresh-workspace marker is missing.'
}

$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $task).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) {
    throw "Unexpected task.txt SHA-256: $actualHash"
}

$forbiddenNames = @('.env', 'auth.json', 'auth.lock', 'state.db')
$forbidden = Get-ChildItem -Recurse -Force -File -LiteralPath $root |
    Where-Object { $forbiddenNames -contains $_.Name }

if ($forbidden.Count -gt 0) {
    throw "Credential or live-state shaped file found in fixtures: $($forbidden.FullName -join ', ')"
}

Write-Host "PASS: Part 1 fixture validation passed: $root"
