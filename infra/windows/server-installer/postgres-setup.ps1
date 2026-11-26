#Requires -Version 5.1

function Read-SetupDatabasePassword {
    param([string]$Prompt, [switch]$Confirm)

    do {
        $password = [pscredential]::new('postgresql', (Read-Host $Prompt -AsSecureString)).GetNetworkCredential().Password
        if (-not $password) { throw 'A database password is required.' }
        if (-not $Confirm) { return $password }
        $confirmation = [pscredential]::new('postgresql', (Read-Host 'Confirm password' -AsSecureString)).GetNetworkCredential().Password
        if ($password -ceq $confirmation -and $password.Length -ge 12) { return $password }
        Write-Host 'Enter matching passwords with at least 12 characters.' -ForegroundColor Yellow
    } while ($true)
}

function Install-SetupPostgres {
    param([string]$AdminPassword)

    $url = 'https://get.enterprisedb.com/postgresql/postgresql-18.7-1-windows-x64.exe'
    $expectedHash = '90BF244854A6C7F6D204B26934A32BD571B9953963B6137BB46D2FCD3F1A313E'
    $work = Join-Path ([System.IO.Path]::GetTempPath()) ('webstudio-postgres-' + [guid]::NewGuid().ToString('N'))
    $acl = New-Object System.Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @('S-1-5-18', 'S-1-5-32-544')) {
        $identity = [System.Security.Principal.SecurityIdentifier]::new($sid)
        $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
            $identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
        ))
    }
    [System.IO.Directory]::CreateDirectory($work, $acl) | Out-Null
    try {
        $installer = Join-Path $work 'postgresql-installer.exe'
        Write-Host '[WEBSTUDIO] Downloading PostgreSQL 18 from EDB...'
        $ProgressPreference = 'SilentlyContinue'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing -TimeoutSec 600
        if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expectedHash) {
            throw 'PostgreSQL installer checksum failed. Use a verified installer or contact support.'
        }

        $options = Join-Path $work 'install-options.txt'
        [System.IO.File]::WriteAllLines($options, @(
            'serverport=5432'
            'servicename=postgresql-x64-18'
            'disable-components=stackbuilder'
            "superpassword=$AdminPassword"
        ), [System.Text.UTF8Encoding]::new($false))
        Write-Host '[WEBSTUDIO] Installing PostgreSQL 18 and its command-line tools...'
        $arguments = "--mode unattended --unattendedmodeui minimal --optionfile `"$options`""
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "PostgreSQL setup returned exit code $($process.ExitCode). Check the PostgreSQL installation before retrying."
        }
    } finally {
        Remove-Item -LiteralPath $work -Recurse -Force
    }
}

function Invoke-SetupPsql {
    param(
        [string]$Psql, [int]$Port, [string]$User, [string]$Database,
        [string]$Password, [string]$Sql, [string]$NewRolePassword
    )

    $oldPassword = $env:PGPASSWORD
    $oldRolePassword = $env:WEBSTUDIO_SETUP_ROLE_PASSWORD
    try {
        $env:PGPASSWORD = $Password
        $env:WEBSTUDIO_SETUP_ROLE_PASSWORD = $NewRolePassword
        $ErrorActionPreference = 'Continue'
        $output = $Sql | & $Psql -X -w -qAt -h 127.0.0.1 -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 2>$null
        return [pscustomobject]@{ Succeeded = ($LASTEXITCODE -eq 0); Output = @($output) }
    } finally {
        $env:PGPASSWORD = $oldPassword
        $env:WEBSTUDIO_SETUP_ROLE_PASSWORD = $oldRolePassword
    }
}

function Initialize-SetupDatabase {
    param([string]$EnvFile, [string]$PostgresServiceName, [switch]$Manual)

    $services = @(
        if ($PostgresServiceName) {
            Get-Service -Name $PostgresServiceName
        } else {
            Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue
        }
    )
    if (-not $services.Count) {
        if ($Manual -or $PostgresServiceName) {
            throw 'Install PostgreSQL and create the webstudio database and webstudio_app login, then rerun setup in manual mode.'
        }
        if (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue) {
            throw 'Port 5432 is already in use. Identify the existing PostgreSQL instance before continuing.'
        }
        $adminPassword = Read-SetupDatabasePassword -Prompt 'Choose the PostgreSQL administrator (postgres) password' -Confirm
        Install-SetupPostgres -AdminPassword $adminPassword
        $PostgresServiceName = 'postgresql-x64-18'
        $port = 5432
    } else {
        if (-not $PostgresServiceName -and $services.Count -gt 1) {
            Write-Host ('PostgreSQL services: ' + ($services.Name -join ', '))
            $PostgresServiceName = Read-Host 'Enter the PostgreSQL service for WEBSTUDIO'
            if (-not $PostgresServiceName) { throw 'Select a PostgreSQL service and rerun setup.' }
        }
        if (-not $PostgresServiceName) { $PostgresServiceName = $services[0].Name }
        $portValue = Read-Host 'PostgreSQL port [5432]'
        if (-not $portValue) { $portValue = '5432' }
        if ($portValue -notmatch '^\d{1,5}$' -or [int]$portValue -lt 1 -or [int]$portValue -gt 65535) {
            throw 'Enter a valid PostgreSQL port.'
        }
        $port = [int]$portValue
    }

    $service = Get-Service -Name $PostgresServiceName
    if ($service.Status -ne 'Running') { Start-Service -InputObject $service }
    $serviceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\$PostgresServiceName"
    $imagePath = (Get-ItemProperty -LiteralPath $serviceKey -Name ImagePath).ImagePath
    if ($imagePath -notmatch '^\s*"?([^"]*?\\(?:pg_ctl|postgres)\.exe)"?(?:\s|$)') {
        throw 'Could not find the PostgreSQL executable for the selected service.'
    }
    $bin = Split-Path -Parent ([Environment]::ExpandEnvironmentVariables($Matches[1]))
    $psql = Join-Path $bin 'psql.exe'
    if (-not (Test-Path -LiteralPath $psql -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $bin 'pg_dump.exe') -PathType Leaf)) {
        throw 'Install the PostgreSQL command-line tools for the selected service.'
    }

    if ($adminPassword) {
        $localOnly = Invoke-SetupPsql -Psql $psql -Port $port -User 'postgres' -Database 'postgres' -Password $adminPassword -Sql "ALTER SYSTEM SET listen_addresses = 'localhost';"
        if (-not $localOnly.Succeeded) { throw 'Could not configure the new PostgreSQL server for local access.' }
        Restart-Service -InputObject $service
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
    }

    $appPassword = Read-SetupDatabasePassword -Prompt 'Enter the webstudio_app password (choose one if the login is new)' -Confirm:([bool]$adminPassword)
    $appArgs = @{ Psql = $psql; Port = $port; User = 'webstudio_app'; Password = $appPassword }
    $ready = Invoke-SetupPsql @appArgs -Database 'webstudio' -Sql 'SELECT 1;'
    if (-not $ready.Succeeded) {
        if ($Manual) { throw 'Could not connect to webstudio as webstudio_app. Check the database, password, and port, then rerun setup.' }
        if (-not $adminPassword) {
            $adminPassword = Read-SetupDatabasePassword -Prompt 'Enter the existing PostgreSQL administrator (postgres) password'
        }
        $adminArgs = @{ Psql = $psql; Port = $port; User = 'postgres'; Database = 'postgres'; Password = $adminPassword }
        $check = Invoke-SetupPsql @adminArgs -Sql @'
SELECT current_setting('server_version_num')::integer >= 160000;
SELECT EXISTS (SELECT FROM pg_database WHERE datname = 'webstudio');
SELECT EXISTS (SELECT FROM pg_roles WHERE rolname = 'webstudio_app');
'@
        if (-not $check.Succeeded) { throw 'Could not authenticate to PostgreSQL as postgres. Verify the selected service, port, and password.' }
        if ($check.Output[0] -ne 't') { throw 'WEBSTUDIO requires PostgreSQL 16 or newer.' }
        if ($check.Output[1] -eq 't') { throw 'The webstudio database already exists. Rerun setup with the existing application password.' }
        if ($check.Output[2] -eq 't') {
            $login = Invoke-SetupPsql @appArgs -Database 'postgres' -Sql 'SELECT 1;'
            if (-not $login.Succeeded) { throw 'The webstudio_app login already exists. Rerun setup with its existing password.' }
        } else {
            if ($appPassword.Length -lt 12 -or $appPassword -ceq $adminPassword) {
                throw 'Choose a separate webstudio_app password with at least 12 characters, then rerun setup.'
            }
            $createRole = Invoke-SetupPsql @adminArgs -NewRolePassword $appPassword -Sql @'
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
SET log_min_duration_statement = -1;
SET log_min_duration_sample = -1;
SET log_duration = off;
SET password_encryption = 'scram-sha-256';
\getenv app_password WEBSTUDIO_SETUP_ROLE_PASSWORD
CREATE ROLE webstudio_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
'@
            if (-not $createRole.Succeeded) { throw 'Could not create the webstudio_app login. Review PostgreSQL configuration and retry.' }
        }
        $created = Invoke-SetupPsql @adminArgs -Sql 'CREATE DATABASE webstudio OWNER webstudio_app;'
        if (-not $created.Succeeded) { throw 'Could not create the webstudio database. Verify PostgreSQL health and retry.' }
    }

    $verified = Invoke-SetupPsql @appArgs -Database 'webstudio' -Sql @'
SELECT current_setting('server_version_num')::integer >= 160000
   AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
FROM pg_roles WHERE rolname = current_user;
'@
    if (-not $verified.Succeeded -or $verified.Output[0] -ne 't') {
        throw 'Use PostgreSQL 16 or newer and a dedicated, unprivileged webstudio_app login.'
    }
    Set-DotEnvValue -Path $EnvFile -Key 'POSTGRES_BIN' -Value $bin
    Set-DotEnvValue -Path $EnvFile -Key 'DATABASE_URL' -Value (Build-DatabaseUrl -Password $appPassword -Port $port)
    return $PostgresServiceName
}

function Ensure-SetupDatabase {
    param([string]$EnvFile, [string]$PostgresServiceName, [switch]$Manual)

    $dbUrl = (Read-DotEnvFile -Path $EnvFile)['DATABASE_URL']
    if ($dbUrl -and $dbUrl -notmatch ':CHANGE_ME@') {
        # Alembic will connect to this exact database and stop the install if
        # authentication fails. Provisioning must not run on a configured server.
        return
    }
    if (Get-Service -Name 'WEBSTUDIO Server' -ErrorAction SilentlyContinue) {
        throw 'This server already has an IMS service. Configure its existing DATABASE_URL before upgrading.'
    }
    Initialize-SetupDatabase -EnvFile $EnvFile -PostgresServiceName $PostgresServiceName -Manual:$Manual | Out-Null
}
