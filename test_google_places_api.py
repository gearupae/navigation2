#!/usr/bin/env python3
"""
Test script to verify Google Places API key is enabled and working
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv('GOOGLE_MAPS_API_KEY')

if not api_key:
    print("❌ ERROR: GOOGLE_MAPS_API_KEY not found in .env file!")
    sys.exit(1)

print("=" * 60)
print("🔍 Testing Google Places API Key")
print("=" * 60)
print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
print()

# Test 1: Text Search (Places API)
print("📋 Test 1: Places API Text Search")
print("-" * 60)
url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
params = {
    'query': 'restaurant near Abu Dhabi',
    'key': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    status = data.get('status')
    
    if status == 'OK':
        results = data.get('results', [])
        print(f"✅ SUCCESS! Places API is ENABLED and working!")
        print(f"   Found {len(results)} results")
        if results:
            print(f"   First result: {results[0].get('name', 'N/A')}")
    elif status == 'REQUEST_DENIED':
        error_message = data.get('error_message', 'No error message')
        print(f"❌ REQUEST DENIED: {error_message}")
        if 'API key not valid' in error_message:
            print("   → Your API key is INVALID or REVOKED")
        elif 'This API project is not authorized' in error_message:
            print("   → Places API is NOT ENABLED in your Google Cloud project")
            print("   → Enable it at: https://console.cloud.google.com/apis/library/places-backend.googleapis.com")
        elif 'billing' in error_message.lower() or 'quota' in error_message.lower():
            print("   → Billing not enabled or quota exceeded")
    elif status == 'ZERO_RESULTS':
        print(f"✅ API is working (but no results found)")
    else:
        error_message = data.get('error_message', 'Unknown error')
        print(f"❌ Status: {status}")
        print(f"   Error: {error_message}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 2: Place Details (Places API)
print("📋 Test 2: Places API Place Details")
print("-" * 60)
# Use a well-known place ID for testing
place_id = "ChIJP3Sa8ziYEmsRUKgyFmh9AQM"  # Google Sydney
url = "https://maps.googleapis.com/maps/api/place/details/json"
params = {
    'place_id': place_id,
    'key': api_key,
    'fields': 'name,formatted_address'
}

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    status = data.get('status')
    
    if status == 'OK':
        result = data.get('result', {})
        print(f"✅ SUCCESS! Place Details API is working!")
        print(f"   Place: {result.get('name', 'N/A')}")
        print(f"   Address: {result.get('formatted_address', 'N/A')[:60]}...")
    elif status == 'REQUEST_DENIED':
        error_message = data.get('error_message', 'No error message')
        print(f"❌ REQUEST DENIED: {error_message}")
    else:
        error_message = data.get('error_message', 'Unknown error')
        print(f"❌ Status: {status} - {error_message}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print("📚 To Enable Places API:")
print("   1. Go to: https://console.cloud.google.com/apis/library")
print("   2. Search for 'Places API'")
print("   3. Click 'Enable'")
print("   4. Also enable 'Places API (New)' if available")
print("=" * 60)


