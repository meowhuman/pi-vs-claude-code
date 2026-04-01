#!/usr/bin/env python3
"""
Polymarket 直接交易 - 使用 Proxy Wallet Private Key
不使用 API credentials，直接用 L1 authentication
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 從 .env 加載配置
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.constants import POLYGON

def main():
    try:
        print("🚀 POLYMARKET DIRECT TRADE VIA PROXY WALLET")
        print("=" * 50)
        print()

        # 1. 獲取 proxy wallet private key
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        if not private_key:
            print("❌ 錯誤: 在 .env 中找不到 POLYGON_PRIVATE_KEY")
            return False

        # 移除 0x prefix 如果有
        clean_key = private_key[2:] if private_key.startswith("0x") else private_key

        print(f"🔑 使用 Proxy Wallet Private Key")
        print(f"   Key (前 10 位): {clean_key[:10]}...")
        print(f"   Chain: Polygon (ID: {POLYGON})")
        print()

        # 2. 初始化 ClobClient (L1 mode - 只傳入 private key)
        print("📡 初始化 ClobClient (L1 mode)...")
        client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=POLYGON,
            key=clean_key  # 直接傳入 private key，唔需要 API credentials
        )

        print("✅ ClobClient 初始化成功")
        print()

        # 3. 獲取市場資訊
        print("📊 獲取市場資訊...")
        market_id = "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"

        market = client.get_market(market_id)
        print(f"✅ 市場: {market['question']}")
        print(f"   狀態: {'✅ 活躍' if market.get('active') else '❌ 已關閉'}")
        print()

        # 4. 創建訂單參數
        print("💰 準備訂單...")

        # 獲取 YES token ID
        token_id = None
        for token in market.get('tokens', []):
            if token.get('outcome', '').lower() == 'yes':
                token_id = token.get('token_id')
                current_price = token.get('price', 0.425)
                break

        if not token_id:
            print("❌ 找不到 YES token")
            return False

        amount_usdc = 0.1  # 0.1 USDC
        price = current_price
        size = amount_usdc / price

        print(f"   Token ID: {token_id[:30]}...")
        print(f"   價格: ${price}")
        print(f"   數量: {size:.6f} shares")
        print(f"   總額: ${amount_usdc} USDC")
        print()

        # 5. 創建訂單
        print("📝 創建訂單...")

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY",
            fee_rate_bps=0
        )

        signed_order = client.create_order(order_args)
        print("✅ 訂單已簽署")
        # SignedOrder 可能係 object 而唔係 dict
        print(f"   類型: {type(signed_order).__name__}")
        if hasattr(signed_order, 'maker'):
            print(f"   Maker: {signed_order.maker}")
        if hasattr(signed_order, 'signature'):
            print(f"   Signature: {signed_order.signature[:30]}...")
        print()

        # 6. 提交訂單
        print("📤 提交訂單到 CLOB...")

        result = client.post_order(signed_order)

        print("\n🎉🎉🎉 成功！🎉🎉🎉")
        print("✅ 訂單已提交")
        # Result 可能都係 object
        if hasattr(result, 'orderID'):
            print(f"   Order ID: {result.orderID}")
        if hasattr(result, 'status'):
            print(f"   狀態: {result.status}")
        elif hasattr(result, 'message'):
            print(f"   訊息: {result.message}")
        print()

        return True

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()

    if success:
        print("🎊 恭喜！交易成功！")
        sys.exit(0)
    else:
        print("\n❌ 交易失敗")
        sys.exit(1)
