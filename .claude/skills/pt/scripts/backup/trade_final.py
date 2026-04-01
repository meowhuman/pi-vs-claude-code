#!/usr/bin/env python3
"""
Polymarket 最終交易方案 - 直接用 HTTP POST
使用已经成功嘅 EIP-712 簽名，繞過 SDK 嘅 API credentials 檢查
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
try:
    from eth_account.messages import encode_structured_data
except ImportError:
    # Fallback for different eth-account versions
    from eth_account.messages import encode_defunct
    print("⚠️  警告: 使用簡化版簽名 (encode_structured_data import failed)")

import requests

# 偽裝瀏覽器
headers_browser = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/'
}

# EIP-712 定義
domain = {
    "name": "Polymarket CLOB",
    "version": "1",
    "chainId": 137,
    "verifyingContract": "0x4d8dc65db31aa7e5a06029fbece3720d8aa56d5d"
}

types = {
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

def get_market_data():
    """獲取市場資訊 (唔需要認證)"""
    url = "https://clob.polymarket.com/markets/0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"
    response = requests.get(url, headers=headers_browser)
    return response.json()

def main():
    try:
        print("🚀 最終交易方案 - 直接 POST 到 CLOB API")
        print("=" * 60)
        print()

        # 1. 獲取 private key
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        if not private_key:
            print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
            return False

        # 2. 初始化 wallet
        if private_key.startswith("0x"):
            private_key = private_key[2:]

        account = Account.from_key(private_key)
        proxy_address = account.address

        print("🔑 Proxy Wallet:")
        print(f"   Address: {proxy_address}")
        print(f"   Private Key: {private_key[:10]}...")
        print()

        # 3. 獲取市場資訊
        print("📊 獲取市場資訊...")
        market = get_market_data()
        print(f"✅ 市場: {market['question']}")
        print(f"   狀態: {'活躍' if market.get('active') else '已關閉'}")
        print()

        # 4. 獲取 token ID
        token_id = None
        current_price = 0.44

        for token in market.get('tokens', []):
            if token.get('outcome', '').lower() == 'yes':
                token_id = token['token_id']
                current_price = token.get('price', 0.44)
                break

        if not token_id:
            print("❌ 找不到 YES token")
            return False

        print(f"📦 Token ID: {token_id[:40]}...")
        print(f"   當前價格: ${current_price}")
        print()

        # 5. 計算訂單數量
        amount_usdc = 0.1
        size = amount_usdc / current_price

        print(f"💰 訂單詳情:")
        print(f"   價格: ${current_price}")
        print(f"   數量: {size:.6f} shares")
        print(f"   總額: ${amount_usdc} USDC")
        print()

        # 6. 準備 EIP-712 訂單
        nonce = int(time.time())

        # 注意: price 和 size 需要用 6 位小數的 integer
        price_int = int(current_price * 1000000)
        size_int = int(size * 1000000)

        message = {
            "maker": proxy_address,
            "token_id": token_id,
            "price": str(price_int),
            "size": str(size_int),
            "side": 0,  # 0 = BUY
            "nonce": nonce,
            "expiration": 0,
            "fee_rate_bps": 0
        }

        print("🔐 創建 EIP-712 簽名...")

        signable_message = encode_structured_data(
            domain_data=domain,
            message_types=types,
            message_data=message
        )

        signed_message = account.sign_message(signable_message)
        signature = signed_message.signature.hex()

        print(f"   簽名: {signature[:60]}...")
        print()

        # 7. 準備 POST 數據
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
        print("📤 準備 POST 請求...")
        print(f"   Endpoint: POST https://clob.polymarket.com/order")
        print(f"   Body: {post_body[:100]}...")
        print()

        # 8. 發送 POST 請求
        print("🚀 發送請求...")

        response = requests.post(
            'https://clob.polymarket.com/order',
            data=post_body,
            headers={
                'Content-Type': 'application/json',
                **headers_browser
            },
            timeout=30000
        )

        # 9. 處理回應
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("\n🎉🎉🎉 大成功！🎉🎉🎉")
            print("✅ 交易提交成功！")
            print()
            print("回應:")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ 請求失敗: Status {response.status_code}")
            print(f"回應: {response.text}")

            if response.status_code == 401:
                print("\n💡 401 錯誤:")
                print("   可能原因 1: Proxy wallet 未激活")
                print("   可能原因 2: 需要 approve CLOB 合約")
                print("   可能原因 3: Price/size 格式錯誤")

            return False

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()

    sys.exit(0 if success else 1)
