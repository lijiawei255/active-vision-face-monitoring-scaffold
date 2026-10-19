param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "== ruff check =="
conda run -n avfm ruff check src tests

Write-Host "== ruff format check =="
conda run -n avfm ruff format --check src tests

Write-Host "== docs parity =="
conda run -n avfm python scripts/check_docs_parity.py
Write-Host "== docs links =="
conda run -n avfm python scripts/check_docs_links.py

Write-Host "== core tests =="
conda run -n avfm python -m pytest -m "not webcam and not hardware and not mediapipe" --cov=avfm --cov-fail-under=80

Write-Host "== selftest =="
conda run -n avfm avfm selftest

Write-Host "All checks passed."
