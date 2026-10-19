param(
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"
$envName = "avfm"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "== avfm bootstrap =="
conda --version
$envExists = conda env list | Select-String -Pattern "^$envName\s"
if (-not $envExists) {
    Write-Host "Creating conda env '$envName' (conda-forge, Python 3.11)..."
    conda create -n $envName python=3.11 -c conda-forge -y
} else {
    Write-Host "Conda env '$envName' already exists."
}

Write-Host "Installing project + dev + MediaPipe extras..."
conda run -n $envName python -m pip install -U pip
conda run -n $envName python -m pip install -e ".[dev,mediapipe]"

if (-not $SkipModels) {
    Write-Host "Downloading/verifying models..."
    conda run -n $envName avfm models download --all
}

Write-Host "Running selftest..."
conda run -n $envName avfm selftest

Write-Host "Done. Activate with: conda activate $envName"
