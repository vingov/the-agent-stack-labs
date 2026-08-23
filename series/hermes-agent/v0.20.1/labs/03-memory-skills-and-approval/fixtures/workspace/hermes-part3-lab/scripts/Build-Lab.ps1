[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$labRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $labRoot 'app/index.html'
$artifactDir = Join-Path $labRoot 'artifacts'
$artifact = Join-Path $artifactDir 'site.bundle'
$digestFile = Join-Path $artifactDir 'site.bundle.sha256'

New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$body = (Get-Content -LiteralPath $source -Raw).Replace("`r`n", "`n").TrimEnd()
$payload = "HERMES-P3-SKILL-LOCAL-DEPLOY-V1`npath=app/index.html`n$body`n"
[IO.File]::WriteAllText($artifact, $payload, [Text.UTF8Encoding]::new($false))
$digest = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($digestFile, "$digest`n", [Text.UTF8Encoding]::new($false))

"artifact=$artifact"
"sha256=$digest"
