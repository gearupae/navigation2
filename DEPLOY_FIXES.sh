#!/bin/bash
# Deploy fixes to production server

echo "📦 Deploying blind-user safety fixes to server..."

# Upload app.py
echo "⬆️  Uploading app.py..."
scp app.py root@64.23.234.72:/var/www/navigation2/app.py

# Restart server
echo "🔄 Restarting server..."
ssh root@64.23.234.72 '
cd /var/www/navigation2 && \
pkill -9 gunicorn && \
sleep 3 && \
source venv/bin/activate && \
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
sleep 4 && \
ps aux | grep gunicorn | grep -v grep | wc -l
'

echo ""
echo "✅ Deployment complete!"
echo "🌐 Test at: https://64.23.234.72:5001/google"
echo ""
echo "📋 Changes deployed:"
echo "  ✅ Obstacle warning comes FIRST (before distance)"
echo "  ✅ No specific object names (only 'obstacle detected')"
echo "  ✅ Instructions update when obstacles change"
echo "  ✅ Faster LLM responses (15s timeout, 50 tokens)"
echo "  ✅ Smaller images (800x600, 50% quality)"


