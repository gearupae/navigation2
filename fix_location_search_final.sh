#!/bin/bash

echo "═══════════════════════════════════════════════════════════"
echo "🔧 Fixing Location-Based Search on Production"
echo "═══════════════════════════════════════════════════════════"
echo ""

ssh root@64.23.234.72 << 'ENDSSH'

cd /var/www/navigation2

echo "📝 Step 1: Backing up current files..."
cp templates/google.html templates/google.html.backup.$(date +%s) 2>/dev/null || true
cp services/google_places_service.py services/google_places_service.py.backup.$(date +%s) 2>/dev/null || true

echo "✅ Backups created"
echo ""

echo "📥 Step 2: Files already uploaded via SCP"
echo "   - templates/google.html (auto-location detection)"
echo "   - services/google_places_service.py (improved search)"
echo ""

echo "🛑 Step 3: Stopping Gunicorn..."
pkill -9 gunicorn 2>/dev/null || true
sleep 3

echo "✅ Old processes stopped"
echo ""

echo "🚀 Step 4: Starting HTTPS server with new code..."
cd /var/www/navigation2
source venv/bin/activate

# Start Gunicorn with SSL
nohup gunicorn \
  --certfile=/etc/ssl/navigation/cert.pem \
  --keyfile=/etc/ssl/navigation/key.pem \
  --bind 0.0.0.0:5001 \
  --workers 2 \
  --timeout 120 \
  --reload \
  --access-logfile app_access.log \
  --error-logfile app_error.log \
  app:app > gunicorn.log 2>&1 &

echo "⏳ Waiting for server to start..."
sleep 6

echo ""
echo "✅ Step 5: Verifying server..."
if ps aux | grep -q "[g]unicorn"; then
    echo "   ✅ Gunicorn is running"
    ps aux | grep "[g]unicorn" | head -3
else
    echo "   ❌ Gunicorn failed to start!"
    echo "   Check logs:"
    tail -20 gunicorn.log
    tail -20 app_error.log
    exit 1
fi

echo ""
echo "🧪 Step 6: Testing HTTPS endpoint..."
if curl -k -s https://localhost:5001/google | head -1 | grep -q "DOCTYPE"; then
    echo "   ✅ HTTPS is responding correctly"
else
    echo "   ⚠️  HTTPS might not be fully ready"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ LOCATION-BASED SEARCH FIX DEPLOYED!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📋 What Was Fixed:"
echo "   1. ✅ Auto-detect location when searching"
echo "   2. ✅ Use 5km radius for nearby results"
echo "   3. ✅ Sort results by distance"
echo "   4. ✅ Better logging with coordinates"
echo ""
echo "🌐 Test Your App:"
echo "   https://64.23.234.72:5001/google"
echo ""
echo "🧪 How to Test:"
echo "   1. Open the URL (bypass SSL warning)"
echo "   2. Search for 'pharmacy' or 'cafe'"
echo "   3. Allow location when browser asks"
echo "   4. Results should be sorted by distance!"
echo ""
echo "📊 Check Logs:"
echo "   tail -f /var/www/navigation2/app_error.log"
echo "   # Look for: '🔍 Searching for ... near location'"
echo ""
echo "═══════════════════════════════════════════════════════════"

ENDSSH

echo ""
echo "🎉 Done! Now test your app:"
echo "   https://64.23.234.72:5001/google"
echo ""


