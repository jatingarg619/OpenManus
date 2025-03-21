#!/bin/bash

# Kill any existing processes on ports 3000, 8000 and 8001
kill_port() {
    local port=$1
    if lsof -i :$port > /dev/null; then
        echo "Killing process on port $port"
        lsof -ti :$port | xargs kill -9
    fi
}

kill_port 3000
kill_port 8000
kill_port 8001

# Create log directory if it doesn't exist
mkdir -p logs

# Start the FastAPI backend
echo "Starting FastAPI backend..."
cd "$(dirname "$0")"
PYTHONUNBUFFERED=1 python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
TIMEOUT=30
COUNTER=0
while ! curl -s http://localhost:8000/health > /dev/null; do
    sleep 1
    let COUNTER+=1
    if [ $COUNTER -ge $TIMEOUT ]; then
        echo "Error: Backend failed to start within $TIMEOUT seconds"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    echo -n "."
done
echo "Backend started!"

# Start the browser API server
echo "Starting Browser API server..."
python browser_api.py &
BROWSER_PID=$!

# Wait for browser API to initialize
sleep 2

# Start the React frontend
echo "Starting React frontend..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    npm install react-router-dom
fi

npm start &
FRONTEND_PID=$!

# Function to handle cleanup
cleanup() {
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null
    kill $BROWSER_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up cleanup trap
trap cleanup INT TERM

# Wait for user to press Ctrl+C
echo "Services running. Press Ctrl+C to stop."
wait 