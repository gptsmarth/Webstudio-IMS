#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Installs WEBSTUDIO Server as a Windows service (Automatic Delayed Start) via NSSM.
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$ServiceName = "WEBSTUDIO Server",
    [string]$NssmPath = "",
    [string]$PythonExe = "",
    [string]$EnvFile = "",
    [string]$PostgresServiceName = "",
    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\webstudio-env.ps1"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

if (-not $EnvFile) {
    $EnvFile = "$InstallRoot\config\env\.env"
}
if (-not $NssmPath) {
    $NssmPath = "$InstallRoot\tools\nssm\nssm.exe"
}
if (-not $PythonExe) {
    $PythonExe = & "$PSScriptRoot\ensure-python-runtime.ps1" -InstallRoot $InstallRoot
}

if (-not (Test-Path $NssmPath)) {
    throw "NSSM not found at $NssmPath. Re-run WEBSTUDIO Server Setup.exe from the latest release build."
}
if (-not (Test-Path $PythonExe)) {
    throw "Python runtime not found at $PythonExe"
}
if (-not (Test-Path $EnvFile)) {
    throw "Missing env file: $EnvFile"
}

$resolvedPostgres = & "$PSScriptRoot\resolve-postgresql-service.ps1" -PostgresServiceName $PostgresServiceName

Write-Step "Ensuring PostgreSQL is available..."
& "$PSScriptRoot\ensure-postgresql.ps1" -PostgresServiceName $resolvedPostgres

Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $EnvFile
Sync-BackendEnvFile -InstallRoot $InstallRoot

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Step "Removing existing service registration..."
    & $NssmPath stop $ServiceName confirm
    & $NssmPath remove $ServiceName confirm
}

Write-Step "Installing $ServiceName..."
& $NssmPath install $ServiceName $PythonExe "-m" "webstudio_backend.main"
& $NssmPath set $ServiceName AppDirectory "$InstallRoot\apps\backend"
& $NssmPath set $ServiceName DisplayName "WEBSTUDIO Server Service"
& $NssmPath set $ServiceName Description "WEBSTUDIO IMS API - business-hours inventory server"
& $NssmPath set $ServiceName Start SERVICE_DELAYED_AUTO_START
& $NssmPath set $ServiceName AppStdout "$InstallRoot\logs\webstudio-api.log"
& $NssmPath set $ServiceName AppStderr "$InstallRoot\logs\webstudio-api-error.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppRestartDelay 5000

Write-Step "Applying production environment to service..."
Apply-NssmServiceEnvironment -InstallRoot $InstallRoot -ServiceName $ServiceName -EnvFile $EnvFile -NssmPath $NssmPath

Write-Step "Configuring service recovery (restart on failure)..."
& "$PSScriptRoot\configure-service-recovery.ps1" -ServiceName $ServiceName

if (-not $SkipMigrations) {
    Write-Step "Running database migrations..."
    & "$PSScriptRoot\run-alembic-upgrade.ps1" -InstallRoot $InstallRoot -PythonExe $PythonExe
}

Write-Step "Starting WEBSTUDIO Server Service..."
Start-Service -Name $ServiceName
Write-Step "Installation complete."
