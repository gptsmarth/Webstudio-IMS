#Requires -Version 5.1
<#
.SYNOPSIS
  Compile WEBSTUDIO Server Setup.exe via Inno Setup.
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$InnoSetupCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InnoSetupCompiler)) {
    throw "Inno Setup 6 not found at $InnoSetupCompiler. Install from https://jrsoftware.org/isinfo.php"
}

$IssFile = Join-Path $RepoRoot "infra\windows\server-installer\WEBSTUDIO-Server-Setup.iss"
& $InnoSetupCompiler $IssFile
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed with exit code $LASTEXITCODE"
}

$OutputExe = Join-Path $RepoRoot "release\server\WEBSTUDIO Server Setup.exe"
if (-not (Test-Path $OutputExe)) {
    throw "Expected installer not found at $OutputExe"
}

Write-Host "[release] Output: $OutputExe"
