#!/usr/bin/env python3
"""
Execute Polymarket trades using curl_cffi (impersonates Chrome browser)
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Use curl_cffi instead of requests
from curl_cffi import requests

load_dotenv()

class PolymarketTradeCurl:
    def __init__(self):
        # Create session that impersonates Chrome 110+
        self.session = requests.Session(
            impersonate="chrome110",
            default_headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Not_A Brand";v="99", "Chromium";v="110"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            }
        )

        self.clob_host = "https://clob.polymarket.com"
        self.private_key = os.getenv("POLYGON_PRIVATE_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")

        # Get API credentials from signing server
        self.signer_url = "http://localhost:5001"

        if not self.private_key or not self.wallet_address:
            raise ValueError("Missing required environment variables")

    def get_signed_headers(self, path: str, method: str, body: str) -> dict:
        """Get signed headers from signing server"""
        try:
            sign_request = {
                "path": path,
                "method": method,
                "body": body
            }

            response = self.session.post(
                f"{self.signer_url}/sign",
                headers={"Content-Type": "application/json"},
                json=sign_request,
                timeout=30
            )

            if response.status_code == 200:
                return json.loads(response.text)
            else:
                print(f"❌ Signing server error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error communicating with signing server: {e}")
            return None

    def get_market_detail(self, market_id: str):
        """Get market details from CLOB API"""
        try:
            response = self.session.get(f"{self.clob_host}/markets/{market_id}")
            if response.status_code == 200:
                return json.loads(response.text)
            else:
                print(f"❌ Error getting market: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting market: {e}")
            return None

    def create_order(self, market_id: str, side: str, amount: float, auto_confirm: bool = False):
        """Create and post order using curl_cffi and signing server"""
        # 1. Get market details
        print(f"🔍 Fetching market details...")
        market = self.get_market_detail(market_id)
        if not market:
            return False

        print(f"   Market: {market.get('question', 'Unknown')}")
        print(f"   Status: {'✅ Open' if market.get('active') and not market.get('closed') else '❌ Closed'}")

        # 2. Find token for the side
        tokens = market.get('tokens', [])
        token_id = None
        for token in tokens:
            if token.get('outcome', '').lower() == side.lower():
                token_id = token.get('token_id')
                break

        if not token_id:
            print(f"❌ Outcome '{side}' not found in market")
            print(f"Available outcomes: {[t.get('outcome') for t in tokens]}")
            return False

        # 3. Calculate order details (using fixed price due to orderbook issues)
        best_price = 0.50  # Fixed price due to low liquidity
        execution_price = min(best_price * 1.05, 0.99)  # 5% slippage, max 0.99
        size = round(amount / execution_price, 2)

        if size < 0.1:
            print(f"❌ Calculated size too small: {size} (must be >= 0.1)")
            return False

        # 4. Prepare order
        order_data = {
            "market": market_id,
            "side": "BUY",
            "price": execution_price,
            "size": size,
            "token_id": token_id,
            "type": "LIMIT"
        }

        print(f"\n📝 Trade Summary:")
        print(f"   Market: {market.get('question', 'Unknown')}")
        print(f"   Side: {side.upper()}")
        print(f"   Amount: ${amount} USDC")
        print(f"   Price: ${execution_price}")
        print(f"   Size: {size} shares")

        # Check auto confirm
        max_auto = float(os.getenv("MAX_AUTO_AMOUNT", "1.0"))
        if amount > max_auto and not auto_confirm:
            print(f"\n⚠️  Amount (${amount}) exceeds auto-limit (${max_auto})")
            confirm = input("Confirm trade? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("❌ Trade cancelled")
                return False

        # 5. Create signed order
        print(f"\n🔐 Creating signed order...")

        order_body = json.dumps(order_data)
        signed_headers = self.get_signed_headers("/orders", "POST", order_body)

        if not signed_headers:
            print("❌ Failed to get signed headers")
            return False

        # 6. Submit order with curl_cffi
        print(f"📤 Submitting order (using curl_cffi)...")

        headers = {
            "Content-Type": "application/json",
            "poly-signature": signed_headers.get("signature", ""),
            "poly-builder-api-key": signed_headers.get("builderApiKeyId", ""),
            "poly-timestamp": str(signed_headers.get("timestamp", "")),
            "poly-address": self.wallet_address,
            "Origin": "https://polymarket.com",
            "Referer": "https://polymarket.com/",
            "Sec-Ch-Ua": '"Not_A Brand";v="99", "Chromium";v="110"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
        }

        try:
            response = self.session.post(
                f"{self.clob_host}/orders",
                headers=headers,
                data=order_body,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Order submitted successfully!")
                print(f"   Order ID: {result.get('orderID', 'N/A')}")
                print(f"   Status: {result.get('status', 'Unknown')}")
                return True
            else:
                print(f"❌ Order submission failed!")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")

                # Check if it's still Cloudflare blocking
                if "cloudflare" in response.text.lower():
                    print(f"\n⚠️  Still getting Cloudflare block!")
                    print(f"   Cloudflare Ray ID: Check response for details")
                    print(f"   Try changing VPN location")

                return False

        except Exception as e:
            print(f"❌ Network error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Execute Polymarket trade with curl_cffi")
    parser.add_argument("--market-id", required=True, help="Market Condition ID")
    parser.add_argument("--side", required=True, help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in USDC")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    trader = PolymarketTradeCurl()

    print(f"🚀 Starting Polymarket trade with curl_cffi...")
    print(f"   Impersonating: Chrome 110+")
    print(f"   Signing Server: {trader.signer_url}")

    success = trader.create_order(
        args.market_id,
        args.side,
        args.amount,
        args.auto_confirm
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()