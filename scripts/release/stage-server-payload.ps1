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

function Test-ZipFile([string]$Path) {
    if (-not (Test-Path $Path)) {
        return $false
    }
    $info = Get-Item $Path
    if ($info.Length -lt 4096) {
        return $false
    }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 4) {
        return $false
    }
    # PK\x03\x04 local file header
    return ($bytes[0] -eq 0x50 -and $bytes[1] -eq 0x4B -and $bytes[2] -eq 0x03 -and $bytes[3] -eq 0x04)
}

function Invoke-DownloadWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination,
        [int]$MaxAttempts = 3
    )
    $attempt = 0
    while ($attempt -lt $MaxAttempts) {
        $attempt++
        try {
            Write-Step "  GET $Uri (attempt $attempt/$MaxAttempts)"
            Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing
            if (Test-Path $Destination) {
                return
            }
        } catch {
            if ($attempt -ge $MaxAttempts) {
                throw
            }
            Start-Sleep -Seconds ([Math]::Min(5 * $attempt, 15))
        }
    }
}

function Copy-NssmFromZipLayout {
    param(
        [Parameter(Mandatory = $true)][string]$ExtractRoot,
        [Parameter(Mandatory = $true)][string]$DestinationExe
    )
    $flat = Get-ChildItem -Path $ExtractRoot -Recurse -Filter "nssm.exe" |
        Where-Object { $_.FullName -match "win64" -or $_.DirectoryName -eq $ExtractRoot } |
        Sort-Object { if ($_.FullName -match "win64") { 0 } else { 1 } } |
        Select-Object -First 1
    if ($null -eq $flat) {
        $flat = Get-ChildItem -Path $ExtractRoot -Recurse -Filter "nssm.exe" | Select-Object -First 1
    }
    if ($null -eq $flat) {
        throw "nssm.exe not found under $ExtractRoot"
    }
    Copy-Item $flat.FullName $DestinationExe -Force
}

function Install-NssmBinary {
    param(
        [Parameter(Mandatory = $true)][string]$DestinationDir,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string]$NssmVersion = "2.24"
    )
    $DestinationExe = Join-Path $DestinationDir "nssm.exe"
    $VendorExe = Join-Path $RepoRoot "infra\windows\vendor\nssm\win64\nssm.exe"

    $sources = @(
        @{
            Name = "GitHub fawno/nssm.cc Win64"
            Url  = "https://github.com/fawno/nssm.cc/releases/download/v2.24.1/nssm-v2.24.1-Win64.zip"
            Zip  = "nssm-v2.24.1-Win64.zip"
        },
        @{
            Name = "nssm.cc official archive"
            Url  = "https://nssm.cc/release/nssm-$NssmVersion.zip"
            Zip  = "nssm-$NssmVersion.zip"
        }
    )

    foreach ($source in $sources) {
        $zipPath = Get-DownloadPath $source.Zip
        if (-not (Test-Path $zipPath) -or -not (Test-ZipFile $zipPath)) {
            if (Test-Path $zipPath) {
                Remove-Item $zipPath -Force
            }
            Write-Step "Downloading NSSM from $($source.Name)..."
            try {
                Invoke-DownloadWithRetry -Uri $source.Url -Destination $zipPath
            } catch {
                Write-Step "  Download failed: $($_.Exception.Message)"
                continue
            }
        }
        if (-not (Test-ZipFile $zipPath)) {
            Write-Step "  Invalid zip from $($source.Name); trying next source..."
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
            continue
        }

        $extractRoot = Join-Path $CacheDir ("extract-" + ($source.Zip -replace '\.zip$', ''))
        try {
            Expand-ZipArchive -ZipPath $zipPath -Destination $extractRoot
            Copy-NssmFromZipLayout -ExtractRoot $extractRoot -DestinationExe $DestinationExe
            Write-Step "NSSM staged from $($source.Name)"
            return
        } catch {
            Write-Step "  Extract failed: $($_.Exception.Message)"
        }
    }

    if (Test-Path $VendorExe) {
        Write-Step "Using vendored NSSM fallback from $VendorExe"
        Copy-Item $VendorExe $DestinationExe -Force
        return
    }

    throw @"
Could not download or extract NSSM. Tried GitHub and nssm.cc mirrors.
Add infra\windows\vendor\nssm\win64\nssm.exe or retry when nssm.cc is reachable.
"@
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
# Embeddable Python cannot create PEP 517 isolated build envs (no venv).
# Install hatchling into the runtime, then build without isolation.
& $PythonExe -m pip install hatchling wheel --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "pip install hatchling/wheel failed with exit code $LASTEXITCODE"
}
& $PythonExe -m pip install --no-build-isolation $BackendDir --no-warn-script-location
if ($LASTEXITCODE -ne 0) {
    throw "pip install apps/backend failed with exit code $LASTEXITCODE"
}

Write-Step "Verifying bundled runtime imports..."
& $PythonExe -c "import webstudio_backend; print('webstudio_backend ok')"
if ($LASTEXITCODE -ne 0) {
    throw "Bundled runtime import check failed"
}

Write-Step "Staging NSSM..."
Install-NssmBinary -DestinationDir $NssmDir -RepoRoot $RepoRoot -NssmVersion $NssmVersion

Write-Step "Staging complete:"
Write-Step "  Runtime: $RuntimeDir"
Write-Step "  NSSM:    $(Join-Path $NssmDir 'nssm.exe')"
