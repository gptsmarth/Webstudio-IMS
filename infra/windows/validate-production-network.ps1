#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Production networking validation for WEBSTUDIO IMS (M14B).
.DESCRIPTION
  Complements POST /api/v1/network/admin/validate?scope=production on the server.
  Run on the dedicated Windows server PC after install and firewall configuration.
#>
param(
    [int]$ApiPort = 8000,
    [string]$Subnet = "",
    [string]$ApiBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$RulePrefix = "WEBSTUDIO IMS"

function Get-LanIPv4 {
    $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
        Where-Object { $_.NextHop -ne "0.0.0.0" } |
        Sort-Object -Property RouteMetric |
        Select-Object -First 1
    if (-not $route) {
        return "127.0.0.1"
    }
    $address = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "169.254.*" } |
        Select-Object -First 1
    if ($address) {
        return $address.IPAddress
    }
    return "127.0.0.1"
}

function Test-TcpPort($HostName, $Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $waited = $async.AsyncWaitHandle.WaitOne(2000, $false)
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

function Test-HttpEndpoint($Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return [pscustomobject]@{ Ok = $true; StatusCode = $response.StatusCode }
    } catch {
        return [pscustomobject]@{ Ok = $false; StatusCode = 0; Error = $_.Exception.Message }
    }
}

$lanIp = Get-LanIPv4
if (-not $Subnet) {
    $octets = $lanIp.Split(".")
    if ($octets.Count -eq 4) {
        $Subnet = "$($octets[0]).$($octets[1]).$($octets[2]).0/24"
    } else {
        $Subnet = "192.168.1.0/24"
    }
}
if (-not $ApiBaseUrl) {
    $ApiBaseUrl = "http://${lanIp}:${ApiPort}"
}

Write-Host "[WEBSTUDIO] Production network validation (M14B)"
Write-Host "[WEBSTUDIO] LAN IP: $lanIp"
Write-Host "[WEBSTUDIO] Subnet: $Subnet"
Write-Host "[WEBSTUDIO] API base: $ApiBaseUrl"

$results = @()

$dhcp = Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.Dhcp -eq "Enabled" }
$staticHint = if ($dhcp) { "warning" } else { "passed" }
$results += [pscustomobject]@{
    Key = "static_server_ip"
    Status = $staticHint
    Message = if ($dhcp) { "Primary interface uses DHCP — prefer reservation for production." } else { "Primary interface appears statically addressed." }
}

$lanTcp = Test-TcpPort $lanIp $ApiPort
$lanHttp = Test-HttpEndpoint "$ApiBaseUrl/api/v1/health/live"
$results += [pscustomobject]@{
    Key = "lan_accessibility"
    Status = if ($lanTcp -and $lanHttp.Ok) { "passed" } else { "failed" }
    Message = "LAN TCP=$lanTcp HTTP=$($lanHttp.StatusCode)"
}

$apiRule = Get-NetFirewallRule -DisplayName "$RulePrefix API Inbound" -ErrorAction SilentlyContinue
$mdnsRule = Get-NetFirewallRule -DisplayName "$RulePrefix mDNS" -ErrorAction SilentlyContinue
$results += [pscustomobject]@{
    Key = "windows_firewall"
    Status = if ($apiRule -and $mdnsRule) { "passed" } else { "warning" }
    Message = "API rule=$([bool]$apiRule); mDNS rule=$([bool]$mdnsRule)"
}

$pgLocal = Test-TcpPort "127.0.0.1" 5432
$results += [pscustomobject]@{
    Key = "postgresql_connectivity"
    Status = if ($pgLocal) { "passed" } else { "failed" }
    Message = "PostgreSQL localhost:5432 reachable=$pgLocal"
}

$discovery = Test-HttpEndpoint "$ApiBaseUrl/api/v1/discovery/health"
$results += [pscustomobject]@{
    Key = "server_discovery"
    Status = if ($discovery.Ok) { "passed" } else { "failed" }
    Message = "Discovery health HTTP $($discovery.StatusCode)"
}

$android = Test-HttpEndpoint "$ApiBaseUrl/api/v1/client-updates/check?platform=mobile_android&current_version=0.0.0"
$ios = Test-HttpEndpoint "$ApiBaseUrl/api/v1/client-updates/check?platform=mobile_ios&current_version=0.0.0"
$results += [pscustomobject]@{
    Key = "android_connectivity"
    Status = if ($android.Ok) { "passed" } else { "failed" }
    Message = "Android update check HTTP $($android.StatusCode)"
}
$results += [pscustomobject]@{
    Key = "ios_connectivity"
    Status = if ($ios.Ok) { "passed" } else { "failed" }
    Message = "iOS update check HTTP $($ios.StatusCode)"
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq "failed" })
if ($failed.Count -gt 0) {
    Write-Host "[WEBSTUDIO] FAILED checks: $($failed.Key -join ', ')"
    exit 1
}

Write-Host "[WEBSTUDIO] Production network validation passed."
exit 0
