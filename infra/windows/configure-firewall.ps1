#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Enable or disable inbound access to the WEBSTUDIO API on a trusted Private IPv4 network.
#>
[CmdletBinding(DefaultParameterSetName = 'Enable')]
param(
    [Parameter(ParameterSetName = 'Enable')][switch]$Enable,
    [Parameter(Mandatory, ParameterSetName = 'Disable')][switch]$Disable,
    [Parameter(ParameterSetName = 'Enable')][string]$ServerIp,
    [Parameter(ParameterSetName = 'Enable')][string]$Subnet,
    [Parameter(ParameterSetName = 'Enable')][ValidateRange(1, 65535)][int]$ApiPort,
    [Parameter(ParameterSetName = 'Enable')][string]$InstallRoot = (Join-Path $PSScriptRoot '..\..')
)

$ErrorActionPreference = 'Stop'
$ruleName = 'WEBSTUDIO-IMS-Office-LAN'
$displayName = 'WEBSTUDIO IMS - Office LAN'
$knownDisplayNames = @($displayName, 'WEBSTUDIO IMS API Inbound', 'WEBSTUDIO API In')
$privateNetworkHelp = 'For a trusted office network, open Windows Settings > Network & internet, select the office connection, choose the Private network profile, then rerun this command. Leave untrusted networks Public.'

function ConvertTo-IPv4Number([string]$Address) {
    if ($Address -notmatch '^(0|[1-9][0-9]{0,2})(\.(0|[1-9][0-9]{0,2})){3}$') {
        throw "Invalid IPv4 address: $Address"
    }
    $bytes = [System.Net.IPAddress]::Parse($Address).GetAddressBytes()
    [array]::Reverse($bytes)
    [BitConverter]::ToUInt32($bytes, 0)
}

function Get-PrivatePrefix([string]$Address) {
    $octets = $Address.Split('.')
    if ($octets[0] -eq '10') { return 8 }
    if ($octets[0] -eq '172' -and [int]$octets[1] -ge 16 -and [int]$octets[1] -le 31) { return 12 }
    if ($octets[0] -eq '192' -and $octets[1] -eq '168') { return 16 }
    return 0
}

function Get-NetworkAddress([uint32]$Address, [int]$Prefix) {
    $blockSize = [math]::Pow(2, 32 - $Prefix)
    $number = [uint32]([math]::Floor($Address / $blockSize) * $blockSize)
    $bytes = [BitConverter]::GetBytes($number)
    [array]::Reverse($bytes)
    ([System.Net.IPAddress]::new($bytes)).ToString()
}

try {
    $legacyEnable = $Subnet -and -not $PSBoundParameters.ContainsKey('Enable')
    if (-not ($Enable -or $Disable -or $legacyEnable)) {
        throw 'Specify -Enable for office access or -Disable to turn it off.'
    }
    $managedRules = @(Get-NetFirewallRule -PolicyStore PersistentStore | Where-Object {
        $_.Direction -eq 'Inbound' -and $_.Action -eq 'Allow' -and
        ($_.Name -eq $ruleName -or $_.DisplayName -in $knownDisplayNames)
    })
    if ($Disable) {
        if ($managedRules.Count) { Set-NetFirewallRule -InputObject $managedRules -Enabled False }
        Write-Host '[WEBSTUDIO] Office LAN API firewall access is disabled.'
        return
    }

    if (-not $PSBoundParameters.ContainsKey('ApiPort')) {
        $ApiPort = 8000
        $envFile = Join-Path $InstallRoot 'config\env\.env'
        if (Test-Path -LiteralPath $envFile -PathType Leaf) {
            . (Join-Path $PSScriptRoot 'webstudio-env.ps1')
            $savedPort = (Read-DotEnvFile -Path $envFile)['API_PORT']
            if ($savedPort -and -not [int]::TryParse($savedPort.Trim('"').Trim("'"), [ref]$ApiPort)) {
                throw 'Set API_PORT in the installed .env to a valid TCP port.'
            }
        }
    }
    if ($ApiPort -lt 1 -or $ApiPort -gt 65535 -or $ApiPort -eq 5432) {
        throw 'Select an API TCP port between 1 and 65535, excluding PostgreSQL port 5432.'
    }

    if ($ServerIp) { $null = ConvertTo-IPv4Number $ServerIp }
    $privateProfiles = @(Get-NetConnectionProfile | Where-Object NetworkCategory -eq Private)
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred | Where-Object {
        $_.InterfaceIndex -in $privateProfiles.InterfaceIndex -and
        (Get-PrivatePrefix $_.IPAddress) -gt 0 -and
        (-not $ServerIp -or $_.IPAddress -eq $ServerIp)
    })
    if ($addresses.Count -eq 0) {
        throw "The selected address must be assigned to an active Private office connection with a private IPv4 address. $privateNetworkHelp"
    }
    if ($addresses.Count -gt 1) {
        throw "Multiple eligible Private IPv4 addresses were found ($($addresses.IPAddress -join ', ')). Rerun with the office server's -ServerIp."
    }
    $address = $addresses[0]
    $localNumber = ConvertTo-IPv4Number $address.IPAddress
    $minPrefix = [math]::Max($address.PrefixLength, (Get-PrivatePrefix $address.IPAddress))
    $prefix = $address.PrefixLength
    $networkNumber = $localNumber
    if ($Subnet) {
        if ($Subnet -notmatch '^([^/]+)/([0-9]{1,2})$') { throw 'Enter the office subnet in IPv4 CIDR format.' }
        $prefix = [int]$Matches[2]
        $networkNumber = ConvertTo-IPv4Number $Matches[1]
    }
    if ($prefix -lt $minPrefix -or $prefix -gt 32) {
        throw "Use the connected private subnet or a narrower subnet (prefix length $minPrefix through 32)."
    }
    $network = Get-NetworkAddress $networkNumber $prefix
    if ($network -ne (Get-NetworkAddress $localNumber $prefix)) {
        throw 'The office subnet must contain the selected server IPv4 address.'
    }
    $cidr = "$network/$prefix"

    $firewall = Get-NetFirewallProfile -PolicyStore ActiveStore -Name Private
    if ($firewall.Enabled -ne 'True' -or $firewall.DefaultInboundAction -eq 'Allow' -or
        $firewall.AllowInboundRules -eq 'False' -or $firewall.AllowLocalFirewallRules -eq 'False') {
        throw 'The active Private firewall policy must be enabled, block unsolicited inbound traffic, and allow local rules. Review Windows Firewall or Group Policy.'
    }

    $preference = @(
        @{ Expression = { $_.Name -eq $ruleName }; Descending = $true }
        @{ Expression = { $_.DisplayName -eq $displayName }; Descending = $true }
        'Name'
    )
    $rule = $managedRules | Sort-Object -Property $preference | Select-Object -First 1
    $scope = @{
        Enabled = 'True'
        Profile = 'Private'
        Direction = 'Inbound'
        Action = 'Allow'
        Protocol = 'TCP'
        LocalPort = $ApiPort
        LocalAddress = $address.IPAddress
        RemoteAddress = $cidr
        InterfaceAlias = [System.Management.Automation.WildcardPattern]::Escape($address.InterfaceAlias)
        EdgeTraversalPolicy = 'Block'
    }
    if ($rule) {
        $duplicates = @($managedRules | Where-Object { $_.Name -ne $rule.Name })
        if ($duplicates.Count) { Set-NetFirewallRule -InputObject $duplicates -Enabled False }
        Set-NetFirewallRule -InputObject $rule -NewDisplayName $displayName @scope
        $ruleName = $rule.Name
    } else {
        New-NetFirewallRule -PolicyStore PersistentStore -Name $ruleName -DisplayName $displayName @scope | Out-Null
    }
    $activeRule = Get-NetFirewallRule -PolicyStore ActiveStore -Name $ruleName
    if ($activeRule.Enabled -ne 'True' -or $activeRule.Profile -ne 'Private') {
        throw 'The scoped rule was saved but did not take effect. Check the active Windows Firewall policy.'
    }
    Write-Host "[WEBSTUDIO] Office LAN API access enabled for TCP $($address.IPAddress):$ApiPort from $cidr on $($address.InterfaceAlias) (Private profile)."
} catch {
    throw "WEBSTUDIO LAN configuration failed. $($_.Exception.Message)"
}
