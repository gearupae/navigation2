#!/bin/bash

# Navigation2 Deployment Script
# This script helps deploy changes to the main server

echo "=== Navigation2 Deployment Script ==="
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the navigation2 directory."
    exit 1
fi

echo "Current directory: $(pwd)"
echo ""

# List files that need to be deployed
echo "Files to deploy:"
echo "1. app.py (main Flask application)"
echo "2. templates/index.html (enhanced frontend)"
echo "3. templates/google.html (corrected DOM handling)"
echo "4. services/google_integrated_navigation.py (new facade service)"
echo "5. services/google_places_service.py (enhanced search)"
echo "6. .env (environment variables)"
echo ""

# Create deployment package
echo "Creating deployment package..."
mkdir -p deployment_package
cp app.py deployment_package/
cp -r templates/ deployment_package/
cp -r services/ deployment_package/
cp .env deployment_package/
cp DEPLOYMENT_CHANGES.md deployment_package/

echo "Deployment package created in 'deployment_package/' directory"
echo ""

# Show package contents
echo "Package contents:"
ls -la deployment_package/
echo ""

echo "=== Deployment Instructions ==="
echo "1. Copy the 'deployment_package' folder to your production server"
echo "2. Backup your current production files"
echo "3. Replace the files on production server with the new ones"
echo "4. Update environment variables (especially GROK_API_KEY)"
echo "5. Restart your Flask application"
echo "6. Test the unified instruction functionality"
echo ""

echo "=== Key Changes Summary ==="
echo "✅ Enhanced unified instruction system with LLM integration"
echo "✅ Fixed route display and map controls"
echo "✅ Added Arabic street name translation for TTS"
echo "✅ Improved Google Places search"
echo "✅ Conditional sign mentioning (only when signs exist)"
echo "✅ Better session management and debugging"
echo ""

echo "Deployment package ready!"
echo "Location: $(pwd)/deployment_package/"


