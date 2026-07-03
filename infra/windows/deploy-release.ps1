#Requires -RunAsAdministrator
<#
.SYNOPSIS
  External helper for Enterprise Deployment Engine — stop/start WEBSTUDIO Server during release swap.
.DESCRIPTION
  Invoked by deployment_platform_adapter when the in-process API cannot restart itself.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("stop", "start", "migrate")]
    [string]$Action,
    [string]$WebstudioServiceName = "WEBSTUDIO Server",
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$BundleDir = "",
    [int]$GracefulWaitSeconds = 45
)

$ErrorActionPreference = "Stop"

function Stop-WebstudioService {
    $service = Get-Service -Name $WebstudioServiceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq "Running") {
        Write-Host "[DEPLOY] Stopping $WebstudioServiceName..."
        Stop-Service -Name $WebstudioServiceName -Force:$false
        $deadline = (Get-Date).AddSeconds($GracefulWaitSeconds)
        while ((Get-Date) -lt $deadline) {
            $service.Refresh()
            if ($service.Status -eq "Stopped") { break }
            Start-Sleep -Seconds 2
        }
        if ($service.Status -ne "Stopped") {
            Stop-Service -Name $WebstudioServiceName -Force
        }
    }
}

function Start-WebstudioService {
    $service = Get-Service -Name $WebstudioServiceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne "Running") {
        Write-Host "[DEPLOY] Starting $WebstudioServiceName..."
        Start-Service -Name $WebstudioServiceName
    }
}

function Invoke-AlembicUpgrade {
    $alembicIni = Join-Path $InstallRoot "database\migrations\alembic.ini"
    if (-not (Test-Path $alembicIni)) {
        throw "Alembic config not found: $alembicIni"
    }
    Push-Location (Split-Path $alembicIni)
    try {
        python -m alembic -c $alembicIni upgrade head
        if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed with exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
}

switch ($Action) {
    "stop" { Stop-WebstudioService }
    "start" { Start-WebstudioService }
    "migrate" { Invoke-AlembicUpgrade }
}

Write-Host "[DEPLOY] Action '$Action' completed."
