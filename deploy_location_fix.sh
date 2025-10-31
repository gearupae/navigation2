#!/bin/bash

# Deploy Location-Based Search Fix to Production Server
# This script deploys the improved search functionality

echo "=== Deploying Location-Based Search Fix ==="
echo ""

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p location_fix_deployment

# Copy updated files
echo "📄 Copying updated files..."
cp templates/google.html location_fix_deployment/
cp services/google_places_service.py location_fix_deployment/

# Create deployment instructions
cat > location_fix_deployment/DEPLOY_INSTRUCTIONS.txt << 'EOF'
=== Location-Based Search Fix Deployment ===

ISSUE FIXED:
- Search was not using user's current location
- Results were random/not sorted by distance
- No automatic location detection on search

IMPROVEMENTS:
1. ✅ Auto-detect location when searching (if not already set)
2. ✅ Use location for nearby search (5km radius)
3. ✅ Sort results by distance from user
4. ✅ Better logging to track search parameters
5. ✅ Announce distance in voice feedback

FILES TO UPDATE:
1. templates/google.html
2. services/google_places_service.py

DEPLOYMENT STEPS:
══════════════════════════════════════════════════════════

1. SSH to Production Server:
   ssh root@64.23.234.72
   Password: kuyi*&^HJjj666H

2. Navigate to App Directory:
   cd /var/www/navigation2

3. Backup Current Files:
   cp templates/google.html templates/google.html.backup
   cp services/google_places_service.py services/google_places_service.py.backup

4. Upload New Files (from your local machine):
   # On your local machine, run:
   cd /home/gearup/Work/navigation2
   scp templates/google.html root@64.23.234.72:/var/www/navigation2/templates/
   scp services/google_places_service.py root@64.23.234.72:/var/www/navigation2/services/

5. Restart Flask Application (on production server):
   cd /var/www/navigation2
   
   # Kill old processes
   pkill -f 'python app.py'
   
   # Start new process with virtual environment
   source venv/bin/activate
   nohup python app.py runserver 5001 > app.log 2>&1 &
   
   # Verify it's running
   sleep 3
   ps aux | grep 'python app.py' | grep -v grep
   curl -s http://localhost:5001/google | head -20

6. Test the Fix:
   # Open in browser:
   http://64.23.234.72:5001/google
   
   # Test search:
   - Enter a search query (e.g., "pharmacy", "cafe")
   - Click "Search with Google"
   - If location permission requested, allow it
   - Results should be sorted by distance from your current location
   - Voice feedback should announce distances

7. Check Logs:
   cd /var/www/navigation2
   tail -f app.log
   
   # Look for lines like:
   # "🔍 Searching for 'pharmacy' near location (24.xxxx, 54.xxxx) with radius 5000m"
   # "✅ Returning X filtered results"

VERIFICATION:
════════════════════════════════════════════════════════

✅ Search button automatically gets location if not set
✅ Search results show distance in meters
✅ Results are sorted by proximity (closest first)
✅ Voice announces: "Found X results nearby. First result: [name], [distance] meters away"
✅ Logs show location coordinates being used in search

TROUBLESHOOTING:
════════════════════════════════════════════════════════

Problem: "Location denied" message
Fix: User needs to allow location access in browser

Problem: Results still not local
Fix: Check logs - if you see "WITHOUT location context", the location wasn't set
      Try clicking "Get Location" button first

Problem: Server not accessible
Fix: Check firewall: ufw allow 5001/tcp

EOF

echo ""
echo "✅ Deployment package created in: location_fix_deployment/"
echo ""
echo "📋 Next Steps:"
echo "   1. Review DEPLOY_INSTRUCTIONS.txt"
echo "   2. Upload files to production server using SCP"
echo "   3. Restart the Flask application"
echo "   4. Test the location-based search"
echo ""
echo "🚀 Quick Deploy Commands:"
echo "   scp templates/google.html root@64.23.234.72:/var/www/navigation2/templates/"
echo "   scp services/google_places_service.py root@64.23.234.72:/var/www/navigation2/services/"
echo ""


