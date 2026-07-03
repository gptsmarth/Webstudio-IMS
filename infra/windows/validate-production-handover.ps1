#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Final production handover validation for WEBSTUDIO IMS v1.0.0 (M14J).
#>
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$BearerToken = ""
)

$ErrorActionPreference = "Stop"

if (-not $BearerToken) {
    Write-Host "[WEBSTUDIO] Set -BearerToken for M14J handover API validation."
    exit 2
}

$response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/v1/deployment/production-handover" `
    -Headers @{ Authorization = "Bearer $BearerToken" } -TimeoutSec 120
$payload = $response.data

Write-Host "[WEBSTUDIO] $($payload.version_label)"
Write-Host "[WEBSTUDIO] Overall: $($payload.overall_status) | production_ready: $($payload.production_ready)"
Write-Host "[WEBSTUDIO] Version: $($payload.verified_version) / $($payload.verified_channel)"

foreach ($check in $payload.checks) {
    if ($check.status -ne "passed") {
        Write-Host "[$($check.status.ToUpper())] $($check.key): $($check.message)"
    }
}

if (-not $payload.production_ready) { exit 1 }
if ($payload.overall_status -eq "warning") { exit 2 }
exit 0
