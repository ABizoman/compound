#!/usr/bin/env python3
"""
Test script to manually check Alpha Vantage API status and rate limits.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

def test_alpha_vantage():
    """Test Alpha Vantage API to check for rate limiting."""
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    print("=" * 70)
    print("ALPHA VANTAGE API TEST")
    print("=" * 70)
    print()
    
    # Check if API key exists
    if not api_key:
        print("❌ ERROR: ALPHA_VANTAGE_API_KEY not found in environment")
        print("   Please add it to your .env file:")
        print("   ALPHA_VANTAGE_API_KEY=your_key_here")
        return
    
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Test 1: Basic API call
    print("-" * 70)
    print("TEST 1: Basic News Sentiment API Call (AAPL)")
    print("-" * 70)
    
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": "AAPL",
        "apikey": api_key,
        "limit": 5
    }
    

    print(f"Making request to: {url}")
    print(f"Parameters: {json.dumps({k: v for k, v in params.items() if k != 'apikey'}, indent=2)}")
    print()
    
    response = requests.get(url, params=params, timeout=10)
    print(f"Response Status Code: {response.status_code}")
    print()
    
    data = response.json()
    
    # Pretty print the response
    print("Response Data:")
    print(json.dumps(data, indent=2)[:1000])  # First 1000 chars

if __name__ == "__main__":
    test_alpha_vantage()
