[CmdletBinding()]
param(
    [string]$FixtureRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'fixtures/workspace'),
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$fixtureRootPath = [IO.Path]::GetFullPath($FixtureRoot)
$artifact = Join-Path $fixtureRootPath 'input/artifact.txt'
$policyPath = Join-Path $fixtureRootPath 'policy/policy-v2.json'
$procedure = Join-Path $fixtureRootPath 'procedures/HERMES-P4-PROCEDURE-V2.md'

foreach ($required in @($artifact, $policyPath, $procedure)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing fixture: $required"
    }
}

if ((Get-Item -LiteralPath $artifact).Length -ne 91) {
    throw 'artifact.txt must remain exactly 91 bytes.'
}

$policy = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json
$actualHash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
if ($policy.required_sha256 -ne $actualHash) {
    throw "Policy hash mismatch: expected $($policy.required_sha256), got $actualHash"
}
if ($policy.required_procedure -ne 'HERMES-P4-PROCEDURE-V2') {
    throw 'Unexpected required procedure.'
}
if ($policy.allowed_output -ne 'state/deployed/artifact.txt') {
    throw 'Unexpected allowed output path.'
}

if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
}
& $PythonPath -m py_compile (Join-Path $PSScriptRoot 'run_contract.py') (Join-Path $PSScriptRoot 'run_controls.py') (Join-Path $PSScriptRoot 'verify_operation.py') (Join-Path $PSScriptRoot 'seed_goal.py') (Join-Path $PSScriptRoot 'render_commands.py') (Join-Path $PSScriptRoot 'run_plugin_probe.py')
if ($LASTEXITCODE -ne 0) {
    throw 'Python fixture compilation failed.'
}

Write-Output 'Part 4 fixtures: PASS'
