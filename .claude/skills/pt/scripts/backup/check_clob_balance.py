#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "py-clob-client>=0.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
使用 Polymarket CLOB API 檢查餘額
"""

import os
import sys
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

def check_polymarket_balance():
    """使用 Polymarket CLOB API 檢查餘額"""
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
        try:
            client = ClobClient(host, key=private_key, chain_id=POLYGON)
            # 創建或導入 API 憑證
            try:
                client.create_or_derive_api_creds()
                print("✅ API 憑證設置成功")
            except Exception as e:
                print(f"⚠️  API 憑證可能已存在: {str(e)}")

        except Exception as e:
            print(f"❌ 初始化客戶端失敗: {str(e)}")
            return False

        print("\n💰 檢查餘額...")

        # 檢查餘額
        try:
            balance_response = client.get_balance()
            print(f"📊 餘額回應: {balance_response}")

            if isinstance(balance_response, dict):
                # 嘗試提取 USDC 餘額
                if 'usdc' in balance_response:
                    usdc_balance = float(balance_response['usdc'])
                    print(f"💵 USDC 餘額: {usdc_balance:.2f} USDC")
                else:
                    # 檢查其他可能嘅字段名
                    for key, value in balance_response.items():
                        if 'usdc' in key.lower() or 'balance' in key.lower():
                            print(f"💵 {key}: {value}")

            elif isinstance(balance_response, list):
                print("📊 餘額列表:")
                for item in balance_response:
                    print(f"   - {item}")
            else:
                print(f"📊 餘額類型: {type(balance_response)}")
                print(f"📊 餘額內容: {balance_response}")

        except Exception as e:
            print(f"❌ 獲取餘額失敗: {str(e)}")
            # 嘗試其他方法
            try:
                print("\n🔄 嘗試其他方法...")
                # 可能需要使用不同的 API 端點
                token_balances = client.get_token_balances()
                print(f"🪙 Token 餘額: {token_balances}")
            except Exception as e2:
                print(f"❌ 替代方法也失敗: {str(e2)}")

        # 嘗試獲取賬戶信息
        try:
            print("\n👤 獲取賬戶信息...")
            account_info = client.get_me()
            print(f"📋 賬戶信息: {account_info}")
        except Exception as e:
            print(f"⚠️  無法獲取賬戶信息: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_polymarket_balance()
    sys.exit(0 if success else 1)