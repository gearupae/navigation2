#!/bin/bash
# Navigation System Startup Script

echo "🚀 Starting Navigation System..."
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if required packages are installed (including Pillow for vision)
echo "🔍 Checking dependencies..."
python -c "import flask, requests, openrouteservice, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies! Installing..."
    pip install flask flask-cors requests openrouteservice python-dotenv gtts pyttsx3 speechrecognition pyaudio geopy Pillow
fi

# Start the application
echo "🌐 Starting Flask application on http://localhost:5001"
echo "Press Ctrl+C to stop the server"
echo "================================"

python app.py





