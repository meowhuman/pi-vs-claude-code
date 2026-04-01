#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "py-clob-client>=0.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
設置 Polymarket API 憑證並檢查餘額
"""

import os
import sys
import json
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

def setup_polymarket_api():
    """設置 Polymarket API 憑證並檢查餘額"""
    try:
        # Load environment variables
        load_dotenv()

        # 讀取配置
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        host = "https://clob.polymarket.com"

        if not private_key:
            print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
            return False

        print("🔧 連接到 Polymarket CLOB API...")

        # 初始化客戶端
        client = ClobClient(host, key=private_key, chain_id=POLYGON)

        # 獲取錢包地址
        wallet_address = client.get_address()
        print(f"📍 錢包地址: {wallet_address}")

        print("\n🔑 設置 API 憑證...")

        try:
            # 嘗試獲取現有的 API 憑證
            try:
                api_keys = client.get_api_keys()
                print(f"🔑 現有 API 憑證: {api_keys}")

                if api_keys:
                    # 使用現有的 API 憑證
                    first_key = api_keys[0]
                    if hasattr(first_key, 'api_key'):
                        client.set_api_creds(first_key)
                    else:
                        # 如果是字典格式，創建 ApiCreds 對象
                        from py_clob_client.clob_types import ApiCreds
                        api_creds = ApiCreds(
                            api_key=first_key['api_key'],
                            api_secret=first_key['api_secret'],
                            api_passphrase=first_key['api_passphrase']
                        )
                        client.set_api_creds(api_creds)
                    print("✅ 使用現有 API 憑證")
                else:
                    print("⚠️  沒有現有 API 憑證，創建新的...")
                    # 創建新的 API 憑證
                    api_creds = client.create_api_key()
                    print(f"🆕 新 API 憑證: {api_creds}")

                    # 使用新的憑證
                    client.set_api_creds(
                        api_creds['access_key'],
                        api_creds['secret_key'],
                        api_creds['passphrase']
                    )
                    print("✅ 使用新 API 憑證")

            except Exception as e:
                print(f"⚠️  API 憑證相關操作: {str(e)}")
                # 嘗試使用 derive 方法
                print("🔄 嘗試導出 API 憑證...")
                derived_creds = client.derive_api_key()
                print(f"🔑 導出憑證: {derived_creds}")

                client.set_api_creds(derived_creds)
                print("✅ 使用導出 API 憑證")

        except Exception as e:
            print(f"❌ API 憑證設置失敗: {str(e)}")
            return False

        print("\n💰 檢查餘額相關信息...")

        # 現在嘗試獲取餘額信息
        try:
            print("\n1. 檢查餘額額度...")
            balance_allowance = client.get_balance_allowance()
            print(f"📊 餘額額度: {balance_allowance}")
        except Exception as e:
            print(f"⚠️  餘額額度: {str(e)}")

        try:
            print("\n2. 檢查訂單...")
            orders = client.get_orders()
            print(f"📋 訂單數量: {len(orders) if isinstance(orders, list) else 'N/A'}")
            if isinstance(orders, list) and len(orders) > 0:
                print(f"📄 第一個訂單: {orders[0]}")
        except Exception as e:
            print(f"⚠️  訂單查詢: {str(e)}")

        try:
            print("\n3. 檢查市場...")
            markets = client.get_markets()
            print(f"📈 市場數據: {type(markets)}")
            if isinstance(markets, dict):
                print(f"📈 市場數據鍵: {list(markets.keys())}")
        except Exception as e:
            print(f"⚠️  市場查詢: {str(e)}")

        # 檢查特定市場（測試交易功能）
        try:
            print("\n4. 測試市場查詢...")
            # 獲取簡化市場
            simplified_markets = client.get_simplified_markets()
            print(f"📊 簡化市場數量: {len(simplified_markets) if isinstance(simplified_markets, list) else 'N/A'}")
        except Exception as e:
            print(f"⚠️  簡化市場查詢: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_polymarket_api()
    sys.exit(0 if success else 1)