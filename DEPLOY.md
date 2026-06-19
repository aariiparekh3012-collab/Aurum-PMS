# Aurum PMS — Deployment Guide

Two paths. Pick one.

| | **Path A — Free cloud** | **Path B — VPS / self-hosted** |
|---|---|---|
| Cost | $0 | ~$5–6/month (Hetzner CX22 or DigitalOcean Basic) |
| SSL | Automatic | One command (`setup-ssl.sh`) |
| Setup time | ~15 min | ~20 min |
| Best for | Demo, presenting to office | Permanent production |

---

## Prerequisites (both paths)

1. **Push code to GitHub**

```powershell
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management"
git init
git add .
git commit -m "Initial commit — Aurum PMS"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/aurum-pms.git
git push -u origin main
```

2. **Generate secrets** — run these on your local machine, save the output:

```bash
# JWT secret
python -c "import secrets; print(secrets.token_hex(32))"

# PII encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Path A — Free Cloud (Render)

Everything — backend API, frontend, database — runs on Render for free.
SSL is automatic. No server to manage.

### Step 1 — Database (Neon free tier)

1. Go to [neon.tech](https://neon.tech) → sign up with GitHub
2. **Create Project** → name `aurum-pms`, region closest to you, Postgres 16
3. Copy the **Connection string** (looks like `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`)
4. In the Neon dashboard → **SQL Editor** → run:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE SCHEMA IF NOT EXISTS client;
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS portfolio;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS performance;
CREATE SCHEMA IF NOT EXISTS notifications;
```

### Step 2 — Deploy on Render (one click)

1. Go to [render.com](https://render.com) → sign up with GitHub
2. Click **New** → **Blueprint** → connect your `aurum-pms` repo
3. Render reads `render.yaml` and creates **two services automatically**:
   - `aurum-pms-api` — FastAPI backend
   - `aurum-pms-app` — React frontend (static site)
4. Set environment variables for the **backend** service (`aurum-pms-api`):

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon connection string from Step 1 |
| `JWT_SECRET` | Your generated JWT secret |
| `PII_ENCRYPTION_KEY` | Your generated Fernet key |
| `CORS_ORIGINS` | *(leave blank for now — fill in after Step 3)* |
| `ENVIRONMENT` | `production` |

5. Set environment variables for the **frontend** service (`aurum-pms-app`):

| Variable | Value |
|---|---|
| `VITE_API_URL` | *(leave blank for now — fill in after backend deploys)* |

6. Click **Apply** → wait ~3 min for both services to build

### Step 3 — Connect frontend ↔ backend

After both services are up:

1. Copy the backend URL from Render dashboard (e.g. `https://aurum-pms-api.onrender.com`)
2. In the **frontend** service environment: set `VITE_API_URL` = `https://aurum-pms-api.onrender.com/api/v1`
3. In the **backend** service environment: set `CORS_ORIGINS` = `https://aurum-pms-app.onrender.com`
4. Save changes (Render auto-redeploys both)

### Step 4 — Seed demo data

```bash
# From your local machine, with the backend URL:
BASE_URL=https://aurum-pms-api.onrender.com/api/v1 python backend/scripts/seed_demo.py
```

### Step 5 — Done

Visit your frontend URL (e.g. `https://aurum-pms-app.onrender.com`).
Use the **Quick Demo Access** buttons on the login page.

> **Note:** Render free tier spins down after 15 min of inactivity.
> First request after sleep takes ~30 sec. Upgrade to Starter ($7/mo) to avoid this.

---

## Path B — VPS / Self-hosted

Run everything on a single Linux server with Docker. Full control, HTTPS included.

### Recommended servers (all have free credit offers)

| Provider | Size | Cost | Notes |
|---|---|---|---|
| [Hetzner](https://hetzner.com) | CX22 (2 vCPU, 4 GB) | ~€4/mo | Best value |
| [DigitalOcean](https://digitalocean.com) | Basic 2 GB | $12/mo | $200 free credit |
| [Vultr](https://vultr.com) | Cloud Compute 2 GB | $10/mo | Easy setup |

### Step 1 — Server setup

SSH into your server, then:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 2 — Clone your repo

```bash
git clone https://github.com/YOUR_USERNAME/aurum-pms.git
cd aurum-pms
```

### Step 3 — Configure environment

```bash
cp .env.example .env
nano .env   # fill in: DB_PASSWORD, JWT_SECRET, PII_ENCRYPTION_KEY
            # set ENVIRONMENT=production
            # set CORS_ORIGINS=https://yourdomain.com
```

### Step 4 — Point your domain DNS

In your domain registrar, add an **A record**:
- Host: `@` (or `aurum`)
- Value: your server's IP address
- TTL: 300

Wait 5–10 min for DNS to propagate.

### Step 5 — Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This starts: PostgreSQL → backend (gunicorn) → frontend (nginx) → nginx proxy → certbot.

Wait ~2 min for all services to be healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

All should show `Up` or `healthy`.

### Step 6 — SSL (one command)

```bash
bash scripts/setup-ssl.sh yourdomain.com you@email.com
```

This: gets a Let's Encrypt cert → swaps nginx to HTTPS config → reloads nginx → sets up auto-renewal.

Visit `https://yourdomain.com` — you should see the app with a valid SSL certificate.

### Step 7 — Seed demo data

```bash
BASE_URL=https://yourdomain.com/api/v1 python backend/scripts/seed_demo.py
```

### Step 8 — Done

| URL | What |
|---|---|
| `https://yourdomain.com` | React app |
| `https://yourdomain.com/docs` | FastAPI Swagger UI |
| `https://yourdomain.com/api/v1/healthz` | Health check (liveness) |

---

## Demo logins (after seeding)

| Role | How to log in |
|---|---|
| Compliance officer | Click "Compliance" on login page Quick Demo Access |
| Relationship Manager | Click "RM" on login page Quick Demo Access |
| Investor | Click "Investor" on login page, or: `asha@example.com` / `investor123` |

> Quick Demo Access uses `/auth/dev-token` — this endpoint is **disabled** when `ENVIRONMENT=production`.
> On a live server, create real users via the onboarding flow or the `/auth/register` endpoint.

---

## Updating the app

### Render (Path A)
Push to `main` → Render auto-redeploys both services.

### VPS (Path B)
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Troubleshooting

**Backend won't start?**
```bash
docker compose -f docker-compose.prod.yml logs backend
```
Most common cause: `DATABASE_URL` wrong format. Must start with `postgresql://` (not `postgres://`).

**Frontend shows network errors / CORS?**
- Check `CORS_ORIGINS` in backend env matches the frontend URL exactly (no trailing slash)
- Check `VITE_API_URL` in frontend env ends with `/api/v1`

**SSL cert fails?**
- DNS must point to your server before running `setup-ssl.sh`
- Port 80 must be open in your server's firewall: `ufw allow 80 && ufw allow 443`

**Render cold start is slow?**
- Normal on free tier. Upgrade to Render Starter ($7/mo) for always-on.

**Want to wipe and re-seed?**
```bash
# VPS:
docker compose -f docker-compose.prod.yml down -v   # -v removes the DB volume
docker compose -f docker-compose.prod.yml up -d --build
BASE_URL=https://yourdomain.com/api/v1 python backend/scripts/seed_demo.py
```
