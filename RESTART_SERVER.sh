#!/bin/bash
# Quick restart script for production server
# Run this on the SERVER (after SSH)

echo "🔄 Restarting navigation server..."

cd /var/www/navigation2

# Kill old processes
pkill -9 gunicorn
sleep 3

# Start fresh
source venv/bin/activate
nohup gunicorn --workers 3 \
    --bind 0.0.0.0:5001 \
    --certfile=ssl/cert.pem \
    --keyfile=ssl/key.pem \
    --timeout 300 \
    --graceful-timeout 90 \
    --keep-alive 5 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    app:app > gunicorn_out.log 2>&1 &

sleep 4

# Verify
echo ""
echo "=== SERVER STATUS ==="
ps aux | grep gunicorn | grep -v grep | wc -l | xargs -I {} echo "Workers: {}"
lsof -i:5001 | head -2

echo ""
echo "✅ Server restarted!"
echo "🌐 Access: https://64.23.234.72:5001/google"

