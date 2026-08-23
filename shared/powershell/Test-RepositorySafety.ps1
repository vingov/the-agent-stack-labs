[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$files = Get-ChildItem -Recurse -Force -File -LiteralPath $repositoryRoot |
    Where-Object {
        $relativeParts = [System.IO.Path]::GetRelativePath($repositoryRoot, $_.FullName) -split '[\\/]'
        $_.FullName -notmatch '[\\/]\.git[\\/]' -and -not ($relativeParts -contains 'runs')
    }

$findings = [System.Collections.Generic.List[string]]::new()
$forbiddenNames = @(
    '.env',
    'auth.json',
    'auth.lock',
    'cookies.json',
    'state.db'
)

foreach ($file in $files) {
    if ($forbiddenNames -contains $file.Name) {
        $findings.Add("Forbidden filename: $($file.FullName)")
    }
}

$textExtensions = @('.md', '.txt', '.json', '.yaml', '.yml', '.ps1', '.sh', '.py', '.toml')
$patterns = @(
    @{ Name = 'Private key'; Regex = '-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----' },
    @{ Name = 'GitHub token'; Regex = 'gh[pousr]_[A-Za-z0-9]{20,}' },
    @{ Name = 'Bearer credential'; Regex = '(?i)Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]{16,}' },
    @{ Name = 'Assigned secret'; Regex = '(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\s*[:=]\s*[''"]?[A-Za-z0-9._-]{16,}' },
    @{ Name = 'Windows home path'; Regex = '(?i)[A-Z]:\\Users\\[^\\\s]+' }
)

foreach ($file in $files | Where-Object { $textExtensions -contains $_.Extension.ToLowerInvariant() }) {
    $content = Get-Content -Raw -LiteralPath $file.FullName
    foreach ($pattern in $patterns) {
        if ($content -match $pattern.Regex) {
            $relative = [System.IO.Path]::GetRelativePath($repositoryRoot, $file.FullName)
            $findings.Add("$($pattern.Name) pattern in $relative")
        }
    }
}

$required = @(
    'README.md',
    'COURSE_MAP.md',
    'SECURITY.md',
    'catalog/labs.yaml',
    'shared/python/test_repository_safety.py',
    'series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/lab.yaml',
    'series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/initialize-lab.sh',
    'series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/run-storage-probe.py',
    'series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/reference-results/windows-2026-08-16/result.json',
    'series/hermes-agent/v0.20.1/labs/02-context-and-compression/lab.yaml',
    'series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/initialize-lab.sh',
    'series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/test-lab-fixtures.sh',
    'series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/new-sha256-manifest.sh',
    'series/hermes-agent/v0.20.1/labs/02-context-and-compression/reference-results/windows-2026-08-15/result.json',
    'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/lab.yaml',
    'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/Initialize-Lab.ps1',
    'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/initialize-lab.sh',
    'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/scripts/test-lab-fixtures.sh',
    'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/reference-results/windows-2026-08-23/result.json'
)

foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $repositoryRoot $relative) -PathType Leaf)) {
        $findings.Add("Required file missing: $relative")
    }
}

$resultPath = Join-Path $repositoryRoot 'series/hermes-agent/v0.20.1/labs/02-context-and-compression/reference-results/windows-2026-08-15/result.json'
if (Test-Path -LiteralPath $resultPath) {
    try {
        $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
        if ($result.lab_id -ne 'hermes-02-context-compression') {
            $findings.Add('Reference result has an unexpected lab_id.')
        }
        if ($result.contains_credentials -ne $false) {
            $findings.Add('Reference result does not explicitly declare contains_credentials=false.')
        }
    } catch {
        $findings.Add("Reference result is not valid JSON: $($_.Exception.Message)")
    }
}

$part1ResultPath = Join-Path $repositoryRoot 'series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/reference-results/windows-2026-08-16/result.json'
if (Test-Path -LiteralPath $part1ResultPath) {
    try {
        $part1Result = Get-Content -Raw -LiteralPath $part1ResultPath | ConvertFrom-Json
        if ($part1Result.lab_id -ne 'hermes-01-session-workspace') {
            $findings.Add('Part 1 reference result has an unexpected lab_id.')
        }
        if ($part1Result.evidence_boundary.contains_credentials -ne $false) {
            $findings.Add('Part 1 result does not declare contains_credentials=false.')
        }
        if ($part1Result.evidence_boundary.contains_absolute_paths -ne $false) {
            $findings.Add('Part 1 result does not declare contains_absolute_paths=false.')
        }
    } catch {
        $findings.Add("Part 1 reference result is not valid JSON: $($_.Exception.Message)")
    }
}

$part3ResultPath = Join-Path $repositoryRoot 'series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/reference-results/windows-2026-08-23/result.json'
if (Test-Path -LiteralPath $part3ResultPath) {
    try {
        $part3Result = Get-Content -Raw -LiteralPath $part3ResultPath | ConvertFrom-Json
        if ($part3Result.lab_id -ne 'hermes-03-memory-skills-approval') {
            $findings.Add('Part 3 reference result has an unexpected lab_id.')
        }
        if ($part3Result.evidence_boundary.contains_credentials -ne $false) {
            $findings.Add('Part 3 result does not declare contains_credentials=false.')
        }
        if ($part3Result.evidence_boundary.contains_absolute_paths -ne $false) {
            $findings.Add('Part 3 result does not declare contains_absolute_paths=false.')
        }
    } catch {
        $findings.Add("Part 3 reference result is not valid JSON: $($_.Exception.Message)")
    }
}

if ($findings.Count -gt 0) {
    $findings | Sort-Object -Unique | ForEach-Object { Write-Error $_ }
    throw "Repository safety validation failed with $($findings.Count) finding(s)."
}

Write-Host "PASS: scanned $($files.Count) repository files; no forbidden state or credential patterns found."
