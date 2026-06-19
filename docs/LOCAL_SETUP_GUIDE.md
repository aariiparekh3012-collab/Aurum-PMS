# Local Setup Guide (Beginner-Friendly)

This guide gets the PMS Onboarding project running on your **Windows** computer for the
first time. Follow it top to bottom. Commands are shown for **Command Prompt (cmd)**; notes
for PowerShell and macOS/Linux are included where they differ.

> Recommended approach: run **PostgreSQL inside Docker** (no painful database install) and
> run the **backend and frontend directly** on your machine. This is the most reliable path
> for a first run.

The project folder (your "project root") is:

```
C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management
```

---

## 1. Required software to install

Install these first. Accept default options in each installer. **Restart your terminal**
after installing so the new commands are recognised.

| Software | Version | Why | Download |
|----------|---------|-----|----------|
| **Python** | 3.11 or newer | Runs the backend | https://www.python.org/downloads/ |
| **Node.js** | 20 LTS | Runs the frontend | https://nodejs.org/ |
| **Docker Desktop** | latest | Runs the PostgreSQL database | https://www.docker.com/products/docker-desktop/ |
| **Git** (optional) | latest | Version control | https://git-scm.com/ |
| **VS Code** (optional) | latest | Code editor | https://code.visualstudio.com/ |

> **IMPORTANT for Python:** on the first installer screen, tick **"Add python.exe to PATH"**
> before clicking Install. Otherwise the `python` command won't be found.

### Verify the tools are installed

Open a **new** Command Prompt and run each line. You should see a version number, not an error.

```bat
python --version
pip --version
node --version
npm --version
docker --version
```

If `python` shows nothing or an error, close and reopen the terminal. If it still fails,
re-run the Python installer and ensure "Add to PATH" is ticked.

---

## 2. Database setup (PostgreSQL via Docker)

Make sure **Docker Desktop is running** (launch it from the Start menu; wait until the whale
icon is steady). Then, from the project root:

```bat
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management"
docker compose up -d db
```

This downloads PostgreSQL and starts it in the background with everything pre-created:

- database name: `pms_onboarding`
- username: `pms`
- password: `pms`
- port: `5432`

Check it is healthy:

```bat
docker compose ps
```

You should see the `db` service with status `running` / `healthy`.

> **No Docker?** Install PostgreSQL 16 from https://www.postgresql.org/download/windows/.
> During install set the password, then open "SQL Shell (psql)" and run:
> ```sql
> CREATE USER pms WITH PASSWORD 'pms';
> CREATE DATABASE pms_onboarding OWNER pms;
> ```

---

## 3. Environment variables

The backend reads its configuration from a file named `.env` inside the `backend` folder.
**This file already exists** in the project — you do not need to create it. For reference,
these are the variables it contains:

| Variable | Example value | What it is |
|----------|---------------|------------|
| `DATABASE_URL` | `postgresql+psycopg://pms:pms@localhost:5432/pms_onboarding` | How the app connects to the database |
| `JWT_SECRET` | `dev-only-secret-change-me` | Secret used to sign login tokens |
| `PII_ENCRYPTION_KEY` | `hZ8c0J6n2pQ5sV8yB1eH4kN7qT0wZ3cF6iL9oR2uX5A=` | Key that encrypts PAN/Aadhaar/bank data |
| `ENVIRONMENT` | `local` | Enables the dev helpers |
| `MIN_INVESTMENT_INR` | `5000000` | SEBI minimum ticket (₹50 lakh) |

> The `PII_ENCRYPTION_KEY` must be a valid Fernet key (a 44-character base64 string). The one
> provided works out of the box. To generate your own later:
> ```bat
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

---

## 4. Backend setup and run

Open a Command Prompt and go to the **backend** folder:

```bat
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management\backend"
```

### 4a. Create and activate a virtual environment

A "virtual environment" keeps this project's Python packages separate from the rest of your
system.

```bat
python -m venv .venv
.venv\Scripts\activate
```

After activating you'll see `(.venv)` at the start of your prompt.

- **PowerShell** users: activate with `.venv\Scripts\Activate.ps1`. If you get a script
  execution error, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **macOS/Linux** users: `python3 -m venv .venv && source .venv/bin/activate`.

### 4b. Install the Python packages

```bat
pip install -r requirements.txt
```

This takes a minute or two the first time.

### 4c. Create the database tables (migrations)

```bat
alembic upgrade head
```

You should see Alembic running migration `0001_initial`. This creates all the onboarding
tables.

### 4d. Start the backend server

```bat
uvicorn app.main:app --reload
```

Leave this window open and running. You should see `Uvicorn running on http://127.0.0.1:8000`.

---

## 5. Frontend setup and run

Open a **second, separate** Command Prompt window (leave the backend running in the first).

```bat
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management\frontend"
npm install
npm run dev
```

`npm install` downloads the frontend packages (first time only). `npm run dev` starts the
app. You should see a line like `Local: http://localhost:5173/`. Leave this window running.

---

## 6. How to verify the BACKEND is working

Pick any of these (easiest first):

**A. Health check in the browser.** Open: http://localhost:8000/api/v1/healthz
You should see: `{"status":"ok"}`. Then try http://localhost:8000/api/v1/readyz — it returns
`{"status":"ready","db":"ok"}`, which also confirms the database connection works.

**B. Interactive API docs.** Open: http://localhost:8000/docs
You'll see the Swagger UI listing all endpoints. To try a protected one:
1. Expand `POST /api/v1/auth/dev-token`, click **Try it out**, then **Execute**. Copy the
   `access_token` from the response.
2. Click the green **Authorize** button (top right), paste the token, click Authorize.
3. Now you can run the onboarding endpoints with **Try it out**.

**C. Full end-to-end smoke test (best single proof).** In a new terminal, with the backend
running:

```bat
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management\backend"
.venv\Scripts\activate
python scripts\smoke_test.py
```

Expected output ends with `RESULT: PASS` and shows the status moving
`draft → kyc_verified → agreement_pending → under_review → active`.

**D. Unit tests (no database needed).**

```bat
pytest -q
```

You should see a row of dots and `passed`.

---

## 7. How to verify the FRONTEND is working

1. Open http://localhost:5173 — you should see the **"PMS Client Onboarding"** wizard.
2. Because every API call needs a login token, do this once:
   - Get a token from http://localhost:8000/docs (`POST /api/v1/auth/dev-token` → Execute →
     copy `access_token`), **or** from the smoke test output.
   - On the frontend tab, press **F12** to open Developer Tools, click **Console**, paste:
     ```js
     sessionStorage.setItem("access_token", "PASTE_YOUR_TOKEN_HERE")
     ```
     and press Enter.
3. Fill in the first step (use PAN `ABCDE1234F`, investment `5000000`, mobile `9876543210`)
   and click **Continue**. Walk through KYC → Risk Profile → Agreement. The final screen
   shows "Submitted for compliance review", which means the frontend and backend are talking
   to each other correctly.

---

## 8. Common errors and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `'python' is not recognized` | Python not on PATH | Reinstall Python with "Add to PATH" ticked; reopen terminal |
| `'docker' is not recognized` / "Cannot connect to the Docker daemon" | Docker Desktop not running | Start Docker Desktop, wait for it to finish loading, retry |
| `pip install` fails to build a package | Old pip | Run `python -m pip install --upgrade pip` then retry |
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from the wrong folder | `cd` into the `backend` folder first, then run `uvicorn app.main:app --reload` |
| Backend won't start: `Field required ... DATABASE_URL` | `.env` not found | Make sure you ran uvicorn from the `backend` folder where `.env` lives |
| `connection refused` / `could not connect to server` on `alembic upgrade` | Database not running | Run `docker compose up -d db` and wait until `docker compose ps` shows `healthy` |
| `password authentication failed for user "pms"` | Wrong DB credentials | Confirm DB is the Docker one; credentials are `pms`/`pms` |
| `ValueError: Invalid base64` / Fernet key error | `PII_ENCRYPTION_KEY` malformed | Use the provided key, or regenerate (see section 3) |
| `Port 5432 is already allocated` | Another PostgreSQL already running | Stop the other Postgres, or change the host port in `docker-compose.yml` (e.g. `"5433:5432"`) and update `DATABASE_URL` |
| `[Errno 10048] address already in use` (port 8000 or 5173) | Port busy | Close the other program, or run on another port: `uvicorn app.main:app --reload --port 8001` / `npm run dev -- --port 5174` |
| Browser shows `401 Unauthorized` in the wizard | No token set | Do the `sessionStorage.setItem(...)` step in section 7 |
| Browser console shows a CORS error | Frontend not on port 5173 | Run the frontend on `5173` (the backend only allows that origin); adjust origins in `backend/app/main.py` if you must use another port |
| PowerShell: "running scripts is disabled" when activating venv | Execution policy | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again |
| `npm run build` fails with TypeScript errors | Strict build | For first run use `npm run dev` (no type-check); fix types later before production |

---

## Quick reference — full start sequence

```bat
:: Terminal 0 — database (once, leave running in Docker)
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management"
docker compose up -d db

:: Terminal 1 — backend
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload

:: Terminal 2 — frontend
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management\frontend"
npm run dev
```

Then open http://localhost:5173 (app) and http://localhost:8000/docs (API).

To stop: press **Ctrl+C** in the backend and frontend windows, and run
`docker compose stop db` to stop the database (your data is kept for next time).
