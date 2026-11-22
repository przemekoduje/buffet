#!/bin/bash
# Skrypt startowy projektu BUFFET (Backend FastAPI + Frontend React/Vite)

echo "=========================================================="
echo "      BUFFET — Value Investing & AI Screener"
echo "  '1: Nigdy nie trać pieniędzy. 2: Pamiętaj o punkcie 1'"
echo "=========================================================="

# 1. Start Backend w tle
echo "-> Uruchamianie Backend (FastAPI na porcie 8000)..."
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Start Frontend
echo "-> Uruchamianie Frontend (Vite na porcie 5173)..."
cd frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo "=========================================================="
echo " Aplikacja dziala:"
echo " - Frontend (Panel Admina): http://localhost:5173"
echo " - Backend API Swagger:     http://localhost:8000/docs"
echo "=========================================================="
echo "Nacisnij CTRL+C, aby zatrzymac oba procesy."

# Obsługa zatrzymania
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait
