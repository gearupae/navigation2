#!/bin/bash

# Fix Production Deployment Issues
# This script addresses the deployment problems on the production server

echo "=== Fixing Production Deployment Issues ==="
echo ""

echo "🔧 Issues Found:"
echo "1. App directory is /var/www/navigation2 (not /root/navigation2)"
echo "2. Python environment is externally managed"
echo "3. Dependencies need to be installed properly"
echo "4. App failed to start due to missing dependencies"
echo ""

echo "📋 Commands to Run on Production Server:"
echo ""

echo "1️⃣ Navigate to the correct directory:"
echo "   cd /var/www/navigation2"
echo ""

echo "2️⃣ Create a virtual environment:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo ""

echo "3️⃣ Install dependencies in virtual environment:"
echo "   pip install -r requirements.txt"
echo ""

echo "4️⃣ Install any missing system packages:"
echo "   apt update"
echo "   apt install -y python3-full python3-venv"
echo ""

echo "5️⃣ Start the application with virtual environment:"
echo "   source venv/bin/activate"
echo "   nohup python app.py runserver 5001 > app.log 2>&1 &"
echo ""

echo "6️⃣ Verify the deployment:"
echo "   ps aux | grep 'python app.py'"
echo "   tail -f app.log"
echo "   curl -s 'http://localhost:5001/api/navigation/unified-instruction'"
echo ""

echo "🌐 Alternative: Use system packages if virtual environment fails:"
echo "   pip install --break-system-packages -r requirements.txt"
echo "   nohup python app.py runserver 5001 > app.log 2>&1 &"
echo ""

echo "✅ Expected Results:"
echo "   - Application should start without errors"
echo "   - Unified instruction endpoint should work"
echo "   - All enhanced features should be available"
echo ""

echo "🔍 Troubleshooting:"
echo "   - Check logs: tail -f app.log"
echo "   - Check if app is running: ps aux | grep python"
echo "   - Test endpoint: curl -s 'http://localhost:5001/api/navigation/unified-instruction'"


