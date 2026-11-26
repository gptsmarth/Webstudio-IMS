#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$windowsScripts = Join-Path $PSScriptRoot '..\..\infra\windows'
$fixture = Join-Path ([System.IO.Path]::GetTempPath()) ("webstudio firewall " + [guid]::NewGuid())
New-Item -Path $fixture -ItemType Directory | Out-Null
$scriptPath = Join-Path $fixture 'configure-firewall.ps1'

$rules = [System.Collections.Generic.List[object]]::new()
$officeProfile = [pscustomobject]@{ InterfaceIndex = 5; NetworkCategory = 'Private' }
$officeIp = [pscustomobject]@{ InterfaceIndex = 5; InterfaceAlias = 'Wi-Fi'; IPAddress = '10.20.30.10'; PrefixLength = 24 }
$fixtureState = @{ Addresses = @($officeIp); Writes = 0; NewRules = 0 }
$policy = [pscustomobject]@{
    Enabled = 'True'
    DefaultInboundAction = 'Block'
    AllowInboundRules = 'True'
    AllowLocalFirewallRules = 'True'
}

function Get-NetConnectionProfile { $officeProfile }
function Get-NetIPAddress { param($AddressFamily, $AddressState) $fixtureState.Addresses }
function Set-NetConnectionProfile { throw 'The LAN helper must leave Windows profiles unchanged.' }
function Set-NetFirewallProfile { throw 'The LAN helper must leave firewall policy enabled.' }
function Remove-NetFirewallRule { throw 'The LAN helper must update rules in place.' }
function Get-NetFirewallProfile { param($PolicyStore, $Name) $policy }
function Get-NetFirewallRule {
    param($PolicyStore, $Name)
    $rules | Where-Object { -not $Name -or $_.Name -eq $Name }
}
function New-NetFirewallRule {
    param(
        $PolicyStore, $Name, $DisplayName, $Enabled, $Profile, $Direction, $Action,
        $Protocol, $LocalPort, $LocalAddress, $RemoteAddress, $InterfaceAlias, $EdgeTraversalPolicy
    )
    $fixtureState.Writes++
    $fixtureState.NewRules++
    $rules.Add([pscustomobject]@{
        Name = $Name; DisplayName = $DisplayName; Enabled = $Enabled; Profile = $Profile
        Direction = $Direction; Action = $Action; Protocol = $Protocol; LocalPort = $LocalPort
        LocalAddress = $LocalAddress; RemoteAddress = $RemoteAddress
        InterfaceAlias = $InterfaceAlias; EdgeTraversalPolicy = $EdgeTraversalPolicy
    })
}
function Set-NetFirewallRule {
    param(
        [object[]]$InputObject, $NewDisplayName, $Enabled, $Profile, $Direction, $Action,
        $Protocol, $LocalPort, $LocalAddress, $RemoteAddress, $InterfaceAlias, $EdgeTraversalPolicy
    )
    $fixtureState.Writes++
    foreach ($rule in $InputObject) {
        if ($NewDisplayName) { $rule.DisplayName = $NewDisplayName }
        foreach ($field in $PSBoundParameters.Keys) {
            if ($field -notin @('InputObject', 'NewDisplayName')) {
                $rule.$field = $PSBoundParameters[$field]
            }
        }
    }
}
function Assert-Blocked([scriptblock]$Command, [string]$Expected) {
    $before = $fixtureState.Writes
    $failure = $null
    try { & $Command } catch { $failure = $_.Exception.Message }
    if ($failure -notlike "*$Expected*") { throw "Expected '$Expected'. Got '$failure'." }
    if ($fixtureState.Writes -ne $before) { throw 'A rejected configuration changed the firewall.' }
}

try {
    # All firewall cmdlets are mocked. Strip only the elevation directive in this fixture.
    $source = Get-Content -LiteralPath (Join-Path $windowsScripts 'configure-firewall.ps1') -Raw
    $source -replace '(?m)^#Requires -RunAsAdministrator\r?\n', '' | Set-Content -LiteralPath $scriptPath
    Copy-Item -LiteralPath (Join-Path $windowsScripts 'webstudio-env.ps1') -Destination $fixture

    & $scriptPath -Enable -InstallRoot $fixture
    $rule = $rules[0]
    if ($rules.Count -ne 1 -or $rule.Name -ne 'WEBSTUDIO-IMS-Office-LAN' -or
        $rule.Protocol -ne 'TCP' -or $rule.LocalPort -ne 8000 -or $rule.LocalAddress -ne '10.20.30.10' -or
        $rule.RemoteAddress -ne '10.20.30.0/24' -or $rule.Profile -ne 'Private' -or
        $rule.InterfaceAlias -ne 'Wi-Fi' -or $rule.EdgeTraversalPolicy -ne 'Block') {
        throw 'The automatic rule did not use the connected Private office scope.'
    }

    $officeIp.IPAddress = '192.168.80.22'
    & $scriptPath -Enable -ServerIp '192.168.80.22' -Subnet '192.168.80.0/25' -ApiPort 8443
    if ($rules.Count -ne 1 -or $fixtureState.NewRules -ne 1 -or $rule.LocalAddress -ne '192.168.80.22' -or
        $rule.RemoteAddress -ne '192.168.80.0/25' -or $rule.LocalPort -ne 8443) {
        throw 'Changing the office configuration did not update the existing rule.'
    }

    $envDir = Join-Path $fixture 'config\env'
    New-Item -Path $envDir -ItemType Directory -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $envDir '.env') -Value 'API_PORT="8181"'
    & $scriptPath -Enable -InstallRoot $fixture
    if ($rule.LocalPort -ne 8181) { throw 'The rule did not use the installed API_PORT.' }

    Assert-Blocked { & $scriptPath -Enable -ApiPort 5432 } 'excluding PostgreSQL port'
    Assert-Blocked { & $scriptPath -Enable -ApiPort 8000 -Subnet '0.0.0.0/0' } 'narrower subnet'
    Assert-Blocked { & $scriptPath -Enable -ApiPort 8000 -Subnet '192.168.81.0/24' } 'must contain'
    Assert-Blocked { & $scriptPath -Enable:$false -Subnet '192.168.80.0/24' } 'Specify -Enable'
    $officeProfile.NetworkCategory = 'Public'
    Assert-Blocked { & $scriptPath -Enable -ApiPort 8000 -ServerIp '192.168.80.22' } 'choose the Private network profile'
    if ($officeProfile.NetworkCategory -ne 'Public') { throw 'The network profile was modified.' }
    $officeProfile.NetworkCategory = 'Private'
    $fixtureState.Addresses = @($officeIp, [pscustomobject]@{
        InterfaceIndex = 5; InterfaceAlias = 'Wi-Fi'; IPAddress = '192.168.80.23'; PrefixLength = 24
    })
    Assert-Blocked { & $scriptPath -Enable -ApiPort 8000 } 'Multiple eligible Private IPv4 addresses'
    $fixtureState.Addresses = @($officeIp)
    $policy.Enabled = 'False'
    Assert-Blocked { & $scriptPath -Enable -ApiPort 8000 } 'active Private firewall policy'
    $policy.Enabled = 'True'

    $rules.Clear()
    New-NetFirewallRule -Name 'manual-guid' -DisplayName 'WEBSTUDIO IMS - Office LAN' -Enabled True -Direction Inbound -Action Allow
    New-NetFirewallRule -Name 'older-guid' -DisplayName 'WEBSTUDIO IMS API Inbound' -Enabled True -Direction Inbound -Action Allow
    New-NetFirewallRule -Name 'mdns-guid' -DisplayName 'WEBSTUDIO IMS mDNS' -Enabled True -Direction Inbound -Action Allow
    New-NetFirewallRule -Name 'runbook-guid' -DisplayName 'WEBSTUDIO API In' -Enabled True -Direction Inbound -Action Allow
    $before = $fixtureState.NewRules
    & $scriptPath -Enable -ApiPort 8000
    if ($fixtureState.NewRules -ne $before -or $rules[0].Name -ne 'manual-guid' -or
        $rules[0].Profile -ne 'Private' -or $rules[1].Enabled -ne 'False' -or
        $rules[2].Enabled -ne 'True' -or $rules[3].Enabled -ne 'False') {
        throw 'Legacy API rules were not adopted safely or discovery was changed.'
    }

    & $scriptPath -Disable
    & $scriptPath -Disable
    if ($rules[0].Enabled -ne 'False' -or $rules[2].Enabled -ne 'True') {
        throw 'Disabling LAN access affected an unexpected firewall rule.'
    }
    Write-Host '[release] Office LAN firewall setup checks passed.'
} finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
