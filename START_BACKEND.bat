@echo off
cd /d "C:\Users\AARYA\Desktop\discretionary portfolio management\backend"
echo Clearing migration cache...
rmdir /s /q "alembic\versions\__pycache__" 2>nul
echo Running alembic migrations...
alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo MIGRATION FAILED - check errors above
    pause
    exit /b 1
)
echo.
echo Starting uvicorn on port 8000...
uvicorn app.main:app --reload --port 8000
