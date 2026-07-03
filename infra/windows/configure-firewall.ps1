#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Configure Windows Firewall rules for WEBSTUDIO IMS on the dedicated server PC.
#>
param(
    [int]$ApiPort = 8000,
    [string]$Subnet = "192.168.1.0/24",
    [string]$RulePrefix = "WEBSTUDIO IMS"
)

$ErrorActionPreference = "Stop"

function Add-Rule($Name, $Direction, $Action, $Protocol, $Port, $RemoteAddress) {
    $existing = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-NetFirewallRule -DisplayName $Name
    }
    New-NetFirewallRule `
        -DisplayName $Name `
        -Direction $Direction `
        -Action $Action `
        -Protocol $Protocol `
        -LocalPort $Port `
        -RemoteAddress $RemoteAddress | Out-Null
    Write-Host "[WEBSTUDIO] Firewall rule: $Name"
}

Add-Rule "$RulePrefix API Inbound" "Inbound" "Allow" "TCP" $ApiPort $Subnet
Add-Rule "$RulePrefix mDNS" "Inbound" "Allow" "UDP" 5353 $Subnet

Write-Host "[WEBSTUDIO] Firewall configured for API TCP $ApiPort and mDNS UDP 5353 from $Subnet"
Write-Host "[WEBSTUDIO] PostgreSQL remains localhost-only. Tally TCP 9000 is outbound from this server to the laptop."
