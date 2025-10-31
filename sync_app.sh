#!/bin/bash
# Sync updated app.py to server and restart service
SERVER_IP=64.23.234.72
SERVER_USER=root
SERVER_PASS='kuyi*&^HJjj666H'
set -euo pipefail
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no app.py $SERVER_USER@$SERVER_IP:/var/www/navigation2/app.py
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP 'systemctl restart navigation2-https.service && sleep 3 && systemctl status navigation2-https.service --no-pager || true'
