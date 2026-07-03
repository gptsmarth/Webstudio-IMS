<#
.SYNOPSIS
  Returns the Python executable used by WEBSTUDIO Server on Windows.
.OUTPUTS
  Full path to python.exe
#>
param(
    [string]$InstallRoot = "D:\WEBSTUDIO-IMS"
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[WEBSTUDIO] $Message"
}

function Test-SystemPython([string]$Command, [string[]]$Arguments) {
    try {
        $output = & $Command @Arguments --version 2>&1 | Out-String
        return $output -match "Python 3\.(1[2-9]|[2-9]\d)"
    } catch {
        return $false
    }
}

function Invoke-SystemPython([string]$Command, [string[]]$Arguments, [string[]]$CommandArgs) {
    & $Command @Arguments @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ') $($CommandArgs -join ' ') (exit $LASTEXITCODE)"
    }
}

$BundledPython = Join-Path $InstallRoot "runtime\python\python.exe"
$LegacyVenvPython = Join-Path $InstallRoot "venv\Scripts\python.exe"

if (Test-Path $BundledPython) {
    return $BundledPython
}

if (Test-Path $LegacyVenvPython) {
    Write-Step "Using legacy venv Python at $LegacyVenvPython"
    return $LegacyVenvPython
}

Write-Step "Bundled runtime not found; creating venv from system Python 3.12+..."

$launcher = $null
$launcherArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    if (Test-SystemPython "py" @("-3.12")) {
        $launcher = "py"
        $launcherArgs = @("-3.12")
    } elseif (Test-SystemPython "py" @("-3")) {
        $launcher = "py"
        $launcherArgs = @("-3")
    }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    if (Test-SystemPython "python" @()) {
        $launcher = "python"
        $launcherArgs = @()
    }
}

if (-not $launcher) {
    throw @"
Python runtime not found under $InstallRoot\runtime\python or $InstallRoot\venv.
Re-run WEBSTUDIO Server Setup.exe from the latest release, or install Python 3.12+ and re-run server-install-post.ps1.
"@
}

$VenvDir = Join-Path $InstallRoot "venv"
if (-not (Test-Path $VenvDir)) {
    Invoke-SystemPython $launcher $launcherArgs @("-m", "venv", $VenvDir)
}

$CreatedPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $CreatedPython)) {
    throw "venv creation did not produce $CreatedPython"
}

return $CreatedPython
