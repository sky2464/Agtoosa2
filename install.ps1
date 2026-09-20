# ==============================================================================
# Agtoosa2 Universal Installer for Windows (PowerShell)
# Installs Agtoosa2 cleanly on Windows with zero dependency conflicts.
# Usage:
#   irm https://raw.githubusercontent.com/sky2464/Agtoosa2/main/install.ps1 | iex
#   OR inside repo: .\install.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

$RepoUrl = "git+https://github.com/sky2464/Agtoosa2.git"
$InstallDir = Join-Path $HOME ".local\bin"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Write-Host ""
Write-Host "🚀 Agtoosa2 Universal Installer (Windows)" -ForegroundColor Cyan
Write-Host "   Checking environment..."
Write-Host ""

# 1. Locate compatible Python runtime (>= 3.11 required)
$PythonCmd = $null
$CandidateCmds = @("py", "python", "python3")

foreach ($cmd in $CandidateCmds) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        try {
            $verOutput = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($verOutput) {
                $parts = $verOutput.Trim().Split(".")
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -ge 3 -and $minor -ge 11) {
                    $PythonCmd = $cmd
                    $PythonVer = "$major.$minor"
                    break
                }
            }
        } catch {}
    }
}

if (-not $PythonCmd) {
    Write-Host "❌ Python 3.11 or higher is required." -ForegroundColor Red
    Write-Host "   Please install Python 3.11+ from https://www.python.org/downloads/windows/"
    Write-Host "   or via winget: winget install Python.Python.3.12"
    exit 1
}

Write-Host "   • Found Python: $PythonCmd ($PythonVer)" -ForegroundColor Green

# Determine package target (local repo or GitHub)
$PkgSpec = $RepoUrl
if (Test-Path "pyproject.toml") {
    $tomlContent = Get-Content "pyproject.toml" -Raw
    if ($tomlContent -match 'name\s*=\s*"agtoosa"') {
        $PkgSpec = (Get-Location).Path
        Write-Host "   • Detected local repository: $PkgSpec" -ForegroundColor Green
    }
} else {
    Write-Host "   • Package source: $PkgSpec" -ForegroundColor Green
}

# 2. Installation order: uv -> pipx -> isolated venv
$InstalledVia = ""

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    Write-Host "   • Installing via uv tool (fastest)..." -ForegroundColor Cyan
    & uv tool install --force "$PkgSpec"
    $InstalledVia = "uv"
} elseif (Get-Command "pipx" -ErrorAction SilentlyContinue) {
    Write-Host "   • Installing via pipx..." -ForegroundColor Cyan
    & pipx install --force "$PkgSpec"
    $InstalledVia = "pipx"
} else {
    Write-Host "   • Installing into isolated user environment ($HOME\.agtoosa\venv)..." -ForegroundColor Cyan
    $VenvDir = Join-Path $HOME ".agtoosa\venv"
    if (-not (Test-Path (Join-Path $HOME ".agtoosa"))) {
        New-Item -ItemType Directory -Path (Join-Path $HOME ".agtoosa") -Force | Out-Null
    }
    & $PythonCmd -m venv "$VenvDir"
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    $VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
    & $VenvPython -m pip install --quiet --upgrade pip
    & $VenvPip install --quiet --upgrade "$PkgSpec"

    # Create agtoosa.cmd in ~/.local/bin
    $BatchWrapper = Join-Path $InstallDir "agtoosa.cmd"
    $VenvAgtoosa = Join-Path $VenvDir "Scripts\agtoosa.exe"
    Set-Content -Path $BatchWrapper -Value "@echo off`r`n`"$VenvAgtoosa`" %*"
    $InstalledVia = "venv"
}

# 3. Verify PATH availability
Write-Host ""
$InPath = $false
if (Get-Command "agtoosa" -ErrorAction SilentlyContinue) {
    $InPath = $true
} else {
    $EnvPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($EnvPath -like "*$InstallDir*") {
        $InPath = $true
    }
}

if (-not $InPath) {
    Write-Host "⚠️  Note: $InstallDir is not yet in your PATH." -ForegroundColor Yellow
    Write-Host "   To add it permanently for your user, run:"
    Write-Host "     [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$InstallDir', 'User')" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "✅ Agtoosa2 installed successfully via $InstalledVia!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Get Started on Autopilot:"
Write-Host "   1. cd C:\path\to\your\project"
Write-Host "   2. agtoosa autopilot             # Turns on AI agent guardrails & git hooks"
Write-Host "   3. agtoosa graph build           # Index symbols into .agtoosa\graph.db"
Write-Host "   4. agtoosa graph view --serve    # Launch Studio in default browser"
Write-Host ""
