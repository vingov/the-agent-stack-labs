[CmdletBinding()]
param(
    [string]$Destination
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Destination)) {
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $Destination = Join-Path ([System.IO.Path]::GetTempPath()) "the-agent-stack-hermes-01-$suffix"
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

foreach ($name in @('profile', 'evidence', 'runs')) {
    New-Item -ItemType Directory -Path (Join-Path $resolvedDestination $name) -Force | Out-Null
}

Copy-Item -LiteralPath (Join-Path $fixtures 'workspace-a') -Destination $resolvedDestination -Recurse
Copy-Item -LiteralPath (Join-Path $fixtures 'workspace-b') -Destination $resolvedDestination -Recurse

$profile = Join-Path $resolvedDestination 'profile'
$workspace = Join-Path $resolvedDestination 'workspace-a'

Write-Host ''
Write-Host 'Disposable Part 1 lab created safely.'
Write-Host "Lab root: $resolvedDestination"
Write-Host "Profile: $profile"
Write-Host "Primary workspace: $workspace"
Write-Host ''
Write-Host 'Run these commands in the PowerShell session used for Hermes:'
Write-Host ('$env:PART1_LAB_ROOT = ' + "'" + $resolvedDestination + "'")
Write-Host ('$env:HERMES_HOME = ' + "'" + $profile + "'")
Write-Host ("Set-Location '" + $workspace + "'")
