#!/bin/bash

# Activate Python venv and start FastAPI backend
source .venv/bin/activate

# Kill any process using port 8000 (backend) or 3000 (frontend) to avoid conflicts
echo "[INFO] Killing processes on ports 8000 and 3000 (if any)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start FastAPI backend
uvicorn main:app --reload &
BACKEND_PID=$!
echo "[Backend] FastAPI running with PID $BACKEND_PID."

# Start frontend React app
cd frontend
npm start &
FRONTEND_PID=$!
echo "[Frontend] React app running with PID $FRONTEND_PID."
cd ..

echo "---"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "---"

# Wait for both to exit
wait $BACKEND_PID $FRONTEND_PID
