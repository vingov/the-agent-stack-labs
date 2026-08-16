[CmdletBinding()]
param(
    [string]$Destination
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Destination)) {
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $Destination = Join-Path ([System.IO.Path]::GetTempPath()) "the-agent-stack-hermes-02-$suffix"
}

$labSource = Split-Path -Parent $PSScriptRoot
$fixtures = Join-Path $labSource 'fixtures'
$resolvedDestination = [System.IO.Path]::GetFullPath($Destination)
$userHome = [System.IO.Path]::GetFullPath([Environment]::GetFolderPath('UserProfile')).TrimEnd('\', '/')
$driveRoot = [System.IO.Path]::GetPathRoot($resolvedDestination).TrimEnd('\', '/')
$normalizedDestination = $resolvedDestination.TrimEnd('\', '/')
$normalHermes = Join-Path $userHome '.hermes'

if ($normalizedDestination -eq $userHome -or $normalizedDestination -eq $driveRoot) {
    throw "Refusing unsafe destination: $resolvedDestination"
}

if ($normalizedDestination.StartsWith($normalHermes, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create the lab inside the normal Hermes profile: $resolvedDestination"
}

if (Test-Path -LiteralPath $resolvedDestination) {
    $existing = Get-ChildItem -Force -LiteralPath $resolvedDestination
    if ($existing.Count -gt 0) {
        throw "Destination already exists and is not empty: $resolvedDestination"
    }
} else {
    New-Item -ItemType Directory -Path $resolvedDestination | Out-Null
}

Copy-Item -LiteralPath (Join-Path $fixtures 'workspace') -Destination $resolvedDestination -Recurse
Copy-Item -LiteralPath (Join-Path $fixtures 'profile') -Destination $resolvedDestination -Recurse

foreach ($name in @('evidence', 'logs', 'runs')) {
    New-Item -ItemType Directory -Path (Join-Path $resolvedDestination $name) -Force | Out-Null
}

$workspace = Join-Path $resolvedDestination 'workspace'
$profile = Join-Path $resolvedDestination 'profile'

git -C $workspace init | Out-Null
git -C $workspace config user.name 'The Agent Stack Lab'
git -C $workspace config user.email 'lab@example.invalid'
git -C $workspace add AGENTS.md README.md backend/AGENTS.md backend/probe.txt
git -C $workspace commit -m 'Create synthetic Hermes context fixture' | Out-Null

Write-Host ''
Write-Host 'Hermes context lab created safely.'
Write-Host "Lab root: $resolvedDestination"
Write-Host "Workspace: $workspace"
Write-Host "Profile: $profile"
Write-Host ''
Write-Host 'Run these commands in the PowerShell session used for Hermes:'
Write-Host ('$env:HERMES_HOME = ' + "'" + $profile + "'")
Write-Host ("Set-Location '" + $workspace + "'")
