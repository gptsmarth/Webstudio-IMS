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

Write-Step "Ensuring GitHub release sync is enabled when repo is configured..."
$envVars = Read-DotEnvFile -Path $envFile
if ($envVars.ContainsKey("WEBSTUDIO_GITHUB_REPO") -and $envVars["WEBSTUDIO_GITHUB_REPO"]) {
    $enableSyncSql = @"
UPDATE webstudio.system_settings
SET setting_value = 'true', value_type = 'boolean', updated_at = NOW()
WHERE setting_key = 'github_release_sync_enabled';
INSERT INTO webstudio.system_settings (setting_key, setting_value, value_type)
VALUES ('github_release_sync_enabled', 'true', 'boolean')
ON CONFLICT (setting_key)
DO UPDATE SET setting_value = 'true', value_type = 'boolean', updated_at = NOW();
"@
    try {
        $dbUrl = $envVars["DATABASE_URL"]
        if ($dbUrl -match 'postgresql\+asyncpg://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)') {
            $pgUser = $Matches[1]
            $pgPass = [uri]::UnescapeDataString($Matches[2])
            $pgHost = $Matches[3]
            $pgPort = $Matches[4]
            $pgDb = $Matches[5]
            $env:PGPASSWORD = $pgPass
            & psql -h $pgHost -p $pgPort -U $pgUser -d $pgDb -c $enableSyncSql 2>$null
            Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
            Write-Host "  github_release_sync_enabled -> true" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Skipped DB sync toggle (run H3 SQL manually if needed): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

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
