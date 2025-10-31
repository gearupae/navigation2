#!/bin/bash

# Manual Deployment Script for Navigation2
# This script prepares files for manual upload to production server

echo "=== Navigation2 Manual Deployment Preparation ==="
echo ""

# Create deployment package
echo "Creating deployment package..."
rm -rf production_deployment
mkdir -p production_deployment

# Copy all necessary files
echo "Copying files..."
cp app.py production_deployment/
cp -r templates production_deployment/
cp -r services production_deployment/
cp .env production_deployment/
cp requirements.txt production_deployment/ 2>/dev/null || echo "requirements.txt not found, skipping"

# Create deployment instructions
cat > production_deployment/DEPLOYMENT_INSTRUCTIONS.md << 'EOF'
# Production Deployment Instructions

## Files to Upload
1. app.py - Main Flask application with unified instruction logic
2. templates/ - Updated HTML files with fixed JavaScript
3. services/ - New and enhanced service files
4. .env - Updated environment variables
5. requirements.txt - Python dependencies

## Deployment Steps

### 1. Connect to Server
```bash
ssh root@64.23.234.72
# Use password: kuyi*&^HJjj666H
```

### 2. Navigate to Application Directory
```bash
cd /root/navigation2
```

### 3. Create Backup
```bash
cp -r . ../navigation2_backup_$(date +%Y%m%d_%H%M%S)
```

### 4. Stop Current Application
```bash
pkill -f "python app.py"
```

### 5. Upload Files
Upload the following files from this deployment package:
- app.py
- templates/ (entire directory)
- services/ (entire directory)
- .env
- requirements.txt

### 6. Install Dependencies
```bash
pip install -r requirements.txt
```

### 7. Start Application
```bash
nohup python app.py runserver 5001 > app.log 2>&1 &
```

### 8. Verify Deployment
```bash
# Check if application is running
ps aux | grep "python app.py"

# Check logs
tail -f app.log

# Test endpoint
curl -s "http://localhost:5001/api/navigation/unified-instruction" | head -20
```

## Key Changes Deployed
- Enhanced unified instruction system with LLM integration
- Fixed frontend JavaScript DOM handling
- Added Arabic street name translation for TTS
- Improved route display and debugging
- Enhanced Google Places search functionality
- Only mentions signs when they are actually present

## Environment Variables
Make sure these are set in .env:
- GROK_API_KEY=your_grok_api_key
- XAI_API_KEY=your_xai_api_key
- GROK_TEXT_MODEL=grok-2-latest
EOF

echo "Deployment package created in: production_deployment/"
echo ""
echo "Files ready for upload:"
ls -la production_deployment/
echo ""
echo "📋 Manual Upload Instructions:"
echo "1. Connect to server: ssh root@64.23.234.72"
echo "2. Password: kuyi*&^HJjj666H"
echo "3. Navigate to: cd /root/navigation2"
echo "4. Upload files from production_deployment/ directory"
echo "5. Follow instructions in DEPLOYMENT_INSTRUCTIONS.md"
echo ""
echo "🚀 Quick Upload Commands:"
echo "scp -r production_deployment/* root@64.23.234.72:/root/navigation2/"
echo ""
echo "📁 Deployment package location: $(pwd)/production_deployment/"


