<#
.SYNOPSIS
  Resolves the PostgreSQL Windows service name (postgresql-x64-*).
.OUTPUTS
  Service name string
#>
param(
    [string]$PostgresServiceName = ""
)

$ErrorActionPreference = "Stop"

if ($PostgresServiceName) {
    $explicit = Get-Service -Name $PostgresServiceName -ErrorAction SilentlyContinue
    if ($null -ne $explicit) {
        return $PostgresServiceName
    }
    Write-Warning "[WEBSTUDIO] PostgreSQL service '$PostgresServiceName' not found; auto-detecting..."
}

$candidates = @(Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^postgresql-x64-\d+$' } |
    Sort-Object Name)

if ($candidates.Count -eq 0) {
    throw @"
PostgreSQL Windows service not found (expected name like postgresql-x64-16 or postgresql-x64-18).
Install PostgreSQL 16 or newer, create the webstudio database, then re-run post-install.
"@
}

if ($candidates.Count -gt 1) {
    $names = ($candidates | ForEach-Object { $_.Name }) -join ", "
    Write-Warning "[WEBSTUDIO] Multiple PostgreSQL services found ($names); using $($candidates[0].Name)"
}

return $candidates[0].Name
