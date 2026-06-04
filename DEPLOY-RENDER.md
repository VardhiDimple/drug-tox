# Deploy DRUG TOX PRO to Render (permanent URL)

Your live URL will look like: **`https://drug-tox.onrender.com`** (name you choose).

No laptop required after deploy. Team opens that link from any network.

---

## Before you start

1. Code is on GitHub: **https://github.com/VardhiDimple/drug-tox**
2. Free [Render](https://render.com) account (sign up with GitHub).
3. This app uses **RDKit + ML** — use at least the **Starter** plan (~$7/month) or builds may run out of memory on Free.

---

## Step 1 — Push latest code to GitHub

In PowerShell (project folder):

```powershell
cd "c:\Users\Dharani\Downloads\drug-tox-pro\drug-tox-pro"
git add Dockerfile render.yaml docker/start.sh DEPLOY-RENDER.md
git commit -m "Add Render deployment configuration"
git push origin main
```

Skip if everything is already pushed.

---

## Step 2 — Create a Render account

1. Open **https://render.com**
2. Click **Get Started** → sign in with **GitHub**
3. Authorize Render to access your repositories

---

## Step 3 — Create the web service (Blueprint — easiest)

1. In Render Dashboard, click **New +** → **Blueprint**
2. Connect repository **`VardhiDimple/drug-tox`**
3. Render detects **`render.yaml`** in the repo
4. Review the service name **`drug-tox`**
5. Choose **Starter** plan if prompted (recommended)
6. Click **Apply**

Render will build the Docker image and deploy (first build often **10–20 minutes**).

---

## Step 3 (alternative) — Manual web service

If Blueprint is not available:

1. **New +** → **Web Service**
2. Connect **`VardhiDimple/drug-tox`**
3. Settings:

| Setting | Value |
|---------|--------|
| **Name** | `drug-tox` |
| **Region** | Oregon (or nearest) |
| **Branch** | `main` |
| **Runtime** | **Docker** |
| **Dockerfile Path** | `./Dockerfile` |
| **Instance type** | **Starter** (recommended) |
| **Health Check Path** | `/api/health` |

4. Click **Create Web Service**

---

## Step 4 — Wait for deploy

1. Open the service → **Logs**
2. Wait until you see **Deploy live**
3. Open the URL at the top, e.g. `https://drug-tox-xxxx.onrender.com`

Test:

- Home page loads
- `https://YOUR-URL.onrender.com/api/health` returns `{"status":"ok",...}`

---

## Step 5 — Share with your team

Send the Render URL to friends/colleagues, for example:

```
https://drug-tox.onrender.com
```

They can use it from any network. Your PC can be off.

---

## Free tier notes

- **Free** services **spin down after ~15 min idle**; first visit may take 30–60 seconds to wake.
- **ML training** may fail on Free (512 MB RAM). Use **Starter** for reliable ML uploads.
- Custom domain: Render Dashboard → your service → **Settings** → **Custom Domains**

---

## Auto-deploy on every push

Enabled by default when connected to GitHub:

```powershell
git push origin main
```

Render rebuilds automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails / out of memory | Upgrade to **Starter** or higher |
| 502 on first visit (Free) | Wait 1 minute; service is waking |
| Frontend blank | Check logs; ensure `static/` and `templates/` are in the repo |
| Health check fails | Confirm path `/api/health` in service settings |

---

## Stop using local tunnel

After Render works, you no longer need:

- `docker compose` on your laptop for sharing
- `start-share-public.ps1` / Cloudflare tunnel

Keep Docker only for local development if you want.
