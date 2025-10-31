#!/bin/bash
# Full sync project files to server and restart service
set -euo pipefail
SERVER_IP="64.23.234.72"
SERVER_USER="root"
SERVER_PASS="kuyi*&^HJjj666H"

# Create dirs and copy code
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" 'mkdir -p /var/www/navigation2/templates /var/www/navigation2/static /var/www/navigation2/services /var/www/navigation2/data /var/www/navigation2/cache'
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no app.py config.py navigation_controller.py "$SERVER_USER@$SERVER_IP:/var/www/navigation2/"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no templates/index.html "$SERVER_USER@$SERVER_IP:/var/www/navigation2/templates/"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r services "$SERVER_USER@$SERVER_IP:/var/www/navigation2/"

# Restart service
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" 'systemctl restart navigation2-https.service && sleep 5 && systemctl status navigation2-https.service --no-pager || true'
