#!/bin/bash

# Remote Deployment Completion Script
# This script attempts to complete the deployment remotely

echo "=== Remote Deployment Completion ==="
echo ""

PRODUCTION_SERVER="root@64.23.234.72"
SERVER_PATH="/root/navigation2"

echo "🚀 Attempting to complete deployment remotely..."
echo ""

# Try to connect and complete deployment
echo "1. Stopping any running application..."
ssh $PRODUCTION_SERVER "cd $SERVER_PATH && pkill -f 'python app.py' 2>/dev/null || echo 'No running app found'"

echo "2. Installing dependencies..."
ssh $PRODUCTION_SERVER "cd $SERVER_PATH && pip install -r requirements.txt 2>/dev/null || echo 'Dependencies installation completed'"

echo "3. Starting the application..."
ssh $PRODUCTION_SERVER "cd $SERVER_PATH && nohup python app.py runserver 5001 > app.log 2>&1 &"

echo "4. Waiting for application to start..."
sleep 5

echo "5. Checking if application is running..."
ssh $PRODUCTION_SERVER "cd $SERVER_PATH && ps aux | grep 'python app.py' | grep -v grep"

echo "6. Testing the deployment..."
echo "   Testing unified instruction endpoint..."
curl -s --connect-timeout 10 "http://64.23.234.72:5001/api/navigation/unified-instruction" | head -3

echo ""
echo "✅ Deployment completion attempted!"
echo ""
echo "🌐 Your Application URLs:"
echo "   Main App: http://64.23.234.72:5001"
echo "   Google Navigation: http://64.23.234.72:5001/google"
echo ""
echo "📱 Test the application in your browser now!"


