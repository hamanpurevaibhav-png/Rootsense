<#
.SYNOPSIS
    Automated uv Virtual Environment & Dependency Bootstrapper for RootSense SAC.
.DESCRIPTION
    1. Configures Corporate SSL Certificate Bundle (.certs/ca_bundle.pem) & UTF-8 encoding.
    2. Creates an isolated .venv virtual environment using uv.
    3. Installs all dependencies from requirements.txt via uv pip.
    4. Loads .env (GEMINI_API_KEY / GOOGLE_API_KEY) and executes tests/test_health.py.
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " RootSense for SAC - AI Platform Environment Bootstrapper (uv)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Step 0: Configure Corporate SSL Certificate Bundle & UTF-8 logging (from test_neurosan)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$caBundle = Join-Path $PSScriptRoot ".certs\ca_bundle.pem"
if (Test-Path $caBundle) {
    $env:SSL_CERT_FILE = $caBundle
    $env:REQUESTS_CA_BUNDLE = $caBundle
    $env:CURL_CA_BUNDLE = $caBundle
    $env:GRPC_DEFAULT_SSL_ROOTS_FILE_PATH = $caBundle
    Write-Host "[SSL] Loaded corporate CA bundle: $caBundle" -ForegroundColor Green
}

# Step 1: Virtual Environment Inception
Write-Host "`n[1/4] Creating isolated virtual environment (.venv) via uv..." -ForegroundColor Yellow
uv venv .venv

# Step 2: Activate Virtual Environment in current PowerShell session
Write-Host "`n[2/4] Activating .venv virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

# Step 3: High-Speed Dependency Installation
Write-Host "`n[3/4] Installing dependencies from requirements.txt via uv pip..." -ForegroundColor Yellow
uv pip install -r requirements.txt

# Step 4: Verify .env configuration and execute Health Ping
Write-Host "`n[4/4] Verifying .env configuration and executing Health Check..." -ForegroundColor Yellow
if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
}

python tests/test_health.py
