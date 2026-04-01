#!/usr/bin/env python3
"""
Execute Polymarket trades using Builder Signing Server
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv
import requests
from web3 import Web3

load_dotenv()

class PolymarketTradeWithSigner:
    def __init__(self):
        self.signer_url = "http://localhost:5001"
        self.clob_host = "https://clob.polymarket.com"
        self.private_key = os.getenv("POLYGON_PRIVATE_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")

        if not self.private_key or not self.wallet_address:
            raise ValueError("Missing required environment variables")

    def get_market_detail(self, market_id: str):
        """Get market details from CLOB API"""
        try:
            response = requests.get(f"{self.clob_host}/markets/{market_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error getting market: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting market: {e}")
            return None

    def get_orderbook(self, token_id: str):
        """Get orderbook for token"""
        try:
            response = requests.get(f"{self.clob_host}/orderbook/{token_id}")
            if response.status_code == 200:
                return response.json()
            else:
                # Try with condition_id as fallback
                print(f"⚠️  Token ID not found, trying market orderbook...")
                return None
        except Exception as e:
            print(f"❌ Error getting orderbook: {e}")
            return None

    def get_market_orderbook(self, market_id: str):
        """Get market orderbook"""
        try:
            response = requests.get(f"{self.clob_host}/orderbook/{market_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error getting market orderbook: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting market orderbook: {e}")
            return None

    def get_signed_headers(self, path: str, method: str, body: str) -> dict:
        """Get signed headers from signing server"""
        try:
            sign_request = {
                "path": path,
                "method": method,
                "body": body
            }

            response = requests.post(
                f"{self.signer_url}/sign",
                headers={"Content-Type": "application/json"},
                json=sign_request,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Signing server error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error communicating with signing server: {e}")
            return None

    def create_order(self, market_id: str, side: str, amount: float, auto_confirm: bool = False):
        """Create and post order using signing server"""
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

        # 3. Get orderbook to determine price
        print(f"📊 Fetching orderbook...")
        orderbook = self.get_orderbook(token_id)

        if not orderbook:
            # Try market orderbook
            print(f"⚠️  Token orderbook not available, using market orderbook")
            orderbook = self.get_market_orderbook(market_id)

        if not orderbook:
            # Fallback to fixed price
            print(f"⚠️  No orderbook data, using fixed price $0.50")
            best_price = 0.50
        else:
            # Get best ask price
            asks = orderbook.get('asks', [])
            if asks:
                best_price = float(asks[0]['price'])
                print(f"💰 Best Ask Price: ${best_price}")
            else:
                print(f"⚠️  No asks in orderbook, using fixed price $0.50")
                best_price = 0.50

        # 4. Calculate order details
        execution_price = min(best_price * 1.05, 0.99)  # 5% slippage, max 0.99
        size = round(amount / execution_price, 2)

        if size < 0.1:
            print(f"❌ Calculated size too small: {size} (must be >= 0.1)")
            return False

        # 5. Prepare order
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

        # 6. Create signed order
        print(f"\n🔐 Creating signed order...")

        order_body = json.dumps(order_data)
        signed_headers = self.get_signed_headers("/orders", "POST", order_body)

        if not signed_headers:
            print("❌ Failed to get signed headers")
            return False

        # 7. Submit order
        print(f"📤 Submitting order...")

        headers = {
            "Content-Type": "application/json",
            "poly-signature": signed_headers.get("signature", ""),
            "poly-builder-api-key": signed_headers.get("builderApiKeyId", ""),
            "poly-timestamp": str(signed_headers.get("timestamp", "")),
            "poly-address": self.wallet_address
        }

        response = requests.post(
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
            print(f"   Error: {response.text}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Execute Polymarket trade with signing server")
    parser.add_argument("--market-id", required=True, help="Market Condition ID")
    parser.add_argument("--side", required=True, help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in USDC")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    trader = PolymarketTradeWithSigner()
    success = trader.create_order(
        args.market_id,
        args.side,
        args.amount,
        args.auto_confirm
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()