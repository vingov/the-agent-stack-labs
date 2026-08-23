[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$page = Join-Path $labRoot 'app/index.html'

if (-not (Test-Path -LiteralPath $page -PathType Leaf)) {
    throw "Missing fixture: $page"
}

$content = Get-Content -LiteralPath $page -Raw
if (-not $content.Contains('HERMES-P3-SKILL-LOCAL-DEPLOY-V1')) {
    throw 'Procedure marker is missing.'
}
if ($content -match '(?i)https?://|\bcurl\b|\bwget\b|\bssh\b|\bscp\b') {
    throw 'Unexpected network-shaped content.'
}

'tests: pass'
