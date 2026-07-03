#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Ensures PostgreSQL Windows service is running before WEBSTUDIO Server starts.
#>
param(
    [string]$PostgresServiceName = ""
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

$resolvedName = & "$PSScriptRoot\resolve-postgresql-service.ps1" -PostgresServiceName $PostgresServiceName

Write-Step "Verifying PostgreSQL service ($resolvedName)..."
$service = Get-Service -Name $resolvedName -ErrorAction Stop

if ($service.Status -ne "Running") {
    Write-Step "Starting PostgreSQL..."
    Start-Service -Name $resolvedName
    Start-Sleep -Seconds 5
}

$service.Refresh()
if ($service.Status -ne "Running") {
    throw "PostgreSQL failed to start."
}

Write-Step "PostgreSQL is running."
