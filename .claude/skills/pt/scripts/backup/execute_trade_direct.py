#!/usr/bin/env python3
"""
Execute Polymarket trades using direct curl (bypassing Python JSON issues)
"""
import os
import sys
import json
import argparse
import subprocess
from dotenv import load_dotenv

load_dotenv()

class PolymarketTradeDirect:
    def __init__(self):
        self.signer_url = "http://localhost:5001"
        self.private_key = os.getenv("POLYGON_PRIVATE_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")

        if not self.private_key or not self.wallet_address:
            raise ValueError("Missing required environment variables")

    def get_signed_headers(self, path: str, method: str, body: str):
        """Get signed headers from signing server"""
        try:
            sign_request = {
                "path": path,
                "method": method,
                "body": body
            }

            # Use curl instead of requests to avoid JSON parsing issues
            curl_cmd = [
                "curl", "-X", "POST",
                f"{self.signer_url}/sign",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(sign_request),
                "--silent",
                "--connect-timeout", "30"
            ]

            result = subprocess.run(curl_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"❌ Signing server error: {result.returncode}")
                print(f"Stderr: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error communicating with signing server: {e}")
            return None

    def get_market_data(self, market_id: str):
        """Get market data using direct curl"""
        try:
            curl_cmd = [
                "curl", "-X", "GET",
                f"https://clob.polymarket.com/markets/{market_id}",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "-H", "Accept: application/json",
                "--silent",
                "--connect-timeout", "30"
            ]

            result = subprocess.run(curl_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"❌ Error getting market: {result.returncode}")
                print(f"Stderr: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error getting market: {e}")
            return None

    def submit_order(self, order_data: dict, signed_headers: dict):
        """Submit order using direct curl"""
        try:
            order_body = json.dumps(order_data)

            headers = [
                "-H", f"Content-Type: application/json",
                "-H", f"poly-signature: {signed_headers.get('signature', '')}",
                "-H", f"poly-builder-api-key: {signed_headers.get('builderApiKeyId', '')}",
                "-H", f"poly-timestamp: {signed_headers.get('timestamp', '')}",
                "-H", f"poly-address: {self.wallet_address}",
                "-H", "Origin: https://polymarket.com",
                "-H", "Referer: https://polymarket.com/",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            ]

            curl_cmd = [
                "curl", "-X", "POST",
                "https://clob.polymarket.com/orders",
                *headers,
                "-d", order_body,
                "--silent",
                "--connect-timeout", "30"
            ]

            result = subprocess.run(curl_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Try to extract error info from HTML response
                    if "cloudflare" in result.stdout.lower():
                        print(f"❌ Cloudflare still blocking")
                        # Extract Cloudflare Ray ID if available
                        import re
                        ray_match = re.search(r'Cloudflare Ray ID: <strong>([^<]+)</strong>', result.stdout)
                        if ray_match:
                            print(f"   Ray ID: {ray_match.group(1)}")
                    return None
            else:
                print(f"❌ Order submission failed!")
                print(f"   Return code: {result.returncode}")
                print(f"   Stderr: {result.stderr}")
                print(f"   Stdout: {result.stdout[:500]}...")
                return None

        except Exception as e:
            print(f"❌ Network error: {e}")
            return None

    def create_order(self, market_id: str, side: str, amount: float, auto_confirm: bool = False):
        """Create and post order"""
        # 1. Get market details
        print(f"🔍 Fetching market details...")
        market = self.get_market_data(market_id)
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

        # 3. Use current price from market data
        current_price = None
        for token in tokens:
            if token.get('outcome', '').lower() == side.lower():
                current_price = token.get('price', 0.5)
                break

        if current_price is None:
            current_price = 0.5

        execution_price = min(current_price * 1.05, 0.99)
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
        print(f"   Price: ${execution_price} (Current: ${current_price})")
        print(f"   Size: {size} shares")

        # Check auto confirm
        max_auto = float(os.getenv("MAX_AUTO_AMOUNT", "1.0"))
        if amount > max_auto and not auto_confirm:
            print(f"\n⚠️  Amount (${amount}) exceeds auto-limit (${max_auto})")
            try:
                confirm = input("Confirm trade? (yes/no): ").strip().lower()
                if confirm != "yes":
                    print("❌ Trade cancelled")
                    return False
            except:
                print("❌ No input available, cancelling")
                return False

        # 5. Create signed order
        print(f"\n🔐 Creating signed order...")

        order_body = json.dumps(order_data)
        signed_headers = self.get_signed_headers("/orders", "POST", order_body)

        if not signed_headers:
            print("❌ Failed to get signed headers")
            return False

        # 6. Submit order
        print(f"📤 Submitting order (direct curl)...")
        result = self.submit_order(order_data, signed_headers)

        if result:
            print(f"✅ Order submitted successfully!")
            print(f"   Order ID: {result.get('orderID', 'N/A')}")
            print(f"   Status: {result.get('status', 'Unknown')}")
            return True
        else:
            return False

def main():
    parser = argparse.ArgumentParser(description="Execute Polymarket trade with direct curl")
    parser.add_argument("--market-id", required=True, help="Market Condition ID")
    parser.add_argument("--side", required=True, help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in USDC")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    trader = PolymarketTradeDirect()

    print(f"🚀 Starting Polymarket trade with direct curl...")
    print(f"   Method: Direct curl with Builder signing")
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