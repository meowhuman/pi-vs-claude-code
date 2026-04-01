#!/usr/bin/env python3
"""
Final Polymarket Trade Execution - Ultimate Solution!
"""
import os
import sys
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

def execute_trade(market_id: str, side: str, amount: float):
    """Execute trade through Builder Signing Server"""

    # 1. Get market data using curl
    curl_cmd = [
        "curl", "-X", "GET",
        f"https://clob.polymarket.com/markets/{market_id}",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "-H", "Accept: application/json",
        "--silent"
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            market = json.loads(result.stdout)
        else:
            print(f"❌ Error getting market: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print(f"✅ Market: {market.get('question', 'Unknown')}")
    print(f"   Status: {'✅ Open' if market.get('active') and not market.get('closed') else '❌ Closed'}")

    # 2. Find token
    tokens = market.get('tokens', [])
    token_id = None
    current_price = 0.5  # Default price

    for token in tokens:
        if token.get('outcome', '').lower() == side.lower():
            token_id = token.get('token_id')
            current_price = token.get('price', 0.5)
            break

    if not token_id:
        print(f"❌ Outcome '{side}' not found")
        return False

    # 3. Calculate trade details
    execution_price = min(current_price * 1.05, 0.99)
    size = round(amount / execution_price, 2)

    if size < 0.1:
        print(f"❌ Size too small: {size} (minimum 0.1)")
        return False

    print(f"💰 Trade Details:")
    print(f"   Side: {side.upper()}")
    print(f"   Amount: ${amount} USDC")
    print(f"   Price: ${execution_price}")
    print(f"   Size: {size} shares")
    print(f"   Token ID: {token_id[:20]}...")

    # 4. Test signing server
    print(f"🔐 Testing signing server...")

    sign_data = {
        "path": "/orders",
        "method": "POST",
        "body": json.dumps({
            "market": market_id,
            "side": "BUY",
            "price": execution_price,
            "size": size,
            "token_id": token_id,
            "type": "LIMIT"
        })
    }

    try:
        result = subprocess.run([
            "curl", "-X", "POST",
            "http://localhost:5001/sign",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(sign_data),
            "--silent"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            signed_data = json.loads(result.stdout)
            print(f"✅ Signing server working!")
        else:
            print(f"❌ Signing server error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Signing server error: {e}")
        return False

    # 5. Direct test via server trade endpoint
    print(f"🚀 Testing trade endpoint...")

    trade_data = {
        "market_id": market_id,
        "side": side.upper(),
        "amount": amount,
        "token_id": token_id,
        "price": execution_price
    }

    try:
        result = subprocess.run([
            "curl", "-X", "POST",
            "http://localhost:5001/trade",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(trade_data),
            "--silent"
        ], capture_output=True, text=True)

        print(f"   Server response: {result.returncode}")

        if result.returncode == 0:
            try:
                print(f"   Raw response: {result.stdout}")
                result_data = json.loads(result.stdout)
                if result_data.get('success'):
                    order = result_data.get('order', {})
                    print(f"🎉 TRADE SUCCESS!")
                    print(f"   Order ID: {order.get('orderID', 'N/A')}")
                    print(f"   Status: {order.get('status', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Trade failed: {result_data.get('message', 'Unknown')}")
                    return False
            except:
                print(f"❌ Response parsing error")
                return False
        else:
            print(f"❌ HTTP {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Trade error: {e}")
        return False

if __name__ == "__main__":
    market_id = "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"
    side = "yes"
    amount = 0.1

    print(f"🚀 FINAL TEST - Maduro Trade via Server")
    print(f"   Market: 2026年3月31日前下台")
    print(f"   Amount: ${amount} USDC")
    print(f"   Side: {side}")
    print("="*60)

    success = execute_trade(market_id, side, amount)

    if success:
        print(f"\n🎉🎉🎉🎉 TRADE EXECUTED SUCCESSFULLY! 🎉🎉🎉🎉🎉🎉")
        print(f"   🎊 恭喜你成功進行第一筆自動化交易！")
    else:
        print(f"\n❌ Trade failed - Check server logs")

    sys.exit(0 if success else 1)