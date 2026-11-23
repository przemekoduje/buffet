@echo off
title Buffet - Launcher
start "Buffet Backend (8000)" cmd /k "cd /d %~dp0backend && .\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 --reload"
start "Buffet Frontend (5173)" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 0.0.0.0"
