#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Installs WEBSTUDIO Server as a Windows service (Automatic Delayed Start) via NSSM.
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$ServiceName = "WEBSTUDIO Server",
    [string]$NssmPath = "$InstallRoot\tools\nssm\nssm.exe",
    [string]$PythonExe = "$InstallRoot\venv\Scripts\python.exe",
    [string]$EnvFile = "$InstallRoot\config\env\.env",
    [string]$PostgresServiceName = "postgresql-x64-16"
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

if (-not (Test-Path $NssmPath)) {
    throw "NSSM not found at $NssmPath. Download NSSM and place under $InstallRoot\tools\nssm\"
}
if (-not (Test-Path $PythonExe)) {
    throw "Python venv not found at $PythonExe"
}

Write-Step "Ensuring PostgreSQL is available..."
& "$PSScriptRoot\ensure-postgresql.ps1" -PostgresServiceName $PostgresServiceName

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
Pop-Location

Write-Step "Starting WEBSTUDIO Server Service..."
Start-Service -Name $ServiceName
Write-Step "Installation complete."
