#!/bin/bash

# Restart Production Server with Updated Files

echo "=== Restarting Production Server ==="
echo ""

ssh root@64.23.234.72 << 'ENDSSH'

echo "📂 Navigating to app directory..."
cd /var/www/navigation2

echo "🛑 Stopping existing Flask processes..."
pkill -f 'python app.py'
sleep 2

echo "🔍 Verifying processes stopped..."
ps aux | grep 'python app.py' | grep -v grep || echo "✅ All Flask processes stopped"

echo "🚀 Starting Flask application..."
source venv/bin/activate
nohup python app.py runserver 5001 > app.log 2>&1 &

echo "⏳ Waiting for server to start..."
sleep 3

echo "✅ Checking if server is running..."
ps aux | grep 'python app.py' | grep -v grep

echo ""
echo "🧪 Testing server response..."
curl -s http://localhost:5001/google | head -10

echo ""
echo "📋 Recent logs:"
tail -20 app.log

ENDSSH

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo ""
echo "🌐 Test your application:"
echo "   http://64.23.234.72:5001/google"
echo ""
echo "🔬 Features to Test:"
echo "   1. Search without clicking 'Get Location' first"
echo "   2. Results should be sorted by distance"
echo "   3. Voice should announce distances"
echo "   4. Check browser console for location logs"
echo ""
echo "════════════════════════════════════════════════════════"


