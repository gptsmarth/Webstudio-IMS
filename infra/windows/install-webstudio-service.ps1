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
    [string]$EnvFile = "$InstallRoot\config\env\.env",
    [string]$PostgresServiceName = ""
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
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

$resolvedPostgres = & "$PSScriptRoot\resolve-postgresql-service.ps1" -PostgresServiceName $PostgresServiceName

Write-Step "Ensuring PostgreSQL is available..."
& "$PSScriptRoot\ensure-postgresql.ps1" -PostgresServiceName $resolvedPostgres

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
& $NssmPath set $ServiceName Description "WEBSTUDIO IMS API — business-hours inventory server"
& $NssmPath set $ServiceName Start SERVICE_DELAYED_AUTO_START
& $NssmPath set $ServiceName AppEnvironmentExtra "APP_ENV=production" "WEBSTUDIO_DATA_ROOT=$InstallRoot" "WEBSTUDIO_TALLY_SCHEDULER=1" "WEBSTUDIO_BACKUP_SCHEDULER=1" "WEBSTUDIO_NOTIFICATION_SCHEDULER=1" "WEBSTUDIO_MAINTENANCE_SCHEDULER=1"
& $NssmPath set $ServiceName AppStdout "$InstallRoot\logs\webstudio-api.log"
& $NssmPath set $ServiceName AppStderr "$InstallRoot\logs\webstudio-api-error.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppRestartDelay 5000

Write-Step "Configuring service recovery (restart on failure)..."
& "$PSScriptRoot\configure-service-recovery.ps1" -ServiceName $ServiceName

Write-Step "Running database migrations..."
Push-Location "$InstallRoot\apps\backend"
& $PythonExe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "Alembic migration failed with exit code $LASTEXITCODE"
}
Pop-Location

Write-Step "Starting WEBSTUDIO Server Service..."
Start-Service -Name $ServiceName
Write-Step "Installation complete."
