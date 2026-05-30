# DRUG TOX PRO — Start for sharing on your local network
# Run in PowerShell: .\scripts\start-share.ps1
# Others on the same Wi‑Fi can open the URL shown below.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$Port = 8000
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Virtual environment not found. Run: python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Windows Firewall — allow inbound (may prompt for Administrator)
$ruleName = "DRUG TOX PRO Port $Port"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -ErrorAction Stop | Out-Null
        Write-Host "Firewall rule added for port $Port"
    } catch {
        Write-Host "Could not add firewall rule (run PowerShell as Administrator if others cannot connect):"
        Write-Host "  New-NetFirewallRule -DisplayName '$ruleName' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port"
    }
}

# Local IP addresses
$ips = @(Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -ExpandProperty IPAddress -Unique)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DRUG TOX PRO — Network sharing" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  On this PC:     http://localhost:$Port"
foreach ($ip in $ips) {
    Write-Host "  Share this URL: http://${ip}:$Port" -ForegroundColor Green
}
Write-Host ""
Write-Host "  Frontend + API run together on port $Port."
Write-Host "  Keep this window open while others use the app."
Write-Host "  Same Wi‑Fi / LAN required (not the public internet)."
Write-Host ""

& $Python -m uvicorn app.main:app --host 0.0.0.0 --port $Port
