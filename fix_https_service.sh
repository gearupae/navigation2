#!/bin/bash
# Fix HTTPS service on server by creating logs dir and restarting

SERVER_IP="64.23.234.72"
SERVER_USER="root"
SERVER_PASS="kuyi*&^HJjj666H"

set -euo pipefail

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'EOF'
set -e
mkdir -p /var/www/navigation2/logs /var/www/navigation2/templates /var/www/navigation2/static
chown -R root:root /var/www/navigation2
systemctl daemon-reload
systemctl restart navigation2-https.service || true
sleep 5
echo "==== STATUS ===="
systemctl status navigation2-https.service --no-pager || true
echo "==== LISTEN PORTS ===="
ss -tulpn | grep :5001 || true
echo "==== HEALTH localhost ===="
curl -k -sS https://localhost:5001/api/health || true
echo
echo "==== LOG TAIL ===="
[ -f /var/www/navigation2/logs/navigation_https.log ] && tail -n 200 /var/www/navigation2/logs/navigation_https.log || echo "No HTTPS log file yet"
echo
journalctl -u navigation2-https.service --no-pager -n 50 || true
EOF
