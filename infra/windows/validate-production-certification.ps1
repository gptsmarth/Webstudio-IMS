#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Production certification for WEBSTUDIO IMS (M14G).
.DESCRIPTION
  Complements GET /api/v1/deployment/production-certification.
#>
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$BearerToken = ""
)

$ErrorActionPreference = "Stop"

function Invoke-CertificationApi($Path) {
    $headers = @{}
    if ($BearerToken) {
        $headers["Authorization"] = "Bearer $BearerToken"
    }
    return Invoke-RestMethod -Uri "$ApiBaseUrl$Path" -Headers $headers -TimeoutSec 120
}

Write-Host "[WEBSTUDIO] Production certification (M14G)"

$service = Get-Service -Name "WEBSTUDIO Server" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "[WEBSTUDIO] WEBSTUDIO Server service: $($service.Status)"
} else {
    Write-Host "[WEBSTUDIO] WARNING: WEBSTUDIO Server service not registered"
}

if (-not $BearerToken) {
    Write-Host "[WEBSTUDIO] Set -BearerToken (Main Admin or network admin) for full certification API."
    Write-Host "[WEBSTUDIO] Docs: docs/milestones/m14/PRODUCTION_CERTIFICATION_REPORT.md"
    exit 2
}

try {
    $health = Invoke-CertificationApi "/api/v1/health/live"
    Write-Host "[WEBSTUDIO] Health: $($health.data.status)"
} catch {
    Write-Host "[WEBSTUDIO] ERROR: API not reachable at $ApiBaseUrl"
    exit 1
}

$response = Invoke-CertificationApi "/api/v1/deployment/production-certification"
$payload = $response.data

Write-Host "[WEBSTUDIO] Overall: $($payload.overall_status)"
Write-Host "[WEBSTUDIO] Security: $($payload.security_certification.overall_status)"
Write-Host "[WEBSTUDIO] Performance: $($payload.performance_certification.overall_status)"
Write-Host "[WEBSTUDIO] Infrastructure: $($payload.infrastructure_certification.overall_status)"

foreach ($section in @("security_certification", "performance_certification", "infrastructure_certification")) {
    $checks = $payload.$section.checks | Where-Object { $_.status -ne "passed" }
    foreach ($check in $checks) {
        Write-Host "[WEBSTUDIO] $($check.status.ToUpper()) $($check.key): $($check.message)"
    }
}

if ($payload.recommendations.Count -gt 0) {
    Write-Host "[WEBSTUDIO] Recommendations:"
    foreach ($rec in $payload.recommendations) {
        Write-Host "  - $rec"
    }
}

if ($payload.overall_status -eq "failed") {
    exit 1
}
if ($payload.overall_status -eq "warning") {
    exit 2
}
exit 0
