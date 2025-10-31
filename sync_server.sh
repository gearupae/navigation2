#!/bin/bash
# Sync updated app and template to server and restart HTTPS service

SERVER_IP="64.23.234.72"
SERVER_USER="root"
SERVER_PASS="kuyi*&^HJjj666H"

set -euo pipefail

sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
  app.py templates/index.html "$SERVER_USER@$SERVER_IP:/var/www/navigation2/"

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'EOF'
set -e
systemctl restart navigation2-https.service
sleep 3
curl -k -sS https://localhost:5001/api/status || true
EOF
