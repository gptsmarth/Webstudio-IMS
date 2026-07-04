#Requires -Version 5.1
<#
.SYNOPSIS
  Run Alembic migrations for a WEBSTUDIO Server install.
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\webstudio-env.ps1"

if (-not $PythonExe) {
    $PythonExe = Join-Path $InstallRoot "runtime\python\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    throw "Python runtime not found at $PythonExe"
}

$alembicIni = Join-Path $InstallRoot "database\migrations\alembic.ini"
if (-not (Test-Path $alembicIni)) {
    throw "Alembic config not found: $alembicIni"
}

$envFile = Join-Path $InstallRoot "config\env\.env"
Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $envFile
Sync-BackendEnvFile -InstallRoot $InstallRoot
Import-DotEnvIntoProcess -Path $envFile

$dbUrl = $env:DATABASE_URL
if (-not $dbUrl -or $dbUrl -match 'CHANGE_ME') {
    throw @"
DATABASE_URL in $envFile still contains CHANGE_ME or is empty.
Run: powershell -ExecutionPolicy Bypass -File "$InstallRoot\infra\windows\finalize-server-setup.ps1"
"@
}

$migrationsDir = Join-Path $InstallRoot "database\migrations"
Push-Location $migrationsDir
try {
    & $PythonExe -m alembic -c alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic upgrade failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host "[WEBSTUDIO] Alembic migrations complete."
