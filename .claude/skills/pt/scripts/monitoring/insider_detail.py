#!/usr/bin/env python3
"""
Insider 詳細分析器 - 生成價格走勢圖表和內幕交易標註
使用香港時間 (HKT = UTC+8)
"""

import json
import requests
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# 香港時區 (UTC+8)
HKT = timezone(timedelta(hours=8))

def get_market_info(condition_id: str, cache_file: str = "cache/all_markets_cache_active.json") -> Optional[Dict]:
    """從緩存獲取市場資訊"""
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
            for m in data.get('markets', []):
                if m.get('conditionId') == condition_id:
                    return m
    except:
        pass
    return None

def get_token_id(market: Dict) -> Optional[str]:
    """獲取 token ID"""
    clob_ids = market.get('clobTokenIds', [])
    if isinstance(clob_ids, str):
        clob_ids = json.loads(clob_ids)
    return clob_ids[0] if clob_ids else None

def get_price_history(token_id: str, days: int = 17) -> List[Dict]:
    """獲取價格歷史"""
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    
    resp = requests.get(
        "https://clob.polymarket.com/prices-history",
        params={
            "market": token_id,
            "interval": "1d",
            "fidelity": 500,
            "startTs": start_ts
        },
        timeout=15
    )
    
    if resp.status_code != 200:
        return []
    
    history = resp.json().get('history', [])
    
    # 轉換為香港時間
    result = []
    for h in sorted(history, key=lambda x: x.get('t', 0)):
        ts = h.get('t', 0)
        price = h.get('p', 0) * 100  # 轉換為百分比
        dt = datetime.fromtimestamp(ts, tz=HKT)
        result.append({
            'timestamp': ts,
            'datetime': dt,
            'time_str': dt.strftime("%m-%d %H:%M"),
            'price': round(price, 2)
        })
    
    return result

def get_trades(condition_id: str, limit: int = 1000) -> List[Dict]:
    """獲取交易記錄"""
    resp = requests.get(
        "https://data-api.polymarket.com/trades",
        params={"market": condition_id, "limit": limit},
        timeout=15
    )
    
    if resp.status_code != 200:
        return []
    
    trades = resp.json()
    result = []
    
    for t in trades:
        ts = t.get('timestamp', 0)
        shares = float(t.get('size', 0) or 0)
        price = float(t.get('price', 0) or 0)
        usd_value = shares * price
        
        if usd_value >= 1000:  # 只顯示 >= $1000 的交易
            dt = datetime.fromtimestamp(ts, tz=HKT)
            result.append({
                'timestamp': ts,
                'datetime': dt,
                'time_str': dt.strftime("%m-%d %H:%M"),
                'wallet': t.get('proxyWallet', '?'),
                'usd_value': round(usd_value, 2),
                'shares': shares,
                'price': price,
                'side': t.get('side', '?'),
                'outcome': t.get('outcome', '?')
            })
    
    return sorted(result, key=lambda x: x['timestamp'])

def generate_bar(price: float, max_price: float, width: int = 40) -> str:
    """生成進度條"""
    if max_price <= 0:
        return ""
    ratio = min(price / max_price, 1.0)
    filled = int(ratio * width)
    return "█" * filled

def find_spikes(prices: List[Dict], threshold: float = 15.0) -> List[Dict]:
    """找出價格突變 (過濾 <5% 死市場噪音)"""
    MIN_MEANINGFUL_PRICE = 5.0  # 5% - below this, relative changes are meaningless
    
    spikes = []
    for i in range(1, len(prices)):
        p1 = prices[i-1]['price']
        p2 = prices[i]['price']
        
        # Skip if both prices are below 5% - dead market, no trading value
        if p1 < MIN_MEANINGFUL_PRICE and p2 < MIN_MEANINGFUL_PRICE:
            continue
        
        if p1 > 0:
            change = ((p2 - p1) / p1) * 100
            if abs(change) >= threshold:
                spikes.append({
                    'index': i,
                    'time': prices[i]['time_str'],
                    'timestamp': prices[i]['timestamp'],
                    'from_price': p1,
                    'to_price': p2,
                    'change': change,
                    'direction': '⬆️' if change > 0 else '⬇️'
                })
    return spikes

def find_trades_before_spike(trades: List[Dict], spike_ts: int, hours: int = 48) -> List[Dict]:
    """找出突變前的交易"""
    window_start = spike_ts - (hours * 3600)
    return [t for t in trades if window_start <= t['timestamp'] <= spike_ts]

def get_wallet_pnl(wallet: str, condition_id: str) -> Dict:
    """獲取錢包在特定市場的盈虧"""
    try:
        resp = requests.get(
            "https://data-api.polymarket.com/trades",
            params={"maker": wallet, "market": condition_id, "limit": 1000},
            timeout=15
        )
        
        if resp.status_code != 200:
            return None
        
        trades = resp.json()
        
        # 計算 YES 和 NO 的買賣
        yes_buy = yes_sell = no_buy = no_sell = 0
        trade_count = 0
        
        for t in trades:
            shares = float(t.get('size', 0) or 0)
            price = float(t.get('price', 0) or 0)
            usd = shares * price
            side = t.get('side', '')
            outcome = t.get('outcome', '')
            
            if usd > 0:
                trade_count += 1
                if outcome == 'Yes':
                    if side == 'BUY':
                        yes_buy += usd
                    else:
                        yes_sell += usd
                elif outcome == 'No':
                    if side == 'BUY':
                        no_buy += usd
                    else:
                        no_sell += usd
        
        # 計算淨收益 (簡化版: 賣出 - 買入)
        net_pnl = (yes_sell + no_sell) - (yes_buy + no_buy)
        
        return {
            'trade_count': trade_count,
            'yes_buy': yes_buy,
            'yes_sell': yes_sell,
            'no_buy': no_buy,
            'no_sell': no_sell,
            'total_buy': yes_buy + no_buy,
            'total_sell': yes_sell + no_sell,
            'net_pnl': net_pnl
        }
    except:
        return None

def get_wallet_overall_stats(wallet: str) -> Dict:
    """獲取錢包整體統計"""
    try:
        resp = requests.get(
            f"https://data-api.polymarket.com/wallet/{wallet}",
            timeout=15
        )
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        return {
            'total_pnl': data.get('pnl', 0),
            'total_volume': data.get('volume', 0),
            'markets_traded': data.get('marketsTraded', 0)
        }
    except:
        return None

def print_chart(prices: List[Dict], trades: List[Dict], spikes: List[Dict], 
                start_date: str = None, end_date: str = None):
    """打印價格走勢圖表"""
    
    # 過濾日期範圍
    if start_date:
        prices = [p for p in prices if p['time_str'] >= start_date]
    if end_date:
        prices = [p for p in prices if p['time_str'] <= end_date]
    
    if not prices:
        print("❌ 沒有數據")
        return
    
    max_price = max(p['price'] for p in prices)
    
    # 建立交易時間索引
    trade_times = {t['time_str']: t for t in trades}
    spike_times = {s['time']: s for s in spikes}
    
    print()
    print("📊 價格走勢圖 (香港時間 HKT)")
    print("─" * 70)
    print()
    
    for p in prices:
        bar = generate_bar(p['price'], max_price)
        annotations = []
        
        # 檢查是否有突變
        if p['time_str'] in spike_times:
            s = spike_times[p['time_str']]
            annotations.append(f"{s['direction']} {s['change']:+.1f}%")
        
        # 檢查是否有大額交易
        if p['time_str'] in trade_times:
            t = trade_times[p['time_str']]
            annotations.append(f"💰 ${t['usd_value']:,.0f} {t['side']}")
        
        annotation_str = " ← " + ", ".join(annotations) if annotations else ""
        
        print(f"{p['time_str']}  {p['price']:6.2f}%  {bar}{annotation_str}")
    
    print()
    print("─" * 70)

def print_trades_summary(trades: List[Dict], spike_ts: int = None):
    """打印交易摘要"""
    if not trades:
        print("📭 沒有找到大額交易 (>= $1,000)")
        return
    
    print()
    print("💰 大額交易記錄 (>= $1,000)")
    print("─" * 70)
    print()
    print(f"{'時間':<12} {'金額':>10} {'方向':<6} {'結果':<6} {'錢包'}")
    print("-" * 70)
    
    for t in trades[-20:]:  # 最近 20 筆
        hours_before = ""
        if spike_ts:
            hours = (spike_ts - t['timestamp']) / 3600
            if 0 < hours < 48:
                hours_before = f" (突變前 {hours:.1f}h)"
        
        wallet_short = t['wallet'][:10] + "..." if len(t['wallet']) > 13 else t['wallet']
        print(f"{t['time_str']:<12} ${t['usd_value']:>9,.0f} {t['side']:<6} {t['outcome']:<6} {wallet_short}{hours_before}")
    
    print()

def print_insider_analysis(condition_id: str, trades: List[Dict], spikes: List[Dict]):
    """打印內幕交易分析"""
    if not spikes:
        print("✅ 沒有檢測到顯著的價格突變")
        return
    
    print()
    print("🕵️ 內幕交易分析")
    print("─" * 70)
    
    for i, spike in enumerate(spikes, 1):
        print(f"\n{i}. {spike['direction']} 突變: {spike['time']}")
        print(f"   價格: {spike['from_price']:.2f}% → {spike['to_price']:.2f}% ({spike['change']:+.1f}%)")
        
        # 找出突變前的交易
        trades_before = find_trades_before_spike(trades, spike['timestamp'], hours=48)
        
        if trades_before:
            total_volume = sum(t['usd_value'] for t in trades_before)
            # 按錢包分組
            wallets = {}
            for t in trades_before:
                w = t['wallet']
                if w not in wallets:
                    wallets[w] = {'total': 0, 'trades': []}
                wallets[w]['total'] += t['usd_value']
                wallets[w]['trades'].append(t)
            
            print(f"\n   📊 突變前 48 小時交易統計:")
            print(f"   總金額: ${total_volume:,.0f}")
            print(f"   交易筆數: {len(trades_before)}")
            print(f"   涉及錢包: {len(wallets)} 個")
            
            # 列出最大的錢包
            sorted_wallets = sorted(wallets.items(), key=lambda x: x[1]['total'], reverse=True)
            print(f"\n   🔝 最大交易錢包:")
            for wallet, data in sorted_wallets[:3]:
                wallet_short = wallet[:16] + "..." if len(wallet) > 19 else wallet
                print(f"   • {wallet_short}: ${data['total']:,.0f} ({len(data['trades'])} 筆)")
                
                # 獲取該錢包在此市場的盈虧
                pnl = get_wallet_pnl(wallet, condition_id)
                if pnl and pnl['trade_count'] > 0:
                    pnl_str = f"+${pnl['net_pnl']:,.0f}" if pnl['net_pnl'] > 0 else f"-${abs(pnl['net_pnl']):,.0f}"
                    pnl_emoji = "💰" if pnl['net_pnl'] > 0 else "📉"
                    print(f"     {pnl_emoji} 該市場盈虧: {pnl_str} (買入 ${pnl['total_buy']:,.0f}, 賣出 ${pnl['total_sell']:,.0f})")
                    
                    # 獲取整體統計
                    overall = get_wallet_overall_stats(wallet)
                    if overall and overall.get('total_pnl'):
                        overall_pnl = overall['total_pnl']
                        overall_str = f"+${overall_pnl:,.0f}" if overall_pnl > 0 else f"-${abs(overall_pnl):,.0f}"
                        wallet_type = "🧠 SMART MONEY" if overall_pnl > 1000 else "📉 LOSER" if overall_pnl < -1000 else "👤 REGULAR"
                        print(f"     📊 整體盈虧: {overall_str} ({wallet_type})")
                        
                        # 檢測矛盾模式
                        if overall_pnl < -1000 and pnl['net_pnl'] > 1000:
                            print(f"     ⚠️  矛盾: 通常虧錢但這次大賺 → 極度可疑!")
                        elif overall_pnl > 1000 and pnl['net_pnl'] > 1000:
                            print(f"     ✅ 一致: Smart Money 持續獲利")
        else:
            print("   📭 沒有找到突變前的大額交易")

def analyze_market(condition_id: str, days: int = 17, start_date: str = None, end_date: str = None):
    """分析單個市場"""
    print("=" * 70)
    print("🔍 Polymarket 內幕掃描 - 詳細分析器")
    print("=" * 70)
    
    # 獲取市場資訊
    market = get_market_info(condition_id)
    if market:
        print(f"\n📌 市場: {market.get('question', 'Unknown')}")
        print(f"   成交量: ${float(market.get('volumeNum', 0)):,.0f}")
        
        # 構建連結
        events = market.get('events', [])
        if events:
            slug = events[0].get('slug', '')
            print(f"   連結: https://polymarket.com/event/{slug}")
        
        token_id = get_token_id(market)
    else:
        print(f"\n⚠️ 無法從緩存找到市場資訊,使用 condition_id 直接查詢")
        token_id = None
    
    print(f"\n   Condition ID: {condition_id}")
    
    # 獲取價格歷史
    if token_id:
        print(f"\n📈 獲取價格歷史 (過去 {days} 天)...")
        prices = get_price_history(token_id, days)
        print(f"   獲取到 {len(prices)} 個數據點")
    else:
        prices = []
    
    # 獲取交易記錄
    print(f"\n💼 獲取交易記錄...")
    trades = get_trades(condition_id)
    print(f"   獲取到 {len(trades)} 筆大額交易 (>= $1,000)")
    
    # 找出突變
    spikes = find_spikes(prices)
    print(f"\n⚡ 檢測到 {len(spikes)} 次價格突變 (>= 15%, 排除 <5% 死市場)")
    
    # Check if current price indicates a dead market
    if prices:
        current_price = prices[-1]['price']
        if current_price < 5.0 or current_price > 95.0:
            print(f"\n⚠️  警告: 當前價格 {current_price:.2f}% 表示市場已基本定局")
            print(f"   此類市場的價格突變通常沒有實際交易價值")
    
    # 打印圖表
    if prices:
        print_chart(prices, trades, spikes, start_date, end_date)
    
    # 打印交易摘要
    max_spike_ts = max((s['timestamp'] for s in spikes), default=None)
    print_trades_summary(trades, max_spike_ts)
    
    # 打印內幕分析
    print_insider_analysis(condition_id, trades, spikes)
    
    print("\n" + "=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Polymarket 內幕交易詳細分析器")
    parser.add_argument("cid", help="市場的 Condition ID (0x...)")
    parser.add_argument("--days", type=int, default=17, help="查看過去多少天的數據 (預設: 17)")
    parser.add_argument("--start", help="起始日期 (格式: MM-DD, 例如 12-08)")
    parser.add_argument("--end", help="結束日期 (格式: MM-DD, 例如 12-10)")
    
    args = parser.parse_args()
    
    analyze_market(args.cid, args.days, args.start, args.end)

if __name__ == "__main__":
    main()
