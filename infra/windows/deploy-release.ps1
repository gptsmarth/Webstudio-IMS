#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Stop or start WEBSTUDIO Server, or migrate its installed database.
.DESCRIPTION
  Apply Windows production releases through WEBSTUDIO Server Setup. The migrate action
  uses the installed Python runtime and database configuration while the service is stopped.
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
    $service = Get-Service -Name $WebstudioServiceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne 'Stopped') {
        throw "Stop $WebstudioServiceName before migrating the installed database."
    }
    $pythonExe = & "$PSScriptRoot\ensure-python-runtime.ps1" -InstallRoot $InstallRoot
    & "$PSScriptRoot\run-alembic-upgrade.ps1" -InstallRoot $InstallRoot -PythonExe $pythonExe
}

switch ($Action) {
    "stop" { Stop-WebstudioService }
    "start" { Start-WebstudioService }
    "migrate" { Invoke-AlembicUpgrade }
}

Write-Host "[DEPLOY] Action '$Action' completed."
