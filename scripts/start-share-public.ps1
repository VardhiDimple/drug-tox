# DRUG TOX PRO — Share with friends on any network (public HTTPS URL)
#
# Prerequisites:
#   1. Docker Desktop running
#   2. App up: docker compose up --build  (terminal 1)
#   3. Run this script (terminal 2)
#
# Share the https://....trycloudflare.com URL printed below.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Cloudflared = Join-Path $ProjectRoot "scripts\cloudflared.exe"
$Port = 8080

Set-Location $ProjectRoot

Write-Host ""
Write-Host "Checking app on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "ERROR: Start Docker first:" -ForegroundColor Red
    Write-Host "  docker compose up --build"
    exit 1
}

if (-not (Test-Path $Cloudflared)) {
    Write-Host "Downloading cloudflared..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/download/2025.4.0/cloudflared-windows-amd64.exe" -OutFile $Cloudflared -UseBasicParsing
}

Write-Host ""
Write-Host "Starting public tunnel (keep this window open)..." -ForegroundColor Green
Write-Host "Copy the https://....trycloudflare.com URL and send it to your friends." -ForegroundColor Yellow
Write-Host ""

& $Cloudflared tunnel --url "http://127.0.0.1:$Port"
