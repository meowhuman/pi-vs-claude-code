#!/usr/bin/env python3
"""
完整交易流程 - 使用 ClobClient 的 create_and_post_order
嘗試直接交易
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON

def main():
    try:
        print("🚀 COMBINED TRADE - Create & Post")
        print("=" * 50)
        print()

        # 1. 設置 proxy wallet
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        if not private_key:
            print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
            return False

        clean_key = private_key[2:] if private_key.startswith("0x") else private_key

        # 2. 設置 API credentials
        api_key = os.getenv("POLY_BUILDER_API_KEY")
        api_secret = os.getenv("POLY_BUILDER_SECRET")
        api_passphrase = os.getenv("POLY_BUILDER_PASSPHRASE")

        if not all([api_key, api_secret, api_passphrase]):
            print("❌ 錯誤: 找不到完整的 API credentials")
            return False

        print("🔑 配置:")
        print(f"   Proxy Private Key: {clean_key[:10]}...")
        print(f"   Builder Address: {os.getenv('POLY_ADDRESS')}")
        print(f"   API Key: {api_key}")
        print()

        # 3. 初始化 ClobClient (L2 mode)
        print("📡 初始化 ClobClient (L2 mode)...")

        api_creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )

        client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=POLYGON,
            key=clean_key,
            creds=api_creds
        )

        print("✅ ClobClient 初始化成功")
        print()

        # 4. 獲取市場
        print("📊 獲取市場資訊...")
        market_id = "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"
        market = client.get_market(market_id)

        # 5. 獲取 token ID
        token_id = None
        for token in market.get('tokens', []):
            if token.get('outcome', '').lower() == 'yes':
                token_id = token.get('token_id')
                price = token.get('price', 0.425)
                break

        if not token_id:
            print("❌ 找不到 YES token")
            return False

        # 6. 創建訂單參數
        amount_usdc = 0.1
        size = amount_usdc / price

        print(f"💰 準備訂單:")
        print(f"   Token: {token_id[:30]}...")
        print(f"   價格: ${price}")
        print(f"   數量: {size:.6f} shares")
        print(f"   總額: {amount_usdc} USDC")
        print()

        # 7. 直接創建並提交訂單 (一個方法完成兩步)
        print("🚀 執行 create_and_post_order...")

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY",  # 直接用 string
            fee_rate_bps=0
        )

        result = client.create_and_post_order(order_args)

        print("\n🎉🎉🎉 成功！🎉🎉🎉")
        print("✅ 訂單已提交")
        print(f"   結果類型: {type(result).__name__}")
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
        print("🎊 恭喜！交易成功完成！")
        sys.exit(0)
    else:
        print("\n❌ 交易失敗")
        sys.exit(1)
