#!/bin/bash

# Production Deployment Script for Navigation2
# This script securely uploads all changes to the production server

echo "=== Navigation2 Production Deployment ==="
echo ""

# Server details
SERVER="root@64.23.234.72"
SERVER_PATH="/root/navigation2"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the navigation2 directory."
    exit 1
fi

echo "Current directory: $(pwd)"
echo "Target server: $SERVER"
echo "Target path: $SERVER_PATH"
echo ""

# Create a temporary deployment directory
echo "Preparing deployment files..."
mkdir -p temp_deployment

# Copy all necessary files
cp app.py temp_deployment/
cp -r templates temp_deployment/
cp -r services temp_deployment/
cp .env temp_deployment/
cp requirements.txt temp_deployment/ 2>/dev/null || echo "requirements.txt not found, skipping"

# Create deployment info
cat > temp_deployment/DEPLOYMENT_INFO.txt << EOF
Deployment Date: $(date)
Deployment Source: $(pwd)
Key Changes:
- Enhanced unified instruction system with LLM integration
- Fixed frontend JavaScript DOM handling
- Added Arabic street name translation
- Improved route display and debugging
- Enhanced Google Places search functionality
EOF

echo "Files prepared for deployment:"
ls -la temp_deployment/
echo ""

# Test SSH connection
echo "Testing SSH connection..."
if ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER "echo 'SSH connection successful'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed. Please check:"
    echo "1. Server IP and credentials are correct"
    echo "2. SSH key is properly configured"
    echo "3. Server is accessible"
    exit 1
fi

# Create backup on server
echo "Creating backup on production server..."
ssh $SERVER "cd $SERVER_PATH && cp -r . ../navigation2_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'No existing backup needed'"

# Upload files
echo "Uploading files to production server..."
rsync -avz --progress temp_deployment/ $SERVER:$SERVER_PATH/

# Set proper permissions
echo "Setting permissions..."
ssh $SERVER "cd $SERVER_PATH && chmod +x *.sh 2>/dev/null || true"

# Install/update dependencies
echo "Installing dependencies..."
ssh $SERVER "cd $SERVER_PATH && pip install -r requirements.txt 2>/dev/null || echo 'requirements.txt not found, skipping pip install'"

# Restart services (adjust based on your production setup)
echo "Restarting services..."
ssh $SERVER "cd $SERVER_PATH && pkill -f 'python app.py' 2>/dev/null || true"
ssh $SERVER "cd $SERVER_PATH && nohup python app.py runserver 5001 > app.log 2>&1 &"

# Cleanup
echo "Cleaning up temporary files..."
rm -rf temp_deployment

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Check server logs: ssh $SERVER 'cd $SERVER_PATH && tail -f app.log'"
echo "2. Test the application: http://64.23.234.72:5001"
echo "3. Verify unified instruction endpoint is working"
echo ""
echo "To monitor the deployment:"
echo "ssh $SERVER 'cd $SERVER_PATH && tail -f app.log'"


