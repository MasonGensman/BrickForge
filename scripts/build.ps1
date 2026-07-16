# Builds dist/StudWorks.exe from StudWorks.spec.
#
# Usage:
#   scripts/build.ps1            Preview build (no console window)
#   scripts/build.ps1 -Debug     Debug build (keeps the console window,
#                                 showing the startup GPU/vendor banner
#                                 and any tracebacks)
#
# Requires PyInstaller in the active Python environment
# (pip install pyinstaller) in addition to requirements.txt.

param(
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& (Join-Path $PSScriptRoot "clean.ps1")

if ($Debug) {
    $env:STUDWORKS_DEBUG_CONSOLE = "1"
    Write-Host "Building StudWorks (debug console build)..."
} else {
    $env:STUDWORKS_DEBUG_CONSOLE = "0"
    Write-Host "Building StudWorks (Preview build)..."
}

pyinstaller StudWorks.spec

Remove-Item Env:\STUDWORKS_DEBUG_CONSOLE -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit $LASTEXITCODE
}

$exePath = Join-Path $repoRoot "dist\StudWorks.exe"

if (Test-Path $exePath) {
    Write-Host "Build succeeded: $exePath"
} else {
    Write-Error "Build reported success but $exePath was not found."
    exit 1
}
