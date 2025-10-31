#!/bin/bash
# Deployment script for Navigation System to Server

# Server details
SERVER_IP="64.23.234.72"
SERVER_USER="root"
SERVER_PASS="kuyi*&^HJjj666H"
REMOTE_DIR="/var/www/navigation2"

echo "🚀 Deploying Navigation System to Server..."
echo "=============================================="

# Create deployment package
echo "📦 Creating deployment package..."
tar -czf navigation2_deploy.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='cache/*.json' \
    --exclude='test_voice.mp3' \
    .

echo "✅ Deployment package created: navigation2_deploy.tar.gz"

# Upload to server using scp
echo "📤 Uploading to server..."
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no navigation2_deploy.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

# Execute deployment commands on server
echo "🔧 Setting up on server..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << 'EOF'
    echo "📁 Creating directory structure..."
    mkdir -p /var/www/navigation2
    cd /var/www/navigation2
    
    echo "📦 Extracting files..."
    tar -xzf /tmp/navigation2_deploy.tar.gz
    
    echo "🐍 Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "📋 Installing dependencies..."
    pip install --upgrade pip
    pip install flask flask-cors requests openrouteservice python-dotenv gtts pyttsx3 speechrecognition pyaudio geopy
    
    echo "🔧 Installing system dependencies..."
    apt update
    apt install -y espeak espeak-data festival festvox-kallpc16k alsa-utils
    
    echo "📝 Creating systemd service..."
    cat > /etc/systemd/system/navigation2.service << 'SERVICE_EOF'
[Unit]
Description=Navigation System for Blind Users
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/navigation2
Environment=PATH=/var/www/navigation2/venv/bin
ExecStart=/var/www/navigation2/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    echo "🔄 Enabling and starting service..."
    systemctl daemon-reload
    systemctl enable navigation2.service
    systemctl start navigation2.service
    
    echo "⏳ Waiting for service to start..."
    sleep 5
    
    echo "🔍 Checking service status..."
    systemctl status navigation2.service --no-pager
    
    echo "🌐 Testing web interface..."
    curl -s http://localhost:5001/api/health || echo "Service not responding yet"
    
    echo "🧹 Cleaning up..."
    rm /tmp/navigation2_deploy.tar.gz
    
    echo "✅ Deployment completed!"
    echo "🌐 Access your navigation system at: http://$SERVER_IP:5001"
EOF

echo ""
echo "🎉 Deployment completed successfully!"
echo "=============================================="
echo "🌐 Your Navigation System is now available at:"
echo "   http://64.23.234.72:5001"
echo ""
echo "📋 To check service status:"
echo "   ssh root@64.23.234.72 'systemctl status navigation2.service'"
echo ""
echo "📋 To view logs:"
echo "   ssh root@64.23.234.72 'journalctl -u navigation2.service -f'"
echo ""
echo "📋 To restart service:"
echo "   ssh root@64.23.234.72 'systemctl restart navigation2.service'"