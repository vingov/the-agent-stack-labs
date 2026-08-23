[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Region,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$RunId,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
if ($Region -ne 'eu-west-2') {
    throw 'Region must be eu-west-2 for this synthetic fixture.'
}

$artifact = Join-Path $labRoot 'artifacts/site.bundle'
$digestFile = Join-Path $labRoot 'artifacts/site.bundle.sha256'
if (-not (Test-Path -LiteralPath $artifact) -or -not (Test-Path -LiteralPath $digestFile)) {
    throw 'Build the artifact first.'
}

$expected = (Get-Content -LiteralPath $digestFile -Raw).Trim()
$actual = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -ne $actual) {
    throw 'Artifact digest mismatch.'
}

$receiptsDir = Join-Path $labRoot 'receipts'
New-Item -ItemType Directory -Force -Path $receiptsDir | Out-Null
$mode = if ($DryRun) { 'dry-run' } else { 'deploy' }
$receiptPath = Join-Path $receiptsDir "$RunId.$mode.json"
$deployed = $false

if (-not $DryRun) {
    $dryRunReceipt = Join-Path $receiptsDir "$RunId.dry-run.json"
    if (-not (Test-Path -LiteralPath $dryRunReceipt -PathType Leaf)) {
        throw 'A matching dry-run receipt is required before deployment.'
    }
    $staging = Join-Path $labRoot "staging/$Region"
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Copy-Item -LiteralPath $artifact -Destination (Join-Path $staging 'site.bundle')
    Copy-Item -LiteralPath $digestFile -Destination (Join-Path $staging 'site.bundle.sha256')
    $deployed = $true
}

$receipt = [ordered]@{
    marker = 'HERMES-P3-SKILL-LOCAL-DEPLOY-V1'
    fact_marker = 'HERMES-P3-FACT-EU-WEST-2'
    preference_marker = 'HERMES-P3-PREF-DRY-RUN-FIRST'
    region = $Region
    artifact_sha256 = $actual
    dry_run = [bool]$DryRun
    deployed = $deployed
    run_id = $RunId
    network_used = $false
}
$receipt | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8NoBOM
"receipt=$receiptPath"
