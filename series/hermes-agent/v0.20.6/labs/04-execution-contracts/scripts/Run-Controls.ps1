[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Workspace,
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
}
& $PythonPath (Join-Path $PSScriptRoot 'run_controls.py') --workspace ([IO.Path]::GetFullPath($Workspace))
if ($LASTEXITCODE -ne 0) {
    throw "Part 4 controls failed with exit code $LASTEXITCODE"
}
