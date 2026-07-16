# StudWorks build-artifact cleanup.
#
# Removes PyInstaller's build/ and dist/ output directories so the next
# build.ps1 run starts from a known-clean state. Safe to run any time --
# both directories are already gitignored, disposable build output.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

foreach ($dir in @("build", "dist")) {

    $path = Join-Path $repoRoot $dir

    if (Test-Path $path) {
        Write-Host "Removing $path"
        Remove-Item -Recurse -Force $path
    }
}

Write-Host "Clean complete."
