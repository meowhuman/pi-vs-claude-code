#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "py-clob-client>=0.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
測試活躍市場查詢和交易功能
"""

import os
import sys
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

def test_live_market():
    """測試活躍市場查詢"""
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

        # 初始化客戶端並設置憑證
        client = ClobClient(host, key=private_key, chain_id=POLYGON)

        try:
            api_keys = client.get_api_keys()
            if api_keys:
                client.set_api_creds(api_keys[0])
                print("✅ 使用現有 API 憑證")
            else:
                derived_creds = client.derive_api_key()
                client.set_api_creds(derived_creds)
                print("✅ 使用導出 API 憑證")
        except:
            derived_creds = client.derive_api_key()
            client.set_api_creds(derived_creds)
            print("✅ 使用導出 API 憑證")

        # 獲取簡化市場
        print("\n📊 獲取活躍市場...")
        try:
            simplified_markets = client.get_simplified_markets()
            print(f"✅ 獲取到 {len(simplified_markets)} 個簡化市場")

            if len(simplified_markets) > 0:
                print("\n前 5 個活躍市場:")
                for i, market in enumerate(simplified_markets[:5]):
                    print(f"\n{i+1}. {market.get('question', 'N/A')}")
                    print(f"   ID: {market.get('condition_id', 'N/A')}")

                    # 顯示 outcomes
                    outcomes = market.get('outcomes', [])
                    if outcomes:
                        print(f"   選項: {', '.join([outcome.get('outcome', 'N/A') for outcome in outcomes])}")

                        # 顯示價格
                        for outcome in outcomes:
                            price = outcome.get('price', 0)
                            outcome_name = outcome.get('outcome', 'N/A')
                            print(f"   {outcome_name}: {price:.2f} USDC")

                    # 顯示交易量
                    volume = market.get('volume_24h', 0)
                    if volume:
                        print(f"   24h 交易量: {volume:.2f} USDC")

                    # 顯示結束時間
                    end_date = market.get('end_time')
                    if end_date:
                        print(f"   結束時間: {end_date}")

                    # 檢查是否活躍
                    active = market.get('active', False)
                    print(f"   狀態: {'✅ 活躍' if active else '❌ 不活躍'}")

                # 測試獲取第一個市場的詳細信息
                first_market_id = simplified_markets[0].get('condition_id')
                if first_market_id:
                    print(f"\n🔍 測試市場詳情: {first_market_id}")
                    try:
                        market_detail = client.get_market(first_market_id)
                        print("✅ 市場詳情獲取成功")
                        print(f"   標題: {market_detail.get('question', 'N/A')}")
                    except Exception as e:
                        print(f"⚠️  市場詳情獲取失敗: {str(e)}")

                return True

        except Exception as e:
            print(f"❌ 獲取簡化市場失敗: {str(e)}")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_live_market()
    sys.exit(0 if success else 1)