#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Wrapper for server post-install - surfaces errors instead of failing silently.
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$PostgresServiceName = ""
)

$ErrorActionPreference = "Stop"

$LogDir = Join-Path $InstallRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$LogFile = Join-Path $LogDir "install-post.log"

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

try {
    Write-Log "Starting WEBSTUDIO Server post-install..."
    $PostScript = Join-Path $PSScriptRoot "server-install-post.ps1"
    & $PostScript -InstallRoot $InstallRoot -PostgresServiceName $PostgresServiceName
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "server-install-post.ps1 exited with code $LASTEXITCODE"
    }
    Write-Log "Post-install completed successfully."
    exit 0
} catch {
    $errorText = $_.Exception.Message
    if ($_.ScriptStackTrace) {
        $errorText += "`n$($_.ScriptStackTrace)"
    }
    Write-Log "ERROR: $errorText"
    Write-Host ""
    Write-Host "WEBSTUDIO Server post-install FAILED." -ForegroundColor Red
    Write-Host $errorText -ForegroundColor Red
    Write-Host "Full log: $LogFile" -ForegroundColor Yellow
    exit 1
}
