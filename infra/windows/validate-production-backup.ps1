#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Production backup validation for WEBSTUDIO IMS (M14D).
.DESCRIPTION
  Complements GET /api/v1/settings/backups/production-validation.
#>
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$BearerToken = ""
)

$ErrorActionPreference = "Stop"

function Invoke-BackupApi($Path) {
    $headers = @{}
    if ($BearerToken) {
        $headers["Authorization"] = "Bearer $BearerToken"
    }
    return Invoke-RestMethod -Uri "$ApiBaseUrl$Path" -Headers $headers -TimeoutSec 60
}

Write-Host "[WEBSTUDIO] Production backup validation (M14D)"

$service = Get-Service -Name "WEBSTUDIO Server" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "[WEBSTUDIO] WEBSTUDIO Server service: $($service.Status)"
} else {
    Write-Host "[WEBSTUDIO] WARNING: WEBSTUDIO Server service not registered"
}

try {
    $pgName = & "$PSScriptRoot\resolve-postgresql-service.ps1"
    $pg = Get-Service -Name $pgName -ErrorAction SilentlyContinue
    if ($pg) {
        Write-Host "[WEBSTUDIO] PostgreSQL service ($pgName): $($pg.Status)"
    }
} catch {
    Write-Host "[WEBSTUDIO] WARNING: PostgreSQL service not found"
}

if (-not $BearerToken) {
    Write-Host "[WEBSTUDIO] Set -BearerToken for full API validation."
    Write-Host "[WEBSTUDIO] Desktop: Settings -> Backup -> Recovery Center"
    exit 2
}

try {
    $payload = Invoke-BackupApi "/api/v1/settings/backups/production-validation"
    $data = $payload.data
    if (-not $data) { $data = $payload }
    $data.checks | ForEach-Object {
        Write-Host ("[{0}] {1}: {2}" -f $_.status.ToUpper(), $_.name, $_.message)
    }
    $failed = @($data.checks | Where-Object { $_.status -eq "failed" })
    if ($failed.Count -gt 0) {
        Write-Host "[WEBSTUDIO] FAILED: $($failed.key -join ', ')"
        exit 1
    }
    Write-Host "[WEBSTUDIO] Production backup validation passed (overall: $($data.overall_status))."
    exit 0
} catch {
    Write-Host "[WEBSTUDIO] Validation failed: $($_.Exception.Message)"
    exit 1
}
