#!/usr/bin/env python3
"""
Trade via Builder Signing Server - Final solution!
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv
import requests

load_dotenv()

class PolymarketTradeViaServer:
    def __init__(self):
        self.server_url = "http://localhost:5001"
        self.private_key = os.getenv("POLYGON_PRIVATE_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")

        if not self.private_key or not self.wallet_address:
            raise ValueError("Missing required environment variables")

    def get_market_data(self, market_id: str):
        """Get market data using regular requests"""
        try:
            response = requests.get(f"https://clob.polymarket.com/markets/{market_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error getting market: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting market: {e}")
            return None

    def trade_via_server(self, market_id: str, side: str, amount: float, auto_confirm: bool = False):
        """Trade through Builder Signing Server"""
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
        current_price = None

        for token in tokens:
            if token.get('outcome', '').lower() == side.lower():
                token_id = token.get('token_id')
                current_price = token.get('price', 0.5)
                break

        if not token_id:
            print(f"❌ Outcome '{side}' not found in market")
            print(f"Available outcomes: {[t.get('outcome') for t in tokens]}")
            return False

        if current_price is None:
            current_price = 0.5

        # 3. Calculate trade details
        execution_price = min(current_price * 1.05, 0.99)
        size = round(amount / execution_price, 2)

        if size < 0.1:
            print(f"❌ Calculated size too small: {size} (must be >= 0.1)")
            return False

        # 4. Prepare trade request
        trade_data = {
            "market_id": market_id,
            "side": side.upper(),
            "amount": amount,
            "token_id": token_id,
            "price": execution_price
        }

        print(f"\n📝 Trade Summary:")
        print(f"   Market: {market.get('question', 'Unknown')}")
        print(f"   Side: {side.upper()}")
        print(f"   Amount: ${amount} USDC")
        print(f"   Price: ${execution_price} (Current: ${current_price})")
        print(f"   Size: {size} shares")
        print(f"   Token ID: {token_id[:20]}...")

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

        # 5. Submit trade via server
        print(f"\n🚀 Submitting trade via Builder Server...")
        print(f"   Server URL: {self.server_url}/trade")

        try:
            response = requests.post(
                f"{self.server_url}/trade",
                headers={"Content-Type": "application/json"},
                json=trade_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    order = result.get('order', {})
                    print(f"✅ Trade executed successfully!")
                    print(f"   Order ID: {order.get('orderID', 'N/A')}")
                    print(f"   Status: {order.get('status', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Server error: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Network error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Trade via Builder Signing Server")
    parser.add_argument("--market-id", required=True, help="Market Condition ID")
    parser.add_argument("--side", required=True, help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in USDC")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    trader = PolymarketTradeViaServer()

    print(f"🎯 Trading via Builder Signing Server!")
    print(f"   Server: {trader.server_url}")
    print(f"   Wallet: {trader.wallet_address}")
    print(f"   Amount: ${args.amount} USDC")

    success = trader.trade_via_server(
        args.market_id,
        args.side,
        args.amount,
        args.auto_confirm
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()