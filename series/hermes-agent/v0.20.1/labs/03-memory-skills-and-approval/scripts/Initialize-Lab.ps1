[CmdletBinding()]
param(
    [string]$Destination
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Destination)) {
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $Destination = Join-Path ([IO.Path]::GetTempPath()) "the-agent-stack-hermes-03-$suffix"
}

$labSource = Split-Path -Parent $PSScriptRoot
$fixtures = Join-Path $labSource 'fixtures'
$resolvedDestination = [IO.Path]::GetFullPath($Destination)
$userHome = [IO.Path]::GetFullPath([Environment]::GetFolderPath('UserProfile')).TrimEnd('\', '/')
$driveRoot = [IO.Path]::GetPathRoot($resolvedDestination).TrimEnd('\', '/')
$normalHermesCandidates = @(
    (Join-Path $userHome '.hermes'),
    (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'hermes')
)

if ($resolvedDestination.TrimEnd('\', '/') -in @($userHome, $driveRoot)) {
    throw "Refusing unsafe destination: $resolvedDestination"
}
foreach ($candidate in $normalHermesCandidates) {
    if ($resolvedDestination.StartsWith($candidate, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to create the lab inside a normal Hermes profile: $resolvedDestination"
    }
}

if (Test-Path -LiteralPath $resolvedDestination) {
    if ((Get-ChildItem -Force -LiteralPath $resolvedDestination).Count -gt 0) {
        throw "Destination already exists and is not empty: $resolvedDestination"
    }
} else {
    New-Item -ItemType Directory -Path $resolvedDestination | Out-Null
}

Copy-Item -LiteralPath (Join-Path $fixtures 'workspace') -Destination $resolvedDestination -Recurse
Copy-Item -LiteralPath (Join-Path $fixtures 'profile') -Destination $resolvedDestination -Recurse
New-Item -ItemType Directory -Force -Path (Join-Path $resolvedDestination 'evidence') | Out-Null

$workspace = Join-Path $resolvedDestination 'workspace/hermes-part3-lab'
$profile = Join-Path $resolvedDestination 'profile'

Write-Host ''
Write-Host 'Hermes Part 3 lab created safely.'
Write-Host "Lab root: $resolvedDestination"
Write-Host "Workspace: $workspace"
Write-Host "Profile: $profile"
Write-Host ''
Write-Host 'For a provider-backed Builder run, use these commands in the same PowerShell session:'
Write-Host ('$env:HERMES_HOME = ' + "'$profile'")
Write-Host ("Set-Location '$workspace'")
Write-Host ''
Write-Host 'The Explorer track can run the fixture scripts without Hermes or a provider.'
