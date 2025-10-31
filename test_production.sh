#!/bin/bash

# Test Production Deployment Script
# This script tests the deployed application on the production server

echo "=== Testing Production Deployment ==="
echo ""

PRODUCTION_URL="http://64.23.234.72:5001"

echo "🧪 Testing Production Server: $PRODUCTION_URL"
echo ""

# Test 1: Basic connectivity
echo "1. Testing basic connectivity..."
if curl -s --connect-timeout 10 "$PRODUCTION_URL" > /dev/null; then
    echo "   ✅ Server is accessible"
else
    echo "   ❌ Server is not accessible"
    exit 1
fi

# Test 2: Unified instruction endpoint
echo "2. Testing unified instruction endpoint..."
UNIFIED_RESPONSE=$(curl -s --connect-timeout 10 "$PRODUCTION_URL/api/navigation/unified-instruction" 2>/dev/null)
if [ $? -eq 0 ] && [ ! -z "$UNIFIED_RESPONSE" ]; then
    echo "   ✅ Unified instruction endpoint working"
    echo "   Response: $(echo "$UNIFIED_RESPONSE" | head -c 100)..."
else
    echo "   ❌ Unified instruction endpoint not working"
fi

# Test 3: Google navigation page
echo "3. Testing Google navigation page..."
GOOGLE_RESPONSE=$(curl -s --connect-timeout 10 "$PRODUCTION_URL/google" 2>/dev/null)
if [ $? -eq 0 ] && echo "$GOOGLE_RESPONSE" | grep -q "Google Integrated Navigation"; then
    echo "   ✅ Google navigation page accessible"
else
    echo "   ❌ Google navigation page not accessible"
fi

# Test 4: API status
echo "4. Testing API status..."
STATUS_RESPONSE=$(curl -s --connect-timeout 10 "$PRODUCTION_URL/api/status" 2>/dev/null)
if [ $? -eq 0 ] && [ ! -z "$STATUS_RESPONSE" ]; then
    echo "   ✅ API status endpoint working"
else
    echo "   ❌ API status endpoint not working"
fi

echo ""
echo "🎯 Production URLs:"
echo "   Main App: $PRODUCTION_URL"
echo "   Google Navigation: $PRODUCTION_URL/google"
echo "   API Status: $PRODUCTION_URL/api/status"
echo "   Unified Instruction: $PRODUCTION_URL/api/navigation/unified-instruction"
echo ""
echo "📱 Test the application in your browser:"
echo "   Open: $PRODUCTION_URL"
echo "   Then navigate to: $PRODUCTION_URL/google"


