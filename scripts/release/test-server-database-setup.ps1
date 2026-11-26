#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$repo = Join-Path $PSScriptRoot '..\..'
. (Join-Path $repo 'infra\windows\server-installer\postgres-setup.ps1')
. (Join-Path $repo 'infra\windows\webstudio-env.ps1')

$fixtureEnv = [System.IO.Path]::GetTempFileName()
try {
    $fixtureUrl = 'postgresql+asyncpg://webstudio_app:fixture%40text@localhost:5540/webstudio'
    Set-Content -LiteralPath $fixtureEnv -Value "DATABASE_URL=$fixtureUrl"
    Set-DotEnvValue -Path $fixtureEnv -Key 'POSTGRES_BIN' -Value 'C:\PostgreSQL\bin'
    $saved = Read-DotEnvFile -Path $fixtureEnv
    if ([System.IO.File]::ReadAllBytes($fixtureEnv)[0] -ne [byte][char]'D' -or
        $saved['DATABASE_URL'] -ne $fixtureUrl -or $saved['POSTGRES_BIN'] -ne 'C:\PostgreSQL\bin') {
        throw 'Updating .env changed the existing database URL or its file encoding.'
    }
} finally {
    Remove-Item -LiteralPath $fixtureEnv
}

$service = [pscustomobject]@{ Name = 'postgresql-x64-18'; Status = 'Running' }
# Emulate the missing Count property on scalar custom objects in Windows PowerShell 5.1.
$service | Add-Member -MemberType NoteProperty -Name Count -Value $null
$service | Add-Member -MemberType ScriptMethod -Name WaitForStatus -Value {}

function Get-Service {
    [CmdletBinding()]
    param([string]$Name)
    if ($Name -eq 'WEBSTUDIO Server') {
        if ($script:existingIms) { return [pscustomobject]@{ Name = 'WEBSTUDIO Server' } }
    } elseif ($script:installed) {
        return $script:service
    }
}
function Get-NetTCPConnection {
    [CmdletBinding()]
    param([int]$LocalPort, [string]$State)
}
function Install-SetupPostgres {
    param([string]$AdminPassword)
    if ($AdminPassword -ne 'admin-fixture-password') { throw 'Wrong fixture password.' }
    $script:installed = $true
    $script:actions.Add('install')
}
function Restart-Service { param($InputObject) }
function Get-ItemProperty {
    param([string]$LiteralPath, [string]$Name)
    @{ ImagePath = '"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" runservice' }
}
function Split-Path { param([switch]$Parent, [string]$Path) $PSScriptRoot }
function Test-Path { param([string]$LiteralPath, [string]$PathType) $true }
function Read-Host { param([string]$Prompt) '' }
function Read-SetupDatabasePassword {
    param([string]$Prompt, [switch]$Confirm)
    if ($Prompt -match 'postgres\) password') { return 'admin-fixture-password' }
    return 'app-fixture-password'
}
function Invoke-SetupPsql {
    param(
        [string]$Psql, [int]$Port, [string]$User, [string]$Database,
        [string]$Password, [string]$Sql, [string]$NewRolePassword
    )
    if ($Sql.StartsWith('ALTER SYSTEM')) {
        $script:actions.Add('local-only')
    } elseif ($Sql -match 'CREATE ROLE') {
        if ($NewRolePassword -ne 'app-fixture-password') { throw 'Wrong application password.' }
        $script:actions.Add('create-role')
    } elseif ($Sql.StartsWith('CREATE DATABASE')) {
        $script:actions.Add('create-database')
        $script:databaseExists = $true
    } elseif ($Sql -eq 'SELECT 1;') {
        return @{ Succeeded = $script:databaseExists; Output = @(1) }
    } elseif ($Sql -match 'SELECT EXISTS') {
        $exists = if ($script:databaseExists) { 't' } else { 'f' }
        return @{ Succeeded = $true; Output = @('t', $exists, 'f') }
    }
    return @{ Succeeded = $true; Output = @('t') }
}
function Set-DotEnvValue {
    param([string]$Path, [string]$Key, [string]$Value)
    $script:settings[$Key] = $Value
}
function Read-DotEnvFile { param([string]$Path) $script:settings }
function Build-DatabaseUrl { param([string]$Password, [int]$Port) "configured:$Password`:$Port" }

$script:actions = [System.Collections.Generic.List[string]]::new()
$script:settings = @{}
$script:installed = $false
$script:databaseExists = $false
$script:existingIms = $false
Ensure-SetupDatabase -EnvFile 'fixture.env'
if (($script:actions -join ',') -ne 'install,local-only,create-role,create-database' -or
    $script:settings['DATABASE_URL'] -ne 'configured:app-fixture-password:5432') {
    throw 'Fresh PostgreSQL setup failed to provision the expected instance.'
}

$script:actions.Clear()
$result = Initialize-SetupDatabase -EnvFile 'fixture.env' -Manual
if ($result -ne 'postgresql-x64-18' -or $script:actions.Count -ne 0) {
    throw 'Manual setup changed an existing PostgreSQL database.'
}

$script:installed = $false
try {
    Initialize-SetupDatabase -EnvFile 'fixture.env' -Manual
    throw 'Manual setup unexpectedly succeeded without PostgreSQL.'
} catch {
    if ($_.Exception.Message -notmatch 'rerun setup in manual mode') { throw }
}
if ($script:actions.Count -ne 0) { throw 'Manual setup tried automatic provisioning.' }

$script:existingIms = $true
$script:settings['DATABASE_URL'] = 'postgresql+asyncpg://existing:fixture@localhost:5540/ims_custom'
Ensure-SetupDatabase -EnvFile 'fixture.env'
Ensure-SetupDatabase -EnvFile 'fixture.env' -Manual -PostgresServiceName 'unused-service'
if ($script:actions.Count -ne 0 -or
    $script:settings['DATABASE_URL'] -ne 'postgresql+asyncpg://existing:fixture@localhost:5540/ims_custom') {
    throw 'Upgrade replaced the existing database configuration.'
}
$script:settings['DATABASE_URL'] = 'postgresql+asyncpg://webstudio_app:CHANGE_ME@127.0.0.1:5432/webstudio'
try {
    Ensure-SetupDatabase -EnvFile 'fixture.env'
    throw 'Upgrade unexpectedly accepted a placeholder database password.'
} catch {
    if ($_.Exception.Message -notmatch 'already has an IMS service') { throw }
}
if ($script:actions.Count -ne 0) { throw 'An unconfigured upgrade tried automatic provisioning.' }
Write-Host '[release] PostgreSQL setup checks passed.'
