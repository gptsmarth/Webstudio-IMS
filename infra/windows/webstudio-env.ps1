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
    Copy-Item $source (Join-Path $destDir ".env") -Force
    Copy-Item $source (Join-Path $InstallRoot "apps\backend\.env") -Force
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
    $lines = Get-Content $Path | ForEach-Object {
        $line = $_.TrimEnd("`r")
        if ($line -match "^$([regex]::Escape($Key))=") {
            $updated = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $updated) {
        $lines += "$Key=$Value"
    }
    Set-Content -Path $Path -Value $lines -Encoding UTF8
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

    if ($vars.ContainsKey("DATABASE_URL") -and $vars["DATABASE_URL"] -match '@localhost') {
        Set-DotEnvValue -Path $EnvFile -Key "DATABASE_URL" -Value ($vars["DATABASE_URL"] -replace '@localhost', '@127.0.0.1')
        $vars = Read-DotEnvFile -Path $EnvFile
    }

    foreach ($tlsKey in @("TLS_CERT_PATH", "TLS_KEY_PATH")) {
        if (-not $vars.ContainsKey($tlsKey)) {
            continue
        }
        $path = $vars[$tlsKey]
        if ($path -and -not (Test-Path $path)) {
            Set-DotEnvValue -Path $EnvFile -Key $tlsKey -Value ""
        }
    }

    if ($vars.ContainsKey("API_PORT") -and $vars["API_PORT"] -eq "8443") {
        Set-DotEnvValue -Path $EnvFile -Key "API_PORT" -Value "8000"
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

    if ($dbUrl -and $dbUrl -notmatch 'CHANGE_ME') {
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
    Write-Host "Enter the password for PostgreSQL user 'webstudio_app' (from pgAdmin Part C2)."
    $password = Read-Host "webstudio_app password"
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
        "DATABASE_URL",
        "POSTGRES_BIN",
        "JWT_SECRET",
        "WEBSTUDIO_DATA_ROOT",
        "WEBSTUDIO_DISCOVERY_CANDIDATES",
        "TLS_CERT_PATH",
        "TLS_KEY_PATH",
        "WEBSTUDIO_TALLY_SCHEDULER",
        "WEBSTUDIO_BACKUP_SCHEDULER",
        "WEBSTUDIO_NOTIFICATION_SCHEDULER",
        "WEBSTUDIO_MAINTENANCE_SCHEDULER",
        "WEBSTUDIO_RELEASE_SYNC_SCHEDULER",
        "WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS",
        "WEBSTUDIO_RELEASE_UPDATES_ROOT",
        "WEBSTUDIO_RELEASE_CHANNEL",
        "WEBSTUDIO_GITHUB_REPO",
        "WEBSTUDIO_GITHUB_TOKEN",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY"
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

    return ,@($pairs)
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
    $pairs = @(Get-NssmEnvironmentPairs -InstallRoot $InstallRoot -EnvFile $EnvFile)
    if ($pairs.Count -eq 0) {
        throw "No NSSM environment pairs generated from $EnvFile"
    }

    $regPath = Get-NssmServiceParametersRegPath -ServiceName $ServiceName
    if (-not (Test-Path $regPath)) {
        throw "Service Parameters registry key not found: $regPath"
    }

    # Registry write is reliable when PowerShell argument parsing breaks nssm.exe set.
    Set-ItemProperty -Path $regPath -Name "AppEnvironmentExtra" -Value $pairs -Type MultiString

    & $NssmPath set $ServiceName AppEnvironmentExtra @pairs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply NSSM environment for $ServiceName"
    }

    $stored = @((Get-ItemProperty -Path $regPath -Name "AppEnvironmentExtra" -ErrorAction Stop).AppEnvironmentExtra)
    $tallyPair = @($stored | Where-Object { $_ -like "WEBSTUDIO_TALLY_SCHEDULER=*" })
    if ($tallyPair.Count -eq 0) {
        throw "WEBSTUDIO_TALLY_SCHEDULER was not stored in $regPath\AppEnvironmentExtra"
    }
    Write-Host "[WEBSTUDIO] NSSM environment applied ($($pairs.Count) vars). $($tallyPair[0])"
}
