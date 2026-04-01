#!/usr/bin/env python3
"""
Test curl_cffi with Polymarket API
"""
import json
from curl_cffi import requests

def test_polymarket_api():
    """Test direct API access with curl_cffi"""

    # Create session that impersonates Chrome 110+
    session = requests.Session(
        impersonate="chrome110",
        default_headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    market_id = "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"

    print(f"🔍 Testing Polymarket API with curl_cffi...")
    print(f"   Market ID: {market_id}")

    try:
        response = session.get(f"https://clob.polymarket.com/markets/{market_id}")

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = json.loads(response.text)
            print(f"✅ Success!")
            print(f"   Market: {data.get('question', 'Unknown')}")
            print(f"   Status: {'Open' if data.get('active') and not data.get('closed') else 'Closed'}")

            tokens = data.get('tokens', [])
            print(f"   Tokens: {len(tokens)}")

            for token in tokens:
                print(f"     - {token.get('outcome')}: ${token.get('price', 0)}")

            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_polymarket_api()