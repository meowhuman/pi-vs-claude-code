#!/usr/bin/env python3
"""
獲取所有活躍市場 - 繞過 200 個限制
Fetch all active markets - bypass 200 limit
"""

import requests
import json
from datetime import datetime

GAMMA_API = "https://gamma-api.polymarket.com"

def fetch_all_markets():
    """獲取所有活躍市場"""
    all_markets = []
    offset = 0
    limit = 100  # 每次獲取 100 個
    total_fetched = 0

    print("🚀 開始獲取所有市場...")

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
                print(f"✅ 沒有更多數據，總共獲取 {total_fetched} 個事件")
                break

            print(f"📊 獲取第 {offset//limit + 1} 批，{len(events)} 個事件")

            # 處理每個 event
            for event in events:
                markets = event.get('markets', [])
                for market in markets:
                    all_markets.append({
                        'question': market.get('question', event.get('title', 'N/A')),
                        'condition_id': market.get('conditionId', 'N/A'),
                        'end_date_iso': event.get('endDate', 'N/A'),
                        'event_title': event.get('title', ''),
                        'event_slug': event.get('slug', ''),
                        'active': event.get('active', False),
                        'closed': event.get('closed', False)
                    })

            total_fetched += len(events)

            # 如果返回的數量少於 limit，說明已經到最後一批
            if len(events) < limit:
                break

            offset += limit

            # 避免請求過於頻繁
            import time
            time.sleep(0.1)

        except Exception as e:
            print(f"❌ 錯誤: {e}")
            break

    print(f"\n✅ 總共找到 {len(all_markets)} 個活躍市場")
    return all_markets

def search_markets_in_all(markets, keywords, end_date_filter=None):
    """在所有市場中搜索關鍵字"""
    results = []

    for market in markets:
        question_lower = market.get('question', '').lower()
        title_lower = market.get('event_title', '').lower()

        # 檢查是否包含任何關鍵字
        for keyword in keywords:
            if keyword.lower() in question_lower or keyword.lower() in title_lower:
                # 檢查截止日期（如果指定）
                if end_date_filter:
                    end_date = market.get('end_date_iso', '')
                    if end_date_filter in end_date:
                        results.append(market)
                else:
                    results.append(market)
                break

    return results

def main():
    # 1. 獲取所有市場
    all_markets = fetch_all_markets()

    # 2. 定義搜索的科技關鍵字
    tech_keywords = [
        "AI", "artificial intelligence", "OpenAI", "Anthropic", "ChatGPT", "GPT",
        "Google", "Microsoft", "Apple", "NVIDIA", "Tesla", "Meta", "Facebook",
        "Amazon", "SpaceX", "Musk", "Bitcoin", "cryptocurrency", "crypto", "blockchain",
        "tech", "technology", "software", "iPhone", "Android", "Mac", "Windows",
        "robot", "robotaxi", "Starship", "launch", "CEO", "IPO"
    ]

    print("\n🔍 搜索科技相關市場...")
    tech_markets = search_markets_in_all(all_markets, tech_keywords)
    print(f"✅ 找到 {len(tech_markets)} 個科技相關市場")

    # 3. 搜索 2026 年 6 月截止的市場
    print("\n📅 搜索 2026 年 6 月截止的市場...")
    june_2026_markets = search_markets_in_all(all_markets, [], end_date_filter="2026-06")
    print(f"✅ 找到 {len(june_2026_markets)} 個 2026 年 6 月截止的市場")

    # 4. 保存結果
    results = {
        "total_markets": len(all_markets),
        "tech_markets": len(tech_markets),
        "june_2026_markets": len(june_2026_markets),
        "sample_tech_markets": tech_markets[:20],  # 前 20 個樣本
        "sample_june_2026_markets": june_2026_markets[:20]  # 前 20 個樣本
    }

    # 保存到 JSON 文件
    output_file = "market_search_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 結果已保存到 {output_file}")

    # 5. 顯示一些有趣的統計
    print("\n📊 市場統計:")
    print(f"   總活躍市場數: {len(all_markets)}")
    print(f"   科技相關市場: {len(tech_markets)} ({len(tech_markets)/len(all_markets)*100:.1f}%)")
    print(f"   2026年6月截止: {len(june_2026_markets)} ({len(june_2026_markets)/len(all_markets)*100:.1f}%)")

    # 6. 顯示前 10 個科技市場
    print("\n🔬 前 10 個科技市場:")
    for i, market in enumerate(tech_markets[:10], 1):
        question = market.get('question', 'N/A')[:60]
        end_date = market.get('end_date_iso', 'N/A')
        print(f"\n{i}. {question}...")
        print(f"   截止日期: {end_date}")
        if market.get('event_slug'):
            print(f"   URL: https://polymarket.com/event/{market.get('event_slug')}")

if __name__ == "__main__":
    main()