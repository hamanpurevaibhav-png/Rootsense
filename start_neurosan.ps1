# ============================================================================
# RootSense for SAC — Neuro-SAN Studio & NSFlow Visual UI Launcher
# ============================================================================
# Launches the official Neuro-SAN Server (port 8080) and NSFlow React UI
# (http://localhost:4173) for inspecting the `rootsense_sac.hocon` multi-agent
# topology, AAOSA Determine/Fulfill calls, CodedTools, and `sly_data`.
#
# Usage:
#   .\start_neurosan.ps1
# ============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# 1. Load environment variables from .env
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $key = $parts[0].Trim()
            $val = $parts[1].Trim().Trim('"').Trim("'")
            [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

# 2. Corporate SSL / TLS trust bundle
$CaBundle = Join-Path $ProjectRoot ".certs\ca_bundle.pem"
if (Test-Path $CaBundle) {
    $env:SSL_CERT_FILE = $CaBundle
    $env:REQUESTS_CA_BUNDLE = $CaBundle
    $env:CURL_CA_BUNDLE = $CaBundle
    $env:GRPC_DEFAULT_SSL_ROOTS_FILE_PATH = $CaBundle
}

# 3. Configure Neuro-SAN manifest and CodedTool paths for RootSense
$env:AGENT_MANIFEST_FILE = Join-Path $ProjectRoot "registries\manifest.hocon"
$env:AGENT_TOOL_PATH = Join-Path $ProjectRoot "coded_tools"
$env:AGENT_LLM_CONFIG = Join-Path $ProjectRoot "config\llm_config.hocon"
$env:PYTHONUTF8 = "1"

# 4. Locate `ns.exe` (in local .venv or sibling test_neurosan .venv)
$LocalNs = Join-Path $ProjectRoot ".venv\Scripts\ns.exe"
$SiblingNs = Join-Path (Split-Path -Parent $ProjectRoot) "test_neurosan\.venv\Scripts\ns.exe"

if (Test-Path $LocalNs) {
    $NsExe = $LocalNs
    $VenvScripts = Join-Path $ProjectRoot ".venv\Scripts"
} elseif (Test-Path $SiblingNs) {
    $NsExe = $SiblingNs
    $VenvScripts = Join-Path (Split-Path -Parent $ProjectRoot) "test_neurosan\.venv\Scripts"
} else {
    Write-Error "Could not find 'ns.exe'. Install neuro-san-studio or ensure test_neurosan\.venv exists."
    exit 1
}

$env:PATH = "$VenvScripts;$env:PATH"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Starting RootSense Neuro-SAN Studio + NSFlow Visual Graph UI" -ForegroundColor Cyan
Write-Host " -> Manifest  : $env:AGENT_MANIFEST_FILE" -ForegroundColor Green
Write-Host " -> Tools     : $env:AGENT_TOOL_PATH" -ForegroundColor Green
Write-Host " -> NSFlow UI : http://localhost:4173" -ForegroundColor Yellow
Write-Host " -> Server    : http://localhost:8080" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Cyan

& $NsExe run
