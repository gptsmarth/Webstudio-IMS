#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Post-install configuration for WEBSTUDIO Server Setup.exe
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$PostgresServiceName = "",
    [switch]$ManualDatabase
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\..\webstudio-env.ps1"
. "$PSScriptRoot\postgres-setup.ps1"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

$dirs = @(
    "$InstallRoot\logs",
    "$InstallRoot\backups",
    "$InstallRoot\backups\config",
    "$InstallRoot\backups\certs",
    "$InstallRoot\certs",
    "$InstallRoot\exports",
    "$InstallRoot\exports\archive",
    "$InstallRoot\config\env",
    "$InstallRoot\apps\backend\config\env",
    "$InstallRoot\tools\nssm",
    "$InstallRoot\runtime\python"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

$pythonExe = & "$PSScriptRoot\..\ensure-python-runtime.ps1" -InstallRoot $InstallRoot
Write-Step "Using Python: $pythonExe"

$nssmPath = "$InstallRoot\tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    throw "NSSM not found at $nssmPath. Re-run WEBSTUDIO Server Setup.exe from the latest release build."
}

$envFile = "$InstallRoot\config\env\.env"
if (-not (Test-Path $envFile)) {
    Write-Step "Generating production .env..."
    $template = Join-Path $InstallRoot "config\env\.env.production.template"
    if (-not (Test-Path $template)) {
        $template = Join-Path (Split-Path $PSScriptRoot -Parent) "..\..\config\env\.env.production.template"
    }
    if (-not (Test-Path $template)) {
        throw "Missing .env.production.template under $InstallRoot\config\env\"
    }
    Copy-Item $template $envFile -Force
    $secretBytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($secretBytes)
        $jwt = [Convert]::ToBase64String($secretBytes)
    } finally {
        $rng.Dispose()
    }
    (Get-Content $envFile) `
        -replace 'JWT_SECRET=GENERATED_BY_INSTALLER', "JWT_SECRET=$jwt" `
        -replace 'API_PORT=8443', 'API_PORT=8000' `
        -replace '@localhost:5432', '@127.0.0.1:5432' | Set-Content $envFile
    Set-DotEnvValue -Path $envFile -Key 'WEBSTUDIO_DATA_ROOT' -Value $InstallRoot
    Set-DotEnvValue -Path $envFile -Key 'WEBSTUDIO_RELEASE_UPDATES_ROOT' -Value (Join-Path $InstallRoot 'Updates')
}

Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $envFile
Sync-BackendEnvFile -InstallRoot $InstallRoot

Write-Step "Installing/updating Python dependencies..."
Push-Location "$InstallRoot\apps\backend"
try {
    $importCheck = & $pythonExe -c "import webstudio_backend" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Bundled backend not importable; installing package..."
        & $pythonExe -m pip install hatchling wheel --no-warn-script-location
        if ($LASTEXITCODE -ne 0) {
            throw "pip install hatchling/wheel failed with exit code $LASTEXITCODE"
        }
        & $pythonExe -m pip install --no-build-isolation . --no-warn-script-location
        if ($LASTEXITCODE -ne 0) {
            throw "pip install failed with exit code $LASTEXITCODE"
        }
    } else {
        Write-Step "Bundled backend runtime already installed."
    }
} finally {
    Pop-Location
}

Write-Step "Configuring database connection..."
Ensure-SetupDatabase -EnvFile $envFile -PostgresServiceName $PostgresServiceName -Manual:$ManualDatabase
Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $envFile
Sync-BackendEnvFile -InstallRoot $InstallRoot

$existingService = Get-Service -Name 'WEBSTUDIO Server' -ErrorAction SilentlyContinue
if ($existingService -and $existingService.Status -ne 'Stopped') {
    Stop-Service -InputObject $existingService
    $existingService.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
}

Write-Step "Running Alembic migrations..."
& "$PSScriptRoot\..\run-alembic-upgrade.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe

if ($existingService) {
    Write-Step 'Updating the existing WEBSTUDIO Server service environment...'
    Apply-NssmServiceEnvironment -InstallRoot $InstallRoot -EnvFile $envFile
    Start-Service -InputObject $existingService
} else {
    Write-Step "Installing WEBSTUDIO Server Windows Service..."
    & "$PSScriptRoot\..\install-webstudio-service.ps1" `
        -InstallRoot $InstallRoot -PythonExe $pythonExe -NssmPath $nssmPath -SkipMigrations -SkipPostgresCheck
}

$settings = Read-DotEnvFile -Path $envFile
if (-not $settings['TLS_CERT_PATH']) {
    $apiAddress = $settings['API_HOST']
    if (-not $apiAddress -or $apiAddress -eq '0.0.0.0') { $apiAddress = '127.0.0.1' }
    $apiPort = $settings['API_PORT']
    if (-not $apiPort) { $apiPort = 8000 }
    Wait-WebstudioReadiness -ApiBaseUrl "http://${apiAddress}:${apiPort}"
} else {
    Write-Step 'TLS is configured. Confirm /health/ready using the existing certified HTTPS URL.'
}

Write-Step "WEBSTUDIO Server post-install complete."
