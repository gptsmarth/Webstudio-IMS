#Requires -Version 5.1
<#
.SYNOPSIS
  Stage server payload and compile WEBSTUDIO Server Setup.exe via Inno Setup.
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$InnoSetupCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    [switch]$SkipPayloadStaging
)

$ErrorActionPreference = "Stop"

if (-not $SkipPayloadStaging) {
    & (Join-Path $PSScriptRoot "stage-server-payload.ps1") -RepoRoot $RepoRoot
}

$StagingRuntime = Join-Path $RepoRoot "release\server\staging\runtime\python\python.exe"
$StagingNssm = Join-Path $RepoRoot "release\server\staging\tools\nssm\nssm.exe"
if (-not (Test-Path $StagingRuntime)) {
    throw "Missing staged Python runtime at $StagingRuntime. Run stage-server-payload.ps1 first."
}
if (-not (Test-Path $StagingNssm)) {
    throw "Missing staged NSSM at $StagingNssm. Run stage-server-payload.ps1 first."
}

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
