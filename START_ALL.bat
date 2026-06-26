@echo off
cd /d "C:\Users\AARYA\Desktop\discretionary portfolio management"

echo [1/3] Starting PostgreSQL + Redis via Docker...
start "Docker DB" cmd /k "cd /d "C:\Users\AARYA\Desktop\discretionary portfolio management" && docker compose up db redis"

echo Waiting 10s for DB to be ready...
timeout /t 10 /nobreak > nul

echo [2/3] Starting Backend...
start "Backend" cmd /k "cd /d "C:\Users\AARYA\Desktop\discretionary portfolio management\backend" && pip install -r requirements.txt -q && alembic upgrade head && uvicorn app.main:app --reload --port 8000"

echo Waiting 5s for backend to start...
timeout /t 5 /nobreak > nul

echo [3/3] Starting Frontend...
start "Frontend" cmd /k "cd /d "C:\Users\AARYA\Desktop\discretionary portfolio management\frontend" && npm install && npm run dev"

echo.
echo All services launching!
echo   Backend API:  http://localhost:8000/docs
echo   Frontend:     http://localhost:5173
