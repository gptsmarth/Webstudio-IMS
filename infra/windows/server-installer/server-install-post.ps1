#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Post-install configuration for WEBSTUDIO Server Setup.exe
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$PostgresServiceName = "postgresql-x64-16"
)

$ErrorActionPreference = "Stop"

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
    "$InstallRoot\tools\nssm"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Step "Ensuring PostgreSQL..."
& "$PSScriptRoot\..\ensure-postgresql.ps1" -PostgresServiceName $PostgresServiceName

$pythonExe = "$InstallRoot\venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found at $pythonExe"
}

$envFile = "$InstallRoot\config\env\.env"
if (-not (Test-Path $envFile)) {
    Write-Step "Generating production .env..."
    $template = Join-Path $InstallRoot "config\env\.env.production.template"
    if (-not (Test-Path $template)) {
        $template = Join-Path (Split-Path $PSScriptRoot -Parent) "..\..\config\env\.env.production.template"
    }
    Copy-Item $template $envFile -Force
    $jwt = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
    (Get-Content $envFile) -replace 'JWT_SECRET=GENERATED_BY_INSTALLER', "JWT_SECRET=$jwt" | Set-Content $envFile
}

Write-Step "Installing Python dependencies..."
Push-Location "$InstallRoot\apps\backend"
& $pythonExe -m pip install -e . --quiet
Write-Step "Running Alembic migrations..."
& $pythonExe -m alembic upgrade head
Pop-Location

Write-Step "Installing WEBSTUDIO Server Windows Service..."
& "$PSScriptRoot\..\install-webstudio-service.ps1" -InstallRoot $InstallRoot -PostgresServiceName $PostgresServiceName

Write-Step "WEBSTUDIO Server post-install complete."
