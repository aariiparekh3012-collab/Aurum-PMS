# Deployment Guide — PMS Platform (Free Tier)

**Stack:** Vercel (frontend) + Render (backend) + Neon (database)  
**Cost:** $0 — all free tier

---

## STEP 1: Push Code to GitHub

Open PowerShell in your project folder:

```powershell
cd "C:\Users\AARYA\OneDrive\Desktop\discretionary portfolio management"
```

If this is a fresh start (no git repo yet):
```powershell
git init
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

If the repo already exists, skip the above.

```powershell
git add .
git commit -m "Deploy: all fixes applied"
git branch -M main
git push -u origin main
```

> **If git asks for identity:**
> ```powershell
> git config user.email "aariiparekh3012@gmail.com"
> git config user.name "Aarya"
> ```

---

## STEP 2: Create Neon Database

1. Go to **https://neon.tech** → Sign up (use GitHub login)
2. Click **"New Project"** → Name it `pms` → Region: pick closest → Create
3. Copy the **connection string** — it looks like:
   ```
   postgresql://neondb_owner:XXXX@ep-something.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. **IMPORTANT:** If the connection string has `channel_binding=require` at the end, **remove that part**. Only keep `?sslmode=require`.

5. Open the **SQL Editor** in Neon dashboard and run this:

```sql
CREATE SCHEMA IF NOT EXISTS client;
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS portfolio;
CREATE SCHEMA IF NOT EXISTS performance;
CREATE SCHEMA IF NOT EXISTS notifications;
```

Save your connection string somewhere — you'll need it in Step 3.

---

## STEP 3: Deploy Backend on Render

1. Go to **https://render.com** → Sign up (use GitHub login)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `pms-api` (or whatever you want) |
| **Region** | Oregon (or closest) |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

5. **Add Environment Variables** (click "Add Environment Variable" for each):

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Neon connection string from Step 2 |
| `JWT_SECRET` | Any random 32+ char string (e.g. `mySuper$ecretKey2024forJWTsigning!`) |
| `PII_ENCRYPTION_KEY` | A Fernet key (see below how to generate) |
| `CORS_ORIGINS` | Leave blank for now — you'll fill this after Step 4 |
| `ENVIRONMENT` | `production` |
| `PYTHON_VERSION` | `3.11.9` |

6. Click **"Deploy Web Service"**

### How to generate PII_ENCRYPTION_KEY:

Open PowerShell and run:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Or if you don't have Python with cryptography installed, use this pre-generated one for testing:
```
B5xHl5YOlKrJcE5S_YN3bKl3-5FlrZY7-X3l0Uv5qQo=
```

### Wait for deploy to finish (~3-5 min)

Once deployed, you'll get a URL like `https://pms-api-xxxx.onrender.com`

**Test it:** Open `https://YOUR-RENDER-URL/docs` in your browser. You should see the Swagger UI.

> **NOTE:** Free tier sleeps after 15 min of no traffic. First request after sleep takes ~30 seconds.

---

## STEP 4: Deploy Frontend on Vercel

1. Go to **https://vercel.com** → Sign up (use GitHub login)
2. Click **"Add New..." → "Project"**
3. Import your GitHub repo
4. Configure:

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

5. **Add Environment Variable:**

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://YOUR-RENDER-URL/api/v1` |

   Replace `YOUR-RENDER-URL` with the actual Render URL from Step 3 (e.g. `https://pms-api-xxxx.onrender.com/api/v1`)

6. Click **"Deploy"**

Once deployed, you'll get a URL like `https://your-project.vercel.app`

---

## STEP 5: Update CORS on Render

Now that you have the Vercel URL:

1. Go back to **Render Dashboard** → your web service → **Environment**
2. Set `CORS_ORIGINS` to your Vercel URL:
   ```
   https://your-project.vercel.app
   ```
3. Click **Save Changes** → Render will auto-redeploy

---

## STEP 6: Test Everything

1. Open your Vercel URL in the browser
2. Click **"Create Account"**
3. Enter email, password (8-64 chars), full name
4. You should be logged in and see the dashboard

> **If the first request is slow:** That's Render's free tier cold start (~30 sec). Just wait.

---

## Troubleshooting

### "Network Error" on register/login
- Check Render is running (visit `https://YOUR-RENDER-URL/docs`)
- Check `CORS_ORIGINS` on Render matches your exact Vercel URL (no trailing slash)
- Check `VITE_API_URL` on Vercel ends with `/api/v1`

### Render build fails
- Make sure **Root Directory** is set to `backend`
- Make sure **Runtime** is Python (NOT Docker)
- Check `PYTHON_VERSION` env var is `3.11.9`
- There should be NO file named `Dockerfile` in backend/ (only `Dockerfile.local`)

### 500 error on register
- Check Render logs for the actual error message
- Make sure all 6 schemas were created in Neon (Step 2)
- Make sure `DATABASE_URL` doesn't have `channel_binding=require`

### Vercel shows blank page
- Check `VITE_API_URL` is set correctly
- Redeploy: Vercel Dashboard → Deployments → Redeploy

### "Internal Server Error" with no details
- The catch-all handler in the code now prints tracebacks to Render logs
- Go to Render → your service → Logs to see the actual error

---

## Quick Reference

| Service | URL Pattern | Dashboard |
|---------|------------|-----------|
| Frontend | `https://your-project.vercel.app` | vercel.com/dashboard |
| Backend | `https://pms-api-xxxx.onrender.com` | dashboard.render.com |
| Backend Docs | `https://pms-api-xxxx.onrender.com/docs` | — |
| Database | — | console.neon.tech |
