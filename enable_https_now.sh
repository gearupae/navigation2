#!/bin/bash

# Quick HTTPS Setup with Self-Signed Certificate
# This script automates the setup process

echo "═══════════════════════════════════════════════════════════"
echo "🔒 Enabling HTTPS with Self-Signed Certificate"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "This will:"
echo "  1. Generate SSL certificate"
echo "  2. Install Gunicorn"
echo "  3. Start server with HTTPS"
echo ""
echo "⚠️  Browser will show security warning (this is normal for self-signed)"
echo ""
echo "Password: kuyi*&^HJjj666H"
echo ""

ssh root@64.23.234.72 << 'ENDSSH'

echo "📁 Step 1: Creating SSL directory..."
mkdir -p /etc/ssl/navigation
cd /etc/ssl/navigation

echo ""
echo "🔐 Step 2: Generating self-signed certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=AE/ST=AbuDhabi/L=AbuDhabi/O=Navigation/CN=64.23.234.72" 2>&1 | grep -v "^writing"

echo ""
echo "📦 Step 3: Installing Gunicorn..."
cd /var/www/navigation2
source venv/bin/activate
pip install gunicorn --quiet

echo ""
echo "📝 Step 4: Creating startup script..."
cat > /var/www/navigation2/start_https.sh << 'STARTSCRIPT'
#!/bin/bash
cd /var/www/navigation2
source venv/bin/activate
gunicorn --certfile=/etc/ssl/navigation/cert.pem \
         --keyfile=/etc/ssl/navigation/key.pem \
         --bind 0.0.0.0:5001 \
         --workers 2 \
         --timeout 120 \
         --access-logfile app_access.log \
         --error-logfile app_error.log \
         app:app
STARTSCRIPT

chmod +x /var/www/navigation2/start_https.sh

echo ""
echo "🛑 Step 5: Stopping old processes..."
pkill -f 'python app.py' 2>/dev/null || true
pkill -f 'gunicorn' 2>/dev/null || true
sleep 2

echo ""
echo "🚀 Step 6: Starting HTTPS server..."
nohup /var/www/navigation2/start_https.sh > /dev/null 2>&1 &
sleep 4

echo ""
echo "✅ Step 7: Verifying server status..."
if ps aux | grep -q "[g]unicorn"; then
    echo "   ✅ Gunicorn is running"
    ps aux | grep "[g]unicorn" | head -2
else
    echo "   ❌ Gunicorn failed to start - check logs"
fi

echo ""
echo "🧪 Step 8: Testing HTTPS endpoint..."
if curl -k -s https://localhost:5001/google | head -1 | grep -q "DOCTYPE"; then
    echo "   ✅ HTTPS is working!"
else
    echo "   ⚠️  HTTPS might not be responding yet"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ HTTPS SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🌐 Your HTTPS URL:"
echo "   https://64.23.234.72:5001/google"
echo ""
echo "⚠️  IMPORTANT - Browser Security Warning:"
echo "   1. Browser will show 'Your connection is not private'"
echo "   2. Click 'Advanced'"
echo "   3. Click 'Proceed to 64.23.234.72 (unsafe)'"
echo "   4. This is NORMAL for self-signed certificates"
echo ""
echo "🎥 Camera Access:"
echo "   - Now camera will work over HTTPS!"
echo "   - Click 'Start Camera' and allow permissions"
echo ""
echo "📋 Logs:"
echo "   Access: tail -f /var/www/navigation2/app_access.log"
echo "   Errors: tail -f /var/www/navigation2/app_error.log"
echo ""
echo "🔄 To restart server:"
echo "   pkill gunicorn && nohup /var/www/navigation2/start_https.sh > /dev/null 2>&1 &"
echo ""
echo "═══════════════════════════════════════════════════════════"

ENDSSH

echo ""
echo "🎉 Done! Try accessing:"
echo "   https://64.23.234.72:5001/google"
echo ""


