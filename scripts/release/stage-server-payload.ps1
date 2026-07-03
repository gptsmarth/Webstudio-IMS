#Requires -Version 5.1
<#
.SYNOPSIS
  Stage bundled Python runtime, backend dependencies, and NSSM for WEBSTUDIO Server Setup.exe.
#>
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$PythonVersion = "3.12.8",
    [string]$NssmVersion = "2.24"
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[release:server-payload] $Message"
}

$StagingRoot = Join-Path $RepoRoot "release\server\staging"
$RuntimeDir = Join-Path $StagingRoot "runtime\python"
$NssmDir = Join-Path $StagingRoot "tools\nssm"
$BackendDir = Join-Path $RepoRoot "apps\backend"
$CacheDir = Join-Path $StagingRoot ".cache"

function Get-DownloadPath([string]$Name) {
    if (-not (Test-Path $CacheDir)) {
        New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    }
    return Join-Path $CacheDir $Name
}

function Expand-ZipArchive([string]$ZipPath, [string]$Destination) {
    if (Test-Path $Destination) {
        Remove-Item -Recurse -Force $Destination
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $Destination)
}

Write-Step "Preparing staging directories..."
if (Test-Path $StagingRoot) {
    Remove-Item -Recurse -Force $StagingRoot
}
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $NssmDir -Force | Out-Null

Write-Step "Downloading Python $PythonVersion embeddable (amd64)..."
$EmbedZipName = "python-$PythonVersion-embed-amd64.zip"
$EmbedZipPath = Get-DownloadPath $EmbedZipName
if (-not (Test-Path $EmbedZipPath)) {
    $EmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/$EmbedZipName"
    Invoke-WebRequest -Uri $EmbedUrl -OutFile $EmbedZipPath -UseBasicParsing
}
Expand-ZipArchive -ZipPath $EmbedZipPath -Destination $RuntimeDir

$SitePackages = Join-Path $RuntimeDir "Lib\site-packages"
New-Item -ItemType Directory -Path $SitePackages -Force | Out-Null

$PthFile = Get-ChildItem -Path $RuntimeDir -Filter "python*._pth" | Select-Object -First 1
if ($null -eq $PthFile) {
    throw "Could not find python*._pth in embedded Python layout."
}
$StdlibZip = Get-ChildItem -Path $RuntimeDir -Filter "python*.zip" | Select-Object -First 1
if ($null -eq $StdlibZip) {
    throw "Could not find python*.zip stdlib archive in embedded Python layout."
}
# Keep python312.zip on the path — required for encodings and the rest of the stdlib.
$PthContent = @(
    $StdlibZip.Name
    "."
    "Lib\site-packages"
    "import site"
)
Set-Content -Path $PthFile.FullName -Value $PthContent -Encoding ASCII

$PythonExe = Join-Path $RuntimeDir "python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Embedded python.exe not found at $PythonExe"
}

Write-Step "Bootstrapping pip into embedded Python..."
$GetPipPath = Get-DownloadPath "get-pip.py"
if (-not (Test-Path $GetPipPath)) {
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPipPath -UseBasicParsing
}
& $PythonExe $GetPipPath --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "get-pip.py failed with exit code $LASTEXITCODE"
}

Write-Step "Installing backend package into bundled runtime..."
& $PythonExe -m pip install --upgrade pip --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE"
}
& $PythonExe -m pip install -e $BackendDir --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "pip install -e apps/backend failed with exit code $LASTEXITCODE"
}

Write-Step "Verifying bundled runtime imports..."
& $PythonExe -c "import webstudio_backend; print('webstudio_backend ok')"
if ($LASTEXITCODE -ne 0) {
    throw "Bundled runtime import check failed"
}

Write-Step "Downloading NSSM $NssmVersion..."
$NssmZipName = "nssm-$NssmVersion.zip"
$NssmZipPath = Get-DownloadPath $NssmZipName
if (-not (Test-Path $NssmZipPath)) {
    Invoke-WebRequest -Uri "https://nssm.cc/release/$NssmZipName" -OutFile $NssmZipPath -UseBasicParsing
}
$NssmExtract = Join-Path $CacheDir "nssm-$NssmVersion"
Expand-ZipArchive -ZipPath $NssmZipPath -Destination $NssmExtract
$NssmSource = Get-ChildItem -Path $NssmExtract -Recurse -Filter "nssm.exe" |
    Where-Object { $_.FullName -match "win64" } |
    Select-Object -First 1
if ($null -eq $NssmSource) {
    throw "nssm.exe (win64) not found in $NssmExtract"
}
Copy-Item $NssmSource.FullName (Join-Path $NssmDir "nssm.exe") -Force

Write-Step "Staging complete:"
Write-Step "  Runtime: $RuntimeDir"
Write-Step "  NSSM:    $(Join-Path $NssmDir 'nssm.exe')"
