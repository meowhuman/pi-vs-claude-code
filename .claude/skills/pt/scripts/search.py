#!/usr/bin/env python3
"""
Polymarket Search - 統一市場搜尋入口
整合: search_market.py, search_extended_markets.py

用法:
    python search.py "Trump"                           # 基礎搜尋
    python search.py "NBA" --limit 20                  # 指定數量
    python search.py --prob 80:20                      # 機率篩選
    python search.py --min-vol 50000                   # 最低成交量
    python search.py --urgent 7                        # 7 日內截止
    python search.py "crypto" --sort volume            # 排序
    python search.py --analyze                         # 分佈分析
    python search.py detail <ID>                       # 市場詳情
    python search.py url <slug>                        # 從 URL 獲取
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.client import get_client, get_api_urls
from utils.market import get_market_info, get_orderbook

load_dotenv()

# Cache file for all markets
CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "all_markets_cache.json")

# category keywords for smart filtering
CATEGORIES = {
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto", "blockchain", 
               "usdt", "usdc", "tether", "stablecoin", "defi", "nft", "memecoin", "doge", 
               "xrp", "ripple", "cardano", "ada", "polygon", "matic", "avalanche", "avax",
               "chainlink", "link", "uniswap", "aave", "compound", "binance", "coinbase",
               "hyperliquid", "microstrategy", "satoshi"],
    "politics": ["trump", "biden", "election", "president", "congress", "senate", "house",
                 "republican", "democrat", "gop", "white house", "governor", "vote",
                 "impeach", "tariff", "fed chair", "cabinet", "administration"],
    "sports": ["nba", "nfl", "mlb", "nhl", "mls", "fifa", "super bowl", "world cup",
               "premier league", "champions league", "ufc", "boxing", "tennis", "golf",
               "olympics", "f1", "formula 1", "playoff", "championship", "mvp"],
    "economy": ["fed", "inflation", "recession", "interest rate", "gdp", "unemployment",
                "stock", "s&p", "nasdaq", "dow", "treasury", "bond", "dollar", "forex",
                "housing", "cpi", "fomc", "powell"],
    "entertainment": ["movie", "oscar", "grammy", "emmy", "netflix", "disney", "spotify",
                      "gta", "game", "playstation", "xbox", "steam", "twitch", "youtube",
                      "tiktok", "celebrity", "music", "album", "tour"],
    "tech": ["apple", "google", "microsoft", "amazon", "meta", "facebook", "nvidia",
             "ai", "chatgpt", "openai", "anthropic", "tesla", "spacex", "elon musk",
             "iphone", "android", "startup", "ipo"],
    "world": ["china", "russia", "ukraine", "taiwan", "europe", "nato", "un", "war",
              "ceasefire", "sanction", "xi jinping", "putin", "zelensky", "israel", 
              "gaza", "iran", "north korea", "climate", "pandemic"]
}


# =============================================================================
# Market Fetching Functions
# =============================================================================

def fetch_all_markets(use_cache: bool = True, max_age_hours: int = 6, include_closed: bool = False) -> list:
    """
    獲取全部市場 (使用緩存)
    
    Args:
        use_cache: 是否使用緩存
        max_age_hours: 緩存最大時間
        include_closed: 是否包含已結束市場
    """
    # Check cache
    cache_key = "closed" if include_closed else "active"
    cache_file = CACHE_FILE.replace(".json", f"_{cache_key}.json")
    
    if use_cache and os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        age_hours = (datetime.now().timestamp() - mtime) / 3600
        
        if age_hours < max_age_hours:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get('markets', [])
    
def fetch_all_markets(use_cache: bool = True, max_age_hours: int = 6, include_closed: bool = False, fast: bool = False, min_volume: float = 0) -> list:
    """
    獲取市場 (支持增量更新)
    
    Args:
        use_cache: 是否使用緩存
        max_age_hours: 緩存最大時間
        include_closed: 是否包含已結束市場
        fast: 是否只獲取前幾頁 (快速模式)
        min_volume: 最低成交量門檻 (掃描時過濾)
    """
    cache_key = "closed" if include_closed else "active"
    cache_file = CACHE_FILE.replace(".json", f"_{cache_key}.json")
    
    existing_markets = []
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                existing_markets = cached_data.get('markets', [])
                
                # 如果快取仲好新，且唔係強制刷新，就直接回傳
                mtime = os.path.getmtime(cache_file)
                age_hours = (datetime.now().timestamp() - mtime) / 3600
                if use_cache and age_hours < max_age_hours and not fast:
                    return existing_markets
        except:
            pass

    # Fetch from Gamma API
    urls = get_api_urls()
    status = "所有" if include_closed else "活躍"
    vol_info = f" (最低成交量: ${min_volume:,.0f})" if min_volume > 0 else ""
    print(f"📡 正在獲取{status}市場{vol_info}...")
    
    new_markets = []
    limit = 100
    offset = 0
    max_pages = 10 if fast else 100 # 快速模式 1000 個，正常模式 10000 個
    
    # Store existing IDs for quick lookup
    existing_ids = {str(m.get('id')): True for m in existing_markets}

    # Track consecutive empty pages for early stopping
    consecutive_empty_pages = 0
    max_consecutive_empty = 5  # 連續 5 頁沒有新數據才停止

    try:
        while (offset // limit) < max_pages:
            params = {
                "limit": limit,
                "offset": offset,
            }
            if not include_closed:
                params["closed"] = "false"

            try:
                resp = requests.get(f"{urls['gamma']}/markets", params=params, timeout=15)
                if resp.status_code != 200:
                    print(f"   ⚠️ API 返回錯誤 {resp.status_code}，停止獲取新數據")
                    break
            except Exception as conn_error:
                print(f"   ⚠️ 連線中斷 ({conn_error})，將使用現有緩存數據")
                break

            data = resp.json()
            if not isinstance(data, list) or not data:
                print(f"   ✓ API 無更多數據，已完成抓取")
                break

            page_markets = data

            # 如果有成交量門檻，過濾低成交量市場
            if min_volume > 0:
                page_markets = [
                    m for m in page_markets
                    if float(m.get('volumeNum', m.get('volume', 0)) or 0) >= min_volume
                ]

            new_markets.extend(page_markets)

            # 檢查係咪已經開始見到舊資料
            new_count_in_page = sum(1 for m in page_markets if str(m.get('id')) not in existing_ids)

            kept = len(page_markets)
            total = len(data)
            print(f"   已獲取 {len(new_markets)} 個市場... (第 {offset//limit + 1} 頁, 保留 {kept}/{total}, 新增 {new_count_in_page})")

            # 改進的重複檢測：連續多頁沒有新數據才停止
            if new_count_in_page == 0:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_consecutive_empty and offset > 1000:
                    print(f"   ℹ️ 連續 {consecutive_empty_pages} 頁無新數據，停止獲取")
                    break
            else:
                consecutive_empty_pages = 0  # 重置計數器

            offset += limit
            import time
            time.sleep(0.1) # 稍微延遲避免被 rate limit
            
        # Merge: 用新資料覆蓋舊資料，並保持唯一性
        all_markets_dict = {str(m.get('id', m.get('conditionId'))): m for m in existing_markets}
        for m in new_markets:
            all_markets_dict[str(m.get('id', m.get('conditionId')))] = m
            
        final_markets = list(all_markets_dict.values())
        
        # Save cache
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(final_markets),
                "include_closed": include_closed,
                "markets": final_markets
            }, f)
        
        print(f"✅ 緩存更新完成，共 {len(final_markets)} 個市場")
        return final_markets
        
    except Exception as e:
        print(f"❌ 獲取失敗: {e}")
        return existing_markets if existing_markets else []


def search_markets_api(query: str, limit: int = 10) -> list:
    """使用 API 搜尋市場"""
    urls = get_api_urls()
    
    try:
        resp = requests.get(
            f"{urls['gamma']}/public-search",
            params={"query": query, "limit": limit},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            # Handle different response formats
            if isinstance(data, dict):
                return data.get('markets', data.get('data', []))
            return data[:limit] if isinstance(data, list) else []
        return []
        
    except Exception as e:
        print(f"⚠️ API 搜尋失敗: {e}")
        return []


# =============================================================================
# Filtering Functions
# =============================================================================

def parse_prob_range(prob_arg: str) -> tuple:
    """
    解析機率範圍
    
    支持格式:
    - 80:20 -> (20, 80)
    - 75:25 -> (25, 75)
    """
    try:
        parts = prob_arg.split(':')
        if len(parts) == 2:
            high = float(parts[0])
            low = float(parts[1])
            return (low, high)
        return (0, 100)
    except:
        return (0, 100)


def get_market_probability(market: dict) -> float:
    """獲取市場 Yes 機率"""
    # 1. 優先從 outcomePrices 獲取 (Gamma 格式)
    prob = market.get('outcomePrices')
    if prob:
        try:
            prices = json.loads(prob) if isinstance(prob, str) else prob
            if len(prices) >= 2:
                # Gamma 格式: [Yes_Price, No_Price] (跟 outcomes: ["Yes", "No"] 順序一致)
                return float(prices[0]) * 100
        except:
            pass
    
    # 2. 試下直接從 bestAsk 獲取
    best_ask = market.get('bestAsk')
    if best_ask:
        try:
            return float(best_ask) * 100
        except:
            pass
    
    # 3. 試下從 tokens 獲取 (CLOB 格式)
    tokens = market.get('tokens', [])
    if tokens:
        for t in tokens:
            outcome = str(t.get('outcome', '')).lower()
            if outcome == 'yes':
                price = t.get('price', t.get('last_trade_price'))
                if price:
                    return float(price) * 100
    
    return 50.0


def get_market_volume(market: dict) -> float:
    """獲取市場成交量"""
    # 優先使用 volumeNum (Gamma 格式)
    vol = market.get('volumeNum', market.get('volume', 0))
    try:
        return float(vol)
    except:
        return 0


def get_market_end_date(market: dict) -> datetime:
    """獲取市場結束日期"""
    end_str = market.get('endDate', market.get('end_date'))
    
    if not end_str:
        return datetime.max.replace(tzinfo=timezone.utc)
    
    try:
        if isinstance(end_str, str):
            if 'T' in end_str:
                return datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            return datetime.strptime(end_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        return datetime.max.replace(tzinfo=timezone.utc)
    except:
        return datetime.max.replace(tzinfo=timezone.utc)


def filter_by_query(markets: list, query: str) -> list:
    """根據關鍵字過濾"""
    if not query:
        return markets
    
    query_lower = query.lower()
    result = []
    for m in markets:
        # Search in multiple fields
        text = ' '.join([
            str(m.get('question', '')),
            str(m.get('title', '')),
            str(m.get('description', ''))
        ]).lower()
        if query_lower in text:
            result.append(m)
    return result


def filter_by_category(markets: list, category: str) -> list:
    """根據類別過濾市場
    
    類別會自動搜尋相關嘅所有關鍵字
    只搜尋 question 同 title，避免 description 中嘅噪音
    """
    import re
    
    if not category:
        return markets
    
    category_lower = category.lower()
    if category_lower not in CATEGORIES:
        print(f"⚠️ 未知類別 '{category}'")
        print(f"可用類別: {', '.join(CATEGORIES.keys())}")
        return markets
    
    keywords = CATEGORIES[category_lower]
    result = []
    
    for m in markets:
        # 只搜尋 question 同 title，唔包括 description（避免噪音）
        text = ' '.join([
            str(m.get('question', '')),
            str(m.get('title', ''))
        ]).lower()
        
        # 用 word boundary 確保係完整單詞匹配
        for kw in keywords:
            # 對於多字關鍵字用普通匹配，單字用 word boundary
            if ' ' in kw:
                if kw in text:
                    result.append(m)
                    break
            else:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text):
                    result.append(m)
                    break
    
    return result



def filter_by_probability(markets: list, prob_range: tuple) -> list:
    """根據機率範圍過濾
    
    80:20 意思係搜尋機率介於 20% 到 80% 之間嘅市場
    即係仲有不確定性、有交易價值嘅市場
    """
    min_prob, max_prob = prob_range  # e.g., (20, 80)
    result = []
    
    for m in markets:
        prob = get_market_probability(m)
        
        # 80:20 意思係 20 <= prob <= 80
        # 搵出機率介於呢個範圍嘅市場
        if min_prob <= prob <= max_prob:
            result.append(m)
    
    return result


def filter_by_volume(markets: list, min_volume: float) -> list:
    """根據最低成交量過濾"""
    return [m for m in markets if get_market_volume(m) >= min_volume]


def filter_urgent(markets: list, days: int = 7) -> list:
    """只保留 N 日內截止嘅市場"""
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days)
    
    result = []
    for m in markets:
        end_date = get_market_end_date(m)
        if end_date <= deadline and end_date >= now:
            result.append(m)
    
    return result


def filter_by_date_range(markets: list, date_from: str = None, date_to: str = None) -> list:
    """根據結束日期範圍過濾
    
    Args:
        date_from: 開始日期 (YYYY-MM-DD)
        date_to: 結束日期 (YYYY-MM-DD)
    """
    result = []
    
    try:
        from_date = datetime.strptime(date_from, '%Y-%m-%d').replace(tzinfo=timezone.utc) if date_from else None
        to_date = datetime.strptime(date_to, '%Y-%m-%d').replace(tzinfo=timezone.utc) if date_to else None
    except ValueError as e:
        print(f"⚠️ 日期格式錯誤: {e}")
        return markets
    
    for m in markets:
        end_date = get_market_end_date(m)
        has_no_deadline = (end_date == datetime.max.replace(tzinfo=timezone.utc))
        
        # 如果市場沒有截止日期，視為符合 date_to 條件（因為它會一直接受交易）
        if from_date and not has_no_deadline and end_date < from_date:
            continue
        if to_date and not has_no_deadline and end_date > to_date:
            continue
        
        result.append(m)
    
    return result


def filter_active_or_closed(markets: list, status: str = 'active') -> list:
    """根據市場狀態過濾
    
    Args:
        status: 'active' (活躍), 'closed' (已結束), 'all' (全部)
    """
    if status == 'all':
        return markets
    
    now = datetime.now(timezone.utc)
    result = []
    
    for m in markets:
        end_date = get_market_end_date(m)
        is_active = end_date > now
        
        if status == 'active' and is_active:
            result.append(m)
        elif status == 'closed' and not is_active:
            result.append(m)
    
    return result


def sort_markets(markets: list, sort_by: str = 'volume') -> list:
    """排序市場"""
    if sort_by == 'volume':
        return sorted(markets, key=lambda x: get_market_volume(x), reverse=True)
    elif sort_by == 'prob':
        return sorted(markets, key=lambda x: abs(get_market_probability(x) - 50))
    elif sort_by == 'date':
        return sorted(markets, key=lambda x: get_market_end_date(x))
    return markets


# =============================================================================
# Display Functions
# =============================================================================

def display_markets(markets: list, limit: int = 20, show_id: bool = True, total_in_cache: int = 0, min_vol: float = 0):
    """顯示市場列表"""
    if not markets:
        print("📭 沒有找到符合條件嘅市場")
        return
    
    display = markets[:limit]
    
    print(f"\n{'='*100}")
    print(f"📊 找到 {len(markets)} 個市場 (顯示前 {len(display)} 個)")
    if total_in_cache > 0:
        vol_info = f", 成交量 >= ${min_vol:,.0f}" if min_vol > 0 else ""
        print(f"💾 緩存: {total_in_cache} 個市場{vol_info}")
    print(f"{'='*100}")
    
    for i, m in enumerate(display, 1):
        question = m.get('question', 'Unknown')[:70]
        prob = get_market_probability(m)
        volume = get_market_volume(m)
        end_date = get_market_end_date(m)
        
        # Get market identifiers
        condition_id = m.get('conditionId', m.get('condition_id', m.get('id', '?')))
        
        # 優先用 Event slug (父級)，如果冇就用 Market slug
        event_slug = None
        events = m.get('events', [])
        if events and len(events) > 0:
            event_slug = events[0].get('slug')
        if not event_slug:
            event_slug = m.get('slug', m.get('market_slug', ''))
        
        prob_color = "🟢" if prob > 70 or prob < 30 else "🟡"
        days_left = (end_date - datetime.now(timezone.utc)).days if end_date != datetime.max.replace(tzinfo=timezone.utc) else 999
        
        print(f"\n{i}. {question}...")
        print(f"   {prob_color} Yes: {prob:.0f}% | No: {100-prob:.0f}%")
        print(f"   💰 Volume: ${volume:,.0f}")
        print(f"   ⏰ {days_left} days left" if days_left < 999 else "   ⏰ No deadline")
        
        if show_id:
            print(f"   📋 ID: {condition_id}")
            if event_slug:
                print(f"   🔗 https://polymarket.com/event/{event_slug}")
    
    print(f"\n{'='*100}\n")


def print_distribution_analysis(markets: list):
    """顯示機率分佈分析"""
    if not markets:
        print("📭 沒有市場可分析")
        return
    
    total = len(markets)
    
    # Probability buckets
    buckets = {
        "0-10%": 0,
        "10-20%": 0,
        "20-30%": 0,
        "30-40%": 0,
        "40-50%": 0,
        "50-60%": 0,
        "60-70%": 0,
        "70-80%": 0,
        "80-90%": 0,
        "90-100%": 0
    }
    
    total_volume = 0
    
    for m in markets:
        prob = get_market_probability(m)
        volume = get_market_volume(m)
        total_volume += volume
        
        bucket_idx = min(int(prob // 10), 9)
        bucket_name = list(buckets.keys())[bucket_idx]
        buckets[bucket_name] += 1
    
    print(f"\n{'='*60}")
    print(f"📈 市場分佈分析 ({total} 個市場)")
    print(f"{'='*60}")
    
    print("\n機率分佈:")
    for bucket, count in buckets.items():
        pct = count / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"   {bucket:>8}: {bar:<25} {count:>3} ({pct:>4.1f}%)")
    
    print(f"\n📊 統計:")
    print(f"   總市場數: {total}")
    print(f"   總成交量: ${total_volume:,.0f}")
    print(f"   平均成交量: ${total_volume/total:,.0f}" if total > 0 else "   平均成交量: N/A")
    print(f"\n{'='*60}\n")


# =============================================================================
# Detail Functions
# =============================================================================

def get_market_detail(condition_id: str):
    """獲取市場詳細信息"""
    print(f"\n🔍 獲取市場詳情: {condition_id[:30]}...")
    
    # Get basic info
    market = get_market_info(condition_id)
    
    if not market:
        print("❌ 找不到市場")
        return
    
    question = market.get('question', 'Unknown')
    description = market.get('description', 'N/A')
    
    print(f"\n{'='*80}")
    print(f"📊 {question}")
    print(f"{'='*80}")
    
    print(f"\n📝 描述:")
    print(f"   {description[:200]}..." if len(description) > 200 else f"   {description}")
    
    # Get orderbook for each outcome
    print(f"\n💹 報價:")
    
    try:
        client = get_client(with_creds=False)
        market_data = client.get_market(condition_id)
        tokens = market_data.get('tokens', [])
        
        for t in tokens:
            outcome = t['outcome']
            token_id = t['token_id']
            
            ob = client.get_order_book(token_id)
            
            best_bid = float(ob.bids[0].price) if ob.bids else 0
            best_ask = float(ob.asks[0].price) if ob.asks else 0
            bid_size = float(ob.bids[0].size) if ob.bids else 0
            ask_size = float(ob.asks[0].size) if ob.asks else 0
            spread = best_ask - best_bid if best_ask and best_bid else 0
            
            print(f"\n   {outcome}:")
            print(f"      Best Bid: ${best_bid:.2f} ({bid_size:.0f} shares)")
            print(f"      Best Ask: ${best_ask:.2f} ({ask_size:.0f} shares)")
            print(f"      Spread: ${spread:.4f} ({spread/best_ask*100:.1f}%)" if best_ask else "      Spread: N/A")
    except Exception as e:
        print(f"   ⚠️ 無法獲取 orderbook: {e}")
    
    # Other info
    volume = get_market_volume(market)
    end_date = get_market_end_date(market)
    
    print(f"\n📊 其他資訊:")
    print(f"   成交量: ${volume:,.0f}")
    print(f"   結束日期: {end_date.strftime('%Y-%m-%d') if end_date != datetime.max.replace(tzinfo=timezone.utc) else 'N/A'}")
    print(f"   Condition ID: {condition_id}")
    
    print(f"\n{'='*80}\n")
    
    return market


def get_market_from_url(slug: str):
    """從 URL slug 獲取市場"""
    urls = get_api_urls()
    
    print(f"\n🔍 搜尋: {slug}")
    
    try:
        resp = requests.get(f"{urls['gamma']}/markets", params={"slug": slug}, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            markets = data if isinstance(data, list) else [data]
            
            if markets:
                market = markets[0]
                condition_id = market.get('conditionId', market.get('id'))
                
                if condition_id:
                    return get_market_detail(condition_id)
        
        print("❌ 找不到市場")
        return None
        
    except Exception as e:
        print(f"❌ 搜尋失敗: {e}")
        return None


def parse_polymarket_url(url: str) -> dict:
    """
    解析 Polymarket URL，支援多種格式
    
    支援格式:
    - https://polymarket.com/event/{event_slug}
    - https://polymarket.com/event/{event_slug}/{market_slug}
    - https://polymarket.com/market/{market_slug}
    - {event_slug}/{market_slug} (直接輸入)
    - {slug} (直接輸入)
    
    Returns:
        dict with keys: event_slug, market_slug
    """
    import re
    from urllib.parse import urlparse
    
    result = {"event_slug": None, "market_slug": None}
    
    # 移除多餘空格
    url = url.strip()
    
    # 如果係完整 URL
    if url.startswith("http"):
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        
        # /event/{event_slug} 或 /event/{event_slug}/{market_slug}
        if len(path_parts) >= 2 and path_parts[0] == "event":
            result["event_slug"] = path_parts[1]
            if len(path_parts) >= 3:
                result["market_slug"] = path_parts[2]
        
        # /market/{market_slug}
        elif len(path_parts) >= 2 and path_parts[0] == "market":
            result["market_slug"] = path_parts[1]
    
    # 如果唔係 URL，當作直接輸入
    else:
        parts = url.split("/")
        if len(parts) >= 2:
            result["event_slug"] = parts[0]
            result["market_slug"] = parts[1]
        else:
            result["market_slug"] = url
    
    return result


def get_market_from_full_url(url: str, return_raw: bool = False):
    """
    從完整 Polymarket URL 獲取市場
    
    Args:
        url: 完整 URL 或 slug
        return_raw: 如果 True，返回原始 market dict 而唔係顯示詳情
    
    Returns:
        market dict 或 None
    """
    urls = get_api_urls()
    
    parsed = parse_polymarket_url(url)
    event_slug = parsed.get("event_slug")
    market_slug = parsed.get("market_slug")
    
    print(f"\n🔍 解析 URL...")
    print(f"   Event Slug: {event_slug or 'N/A'}")
    print(f"   Market Slug: {market_slug or 'N/A'}")
    
    markets_found = []
    
    # 策略 1: 用 market_slug 直接搜尋
    if market_slug:
        try:
            resp = requests.get(f"{urls['gamma']}/markets", params={"slug": market_slug}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    markets_found.extend(data)
                elif isinstance(data, dict) and data:
                    markets_found.append(data)
        except Exception as e:
            print(f"   ⚠️ Slug 搜尋失敗: {e}")
    
    # 策略 2: 用 event_slug 搜尋所有 event 下嘅 markets
    if event_slug and not markets_found:
        try:
            # 試用 event slug 作為搜尋關鍵字
            resp = requests.get(
                f"{urls['gamma']}/public-search",
                params={"query": event_slug.replace("-", " "), "limit": 50},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                search_results = data.get('markets', data) if isinstance(data, dict) else data
                
                # 過濾出 event slug 匹配嘅市場
                for m in search_results:
                    m_events = m.get('events', [])
                    for ev in m_events:
                        if ev.get('slug') == event_slug:
                            markets_found.append(m)
                            break
                    
                    # 或者市場本身 slug 匹配
                    if m.get('slug') == market_slug or m.get('slug') == event_slug:
                        if m not in markets_found:
                            markets_found.append(m)
        except Exception as e:
            print(f"   ⚠️ Event 搜尋失敗: {e}")
    
    # 策略 3: 如果有 market_slug，在 cache 中搜尋
    if not markets_found and (market_slug or event_slug):
        print(f"   🔍 嘗試從 cache 搜尋...")
        cache_file = CACHE_FILE.replace(".json", "_active.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    cached_markets = cached.get('markets', [])
                    
                    for m in cached_markets:
                        m_slug = m.get('slug', '')
                        m_events = m.get('events', [])
                        
                        # 匹配 market slug
                        if market_slug and m_slug == market_slug:
                            markets_found.append(m)
                            break
                        
                        # 匹配 event slug
                        for ev in m_events:
                            if ev.get('slug') == event_slug:
                                # 如果指定咗 market_slug，要進一步匹配
                                if market_slug:
                                    if m_slug == market_slug:
                                        markets_found.append(m)
                                        break
                                else:
                                    markets_found.append(m)
            except Exception as e:
                print(f"   ⚠️ Cache 搜尋失敗: {e}")
    
    if not markets_found:
        print("❌ 找不到市場")
        return None
    
    # 如果搵到多個市場（event 下有多個 market）
    if len(markets_found) > 1:
        print(f"\n📊 發現 {len(markets_found)} 個相關市場:\n")
        for i, m in enumerate(markets_found, 1):
            q = m.get('question', 'Unknown')[:70]
            prob = get_market_probability(m)
            vol = get_market_volume(m)
            cid = m.get('conditionId', m.get('id', '?'))[:20]
            print(f"   {i}. {q}")
            print(f"      Yes: {prob:.0f}% | Vol: ${vol:,.0f} | ID: {cid}...")
        
        # 如果有指定 market_slug，用佢過濾
        if market_slug:
            exact_match = [m for m in markets_found if m.get('slug') == market_slug]
            if exact_match:
                markets_found = exact_match
                print(f"\n   ✅ 精確匹配: {market_slug}")
    
    # 返回第一個匹配
    market = markets_found[0]
    condition_id = market.get('conditionId', market.get('id'))
    
    if return_raw:
        return market
    
    if condition_id:
        return get_market_detail(condition_id)
    
    return None


# =============================================================================
# Main Entry
# =============================================================================

def main():
    # 預處理：如果第一個參數唔係 flag 或 subcommand，當作 query
    # 支持: search.py "Trump" 同 search.py -q "Trump"
    import sys
    
    subcommands = ['detail', 'url', 'refresh']
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # 如果第一個參數唔係 flag (唔以 - 開頭) 且唔係 subcommand
        if not first_arg.startswith('-') and first_arg not in subcommands:
            # 插入 -q flag 嚟處理 positional query
            sys.argv.insert(1, '-q')
    
    parser = argparse.ArgumentParser(
        description="Polymarket Search - 統一市場搜尋",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法範例:
  python search.py "Trump"                    # 基礎搜尋 (positional)
  python search.py -q "Trump"                 # 基礎搜尋 (flag)
  python search.py "NBA" --limit 20           # 指定數量
  python search.py --prob 80:20               # 機率 20-80%
  python search.py --min-vol 50000            # 最低 $50k 成交量
  python search.py --urgent 7                 # 7 日內截止
  python search.py "crypto" --sort volume     # 按成交量排序
  python search.py --analyze                  # 全市場分佈分析
  python search.py detail <ID>                # 市場詳情
  python search.py url <slug>                 # 從 URL slug 獲取
  python search.py refresh                    # 強制刷新緩存
        """
    )
    
    # Search options (before subparsers)
    parser.add_argument("-q", "--query", help="搜尋關鍵字")
    parser.add_argument("--limit", "-l", type=int, default=20, help="結果數量")
    parser.add_argument("--prob", help="機率範圍 (e.g., 80:20)")
    parser.add_argument("--min-vol", type=float, help="最低成交量")
    parser.add_argument("--urgent", type=int, metavar="DAYS", help="N 日內截止")
    parser.add_argument("--sort", choices=["volume", "prob", "date"], default="volume", help="排序方式")
    parser.add_argument("--analyze", action="store_true", help="顯示分佈分析")
    parser.add_argument("--json", action="store_true", help="JSON 格式輸出")
    parser.add_argument("--no-cache", action="store_true", help="不使用緩存")
    parser.add_argument("--fast", action="store_true", help="快速模式 (只獲取最新市場)")
    parser.add_argument("-c", "--category", choices=list(CATEGORIES.keys()), 
                        help=f"按類別搜尋: {', '.join(CATEGORIES.keys())}")
    
    # Time range filters
    parser.add_argument("--closed", action="store_true", help="只顯示已結束嘅市場")
    parser.add_argument("--active", action="store_true", help="只顯示活躍中嘅市場（預設）")
    parser.add_argument("--date-from", help="結束日期範圍 - 開始 (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="結束日期範圍 - 結束 (YYYY-MM-DD)")
    parser.add_argument("--scan-min-vol", type=float, default=10000, help="掃描時最低成交量門檻 (預設 $10,000)")
    
    # Insider detection
    parser.add_argument("--scan-insider", action="store_true", help="批量掃描 insider activity")
    parser.add_argument("--insider-price-threshold", "-ip", type=float, default=10.0, 
                       help="Insider 掃描: 價格變化門檻 (percent, 預設: 10)")
    parser.add_argument("--insider-trade-threshold", "-it", type=float, default=5000, 
                       help="Insider 掃描: 大額交易門檻 (USD, 預設: 5000)")
    parser.add_argument("--insider-min-risk", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], 
                       default="MEDIUM", help="只顯示此風險等級以上的市場 (預設: MEDIUM)")
    
    # Optional subcommands (不會衝突 query)
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Detail command
    detail_parser = subparsers.add_parser("detail", help="市場詳情")
    detail_parser.add_argument("condition_id", help="市場 Condition ID")
    
    # URL command
    url_parser = subparsers.add_parser("url", help="從完整 URL 或 slug 獲取")
    url_parser.add_argument("url_or_slug", help="完整 Polymarket URL 或 slug (e.g., https://polymarket.com/event/xxx/yyy)")
    
    # Refresh command
    subparsers.add_parser("refresh", help="強制刷新緩存")

    args = parser.parse_args()
    
    # === 處理子命令 ===
    if args.command == "detail":
        get_market_detail(args.condition_id)
        return
    
    if args.command == "url":
        get_market_from_full_url(args.url_or_slug)
        return
    
    if args.command == "refresh":
        fetch_all_markets(use_cache=False)
        print("✅ 緩存已刷新")
        return
    
    # === 處理搜尋（預設行為）===
    # 只有明確指定 --closed 時才獲取已結束市場
    # 日期範圍篩選會在獲取後進行，唔需要預先判斷
    include_closed = args.closed
    
    # Fetch all markets first (Incremental Update logic is inside)
    all_cached_markets = fetch_all_markets(
        use_cache=not args.no_cache, 
        include_closed=include_closed,
        fast=args.fast,
        min_volume=args.scan_min_vol
    )
    total_in_cache = len(all_cached_markets)
    markets = all_cached_markets
    
    # Apply status filter (active/closed)
    if args.closed:
        markets = filter_active_or_closed(markets, 'closed')
    elif args.active:
        markets = filter_active_or_closed(markets, 'active')
    
    # Apply date range filter
    if args.date_from or args.date_to:
        markets = filter_by_date_range(markets, args.date_from, args.date_to)
    
    # Apply category filter
    if args.category:
        markets = filter_by_category(markets, args.category)
    
    # Apply query filter
    if args.query:
        markets = filter_by_query(markets, args.query)
    
    # Apply other filters
    if args.prob:
        prob_range = parse_prob_range(args.prob)
        markets = filter_by_probability(markets, prob_range)
    
    if args.min_vol:
        markets = filter_by_volume(markets, args.min_vol)
    
    if args.urgent:
        markets = filter_urgent(markets, args.urgent)
    
    # Sort
    markets = sort_markets(markets, args.sort)
    
    # === Insider Detection Scan ===
    if args.scan_insider:
        print(f"\n🕵️  開始批量掃描 Insider Activity...")
        print(f"   掃描範圍: {len(markets)} 個市場")
        print(f"   價格門檻: {args.insider_price_threshold}%")
        print(f"   交易門檻: ${args.insider_trade_threshold:,.0f}")
        print(f"   最低風險: {args.insider_min_risk}")
        print("="*80 + "\n")
        
        # Import insider detection function
        import sys
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        from analyze import detect_insider_activity
        
        # Risk level ordering
        risk_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        min_risk_level = risk_levels[args.insider_min_risk]
        
        insider_results = []
        
        for i, market in enumerate(markets[:args.limit], 1):
            condition_id = market.get('conditionId', market.get('condition_id', market.get('id')))
            question = market.get('question', 'Unknown')[:60]
            
            print(f"\n[{i}/{min(len(markets), args.limit)}] 掃描: {question}...")
            print("-" * 80)
            
            try:
                result = detect_insider_activity(
                    condition_id,
                    price_threshold=args.insider_price_threshold,
                    trade_threshold=args.insider_trade_threshold
                )
                
                if result and 'insider_risk' in result:
                    risk_info = result['insider_risk']
                    risk_level = risk_info.get('level', 'LOW')
                    risk_score = risk_info.get('score', 0)
                    
                    # Filter by minimum risk level
                    if risk_levels.get(risk_level, 0) >= min_risk_level:
                        insider_results.append({
                            'market': question,
                            'condition_id': condition_id,
                            'risk_level': risk_level,
                            'risk_score': risk_score,
                            'suspicious_events': len(result.get('suspicious_events', [])),
                            'large_trades': len(result.get('large_trades', [])),
                            'price_spikes': len(result.get('price_spikes', []))
                        })
                
            except Exception as e:
                print(f"   ⚠️  掃描失敗: {e}")
                continue
        
        # Display summary
        print("\n" + "="*80)
        print(f"🕵️  Insider Activity 掃描結果")
        print("="*80 + "\n")
        
        if insider_results:
            # Sort by risk score
            insider_results.sort(key=lambda x: x['risk_score'], reverse=True)
            
            print(f"發現 {len(insider_results)} 個市場符合風險門檻 (>= {args.insider_min_risk}):\n")
            
            for i, r in enumerate(insider_results, 1):
                risk_emoji = "🚨" if r['risk_level'] == "CRITICAL" else "⚠️" if r['risk_level'] == "HIGH" else "⚡" if r['risk_level'] == "MEDIUM" else "✅"
                
                print(f"{i}. {risk_emoji} {r['market']}")
                print(f"   風險等級: {r['risk_level']} (評分: {r['risk_score']}/100)")
                print(f"   可疑事件: {r['suspicious_events']} | 大額交易: {r['large_trades']} | 價格突變: {r['price_spikes']}")
                print(f"   ID: {r['condition_id']}")
                print()
        else:
            print(f"✅ 未發現符合 {args.insider_min_risk} 風險等級的市場\n")
        
        print("="*80 + "\n")
        return  # Skip normal display after insider scan
    
    # Output
    if args.analyze:
        print_distribution_analysis(markets)
    
    if args.json:
        results = []
        for m in markets[:args.limit]:
            # 優先用 Event slug (父級)，如果冇就用 Market slug
            event_slug = None
            events = m.get('events', [])
            if events and len(events) > 0:
                event_slug = events[0].get('slug')
            if not event_slug:
                event_slug = m.get('slug', m.get('market_slug', ''))
            
            results.append({
                "question": m.get('question'),
                "conditionId": m.get('conditionId'),
                "slug": event_slug,
                "probability": get_market_probability(m),
                "volume": get_market_volume(m)
            })
        print(json.dumps(results, indent=2))
    else:
        display_markets(markets, limit=args.limit, total_in_cache=total_in_cache, min_vol=args.scan_min_vol)


if __name__ == "__main__":
    main()
