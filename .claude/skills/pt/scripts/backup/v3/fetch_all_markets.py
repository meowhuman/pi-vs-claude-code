#!/usr/bin/env python3
"""
獲取所有活躍市場 - 帶緩存功能 (Cache)
Fetch all active markets - with caching mechanism
"""

import requests
import json
import os       # <--- 新增: 用嚟 check 文件是否存在
import time     # <--- 新增: 用嚟 check 時間
from datetime import datetime

GAMMA_API = "https://gamma-api.polymarket.com"
CACHE_FILE = "all_markets_cache.json"  # 緩存文件名
CACHE_DURATION = 3600  # 緩存有效期 (秒)，這裡設為 1 小時

def fetch_all_markets(force_refresh=False):
    """
    獲取所有活躍市場
    參數:
    force_refresh (bool): 如果係 True，就強制重新下載，無視緩存
    """

    # --- 1. 檢查緩存邏輯 (Cache Logic) ---
    if not force_refresh and os.path.exists(CACHE_FILE):
        # 獲取文件最後修改時間
        last_modified_time = os.path.getmtime(CACHE_FILE)
        current_time = time.time()

        # 計算過咗幾耐 (秒)
        age = current_time - last_modified_time

        # 如果文件係 1 小時內 (3600秒)，就直接讀取
        if age < CACHE_DURATION:
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_modified_time))
            print(f"⚡️ 發現有效緩存！(上次更新: {time_str})")
            print(f"📖 正在從 {CACHE_FILE} 讀取數據，唔使 Download...")

            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                print(f"✅ 讀取成功！即刻有得用 {len(cached_data)} 個市場數據！")
                return cached_data
            except Exception as e:
                print(f"⚠️ 緩存文件讀取失敗，唯有重新下載... ({e})")
        else:
            print(f"⏰ 緩存已過期 (舊咗 {(age/60):.1f} 分鐘)，準備重新下載...")
    else:
        if force_refresh:
            print("🔄 用戶強制刷新，準備重新下載...")
        else:
            print("📂 搵唔到緩存文件，準備首次下載...")

    # --- 2. 原本嘅下載邏輯 (無變動，只係最後加咗 Save) ---
    all_markets = []
    offset = 0
    limit = 100
    total_fetched = 0

    print("🚀 開始獲取所有市場 (呢個過程比較慢，請耐心等候)...")

    while True:
        params = {
            "closed": "false",
            "limit": limit,
            "offset": offset
        }

        try:
            response = requests.get(f"{GAMMA_API}/events", params=params, timeout=10)

            if response.status_code != 200:
                print(f"❌ API 錯誤: {response.status_code}")
                break

            events = response.json()

            if not events:
                print(f"✅ 下載完成，總共獲取 {total_fetched} 個事件")
                break

            if offset % 500 == 0: # 唔使每 100 個都 print，每 500 個 print 一次少啲雜訊
                print(f"📊 已獲取 {offset} + ...")

            for event in events:
                markets = event.get('markets', [])
                for market in markets:
                    # 1. 獲取成交量
                    vol = market.get('volume', 0)

                    # 2. 獲取勝率 (Chance) 邏輯
                    outcome_prices = market.get('outcomePrices')
                    chance = 0.0
                    try:
                        # API 有時俾 List ["0.64", "0.36"]，有時俾 String '["0.64", "0.36"]'
                        if isinstance(outcome_prices, str):
                            prices = json.loads(outcome_prices)
                        else:
                            prices = outcome_prices

                        # 通常第一個係 "Yes" 嘅價錢
                        if prices and len(prices) > 0:
                            chance = float(prices[0])
                    except:
                        chance = 0.0

                    all_markets.append({
                        'question': market.get('question', event.get('title', 'N/A')),
                        'condition_id': market.get('conditionId', 'N/A'),
                        'volume': float(vol) if vol else 0.0,
                        'chance': chance,  # <--- 記得儲存入去！
                        'end_date_iso': event.get('endDate', 'N/A'),
                        'event_title': event.get('title', ''),
                        'event_slug': event.get('slug', ''),
                        'active': event.get('active', False),
                        'closed': event.get('closed', False)
                    })

            total_fetched += len(events)

            if len(events) < limit:
                break

            offset += limit
            time.sleep(0.05) # 加快少少速度，0.1 有啲太保守

        except Exception as e:
            print(f"❌ 錯誤: {e}")
            break

    print(f"\n✅ 總共下載咗 {len(all_markets)} 個活躍市場")

    # --- 3. 儲存新的緩存 (Save Cache) ---
    print(f"💾 正在儲存緩存到 {CACHE_FILE} ...")
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_markets, f, ensure_ascii=False)
        print("✅ 緩存已儲存！下次 Run 就會快好多！")
    except Exception as e:
        print(f"⚠️ 緩存儲存失敗: {e}")

    return all_markets

# --- 輔助函數 ---
def search_markets_in_all(markets, keywords, end_date_filter=None):
    """在所有市場中搜索關鍵字"""
    results = []
    for market in markets:
        question_lower = market.get('question', '').lower()
        title_lower = market.get('event_title', '').lower()
        for keyword in keywords:
            if keyword.lower() in question_lower or keyword.lower() in title_lower:
                if end_date_filter:
                    if end_date_filter in market.get('end_date_iso', ''):
                        results.append(market)
                else:
                    results.append(market)
                break
    return results

def main():
    # 測試一下個 fetch function
    # 第一次 Run 會下載，第二次 Run (1小時內) 就會秒讀 Cache
    all_markets = fetch_all_markets()

    print(f"\n🎉 主程式測試: 成功攞到 {len(all_markets)} 條數據")

if __name__ == "__main__":
    main()