#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "py-clob-client>=0.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
使用正確的 Polymarket CLOB API 檢查餘額
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

            # 獲取錢包地址
            wallet_address = client.get_address()
            print(f"📍 錢包地址: {wallet_address}")

        except Exception as e:
            print(f"❌ 初始化客戶端失敗: {str(e)}")
            return False

        print("\n💰 檢查餘額相關信息...")

        # 檢查餘額額度
        try:
            print("\n1. 檢查餘額額度...")
            balance_allowance = client.get_balance_allowance()
            print(f"📊 餘額額度: {balance_allowance}")
        except Exception as e:
            print(f"❌ 獲取餘額額度失敗: {str(e)}")

        # 檢查市場列表以驗證連接
        try:
            print("\n2. 檢查市場數量...")
            markets = client.get_markets()
            if isinstance(markets, list):
                print(f"📈 可用市場數量: {len(markets)}")
                if len(markets) > 0:
                    print(f"📄 第一個市場: {markets[0].get('question', 'N/A') if isinstance(markets[0], dict) else markets[0]}")
            else:
                print(f"📈 市場數據類型: {type(markets)}")
        except Exception as e:
            print(f"❌ 獲取市場失敗: {str(e)}")

        # 檢查可用餘額相關方法
        try:
            print("\n3. 檢查其他相關信息...")

            # 檢查抵押品地址
            try:
                collateral_address = client.get_collateral_address()
                print(f"💼 抵押品地址: {collateral_address}")
            except:
                pass

            # 檢查費率
            try:
                fee_rate = client.get_fee_rate_bps()
                print(f"💰 費率: {fee_rate} bps")
            except:
                pass

            # 檢查訂單
            try:
                orders = client.get_orders()
                print(f"📋 訂單數量: {len(orders) if isinstance(orders, list) else 'N/A'}")
            except Exception as e:
                print(f"⚠️  無法獲取訂單: {str(e)}")

        except Exception as e:
            print(f"⚠️  檢查其他信息時出錯: {str(e)}")

        print("\n💡 提示:")
        print("- Polymarket 使用分離的 trading wallet")
        print("- 需要先將 USDC 存入 Polymarket trading wallet 才能交易")
        print("- 可以通過 Polymarket 網頁版進行充值")
        print("- 餘額信息可能需要通過不同的 API 端點獲取")

        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_polymarket_balance()
    sys.exit(0 if success else 1)