#!/usr/bin/env python3
"""
全自動 Insider 掃描器 v2.0
- 掃描所有市場的價格突變
- 自動關聯大額交易
- 識別真正的 Insider Trading
- 輸出所有發現，不限制數量
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import time
import argparse
import os

def get_market_slug(condition_id, cache_markets):
    """從緩存獲取市場 slug"""
    for m in cache_markets:
        if m.get('conditionId') == condition_id:
            slug = m.get('slug', '')
            events = m.get('events', [])
            if events:
                event_slug = events[0].get('slug', '')
                return f"https://polymarket.com/event/{event_slug}" if event_slug else f"https://polymarket.com/market/{slug}"
            return f"https://polymarket.com/market/{slug}"
    return None

def analyze_price_continuation(prices, spike_day):
    """分析價格突變後是否持續"""
    if spike_day >= len(prices) - 1:
        return {"continued": False, "reason": "No data after spike"}
    
    spike_price = prices[spike_day]
    before_price = prices[spike_day - 1] if spike_day > 0 else spike_price
    
    spike_direction = "UP" if spike_price > before_price else "DOWN"
    
    days_after = min(3, len(prices) - spike_day - 1)
    if days_after == 0:
        return {"continued": False, "reason": "No follow-up data"}
    
    continued_count = 0
    for i in range(1, days_after + 1):
        next_price = prices[spike_day + i]
        if spike_direction == "UP" and next_price > spike_price:
            continued_count += 1
        elif spike_direction == "DOWN" and next_price < spike_price:
            continued_count += 1
    
    continued = continued_count >= (days_after / 2)
    
    return {
        "continued": continued,
        "days_checked": days_after,
        "days_continued": continued_count,
        "spike_direction": spike_direction,
        "reason": f"Price {'continued' if continued else 'reversed'} after spike"
    }

def get_trades_around_spike(condition_id, spike_date, window_hours=48):
    """獲取價格突變前後的大額交易"""
    try:
        resp = requests.get("https://data-api.polymarket.com/trades",
                           params={"market": condition_id, "limit": 1000},
                           timeout=15)
        
        if resp.status_code != 200:
            return []
        
        trades = resp.json()
        spike_ts = spike_date.timestamp()
        window_seconds = window_hours * 3600
        
        relevant_trades = []
        for trade in trades:
            trade_ts = trade.get('timestamp', 0)
            size = float(trade.get('usdcSize', 0) or 0)
            
            # 只看突變前 48 小時內的大額交易
            if spike_ts - window_seconds <= trade_ts <= spike_ts and size >= 3000:
                relevant_trades.append({
                    'wallet': trade.get('proxyWallet', '?'),
                    'size': size,
                    'side': trade.get('side', '?'),
                    'outcome': trade.get('outcome', '?'),
                    'timestamp': datetime.fromtimestamp(trade_ts),
                    'hours_before_spike': (spike_ts - trade_ts) / 3600
                })
        
        return sorted(relevant_trades, key=lambda x: x['size'], reverse=True)
        
    except Exception as e:
        return []

def calculate_insider_risk(spike, trades_before):
    """計算內幕交易風險評分"""
    score = 0
    factors = []
    
    # 1. 價格變化幅度
    change = abs(spike.get('change', 0))
    if change > 50:
        score += 30
        factors.append(f"極大價格變化 ({change:.1f}%)")
    elif change > 30:
        score += 20
        factors.append(f"大幅價格變化 ({change:.1f}%)")
    elif change > 15:
        score += 10
        factors.append(f"顯著價格變化 ({change:.1f}%)")
    
    # 2. 持續性
    if spike.get('continuation', {}).get('continued'):
        score += 20
        factors.append("價格持續朝同方向")
    
    # 3. 突變前的大額交易
    if trades_before:
        total_volume = sum(t['size'] for t in trades_before)
        
        if total_volume > 100000:
            score += 30
            factors.append(f"突變前大額交易 (${total_volume:,.0f})")
        elif total_volume > 50000:
            score += 20
            factors.append(f"突變前中等交易 (${total_volume:,.0f})")
        elif total_volume > 10000:
            score += 10
            factors.append(f"突變前小額交易 (${total_volume:,.0f})")
        
        # 4. 交易時間接近度
        closest_trade = min(trades_before, key=lambda x: x['hours_before_spike'])
        if closest_trade['hours_before_spike'] < 6:
            score += 20
            factors.append(f"交易時間極接近 ({closest_trade['hours_before_spike']:.1f}h)")
        elif closest_trade['hours_before_spike'] < 24:
            score += 10
            factors.append(f"交易時間接近 ({closest_trade['hours_before_spike']:.1f}h)")
    
    # 評級
    if score >= 70:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return {
        'score': score,
        'level': level,
        'factors': factors
    }

def auto_insider_scan(min_volume=50000, max_markets=1500, rel_threshold=15.0, abs_threshold=3.0, trade_threshold=3000, update_cache=True, start_index=0):
    """
    全自動 Insider 掃描
    """
    print(f"🚨 全自動 Insider 掃描器 v2.1")
    print(f"   最低成交量: ${min_volume:,.0f}")
    print(f"   掃描範圍: {start_index} ~ {start_index + max_markets}")
    print(f"   相對門檻: {rel_threshold}%")
    print(f"   絕對門檻: {abs_threshold}% (極端市場)")
    print(f"   大額交易門檻: ${trade_threshold:,.0f}")
    print("="*80 + "\n")
    
    # Step 0: Update cache if requested
    if update_cache:
        print("📥 Step 0: 更新市場緩存...")
        print("-"*80)
        try:
            import subprocess
            
            # Check if search.py exists
            search_script = os.path.join(os.path.dirname(__file__), "search.py")
            if os.path.exists(search_script):
                print("   執行: python search.py --fast")
                result = subprocess.run(
                    ["python3", search_script, "--fast"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    print("   ✅ 緩存更新成功")
                    # Extract cache info from output
                    for line in result.stdout.split('\n'):
                        if '總市場數' in line or '成交量門檻' in line:
                            print(f"   {line.strip()}")
                else:
                    print(f"   ⚠️ 緩存更新失敗 (exit code: {result.returncode})")
                    print(f"   將使用現有緩存繼續...")
            else:
                print("   ⚠️ 找不到 search.py，跳過緩存更新")
        except subprocess.TimeoutExpired:
            print("   ⚠️ 緩存更新超時，將使用現有緩存")
        except Exception as e:
            print(f"   ⚠️ 緩存更新錯誤: {e}")
            print(f"   將使用現有緩存繼續...")
        
        print("="*80 + "\n")
    
    # Load markets from cache
    cache_file = "cache/all_markets_cache_active.json"
    
    # Check if cache exists
    if not os.path.exists(cache_file):
        print(f"❌ 錯誤: 找不到緩存文件 {cache_file}")
        print(f"   請先運行: python search.py --fast")
        return []
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
        all_markets = data.get('markets', [])
    
    # Filter by volume
    markets = [m for m in all_markets if float(m.get('volumeNum', 0) or 0) >= min_volume]
    
    print(f"📊 符合條件的市場: {len(markets)} 個")
    print(f"   將掃描 {len(markets[start_index:start_index+max_markets])} 個\n")
    
    insider_candidates = []
    
    target_markets = markets[start_index:start_index + max_markets]
    
    for idx_offset, market in enumerate(target_markets, 1):
        idx = start_index + idx_offset
        cid = market.get('conditionId', '')
        question = market.get('question', '')[:60]
        volume = float(market.get('volumeNum', 0) or 0)
        
        print(f"[{idx}/{len(markets)}] {question}...", end=" ", flush=True)
        
        # Get clob token IDs
        clob_ids = market.get('clobTokenIds', [])
        if isinstance(clob_ids, str):
            clob_ids = json.loads(clob_ids)
        
        if not clob_ids:
            print("❌ No token ID")
            continue
        
        # Get price history
        try:
            token_id = clob_ids[0]
            start_ts = int((datetime.now() - timedelta(days=17)).timestamp())
            
            resp = requests.get("https://clob.polymarket.com/prices-history",
                               params={
                                   "market": token_id,
                                   "interval": "1d",
                                   "fidelity": 100,
                                   "startTs": start_ts
                               }, timeout=10)
            
            if resp.status_code != 200:
                print("❌ No price data")
                continue
            
            history = resp.json().get('history', [])
            if len(history) < 3:
                print("❌ Insufficient data")
                continue
            
            # Analyze for spikes
            prices = [float(h.get('p', 0)) for h in history if h.get('p')]
            dates = [datetime.fromtimestamp(h.get('t', 0)) for h in history if h.get('t')]
            
            if len(prices) < 3:
                print("❌ Insufficient prices")
                continue
            
            # Find spikes with continuation
            spikes_with_trades = []
            
            for i in range(1, len(prices)):
                p1, p2 = prices[i-1], prices[i]
                
                if p1 > 0:
                    relative_change = ((p2 - p1) / p1) * 100
                    absolute_change = abs(p2 - p1) * 100
                    
                    # Smart threshold
                    is_extreme = p1 < 0.05 or p1 > 0.95
                    
                    is_spike = False
                    if is_extreme:
                        if absolute_change >= abs_threshold:
                            is_spike = True
                    else:
                        if abs(relative_change) >= rel_threshold:
                            is_spike = True
                    
                    if is_spike:
                        # Check continuation
                        continuation = analyze_price_continuation(prices, i)
                        
                        if continuation['continued']:
                            spike_info = {
                                'day': i,
                                'date': dates[i],
                                'from_price': p1 * 100,
                                'to_price': p2 * 100,
                                'change': relative_change,
                                'absolute_change': absolute_change,
                                'is_extreme': is_extreme,
                                'continuation': continuation
                            }
                            
                            # 🔥 NEW: Get trades before spike
                            trades_before = get_trades_around_spike(cid, dates[i], window_hours=48)
                            
                            # Calculate insider risk
                            risk = calculate_insider_risk(spike_info, trades_before)
                            
                            spike_info['trades_before'] = trades_before[:5]  # Top 5
                            spike_info['insider_risk'] = risk
                            
                            spikes_with_trades.append(spike_info)
            
            if spikes_with_trades:
                # Calculate overall risk (max of all spikes)
                max_risk = max(s['insider_risk']['score'] for s in spikes_with_trades)
                max_level = max((s['insider_risk']['level'] for s in spikes_with_trades), 
                               key=lambda x: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(x))
                
                emoji = "🚨" if max_level == "CRITICAL" else "⚠️" if max_level == "HIGH" else "⚡" if max_level == "MEDIUM" else "✅"
                print(f"{emoji} {len(spikes_with_trades)} Insider 事件 ({max_level})")
                
                insider_candidates.append({
                    'question': question,
                    'cid': cid,
                    'volume': volume,
                    'spikes': spikes_with_trades,
                    'max_risk_score': max_risk,
                    'max_risk_level': max_level,
                    'url': get_market_slug(cid, all_markets)
                })
            else:
                print("✅ 無可疑")
            
            time.sleep(0.05)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print("\n" + "="*80)
    print(f"🎯 掃描完成！")
    print("="*80 + "\n")
    
    return insider_candidates

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polymarket 全自動 Insider 掃描器")
    parser.add_argument("--max", type=int, default=1500, help="最多掃描市場數量 (預設: 1500)")
    parser.add_argument("--min-vol", type=float, default=50000, help="最低成交量 (預設: 50000)")
    parser.add_argument("--threshold", type=float, default=15.0, help="相對價格變化門檻 %% (預設: 15)")
    parser.add_argument("--abs-threshold", type=float, default=3.0, help="絕對價格變化門檻 %% (預設: 3)")
    parser.add_argument("--trade-threshold", type=float, default=3000, help="大額交易門檻 (預設: 3000)")
    parser.add_argument("--min-risk", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="MEDIUM", 
                       help="只顯示此風險等級以上 (預設: MEDIUM)")
    parser.add_argument("--no-cache-update", action="store_true", help="跳過緩存更新，直接使用現有緩存")
    parser.add_argument("--start-index", type=int, default=0, help="從第幾個市場開始掃描 (用於失敗後恢復)")
    
    args = parser.parse_args()
    
    # Run scan
    candidates = auto_insider_scan(
        min_volume=args.min_vol,
        max_markets=args.max,
        rel_threshold=args.threshold,
        abs_threshold=args.abs_threshold,
        trade_threshold=args.trade_threshold,
        update_cache=not args.no_cache_update,  # Invert the flag
        start_index=args.start_index
    )
    
    # Filter by risk level
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    min_risk_level = risk_order[args.min_risk]
    
    filtered = [c for c in candidates if risk_order[c['max_risk_level']] >= min_risk_level]
    
    # Sort by risk score
    filtered.sort(key=lambda x: x['max_risk_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/tmp/auto_insider_scan_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(filtered, f, indent=2)
    
    # Display results
    print(f"\n發現 {len(filtered)} 個市場符合風險門檻 (>= {args.min_risk}):\n")
    
    for i, c in enumerate(filtered, 1):
        risk_emoji = "🚨" if c['max_risk_level'] == "CRITICAL" else "⚠️" if c['max_risk_level'] == "HIGH" else "⚡"
        
        print(f"{i}. {risk_emoji} {c['question']}...")
        print(f"   風險: {c['max_risk_level']} (評分: {c['max_risk_score']}/100)")
        print(f"   成交量: ${c['volume']:,.0f}")
        print(f"   Insider 事件: {len(c['spikes'])} 次")
        
        # Show top insider event
        top_spike = max(c['spikes'], key=lambda x: x['insider_risk']['score'])
        print(f"   最可疑事件: {top_spike['date'].strftime('%Y-%m-%d')}")
        print(f"      價格: {top_spike['from_price']:.2f}% → {top_spike['to_price']:.2f}% ({top_spike['change']:+.1f}%)")
        
        if top_spike['trades_before']:
            total = sum(t['size'] for t in top_spike['trades_before'])
            print(f"      突變前交易: ${total:,.0f} ({len(top_spike['trades_before'])} 筆)")
        
        print(f"   連結: {c['url']}")
        print(f"   ID: {c['cid']}")
        print()
    
    print(f"\n💾 完整結果已保存到: {output_file}")
