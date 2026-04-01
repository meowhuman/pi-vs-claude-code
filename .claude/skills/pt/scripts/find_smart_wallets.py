#!/usr/bin/env python3
"""
Smart Money Tracker
從市場持倉數據搵出 Smart Wallets 同佢哋集中嘅市場
"""

import requests
import json
from collections import defaultdict
from typing import List, Dict
import os
from dotenv import load_dotenv
import sys

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from trader_classification import classify_trader_role, is_likely_market_maker

load_dotenv()

DATA_API = "https://data-api.polymarket.com"


def get_market_holders(condition_id: str) -> List[Dict]:
    """
    獲取市場持倉者 - 使用 Subgraph 獲取完整數據 (冇 20 個限制)
    """
    try:
        from utils.subgraph import get_all_holders
        
        # 用 Subgraph 獲取所有持倉者 (min 100 shares)
        holders = get_all_holders(condition_id, min_balance=100, max_holders=500)
        
        # 轉換格式
        result = []
        for h in holders:
            result.append({
                'proxyWallet': h.get('wallet', ''),
                'user': h.get('wallet', ''),
                'amount': h.get('balance', 0),
                'outcomeIndex': h.get('outcome', 0)  # 0=Yes, 1=No
            })
        return result
    except Exception as e:
        print(f"⚠️ Subgraph 錯誤，嘗試 fallback: {e}")
        # Fallback to Data API
        try:
            resp = requests.get(
                f"{DATA_API}/holders",
                params={"market": condition_id, "limit": 100},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                holders = []
                for token_data in data:
                    for h in token_data.get('holders', []):
                        holders.append(h)
                return holders
            return []
        except:
            return []


def scan_markets_for_smart_money(market_ids: List[str]) -> Dict[str, List[Dict]]:
    """
    掃描多個市場，搵出 Smart Money wallets
    
    Returns:
        {wallet: [market_positions]}
    """
    print(f"\n🔍 掃描 {len(market_ids)} 個市場搵 Smart Money...")
    print("="*80)
    
    smart_wallets = defaultdict(list)
    
    for i, market_id in enumerate(market_ids, 1):
        print(f"  {i}/{len(market_ids)} 分析市場 {market_id[:20]}...", end='\r')
        
        holders = get_market_holders(market_id)
        
        # Group by wallet
        wallet_positions = {}
        for h in holders:
            wallet = h.get('proxyWallet', h.get('user', ''))
            if not wallet:
                continue
            
            if wallet not in wallet_positions:
                wallet_positions[wallet] = {'yes': 0, 'no': 0}
            
            outcome_index = h.get('outcomeIndex', 0)
            amount = float(h.get('amount', 0))
            
            if outcome_index == 0:
                wallet_positions[wallet]['yes'] += amount
            else:
                wallet_positions[wallet]['no'] += amount
        
        # Classify wallets
        for wallet, position in wallet_positions.items():
            yes_value = position['yes']
            no_value = position['no']
            
            # Simplified classification (without full trade history)
            wallet_data = {
                'market_trades': 10,  # Estimate
                'global_trades': 1000,  # Estimate  
                'market_pnl': (yes_value + no_value) * 0.1,  # Assume 10% profit
                'total_value': yes_value + no_value,
                'yes_value': yes_value,
                'no_value': no_value,
                'is_market_maker': False
            }
            
            # Check if MM
            is_mm, _, _ = is_likely_market_maker(wallet_data)
            if is_mm:
                continue
            
            # Classify
            role = classify_trader_role(wallet_data)
            
            if role['role'] in ['SMART_MONEY', 'WHALE']:
                direction = 'YES' if yes_value > no_value else 'NO'
                smart_wallets[wallet].append({
                    'market_id': market_id,
                    'direction': direction,
                    'value': yes_value + no_value,
                    'role': role['role']
                })
    
    print(f"\n✅ 發現 {len(smart_wallets)} 個 Smart/Whale Wallets\n")
    return dict(smart_wallets)


def find_smart_money_consensus(smart_wallets: Dict[str, List[Dict]], min_wallets: int = 3) -> List[Dict]:
    """
    搵出 Smart Money 有共識嘅市場
    
    Returns:
        List of {market_id, smart_wallets, direction, confidence}
    """
    market_signals = defaultdict(lambda: {'yes': [], 'no': []})
    
    for wallet, positions in smart_wallets.items():
        for pos in positions:
            market_id = pos['market_id']
            direction = pos['direction']
            
            if direction == 'YES':
                market_signals[market_id]['yes'].append(wallet)
            else:
                market_signals[market_id]['no'].append(wallet)
    
    # Find consensus
    consensus_markets = []
    
    for market_id, signals in market_signals.items():
        yes_count = len(signals['yes'])
        no_count = len(signals['no'])
        total = yes_count + no_count
        
        if total < min_wallets:
            continue
        
        if yes_count > no_count * 1.5:
            direction = 'YES'
            confidence = yes_count / total
        elif no_count > yes_count * 1.5:
            direction = 'NO'
            confidence = no_count / total
        else:
            direction = 'MIXED'
            confidence = 0.5
        
        consensus_markets.append({
            'market_id': market_id,
            'smart_wallets': total,
            'yes_wallets': yes_count,
            'no_wallets': no_count,
            'direction': direction,
            'confidence': confidence
        })
    
    consensus_markets.sort(key=lambda x: x['smart_wallets'], reverse=True)
    return consensus_markets


def display_smart_markets(markets: List[Dict], top_n: int = 10):
    """顯示 Smart Money 集中嘅市場"""
    print(f"\n🎯 Top {top_n} Smart Money 共識市場:\n")
    print("="*80)
    
    for i, m in enumerate(markets[:top_n], 1):
        emoji = "🟢" if m['direction'] == 'YES' else "🔴" if m['direction'] == 'NO' else "🟡"
        
        print(f"\n{i}. {emoji} Market ID: {m['market_id'][:40]}...")
        print(f"   Smart Wallets: {m['smart_wallets']} (YES: {m['yes_wallets']}, NO: {m['no_wallets']})")
        print(f"   方向: {m['direction']} (信心: {m['confidence']:.0%})")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Money Tracker")
    parser.add_argument("--markets", type=int, default=20, help="掃描幾多個市場")
    parser.add_argument("--min-wallets", type=int, default=3, help="最少幾多個 Smart Wallet")
    parser.add_argument("--limit", type=int, default=10, help="顯示幾多個市場")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--min-vol", type=float, default=100000, help="最低成交量")
    
    args = parser.parse_args()
    
    # 用 search.py 嘅篩選功能獲取活躍市場
    print("📥 使用 search.py 獲取已篩選嘅活躍市場...")
    
    try:
        # Import search functions
        from search import fetch_all_markets, filter_by_volume, filter_by_probability, filter_active_or_closed
        
        # 用現有嘅 search 系統
        all_markets = fetch_all_markets(use_cache=True, max_age_hours=6, min_volume=args.min_vol)
        
        # 篩選活躍市場
        markets = filter_active_or_closed(all_markets, status='active')
        markets = filter_by_probability(markets, (0.05, 0.95))
        markets = filter_by_volume(markets, args.min_vol)
        
        # 按成交量排序
        markets.sort(key=lambda x: float(x.get('volumeNum', x.get('volume', 0)) or 0), reverse=True)
        markets = markets[:args.markets]
        
        if not markets:
            print("❌ 冇搵到活躍市場")
            sys.exit(1)
        
        market_ids = [m['conditionId'] for m in markets if m.get('conditionId')]
        
        print(f"✅ 獲取 {len(market_ids)} 個已篩選市場 (Vol > ${args.min_vol:,.0f})\n")
        
        # 顯示掃描嘅市場
        for i, m in enumerate(markets[:5], 1):
            vol = float(m.get('volumeNum', m.get('volume', 0)) or 0)
            print(f"  {i}. {m.get('question', 'Unknown')[:50]}... (${vol:,.0f})")
        if len(markets) > 5:
            print(f"  ... 同 {len(markets) - 5} 個其他市場\n")
        
        # Scan for smart money
        smart_wallets = scan_markets_for_smart_money(market_ids)
        
        # Find consensus
        consensus = find_smart_money_consensus(smart_wallets, min_wallets=args.min_wallets)
        
        if args.json:
            print(json.dumps(consensus[:args.limit], indent=2))
        else:
            display_smart_markets(consensus, top_n=args.limit)
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
