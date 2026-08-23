[CmdletBinding()]
param(
    [string]$FixtureRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'fixtures')
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($FixtureRoot)
$failures = [Collections.Generic.List[string]]::new()
$checks = @(
    @{ Path = 'profile/SOUL.md'; Markers = @('HERMES-P3-SOUL-ISOLATED') },
    @{ Path = 'profile/config.yaml'; Markers = @('write_approval: true') },
    @{ Path = 'workspace/hermes-part3-lab/app/index.html'; Markers = @('HERMES-P3-SKILL-LOCAL-DEPLOY-V1') },
    @{ Path = 'workspace/hermes-part3-lab/scripts/Deploy-Local.ps1'; Markers = @('network_used', 'dry-run receipt') }
)

foreach ($check in $checks) {
    $path = Join-Path $root $check.Path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Missing fixture: $($check.Path)")
        continue
    }
    $content = Get-Content -LiteralPath $path -Raw
    foreach ($marker in $check.Markers) {
        if (-not $content.Contains($marker)) { $failures.Add("Marker $marker missing from $($check.Path)") }
    }
}

$forbiddenNames = @('.env', 'auth.json', 'auth.lock', 'cookies.json', 'state.db')
foreach ($file in (Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object { $forbiddenNames -contains $_.Name })) {
    $failures.Add("Forbidden fixture file: $($file.FullName)")
}
if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    throw "Fixture validation failed with $($failures.Count) problem(s)."
}

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) "the-agent-stack-hermes-03-test-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
try {
    Copy-Item -LiteralPath (Join-Path $root 'workspace/hermes-part3-lab') -Destination $temporaryRoot -Recurse
    & (Join-Path $temporaryRoot 'scripts/Test-Lab.ps1')
    & (Join-Path $temporaryRoot 'scripts/Build-Lab.ps1')
    & (Join-Path $temporaryRoot 'scripts/Deploy-Local.ps1') -Region eu-west-2 -RunId P3-CI-0001 -DryRun
    & (Join-Path $temporaryRoot 'scripts/Deploy-Local.ps1') -Region eu-west-2 -RunId P3-CI-0001
    & (Join-Path $temporaryRoot 'scripts/Verify-Lab.ps1') -RunId P3-CI-0001
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}

Write-Host "PASS: $($checks.Count) fixture checks and the network-free PowerShell workflow completed."
