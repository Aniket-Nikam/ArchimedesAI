@echo off
title Archimedes - Starting...

echo ========================================
echo    Starting Archimedes
echo ========================================
echo.

:: Start backend
echo [1/2] Starting Backend (FastAPI)...
start "Archimedes Backend" cmd /k "cd /d %~dp0 && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Small delay to let backend initialize
timeout /t 2 /nobreak >nul

:: Start frontend
echo [2/2] Starting Frontend (Vite)...
start "Archimedes Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo    Both servers are starting!
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo ========================================
echo.
echo You can close this window.
timeout /t 5
