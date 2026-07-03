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

Write-Host "[release] Output: $RepoRoot\release\server\WEBSTUDIO Server Setup.exe"
