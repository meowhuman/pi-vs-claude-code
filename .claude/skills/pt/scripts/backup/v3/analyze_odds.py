#!/usr/bin/env python3
"""
Polymarket Event Odds Analyzer with Historical Lookback
分析整個 event 嘅所有子市場賠率 + 歷史回顧 (7天、14天、30天前)

Features:
- 📊 Current odds analysis
- 📅 Historical lookback (7d, 14d, 30d ago)
- 📈 Price change detection
- 🚨 Identifies significant movements
- 💡 Trend analysis

Usage:
    python analyze_event_odds_with_history.py <event_slug> [OPTIONS]

Examples:
    # 基本分析（7天回顧）
    python analyze_event_odds_with_history.py "which-company-will-have-the-best-ai-model-for-coding-at-the-end-of-2025"

    # 指定回顧期間
    python analyze_event_odds_with_history.py "EVENT_SLUG" --lookback 7,14,30

    # 保存報告
    python analyze_event_odds_with_history.py "EVENT_SLUG" --output /path/to/report.md
"""

import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

GAMMA_API = "https://gamma-api.polymarket.com"


def fetch_event_data(event_slug: str) -> Optional[Dict]:
    """獲取 event 完整數據 - 支援 slug 或 keyword 搜尋"""
    try:
        # Try 1: Exact slug match
        url = f"{GAMMA_API}/events?slug={event_slug}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                event = data[0] if isinstance(data, list) else data
                return event
        
        # Try 2: Search by title_contains (keyword search)
        print(f"  ⚠️ Exact slug not found, trying keyword search...")
        url = f"{GAMMA_API}/events?title_contains={event_slug}&active=true&limit=10"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # Show matches and pick the first
                print(f"  Found {len(data)} matching events:")
                for i, e in enumerate(data[:5]):
                    print(f"    {i+1}. {e.get('title', '?')[:60]}")
                event = data[0]
                print(f"  → Using: {event.get('title', '?')}")
                return event
        
        print(f"❌ 找不到 event: {event_slug}")
        return None

    except Exception as e:
        print(f"❌ 獲取數據失敗: {e}")
        return None


def get_historical_prices(clob_token_id: str, days_ago: int = 30) -> Dict[str, float]:
    """
    獲取歷史價格數據 (使用 CLOB API)
    Get historical prices using CLOB API

    Args:
        clob_token_id: The CLOB Token ID (Asset ID) for the 'Yes' outcome
        days_ago: How many days back to fetch

    Returns:
        Dict with historical prices by date
    """
    try:
        # 正確的 CLOB API Endpoint
        url = "https://clob.polymarket.com/prices-history"

        # 計算開始時間 (Unix timestamp) - 🟢 修正：加多幾日buffer
        start_ts = int((datetime.now() - timedelta(days=days_ago + 5)).timestamp())

        params = {
            "market": clob_token_id,  # 使用 clobTokenId
            "interval": "1d",         # 每日數據
            "fidelity": 1000,         # 數據密度
            "startTs": start_ts       # 🟢 修正：必須傳 startTs 參數！
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"⚠️  API Error: {response.status_code}")
            return {}

        data = response.json()

        # CLOB API 返回格式: { "history": [...] }
        history_data = data.get('history', [])

        if not history_data:
            return {}

        daily_prices = {}
        for entry in history_data:
            t = entry.get('t', 0)
            p = entry.get('p', 0)

            if t and p:
                # Convert timestamp to date
                date = datetime.fromtimestamp(t).strftime('%Y-%m-%d')

                # interval="1d" 一日一個數據
                daily_prices[date] = float(p)

        return daily_prices

    except Exception as e:
        print(f"⚠️  獲取歷史價格失敗 ({clob_token_id[:8]}...): {e}")
        return {}


def get_price_at_date(daily_prices: Dict[str, float], target_date: datetime) -> Optional[float]:
    """
    獲取指定日期嘅價格（或最接近嘅日期）
    Get price at specific date (or closest available)
    """
    if not daily_prices:
        return None

    target_str = target_date.strftime('%Y-%m-%d')

    # Try exact date first
    if target_str in daily_prices:
        return daily_prices[target_str]

    # Find closest date within ±3 days
    for offset in range(-3, 4):
        check_date = (target_date + timedelta(days=offset)).strftime('%Y-%m-%d')
        if check_date in daily_prices:
            return daily_prices[check_date]

    return None


def analyze_market_with_history(event: Dict, lookback_days: List[int]) -> List[Dict]:
    """
    分析所有子市場嘅賠率 + 歷史數據
    Analyze all sub-markets with historical data
    """
    markets = event.get('markets', [])
    results = []

    # Calculate lookback dates
    now = datetime.now()
    lookback_dates = {days: now - timedelta(days=days) for days in lookback_days}

    for market in markets:
        question = market.get('question', '')
        outcome_prices_str = market.get('outcomePrices', '["0", "0"]')

        try:
            outcome_prices = json.loads(outcome_prices_str)
            current_yes_price = float(outcome_prices[0])
            current_no_price = float(outcome_prices[1])
        except:
            current_yes_price = 0
            current_no_price = 0

        # Fix: Handle different market types properly
        company = market.get('groupItemTitle') or question
        # Clean up common prefixes for better display
        if company.startswith('Will '):
            company = company[4:]
        if company.endswith('?'):
            company = company[:-1]
        company = company.strip()

        volume_24h = float(market.get('volume24hr', 0))
        total_volume = float(market.get('volumeNum', 0))
        liquidity = float(market.get('liquidityNum', 0))
        condition_id = market.get('conditionId', '')

        # 🟢 修正重點：獲取 clobTokenIds
        # clobTokenIds[0] 通常係 "Yes" token，[1] 係 "No" token
        clob_token_ids_str = market.get('clobTokenIds', '[]')
        try:
            clob_token_ids = json.loads(clob_token_ids_str) if isinstance(clob_token_ids_str, str) else clob_token_ids_str
            yes_token_id = clob_token_ids[0] if clob_token_ids and len(clob_token_ids) > 0 else None
        except:
            yes_token_id = None

        # Current metrics
        current_yes_prob = current_yes_price * 100
        current_odds = (1 / current_yes_price) if current_yes_price > 0 else 0

        market_data = {
            'company': company,
            'question': question,
            'condition_id': condition_id,
            'yes_token_id': yes_token_id,
            'current_yes_price': current_yes_price,
            'current_yes_prob': current_yes_prob,
            'current_odds': current_odds,
            'volume_24h': volume_24h,
            'total_volume': total_volume,
            'liquidity': liquidity,
            'historical': {}
        }

        # Fetch historical prices
        if yes_token_id:  # 🟢 改用 yes_token_id
            print(f"  📊 正在獲取 {company} 歷史數據 (Token: {yes_token_id[:8]}...)...")
            daily_prices = get_historical_prices(yes_token_id, max(lookback_days))

            for days in lookback_days:
                target_date = lookback_dates[days]
                historical_price = get_price_at_date(daily_prices, target_date)

                if historical_price is not None:
                    historical_prob = historical_price * 100
                    change = current_yes_prob - historical_prob
                    change_pct = (change / historical_prob * 100) if historical_prob > 0 else 0

                    market_data['historical'][f'{days}d'] = {
                        'price': historical_price,
                        'prob': historical_prob,
                        'change': change,
                        'change_pct': change_pct,
                        'date': target_date.strftime('%Y-%m-%d')
                    }
        else:
            print(f"  ⚠️  跳過歷史數據：找不到 Token ID for {company}")

        if volume_24h > 0:
            results.append(market_data)

    # Sort by current probability
    results.sort(key=lambda x: x['current_yes_prob'], reverse=True)

    return results


def print_analysis_with_lookback(results: List[Dict], event_title: str, lookback_days: List[int]):
    """
    打印完整分析報告（包含歷史回顧）
    """
    print("\n" + "="*100)
    print(f"📊 {event_title}")
    print(f"📅 回顧期間: {', '.join([f'{d}天' for d in lookback_days])}")
    print("="*100 + "\n")

    # Find significant movers
    significant_movers = []
    for r in results:
        for days in lookback_days:
            key = f'{days}d'
            if key in r['historical']:
                hist = r['historical'][key]
                if abs(hist['change']) > 5:  # >5% absolute change
                    significant_movers.append({
                        'company': r['company'],
                        'days': days,
                        'change': hist['change'],
                        'change_pct': hist['change_pct'],
                        'from': hist['prob'],
                        'to': r['current_yes_prob']
                    })

    # Print alerts if any
    if significant_movers:
        print("🚨" + "="*98 + "🚨")
        print("⚠️  顯著變化警報 - 以下市場出現 >5% 機率變化")
        print("🚨" + "="*98 + "🚨\n")

        significant_movers.sort(key=lambda x: abs(x['change']), reverse=True)

        for i, mover in enumerate(significant_movers[:10], 1):
            arrow = "📈" if mover['change'] > 0 else "📉"
            print(f"{i}. {arrow} {mover['company']} ({mover['days']}天變化)")
            print(f"   {mover['from']:.2f}% → {mover['to']:.2f}% ({mover['change']:+.2f}%, 相對變化 {mover['change_pct']:+.2f}%)")

        print("\n" + "="*100 + "\n")

    # Print main analysis
    for i, r in enumerate(results, 1):
        print(f"{i}. 🏢 {r['company']}")
        print(f"   {'━'*92}")
        print(f"   當前 YES 價格: ${r['current_yes_price']:.4f} | 隱含機率: {r['current_yes_prob']:.2f}%")
        print(f"   當前賠率: {r['current_odds']:.2f}x")

        # Historical comparison
        if r['historical']:
            print(f"   {'─'*92}")
            print(f"   📅 歷史回顧:")

            for days in sorted(lookback_days):
                key = f'{days}d'
                if key in r['historical']:
                    hist = r['historical'][key]
                    arrow = "📈" if hist['change'] > 0 else "📉" if hist['change'] < 0 else "➡️"

                    # Highlight significant changes
                    if abs(hist['change']) > 5:
                        highlight = "🚨 "
                    elif abs(hist['change']) > 2:
                        highlight = "⚠️  "
                    else:
                        highlight = "   "

                    print(f"      {highlight}{days}天前: {hist['prob']:.2f}% → {arrow} {hist['change']:+.2f}% "
                          f"(相對 {hist['change_pct']:+.2f}%) [{hist['date']}]")

        print(f"   {'━'*92}")
        print(f"   24h 交易量: ${r['volume_24h']:,.2f} | 總交易量: ${r['total_volume']:,.2f}")

        # Market consensus
        if r['current_yes_prob'] >= 50:
            print(f"   ⭐⭐⭐ 市場共識: 極高機會")
        elif r['current_yes_prob'] >= 30:
            print(f"   ⭐⭐ 市場共識: 高機會")
        elif r['current_yes_prob'] >= 15:
            print(f"   ⭐ 市場共識: 中等機會")
        else:
            print(f"   🔵 市場共識: 低機會")

        print()

    # Summary statistics
    print("\n" + "="*100)
    print("📊 趨勢分析總結")
    print("="*100 + "\n")

    for days in lookback_days:
        markets_with_data = [r for r in results if f'{days}d' in r['historical']]
        if markets_with_data:
            avg_change = sum(r['historical'][f'{days}d']['change'] for r in markets_with_data) / len(markets_with_data)
            up_count = sum(1 for r in markets_with_data if r['historical'][f'{days}d']['change'] > 0)
            down_count = sum(1 for r in markets_with_data if r['historical'][f'{days}d']['change'] < 0)

            print(f"過去 {days} 天:")
            print(f"  • 平均變化: {avg_change:+.2f}%")
            print(f"  • 上升市場: {up_count} 個 📈")
            print(f"  • 下降市場: {down_count} 個 📉")
            print()

    print("="*100 + "\n")


def generate_alert_json(results: List[Dict], event_title: str, threshold: float = 10.0) -> Dict:
    """
    生成警報 JSON (適合 webhook/Telegram)
    Only includes markets with >threshold% change
    """
    alerts = []
    for r in results:
        for period, hist in r.get('historical', {}).items():
            if abs(hist['change']) >= threshold:
                alerts.append({
                    "market": r['company'],
                    "period": period,
                    "from_prob": round(hist['prob'], 2),
                    "to_prob": round(r['current_yes_prob'], 2),
                    "change": round(hist['change'], 2),
                    "change_pct": round(hist['change_pct'], 2),
                    "direction": "UP" if hist['change'] > 0 else "DOWN",
                    "current_odds": round(r['current_odds'], 2)
                })
    
    # Sort by absolute change
    alerts.sort(key=lambda x: abs(x['change']), reverse=True)
    
    return {
        "event": event_title,
        "timestamp": datetime.now().isoformat(),
        "alert_threshold": threshold,
        "alert_count": len(alerts),
        "alerts": alerts
    }


def fetch_single_market(condition_id: str) -> Optional[Dict]:
    """獲取單一市場數據 (by condition_id) - 優先用 trades API 取得正確名稱"""
    try:
        # FIRST: Try trades API (more reliable for market name)
        print(f"  📊 Fetching market info from trades...")
        url = f"https://data-api.polymarket.com/trades?market={condition_id}&limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                trade = data[0]
                market_title = trade.get("title", "Unknown Market")
                asset_id = trade.get("asset")
                
                print(f"  ✅ Found: {market_title[:50]}...")
                
                # Try to get additional market data from Gamma
                gamma_data = {}
                try:
                    gamma_resp = requests.get(f"{GAMMA_API}/markets?conditionId={condition_id}", timeout=5)
                    if gamma_resp.status_code == 200:
                        gamma_markets = gamma_resp.json()
                        # Find the correct market by matching title
                        for m in gamma_markets:
                            if m.get("question") == market_title:
                                gamma_data = m
                                break
                except:
                    pass
                
                return {
                    "title": market_title,
                    "markets": [{
                        "question": market_title,
                        "groupItemTitle": market_title,
                        "conditionId": condition_id,
                        "clobTokenIds": json.dumps([asset_id]) if asset_id else gamma_data.get("clobTokenIds", "[]"),
                        "outcomePrices": gamma_data.get("outcomePrices", "[\"0\", \"0\"]"),
                        "volume24hr": gamma_data.get("volume24hr", 1),  # Set to 1 to pass filter
                        "volumeNum": gamma_data.get("volumeNum", 0),
                        "liquidityNum": gamma_data.get("liquidityNum", 0)
                    }]
                }
        
        print(f"❌ 找不到市場: {condition_id}")
        return None
    except Exception as e:
        print(f"❌ 獲取市場失敗: {e}")
        return None


def save_markdown_report(results: List[Dict], event_title: str, lookback_days: List[int], filepath: str):
    """保存報告為 Markdown 檔案"""
    lines = []
    lines.append(f"# 📊 {event_title}")
    lines.append(f"")
    lines.append(f"**分析時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**回顧期間**: {', '.join([f'{d}天' for d in lookback_days])}")
    lines.append(f"")
    
    # Significant movers
    significant = []
    for r in results:
        for days in lookback_days:
            key = f'{days}d'
            if key in r['historical'] and abs(r['historical'][key]['change']) > 5:
                significant.append({
                    'company': r['company'],
                    'days': days,
                    'change': r['historical'][key]['change'],
                    'from': r['historical'][key]['prob'],
                    'to': r['current_yes_prob']
                })
    
    if significant:
        lines.append(f"## 🚨 顯著變化警報 (>5%)")
        lines.append(f"")
        significant.sort(key=lambda x: abs(x['change']), reverse=True)
        for s in significant[:10]:
            arrow = "📈" if s['change'] > 0 else "📉"
            lines.append(f"- {arrow} **{s['company']}** ({s['days']}天): {s['from']:.1f}% → {s['to']:.1f}% ({s['change']:+.1f}%)")
        lines.append(f"")
    
    # Market table
    lines.append(f"## 📋 市場概覽")
    lines.append(f"")
    lines.append(f"| 市場 | 當前機率 | 賠率 | 24h交易量 |")
    lines.append(f"|------|----------|------|-----------|")
    for r in results:
        lines.append(f"| {r['company'][:20]} | {r['current_yes_prob']:.1f}% | {r['current_odds']:.2f}x | ${r['volume_24h']:,.0f} |")
    lines.append(f"")
    
    # Historical details
    lines.append(f"## 📅 歷史回顧詳情")
    lines.append(f"")
    for r in results:
        lines.append(f"### {r['company']}")
        lines.append(f"- 當前: {r['current_yes_prob']:.2f}% ({r['current_odds']:.2f}x)")
        for days in sorted(lookback_days):
            key = f'{days}d'
            if key in r['historical']:
                h = r['historical'][key]
                lines.append(f"- {days}天前: {h['prob']:.2f}% → {h['change']:+.2f}%")
        lines.append(f"")
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"💾 報告已保存: {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Analyze Polymarket event odds with historical lookback')
    parser.add_argument('event_slug', nargs='?', help='Event slug (from URL)')
    parser.add_argument('--market', '-m', help='Analyze single market by condition ID')
    parser.add_argument('--lookback', help='Lookback periods in days (comma-separated, e.g., "7,14,30")',
                       default='7,14,30')
    parser.add_argument('--output', '-o', help='Output file path (Markdown format)', default=None)
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--alert', action='store_true', help='Output alert JSON only (for webhook/Telegram)')
    parser.add_argument('--alert-threshold', type=float, default=10.0, 
                       help='Alert threshold percentage (default: 10)')

    args = parser.parse_args()

    # Parse lookback periods
    try:
        lookback_days = [int(d.strip()) for d in args.lookback.split(',')]
    except:
        print("❌ 無效的回顧期間格式，請使用 '7,14,30' 格式")
        sys.exit(1)

    # Determine data source
    if args.market:
        # Single market mode
        print(f"\n🔍 正在獲取市場數據... / Fetching market data...")
        event = fetch_single_market(args.market)
        if not event:
            print("❌ 無法獲取市場數據")
            sys.exit(1)
    elif args.event_slug:
        # Event mode
        print(f"\n🔍 正在獲取 event 數據... / Fetching event data...")
        event = fetch_event_data(args.event_slug)
        if not event:
            print("❌ 無法獲取 event 數據")
            sys.exit(1)
    else:
        print("❌ 請提供 event_slug 或 --market <condition_id>")
        sys.exit(1)

    event_title = event.get('title', 'Unknown Event')
    print(f"✅ 已找到: {event_title}")

    # Analyze with historical data
    print(f"📊 正在分析賠率同歷史數據... / Analyzing odds with historical data...")
    results = analyze_market_with_history(event, lookback_days)

    if not results:
        print("❌ 沒有活躍市場")
        sys.exit(1)

    print(f"✅ 已分析 {len(results)} 個活躍市場\n")

    # Output mode selection
    if args.alert:
        # Alert JSON mode (for webhook/Telegram)
        alert_data = generate_alert_json(results, event_title, args.alert_threshold)
        print(json.dumps(alert_data, indent=2, ensure_ascii=False))
    elif args.json:
        # Full JSON mode
        output = {
            'event_title': event_title,
            'event_slug': args.event_slug or args.market,
            'timestamp': datetime.now().isoformat(),
            'lookback_days': lookback_days,
            'markets': results
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Pretty print mode
        print_analysis_with_lookback(results, event_title, lookback_days)

    # Save report if requested
    if args.output:
        save_markdown_report(results, event_title, lookback_days, args.output)


if __name__ == "__main__":
    main()
