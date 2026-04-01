#!/usr/bin/env python3
"""
全自動 Insider 掃描器 v3.0 - 異步並發版本
- 使用 asyncio + aiohttp 實現並發請求
- 速度提升 5-10 倍
- 支援斷點續傳
- 智能風險評分
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import os
import sys
from typing import List, Dict, Optional

# 並發控制
MAX_CONCURRENT_REQUESTS = 20  # 同時處理的市場數量
RATE_LIMIT_DELAY = 0.05  # 每個請求之間的延遲

def get_market_slug(condition_id: str, cache_markets: List[Dict]) -> Optional[str]:
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

def analyze_price_continuation(prices: List[float], spike_day: int) -> Dict:
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

async def get_trades_around_spike(session: aiohttp.ClientSession, condition_id: str, 
                                  spike_date: datetime, window_hours: int = 48, 
                                  trade_threshold: float = 3000) -> List[Dict]:
    """獲取價格突變前後的大額交易"""
    try:
        async with session.get(
            "https://data-api.polymarket.com/trades",
            params={"market": condition_id, "limit": 1000},
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status != 200:
                return []
            
            trades = await resp.json()
            spike_ts = spike_date.timestamp()
            window_seconds = window_hours * 3600
            
            relevant_trades = []
            for trade in trades:
                trade_ts = trade.get('timestamp', 0)
                shares = float(trade.get('size', 0) or 0)
                price = float(trade.get('price', 0) or 0)
                
                # Calculate USD value: shares * price
                usd_value = shares * price
                
                # 只看突變前 48 小時內的大額交易 (>= threshold)
                if spike_ts - window_seconds <= trade_ts <= spike_ts and usd_value >= trade_threshold:
                    relevant_trades.append({
                        'wallet': trade.get('proxyWallet', '?'),
                        'usd_value': round(usd_value, 2),
                        'shares': shares,
                        'price': price,
                        'side': trade.get('side', '?'),
                        'outcome': trade.get('outcome', '?'),
                        'timestamp': datetime.fromtimestamp(trade_ts),
                        'hours_before_spike': (spike_ts - trade_ts) / 3600
                    })
            
            return sorted(relevant_trades, key=lambda x: x['usd_value'], reverse=True)
            
    except Exception as e:
        return []

def calculate_insider_risk(spike: Dict, trades_before: List[Dict]) -> Dict:
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
        total_volume = sum(t['usd_value'] for t in trades_before)
        
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

async def analyze_single_market(session: aiohttp.ClientSession, market: Dict, 
                                idx: int, total: int, rel_threshold: float, 
                                abs_threshold: float, trade_threshold: float, 
                                all_markets: List[Dict]) -> Optional[Dict]:
    """分析單個市場 (異步)"""
    cid = market.get('conditionId', '')
    question = market.get('question', '')[:60]
    volume = float(market.get('volumeNum', 0) or 0)
    
    print(f"[{idx}/{total}] {question}...", end=" ", flush=True)
    
    try:
        # Get clob token IDs
        clob_ids = market.get('clobTokenIds', [])
        if isinstance(clob_ids, str):
            clob_ids = json.loads(clob_ids)
        
        if not clob_ids:
            print("❌ No token ID")
            return None
        
        token_id = clob_ids[0]
        start_ts = int((datetime.now() - timedelta(days=17)).timestamp())
        
        # 獲取價格歷史
        async with session.get(
            "https://clob.polymarket.com/prices-history",
            params={
                "market": token_id,
                "interval": "1d",
                "fidelity": 100,
                "startTs": start_ts
            },
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                print(f"❌ No price data ({resp.status})")
                return None
            
            data = await resp.json()
            history = data.get('history', [])
            
            if len(history) < 3:
                print("❌ Insufficient data")
                return None
            
            # Analyze for spikes
            prices = [float(h.get('p', 0)) for h in history if h.get('p')]
            dates = [datetime.fromtimestamp(h.get('t', 0)) for h in history if h.get('t')]
            
            if len(prices) < 3:
                print("❌ Insufficient prices")
                return None
            
            # Skip dead markets: if current price is <5% or >95%, no trading value
            current_price = prices[-1]
            MIN_ACTIVE_PRICE = 0.05  # 5%
            MAX_ACTIVE_PRICE = 0.95  # 95%
            if current_price < MIN_ACTIVE_PRICE or current_price > MAX_ACTIVE_PRICE:
                print(f"⏭️ 死市場 ({current_price*100:.1f}%)")
                return None
            
            # Find spikes with continuation
            spikes_with_trades = []
            
            for i in range(1, len(prices)):
                p1, p2 = prices[i-1], prices[i]
                
                if p1 > 0:
                    # Skip if both prices are below 5% - dead market, no trading value
                    # These often show huge relative changes (e.g., 0.3% → 0.5% = +67%) but are meaningless
                    MIN_MEANINGFUL_PRICE = 0.05  # 5%
                    if p1 < MIN_MEANINGFUL_PRICE and p2 < MIN_MEANINGFUL_PRICE:
                        continue
                    
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
                            
                            # Get trades before spike
                            trades_before = await get_trades_around_spike(session, cid, dates[i], 
                                                                         window_hours=48, 
                                                                         trade_threshold=trade_threshold)
                            
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
                
                return {
                    'question': question,
                    'cid': cid,
                    'volume': volume,
                    'spikes': spikes_with_trades,
                    'max_risk_score': max_risk,
                    'max_risk_level': max_level,
                    'url': get_market_slug(cid, all_markets)
                }
            else:
                print("✅ 無可疑")
                return None
            
    except asyncio.TimeoutError:
        print("❌ Timeout")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def process_batch(session: aiohttp.ClientSession, markets: List[Dict], 
                       start_idx: int, rel_threshold: float, abs_threshold: float,
                       trade_threshold: float, all_markets: List[Dict]) -> List[Dict]:
    """處理一批市場 (並發)"""
    tasks = []
    for offset, market in enumerate(markets):
        idx = start_idx + offset + 1
        task = analyze_single_market(
            session, market, idx, start_idx + len(markets), 
            rel_threshold, abs_threshold, trade_threshold, all_markets
        )
        tasks.append(task)
        
        # 小延遲避免過度請求
        if offset < len(markets) - 1:
            await asyncio.sleep(RATE_LIMIT_DELAY)
    
    # 並發執行所有任務
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 過濾掉 None 和異常
    return [r for r in results if r is not None and not isinstance(r, Exception)]

async def auto_insider_scan_async(min_volume: float = 50000, max_markets: int = 1500, 
                                  rel_threshold: float = 15.0, abs_threshold: float = 3.0,
                                  trade_threshold: float = 3000,
                                  start_index: int = 0, update_cache: bool = True) -> List[Dict]:
    """
    全自動 Insider 掃描 (異步版本)
    """
    print(f"🚨 全自動 Insider 掃描器 v3.0 (異步並發)")
    print(f"   最低成交量: ${min_volume:,.0f}")
    print(f"   掃描範圍: {start_index} ~ {start_index + max_markets}")
    print(f"   相對門檻: {rel_threshold}%")
    print(f"   絕對門檻: {abs_threshold}% (極端市場)")
    print(f"   並發數: {MAX_CONCURRENT_REQUESTS}")
    print("="*80 + "\n")
    
    # Step 0: Update cache if requested
    if update_cache:
        print("📥 Step 0: 更新市場緩存...")
        print("-"*80)
        try:
            import subprocess
            
            search_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "search.py")
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
                else:
                    print(f"   ⚠️ 緩存更新失敗，將使用現有緩存")
            else:
                print("   ⚠️ 找不到 search.py，跳過緩存更新")
        except Exception as e:
            print(f"   ⚠️ 緩存更新錯誤: {e}")
        
        print("="*80 + "\n")
    
    # Load markets from cache
    cache_file = os.path.join(os.path.dirname(__file__), "..", "cache", "all_markets_cache_active.json")
    
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
    target_markets = markets[start_index:start_index + max_markets]
    print(f"   將掃描 {len(target_markets)} 個\n")
    
    insider_candidates = []
    
    # 使用 aiohttp 進行並發請求
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS, limit_per_host=10)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 分批處理
        batch_size = MAX_CONCURRENT_REQUESTS
        
        for batch_start in range(0, len(target_markets), batch_size):
            batch = target_markets[batch_start:batch_start + batch_size]
            batch_results = await process_batch(
                session, batch, start_index + batch_start, 
                rel_threshold, abs_threshold, trade_threshold, all_markets
            )
            insider_candidates.extend(batch_results)
    
    print("\n" + "="*80)
    print(f"🎯 掃描完成！")
    print("="*80 + "\n")
    
    return insider_candidates

def main():
    parser = argparse.ArgumentParser(description="Polymarket 全自動 Insider 掃描器 (異步版)")
    parser.add_argument("--max", type=int, default=1500, help="最多掃描市場數量 (預設: 1500)")
    parser.add_argument("--min-vol", type=float, default=50000, help="最低成交量 (預設: 50000)")
    parser.add_argument("--threshold", type=float, default=15.0, help="相對價格變化門檻 %% (預設: 15)")
    parser.add_argument("--abs-threshold", type=float, default=3.0, help="絕對價格變化門檻 %% (預設: 3)")
    parser.add_argument("--min-risk", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="MEDIUM", 
                       help="只顯示此風險等級以上 (預設: MEDIUM)")
    parser.add_argument("--no-cache-update", action="store_true", help="跳過緩存更新，直接使用現有緩存")
    parser.add_argument("--start-index", type=int, default=0, help="從第幾個市場開始掃描 (用於失敗後恢復)")
    parser.add_argument("--concurrency", type=int, default=20, help="並發請求數 (預設: 20)")
    parser.add_argument("--trade-threshold", type=float, default=3000, help="大額交易門檻 (預設: 3000)")
    parser.add_argument("--output", type=str, help="輸出文件路徑 (JSON)")
    
    args = parser.parse_args()
    
    # 設置並發數
    global MAX_CONCURRENT_REQUESTS
    MAX_CONCURRENT_REQUESTS = args.concurrency
    
    # Run async scan
    candidates = asyncio.run(auto_insider_scan_async(
        min_volume=args.min_vol,
        max_markets=args.max,
        rel_threshold=args.threshold,
        abs_threshold=args.abs_threshold,
        trade_threshold=args.trade_threshold,
        start_index=args.start_index,
        update_cache=not args.no_cache_update
    ))
    
    # Filter by risk level
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    min_risk_level = risk_order[args.min_risk]
    
    filtered = [c for c in candidates if risk_order[c['max_risk_level']] >= min_risk_level]
    
    # Sort by risk score
    filtered.sort(key=lambda x: x['max_risk_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output if args.output else f"/tmp/auto_insider_scan_async_{timestamp}.json"
    
    # Create directory if doesn't exist
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(filtered, f, indent=2, default=str)
    
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
        spike_date = top_spike['date'].strftime('%Y-%m-%d')
        print(f"   最可疑事件: {spike_date}")
        print(f"      價格: {top_spike['from_price']:.2f}% → {top_spike['to_price']:.2f}% ({top_spike['change']:+.1f}%)")
        
        if top_spike['trades_before']:
            total = sum(t['usd_value'] for t in top_spike['trades_before'])
            print(f"      突變前交易: ${total:,.0f} ({len(top_spike['trades_before'])} 筆)")
        
        print(f"   連結: {c['url']}")
        print(f"   ID: {c['cid']}")
        
        # Add tip for detailed analysis
        spike_month_day = spike_date[5:]  # Extract MM-DD
        print(f"   💡 查看詳細圖表: python3 insider_detail.py {c['cid']} --start {spike_month_day}")
        print()
    
    print(f"\n💾 完整結果已保存到: {output_file}")

if __name__ == "__main__":
    main()
