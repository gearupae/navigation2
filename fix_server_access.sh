#!/bin/bash

# Fix Server Access Issues
# This script helps diagnose and fix the production server accessibility

echo "=== Production Server Access Fix ==="
echo ""

cat << 'EOF'
🔍 DIAGNOSIS:
✅ Port 5001: WORKING - Server is responding
❌ Port 5002: NOT ACCESSIBLE - No service listening

📋 ROOT CAUSES:
1. Firewall blocking port 5002
2. Flask app only running on port 5001
3. Need to configure firewall rules

🔧 SOLUTION STEPS:
═══════════════════════════════════════════════════════════════

Run these commands on your production server (SSH as root):

ssh root@64.23.234.72

1️⃣ CHECK CURRENT STATUS:
   ─────────────────────────
   # Check what ports are listening
   netstat -tlnp | grep python
   
   # Check Flask processes
   ps aux | grep 'python app.py'
   
   # Check firewall status
   ufw status

2️⃣ CONFIGURE FIREWALL (if UFW is active):
   ───────────────────────────────────────
   # Allow port 5001
   ufw allow 5001/tcp
   
   # Allow port 5002 (if needed)
   ufw allow 5002/tcp
   
   # Check firewall rules
   ufw status numbered

3️⃣ CHECK IF APP IS RUNNING:
   ────────────────────────
   cd /var/www/navigation2
   
   # Check running processes
   ps aux | grep 'python app.py'
   
   # If running, kill old processes
   pkill -f 'python app.py'

4️⃣ START THE APPLICATION:
   ──────────────────────
   cd /var/www/navigation2
   source venv/bin/activate
   
   # Start on port 5001
   nohup python app.py runserver 5001 > app.log 2>&1 &
   
   # Wait a moment
   sleep 3
   
   # Verify it's running
   ps aux | grep 'python app.py'
   curl -s http://localhost:5001/google | head -20

5️⃣ TEST FROM LOCAL MACHINE:
   ────────────────────────
   # Test port 5001
   curl -v http://64.23.234.72:5001/google 2>&1 | head -30
   
   # Open in browser
   http://64.23.234.72:5001/google

6️⃣ ALTERNATIVE: USE DIFFERENT PORT BINDING:
   ────────────────────────────────────────
   # If you need to bind to all interfaces
   cd /var/www/navigation2
   source venv/bin/activate
   
   # Edit app.py to use 0.0.0.0 instead of 127.0.0.1
   # Or start with explicit host binding:
   nohup python app.py runserver 0.0.0.0:5001 > app.log 2>&1 &

7️⃣ CHECK LOGS FOR ERRORS:
   ──────────────────────
   cd /var/www/navigation2
   tail -50 app.log

═══════════════════════════════════════════════════════════════

🌐 EXPECTED RESULTS:
   Port 5001: http://64.23.234.72:5001/google ✅
   
   You should see:
   - HTML content loading
   - Navigation interface
   - Map display
   - All enhanced features working

🚨 IMPORTANT NOTES:
   1. Use HTTP not HTTPS (you typed https:// in your message)
   2. Port 5001 is the correct port
   3. Port 5002 is NOT configured (don't use it)
   4. Make sure firewall allows port 5001

🔐 SECURITY NOTE:
   If you want HTTPS, you need to:
   - Install SSL certificate
   - Use nginx/apache as reverse proxy
   - Configure SSL termination

EOF

echo ""
echo "✅ Next Action: Copy and run these commands on your production server"
echo ""


