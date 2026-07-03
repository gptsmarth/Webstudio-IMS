#Requires -Version 5.1
<#
.SYNOPSIS
  Build WEBSTUDIO Desktop Setup.exe (Windows x64).
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
Push-Location (Join-Path $RepoRoot "apps/desktop")

Write-Host "[release] Building desktop renderer + electron..."
pnpm build

Write-Host "[release] Packaging NSIS installer..."
pnpm exec electron-builder --win --config electron-builder.yml

Pop-Location
Write-Host "[release] Output: apps/desktop/release/desktop/"
