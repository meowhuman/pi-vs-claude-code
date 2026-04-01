#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
#     "python-dotenv>=1.0.0",
#     "py-clob-client>=0.0.9",
# ]
# ///

"""
整合搜索、详情、URL 的统一 Polymarket 市场工具
Combined Polymarket market search, detail, and URL lookup tool
"""

import sys
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def get_sport_tag_id(sport_name: str):
    """
    從 /sports endpoint 獲取運動項目的 tag ID
    Get sport tag ID from /sports endpoint

    Args:
        sport_name: 運動項目名稱 (e.g., "NBA", "NFL")

    Returns:
        tag_id (str) or None
    """
    try:
        resp = requests.get(f"{GAMMA_API}/sports", timeout=5)
        if resp.status_code == 200:
            sports = resp.json()
            sport_lower = sport_name.lower()

            for sport in sports:
                if sport.get('sport', '').lower() == sport_lower:
                    tags = sport.get('tags', '')
                    # Tags is a comma-separated string like "1,745,100639"
                    # Return the sport-specific tag (usually the middle one)
                    tag_list = [t.strip() for t in tags.split(',') if t.strip()]
                    if len(tag_list) >= 2:
                        return tag_list[1]  # Usually the sport-specific tag
                    elif tag_list:
                        return tag_list[0]
    except Exception as e:
        print(f"   Warning: Could not fetch sport tags: {e}")
    return None


def search_markets(query: str, limit: int = 10):
    """
    搜尋 Polymarket 活跃市場 (使用 Gamma API with tag filtering)
    Search active Polymarket markets by keyword (using Gamma API with tag filtering)

    Args:
        query: 搜尋關鍵字 / Search keyword (e.g., "NBA", "Bitcoin", "Trump")
        limit: 返回結果數量 / Number of results (default 10)
    """
    try:
        print(f"\n🔍 搜尋市場: \"{query}\"")
        print(f"   Searching for markets: \"{query}\"\n")

        all_markets = []

        # Check if query is a sport name
        sport_tag = get_sport_tag_id(query)

        if sport_tag:
            # Strategy 1: Search by sport tag (for sports markets)
            print(f"🏀 檢測到運動項目，使用 tag_id={sport_tag} 搜尋... / Sports detected, using tag filter...")
            try:
                gamma_response = requests.get(
                    f"{GAMMA_API}/events",
                    params={
                        "tag_id": sport_tag,
                        "active": "true",
                        "closed": "false",
                        "limit": 50,
                    },
                    timeout=10,
                )

                if gamma_response.status_code == 200:
                    events = gamma_response.json()
                    if isinstance(events, list):
                        for event in events:
                            markets = event.get('markets', [])
                            for market in markets:
                                all_markets.append({
                                    'question': market.get('question', event.get('title', 'N/A')),
                                    'condition_id': market.get('conditionId', 'N/A'),
                                    'end_date_iso': event.get('endDate', 'N/A'),
                                    'game_start_time': event.get('gameStartTime'),
                                    'active': event.get('active', True),
                                    'closed': event.get('closed', False),
                                    'accepting_orders': True,
                                })
            except Exception as e:
                print(f"   Sport search warning: {e}")

        # Strategy 2: Keyword search (for all other markets)
        if not all_markets:
            print(f"🔄 正在從 Gamma API 查詢市場... / Querying markets from Gamma API...")
            try:
                gamma_response = requests.get(
                    f"{GAMMA_API}/events",
                    params={
                        "limit": 200,
                        "closed": "false",
                    },
                    timeout=10,
                )

                if gamma_response.status_code == 200:
                    events = gamma_response.json()
                    if isinstance(events, list):
                        for event in events:
                            if event.get('closed', False):
                                continue
                            markets = event.get('markets', [])
                            for market in markets:
                                all_markets.append({
                                    'question': market.get('question', event.get('title', 'N/A')),
                                    'condition_id': market.get('conditionId', 'N/A'),
                                    'end_date_iso': event.get('endDate', 'N/A'),
                                    'game_start_time': event.get('gameStartTime'),
                                    'active': event.get('active', False),
                                    'closed': event.get('closed', False),
                                    'accepting_orders': True,
                                })
            except Exception as e:
                print(f"   Gamma API warning: {e}")

            # Filter by keyword (case-insensitive) only if not sport search
            query_lower = query.lower()
            all_markets = [
                m for m in all_markets
                if query_lower in m.get('question', '').lower()
            ]

        if not all_markets:
            print(f"❌ 沒有找到匹配 \"{query}\" 的市場 / No markets found matching \"{query}\"")
            return []

        # Limit results
        filtered_markets = all_markets[:limit]

        print(f"✅ 找到 {len(filtered_markets)} 個市場 / Found {len(filtered_markets)} markets:\n")
        print("=" * 100)

        for idx, market in enumerate(filtered_markets, 1):
            market_id = market.get('condition_id', 'N/A')
            question = market.get('question', 'N/A')
            end_date = market.get("end_date_iso")
            game_start = market.get("game_start_time")  # For sports markets
            active = market.get("active", False)
            closed = market.get("closed", False)
            accepting_orders = market.get("accepting_orders", False)

            print(f"\n{idx}. {question}")
            print(f"   Market ID: {market_id}")

            # Display game start time for sports markets
            if game_start and game_start != 'N/A':
                try:
                    if isinstance(game_start, str):
                        if 'T' in game_start or 'Z' in game_start:
                            dt = datetime.fromisoformat(game_start.replace("Z", "+00:00"))
                        else:
                            dt = datetime.fromisoformat(game_start)
                        print(f"   比賽時間 / Game Start: {dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    print(f"   比賽時間 / Game Start: {game_start}")

            # Display end date
            if end_date and end_date != 'N/A':
                try:
                    if isinstance(end_date, str):
                        if 'T' in end_date or 'Z' in end_date:
                            dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        else:
                            dt = datetime.fromisoformat(end_date)
                        print(f"   結束時間 / Ends: {dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    print(f"   結束時間 / Ends: {end_date}")

            # Display status
            if closed:
                print(f"   狀態 / Status: ❌ 已關閉 / Closed")
            elif active and accepting_orders:
                print(f"   狀態 / Status: ✅ 活躍中 / Active (Accepting Orders)")
            elif active:
                print(f"   狀態 / Status: ⏸️  暫停接單 / Active (Not Accepting Orders)")
            else:
                print(f"   狀態 / Status: ⏸️  暫停 / Paused")

        print("\n" + "=" * 100)
        print("\n💡 提示 / Tips:")
        print("   - 使用 'detail <market-id>' 查看詳細信息與價格")
        print("   - Use 'detail <market-id>' to see detailed information and prices")
        print(f"   - 複製 Market ID 來執行交易 / Copy Market ID to trade")

        return filtered_markets

    except requests.exceptions.Timeout:
        print("❌ 請求超時 / Request timeout - try again")
        return []
    except Exception as e:
        print(f"❌ 錯誤 / Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def get_market_detail(market_id: str):
    """
    獲取市場詳細信息（包括 Bid/Ask 價格）
    Get detailed market information including Bid/Ask prices

    Args:
        market_id: Market condition ID
    """
    host = "https://clob.polymarket.com"
    key = os.getenv("POLYGON_PRIVATE_KEY")

    if not key:
        print("❌ 錯誤 / Error: POLYGON_PRIVATE_KEY 未設定 / not found in .env")
        return None

    try:
        print(f"\n🔍 獲取市場詳情 / Getting market details...")

        # Initialize client
        client = ClobClient(host, key=key, chain_id=POLYGON)

        # Get market details
        market = client.get_market(market_id)

        if not market:
            print("❌ 找不到市場 / Market not found")
            return None

        print(f"\n{'='*80}")
        print(f"📊 市場詳情 / Market Details")
        print(f"{'='*80}")
        print(f"問題 / Question: {market.get('question', 'N/A')}")
        print(f"市場 ID / Market ID: {market_id}")
        status = '✅ 開放 / Open' if market.get('active') and not market.get('closed') else '❌ 已關閉 / Closed'
        print(f"狀態 / Status: {status}")
        print(f"結束時間 / End Date: {market.get('end_date_iso', 'N/A')}")
        description = market.get('description', 'N/A')
        if description and description != 'N/A':
            print(f"描述 / Description: {description[:150]}...")
        print(f"{'='*80}")

        # Get tokens (outcomes)
        tokens = market.get('tokens', [])

        if tokens:
            print(f"\n💰 結果選項與價格 / Outcomes and Prices:")
            print(f"{'='*80}")

            for token in tokens:
                outcome = token.get('outcome', 'N/A')
                token_id = token.get('token_id', 'N/A')

                # Get orderbook for this token
                try:
                    ob = client.get_order_book(token_id)
                    asks = ob.asks if hasattr(ob, 'asks') and ob.asks else []
                    bids = ob.bids if hasattr(ob, 'bids') and ob.bids else []

                    best_ask = float(asks[0].price) if asks else None
                    best_bid = float(bids[0].price) if bids else None

                    print(f"\n  {outcome}:")
                    print(f"    Token ID: {token_id}")
                    if best_bid and best_ask:
                        mid_price = (best_bid + best_ask) / 2
                        spread = best_ask - best_bid
                        print(f"    最佳買價 (Bid) / Best Bid: ${best_bid:.4f}")
                        print(f"    最佳賣價 (Ask) / Best Ask: ${best_ask:.4f}")
                        print(f"    中間價 / Mid Price: ${mid_price:.4f}")
                        print(f"    價差 / Spread: ${spread:.4f}")
                    else:
                        print(f"    ⚠️  流動性不足 / Insufficient liquidity")

                except Exception as e:
                    print(f"\n  {outcome}:")
                    print(f"    Token ID: {token_id}")
                    print(f"    ⚠️  無法獲取價格 / Unable to fetch price: {e}")

        print(f"\n{'='*80}\n")
        return market

    except Exception as e:
        print(f"❌ 錯誤 / Error: {e}")
        return None


def get_market_from_url(slug: str):
    """
    從 URL Slug 獲取市場詳情
    Get market details from URL slug

    Args:
        slug: Market slug from URL (e.g., "maduro-out-in-2025")
    """
    api_url = f"{GAMMA_API}/events"

    try:
        print(f"\n🔍 從 URL 查詢市場 / Looking up market from URL slug: {slug}")

        # Search for events
        params = {
            "slug": slug,
            "closed": "false"
        }
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()

        events = response.json()

        if not events:
            print(f"❌ 找不到市場 / Market not found: {slug}")
            return None

        event = events[0] if isinstance(events, list) else events

        print(f"\n{'='*80}")
        print(f"📊 事件資訊 / Event Information")
        print(f"{'='*80}")
        print(f"標題 / Title: {event.get('title', 'N/A')}")
        description = event.get('description', 'N/A')
        if description and description != 'N/A':
            print(f"描述 / Description: {description[:100]}...")
        print(f"結束時間 / End Date: {event.get('endDate', 'N/A')}")
        print(f"{'='*80}")

        # Get markets from this event
        markets = event.get('markets', [])

        if not markets:
            print("❌ 沒有找到交易市場 / No trading markets found")
            return None

        print(f"\n💱 可交易市場 / Available Trading Markets:")
        print(f"{'='*80}")

        for i, market in enumerate(markets, 1):
            question = market.get('question', 'N/A')
            condition_id = market.get('conditionId', 'N/A')

            # Get outcomes
            tokens = market.get('tokens', [])
            print(f"\n{i}. {question}")
            print(f"   Market ID: {condition_id}")
            print(f"   結果選項 / Outcomes:")

            for token in tokens:
                outcome = token.get('outcome', 'N/A')
                token_id = token.get('token_id', 'N/A')
                price = token.get('price', 'N/A')
                print(f"     - {outcome}: ${price} (Token ID: {token_id})")

        print(f"\n{'='*80}\n")
        return event

    except Exception as e:
        print(f"❌ 錯誤 / Error: {e}")
        return None


def print_help():
    """顯示幫助信息 / Display help information"""
    help_text = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                  Polymarket 統一搜索工具 / Unified Search Tool                ║
╚═══════════════════════════════════════════════════════════════════════════════╝

用法 / Usage:
  python search_market_new.py search <keyword> [limit]
    搜尋市場 / Search for markets by keyword
    範例 / Example: python search_market_new.py search "politics" 10

  python search_market_new.py detail <market-id>
    獲取市場詳細信息（包括價格） / Get detailed market info with prices
    範例 / Example: python search_market_new.py detail 0x3648ab7c...

  python search_market_new.py url <slug>
    從 URL Slug 查詢市場 / Look up market from URL slug
    範例 / Example: python search_market_new.py url "maduro-out-in-2025"

選項 / Options:
  search "keyword" [limit]    : 搜尋市場 / Search markets (default limit: 10)
  detail <market-id>          : 查看詳情 / Show market details
  url <slug>                  : 從 URL 查詢 / Look up from URL slug

範例 / Examples:
  python search_market_new.py search "Trump" 5
  python search_market_new.py search "election" 20
  python search_market_new.py detail 0x3648ab7c146a9a85957e07c1d43a82272be71fde767822fd425e10ba0d6c0757
  python search_market_new.py url "will-trump-win-the-2024-us-presidential-election"

提示 / Tips:
  - 先用 'search' 找市場 / First use 'search' to find markets
  - 複製 Market ID，用 'detail' 查看價格 / Copy Market ID and use 'detail' for prices
  - 或者直接用 'url' + slug 查詢 / Or use 'url' with slug directly
"""
    print(help_text)


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "search":
        if len(sys.argv) < 3:
            print("❌ 請提供搜尋關鍵字 / Please provide search keyword")
            print("用法 / Usage: python search_market_new.py search <keyword> [limit]")
            sys.exit(1)

        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        search_markets(query, limit)

    elif command == "detail":
        if len(sys.argv) < 3:
            print("❌ 請提供市場 ID / Please provide market ID")
            print("用法 / Usage: python search_market_new.py detail <market-id>")
            sys.exit(1)

        market_id = sys.argv[2]
        get_market_detail(market_id)

    elif command == "url":
        if len(sys.argv) < 3:
            print("❌ 請提供 URL Slug / Please provide URL slug")
            print("用法 / Usage: python search_market_new.py url <slug>")
            sys.exit(1)

        slug = sys.argv[2]
        get_market_from_url(slug)

    elif command == "help" or command == "-h" or command == "--help":
        print_help()

    else:
        print(f"❌ 未知命令 / Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
