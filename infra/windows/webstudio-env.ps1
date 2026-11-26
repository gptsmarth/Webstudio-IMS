#Requires -Version 5.1
<#
.SYNOPSIS
  Shared helpers for WEBSTUDIO Server .env and NSSM environment configuration.
#>

function Read-DotEnvFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path $Path)) {
        return $result
    }
    foreach ($line in Get-Content $Path) {
        $line = $line.TrimEnd("`r")
        if ($line -match '^\s*#' -or $line -match '^\s*$') {
            continue
        }
        if ($line -match '^([^=]+)=(.*)$') {
            $result[$matches[1].Trim()] = $matches[2].Trim().TrimEnd("`r")
        }
    }
    return $result
}

function Import-DotEnvIntoProcess {
    param([string]$Path)
    foreach ($entry in (Read-DotEnvFile -Path $Path).GetEnumerator()) {
        Set-Item -Path "env:$($entry.Key)" -Value $entry.Value
    }
}

function Wait-WebstudioReadiness {
    param([string]$ApiBaseUrl)

    $url = $ApiBaseUrl.TrimEnd('/') + '/health/ready'
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Write-Host '[WEBSTUDIO] /health/ready -> 200'
                return
            }
        } catch {
            # During service startup the listener or database may not be ready.
            Start-Sleep -Seconds 2
        }
    }
    throw 'WEBSTUDIO Server did not become ready. Verify the API URL and check logs\webstudio-api-error.log.'
}

function Sync-BackendEnvFile {
    param([string]$InstallRoot)
    $source = Join-Path $InstallRoot "config\env\.env"
    if (-not (Test-Path $source)) {
        throw "Missing production env file: $source"
    }
    $destDir = Join-Path $InstallRoot "apps\backend\config\env"
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    $service = Get-CimInstance -ClassName Win32_Service -Filter "Name='WEBSTUDIO Server'"
    $acl = New-Object System.Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @('S-1-5-18', 'S-1-5-32-544')) {
        $identity = [System.Security.Principal.SecurityIdentifier]::new($sid)
        $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl', 'Allow'))
    }
    if ($service.StartName -and $service.StartName -ne 'LocalSystem') {
        $name = $service.StartName -replace '^\.\\', "$env:COMPUTERNAME\"
        $identity = [System.Security.Principal.NTAccount]::new($name)
        $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new($identity, 'Read', 'Allow'))
    }
    Set-Acl -LiteralPath $source -AclObject $acl
    foreach ($destination in @((Join-Path $destDir '.env'), (Join-Path $InstallRoot 'apps\backend\.env'))) {
        if (-not (Test-Path -LiteralPath $destination)) {
            New-Item -Path $destination -ItemType File | Out-Null
        }
        Set-Acl -LiteralPath $destination -AclObject $acl
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }
    $updated = $false
    $lines = @(Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.TrimEnd("`r")
        if ($line -match "^$([regex]::Escape($Key))=") {
            $updated = $true
            "$Key=$Value"
        } else {
            $line
        }
    })
    if (-not $updated) {
        $lines += "$Key=$Value"
    }
    [System.IO.File]::WriteAllLines($Path, [string[]]$lines, [System.Text.UTF8Encoding]::new($false))
}

function Build-DatabaseUrl {
    param(
        [string]$User = "webstudio_app",
        [string]$Password,
        [string]$DbHost = "127.0.0.1",
        [int]$Port = 5432,
        [string]$Database = "webstudio"
    )
    $encodedPassword = [uri]::EscapeDataString($Password)
    return "postgresql+asyncpg://${User}:${encodedPassword}@${DbHost}:${Port}/${Database}"
}

function Repair-ProductionEnvFile {
    param(
        [string]$InstallRoot,
        [string]$EnvFile
    )
    $vars = Read-DotEnvFile -Path $EnvFile

    foreach ($tlsKey in @("TLS_CERT_PATH", "TLS_KEY_PATH")) {
        if (-not $vars.ContainsKey($tlsKey)) {
            continue
        }
        $path = $vars[$tlsKey]
        if ($path -and -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Configured $tlsKey file is missing. Restore the file or correct its path."
        }
    }

    if (-not $vars.ContainsKey("POSTGRES_BIN") -or -not $vars["POSTGRES_BIN"]) {
        $pgBin = Find-PostgresBin
        if ($pgBin) {
            Set-DotEnvValue -Path $EnvFile -Key "POSTGRES_BIN" -Value $pgBin
        }
    }

    if ($InstallRoot) {
        $updatesRoot = Join-Path $InstallRoot "Updates"
        if (-not $vars.ContainsKey("WEBSTUDIO_RELEASE_SYNC_SCHEDULER") -or -not $vars["WEBSTUDIO_RELEASE_SYNC_SCHEDULER"]) {
            Set-DotEnvValue -Path $EnvFile -Key "WEBSTUDIO_RELEASE_SYNC_SCHEDULER" -Value "1"
        }
        if (-not $vars.ContainsKey("WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS") -or -not $vars["WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS"]) {
            Set-DotEnvValue -Path $EnvFile -Key "WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS" -Value "900"
        }
        if (-not $vars.ContainsKey("WEBSTUDIO_RELEASE_UPDATES_ROOT") -or -not $vars["WEBSTUDIO_RELEASE_UPDATES_ROOT"]) {
            Set-DotEnvValue -Path $EnvFile -Key "WEBSTUDIO_RELEASE_UPDATES_ROOT" -Value $updatesRoot
        }
        if (-not $vars.ContainsKey("WEBSTUDIO_RELEASE_CHANNEL") -or -not $vars["WEBSTUDIO_RELEASE_CHANNEL"]) {
            Set-DotEnvValue -Path $EnvFile -Key "WEBSTUDIO_RELEASE_CHANNEL" -Value "stable"
        }
        if (-not (Test-Path $updatesRoot)) {
            New-Item -ItemType Directory -Path $updatesRoot -Force | Out-Null
        }
        $vars = Read-DotEnvFile -Path $EnvFile
    }

    if ($InstallRoot) {
        Sync-BackendEnvFile -InstallRoot $InstallRoot
    }
}

function Find-PostgresBin {
    $candidates = @()
    $roots = @(
        (Join-Path ${env:ProgramFiles} "PostgreSQL"),
        (Join-Path ${env:ProgramFiles(x86)} "PostgreSQL")
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) {
            continue
        }
        Get-ChildItem $root -Directory | Sort-Object Name -Descending | ForEach-Object {
            $bin = Join-Path $_.FullName "bin"
            if (Test-Path (Join-Path $bin "pg_dump.exe")) {
                $candidates += $bin
            }
        }
    }
    if ($candidates.Count -gt 0) {
        return $candidates[0]
    }
    return ""
}

function Ensure-DatabaseUrlConfigured {
    param(
        [string]$InstallRoot,
        [string]$EnvFile,
        [switch]$PromptIfPlaceholder
    )
    Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $EnvFile
    $vars = Read-DotEnvFile -Path $EnvFile
    $dbUrl = $vars["DATABASE_URL"]

    if ($dbUrl -and $dbUrl -notmatch ':CHANGE_ME@') {
        return $dbUrl
    }

    if (-not $PromptIfPlaceholder) {
        throw @"
DATABASE_URL in $EnvFile is not configured (contains CHANGE_ME or is empty).
Edit .env or run: infra\windows\finalize-server-setup.ps1
"@
    }

    Write-Host ""
    Write-Host "=== WEBSTUDIO database password ===" -ForegroundColor Cyan
    Write-Host "Enter the password for PostgreSQL user 'webstudio_app' (the IMS database login)."
    $password = [pscredential]::new('webstudio_app', (Read-Host 'webstudio_app password' -AsSecureString)).GetNetworkCredential().Password
    if (-not $password) {
        throw "Database password is required to continue setup."
    }

    $dbUrl = Build-DatabaseUrl -Password $password
    Set-DotEnvValue -Path $EnvFile -Key "DATABASE_URL" -Value $dbUrl
    Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $EnvFile
    return $dbUrl
}

function Get-NssmEnvironmentPairs {
    param(
        [string]$InstallRoot,
        [string]$EnvFile
    )
    if (-not $EnvFile) {
        $EnvFile = Join-Path $InstallRoot "config\env\.env"
    }
    if (-not (Test-Path $EnvFile)) {
        throw "Missing production env file: $EnvFile"
    }
    Repair-ProductionEnvFile -InstallRoot $InstallRoot -EnvFile $EnvFile
    Sync-BackendEnvFile -InstallRoot $InstallRoot
    $vars = Read-DotEnvFile -Path $EnvFile

    $keys = @(
        "APP_ENV",
        "API_HOST",
        "API_PORT",
        "POSTGRES_BIN",
        "WEBSTUDIO_DATA_ROOT",
        "WEBSTUDIO_DISCOVERY_CANDIDATES",
        "TLS_CERT_PATH",
        "TLS_KEY_PATH",
        "TLS_REQUIRED",
        "RATE_LIMIT_ENABLED",
        "RATE_LIMIT_PER_MINUTE",
        "AUTH_RATE_LIMIT_PER_MINUTE",
        "WEBSTUDIO_TALLY_SCHEDULER",
        "WEBSTUDIO_BACKUP_SCHEDULER",
        "WEBSTUDIO_NOTIFICATION_SCHEDULER",
        "WEBSTUDIO_MAINTENANCE_SCHEDULER",
        "WEBSTUDIO_RELEASE_SYNC_SCHEDULER",
        "WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS",
        "WEBSTUDIO_RELEASE_UPDATES_ROOT",
        "WEBSTUDIO_RELEASE_CHANNEL",
        "WEBSTUDIO_GITHUB_REPO",
        "WEBSTUDIO_CLOUD_BACKUP_SYNC_SCHEDULER",
        "GOOGLE_DRIVE_CLIENT_ID"
    )

    $pairs = @()
    foreach ($key in $keys) {
        $value = ""
        if ($vars.ContainsKey($key)) {
            $value = $vars[$key]
        }
        if ($key -eq "APP_ENV" -and -not $value) { $value = "production" }
        if ($key -eq "API_HOST" -and -not $value) { $value = "0.0.0.0" }
        if ($key -eq "API_PORT" -and -not $value) { $value = "8000" }
        if ($key -eq "WEBSTUDIO_DATA_ROOT" -and -not $value) { $value = $InstallRoot }
        if ($key -match '^WEBSTUDIO_.*_SCHEDULER$' -and -not $value) { $value = "1" }
        if ($value) {
            $pairs += "${key}=$value"
        }
    }

    $pgBin = ""
    if ($vars.ContainsKey("POSTGRES_BIN") -and $vars["POSTGRES_BIN"]) {
        $pgBin = $vars["POSTGRES_BIN"]
    } else {
        $pgBin = Find-PostgresBin
    }
    if ($pgBin) {
        $pairs += "PATH=${pgBin};C:\Windows\System32;C:\Windows"
    }

    return $pairs
}

function Get-NssmServiceParametersRegPath {
    param([string]$ServiceName = "WEBSTUDIO Server")
    return "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName\Parameters"
}

function Apply-NssmServiceEnvironment {
    param(
        [string]$InstallRoot,
        [string]$ServiceName = "WEBSTUDIO Server",
        [string]$EnvFile = "",
        [string]$NssmPath = ""
    )
    if (-not $EnvFile) {
        $EnvFile = Join-Path $InstallRoot "config\env\.env"
    }
    if (-not $NssmPath) {
        $NssmPath = Join-Path $InstallRoot "tools\nssm\nssm.exe"
    }
    if (-not (Test-Path $NssmPath)) {
        throw "NSSM not found at $NssmPath"
    }
    [string[]]$pairs = @(Get-NssmEnvironmentPairs -InstallRoot $InstallRoot -EnvFile $EnvFile)
    if ($pairs.Count -eq 0) {
        throw "No NSSM environment pairs generated from $EnvFile"
    }

    $regPath = Get-NssmServiceParametersRegPath -ServiceName $ServiceName
    if (-not (Test-Path $regPath)) {
        throw "Service Parameters registry key not found: $regPath"
    }

    # The backend loads secrets from its restricted .env files. Avoid exposing any
    # service settings in a native process command line.
    Set-ItemProperty -LiteralPath $regPath -Name "AppEnvironmentExtra" -Value $pairs -Type MultiString -ErrorAction Stop

    $stored = (Get-ItemProperty -LiteralPath $regPath -Name "AppEnvironmentExtra" -ErrorAction Stop).AppEnvironmentExtra
    if ($stored -isnot [string[]] -or ($stored -join "`0") -cne ($pairs -join "`0")) {
        throw "The NSSM environment was not stored correctly in $regPath\AppEnvironmentExtra"
    }
    Write-Host "[WEBSTUDIO] NSSM environment applied ($($pairs.Count) vars)."
}
