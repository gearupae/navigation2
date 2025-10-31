#!/bin/bash

# Fix Port Conflict on Production Server
# This script resolves the port 5001 conflict issue

echo "=== Fixing Port Conflict on Production Server ==="
echo ""

echo "🔧 Issue: Port 5001 is already in use"
echo "✅ Good news: I can see Python processes are already running!"
echo ""

echo "📋 Commands to Run on Production Server:"
echo ""

echo "1️⃣ Check what's using port 5001:"
echo "   lsof -i :5001"
echo ""

echo "2️⃣ Kill any conflicting processes:"
echo "   lsof -ti:5001 | xargs kill -9"
echo ""

echo "3️⃣ Check if the app is already running:"
echo "   ps aux | grep 'python app.py'"
echo ""

echo "4️⃣ If app is running, test it:"
echo "   curl -s 'http://localhost:5001/api/navigation/unified-instruction'"
echo ""

echo "5️⃣ If app is not running, start it:"
echo "   source venv/bin/activate"
echo "   nohup python app.py runserver 5001 > app.log 2>&1 &"
echo ""

echo "6️⃣ Alternative - Use a different port:"
echo "   source venv/bin/activate"
echo "   nohup python app.py runserver 5002 > app.log 2>&1 &"
echo ""

echo "🌐 Test Your Application:"
echo "   Main App: http://64.23.234.72:5001"
echo "   Google Navigation: http://64.23.234.72:5001/google"
echo ""

echo "✅ Expected Results:"
echo "   - Application should be accessible"
echo "   - Unified instruction endpoint should work"
echo "   - All enhanced features should be available"
echo ""

echo "🔍 Troubleshooting:"
echo "   - Check logs: tail -f app.log"
echo "   - Check processes: ps aux | grep python"
echo "   - Test endpoint: curl -s 'http://localhost:5001/api/navigation/unified-instruction'"


