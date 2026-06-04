# DRUG TOX PRO — Public URL for Docker (any network / internet)
# Requires: Node.js, Docker app running on port 8080
#
# Terminal 1:
#   docker compose up --build
#
# Terminal 2:
#   .\scripts\start-public-docker.ps1
#
# Share the https://....loca.lt URL with anyone (different Wi‑Fi, cities, etc.).
# First visit may ask for a tunnel password — open https://loca.lt/mytunnelpassword
# (uses your public IP; share that password only with your team if prompted).

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Starting public tunnel to http://127.0.0.1:8080 (Docker frontend) ..." -ForegroundColor Cyan
Write-Host "Keep this window open. Share the https URL shown below." -ForegroundColor Yellow
Write-Host ""

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8080/api/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "ERROR: App is not running on port 8080." -ForegroundColor Red
    Write-Host "Start Docker first:"
    Write-Host "  docker compose up --build"
    exit 1
}

npx --yes localtunnel --port 8080
