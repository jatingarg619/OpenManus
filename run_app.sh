#!/bin/bash

# Set environment variables
export PYTHONPATH=$(pwd)

# Function to kill process using a port
kill_port() {
    local port=$1
    local pid=$(lsof -t -i:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process using port $port (PID: $pid)"
        kill -9 $pid
    fi
}

# Kill processes on required ports
echo "Checking for processes using required ports..."
kill_port 3000  # React frontend
kill_port 8000  # Backend server
kill_port 8001  # Browser API

# Wait a moment for processes to be killed
sleep 2

# Start the frontend
echo "Starting frontend..."
cd frontend
npm start &
FRONTEND_PID=$!

# Go back to project root for the API server
cd ..

# Start the browser API server
echo "Starting Browser API server..."
python browser_api.py &
BROWSER_PID=$!

# Wait for browser API to initialize
sleep 2

# Start the backend server
echo "Starting backend server..."
python -m app.api.main &
BACKEND_PID=$!

# Wait for all processes
wait $FRONTEND_PID $BROWSER_PID $BACKEND_PID 