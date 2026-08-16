[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Root,

    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = [System.IO.Path]::GetFullPath($Root)
$userHome = [System.IO.Path]::GetFullPath([Environment]::GetFolderPath('UserProfile')).TrimEnd('\', '/')
$driveRoot = [System.IO.Path]::GetPathRoot($resolvedRoot).TrimEnd('\', '/')
$normalizedRoot = $resolvedRoot.TrimEnd('\', '/')

if ($normalizedRoot -eq $userHome -or $normalizedRoot -eq $driveRoot) {
    throw "Refusing broad manifest root: $resolvedRoot"
}

if (-not (Test-Path -LiteralPath $resolvedRoot -PathType Container)) {
    throw "Manifest root does not exist: $resolvedRoot"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path $resolvedRoot 'SHA256SUMS.txt'
}

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$files = Get-ChildItem -Recurse -File -LiteralPath $resolvedRoot |
    Where-Object { $_.FullName -ne $resolvedOutput } |
    Sort-Object FullName

$lines = foreach ($file in $files) {
    $relative = [System.IO.Path]::GetRelativePath($resolvedRoot, $file.FullName).Replace('\', '/')
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName
    $hash.Hash.ToLowerInvariant() + [char]9 + $relative
}

Set-Content -LiteralPath $resolvedOutput -Value $lines -Encoding utf8NoBOM
Write-Host "Wrote $($lines.Count) SHA256 entries to $resolvedOutput"
