#!/usr/bin/env python3
"""
Polymarket Whale & Smart Money Analyzer
Fixed version of analyze_market.py with corrected ROI and Whale definitions.

Fixes:
1. ROI Calculation: Uses (Current Value + Realized Return - Total Invested) / Total Invested
   to avoid inflated ROI when selling.
2. Whale Definition: Uses Position Value (Size * Price) instead of Share Count
   to correctly identify large capital holders vs cheap share hoarders.
"""

import sys
import json
import requests
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

BASE_URL = "https://data-api.polymarket.com"
GAMMA_URL = "https://gamma-api.polymarket.com"

def extract_event_slug(url: str) -> str:
    """Extract event slug from Polymarket URL or return market ID if provided."""
    if not url: return ""
    if '/' not in url and not url.startswith('http'):
        return url
    if url.startswith('0x') and len(url) == 66:
        return url
    if url.isdigit():
        return f"market_id:{url}"
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if 'event' in path_parts:
        idx = path_parts.index('event')
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]
    return url

def resolve_input_to_condition_id(input_str: str) -> str:
    """
    將用戶輸入（網址、數字 ID、或 Condition ID）轉換為標準的 Condition ID。
    """
    if not input_str:
        return ""
    
    # 1. 已經係 Condition ID (0x... 66 chars)
    if input_str.startswith('0x') and len(input_str) == 66:
        return input_str
        
    # 2. 係數字 Market ID
    if input_str.isdigit():
        print(f"  🔍 偵測到數字 ID: {input_str}，正在查詢 Condition ID...", file=sys.stderr)
        try:
            resp = requests.get(f"{GAMMA_URL}/markets?id={input_str}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    cid = data[0].get('conditionId')
                    if cid:
                        print(f"  ✅ 轉換成功: {cid[:10]}...", file=sys.stderr)
                        return cid
        except:
            pass
            
    # 3. 係網址或 Slug
    try:
        # Avoid recursion, just use parts of logic
        slug = input_str
        if '/' in input_str:
            parsed = urlparse(input_str)
            path_parts = parsed.path.strip('/').split('/')
            if 'event' in path_parts:
                idx = path_parts.index('event')
                if idx + 1 < len(path_parts):
                    slug = path_parts[idx + 1]
        
        if slug:
            print(f"  🔍 偵測到 Slug/URL: {slug}，正在獲取第一個市場...", file=sys.stderr)
            resp = requests.get(f"{GAMMA_URL}/events?slug={slug}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                event = data[0] if isinstance(data, list) else data
                markets = event.get('markets', [])
                if markets:
                    cid = markets[0].get('conditionId')
                    print(f"  ✅ 轉換成功: {cid[:10]}...", file=sys.stderr)
                    return cid
    except:
        pass
        
    return input_str

def load_markets_from_cache():
    """Load markets from polymarket-trader cache if available."""
    try:
        # Try to load from polymarket-trader cache
        cache_path = "/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt/scripts/all_markets_cache.json"
        with open(cache_path, 'r') as f:
            markets = json.load(f)
        print(f"  Loaded {len(markets)} markets from cache", file=sys.stderr)
        return markets
    except Exception as e:
        print(f"  Could not load cache: {e}", file=sys.stderr)
        return None

def get_event_markets(event_slug: str) -> list:
    """Get all markets for an event or return single market if market ID provided."""
    if event_slug.startswith('market_id:'):
        market_id = event_slug.replace('market_id:', '')
        resp = requests.get(f"{GAMMA_URL}/markets/{market_id}")
        return [resp.json()] if resp.status_code == 200 else []

    if event_slug.startswith('0x') and len(event_slug) == 66:
        # First try to find in local cache
        cached_markets = load_markets_from_cache()
        if cached_markets:
            for market in cached_markets:
                if market.get('condition_id') == event_slug:
                    print(f"  Found market in cache: {market.get('question', 'N/A')}", file=sys.stderr)
                    # Convert cache format to expected format
                    converted_market = {
                        'id': market.get('id', ''),
                        'conditionId': market.get('condition_id', ''),
                        'question': market.get('question', ''),
                        'description': market.get('question', ''),
                        'endDate': market.get('end_date_iso', ''),
                        'volume': market.get('volume', 0),
                        'active': market.get('active', True),
                        'clobTokenIds': market.get('token_ids', []),
                        'outcomePrices': [str(market.get('chance', 0)), str(1 - market.get('chance', 0))]
                    }
                    return [converted_market]

        # If not found in cache, try API
        print(f"  Searching by condition_id: {event_slug}", file=sys.stderr)
        resp = requests.get(f"{GAMMA_URL}/markets", params={"condition_id": event_slug})
        if resp.status_code == 200:
            markets = resp.json()
            if markets:
                print(f"  Found {len(markets)} market(s) via API", file=sys.stderr)
                return markets
            else:
                print(f"  No markets found for condition_id via API", file=sys.stderr)
        else:
            print(f"  Error searching by condition_id: {resp.status_code}", file=sys.stderr)

        # Fallback: treat as market ID
        print(f"  Trying as market ID...", file=sys.stderr)
        resp = requests.get(f"{GAMMA_URL}/markets/{event_slug}")
        if resp.status_code == 200:
            market = resp.json()
            print(f"  Found market by ID", file=sys.stderr)
            return [market]
        else:
            print(f"  Error as market ID: {resp.status_code}", file=sys.stderr)
        return []

    resp = requests.get(f"{GAMMA_URL}/events", params={"slug": event_slug})
    if resp.status_code == 200:
        events = resp.json()
        if events:
            return events[0].get('markets', [])
    resp = requests.get(f"{GAMMA_URL}/markets", params={"slug": event_slug})
    return resp.json() if resp.status_code == 200 else []

def get_positions(condition_id: str) -> list:
    """Get all positions for a market."""
    positions = []
    offset = 0
    limit = 100
    print(f"  Fetching positions...", end="", flush=True, file=sys.stderr)
    while True:
        resp = requests.get(f"{BASE_URL}/positions", params={"market": condition_id, "limit": limit, "offset": offset})
        if resp.status_code != 200: break
        data = resp.json()
        if not data: break
        positions.extend(data)
        print(".", end="", flush=True, file=sys.stderr)
        if len(data) < limit: break
        offset += limit
    print(f" Done ({len(positions)})", file=sys.stderr)
    return positions

def get_trades(condition_id: str, limit: int = 1000) -> list:
    """Get recent trades for a market."""
    print(f"  Fetching trades...", end="", flush=True, file=sys.stderr)
    resp = requests.get(f"{BASE_URL}/trades", params={"market": condition_id, "limit": limit})
    trades = resp.json() if resp.status_code == 200 else []
    print(f" Done ({len(trades)})", file=sys.stderr)
    return trades

def get_token_holders(token_id: str) -> list:
    """Get holders for a specific token."""
    holders = []
    offset = 0
    limit = 100
    while True:
        resp = requests.get(f"{BASE_URL}/holders", params={"token": token_id, "limit": limit, "offset": offset})
        if resp.status_code != 200: break
        data = resp.json()
        if not data: break
        holders.extend(data)
        if len(data) < limit: break
        offset += limit
    return holders

def calculate_roi_and_smart_money(wallet_trades: list, current_prices: dict) -> dict:
    """
    Calculate ROI for each wallet with proper Total Investment tracking.
    Fixes previous logic error where selling reduced cost basis to near zero, inflating ROI.
    """
    # Structure: wallet -> {yes: {invested, shares, realized}, no: {invested, shares, realized}, metadata}
    wallet_metrics = defaultdict(lambda: {
        "yes": {"invested": 0, "shares": 0, "realized": 0},
        "no": {"invested": 0, "shares": 0, "realized": 0},
        "metadata": {
            "trade_count": 0,
            "first_trade_time": None,
            "last_trade_time": None
        }
    })

    for trade in wallet_trades:
        wallet = trade.get('proxyWallet', '') or trade.get('maker', '') or trade.get('taker', '')
        if not wallet:
            continue

        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0))
        side = trade.get('side', '').lower()
        timestamp = trade.get('timestamp', '')

        # Identify outcome
        outcome_index = trade.get('outcomeIndex')
        outcome_str = trade.get('outcome', '').upper()

        if outcome_index is not None:
            outcome_key = 'yes' if str(outcome_index) == '0' else 'no'
        elif outcome_str in ['YES', 'NO']:
            outcome_key = outcome_str.lower()
        else:
            outcome_key = 'yes' # Default

        # Update timing
        metadata = wallet_metrics[wallet]["metadata"]
        if timestamp:
            if not metadata["first_trade_time"] or timestamp < metadata["first_trade_time"]:
                metadata["first_trade_time"] = timestamp
            if not metadata["last_trade_time"] or timestamp > metadata["last_trade_time"]:
                metadata["last_trade_time"] = timestamp

        metadata["trade_count"] += 1

        # Update metrics
        outcome_metrics = wallet_metrics[wallet][outcome_key]

        if side == 'buy':
            # Add to total invested amount
            outcome_metrics["invested"] += size * price
            outcome_metrics["shares"] += size
        elif side == 'sell':
            # Add to realized return
            outcome_metrics["realized"] += size * price
            outcome_metrics["shares"] -= size

    # Calculate ROI
    smart_money_wallets = []

    for wallet, outcomes in wallet_metrics.items():
        yes_invested = outcomes['yes']['invested']
        no_invested = outcomes['no']['invested']
        
        yes_realized = outcomes['yes']['realized']
        no_realized = outcomes['no']['realized']
        
        yes_shares = outcomes['yes']['shares']
        no_shares = outcomes['no']['shares']

        total_invested = yes_invested + no_invested

        # Filter out tiny traders
        if total_invested < 10: 
            continue

        # Current Value
        current_yes_value = yes_shares * current_prices.get('yes', 0)
        current_no_value = no_shares * current_prices.get('no', 0)
        current_total_value = current_yes_value + current_no_value

        # Total Return = Realized + Current Value
        total_return = (yes_realized + no_realized) + current_total_value
        
        # Net Profit
        net_profit = total_return - total_invested
        
        # ROI
        roi = net_profit / total_invested if total_invested > 0 else 0

        # Smart Money Logic
        is_smart_money = False
        smart_reason = ""

        if roi > 2.0 and total_invested > 100:
            is_smart_money = True
            smart_reason = "HIGH_ROI"
        elif total_invested > 10000 and roi > 0.5:
            is_smart_money = True
            smart_reason = "LARGE_PROFITABLE_INVESTOR"
        elif outcomes["metadata"]["trade_count"] > 20 and roi > 0.3:
            is_smart_money = True
            smart_reason = "ACTIVE_PROFITABLE_TRADER"

        if is_smart_money:
            smart_money_wallets.append({
                "wallet": wallet,
                "roi_percentage": round(roi * 100, 2),
                "total_investment": round(total_invested, 2),
                "current_value": round(current_total_value, 2),
                "realized_pnl": round(net_profit, 2), # This is total PnL
                "trade_count": outcomes["metadata"]["trade_count"],
                "smart_reason": smart_reason
            })

    return {
        "smart_money_wallets": sorted(smart_money_wallets, key=lambda x: x['roi_percentage'], reverse=True),
        "total_smart_money": len(smart_money_wallets)
    }

def analyze_wallet_distribution(positions: list, trades: list = None, current_prices: dict = None) -> dict:
    """
    Analyze wallet distribution using VALUE instead of SHARES.
    """
    if not positions:
        return {"error": "No positions found"}

    wallet_stats = defaultdict(lambda: {"yes_value": 0, "no_value": 0, "total_value": 0, "yes_shares": 0, "no_shares": 0})

    # Use current prices to calculate value
    yes_price = current_prices.get('yes', 0) if current_prices else 0.5
    no_price = current_prices.get('no', 0) if current_prices else 0.5

    for pos in positions:
        wallet = pos.get('user', pos.get('proxyWallet', 'unknown'))
        size = float(pos.get('size', 0))
        outcome = pos.get('outcome', '').lower()

        if 'yes' in outcome or outcome == 'yes':
            value = size * yes_price
            wallet_stats[wallet]['yes_value'] += value
            wallet_stats[wallet]['yes_shares'] += size
        else:
            value = size * no_price
            wallet_stats[wallet]['no_value'] += value
            wallet_stats[wallet]['no_shares'] += size
        
        wallet_stats[wallet]['total_value'] += value

    # Sort by TOTAL VALUE
    sorted_wallets = sorted(
        wallet_stats.items(),
        key=lambda x: x[1]['total_value'],
        reverse=True
    )

    total_market_value = sum(w[1]['total_value'] for w in sorted_wallets)

    whales = []
    for wallet, data in sorted_wallets[:20]:
        pct = (data['total_value'] / total_market_value * 100) if total_market_value > 0 else 0
        
        # Determine direction based on VALUE
        direction = "YES" if data['yes_value'] > data['no_value'] else "NO"

        whale_type = "MEGA_WHALE" if pct > 10 else ("WHALE" if pct > 5 else ("LARGE_HOLDER" if pct > 1 else "REGULAR"))

        whales.append({
            "wallet": wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet,
            "full_wallet": wallet,
            "total_value": round(data['total_value'], 2),
            "direction": direction,
            "pct_of_market": round(pct, 2),
            "whale_type": whale_type
        })

    # Concentration analysis
    top_10_pct = sum(w['pct_of_market'] for w in whales[:10])

    # Smart money analysis if trades data available
    smart_money_analysis = {}
    if trades and current_prices:
        smart_money_analysis = calculate_roi_and_smart_money(trades, current_prices)

    return {
        "total_wallets": len(sorted_wallets),
        "total_market_value": round(total_market_value, 2),
        "top_10_concentration": round(top_10_pct, 2),
        "whales": whales,
        "insider_risk": {
            "high_concentration": top_10_pct > 50,
            "few_large_wallets": len([w for w in whales if w['pct_of_market'] > 5]) >= 3,
            "mega_whales_present": len([w for w in whales if w['whale_type'] == 'MEGA_WHALE']) > 0
        },
        "smart_money_analysis": smart_money_analysis
    }

def analyze_trades(trades: list) -> dict:
    """Analyze recent trade patterns and detect bot clusters."""
    if not trades:
        return {"error": "No trades found"}

    large_trades = []
    wallet_volumes = defaultdict(lambda: {"buy": 0, "sell": 0, "total": 0, "trades": 0})

    # === 新增：用來儲存時間戳集群 ===
    timestamp_clusters = defaultdict(list)

    for trade in trades:
        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0))
        value = size * price
        side = trade.get('side', '').upper()
        wallet = trade.get('proxyWallet', '') or trade.get('maker', '') or trade.get('taker', '')

        # 獲取時間戳
        ts = trade.get('timestamp')

        if wallet:
            if side == 'BUY':
                wallet_volumes[wallet]['buy'] += value
            else:
                wallet_volumes[wallet]['sell'] += value
            wallet_volumes[wallet]['total'] += value
            wallet_volumes[wallet]['trades'] += 1

            # === 新增：記錄每個時間戳的錢包活動 ===
            if ts:
                timestamp_clusters[ts].append(wallet)

        if value > 500:
            large_trades.append({
                "timestamp": trade.get('timestamp', ''),
                "wallet": wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet,
                "side": side,
                "value": round(value, 2)
            })

    sorted_wallets = sorted(wallet_volumes.items(), key=lambda x: x[1]['total'], reverse=True)
    total_volume = sum(w[1]['total'] for w in sorted_wallets)

    top_traders = []
    for wallet, data in sorted_wallets[:15]:
        pct = (data['total'] / total_volume * 100) if total_volume > 0 else 0
        net_direction = "BUYER" if data['buy'] > data['sell'] else "SELLER"
        top_traders.append({
            "wallet": wallet,  # 顯示完整錢包地址
            "total_volume": round(data['total'], 2),
            "pct_of_volume": round(pct, 2),
            "net_direction": net_direction
        })

    # === 新增：分析疑似機械人集群 ===
    suspicious_clusters = []
    for ts, wallets in timestamp_clusters.items():
        unique_wallets = list(set(wallets))
        # 如果同一秒鐘有 2 個或以上唔同嘅錢包交易，視為嫌疑集群
        if len(unique_wallets) >= 2:
            suspicious_clusters.append({
                "timestamp": ts,
                "count": len(unique_wallets),
                "wallets": unique_wallets
            })

    # 按錢包數量由多到少排序
    suspicious_clusters.sort(key=lambda x: x['count'], reverse=True)

    return {
        "total_volume": round(total_volume, 2),
        "top_traders": top_traders,
        "large_trades": large_trades[:10],
        "suspicious_clusters": suspicious_clusters[:5]  # 只返回前 5 個最大集群
    }

def get_market_info_batch(market_ids: list) -> dict:
    """
    批量獲取市場資訊，減少 API 請求次數
    Returns: {market_id: {question, end_date, resolved, outcome, ...}}
    """
    market_cache = {}
    unique_ids = list(set(market_ids))
    
    # 先嘗試從本地 cache 載入
    cached_markets = load_markets_from_cache()
    cached_by_condition = {}
    if cached_markets:
        for m in cached_markets:
            cid = m.get('condition_id', '')
            if cid:
                cached_by_condition[cid] = m
    
    for market_id in unique_ids:
        if not market_id:
            continue
            
        # 先查本地 cache
        if market_id in cached_by_condition:
            m = cached_by_condition[market_id]
            market_cache[market_id] = {
                'question': m.get('question', 'Unknown'),
                'resolved': m.get('resolved', False) or m.get('closed', False),
                'outcome': m.get('outcome', None),
                'end_date': m.get('end_date_iso', ''),
                'volume': m.get('volume', 0)
            }
            continue
        
        # 否則查 API
        try:
            resp = requests.get(f"{GAMMA_URL}/markets", params={"condition_id": market_id}, timeout=5)
            if resp.status_code == 200:
                markets = resp.json()
                if markets:
                    m = markets[0]
                    market_cache[market_id] = {
                        'question': m.get('question', 'Unknown'),
                        'resolved': m.get('resolved', False) or m.get('closed', False),
                        'outcome': m.get('outcome', None),
                        'end_date': m.get('endDate', ''),
                        'volume': float(m.get('volume', 0)) if m.get('volume') else 0
                    }
                    continue
        except:
            pass
        
        # 最後 fallback
        market_cache[market_id] = {
            'question': 'Unknown Market',
            'resolved': False,
            'outcome': None,
            'end_date': '',
            'volume': 0
        }
    
    return market_cache

def get_global_position_count(wallet_address: str) -> int:
    """Fetch total count of active positions from API."""
    try:
        resp = requests.get(f"{BASE_URL}/positions", params={"user": wallet_address, "limit": 1000}, timeout=5)
        if resp.status_code == 200:
            return len(resp.json())
    except:
        pass
    return 0

def inspect_wallet_history(wallet_address: str, max_trades: int = 5000, load_all: bool = False):
    """
    起底功能 v4.0：完整錢包分析 (Global + Local)
    
    Features:
    - [Global] 官方計算的總資產與歷史總盈虧 (Lifetime PnL)
    - [Local] 最近 N 筆交易的短期策略分析
    - 快速掃描總交易數
    - 智能載入
    """
    print(f"\n🕵️‍♂️ 正在起底錢包: {wallet_address} ...", file=sys.stderr)

    # ========== STEP 0: Get Global Stats ==========
    print(f"  📊 Fetching global positions...", end="", flush=True, file=sys.stderr)
    global_pos_count = get_global_position_count(wallet_address)
    print(f" Done ({global_pos_count} found)", file=sys.stderr)
    url = f"{BASE_URL}/activity"
    
    # ========== STEP 1: Smart Binary Search to find EXACT total trades ==========
    print(f"  📊 Scanning for exact total trades...", end="", flush=True, file=sys.stderr)
    
    def check_offset(idx):
        try:
            r = requests.get(url, params={"user": wallet_address, "limit": 1, "offset": idx, "type": "TRADE"}, timeout=5)
            return r.status_code == 200 and len(r.json()) > 0
        except:
            return False

    # 1. Find the upper bound first (doubling)
    low = 0
    high = 1000
    while check_offset(high):
        low = high
        high *= 2
        if high > 5000000: # Increased safety cap to 5M
            break
            
    # 2. Binary search between low and high
    exact_total = 0
    while low <= high:
        mid = (low + high) // 2
        if check_offset(mid):
            exact_total = mid + 1
            low = mid + 1
        else:
            high = mid - 1
    
    print(f" Done ({exact_total} found)", file=sys.stderr)
    estimated_total = exact_total
    
    # ========== STEP 2: Decide how many to load ==========
    if load_all:
        actual_max = 100000  # Safety limit
        print(f"  ⚠️  Loading ALL trades (this may take a while)...", file=sys.stderr)
    else:
        actual_max = max_trades
        if estimated_total > actual_max:
            print(f"  💡 Loading recent {actual_max} trades only (use --all for complete history)", file=sys.stderr)
    
    # ========== STEP 3: Pagination to load trades ==========
    activities = []
    offset = 0
    limit = 500  # API max per request
    
    print(f"  Fetching", end="", flush=True, file=sys.stderr)
    while len(activities) < actual_max:
        params = {
            "user": wallet_address,
            "limit": limit,
            "offset": offset,
            "type": "TRADE"
        }
        
        try:
            resp = requests.get(url, params=params)
            if resp.status_code != 200:
                break
            
            data = resp.json()
            if not data:
                break
            
            activities.extend(data)
            print(".", end="", flush=True, file=sys.stderr)
            
            # If we got less than the limit, we've reached the end
            if len(data) < limit:
                break
            
            offset += limit
        except Exception as e:
            print(f"\n  Error fetching: {e}", file=sys.stderr)
            break
    
    total_available = estimated_total if estimated_total > len(activities) else len(activities)
    print(f" Done ({len(activities)} loaded / ~{total_available} total)", file=sys.stderr)

    if not activities:
        print(json.dumps({"error": "No history found"}))
        return

    # API 已直接返回 title, conditionId, outcome 等資訊！
    # 唔使另外 fetch market info

    # ========== 統計數據結構 ==========
    # 每個市場的交易統計 - 用 conditionId 作為 key
    market_stats = defaultdict(lambda: {
        'question': 'Unknown',
        'slug': '',
        'buys': [],        # [(size, price, timestamp), ...]
        'sells': [],
        'total_bought': 0,  # 買入總股數
        'total_sold': 0,    # 賣出總股數
        'cost_basis': 0,    # 買入成本 (USDC)
        'sell_revenue': 0,  # 賣出收入 (USDC)
        'resolved': False,
        'outcome': None,
        'bet_outcome': None,  # 我們押注的 outcome (Yes/No)
        'first_trade': None,
        'last_trade': None
    })

    total_trades = 0
    total_buy_volume = 0
    total_sell_volume = 0

    for act in activities:
        # 使用正確的欄位名稱
        market_id = act.get('conditionId', '')
        title = act.get('title', 'Unknown Market')
        slug = act.get('slug', '')
        ts = int(act.get('timestamp', 0))
        side = act.get('side', '').upper()
        size = float(act.get('size', 0))
        price = float(act.get('price', 0)) if act.get('price') else 0
        usdc_size = float(act.get('usdcSize', 0)) if act.get('usdcSize') else size * price
        bet_outcome = act.get('outcome', '')  # Yes 或 No

        if not market_id:
            continue

        total_trades += 1
        stats = market_stats[market_id]

        # 更新市場資訊 (直接從 activity 獲取)
        if title and title != 'Unknown Market':
            stats['question'] = title
        stats['slug'] = slug
        stats['bet_outcome'] = bet_outcome

        # 更新時間範圍
        if not stats['first_trade'] or ts < stats['first_trade']:
            stats['first_trade'] = ts
        if not stats['last_trade'] or ts > stats['last_trade']:
            stats['last_trade'] = ts

        # 記錄交易 (用 usdcSize 因為更準確)
        if side == 'BUY':
            stats['buys'].append((size, price, ts))
            stats['total_bought'] += size
            stats['cost_basis'] += usdc_size
            total_buy_volume += usdc_size
        elif side == 'SELL':
            stats['sells'].append((size, price, ts))
            stats['total_sold'] += size
            stats['sell_revenue'] += usdc_size
            total_sell_volume += usdc_size

    # ========== 計算 PnL ==========
    market_results = []
    total_realized_pnl = 0
    total_unrealized_pnl = 0
    wins = 0
    losses = 0
    
    for market_id, stats in market_stats.items():
        question = stats['question'][:50] + "..." if len(stats['question']) > 50 else stats['question']
        
        cost = stats['cost_basis']
        revenue = stats['sell_revenue']
        shares_held = stats['total_bought'] - stats['total_sold']
        
        # 計算已實現盈虧
        # 假設 FIFO: 先買的先賣
        if stats['total_sold'] > 0 and stats['total_bought'] > 0:
            # 平均買入成本
            avg_buy_price = cost / stats['total_bought'] if stats['total_bought'] > 0 else 0
            # 已賣出部分的成本
            sold_cost = stats['total_sold'] * avg_buy_price
            realized_pnl = revenue - sold_cost
        else:
            realized_pnl = 0
        
        # 判斷勝負 (基於已結算或已平倉的交易)
        trade_status = "OPEN"
        if stats['resolved']:
            trade_status = "RESOLVED"
            # 如果市場已結算，unrealized 變成 realized
            # 假設結算價值為 1 (如果贏) 或 0 (如果輸)
            if stats['outcome']:
                # outcome 可能是 "Yes" 或 "No"
                # 需要知道我們持有的是 Yes 還是 No 才能判斷
                pass
        elif shares_held <= 0.01:  # 已平倉
            trade_status = "CLOSED"
            if realized_pnl > 0:
                wins += 1
            elif realized_pnl < 0:
                losses += 1
        else:
            # 估算未實現盈虧（假設當前價格為 0.5 作為保守估計）
            estimated_value = shares_held * 0.5
            unrealized_pnl = estimated_value - (shares_held * (cost / stats['total_bought']) if stats['total_bought'] > 0 else 0)
            total_unrealized_pnl += unrealized_pnl

        total_realized_pnl += realized_pnl

        market_results.append({
            'market_id': market_id,
            'question': question,
            'total_bought': stats['total_bought'],
            'total_sold': stats['total_sold'],
            'shares_held': shares_held,
            'cost_basis': cost,
            'sell_revenue': revenue,
            'realized_pnl': realized_pnl,
            'status': trade_status,
            'trade_count': len(stats['buys']) + len(stats['sells']),
            'first_trade': stats['first_trade'],
            'last_trade': stats['last_trade']
        })

    # 按 realized PnL 排序
    market_results.sort(key=lambda x: x['realized_pnl'], reverse=True)

    # ========== 輸出報告 ==========
    print("\n" + "="*120)
    print(f"🕵️‍♂️ 錢包深度分析 (Wallet Analysis): {wallet_address}")
    print("="*120)
    
    # 總覽
    print("\n📊 **總體統計 (Summary)**")
    print("-"*60)
    print(f"  📈 總交易次數: {total_trades} (已載入) / ~{total_available} (總數)")
    print(f"  💰 總買入金額: ${total_buy_volume:,.2f}")
    print(f"  💸 總賣出金額: ${total_sell_volume:,.2f}")
    print(f"  📍 參與市場數: {len(market_stats)}")
    
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"\n  ✅ 已平倉勝場: {wins}")
    print(f"  ❌ 已平倉敗場: {losses}")
    print(f"  🎯 勝率 (已平倉): {win_rate:.1f}%")
    
    pnl_color = "🟢" if total_realized_pnl >= 0 else "🔴"
    print(f"\n  {pnl_color} 已實現盈虧: ${total_realized_pnl:+,.2f}")
    print(f"  ⏳ 未實現盈虧 (估算): ${total_unrealized_pnl:+,.2f}")
    print(f"  📊 總盈虧 (估算): ${(total_realized_pnl + total_unrealized_pnl):+,.2f}")

    # 每個市場的詳細資訊
    print("\n" + "="*120)
    print("📋 **市場交易明細 (Market Breakdown)**")
    print("="*120)
    print(f"{'Market':<55} | {'Status':<8} | {'Trades':<6} | {'Cost':<10} | {'Revenue':<10} | {'PnL':<12}")
    print("-"*120)
    
    for r in market_results:
        pnl_str = f"${r['realized_pnl']:+,.2f}"
        if r['realized_pnl'] > 0:
            pnl_str = f"🟢 {pnl_str}"
        elif r['realized_pnl'] < 0:
            pnl_str = f"🔴 {pnl_str}"
        else:
            pnl_str = f"⚪ {pnl_str}"
        
        print(f"{r['question']:<55} | {r['status']:<8} | {r['trade_count']:<6} | ${r['cost_basis']:<9,.2f} | ${r['sell_revenue']:<9,.2f} | {pnl_str}")
    
    # 最近交易紀錄
    print("\n" + "="*120)
    print("📜 **最近交易紀錄 (Recent Trades)**")
    print("="*120)
    print(f"{'Time (UTC)':<20} | {'Side':<5} | {'Size':<12} | {'Price':<8} | {'Value':<12} | {'Market'}")
    print("-"*120)

    # 按時間排序
    sorted_activities = sorted(activities, key=lambda x: x.get('timestamp', 0), reverse=True)
    
    for act in sorted_activities[:30]:  # 只顯示最近 30 筆
        ts = int(act.get('timestamp', 0))
        dt = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        side = act.get('side', 'UNKNOWN')
        size = float(act.get('size', 0))
        price = float(act.get('price', 0)) if act.get('price') else 0
        usdc_value = float(act.get('usdcSize', 0)) if act.get('usdcSize') else size * price
        
        # 直接使用 activity 返回嘅 title
        title = act.get('title', 'Unknown')
        bet_outcome = act.get('outcome', '')
        market_name = f"{title[:35]}... ({bet_outcome})" if len(title) > 35 else f"{title} ({bet_outcome})"
        
        side_icon = "🟢" if side == "BUY" else "🔴"
        print(f"{dt:<20} | {side_icon} {side:<4} | {size:<12,.2f} | {price:<8.4f} | ${usdc_value:<11,.2f} | {market_name}")

    print("="*120 + "\n")
    
    # ========== 🎯 DASHBOARD SUMMARY ==========
    # 計算額外指標
    avg_trade_size = (total_buy_volume + total_sell_volume) / total_trades if total_trades > 0 else 0
    
    # 找出最大盈利和最大虧損的市場
    best_trade = max(market_results, key=lambda x: x['realized_pnl']) if market_results else None
    worst_trade = min(market_results, key=lambda x: x['realized_pnl']) if market_results else None
    
    # 計算開倉中的總成本
    open_positions_cost = sum(r['cost_basis'] for r in market_results if r['status'] == 'OPEN')
    
    # ROI 計算
    roi = (total_realized_pnl / total_buy_volume * 100) if total_buy_volume > 0 else 0
    
    print("╔" + "═"*118 + "╗")
    print("║" + " "*40 + "🎯 WALLET DASHBOARD SUMMARY" + " "*51 + "║")
    print("╠" + "═"*118 + "╣")
    


    # === LOCAL STATS SECTION ===
    pnl_emoji = "🟢" if total_realized_pnl >= 0 else "🔴"
    roi_emoji = "📈" if roi >= 0 else "📉"
    win_emoji = "🏆" if win_rate >= 50 else "⚠️"
    
    pnl_emoji = "🟢" if total_realized_pnl >= 0 else "🔴"
    roi_emoji = "📈" if roi >= 0 else "📉"
    
    print("║" + " "*118 + "║")
    print(f"║   📊 RECENT ACTIVITY ANALYSIS (Based on {len(activities)} loaded trades)" + " "*54 + "║")
    print("║   " + "─"*50 + " "*65 + "║")
    
    # 重點顯示 PnL，弱化 Win Rate
    print(f"║   {pnl_emoji} Realized P&L:     ${total_realized_pnl:>+12,.2f}     │   ⏳ Unrealized P&L:  ${total_unrealized_pnl:>12,.2f}" + " "*38 + "║")
    print(f"║   {roi_emoji} ROI (Recent):     {roi:>+12.2f}%     │   💎 Est. Total P&L:  ${(total_realized_pnl + total_unrealized_pnl):>+12,.2f}" + " "*38 + "║")
    
    trades_display = f"{total_trades} / ~{total_available}"
    print(f"║   📊 Total Trades:      {trades_display:>12}     │   (Win/Loss stats hidden for MM bots)" + " "*40 + "║")
    print("║" + " "*118 + "║")
    
    print("║   💰 VOLUME STATS (Recent)" + " "*91 + "║")
    print("║   " + "─"*50 + " "*65 + "║")
    print(f"║   💵 Total Bought:    ${total_buy_volume:>12,.2f}     │   📍 Markets Traded: {len(market_stats):>6}" + " "*38 + "║")
    local_open_pos = sum(1 for r in market_results if r['status'] == 'OPEN')
    pos_display = f"{local_open_pos} / {global_pos_count}"
    print(f"║   💸 Total Sold:      ${total_sell_volume:>12,.2f}     │   📦 Open Positions: {pos_display:>15}" + " "*29 + "║")
    print(f"║   📐 Avg Trade Size:  ${avg_trade_size:>12,.2f}     │   💼 Open Exposure:  ${open_positions_cost:>10,.2f}" + " "*26 + "║")
    print("║" + " "*118 + "║")
    
    if best_trade and best_trade['realized_pnl'] > 0:
        print("║   🏅 NOTABLE TRADES (Recent)" + " "*90 + "║")
        print("║   " + "─"*50 + " "*65 + "║")
        best_q = best_trade['question'][:40] + "..." if len(best_trade['question']) > 40 else best_trade['question']
        print(f"║   🥇 Best Trade:   {best_q:<45} ${best_trade['realized_pnl']:>+10,.2f}" + " "*10 + "║")
        if worst_trade and worst_trade['realized_pnl'] < 0:
            worst_q = worst_trade['question'][:40] + "..." if len(worst_trade['question']) > 40 else worst_trade['question']
            print(f"║   🥴 Worst Trade:  {worst_q:<45} ${worst_trade['realized_pnl']:>+10,.2f}" + " "*10 + "║")
        print("║" + " "*118 + "║")
    
    print("╚" + "═"*118 + "╝")
    print()
    
    # 輸出 JSON 格式供程式使用
    summary = {
        "wallet": wallet_address,
        "total_trades": total_trades,
        "total_buy_volume": round(total_buy_volume, 2),
        "total_sell_volume": round(total_sell_volume, 2),
        "markets_traded": len(market_stats),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "roi_pct": round(roi, 2),
        "realized_pnl": round(total_realized_pnl, 2),
        "estimated_unrealized_pnl": round(total_unrealized_pnl, 2),
        "estimated_total_pnl": round(total_realized_pnl + total_unrealized_pnl, 2),
        "avg_trade_size": round(avg_trade_size, 2),
        "open_positions_cost": round(open_positions_cost, 2),
        "best_trade": best_trade['question'] if best_trade else None,
        "best_trade_pnl": best_trade['realized_pnl'] if best_trade else 0,
        "worst_trade": worst_trade['question'] if worst_trade else None,
        "worst_trade_pnl": worst_trade['realized_pnl'] if worst_trade else 0,
        "markets": market_results
    }
    
    # print("\n📦 JSON Summary:")
    # print(json.dumps(summary, indent=2))


def get_wallet_trade_count(wallet_address: str) -> int:
    """
    快速獲取錢包的全球交易總數 (使用二分搜尋法)
    """
    url = f"{BASE_URL}/activity"
    
    def check_offset(idx):
        try:
            r = requests.get(url, params={"user": wallet_address, "limit": 1, "offset": idx, "type": "TRADE"}, timeout=5)
            return r.status_code == 200 and len(r.json()) > 0
        except:
            return False
    
    # Binary search
    low = 0
    high = 1000
    while check_offset(high):
        low = high
        high *= 2
        if high > 5000000:
            break
    
    while low < high:
        mid = (low + high + 1) // 2
        if check_offset(mid):
            low = mid
        else:
            high = mid - 1
    
    return low + 1 if check_offset(low) else 0

def get_market_name(condition_id: str) -> str:
    """Fetch market name/question from API."""
    try:
        resp = requests.get(f"{GAMMA_URL}/markets", params={"condition_id": condition_id}, timeout=5)
        if resp.status_code == 200:
            markets = resp.json()
            if markets:
                return markets[0].get('question', 'Unknown Market')
    except:
        pass
    return "Unknown Market"


def is_likely_market_maker(wallet_data: dict) -> tuple:
    """
    判斷一個錢包係咪 Market Maker
    
    Returns:
        (is_mm: bool, confidence: str, reasons: list)
    """
    reasons = []
    score = 0
    
    market_trades = wallet_data.get('market_trades', 0)
    global_trades = wallet_data.get('global_trades', 0)
    market_pnl = wallet_data.get('market_pnl', 0)
    
    # 條件 1: 超高頻市場交易 (>100 筆/市場)
    if market_trades > 200:
        score += 3
        reasons.append(f"極高頻交易 ({market_trades} trades/market)")
    elif market_trades > 100:
        score += 2
        reasons.append(f"高頻交易 ({market_trades} trades/market)")
    elif market_trades > 50:
        score += 1
        reasons.append(f"較高交易量 ({market_trades} trades/market)")
    
    # 條件 2: 全球交易量巨大 (>100萬)
    if global_trades > 5_000_000:
        score += 3
        reasons.append(f"超級大戶 ({global_trades:,} global trades)")
    elif global_trades > 1_000_000:
        score += 2
        reasons.append(f"大額交易者 ({global_trades:,} global trades)")
    elif global_trades > 100_000:
        score += 1
        reasons.append(f"活躍交易者 ({global_trades:,} global trades)")
    
    # 條件 3: 巨額虧損 (MM 經常承受庫存風險)
    if market_pnl < -100000:
        score += 2
        reasons.append(f"巨額庫存虧損 (${abs(market_pnl):,.0f})")
    elif market_pnl < -10000:
        score += 1
        reasons.append(f"顯著虧損 (${abs(market_pnl):,.0f})")
    
    # 判斷
    if score >= 5:
        return True, "HIGH", reasons
    elif score >= 3:
        return True, "MEDIUM", reasons
    elif score >= 2:
        return False, "POSSIBLE", reasons
    else:
        return False, "LOW", reasons


def is_smart_money(wallet_data: dict) -> tuple:
    """
    判斷一個錢包係咪 Smart Money (真正有實力嘅交易者)
    
    Returns:
        (is_sm: bool, confidence: str, reasons: list)
    """
    reasons = []
    score = 0
    
    market_pnl = wallet_data.get('market_pnl', 0)
    market_trades = wallet_data.get('market_trades', 0)
    global_trades = wallet_data.get('global_trades', 0)
    is_mm = wallet_data.get('is_market_maker', False)
    
    # 排除 Market Maker
    if is_mm:
        return False, "EXCLUDED", ["Market Maker - 唔計入 Smart Money"]
    
    # 必須係贏家
    if market_pnl <= 0:
        return False, "EXCLUDED", ["非贏家 - 唔符合 Smart Money 定義"]
    
    # 條件 1: 有實際獲利
    if market_pnl > 10000:
        score += 3
        reasons.append(f"顯著獲利 (+${market_pnl:,.0f})")
    elif market_pnl > 3000:
        score += 2
        reasons.append(f"良好獲利 (+${market_pnl:,.0f})")
    elif market_pnl > 500:
        score += 1
        reasons.append(f"正收益 (+${market_pnl:,.0f})")
    
    # 條件 2: 適度交易頻率 (唔係一次性運氣)
    if 10 <= market_trades <= 100:
        score += 2
        reasons.append(f"主動管理倉位 ({market_trades} trades)")
    elif 5 <= market_trades < 10:
        score += 1
        reasons.append(f"多次交易 ({market_trades} trades)")
    elif market_trades == 1:
        score -= 1  # 只買一次可能係運氣
        reasons.append("⚠️ 單次交易 (可能係運氣)")
    elif market_trades > 100:
        score += 1  # 高頻但唔係 MM
        reasons.append(f"高頻操作 ({market_trades} trades)")
    
    # 條件 3: 有足夠經驗 (跨市場表現)
    if 5000 <= global_trades <= 100000:
        score += 2
        reasons.append(f"資深交易者 ({global_trades:,} total)")
    elif 1000 <= global_trades < 5000:
        score += 1
        reasons.append(f"有經驗 ({global_trades:,} total)")
    elif global_trades > 1000000:
        score -= 1  # 太多可能係 Bot
        reasons.append("⚠️ 超高頻 (可能係 Bot)")
    elif global_trades < 1000:
        score -= 1
        reasons.append("⚠️ 新手 (經驗不足)")
    
    # 條件 4: 效率 (PnL per trade)
    pnl_per_trade = market_pnl / max(market_trades, 1)
    if pnl_per_trade > 500:
        score += 1
        reasons.append(f"高效交易 (${pnl_per_trade:,.0f}/trade)")
    
    # 判斷
    if score >= 5:
        return True, "HIGH", reasons
    elif score >= 3:
        return True, "MEDIUM", reasons
    elif score >= 1:
        return False, "POSSIBLE", reasons
    else:
        return False, "LOW", reasons


def generate_trading_signal(condition_id: str, min_global_trades: int = 1000):
    """
    生成交易信號：比較 Smart Money 與 Losers 的倉位方向。
    策略：跟據 Smart Money 操作，反向操作 Losers。
    """
    print(f"\n📡 生成交易信號: {condition_id}", file=sys.stderr)
    
    # Step 1: Fetch all trades (and get market name from first trade)
    print(f"  📊 Fetching market trades...", end="", flush=True, file=sys.stderr)
    trades = []
    market_name = "Unknown Market"
    offset = 0
    limit = 500
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/trades", params={
                "market": condition_id, "limit": limit, "offset": offset
            }, timeout=10)
            if resp.status_code != 200 or not resp.json():
                break
            data = resp.json()
            trades.extend(data)
            # Get market name from first trade
            if not market_name or market_name == "Unknown Market":
                if data and data[0].get('title'):
                    market_name = data[0].get('title')
            print(".", end="", flush=True, file=sys.stderr)
            if len(data) < limit or offset > 10000:
                break
            offset += limit
        except:
            break
    print(f" {len(trades)} trades", file=sys.stderr)
    print(f"  📛 Market: {market_name[:60]}{'...' if len(market_name) > 60 else ''}", file=sys.stderr)
    
    if len(trades) < 50:
        return {"error": "市場交易量太少，無法生成有效信號", "trades": len(trades)}
    
    # Step 2: Calculate per-wallet stats with direction tracking
    wallet_stats = {}
    for trade in trades:
        wallet = trade.get('proxyWallet') or trade.get('maker') or trade.get('taker')
        if not wallet:
            continue
        if wallet not in wallet_stats:
            wallet_stats[wallet] = {
                "buy_volume": 0, "sell_volume": 0, "trade_count": 0,
                "yes_exposure": 0, "no_exposure": 0
            }
        
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        price = float(trade.get('price', 0) or 0)
        side = trade.get('side', '').lower()
        outcome = trade.get('outcome', '').upper()
        
        value = size * price if price > 0 else size
        
        if side == 'buy':
            wallet_stats[wallet]['buy_volume'] += value
            if outcome == 'YES':
                wallet_stats[wallet]['yes_exposure'] += value
            elif outcome == 'NO':
                wallet_stats[wallet]['no_exposure'] += value
        elif side == 'sell':
            wallet_stats[wallet]['sell_volume'] += value
            if outcome == 'YES':
                wallet_stats[wallet]['yes_exposure'] -= value
            elif outcome == 'NO':
                wallet_stats[wallet]['no_exposure'] -= value
        
        wallet_stats[wallet]['trade_count'] += 1
    
    for w, s in wallet_stats.items():
        s['realized_pnl'] = s['sell_volume'] - s['buy_volume']
        s['net_direction'] = "YES" if s['yes_exposure'] > s['no_exposure'] else "NO"
    
    # Step 3: Identify Smart Money and Losers
    print(f"  🔎 Identifying Smart Money vs Losers...", file=sys.stderr)
    
    # Get top winners and losers
    winners = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] > 100]
    losers = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] < -100]
    
    print(f"    Raw winners (PnL > $100): {len(winners)}", file=sys.stderr)
    print(f"    Raw losers (PnL < -$100): {len(losers)}", file=sys.stderr)
    
    winners.sort(key=lambda x: x[1]['realized_pnl'], reverse=True)
    losers.sort(key=lambda x: x[1]['realized_pnl'])
    
    # Check global trades for top players (parallel)
    def get_global_and_classify(wallet_stats_tuple):
        wallet, stats = wallet_stats_tuple
        global_trades = get_wallet_trade_count(wallet)
        result = {
            "address": wallet,
            "pnl": stats['realized_pnl'],
            "net_direction": stats['net_direction'],
            "yes_exposure": stats['yes_exposure'],
            "no_exposure": stats['no_exposure'],
            "global_trades": global_trades
        }
        # Quick MM check
        is_mm = global_trades > 1_000_000 or stats['trade_count'] > 150
        result['is_mm'] = is_mm
        return result
    
    smart_money = []
    dumb_money = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Check top 20 winners
        winner_futures = [executor.submit(get_global_and_classify, w) for w in winners[:20]]
        for f in winner_futures:
            try:
                r = f.result(timeout=20)
                if r['global_trades'] >= min_global_trades and not r['is_mm']:
                    smart_money.append(r)
            except:
                pass
        
        # Check top 20 losers
        loser_futures = [executor.submit(get_global_and_classify, l) for l in losers[:20]]
        for f in loser_futures:
            try:
                r = f.result(timeout=20)
                if r['global_trades'] >= min_global_trades and not r['is_mm']:
                    dumb_money.append(r)
            except:
                pass
    
    print(f"  🧠 Smart Money: {len(smart_money)} wallets", file=sys.stderr)
    print(f"  💸 Dumb Money: {len(dumb_money)} wallets", file=sys.stderr)
    
    if len(smart_money) < 3:
        return {"error": "Smart Money 樣本不足", "smart_count": len(smart_money)}
    
    # Step 4: Calculate aggregate positions
    sm_yes = sum(w['yes_exposure'] for w in smart_money)
    sm_no = sum(w['no_exposure'] for w in smart_money)
    dm_yes = sum(w['yes_exposure'] for w in dumb_money)
    dm_no = sum(w['no_exposure'] for w in dumb_money)
    
    sm_direction = "YES" if sm_yes > sm_no else "NO"
    dm_direction = "YES" if dm_yes > dm_no else "NO"
    
    sm_conviction = abs(sm_yes - sm_no)
    dm_conviction = abs(dm_yes - dm_no)
    
    # Step 5: Generate signal
    if sm_direction == dm_direction:
        # Both agree - weak signal (could be obvious)
        signal = {
            "action": sm_direction,
            "strength": "WEAK",
            "reasoning": f"Smart Money 與 Losers 方向一致 ({sm_direction})，可能係公眾共識",
            "confidence": "LOW"
        }
    else:
        # Disagreement - strong signal (follow smart money)
        signal = {
            "action": sm_direction,
            "strength": "STRONG",
            "reasoning": f"Smart Money 做 {sm_direction} (${sm_conviction:,.0f})，Losers 做 {dm_direction} (${dm_conviction:,.0f})。經典反向信號！",
            "confidence": "HIGH" if sm_conviction > dm_conviction else "MEDIUM"
        }
    
    result = {
        "market": condition_id,
        "market_name": market_name,
        "signal": signal,
        "smart_money": {
            "count": len(smart_money),
            "total_yes_exposure": round(sm_yes, 2),
            "total_no_exposure": round(sm_no, 2),
            "net_direction": sm_direction,
            "top_3": [{"addr": w['address'][:12]+"...", "pnl": round(w['pnl'], 2), "dir": w['net_direction']} for w in smart_money[:3]]
        },
        "dumb_money": {
            "count": len(dumb_money),
            "total_yes_exposure": round(dm_yes, 2),
            "total_no_exposure": round(dm_no, 2),
            "net_direction": dm_direction,
            "top_3": [{"addr": w['address'][:12]+"...", "pnl": round(w['pnl'], 2), "dir": w['net_direction']} for w in dumb_money[:3]]
        }
    }
    
    # Print summary
    action_emoji = "🟢" if signal['action'] == "YES" else "🔴"
    strength_emoji = "💪" if signal['strength'] == "STRONG" else "🤔"
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"{action_emoji} 交易信號: {signal['action']} {strength_emoji} ({signal['strength']})", file=sys.stderr)
    print(f"📊 信心度: {signal['confidence']}", file=sys.stderr)
    print(f"📝 原因: {signal['reasoning']}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def get_historical_price(clob_token_id: str, days_ago: int = 7) -> dict:
    """獲取歷史價格數據"""
    try:
        from datetime import timedelta
        start_ts = int((datetime.now() - timedelta(days=days_ago + 3)).timestamp())
        
        url = "https://clob.polymarket.com/prices-history"
        params = {
            "market": clob_token_id,
            "interval": "1d",
            "fidelity": 100,
            "startTs": start_ts
        }
        
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return {}
        
        data = resp.json()
        history = data.get('history', [])
        
        if not history:
            return {}
        
        # Get prices at different points
        prices = {}
        now = datetime.now()
        
        for entry in history:
            t = entry.get('t', 0)
            p = entry.get('p', 0)
            if t and p:
                date = datetime.fromtimestamp(t)
                days_diff = (now - date).days
                if days_diff <= days_ago + 2:
                    prices[days_diff] = float(p)
        
        return prices
    except:
        return {}


def generate_pro_signal(condition_id: str, min_global_trades: int = 500):
    """
    🔥 PRO Signal Generator - 雙重確認交易信號
    結合: 1) 歷史價格趨勢 + 2) Smart Money 方向
    """
    print(f"\n🔥 PRO 雙重確認信號: {condition_id}", file=sys.stderr)
    
    # Step 1: Fetch trades and get market info
    print(f"  📊 Step 1/3: Fetching market data...", file=sys.stderr)
    trades = []
    market_name = "Unknown Market"
    clob_token_id = None
    
    offset = 0
    limit = 500
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/trades", params={
                "market": condition_id, "limit": limit, "offset": offset
            }, timeout=10)
            if resp.status_code != 200 or not resp.json():
                break
            data = resp.json()
            trades.extend(data)
            if market_name == "Unknown Market" and data:
                market_name = data[0].get('title', 'Unknown Market')
                clob_token_id = data[0].get('asset')
            if len(data) < limit or offset > 5000:
                break
            offset += limit
        except:
            break
    
    print(f"  📛 Market: {market_name[:50]}...", file=sys.stderr)
    print(f"  📈 Trades: {len(trades)}", file=sys.stderr)
    
    if len(trades) < 50:
        return {"error": "市場交易量太少"}
    
    # Step 2: Get historical price trend
    print(f"  📊 Step 2/3: Analyzing price trend...", file=sys.stderr)
    price_trend = {"direction": "UNKNOWN", "change_7d": 0, "current": 0, "week_ago": 0}
    
    if clob_token_id:
        prices = get_historical_price(clob_token_id, 7)
        if prices:
            current_price = prices.get(0) or prices.get(1) or 0
            week_ago_price = prices.get(7) or prices.get(6) or prices.get(8) or 0
            
            if current_price and week_ago_price:
                change = (current_price - week_ago_price) * 100
                price_trend = {
                    "direction": "UP" if change > 2 else "DOWN" if change < -2 else "FLAT",
                    "change_7d": round(change, 2),
                    "current": round(current_price * 100, 2),
                    "week_ago": round(week_ago_price * 100, 2)
                }
                print(f"    📈 Price: {price_trend['week_ago']}% → {price_trend['current']}% ({price_trend['change_7d']:+.1f}%)", file=sys.stderr)
    
    # Step 3: Analyze Smart Money vs Dumb Money
    print(f"  📊 Step 3/3: Analyzing money flow...", file=sys.stderr)
    
    wallet_stats = {}
    for trade in trades:
        wallet = trade.get('proxyWallet') or trade.get('maker') or trade.get('taker')
        if not wallet:
            continue
        if wallet not in wallet_stats:
            wallet_stats[wallet] = {
                "buy_volume": 0, "sell_volume": 0, "trade_count": 0,
                "yes_exposure": 0, "no_exposure": 0
            }
        
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        price = float(trade.get('price', 0) or 0)
        side = trade.get('side', '').lower()
        outcome = trade.get('outcome', '').upper()
        
        value = size * price if price > 0 else size
        
        if side == 'buy':
            wallet_stats[wallet]['buy_volume'] += value
            if outcome == 'YES':
                wallet_stats[wallet]['yes_exposure'] += value
            elif outcome == 'NO':
                wallet_stats[wallet]['no_exposure'] += value
        elif side == 'sell':
            wallet_stats[wallet]['sell_volume'] += value
        
        wallet_stats[wallet]['trade_count'] += 1
    
    for w, s in wallet_stats.items():
        s['realized_pnl'] = s['sell_volume'] - s['buy_volume']
        s['net_direction'] = "YES" if s['yes_exposure'] > s['no_exposure'] else "NO"
    
    # Get winners and losers
    winners = sorted([(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] > 100], 
                     key=lambda x: x[1]['realized_pnl'], reverse=True)[:10]
    losers = sorted([(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] < -100], 
                    key=lambda x: x[1]['realized_pnl'])[:10]
    
    # Calculate aggregate directions
    sm_yes = sum(s['yes_exposure'] for w, s in winners)
    sm_no = sum(s['no_exposure'] for w, s in winners)
    dm_yes = sum(s['yes_exposure'] for w, s in losers)
    dm_no = sum(s['no_exposure'] for w, s in losers)
    
    smart_money_dir = "YES" if sm_yes > sm_no else "NO"
    dumb_money_dir = "YES" if dm_yes > dm_no else "NO"
    
    # Step 4: Generate dual-confirmation signal
    print(f"\n  🎯 Generating PRO signal...", file=sys.stderr)
    
    # Signal logic
    price_signal = "YES" if price_trend['direction'] == "UP" else "NO" if price_trend['direction'] == "DOWN" else None
    
    signals_aligned = 0
    signal_reasons = []
    
    # Check alignment
    if price_signal and price_signal == smart_money_dir:
        signals_aligned += 1
        signal_reasons.append(f"價格趨勢 ({price_trend['direction']}) 與 Smart Money ({smart_money_dir}) 一致")
    
    if smart_money_dir != dumb_money_dir:
        signals_aligned += 1
        signal_reasons.append(f"Smart Money ({smart_money_dir}) 與 Losers ({dumb_money_dir}) 方向相反")
    
    if price_signal and price_signal != dumb_money_dir:
        signals_aligned += 1
        signal_reasons.append(f"價格趨勢 ({price_trend['direction']}) 與 Losers ({dumb_money_dir}) 方向相反")
    
    # Determine final signal
    if signals_aligned >= 2:
        final_action = smart_money_dir
        strength = "VERY_STRONG" if signals_aligned == 3 else "STRONG"
        confidence = "HIGH"
    elif signals_aligned == 1:
        final_action = smart_money_dir
        strength = "MODERATE"
        confidence = "MEDIUM"
    else:
        final_action = smart_money_dir if smart_money_dir else "UNCLEAR"
        strength = "WEAK"
        confidence = "LOW"
    
    result = {
        "market": condition_id,
        "market_name": market_name,
        "pro_signal": {
            "action": final_action,
            "strength": strength,
            "confidence": confidence,
            "signals_aligned": signals_aligned,
            "reasons": signal_reasons
        },
        "price_trend": price_trend,
        "money_flow": {
            "smart_money_direction": smart_money_dir,
            "smart_money_yes_exposure": round(sm_yes, 2),
            "smart_money_no_exposure": round(sm_no, 2),
            "dumb_money_direction": dumb_money_dir,
            "dumb_money_yes_exposure": round(dm_yes, 2),
            "dumb_money_no_exposure": round(dm_no, 2)
        },
        "summary": {
            "winners_count": len(winners),
            "losers_count": len(losers),
            "total_trades": len(trades)
        }
    }
    
    # Print summary
    action_emoji = "🟢" if final_action == "YES" else "🔴"
    strength_emoji = "💪💪💪" if strength == "VERY_STRONG" else "💪💪" if strength == "STRONG" else "💪" if strength == "MODERATE" else "🤔"
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"{action_emoji} PRO 信號: {final_action} {strength_emoji} ({strength})", file=sys.stderr)
    print(f"📊 信心度: {confidence} ({signals_aligned}/3 指標對齊)", file=sys.stderr)
    for reason in signal_reasons:
        print(f"  ✓ {reason}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def detect_insider_activity(condition_id: str, price_threshold: float = 10.0, trade_threshold: float = 5000):
    """
    🕵️ Insider Activity Detector - 異常交易偵測
    偵測: 價格突變 + 大額交易 = 潛在 Insider 信號
    """
    print(f"\n🕵️ Insider Activity Scan: {condition_id}", file=sys.stderr)
    
    # Step 1: Fetch trades with timestamps
    print(f"  📊 Fetching trades...", end="", flush=True, file=sys.stderr)
    trades = []
    market_name = "Unknown Market"
    clob_token_id = None
    
    offset = 0
    limit = 500
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/trades", params={
                "market": condition_id, "limit": limit, "offset": offset
            }, timeout=10)
            if resp.status_code != 200 or not resp.json():
                break
            data = resp.json()
            trades.extend(data)
            if market_name == "Unknown Market" and data:
                market_name = data[0].get('title', 'Unknown Market')
                clob_token_id = data[0].get('asset')
            print(".", end="", flush=True, file=sys.stderr)
            if len(data) < limit or offset > 5000:
                break
            offset += limit
        except:
            break
    
    print(f" {len(trades)} trades", file=sys.stderr)
    print(f"  📛 Market: {market_name[:50]}...", file=sys.stderr)
    
    if len(trades) < 50:
        return {"error": "市場交易量太少"}
    
    # Step 2: Get price history
    print(f"  📈 Fetching price history...", file=sys.stderr)
    price_spikes = []
    
    if clob_token_id:
        prices = get_historical_price(clob_token_id, 14)
        
        # Detect spikes (>threshold% change between consecutive days)
        sorted_days = sorted(prices.keys())
        for i in range(1, len(sorted_days)):
            day1, day2 = sorted_days[i-1], sorted_days[i]
            p1, p2 = prices[day1], prices[day2]
            
            if p1 > 0:
                change = ((p2 - p1) / p1) * 100
                if abs(change) >= price_threshold:
                    spike_date = datetime.now() - timedelta(days=day2)
                    price_spikes.append({
                        "days_ago": day2,
                        "date": spike_date.strftime("%Y-%m-%d"),
                        "from_price": round(p1 * 100, 2),
                        "to_price": round(p2 * 100, 2),
                        "change": round(change, 2),
                        "direction": "UP" if change > 0 else "DOWN"
                    })
    
    print(f"  🚨 Found {len(price_spikes)} price spikes (>{price_threshold}%)", file=sys.stderr)
    
    # Step 3: Find large trades
    print(f"  💰 Analyzing large trades...", file=sys.stderr)
    large_trades = []
    
    for trade in trades:
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        if size >= trade_threshold:
            ts = trade.get('timestamp', 0)
            trade_date = datetime.fromtimestamp(ts) if ts else None
            
            large_trades.append({
                "wallet": trade.get('proxyWallet', '?')[:12] + "...",
                "size": round(size, 2),
                "side": trade.get('side', '?'),
                "outcome": trade.get('outcome', '?'),
                "timestamp": trade_date.strftime("%Y-%m-%d %H:%M") if trade_date else "?",
                "days_ago": (datetime.now() - trade_date).days if trade_date else 999
            })
    
    print(f"  💰 Found {len(large_trades)} large trades (>${trade_threshold:,.0f})", file=sys.stderr)
    
    # Step 4: Correlate spikes with large trades
    print(f"  🔍 Correlating spikes with trades...", file=sys.stderr)
    suspicious_events = []
    
    for spike in price_spikes:
        # Find large trades around this spike (±1 day)
        related_trades = [t for t in large_trades 
                         if abs(t['days_ago'] - spike['days_ago']) <= 1]
        
        if related_trades:
            total_volume = sum(t['size'] for t in related_trades)
            suspicious_events.append({
                "type": "SPIKE_WITH_LARGE_TRADES",
                "severity": "HIGH" if len(related_trades) >= 2 or total_volume > 20000 else "MEDIUM",
                "date": spike['date'],
                "price_change": f"{spike['from_price']}% → {spike['to_price']}% ({spike['change']:+.1f}%)",
                "related_trades": len(related_trades),
                "total_volume": round(total_volume, 2),
                "trades": related_trades[:5]  # Top 5 trades
            })
    
    # Step 5: Calculate risk score
    risk_score = 0
    risk_reasons = []
    
    if len(suspicious_events) >= 3:
        risk_score += 40
        risk_reasons.append(f"多次價格突變伴隨大額交易 ({len(suspicious_events)} 次)")
    elif len(suspicious_events) >= 1:
        risk_score += 20
        risk_reasons.append(f"價格突變伴隨大額交易 ({len(suspicious_events)} 次)")
    
    high_severity = sum(1 for e in suspicious_events if e['severity'] == "HIGH")
    if high_severity >= 2:
        risk_score += 30
        risk_reasons.append(f"高嚴重性事件 ({high_severity} 次)")
    
    if len(large_trades) >= 10:
        risk_score += 20
        risk_reasons.append(f"大量大額交易 ({len(large_trades)} 筆)")
    
    risk_level = "CRITICAL" if risk_score >= 60 else "HIGH" if risk_score >= 40 else "MEDIUM" if risk_score >= 20 else "LOW"
    
    result = {
        "market": condition_id,
        "market_name": market_name,
        "insider_risk": {
            "level": risk_level,
            "score": risk_score,
            "reasons": risk_reasons
        },
        "price_spikes": price_spikes,
        "large_trades": large_trades[:20],  # Top 20
        "suspicious_events": suspicious_events,
        "thresholds": {
            "price_change": f"{price_threshold}%",
            "trade_size": f"${trade_threshold:,.0f}"
        }
    }
    
    # Print summary
    risk_emoji = "🚨" if risk_level == "CRITICAL" else "⚠️" if risk_level == "HIGH" else "⚡" if risk_level == "MEDIUM" else "✅"
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"{risk_emoji} INSIDER RISK: {risk_level} (Score: {risk_score}/100)", file=sys.stderr)
    for reason in risk_reasons:
        print(f"  • {reason}", file=sys.stderr)
    if suspicious_events:
        print(f"\n  🕵️ Suspicious Events:", file=sys.stderr)
        for event in suspicious_events[:3]:
            print(f"    - {event['date']}: {event['price_change']} | {event['related_trades']} trades (${event['total_volume']:,.0f})", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def scan_market_all(condition_id: str, min_global_trades: int = 1000, min_pnl: float = 0):
    """
    掃描一個市場，找出所有贏家和輸家錢包，並篩選出有足夠交易歷史的專業玩家。
    輸出一個包含 winners 和 losers 的完整 JSON。
    """
    print(f"\n🔍 掃描市場 (贏家 + 輸家): {condition_id}", file=sys.stderr)
    print(f"  篩選條件: 全球交易數 >= {min_global_trades}, |PnL| > ${min_pnl}", file=sys.stderr)
    
    # Step 1: Fetch all trades for this market (and get name from first trade)
    print(f"  📊 Fetching market trades...", end="", flush=True, file=sys.stderr)
    trades = []
    market_name = "Unknown Market"
    offset = 0
    limit = 500
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/trades", params={
                "market": condition_id,
                "limit": limit,
                "offset": offset
            }, timeout=10)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            trades.extend(data)
            # Get market name from first trade
            if market_name == "Unknown Market" and data and data[0].get('title'):
                market_name = data[0].get('title')
            print(".", end="", flush=True, file=sys.stderr)
            if len(data) < limit:
                break
            offset += limit
            if offset > 10000:
                break
        except Exception as e:
            print(f" Error: {e}", file=sys.stderr)
            break
    
    print(f" Done ({len(trades)} trades)", file=sys.stderr)
    
    if not trades:
        print(json.dumps({"error": "No trades found for this market", "market": condition_id, "market_name": market_name}))
        return
    
    # Step 2: Calculate PnL per wallet
    print(f"  💰 Calculating per-wallet PnL...", file=sys.stderr)
    wallet_stats = {}
    
    for trade in trades:
        wallet = trade.get('proxyWallet') or trade.get('maker') or trade.get('taker')
        if not wallet:
            continue
        
        if wallet not in wallet_stats:
            wallet_stats[wallet] = {"buy_volume": 0, "sell_volume": 0, "trade_count": 0}
        
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        price = float(trade.get('price', 0) or 0)
        side = trade.get('side', '').lower()
        
        value = size * price if price > 0 else size
        
        if side == 'buy':
            wallet_stats[wallet]['buy_volume'] += value
        elif side == 'sell':
            wallet_stats[wallet]['sell_volume'] += value
        
        wallet_stats[wallet]['trade_count'] += 1
    
    for wallet, stats in wallet_stats.items():
        stats['realized_pnl'] = stats['sell_volume'] - stats['buy_volume']
    
    # Step 3: Separate winners and losers
    winners_raw = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] > min_pnl]
    losers_raw = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] < -min_pnl]
    
    winners_raw.sort(key=lambda x: x[1]['realized_pnl'], reverse=True)
    losers_raw.sort(key=lambda x: x[1]['realized_pnl'])
    
    print(f"  🏆 Found {len(winners_raw)} wallets with positive PnL", file=sys.stderr)
    print(f"  💩 Found {len(losers_raw)} wallets with negative PnL", file=sys.stderr)
    
    # Step 4: Verify global trade count for top players (PARALLEL)
    print(f"  🚀 Verifying global trade history (parallel)...", file=sys.stderr)
    
    def check_wallet(wallet_stats_tuple):
        """Helper function for parallel execution with MM + SM detection."""
        wallet, stats = wallet_stats_tuple
        global_trades = get_wallet_trade_count(wallet)
        
        result = {
            "address": wallet,
            "market_pnl": round(stats['realized_pnl'], 2),
            "market_trades": stats['trade_count'],
            "global_trades": global_trades
        }
        
        # Add Market Maker detection
        is_mm, mm_conf, mm_reasons = is_likely_market_maker(result)
        result["is_market_maker"] = is_mm
        result["mm_confidence"] = mm_conf
        result["mm_reasons"] = mm_reasons
        
        # Add Smart Money detection
        is_sm, sm_conf, sm_reasons = is_smart_money(result)
        result["is_smart_money"] = is_sm
        result["sm_confidence"] = sm_conf
        result["sm_reasons"] = sm_reasons
        
        return result
    
    # Combine winners and losers for parallel checking
    candidates = []
    candidates.extend([("winner", w, s) for w, s in winners_raw[:30]])
    candidates.extend([("loser", w, s) for w, s in losers_raw[:30]])
    
    print(f"    Checking {len(candidates)} wallets in parallel...", file=sys.stderr)
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_wallet, (c[1], c[2])): c[0] for c in candidates}
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=30)
                role = futures[future]
                results.append((role, result))
                print(f".", end="", flush=True, file=sys.stderr)
            except Exception as e:
                print(f"x", end="", flush=True, file=sys.stderr)
    
    print(f" Done!", file=sys.stderr)
    
    # Separate results
    qualified_winners = [r[1] for r in results if r[0] == "winner" and r[1]["global_trades"] >= min_global_trades]
    qualified_losers = [r[1] for r in results if r[0] == "loser" and r[1]["global_trades"] >= min_global_trades]
    
    # Sort by PnL
    qualified_winners.sort(key=lambda x: x["market_pnl"], reverse=True)
    qualified_losers.sort(key=lambda x: x["market_pnl"])
    
    # Step 5: Output combined results
    result = {
        "market": condition_id,
        "market_name": market_name,
        "filter": {
            "min_global_trades": min_global_trades,
            "min_pnl": min_pnl
        },
        "total_market_trades": len(trades),
        "total_unique_wallets": len(wallet_stats),
        "winners": {
            "total_count": len(winners_raw),
            "qualified_count": len(qualified_winners),
            "list": qualified_winners
        },
        "losers": {
            "total_count": len(losers_raw),
            "qualified_count": len(qualified_losers),
            "list": qualified_losers
        }
    }
    
    print(f"\n✅ 找到 {len(qualified_winners)} 個專業贏家 + {len(qualified_losers)} 個專業輸家", file=sys.stderr)
    print(json.dumps(result, indent=2))


def scan_market_players(condition_id: str, min_global_trades: int = 1000, min_pnl: float = 0, mode: str = "winners"):
    """
    掃描一個市場，找出所有贏家或輸家錢包，並篩選出有足夠交易歷史的專業玩家。
    """
    mode_emoji = "🏆" if mode == "winners" else "💩"
    mode_label = "贏家" if mode == "winners" else "輸家"
    print(f"\n{mode_emoji} 掃描市場{mode_label}: {condition_id}", file=sys.stderr)
    print(f"  篩選條件: 全球交易數 >= {min_global_trades}, |PnL| > ${min_pnl}", file=sys.stderr)
    
    # Step 1: Fetch all trades for this market (get name from first trade)
    print(f"  📊 Fetching market trades...", end="", flush=True, file=sys.stderr)
    trades = []
    market_name = "Unknown Market"
    offset = 0
    limit = 500
    while True:
        try:
            resp = requests.get(f"{BASE_URL}/trades", params={
                "market": condition_id,
                "limit": limit,
                "offset": offset
            }, timeout=10)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            trades.extend(data)
            # Get market name from first trade
            if market_name == "Unknown Market" and data and data[0].get('title'):
                market_name = data[0].get('title')
            print(".", end="", flush=True, file=sys.stderr)
            if len(data) < limit:
                break
            offset += limit
            if offset > 10000:  # Safety cap for market trades
                break
        except Exception as e:
            print(f" Error: {e}", file=sys.stderr)
            break
    
    print(f" Done ({len(trades)} trades)", file=sys.stderr)
    print(f"  📛 Market: {market_name[:60]}{'...' if len(market_name) > 60 else ''}", file=sys.stderr)
    
    if not trades:
        print(json.dumps({"error": "No trades found for this market"}))
        return
    
    # Step 2: Calculate PnL per wallet in THIS market
    print(f"  💰 Calculating per-wallet PnL...", file=sys.stderr)
    wallet_stats = {}
    
    for trade in trades:
        wallet = trade.get('proxyWallet') or trade.get('maker') or trade.get('taker')
        if not wallet:
            continue
        
        if wallet not in wallet_stats:
            wallet_stats[wallet] = {
                "buy_volume": 0,
                "sell_volume": 0,
                "trade_count": 0
            }
        
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        price = float(trade.get('price', 0) or 0)
        side = trade.get('side', '').lower()
        
        value = size * price if price > 0 else size
        
        if side == 'buy':
            wallet_stats[wallet]['buy_volume'] += value
        elif side == 'sell':
            wallet_stats[wallet]['sell_volume'] += value
        
        wallet_stats[wallet]['trade_count'] += 1
    
    # Calculate realized PnL (simple: sell - buy)
    for wallet, stats in wallet_stats.items():
        stats['realized_pnl'] = stats['sell_volume'] - stats['buy_volume']
    
    # Step 3: Filter by mode (winners or losers)
    if mode == "winners":
        players = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] > min_pnl]
        players.sort(key=lambda x: x[1]['realized_pnl'], reverse=True)  # Best first
    else:  # losers
        players = [(w, s) for w, s in wallet_stats.items() if s['realized_pnl'] < -min_pnl]
        players.sort(key=lambda x: x[1]['realized_pnl'])  # Worst first (most negative)
    
    print(f"  {mode_emoji} Found {len(players)} wallets with {'positive' if mode == 'winners' else 'negative'} PnL", file=sys.stderr)
    
    if not players:
        print(json.dumps({"market": condition_id, "players": [], "message": f"No {mode} found"}))
        return
    
    # Step 4: Check global trade count for each player (PARALLEL)
    print(f"  🚀 Verifying global trade history (parallel)...", file=sys.stderr)
    
    def check_wallet_single(wallet_stats_tuple):
        wallet, stats = wallet_stats_tuple
        global_trades = get_wallet_trade_count(wallet)
        result = {
            "address": wallet,
            "market_pnl": round(stats['realized_pnl'], 2),
            "market_trades": stats['trade_count'],
            "global_trades": global_trades
        }
        # Add MM detection
        is_mm, mm_conf, mm_reasons = is_likely_market_maker(result)
        result["is_market_maker"] = is_mm
        result["mm_confidence"] = mm_conf
        result["mm_reasons"] = mm_reasons
        # Add SM detection
        is_sm, sm_conf, sm_reasons = is_smart_money(result)
        result["is_smart_money"] = is_sm
        result["sm_confidence"] = sm_conf
        result["sm_reasons"] = sm_reasons
        return result
    
    print(f"    Checking {min(50, len(players))} wallets in parallel...", file=sys.stderr)
    
    qualified_players = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_wallet_single, (w, s)) for w, s in players[:50]]
        for future in futures:
            try:
                result = future.result(timeout=30)
                print(".", end="", flush=True, file=sys.stderr)
                if result["global_trades"] >= min_global_trades:
                    qualified_players.append(result)
            except:
                print("x", end="", flush=True, file=sys.stderr)
    
    print(f" Done!", file=sys.stderr)
    qualified_players.sort(key=lambda x: x["market_pnl"], reverse=(mode == "winners"))
    
    # Step 5: Output results
    result = {
        "market": condition_id,
        "market_name": market_name,
        "mode": mode,
        "filter": {
            "min_global_trades": min_global_trades,
            "min_pnl": min_pnl
        },
        "total_market_trades": len(trades),
        "total_unique_wallets": len(wallet_stats),
        f"{mode}_count": len(players),
        "qualified_count": len(qualified_players),
        mode: qualified_players
    }
    
    print(f"\n✅ 找到 {len(qualified_players)} 個專業{mode_label}錢包", file=sys.stderr)
    print(json.dumps(result, indent=2))


def main():
    # === 處理 --pro-signal 參數 (PRO 雙重確認信號) ===
    if len(sys.argv) > 2 and sys.argv[1] == "--pro-signal":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        generate_pro_signal(condition_id)
        sys.exit(0)
    
    # === 處理 --insider 參數 (異常交易偵測) ===
    if len(sys.argv) > 2 and sys.argv[1] == "--insider":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        price_threshold = 10.0
        trade_threshold = 5000
        for i, arg in enumerate(sys.argv):
            if arg == "--price-threshold" and i + 1 < len(sys.argv):
                price_threshold = float(sys.argv[i + 1])
            if arg == "--trade-threshold" and i + 1 < len(sys.argv):
                trade_threshold = float(sys.argv[i + 1])
        detect_insider_activity(condition_id, price_threshold, trade_threshold)
        sys.exit(0)
    
    # === 處理 --signal 參數 ===
    if len(sys.argv) > 2 and sys.argv[1] == "--signal":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        min_trades = 1000
        for i, arg in enumerate(sys.argv):
            if arg == "--min-trades" and i + 1 < len(sys.argv):
                min_trades = int(sys.argv[i + 1])
        generate_trading_signal(condition_id, min_global_trades=min_trades)
        sys.exit(0)
    
    # === 處理 --scan-all 參數 ===
    if len(sys.argv) > 2 and sys.argv[1] == "--scan-all":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        min_trades = 1000
        min_pnl = 0
        for i, arg in enumerate(sys.argv):
            if arg == "--min-trades" and i + 1 < len(sys.argv):
                min_trades = int(sys.argv[i + 1])
            if arg == "--min-pnl" and i + 1 < len(sys.argv):
                min_pnl = float(sys.argv[i + 1])
        scan_market_all(condition_id, min_global_trades=min_trades, min_pnl=min_pnl)
        sys.exit(0)
    
    # === 處理 --scan-winners 參數 ===
    if len(sys.argv) > 2 and sys.argv[1] == "--scan-winners":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        min_trades = 1000
        min_pnl = 0
        for i, arg in enumerate(sys.argv):
            if arg == "--min-trades" and i + 1 < len(sys.argv):
                min_trades = int(sys.argv[i + 1])
            if arg == "--min-pnl" and i + 1 < len(sys.argv):
                min_pnl = float(sys.argv[i + 1])
        scan_market_players(condition_id, min_global_trades=min_trades, min_pnl=min_pnl, mode="winners")
        sys.exit(0)
    
    # === 處理 --scan-losers 參數 ===
    if len(sys.argv) > 2 and sys.argv[1] == "--scan-losers":
        condition_id = resolve_input_to_condition_id(sys.argv[2])
        min_trades = 1000
        min_pnl = 0
        for i, arg in enumerate(sys.argv):
            if arg == "--min-trades" and i + 1 < len(sys.argv):
                min_trades = int(sys.argv[i + 1])
            if arg == "--min-pnl" and i + 1 < len(sys.argv):
                min_pnl = float(sys.argv[i + 1])
        scan_market_players(condition_id, min_global_trades=min_trades, min_pnl=min_pnl, mode="losers")
        sys.exit(0)
    
    # === 處理 --inspect 參數，直接查錢包 ===
    if len(sys.argv) > 2 and sys.argv[1] == "--inspect":
        wallet_address = sys.argv[2]
        load_all = "--all" in sys.argv
        inspect_wallet_history(wallet_address, load_all=load_all)
        sys.exit(0)

    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python analyze_whales.py <polymarket_url_or_slug> [options]"}))
        print(json.dumps({"options": {
            "--inspect <wallet>": "Inspect specific wallet history (recent 5000 trades)",
            "--inspect <wallet> --all": "Inspect wallet with ALL trades (slower)",
            "--signal <condition_id>": "🔥 TRADING SIGNAL: Smart Money vs Dumb Money direction",
            "--scan-all <condition_id>": "Find BOTH winners AND losers in one JSON",
            "--scan-winners <condition_id>": "Find winning wallets only",
            "--scan-losers <condition_id>": "Find losing wallets only",
            "--min-trades N": "Set minimum global trades filter (default 1000)",
            "--min-pnl N": "Set minimum absolute PnL filter (default 0)",
            "--show-all": "Show all traders",
            "--show-prices": "Show current market prices",
            "--verbose": "Show all details"
        }}))
        sys.exit(1)

    url = sys.argv[1]

    # Parse command line options
    show_all_traders = "--show-all" in sys.argv or "--verbose" in sys.argv
    show_prices = "--show-prices" in sys.argv or "--verbose" in sys.argv
    try:
        event_slug = extract_event_slug(url)
        markets = get_event_markets(event_slug)

        if not markets:
            print(json.dumps({"error": f"No markets found for event: {event_slug}"}))
            sys.exit(1)

        results = {
            "event_slug": event_slug,
            "markets": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        print(f"Found {len(markets)} markets. Starting analysis...", file=sys.stderr)

        for i, market in enumerate(markets, 1):
            market_id = market.get('conditionId', market.get('id', ''))
            question = market.get('question', 'Unknown')
            print(f"[{i}/{len(markets)}] Analyzing: {question[:50]}...", file=sys.stderr)
            
            if not market_id: continue

            # Get current prices
            outcome_prices = market.get('outcomePrices', [])
            current_prices = {}
            if outcome_prices and len(outcome_prices) >= 2:
                try:
                    if isinstance(outcome_prices, str): outcome_prices = json.loads(outcome_prices)
                    current_prices = {"yes": float(outcome_prices[0]), "no": float(outcome_prices[1])}
                except: pass

            # Get data
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_pos = executor.submit(get_positions, market_id)
                future_trades = executor.submit(get_trades, market_id)
                positions = future_pos.result()
                trades = future_trades.result()

            # If no positions, try token holders
            if not positions:
                tokens = market.get('clobTokenIds', [])
                if isinstance(tokens, str): tokens = json.loads(tokens)
                if tokens:
                    all_holders = []
                    for i, token_id in enumerate(tokens):
                        holders = get_token_holders(token_id)
                        outcome = "YES" if i == 0 else "NO"
                        for h in holders: h['outcome'] = outcome
                        all_holders.extend(holders)
                    positions = all_holders

            # Analyze
            wallet_analysis = analyze_wallet_distribution(positions, trades, current_prices)
            trade_analysis = analyze_trades(trades)
            
            # Add lifetime volume for context
            lifetime_volume = float(market.get('volume', 0)) if market.get('volume') else 0

            results["markets"].append({
                "question": market.get('question', 'Unknown'),
                "lifetime_volume": lifetime_volume,
                "analyzed_recent_volume": trade_analysis.get('total_volume', 0),
                "wallet_analysis": wallet_analysis,
                "trade_analysis": trade_analysis
            })

        # === 將原本的 JSON print 換成下面這個 Report ===

        print("\n" + "="*80)
        print(f"🐋 WHALE ANALYSIS REPORT: {event_slug}")
        print("="*80)

        for market in results["markets"]:
            q = market['question']
            vol = market['trade_analysis'].get('total_volume', 0)
            lifetime_vol = market.get('lifetime_volume', 0)

            print(f"\n📌 市場: {q}")
            print(f"💰 近期分析交易量: ${vol:,.2f} (總成交量: ${lifetime_vol:,.2f})")

            # 顯示市場價格信息（如果啟用）
            if show_prices:
                market_data = next((m for m in markets if m.get('question') == q), {})
                if market_data:
                    outcome_prices = market_data.get('outcomePrices', [])
                    if outcome_prices:
                        try:
                            if isinstance(outcome_prices, str):
                                outcome_prices = json.loads(outcome_prices)
                            if len(outcome_prices) >= 2:
                                yes_price = float(outcome_prices[0]) * 100
                                no_price = float(outcome_prices[1]) * 100
                                print(f"📊 市場價格: YES {yes_price:.1f}% | NO {no_price:.1f}%")
                        except:
                            pass

            print("-" * 80)

            # 1. Top Traders 分析
            traders = market['trade_analysis'].get('top_traders', [])
            if traders:
                print(f"{'Wallet':<42} | {'Role':<10} | {'Volume':<10} | {'%':<6} | {'Direction'}")
                print("-" * 85)

                limit = 20 if show_all_traders else 10
                for t in traders[:limit]:
                    w = t['wallet']
                    role = "🐋 WHALE" if t['pct_of_volume'] > 10 else "🦈 SHARK" if t['pct_of_volume'] > 5 else "🐟 FISH"
                    direction = "🔴 SELL" if t['net_direction'] == "SELLER" else "🟢 BUY"
                    print(f"{w:<42} | {role:<10} | ${t['total_volume']:<9,.0f} | {t['pct_of_volume']:>5.1f}% | {direction}")

            # 2. Sync-Trade Clusters (新增部分!)
            clusters = market['trade_analysis'].get('suspicious_clusters', [])
            if clusters:
                print("-" * 80)
                print("🤖 疑似機械人集群 (Suspicious Bot Clusters):")
                print("   (多個錢包在同一秒鐘交易)")
                for c in clusters:
                    ts = int(c['timestamp'])
                    dt = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    wallets_str = ", ".join([w[:6] for w in c['wallets']])
                    print(f"   ⚠️  {dt} | {c['count']} Wallets | [{wallets_str}]")

            # 4. Large Trades
            print("-" * 80)
            large_trades = market['trade_analysis'].get('large_trades', [])
            if large_trades:
                print("🚨 最近大額異動 (Large Trades):")
                for t in large_trades[:5]:
                    ts = int(t['timestamp'])
                    dt_object = datetime.fromtimestamp(ts)
                    time_str = dt_object.strftime('%H:%M:%S')
                    side_icon = "🔴" if t['side'] == "SELL" else "🟢"
                    print(f"   ⏰ {time_str} {side_icon} {t['side']} ${t['value']:.2f} by {t['wallet']}")

            # 5. Smart Money
            print("-" * 80)
            smart_money = market['wallet_analysis'].get('smart_money_analysis', {})
            smart_wallets = smart_money.get('smart_money_wallets', [])
            if smart_wallets:
                print(f"🧠 Smart Money (ROI > 0):")
                for i, sm in enumerate(smart_wallets[:5], 1):
                    wallet_short = sm['wallet'][:15] + "..."
                    print(f"   {i}. {wallet_short:<15} | ROI: {sm['roi_percentage']:+.1f}% | 投資: ${sm['total_investment']:,.0f}")
            else:
                print("🧠 Smart Money: 未檢測到")

        print("\n" + "="*80)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
