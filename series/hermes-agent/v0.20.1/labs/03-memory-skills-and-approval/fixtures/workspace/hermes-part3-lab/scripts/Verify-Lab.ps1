[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$RunId
)

$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$region = 'eu-west-2'
$artifact = Join-Path $labRoot 'artifacts/site.bundle'
$staged = Join-Path $labRoot "staging/$region/site.bundle"
$expected = (Get-Content -LiteralPath (Join-Path $labRoot 'artifacts/site.bundle.sha256') -Raw).Trim()

foreach ($path in @($artifact, $staged)) {
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "Digest mismatch: $path" }
}

$dryRun = Get-Content -LiteralPath (Join-Path $labRoot "receipts/$RunId.dry-run.json") -Raw | ConvertFrom-Json
$deploy = Get-Content -LiteralPath (Join-Path $labRoot "receipts/$RunId.deploy.json") -Raw | ConvertFrom-Json
if (-not $dryRun.dry_run -or $dryRun.deployed) { throw 'Dry-run receipt is invalid.' }
if ($deploy.dry_run -or -not $deploy.deployed) { throw 'Deploy receipt is invalid.' }
foreach ($receipt in @($dryRun, $deploy)) {
    if ($receipt.marker -ne 'HERMES-P3-SKILL-LOCAL-DEPLOY-V1') { throw 'Procedure marker mismatch.' }
    if ($receipt.region -ne $region) { throw 'Region mismatch.' }
    if ($receipt.artifact_sha256 -ne $expected) { throw 'Receipt digest mismatch.' }
    if ($receipt.network_used) { throw 'Network use was reported.' }
}

'verification: pass'
"sha256=$expected"
