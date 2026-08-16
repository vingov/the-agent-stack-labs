[CmdletBinding()]
param(
    [string]$FixtureRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'fixtures')
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($FixtureRoot)

$checks = @(
    @{ Path = 'workspace/AGENTS.md'; Markers = @('CEDAR') },
    @{ Path = 'workspace/backend/AGENTS.md'; Markers = @('EMBER') },
    @{ Path = 'workspace/backend/probe.txt'; Markers = @('probe') },
    @{ Path = 'profile/SOUL.md'; Markers = @('ORBIT') },
    @{ Path = 'profile/memories/USER.md'; Markers = @('AMBER') },
    @{ Path = 'profile/memories/MEMORY.md'; Markers = @('JADE') },
    @{ Path = 'profile/skills/context-probe/SKILL.md'; Markers = @('VIOLET', 'INDIGO') }
)

$failures = [System.Collections.Generic.List[string]]::new()

foreach ($check in $checks) {
    $path = Join-Path $root $check.Path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Missing fixture: $($check.Path)")
        continue
    }

    $content = Get-Content -Raw -LiteralPath $path
    foreach ($marker in $check.Markers) {
        if (-not $content.Contains($marker)) {
            $failures.Add("Marker $marker missing from $($check.Path)")
        }
    }
}

$forbiddenNames = @('.env', 'auth.json', 'auth.lock', 'cookies.json', 'state.db')
$forbiddenFiles = Get-ChildItem -Recurse -Force -File -LiteralPath $root |
    Where-Object { $forbiddenNames -contains $_.Name }

foreach ($file in $forbiddenFiles) {
    $failures.Add("Forbidden fixture file: $($file.FullName)")
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    throw "Fixture validation failed with $($failures.Count) problem(s)."
}

Write-Host "PASS: $($checks.Count) fixture checks completed with synthetic data only."
