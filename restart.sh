#!/bin/bash
# Convenience script to restart the navigation app

echo "Stopping any running instances..."
pkill -f "python app.py" 2>/dev/null

# Wait a moment for processes to die
sleep 1

# Check if port is still in use
if sudo lsof -i :5001 >/dev/null 2>&1; then
    echo "Force killing processes on port 5001..."
    sudo kill -9 $(sudo lsof -t -i:5001) 2>/dev/null
    sleep 1
fi

echo "Starting navigation app..."
python app.py
