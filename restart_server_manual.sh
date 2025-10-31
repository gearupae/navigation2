#!/bin/bash

cat << 'EOF'
═══════════════════════════════════════════════════════════
🔧 MANUAL SERVER RESTART INSTRUCTIONS
═══════════════════════════════════════════════════════════

The server is running OLD code. You need to restart it manually.

COPY AND PASTE THESE COMMANDS ONE BY ONE:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ssh root@64.23.234.72

# Password: kuyi*&^HJjj666H

cd /var/www/navigation2

pkill -9 gunicorn

lsof -ti:5001 | xargs kill -9

sleep 3

nohup /var/www/navigation2/start_https.sh > /dev/null 2>&1 &

sleep 5

ps aux | grep gunicorn

curl -k -s https://localhost:5001/google | head -5

exit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AFTER RESTART:

1. Open: https://64.23.234.72:5001/google
2. Clear browser cache (Ctrl+Shift+Delete)
3. Reload page
4. Test navigation

✅ EXPECTED RESULTS:

- No 500 error
- No 400 error
- Natural instructions (no brackets)
- Stable instructions (no changes when still)
- Different session IDs for different users

═══════════════════════════════════════════════════════════

EOF


