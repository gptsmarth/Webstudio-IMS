#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Production Tally integration validation for WEBSTUDIO IMS (M14C).
.DESCRIPTION
  Complements GET /api/v1/integrations/tally/production-validation.
  Assumes Tally ERP 9 is running on the billing PC with XML port open.
#>
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$BearerToken = "",
    [string]$TallyHost = "",
    [int]$TallyPort = 9000
)

$ErrorActionPreference = "Stop"

function Test-TcpPort($HostName, $Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $waited = $async.AsyncWaitHandle.WaitOne(3000, $false)
        if (-not $waited) {
            $client.Close()
            return $false
        }
        $client.EndConnect($async)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Invoke-TallyApi($Path) {
    $headers = @{}
    if ($BearerToken) {
        $headers["Authorization"] = "Bearer $BearerToken"
    }
    return Invoke-RestMethod -Uri "$ApiBaseUrl$Path" -Headers $headers -TimeoutSec 30
}

Write-Host "[WEBSTUDIO] Production Tally validation (M14C)"

if ($TallyHost) {
    $tallyTcp = Test-TcpPort $TallyHost $TallyPort
    Write-Host "[WEBSTUDIO] Tally TCP ${TallyHost}:${TallyPort} reachable=$tallyTcp"
    if (-not $tallyTcp) {
        Write-Host "[WEBSTUDIO] WARNING: Tally workstation not reachable on LAN"
    }
}

if (-not $BearerToken) {
    Write-Host "[WEBSTUDIO] Set -BearerToken from a logged-in administrator session to run API validation."
    Write-Host "[WEBSTUDIO] Or run validation from Desktop: Tally page / Settings -> Test Connection."
    exit 2
}

try {
    $payload = Invoke-TallyApi "/api/v1/integrations/tally/production-validation"
    $data = $payload.data
    if (-not $data) {
        $data = $payload
    }
    $checks = $data.checks
    $checks | ForEach-Object {
        Write-Host ("[{0}] {1}: {2}" -f $_.status.ToUpper(), $_.name, $_.message)
    }
    $failed = @($checks | Where-Object { $_.status -eq "failed" })
    if ($failed.Count -gt 0) {
        Write-Host "[WEBSTUDIO] FAILED checks: $($failed.key -join ', ')"
        exit 1
    }
    Write-Host "[WEBSTUDIO] Production Tally validation passed (overall: $($data.overall_status))."
    exit 0
} catch {
    Write-Host "[WEBSTUDIO] API validation failed: $($_.Exception.Message)"
    exit 1
}
