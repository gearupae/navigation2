#!/bin/bash

# Quick Fix for Production Server Firewall
# This will configure the firewall and ensure the app is accessible

echo "=== Quick Fix for Production Server ==="
echo ""
echo "⚠️  You need to type 'yes' and enter password: kuyi*&^HJjj666H"
echo ""

cat << 'COMMANDS'
# Run these commands on your production server:

ssh root@64.23.234.72 << 'ENDSSH'

# 1. Check firewall status
echo "=== Checking Firewall ==="
ufw status

# 2. Allow port 5001 if firewall is active
echo ""
echo "=== Allowing Port 5001 ==="
ufw allow 5001/tcp

# 3. Check what's running
echo ""
echo "=== Checking Running Processes ==="
netstat -tlnp | grep :5001 || echo "No process on port 5001"

# 4. Check Flask app
echo ""
echo "=== Checking Flask App ==="
ps aux | grep 'python app.py' | grep -v grep

# 5. Navigate to app directory
cd /var/www/navigation2

# 6. Check if app responds locally
echo ""
echo "=== Testing Local Access ==="
curl -s http://localhost:5001/google | head -10

# 7. Show app log tail
echo ""
echo "=== Recent App Logs ==="
tail -20 app.log 2>/dev/null || echo "No log file found"

ENDSSH

COMMANDS

echo ""
echo "════════════════════════════════════════════════════════"
echo "🎯 KEY POINTS:"
echo ""
echo "1. URL CORRECTION:"
echo "   ❌ Wrong: https://64.23.234.72:5002/google"
echo "   ✅ Right: http://64.23.234.72:5001/google"
echo ""
echo "2. CHANGES:"
echo "   - Use HTTP not HTTPS"
echo "   - Use port 5001 not 5002"
echo ""
echo "3. BROWSER ACCESS:"
echo "   Open this in your browser:"
echo "   👉 http://64.23.234.72:5001/google"
echo ""
echo "════════════════════════════════════════════════════════"


