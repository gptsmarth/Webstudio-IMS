#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Business-day startup: PostgreSQL → WEBSTUDIO Server (delayed auto-start handles API).
#>
param(
    [string]$PostgresServiceName = "",
    [string]$WebstudioServiceName = "WEBSTUDIO Server"
)

$ErrorActionPreference = "Stop"

& "$PSScriptRoot\ensure-postgresql.ps1" -PostgresServiceName $PostgresServiceName

$service = Get-Service -Name $WebstudioServiceName -ErrorAction SilentlyContinue
if ($null -eq $service) {
    throw "WEBSTUDIO Server service is not installed. Run install-webstudio-service.ps1 first."
}

if ($service.Status -ne "Running") {
    Write-Host "[WEBSTUDIO] Starting WEBSTUDIO Server Service..."
    Start-Service -Name $WebstudioServiceName
}

Write-Host "[WEBSTUDIO] Business-day startup complete."
