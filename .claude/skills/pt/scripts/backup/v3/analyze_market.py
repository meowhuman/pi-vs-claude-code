#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""
Polymarket Market Analyzer
Fetches and analyzes wallet distribution, whale positions, and trading patterns.
"""

import sys
import json
import re
from urllib.parse import urlparse, parse_qs
import requests
from collections import defaultdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://data-api.polymarket.com"
GAMMA_URL = "https://gamma-api.polymarket.com"

def extract_event_slug(url: str) -> str:
    """Extract event slug from Polymarket URL or return market ID if provided."""
    # Check if this is a direct market ID (hex string starting with 0x)
    if url.startswith('0x') and len(url) == 66:
        return url

    # Check if this is a numeric market ID
    if url.isdigit():
        return f"market_id:{url}"

    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    if 'event' in path_parts:
        idx = path_parts.index('event')
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]

    raise ValueError(f"Could not extract event slug from URL: {url}")

def get_event_markets(event_slug: str) -> list:
    """Get all markets for an event or return single market if market ID provided."""
    # If this is a numeric market ID (market_id:239826 format), fetch just that market
    if event_slug.startswith('market_id:'):
        market_id = event_slug.replace('market_id:', '')
        resp = requests.get(f"{GAMMA_URL}/markets/{market_id}")
        if resp.status_code == 200:
            return [resp.json()]
        return []

    # If this is a direct market ID (0x... format), fetch just that market
    if event_slug.startswith('0x') and len(event_slug) == 66:
        # FIX: Use query param instead of path param for Condition IDs
        resp = requests.get(f"{GAMMA_URL}/markets", params={"condition_id": event_slug})
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            return [data]
        return []

    # Try gamma API for event info
    resp = requests.get(f"{GAMMA_URL}/events", params={"slug": event_slug})
    if resp.status_code == 200:
        events = resp.json()
        if events:
            return events[0].get('markets', [])

    # Fallback: try to get markets directly
    resp = requests.get(f"{GAMMA_URL}/markets", params={"slug": event_slug})
    if resp.status_code == 200:
        return resp.json()

    return []

def get_market_info(condition_id: str) -> dict:
    """Get market details."""
    resp = requests.get(f"{GAMMA_URL}/markets", params={"condition_id": condition_id})
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]
        return data
    return {}

def get_positions(condition_id: str) -> list:
    """Get all positions for a market."""
    positions = []
    offset = 0
    limit = 100

    while True:
        resp = requests.get(
            f"{BASE_URL}/positions",
            params={
                "market": condition_id,
                "limit": limit,
                "offset": offset
            }
        )
        if resp.status_code != 200:
            break

        data = resp.json()
        if not data:
            break

        positions.extend(data)
        if len(data) < limit:
            break
        offset += limit

    return positions

def get_token_holders(token_id: str) -> list:
    """Get holders for a specific token."""
    holders = []
    offset = 0
    limit = 100

    while True:
        resp = requests.get(
            f"{BASE_URL}/holders",
            params={
                "token": token_id,
                "limit": limit,
                "offset": offset
            }
        )
        if resp.status_code != 200:
            break

        data = resp.json()
        if not data:
            break

        holders.extend(data)
        if len(data) < limit:
            break
        offset += limit

    return holders

def get_leaderboard(market_id: str) -> list:
    """Get market leaderboard showing top traders."""
    resp = requests.get(
        f"{BASE_URL}/leaderboard",
        params={"market": market_id}
    )
    if resp.status_code == 200:
        return resp.json()
    return []

def get_trades(condition_id: str, limit: int = 500) -> list:
    """Get recent trades for a market."""
    resp = requests.get(
        f"{BASE_URL}/trades",
        params={
            "market": condition_id,
            "limit": limit
        }
    )
    if resp.status_code == 200:
        return resp.json()
    return []

def get_activity(condition_id: str, limit: int = 500) -> list:
    """Get market activity including all trades with wallet info."""
    resp = requests.get(
        f"{BASE_URL}/activity",
        params={
            "market": condition_id,
            "limit": limit
        }
    )
    if resp.status_code == 200:
        return resp.json()
    return []

def get_historical_prices(condition_id: str, days: int = 7) -> dict:
    """Get historical price data for time series analysis."""
    try:
        # Try to get price history from CLOB rewards endpoint
        resp = requests.get(
            f"{GAMMA_URL}/clob/rewards/prices",
            params={"token": condition_id}
        )
        if resp.status_code == 200:
            return resp.json()

        # Alternative: Get historical trades and extract price movements
        trades = get_trades(condition_id, limit=1000)
        if trades:
            # Group trades by time buckets (e.g., hourly)
            time_buckets = defaultdict(list)
            for trade in trades:
                timestamp = str(trade.get('timestamp', ''))
                if timestamp:
                    # Extract date part for grouping
                    date_key = timestamp[:10]  # YYYY-MM-DD
                    time_buckets[date_key].append(float(trade.get('price', 0)))

            # Calculate OHLC for each time bucket
            price_history = {}
            for date, prices in sorted(time_buckets.items()):
                if prices:
                    price_history[date] = {
                        "open": prices[0],
                        "high": max(prices),
                        "low": min(prices),
                        "close": prices[-1],
                        "volume": len(prices)
                    }

            return price_history

    except Exception as e:
        # Fail silently for optional historical data
        pass

    return {}

def analyze_price_momentum(price_history: dict) -> dict:
    """Analyze price momentum and detect unusual movements."""
    if not price_history or len(price_history) < 2:
        return {"momentum": "INSUFFICIENT_DATA"}

    dates = sorted(price_history.keys())
    recent_prices = [price_history[date]["close"] for date in dates[-7:]]  # Last 7 periods
    older_prices = [price_history[date]["close"] for date in dates[:-7]] if len(dates) > 7 else []

    # Calculate momentum indicators
    current_price = recent_prices[-1] if recent_prices else 0
    price_change_7d = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) if len(recent_prices) > 1 and recent_prices[0] > 0 else 0

    # Detect unusual spikes
    price_spikes = []
    for i in range(1, len(recent_prices)):
        change = ((recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]) if recent_prices[i-1] > 0 else 0
        if abs(change) > 0.2:  # 20%+ change
            price_spikes.append({
                "date": dates[-(len(recent_prices)-i)],
                "change": round(change * 100, 2),
                "direction": "SPIKE_UP" if change > 0 else "SPIKE_DOWN"
            })

    # Momentum classification
    momentum_score = 0
    if price_change_7d > 0.5:
        momentum_score = 3  # Strong upward
    elif price_change_7d > 0.2:
        momentum_score = 2  # Moderate upward
    elif price_change_7d > 0:
        momentum_score = 1  # Slight upward
    elif price_change_7d > -0.2:
        momentum_score = 0  # Stable
    else:
        momentum_score = -1  # Downward

    momentum_labels = {
        3: "STRONG_BULLISH",
        2: "BULLISH",
        1: "SLIGHTLY_BULLISH",
        0: "NEUTRAL",
        -1: "BEARISH"
    }

    return {
        "momentum": momentum_labels.get(momentum_score, "NEUTRAL"),
        "momentum_score": momentum_score,
        "price_change_7d": round(price_change_7d * 100, 2),
        "current_price": current_price,
        "price_spikes": price_spikes,
        "volatility": "HIGH" if len(price_spikes) >= 2 else ("MODERATE" if len(price_spikes) == 1 else "LOW")
    }

def calculate_roi_and_smart_money(wallet_trades: list, current_prices: dict) -> dict:
    """Calculate ROI for each wallet with proper YES/NO outcome separation."""
    # Structure: wallet -> {yes: {cost, shares, realized}, no: {cost, shares, realized}, metadata}
    wallet_metrics = defaultdict(lambda: {
        "yes": {"cost": 0, "shares": 0, "realized": 0},
        "no": {"cost": 0, "shares": 0, "realized": 0},
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

        outcome_index = trade.get('outcomeIndex')
        outcome_str = trade.get('outcome', '').upper()

        if outcome_index is not None:
            outcome_key = 'yes' if str(outcome_index) == '0' else 'no'
        elif outcome_str in ['YES', 'NO']:
            outcome_key = outcome_str.lower()
        else:
            outcome_key = 'yes'

        # Update trade timing
        metadata = wallet_metrics[wallet]["metadata"]
        if timestamp:
            if not metadata["first_trade_time"] or timestamp < metadata["first_trade_time"]:
                metadata["first_trade_time"] = timestamp
            if not metadata["last_trade_time"] or timestamp > metadata["last_trade_time"]:
                metadata["last_trade_time"] = timestamp

        metadata["trade_count"] += 1

        # Update outcome-specific metrics
        outcome_metrics = wallet_metrics[wallet][outcome_key]

        if side == 'buy':
            outcome_metrics["cost"] += size * price
            outcome_metrics["shares"] += size
        elif side == 'sell':
            outcome_metrics["realized"] += size * price
            # Simple FIFO cost basis reduction
            if outcome_metrics["shares"] >= size:
                avg_cost_per_share = outcome_metrics["cost"] / outcome_metrics["shares"] if outcome_metrics["shares"] > 0 else 0
                outcome_metrics["cost"] -= size * avg_cost_per_share
                outcome_metrics["shares"] -= size

    # Calculate ROI and identify smart money
    smart_money_wallets = []

    for wallet, outcomes in wallet_metrics.items():
        # Calculate totals across both outcomes
        yes_cost = outcomes['yes']['cost']
        no_cost = outcomes['no']['cost']
        yes_shares = outcomes['yes']['shares']
        no_shares = outcomes['no']['shares']
        yes_realized = outcomes['yes']['realized']
        no_realized = outcomes['no']['realized']

        total_investment = yes_cost + no_cost

        # Filter out tiny traders
        if total_investment < 100:
            continue

        # Calculate current value for each outcome
        current_yes_value = yes_shares * current_prices.get('yes', 0)
        current_no_value = no_shares * current_prices.get('no', 0)
        current_total_value = current_yes_value + current_no_value

        # Total realized from both outcomes
        total_realized = yes_realized + no_realized

        # ROI = (Current Value + Realized - Total Cost) / Total Cost
        net_profit = (current_total_value + total_realized) - total_investment
        roi = net_profit / total_investment if total_investment > 0 else 0

        # Smart money criteria
        is_smart_money = False
        smart_reason = ""

        if roi > 5.0:
            is_smart_money = True
            smart_reason = "EXCEPTIONAL_PERFORMANCE"
        elif roi > 2.0:
            is_smart_money = True
            smart_reason = "HIGH_ROI"
        elif outcomes["metadata"]["trade_count"] > 15 and roi > 0.3:
            is_smart_money = True
            smart_reason = "ACTIVE_PROFITABLE_TRADER"
        elif total_investment > 20000 and roi > 0.8:
            is_smart_money = True
            smart_reason = "LARGE_PROFITABLE_INVESTOR"
        elif roi > 1.0 and outcomes["metadata"]["trade_count"] > 5:
            is_smart_money = True
            smart_reason = "SKILLED_TRADER"

        if is_smart_money:
            smart_money_wallets.append({
                "wallet": wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet,
                "full_wallet": wallet,
                "roi_percentage": round(roi * 100, 2),
                "total_investment": round(total_investment, 2),
                "current_value": round(current_total_value, 2),
                "realized_pnl": round(total_realized - (yes_cost + no_cost - current_total_value), 2),
                "trade_count": outcomes["metadata"]["trade_count"],
                "smart_reason": smart_reason,
                "position_breakdown": {
                    "yes_shares": round(yes_shares, 2),
                    "no_shares": round(no_shares, 2),
                    "yes_value": round(current_yes_value, 2),
                    "no_value": round(current_no_value, 2)
                }
            })

    return {
        "smart_money_wallets": sorted(smart_money_wallets, key=lambda x: x['roi_percentage'], reverse=True),
        "total_smart_money": len(smart_money_wallets)
    }

def analyze_wallet_distribution(positions: list, trades: list = None, current_prices: dict = None) -> dict:
    """Enhanced wallet distribution analysis with ROI and smart money detection."""
    if not positions:
        return {"error": "No positions found"}

    # Aggregate by wallet
    wallet_positions = defaultdict(lambda: {"yes": 0, "no": 0, "total": 0})

    for pos in positions:
        wallet = pos.get('user', pos.get('proxyWallet', 'unknown'))
        size = float(pos.get('size', 0))
        outcome = pos.get('outcome', '').lower()

        if 'yes' in outcome or outcome == 'yes':
            wallet_positions[wallet]['yes'] += size
        else:
            wallet_positions[wallet]['no'] += size
        wallet_positions[wallet]['total'] += size

    sorted_wallets = sorted(
        wallet_positions.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )

    total_value = sum(w[1]['total'] for w in sorted_wallets)

    whales = []
    for wallet, data in sorted_wallets[:20]:
        pct = (data['total'] / total_value * 100) if total_value > 0 else 0
        direction = "YES" if data['yes'] > data['no'] else "NO"

        whale_type = "MEGA_WHALE" if pct > 10 else ("WHALE" if pct > 5 else ("LARGE_HOLDER" if pct > 2 else "REGULAR"))

        whales.append({
            "wallet": wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet,
            "full_wallet": wallet,
            "yes_size": round(data['yes'], 2),
            "no_size": round(data['no'], 2),
            "total_size": round(data['total'], 2),
            "direction": direction,
            "pct_of_market": round(pct, 2),
            "whale_type": whale_type
        })

    top_10_pct = sum(w['pct_of_market'] for w in whales[:10])

    smart_money_analysis = {}
    if trades and current_prices:
        smart_money_analysis = calculate_roi_and_smart_money(trades, current_prices)

    return {
        "total_wallets": len(sorted_wallets),
        "total_market_value": round(total_value, 2),
        "avg_position": round(total_value / len(sorted_wallets), 2) if sorted_wallets else 0,
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
    """Analyze recent trade patterns and build wallet distribution from trades."""
    if not trades:
        return {"error": "No trades found"}

    large_trades = []
    wallet_volumes = defaultdict(lambda: {"buy": 0, "sell": 0, "total": 0, "trades": 0})

    for trade in trades:
        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0))
        value = size * price
        side = trade.get('side', '').upper()

        wallet = trade.get('proxyWallet', '') or trade.get('maker', '') or trade.get('taker', '')

        if wallet:
            if side == 'BUY':
                wallet_volumes[wallet]['buy'] += value
            else:
                wallet_volumes[wallet]['sell'] += value
            wallet_volumes[wallet]['total'] += value
            wallet_volumes[wallet]['trades'] += 1

        outcome_str = trade.get('outcome', '')
        if not outcome_str and trade.get('outcomeIndex') is not None:
            outcome_str = "YES" if str(trade.get('outcomeIndex')) == '0' else "NO"

        if value > 500:
            wallet_display = wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet
            large_trades.append({
                "timestamp": trade.get('timestamp', ''),
                "wallet": wallet_display,
                "full_wallet": wallet,
                "side": side,
                "outcome": outcome_str,
                "size": round(size, 2),
                "price": round(price, 4),
                "value": round(value, 2)
            })

    sorted_wallets = sorted(
        wallet_volumes.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )

    total_volume = sum(w[1]['total'] for w in sorted_wallets)

    top_traders = []
    for wallet, data in sorted_wallets[:15]:
        pct = (data['total'] / total_volume * 100) if total_volume > 0 else 0
        net_direction = "BUYER" if data['buy'] > data['sell'] else "SELLER"

        total_vol = data['total']
        net_position = abs(data['buy'] - data['sell'])
        is_market_maker = False
        role_label = "👤 TRADER"

        if total_vol > 50000 and (net_position / total_vol) < 0.05:
            is_market_maker = True
            role_label = "🏦 MARKET_MAKER"
        elif data['trades'] > 100 and (net_position / total_vol) < 0.1:
            is_market_maker = True
            role_label = "🤖 HIGH_FREQ"

        top_traders.append({
            "wallet": wallet[:10] + "..." + wallet[-6:] if len(wallet) > 20 else wallet,
            "full_wallet": wallet,
            "buy_volume": round(data['buy'], 2),
            "sell_volume": round(data['sell'], 2),
            "total_volume": round(data['total'], 2),
            "trade_count": data['trades'],
            "pct_of_volume": round(pct, 2),
            "net_direction": net_direction,
            "is_market_maker": is_market_maker,
            "role": role_label
        })

    top_5_pct = sum(t['pct_of_volume'] for t in top_traders[:5])
    top_10_pct = sum(t['pct_of_volume'] for t in top_traders[:10])

    return {
        "total_trades": len(trades),
        "unique_wallets": len(sorted_wallets),
        "total_volume": round(total_volume, 2),
        "avg_trade_size": round(total_volume / len(trades), 2) if trades else 0,
        "top_traders": top_traders,
        "concentration": {
            "top_5_pct": round(top_5_pct, 2),
            "top_10_pct": round(top_10_pct, 2),
            "whale_warning": top_5_pct > 40
        },
        "large_trades": large_trades[:10]
    }

def generate_quick_insights(market_data: dict) -> list:
    """Generate actionable insights from the analysis."""
    insights = []

    wallet_analysis = market_data.get("wallet_analysis", {})
    top_10_concentration = wallet_analysis.get("top_10_concentration", 0)
    whales = wallet_analysis.get("whales", [])
    smart_money = wallet_analysis.get("smart_money_analysis", {})

    if top_10_concentration > 70:
        insights.append("🚨 EXTREME CONCENTRATION: Top 10 wallets control >70% of market - high manipulation risk")
    elif top_10_concentration > 50:
        insights.append("⚠️ HIGH CONCENTRATION: Top 10 wallets control >50% of market")

    mega_whales = [w for w in whales if w.get('whale_type') == 'MEGA_WHALE']
    if mega_whales:
        insights.append(f"🐋 MEGA WHALE DETECTED: Single wallet controls {mega_whales[0]['pct_of_market']}% of market")

    if smart_money.get("total_smart_money", 0) > 0:
        top_smart = smart_money.get("smart_money_wallets", [])[0] if smart_money.get("smart_money_wallets") else None
        if top_smart and top_smart.get('roi_percentage', 0) > 200:
            insights.append(f"💰 SMART MONEY ALERT: Wallet with {top_smart['roi_percentage']}% ROI detected")

    volume = market_data.get("trade_analysis", {}).get("total_volume", 0)
    if volume < 1000:
        insights.append("💧 LOW LIQUIDITY: Very low trading volume - high slippage risk")

    return insights

def generate_llm_summary(market_data: dict) -> dict:
    """Generate LLM-friendly natural language summary from raw analysis data."""
    wallet_analysis = market_data.get("wallet_analysis", {})
    trade_analysis = market_data.get("trade_analysis", {})
    smart_money = wallet_analysis.get("smart_money_analysis", {})
    insider_risk = wallet_analysis.get("insider_risk", {})

    total_wallets = wallet_analysis.get("total_wallets", 0)
    total_value = wallet_analysis.get("total_market_value", 0)
    top_10_concentration = wallet_analysis.get("top_10_concentration", 0)

    whales = wallet_analysis.get("whales", [])[:3]
    whale_descriptions = []
    for whale in whales:
        whale_descriptions.append(
            f"{whale['wallet']} ({whale['direction']} - ${whale['total_size']} - {whale['pct_of_market']}%)"
        )

    smart_money_count = smart_money.get("total_smart_money", 0)
    smart_money_wallets = smart_money.get("smart_money_wallets", [])[:2]

    large_trades = trade_analysis.get("large_trades", [])
    mm_wallets = set()
    for trader in trade_analysis.get("top_traders", []):
        if trader.get("is_market_maker") and trader.get("full_wallet"):
            mm_wallets.add(trader["full_wallet"])

    significant_trades = []
    for t in large_trades:
        if t.get('value', 0) <= 10000:
            continue
        if t.get('full_wallet') in mm_wallets:
            continue
        outcome_display = f" {t.get('outcome', '')}" if t.get('outcome') else ""
        t['display_str'] = f"${t['value']} {t['side']}{outcome_display} by {t['wallet']}"
        significant_trades.append(t)

    significant_trades = significant_trades[:5]

    risk_level = "HIGH"
    if insider_risk.get("high_concentration") and insider_risk.get("mega_whales_present"):
        risk_level = "CRITICAL"
    elif not insider_risk.get("high_concentration"):
        risk_level = "LOW"
    elif insider_risk.get("few_large_wallets"):
        risk_level = "MEDIUM"

    return {
        "market_name": market_data.get("question", "Unknown Market"),
        "market_overview": {
            "total_wallets": total_wallets,
            "total_value_usd": total_value,
            "whale_concentration": "HIGH" if top_10_concentration > 50 else "MODERATE" if top_10_concentration > 25 else "LOW"
        },
        "key_players": {
            "top_3_whales": whale_descriptions,
            "smart_money_detected": smart_money_count > 0,
            "smart_money_count": smart_money_count,
            "top_smart_money_wallets": [
                f"{w['wallet']} (ROI: {w['roi_percentage']}%, Reason: {w['smart_reason']})"
                for w in smart_money_wallets
            ]
        },
        "activity_signals": {
            "large_trades_10k_plus": len(significant_trades),
            "notable_trades": [
                t['display_str'] for t in significant_trades[:5]
            ],
            "trade_volume_24h": trade_analysis.get("total_volume", 0),
            "unique_traders": trade_analysis.get("unique_wallets", 0)
        },
        "risk_assessment": {
            "insider_risk_level": risk_level,
            "concentration_warning": top_10_concentration > 50,
            "whale_dominance": len([w for w in whales if w['whale_type'] in ['MEGA_WHALE', 'WHALE']]) > 0,
            "market_manipulation_risk": "HIGH" if top_10_concentration > 70 else "MODERATE" if top_10_concentration > 50 else "LOW"
        },
        "quick_insights": generate_quick_insights(market_data)
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python analyze_market.py <market_id_or_url> [--summary-only]"}))
        sys.exit(1)

    url = sys.argv[1]
    summary_only = "--summary-only" in sys.argv

    try:
        event_slug = extract_event_slug(url)
        markets = get_event_markets(event_slug)

        if not markets:
            print(json.dumps({"error": f"No markets found for: {event_slug}"}))
            sys.exit(1)

        results = {
            "event_slug": event_slug,
            "markets": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis_version": "2.1-hybrid" 
        }

        for market in markets:
            market_id = market.get('conditionId', market.get('id', ''))
            if not market_id:
                continue

            # Handle different token formats
            tokens = market.get('clobTokenIds', [])
            if isinstance(tokens, str):
                try:
                    tokens = json.loads(tokens)
                except:
                    tokens = []
            
            # Outcome prices
            outcome_prices = market.get('outcomePrices', [])
            current_prices = {}
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    pass
            if outcome_prices and len(outcome_prices) >= 2:
                 # Check if outcome prices are strings or floats
                try:
                    current_prices = {
                        "yes": float(outcome_prices[0]),
                        "no": float(outcome_prices[1])
                    }
                except (ValueError, IndexError):
                    pass

            market_data = {
                "id": market_id,
                "question": market.get('question', market.get('title', 'Unknown')),
                "outcomes": market.get('outcomes', []),
                "outcome_prices": outcome_prices,
                "volume": market.get('volume', 0),
                "liquidity": market.get('liquidity', 0),
                "tokens": tokens,
            }

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_pos = executor.submit(get_positions, market_id)
                future_trades = executor.submit(get_trades, market_id)
                positions = future_pos.result()
                trades = future_trades.result()

            if not positions and tokens:
                all_holders = []
                outcomes_list = market.get('outcomes', [])
                if isinstance(outcomes_list, str):
                    try: outcomes_list = json.loads(outcomes_list)
                    except: outcomes_list = []
                
                for i, token_id in enumerate(tokens):
                    try:
                        holders = get_token_holders(token_id)
                        outcome_name = outcomes_list[i] if i < len(outcomes_list) else f"Outcome{i}"
                        for h in holders: h['outcome'] = outcome_name
                        all_holders.extend(holders)
                    except Exception as e:
                        pass
                if all_holders:
                    positions = all_holders

            market_data["wallet_analysis"] = analyze_wallet_distribution(positions, trades, current_prices)
            
            leaderboard = get_leaderboard(market_id)
            if leaderboard:
                market_data["leaderboard"] = leaderboard[:10]

            market_data["trade_analysis"] = analyze_trades(trades)
            
            price_history = get_historical_prices(market_id)
            if price_history:
                market_data["price_momentum"] = analyze_price_momentum(price_history)

            market_data["llm_summary"] = generate_llm_summary(market_data)
            results["markets"].append(market_data)

        if summary_only:
            summaries = [market["llm_summary"] for market in results["markets"]]
            print(json.dumps(summaries[0] if len(summaries)==1 else summaries, indent=2))
        else:
            print(json.dumps(results, indent=2))

    except Exception as e:
        # print error but don't crash hard if possible
        import traceback
        traceback.print_exc()
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
