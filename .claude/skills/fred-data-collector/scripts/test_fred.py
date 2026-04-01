#!/usr/bin/env python3
"""
Test FRED API connectivity and credentials
"""

import os
import sys

# Check current working directory first
cwd = os.getcwd()
cwd_env = os.path.join(cwd, '.env')

if os.path.exists(cwd_env):
    env_file = cwd_env
else:
    # Fall back to relative path
    env_file = os.path.join(cwd, '.env')

print(f"Looking for .env file at: {env_file}")

if os.path.exists(env_file):
    print(f"✓ Found .env file")
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    os.environ[key] = value
                    if key == 'FRED_API_KEY':
                        print(f"  ✓ Loaded {key}")
    except Exception as e:
        print(f"Note: Could not load .env file: {e}")
else:
    print(f"✗ .env file not found at {env_file}")
    print(f"  Current directory: {cwd}")

from fredapi import Fred

def test_fred_connection():
    """Test FRED API connection with user's API key"""
    api_key = os.getenv('FRED_API_KEY')

    if not api_key:
        print("❌ Error: FRED_API_KEY not found in environment")
        print("\nTo fix this:")
        print("1. Copy .env.sample to .env:")
        print("   cp .claude/skills/fred-data-collector/.env.sample .env")
        print("\n2. Edit .env and add your key:")
        print("   FRED_API_KEY=your_api_key_here")
        print("\n3. Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return False

    print(f"✓ API Key found: {api_key[:8]}...")

    try:
        # Initialize FRED
        fred = Fred(api_key=api_key)

        # Test with a simple series (GDP)
        print("\n→ Testing API connection with GDP series...")
        gdp = fred.get_series('GDP', limit=5)

        if not gdp.empty:
            print("✅ Success! API connection working")
            print(f"✅ Retrieved {len(gdp)} GDP data points")
            print(f"✅ Latest GDP: {gdp.iloc[-1]:,.2f} Billion (as of {gdp.index[-1].strftime('%Y-%m-%d')})")

            # Test another common series
            print("\n→ Testing with unemployment rate...")
            unrate = fred.get_series('UNRATE', limit=3)
            print(f"✅ Latest unemployment rate: {unrate.iloc[-1]}% (as of {unrate.index[-1].strftime('%Y-%m-%d')})")

            print("\n" + "="*60)
            print("🎉 All tests passed! Your FRED API is working correctly.")
            print("="*60)
            print("\nNext steps:")
            print("1. Run the collector:")
            print("   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py")
            print("\n2. Or use interactive mode:")
            print("   python3 .claude/skills/fred-data-collector/scripts/collect_fred.py --status")

            return True
        else:
            print("❌ Error: No data returned from API")
            return False

    except Exception as e:
        print(f"\n❌ API Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your API key at https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Check your internet connection")
        print("3. Ensure you haven't exceeded rate limits (120 requests/hour)")
        return False

if __name__ == "__main__":
    print("Testing FRED API Connection")
    print("="*60)
    success = test_fred_connection()
    sys.exit(0 if success else 1)
