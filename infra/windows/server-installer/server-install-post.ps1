#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Post-install configuration for WEBSTUDIO Server Setup.exe
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$PostgresServiceName = ""
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

$resolvedPostgres = & "$PSScriptRoot\..\resolve-postgresql-service.ps1" -PostgresServiceName $PostgresServiceName
Write-Step "Using PostgreSQL service: $resolvedPostgres"

$dirs = @(
    "$InstallRoot\logs",
    "$InstallRoot\backups",
    "$InstallRoot\backups\config",
    "$InstallRoot\backups\certs",
    "$InstallRoot\certs",
    "$InstallRoot\exports",
    "$InstallRoot\exports\archive",
    "$InstallRoot\config\env",
    "$InstallRoot\tools\nssm",
    "$InstallRoot\runtime\python"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Step "Ensuring PostgreSQL..."
& "$PSScriptRoot\..\ensure-postgresql.ps1" -PostgresServiceName $resolvedPostgres

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
    $jwt = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
    (Get-Content $envFile) `
        -replace 'JWT_SECRET=GENERATED_BY_INSTALLER', "JWT_SECRET=$jwt" `
        -replace 'API_PORT=8443', 'API_PORT=8000' | Set-Content $envFile
}

Write-Step "Installing/updating Python dependencies..."
Push-Location "$InstallRoot\apps\backend"
$importCheck = & $pythonExe -c "import webstudio_backend" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Step "Bundled backend not importable; installing package..."
    & $pythonExe -m pip install . --no-warn-script-location
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE"
    }
} else {
    Write-Step "Bundled backend runtime already installed."
}
Write-Step "Running Alembic migrations..."
& $pythonExe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw @"
Alembic migration failed. Ensure PostgreSQL database 'webstudio' and user 'webstudio_app' exist,
and DATABASE_URL in $envFile is correct. Then re-run post-install.
"@
}
Pop-Location

Write-Step "Installing WEBSTUDIO Server Windows Service..."
& "$PSScriptRoot\..\install-webstudio-service.ps1" `
    -InstallRoot $InstallRoot `
    -PostgresServiceName $resolvedPostgres `
    -PythonExe $pythonExe `
    -NssmPath $nssmPath

Write-Step "WEBSTUDIO Server post-install complete."
