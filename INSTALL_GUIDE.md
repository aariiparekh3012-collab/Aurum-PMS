# Aurum PMS — Installation & Run Guide

**Stack:** FastAPI · PostgreSQL · React · React Native (Expo)

---

## Prerequisites

Install these before anything else:

| Tool | Version | Download |
|---|---|---|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |
| Node.js | 20+ | https://nodejs.org |
| Git | Any | https://git-scm.com |
| Expo Go (phone) | Latest | App Store / Play Store |

> **Windows users:** Make sure Docker Desktop is running before any `docker` commands.

---

## 1. Clone the repo

```bash
git clone https://github.com/aariiparekh3012-collab/intern1.git
cd intern1
```

---

## 2. Configure environment

Copy the example env file and fill in secrets:

```bash
cp .env.example .env
```

Open the `.env` file in any text editor (Notepad, VS Code, etc.) and update these values:

> **Windows:** right-click `.env` → Open with → Notepad
> **VS Code:** `code .env`

```env
DATABASE_URL=postgresql://pms_admin:changeme@db:5432/pms_db
JWT_SECRET=<generate and paste here — see below>
PII_ENCRYPTION_KEY=<generate and paste here — see below>
CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=local
```

**Generate JWT_SECRET** — run this in PowerShell, copy the output, paste it into `.env`:
```powershell
[System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

**Generate PII_ENCRYPTION_KEY** — run this in any terminal, copy the output, paste it into `.env`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 3. Start the full stack (backend + database)

From the project root:

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** on port `5432`
- **FastAPI backend** on port `8000`

Wait ~20 seconds for the database to initialize, then verify:

```bash
docker compose ps
```

All services should show `healthy` or `running`.

**Check backend is alive:**
```
http://localhost:8000/health
```
Should return `{"status": "ok"}`.

**API docs (Swagger UI):**
```
http://localhost:8000/docs
```

---

## 4. Seed demo data

Run once to populate the database with demo users, clients, portfolios, and trades:

```bash
docker compose exec backend python scripts/seed.py
```

### Demo login credentials

| Role | Email | Password |
|---|---|---|
| Investor | `asha@example.com` | `investor123` |
| Relationship Manager | `raj@example.com` | `rm123` |
| Compliance Officer | `priya@example.com` | `compliance123` |

---

## 5. Run the web frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Web app opens at: **http://localhost:5173**

---

## 6. Run the mobile app

### Step 1 — Find your computer's local IP

**Windows (PowerShell or CMD):**
```bash
ipconfig
```
Look for **IPv4 Address** under your active WiFi adapter.
Example: `192.168.1.45`

### Step 2 — Update API URL in `mobile/app.json`

Open `mobile/app.json` and change:
```json
"extra": {
  "apiBaseUrl": "http://192.168.1.45:8000/api/v1"
}
```
Replace `192.168.1.45` with your actual IP address.

> ⚠️ Using `localhost` here will NOT work on a physical phone.

### Step 3 — Install dependencies and start

```bash
cd mobile
npm install
npm start
```

Expo will display a **QR code** in the terminal.

### Step 4 — Open on your phone

1. Install **Expo Go** from the App Store (iOS) or Play Store (Android)
2. Open Expo Go
3. Scan the QR code from your terminal

> Your phone and computer must be on the **same WiFi network**.

---

## Verify everything is working

| Check | URL / Action |
|---|---|
| Backend health | http://localhost:8000/health |
| API docs | http://localhost:8000/docs |
| Web app | http://localhost:5173 |
| Mobile app | Scan QR in Expo terminal |
| Login (any role) | Use demo credentials from Step 4 |

---

## Stopping the stack

```bash
docker compose down
```

To also delete all database data:
```bash
docker compose down -v
```

---

## Troubleshooting

### "Port 8000 already in use"
Another process is using the port. Either kill it or change the port in `docker-compose.yml`:
```bash
# Find what's using port 8000 (Windows)
netstat -ano | findstr :8000
```

### "Network request failed" on mobile
Your phone can't reach the backend. Fix:
1. Run `ipconfig` and copy your IPv4 address
2. Update `mobile/app.json` → `extra.apiBaseUrl` with that IP
3. Make sure both devices are on the same WiFi
4. Confirm backend is running: `docker compose ps`

### "relation does not exist" error
Migrations haven't run. The backend Dockerfile runs them on startup, but if something went wrong:
```bash
docker compose exec backend alembic upgrade head
```

### Docker containers keep restarting
Check logs:
```bash
docker compose logs backend
docker compose logs db
```

### "Module not found" on mobile
```bash
cd mobile
npm install
```
Then restart Expo with `npm start`.

### Frontend won't build
```bash
cd frontend
npm install
npm run build
```
If TypeScript errors appear, they are pre-existing test file conflicts — they do not affect the running app.

---

## Folder structure (quick reference)

```
discretionary portfolio management/
├── backend/          # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── domain/   # Business logic
│   │   └── infra/    # DB models, repositories
│   └── alembic/      # Migrations
├── frontend/         # React 18 + TypeScript + Vite
│   └── src/
│       ├── pages/    # Route pages
│       └── components/
├── mobile/           # React Native + Expo 51
│   └── src/
│       ├── screens/  # All app screens
│       ├── navigation/
│       └── lib/      # API client, auth, types
├── nginx/            # Production nginx configs
├── scripts/          # Seed, backup, SSL setup
├── docker-compose.yml         # Local dev stack
├── docker-compose.prod.yml    # Production stack
├── landing.html               # Public marketing page
└── DEPLOY.md                  # Production deployment guide
```

---

## Quick start (TL;DR)

```bash
# 1. Set up env
cp .env.example .env
# (edit .env with your secrets)

# 2. Start backend + DB
docker compose up -d

# 3. Seed data
docker compose exec backend python scripts/seed.py

# 4. Start web
cd frontend && npm install && npm run dev

# 5. Start mobile (new terminal)
cd mobile && npm install && npm start
# → scan QR with Expo Go
```
