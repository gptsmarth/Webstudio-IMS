#Requires -Version 5.1
<#
.SYNOPSIS
  Copy config/env/.env to apps/backend after manual .env edits.
.DESCRIPTION
  Repairs production .env (POSTGRES_BIN, DATABASE_URL localhost fix, etc.) and copies
  the file to apps\backend\.env and apps\backend\config\env\.env so the Python API
  loads the same values as the Windows service.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File D:\WEBSTUDIO-IMS\infra\windows\sync-backend-env.ps1
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [switch]$RestartService
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\webstudio-env.ps1"

$envFile = Join-Path $InstallRoot "config\env\.env"
if (-not (Test-Path $envFile)) {
    throw "Missing production env file: $envFile"
}

Write-Host "[WEBSTUDIO] Repairing config\env\.env..."
Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $envFile
Write-Host "[WEBSTUDIO] Synced to apps\backend\.env and apps\backend\config\env\.env"

if ($RestartService) {
    $service = Get-Service -Name "WEBSTUDIO Server" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "[WEBSTUDIO] Restarting WEBSTUDIO Server..."
        Apply-NssmServiceEnvironment -InstallRoot $InstallRoot
        Restart-Service -Name "WEBSTUDIO Server"
    } else {
        Write-Host "[WEBSTUDIO] WEBSTUDIO Server service not found — restart manually after install." -ForegroundColor Yellow
    }
} else {
    Write-Host "[WEBSTUDIO] Run finalize-server-setup.ps1 or pass -RestartService to apply to the running service."
}
