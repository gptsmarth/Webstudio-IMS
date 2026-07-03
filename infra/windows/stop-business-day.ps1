#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Graceful evening shutdown: stop WEBSTUDIO Server (graceful) then optionally PostgreSQL.
#>
param(
    [string]$WebstudioServiceName = "WEBSTUDIO Server",
    [string]$PostgresServiceName = "postgresql-x64-16",
    [switch]$StopPostgreSQL,
    [int]$GracefulWaitSeconds = 45
)

$ErrorActionPreference = "Stop"

$service = Get-Service -Name $WebstudioServiceName -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Host "[WEBSTUDIO] Requesting graceful shutdown of $WebstudioServiceName..."
    Stop-Service -Name $WebstudioServiceName -Force:$false
    $deadline = (Get-Date).AddSeconds($GracefulWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        $service.Refresh()
        if ($service.Status -eq "Stopped") { break }
        Start-Sleep -Seconds 2
    }
    if ($service.Status -ne "Stopped") {
        Write-Warning "Service did not stop within ${GracefulWaitSeconds}s — forcing stop."
        Stop-Service -Name $WebstudioServiceName -Force
    }
    Write-Host "[WEBSTUDIO] WEBSTUDIO Server stopped."
}

if ($StopPostgreSQL) {
    $pg = Get-Service -Name $PostgresServiceName -ErrorAction SilentlyContinue
    if ($pg -and $pg.Status -eq "Running") {
        Write-Host "[WEBSTUDIO] Stopping PostgreSQL..."
        Stop-Service -Name $PostgresServiceName
    }
}

Write-Host "[WEBSTUDIO] Evening shutdown complete."
