#!/usr/bin/env python3
"""
Final attempt - Pure Python EIP-712 signing + Direct POST
Using eth_account for proper structured data signing
"""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from eth_account import Account
from eth_account.messages import encode_structured_data
import requests

# CLOB API endpoint
CLOB_API = "https://clob.polymarket.com"

# Browser headers for Cloudflare bypass
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9'
}

def get_market():
    """Get market data (no auth required)"""
    url = f"{CLOB_API}/markets/0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"
    response = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    return response.json()

def main():
    try:
        print("=" * 70)
        print("FINAL ATTEMPT - Direct EIP-712 + HTTP POST")
        print("=" * 70)
        print()

        # 1. Load private key
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        if not private_key:
            print("❌ Missing POLYGON_PRIVATE_KEY")
            return False

        if private_key.startswith("0x"):
            private_key = private_key[2:]

        account = Account.from_key(private_key)
        proxy_address = account.address

        print("🔑 Wallet Setup:")
        print(f"   Address: {proxy_address}")
        print(f"   Private: {private_key[:10]}...{private_key[-8:]}")
        print()

        # 2. Get market data
        print("📊 Fetching market data...")
        market = get_market()
        print(f"✅ Market: {market['question'][:50]}...")
        print(f"   Active: {market.get('active', False)}")
        print()

        # 3. Get token and price
        token_id = None
        current_price = 0.44

        for token in market.get('tokens', []):
            if token.get('outcome', '').lower() == 'yes':
                token_id = token['token_id']
                current_price = float(token.get('price', 0.44))
                break

        if not token_id:
            print("❌ YES token not found")
            return False

        print(f"📦 Token Details:")
        print(f"   Token ID: {token_id[:50]}...")
        print(f"   Current Price: ${current_price}")
        print()

        # 4. Calculate order
        amount_usdc = 0.1
        size = amount_usdc / current_price

        print(f"💰 Order Details:")
        print(f"   Price: ${current_price}")
        print(f"   Size: {size:.6f} shares")
        print(f"   Total: ${amount_usdc} USDC")
        print()

        # 5. Prepare EIP-712 data
        nonce = int(time.time())
        price_int = int(current_price * 1000000)  # 6 decimals
        size_int = int(size * 1000000)

        print("🔐 Creating EIP-712 signature...")
        print(f"   Nonce: {nonce}")
        print(f"   Price (int): {price_int}")
        print(f"   Size (int): {size_int}")

        # EIP-712 Domain and types
        domain_data = {
            "name": "Polymarket CLOB",
            "version": "1",
            "chainId": 137,
            "verifyingContract": "0x4d8dc65db31aa7e5a06029fbece3720d8aa56d5d"
        }

        message_types = {
            "Order": [
                {"name": "maker", "type": "address"},
                {"name": "token_id", "type": "uint256"},
                {"name": "price", "type": "uint256"},
                {"name": "size", "type": "uint256"},
                {"name": "side", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiration", "type": "uint256"},
                {"name": "fee_rate_bps", "type": "uint256"}
            ]
        }

        message_data = {
            "maker": proxy_address,
            "token_id": token_id,
            "price": str(price_int),
            "size": str(size_int),
            "side": 0,  # BUY
            "nonce": nonce,
            "expiration": 0,
            "fee_rate_bps": 0
        }

        # Create and sign EIP-712 message
        signable_message = encode_structured_data(
            domain_data=domain_data,
            message_types=message_types,
            message_data=message_data
        )

        signed_message = account.sign_message(signable_message)
        signature = signed_message.signature.hex()

        print(f"   Signature: {signature[:60]}...")
        print()

        # 6. Prepare POST data
        order_payload = {
            "maker": proxy_address,
            "token_id": token_id,
            "price": str(price_int),
            "size": str(size_int),
            "side": 0,
            "nonce": str(nonce),
            "expiration": "0",
            "fee_rate_bps": "0",
            "signature": signature,
            "signature_type": 0
        }

        post_body = json.dumps(order_payload)

        print("📤 Preparing POST request...")
        print(f"   URL: POST {CLOB_API}/order")
        print(f"   Body (first 100 chars): {post_body[:100]}...")
        print()

        # 7. Send POST request
        print("🚀 Sending POST request...")

        response = requests.post(
            f"{CLOB_API}/order",
            data=post_body,
            headers={
                'Content-Type': 'application/json',
                **BROWSER_HEADERS
            },
            timeout=30
        )

        # 8. Process response
        print(f"\n📨 Response Status: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            print("\n🎉🎉🎉 SUCCESS! 🎉🎉🎉")
            print("✅ Trade submitted successfully!")
            print()
            print("Response:")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ FAILED")
            print(f"Response: {response.text[:200]}...")

            if response.status_code == 401:
                print("\n💡 401 Unauthorized:")
                print("   - Builder API keys may not be activated")
                print("   - May need to approve CLOB contract")
                print("   - May need USDC in proxy wallet")
            elif response.status_code == 403:
                print("\n💡 403 Blocked - Cloudflare")
                print("   - Try different VPN location")
            elif response.status_code == 400:
                print("\n💡 400 Bad Request - Data format error")

            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()

    sys.exit(0 if success else 1)
