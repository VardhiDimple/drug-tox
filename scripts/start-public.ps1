# DRUG TOX PRO — Public internet access (different networks)
# Requires: Node.js, app running on port 8000
#
# Step 1 (terminal 1): start the app
#   .\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# Step 2 (terminal 2): run this script
#   .\scripts\start-public.ps1
#
# Share the https://....loca.lt URL with anyone worldwide.
# First visit may ask for your public IP — open https://loca.lt/mytunnelpassword

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Starting public tunnel to http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Write-Host "Keep this window open. Share the URL shown below." -ForegroundColor Yellow
Write-Host ""

# Health check
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
    Write-Host "ERROR: App is not running on port 8000." -ForegroundColor Red
    Write-Host "Start it first in another terminal:"
    Write-Host "  .\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    exit 1
}

npx --yes localtunnel --port 8000
