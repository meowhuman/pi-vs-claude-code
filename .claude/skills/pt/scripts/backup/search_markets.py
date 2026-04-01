#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
搜尋 Polymarket 市場
使用 Polymarket CLOB API
"""

import sys
import json
import requests
from datetime import datetime

# Polymarket CLOB API endpoint
CLOB_API = "https://clob.polymarket.com"


def search_markets(query: str, limit: int = 10):
    """
    搜尋 Polymarket 市場

    Args:
        query: 搜尋關鍵字
        limit: 返回結果數量 (預設 10)
    """
    try:
        print(f"🔍 搜尋市場: \"{query}\"\n")

        # 獲取市場列表
        # 注意: Polymarket CLOB API 的實際 endpoint 可能不同
        # 這裡使用通用的搜尋邏輯
        markets_url = f"{CLOB_API}/markets"

        response = requests.get(
            markets_url,
            params={"search": query, "limit": limit, "active": "true"},
            timeout=10,
        )

        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"回應: {response.text}")
            return False

        data = response.json()
        
        # Handle different API response structures
        if isinstance(data, dict):
            markets = data.get('data', [])
        elif isinstance(data, list):
            markets = data
        else:
            markets = []

        if not markets or len(markets) == 0:
            print(f"❌ 沒有找到相關市場: \"{query}\"")
            print("\n提示:")
            print("- 嘗試使用不同的關鍵字")
            print("- 檢查拼寫是否正確")
            print("- 使用更通用的搜尋詞")
            return False

        print(f"找到 {len(markets)} 個相關市場:\n")
        print("=" * 80)

        for idx, market in enumerate(markets, 1):
            print(f"\n{idx}. {market.get('question', 'N/A')}")
            print(f"   ID: {market.get('condition_id', 'N/A')}")

            # 顯示賠率
            outcomes = market.get("outcomes", [])
            if len(outcomes) >= 2:
                yes_price = float(outcomes[0].get("price", 0))
                no_price = float(outcomes[1].get("price", 0))
                print(f"   賠率: Yes {yes_price:.2f} | No {no_price:.2f}")
            else:
                print(f"   賠率: 資料不可用")

            # 顯示交易量
            volume = market.get("volume", 0)
            if volume > 0:
                if volume >= 1_000_000:
                    print(f"   交易量: ${volume/1_000_000:.1f}M")
                elif volume >= 1_000:
                    print(f"   交易量: ${volume/1_000:.1f}K")
                else:
                    print(f"   交易量: ${volume:.0f}")

            # 顯示結束時間
            end_date = market.get("end_date_iso")
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    print(f"   結束時間: {dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    print(f"   結束時間: {end_date}")

            # 顯示市場狀態
            active = market.get("active", False)
            closed = market.get("closed", False)
            if closed:
                print(f"   狀態: ❌ 已關閉")
            elif active:
                print(f"   狀態: ✅ 活躍中")
            else:
                print(f"   狀態: ⏸️  暫停")

        print("\n" + "=" * 80)
        print("\n使用市場 ID 來執行交易")
        return True

    except requests.exceptions.Timeout:
        print("❌ 請求超時，請檢查網絡連接")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 網絡請求錯誤: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python search_markets.py \"搜尋關鍵字\" [limit]")
        print("範例: python search_markets.py \"Trump 2024\" 5")
        sys.exit(1)

    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    success = search_markets(query, limit)
    sys.exit(0 if success else 1)
