#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Ensures PostgreSQL Windows service is running before WEBSTUDIO Server starts.
#>
param(
    [string]$PostgresServiceName = "postgresql-x64-16"
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

Write-Step "Verifying PostgreSQL service ($PostgresServiceName)..."
$service = Get-Service -Name $PostgresServiceName -ErrorAction SilentlyContinue
if ($null -eq $service) {
    throw "PostgreSQL service '$PostgresServiceName' not found. Install PostgreSQL 16 and update -PostgresServiceName."
}

if ($service.Status -ne "Running") {
    Write-Step "Starting PostgreSQL..."
    Start-Service -Name $PostgresServiceName
    Start-Sleep -Seconds 5
}

$service.Refresh()
if ($service.Status -ne "Running") {
    throw "PostgreSQL failed to start."
}

Write-Step "PostgreSQL is running."
