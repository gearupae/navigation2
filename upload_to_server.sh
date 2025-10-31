#!/bin/bash

# Upload script for Navigation2 to production server
# Run this script and enter password when prompted

echo "=== Uploading Navigation2 to Production Server ==="
echo "Server: root@64.23.234.72"
echo "Password: kuyi*&^HJjj666H"
echo ""

# Upload all files
echo "Uploading files..."
scp -r production_deployment/* root@64.23.234.72:/root/navigation2/

echo ""
echo "✅ Upload completed!"
echo ""
echo "Next steps on the server:"
echo "1. SSH to server: ssh root@64.23.234.72"
echo "2. Navigate to app: cd /root/navigation2"
echo "3. Stop current app: pkill -f 'python app.py'"
echo "4. Start new app: nohup python app.py runserver 5001 > app.log 2>&1 &"
echo "5. Check logs: tail -f app.log"
echo ""
echo "Test the deployment:"
echo "curl -s 'http://64.23.234.72:5001/api/navigation/unified-instruction' | head -20"


