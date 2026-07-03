#Requires -RunAsAdministrator
param(
    [string]$ServiceName = "WEBSTUDIO Server",
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS",
    [string]$NssmPath = "$InstallRoot\tools\nssm\nssm.exe"
)

$ErrorActionPreference = "Stop"

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "[WEBSTUDIO] Stopping $ServiceName..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & $NssmPath remove $ServiceName confirm
    Write-Host "[WEBSTUDIO] Service removed."
} else {
    Write-Host "[WEBSTUDIO] Service not installed."
}
