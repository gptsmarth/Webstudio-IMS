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
    [switch]$PromptForDatabasePassword,
    [string]$ApiBaseUrl = "http://127.0.0.1:8000"
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
$service = Get-Service -Name 'WEBSTUDIO Server' -ErrorAction SilentlyContinue
if ($service -and $service.Status -ne 'Stopped') {
    Stop-Service -InputObject $service
    $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
}

Write-Step "Running database migrations..."
& "$PSScriptRoot\run-alembic-upgrade.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe

if ($service) {
    Write-Step "Applying service environment and starting..."
    Apply-NssmServiceEnvironment -InstallRoot $InstallRoot
    Start-Service -InputObject $service
} else {
    Write-Step "Installing WEBSTUDIO Server Windows service..."
    & "$PSScriptRoot\install-webstudio-service.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe -SkipMigrations
}

Wait-WebstudioReadiness -ApiBaseUrl $ApiBaseUrl
Write-Step "Finalize complete."
