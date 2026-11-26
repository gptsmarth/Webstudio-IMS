#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$repo = Join-Path $PSScriptRoot '..\..'
. (Join-Path $repo 'infra\windows\webstudio-env.ps1')

$fixture = New-Item -Path ([IO.Path]::GetTempPath()) -Name ('webstudio-env-' + [guid]::NewGuid()) -ItemType Directory
$windows = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
$fixtureRegistry = $fixture.FullName

function Repair-ProductionEnvFile { param($InstallRoot, $EnvFile) }
function Sync-BackendEnvFile { param($InstallRoot) }
function Get-NssmServiceParametersRegPath { param($ServiceName) $script:fixtureRegistry }

try {
    if ($windows) {
        $fixtureRegistry = "HKCU:\Software\$($fixture.Name)"
        New-Item -Path $fixtureRegistry | Out-Null
        New-ItemProperty -LiteralPath $fixtureRegistry -Name 'AppEnvironmentExtra' `
            -PropertyType MultiString -Value @('System.Object[]') | Out-Null
    } else {
        $script:fixtureEntries = [string[]]@('System.Object[]')
        function Set-ItemProperty {
            [CmdletBinding()]
            param([Alias('Path')]$LiteralPath, $Name, $Value, $Type)
            if ($Value -isnot [string[]] -or $Type -ne 'MultiString') {
                throw 'The NSSM registry value must be a flat string array.'
            }
            $script:fixtureEntries = $Value
        }
        function Get-ItemProperty {
            [CmdletBinding()]
            param([Alias('Path')]$LiteralPath, $Name)
            [pscustomobject]@{ AppEnvironmentExtra = $script:fixtureEntries }
        }
    }

    $fixtureEnv = Join-Path $fixture.FullName '.env'
    Set-Content -LiteralPath $fixtureEnv -Value @(
        'WEBSTUDIO_TALLY_SCHEDULER=0'
        'API_PORT=8042'
        'POSTGRES_BIN=C:\Program Files\PostgreSQL\16\bin'
        'DATABASE_URL=postgresql://webstudio_app:fixture-only@localhost/webstudio'
        'JWT_SECRET=fixture-only'
        'GOOGLE_DRIVE_CLIENT_SECRET=fixture-only'
    )
    $fixtureNssm = Join-Path $fixture.FullName 'nssm.exe'
    New-Item -Path $fixtureNssm -ItemType File | Out-Null
    Apply-NssmServiceEnvironment -InstallRoot $fixture.FullName -EnvFile $fixtureEnv -NssmPath $fixtureNssm

    $stored = (Get-ItemProperty -LiteralPath $fixtureRegistry -Name 'AppEnvironmentExtra').AppEnvironmentExtra
    if ('WEBSTUDIO_TALLY_SCHEDULER=0' -cnotin $stored -or 'API_PORT=8042' -cnotin $stored -or
        'PATH=C:\Program Files\PostgreSQL\16\bin;C:\Windows\System32;C:\Windows' -cnotin $stored -or
        ($stored | Where-Object { $_ -like '*fixture-only*' })) {
        throw 'The saved NSSM environment did not preserve configuration as separate entries.'
    }
    if ($windows -and (Get-Item -LiteralPath $fixtureRegistry).GetValueKind('AppEnvironmentExtra') -ne 'MultiString') {
        throw 'AppEnvironmentExtra must be REG_MULTI_SZ.'
    }

    Set-DotEnvValue -Path $fixtureEnv -Key 'WEBSTUDIO_TALLY_SCHEDULER' -Value '1'
    Apply-NssmServiceEnvironment -InstallRoot $fixture.FullName -EnvFile $fixtureEnv -NssmPath $fixtureNssm
    $updated = (Get-ItemProperty -LiteralPath $fixtureRegistry -Name 'AppEnvironmentExtra').AppEnvironmentExtra
    if ('WEBSTUDIO_TALLY_SCHEDULER=1' -cnotin $updated -or 'WEBSTUDIO_TALLY_SCHEDULER=0' -cin $updated -or
        'API_PORT=8042' -cnotin $updated) {
        throw 'Updating an existing service did not replace the scheduler entry and retain the configured API port.'
    }
    Write-Host '[release] NSSM service environment checks passed.'
} finally {
    if ($windows -and (Test-Path -LiteralPath $fixtureRegistry)) {
        Remove-Item -LiteralPath $fixtureRegistry
    }
    Remove-Item -LiteralPath $fixture.FullName -Recurse -Force
}
