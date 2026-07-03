#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Configures Windows Service Recovery actions for WEBSTUDIO Server.
#>
param(
    [string]$ServiceName = "WEBSTUDIO Server",
    [int]$ResetFailCountSeconds = 86400,
    [string]$RestartComputer = "none"
)

$ErrorActionPreference = "Stop"

# sc.exe failure actions: restart after 60s for first 3 failures within reset period
& sc.exe failure $ServiceName reset= $ResetFailCountSeconds actions= restart/60000/restart/60000/restart/60000
& sc.exe failureflag $ServiceName 1

Write-Host "[WEBSTUDIO] Recovery configured for $ServiceName (restart on failure, reset after $ResetFailCountSeconds s)."
