# Share DRUG TOX PRO with others

## Quick start (same Wi‑Fi / office network)

1. Open **PowerShell** in the project folder.
2. Run:

```powershell
.\scripts\start-share.ps1
```

3. Share the green URL with others, for example:

```
http://192.168.1.103:8000
```

They open it in Chrome, Edge, or Firefox. **Frontend and backend** are both served on that single URL.

4. Keep your PC **on** and the PowerShell window **open** while they use the app.

---

## Requirements for other people

| Requirement | Details |
|-------------|---------|
| Same network | Same Wi‑Fi or LAN as your PC |
| Your PC running | Server must stay up |
| Firewall | Script tries to open port 8000; if blocked, run PowerShell **as Administrator** and run the firewall command shown by the script |

---

## Docker (frontend + backend containers)

If you use Docker Desktop:

```powershell
docker compose up --build
```

Share this URL (replace with your PC’s IP):

```
http://192.168.1.103:8080
```

- **Frontend:** port `8080` (nginx)
- **Backend:** internal; API is proxied at `/api/...`

---

## If others cannot connect

1. Confirm they are on the **same Wi‑Fi** (not mobile data only).
2. Run PowerShell **as Administrator**:

```powershell
New-NetFirewallRule -DisplayName "DRUG TOX PRO Port 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

3. Find your IP: `ipconfig` → look for **IPv4 Address** under Wi‑Fi.

---

## Access from the internet (different cities)

Local URLs (`192.168.x.x`) only work on your LAN. For access over the internet use one of:

- **[ngrok](https://ngrok.com/)** — `ngrok http 8000` → share the `https://....ngrok.io` link
- **[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)**
- Deploy to **Render**, **Railway**, or **Azure** (production)

---

## Your shareable link (example)

Replace `192.168.1.103` with the IP shown when you run `start-share.ps1`:

**http://192.168.1.103:8000**
