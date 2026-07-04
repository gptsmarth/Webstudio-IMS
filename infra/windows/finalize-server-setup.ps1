#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Complete WEBSTUDIO Server setup after editing config/env/.env (or when post-install prompts for DB password).
.DESCRIPTION
  Syncs .env, runs Alembic migrations, applies NSSM environment, and restarts the WEBSTUDIO Server service.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [switch]$PromptForDatabasePassword
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\webstudio-env.ps1"

function Write-Step([string]$Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

$envFile = Join-Path $InstallRoot "config\env\.env"
if (-not (Test-Path $envFile)) {
    throw "Missing $envFile - run WEBSTUDIO Server Setup.exe first."
}

Write-Step "Configuring database connection..."
if ($PromptForDatabasePassword) {
    Ensure-DatabaseUrlConfigured -InstallRoot $InstallRoot -EnvFile $envFile -PromptIfPlaceholder | Out-Null
} else {
    try {
        Ensure-DatabaseUrlConfigured -InstallRoot $InstallRoot -EnvFile $envFile | Out-Null
    } catch {
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        Ensure-DatabaseUrlConfigured -InstallRoot $InstallRoot -EnvFile $envFile -PromptIfPlaceholder | Out-Null
    }
}

Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $envFile
Write-Step "Syncing config\env\.env to apps\backend\.env..."
Sync-BackendEnvFile -InstallRoot $InstallRoot

$pythonExe = & "$PSScriptRoot\ensure-python-runtime.ps1" -InstallRoot $InstallRoot
Write-Step "Running database migrations..."
& "$PSScriptRoot\run-alembic-upgrade.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe

$service = Get-Service -Name "WEBSTUDIO Server" -ErrorAction SilentlyContinue
if ($service) {
    Write-Step "Applying service environment and restarting..."
    Apply-NssmServiceEnvironment -InstallRoot $InstallRoot
    Restart-Service -Name "WEBSTUDIO Server"
    Start-Sleep -Seconds 10
} else {
    Write-Step "Installing WEBSTUDIO Server Windows service..."
    & "$PSScriptRoot\install-webstudio-service.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe -SkipMigrations
}

Write-Step "Health check..."
try {
    $live = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/live" -UseBasicParsing -TimeoutSec 15
    Write-Host "  /health/live  -> $($live.StatusCode)" -ForegroundColor Green
    $ready = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/ready" -UseBasicParsing -TimeoutSec 15
    Write-Host "  /health/ready -> $($ready.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  Health check warning: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  See logs\webstudio-api-error.log if the service did not start." -ForegroundColor Yellow
}

Write-Step "Finalize complete. Run configure-firewall.ps1 if this is a new server."
