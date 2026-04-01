#!/usr/bin/env python3
"""
Polymarket Analyzer - 統一市場分析入口
整合: analyze_market.py, analyze_whales.py, analyze_odds.py, kelly.py

用法:
    python analyze.py market <ID>              # 市場深度分析
    python analyze.py whales <ID>              # 鯨魚分析
    python analyze.py wallet <address>         # 錢包起底
    python analyze.py odds <event>             # 賠率分析
    python analyze.py kelly <ID> --estimate 0.6  # Kelly 計算
    python analyze.py signal <ID>              # 交易信號
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.client import get_client, get_api_urls
from utils.market import get_market_info, get_orderbook
from utils.subgraph import get_all_holders, get_position_distribution, get_holder_count

load_dotenv()

# =============================================================================
# Constants
# =============================================================================

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


# =============================================================================
# Holder Analysis Functions (Goldsky Subgraph)
# =============================================================================

def analyze_holders(condition_id: str, top: int = 50, min_balance: float = 1, classify: bool = False, ratio_only: bool = False):
    """
    分析市場完整持倉分佈 (使用 Goldsky Subgraph，無 20 人限制)
    
    Args:
        condition_id: 市場 Condition ID
        top: 顯示 Top N 持倉者
        min_balance: 最低持倉量過濾
        classify: 是否進行錢包分類 (Smart Money 等)
        ratio_only: 只顯示 Yes/No 比例
    """
    from utils.subgraph import is_system_wallet
    
    print(f"\n🔍 Holder Analysis (Goldsky Subgraph)")
    print("="*80)
    
    # Get market info
    market_info = get_market_info(condition_id)
    market_volume = 0
    if market_info:
        market_name = market_info.get('question', 'Unknown Market')
        market_volume = float(market_info.get('volumeNum', 0) or 0)
        print(f"📊 {market_name[:70]}...")
        print(f"💰 成交量: ${market_volume:,.0f}")
    else:
        market_name = "Unknown"
        print(f"📊 市場: {condition_id[:30]}...")
    print()
    
    # Fetch all holders via Subgraph
    print("⏳ 從 Goldsky Subgraph 獲取持倉數據...", end="", flush=True)
    dist = get_position_distribution(condition_id, min_balance=min_balance)
    print(f" ✅\n")
    
    # Detect system wallets
    yes_holders = dist['yes']['holders']
    no_holders = dist['no']['holders']
    
    yes_system = []
    no_system = []
    yes_real = []
    no_real = []
    
    for h in yes_holders:
        is_sys, reason = is_system_wallet(h['wallet'], h['balance'], market_volume)
        h['is_system'] = is_sys
        h['system_reason'] = reason
        if is_sys:
            yes_system.append(h)
        else:
            yes_real.append(h)
    
    for h in no_holders:
        is_sys, reason = is_system_wallet(h['wallet'], h['balance'], market_volume)
        h['is_system'] = is_sys
        h['system_reason'] = reason
        if is_sys:
            no_system.append(h)
        else:
            no_real.append(h)
    
    # Calculate real totals (excluding system wallets)
    yes_real_total = sum(h['balance'] for h in yes_real)
    no_real_total = sum(h['balance'] for h in no_real)
    real_grand_total = yes_real_total + no_real_total
    
    # System wallet info
    if yes_system or no_system:
        print("⚠️  偵測到系統錢包 (已從統計中排除):")
        for h in yes_system + no_system:
            side = "YES" if h in yes_system else "NO"
            print(f"   • {h['wallet'][:16]}... | {h['balance']:,.0f} {side} | {h['system_reason']}")
        print()
    
    # Summary (Real holders only)
    print("📊 持倉分佈總覽 (排除系統錢包)")
    print("─"*60)
    print(f"   真實持倉者: {len(yes_real) + len(no_real)} 人")
    print(f"   真實份額:   {real_grand_total:,.0f} shares")
    print()
    
    yes_pct = (yes_real_total / real_grand_total * 100) if real_grand_total > 0 else 0
    no_pct = (no_real_total / real_grand_total * 100) if real_grand_total > 0 else 0
    
    # Visual bar
    bar_len = 40
    yes_bar = int(bar_len * yes_pct / 100)
    no_bar = bar_len - yes_bar
    bar = "█" * yes_bar + "░" * no_bar
    
    print(f"   ✅ YES: {len(yes_real):,} 人 | {yes_real_total:,.0f} shares ({yes_pct:.1f}%)")
    print(f"   ❌ NO:  {len(no_real):,} 人 | {no_real_total:,.0f} shares ({no_pct:.1f}%)")
    print(f"\n   [{bar}]")
    print(f"    YES {yes_pct:.1f}%{' '*20}NO {no_pct:.1f}%")
    
    if ratio_only:
        print("\n" + "="*80)
        return dist
    
    # Top YES holders (real only)
    print(f"\n🐋 Top {top} YES 持倉者")
    print("─"*80)
    print(f"{'#':<4} {'錢包地址':<20} {'持倉量':>15} {'市場佔比':>12} {'YES側佔比':>12} {'類型':>8}")
    print("─"*80)
    
    for i, h in enumerate(yes_real[:top], 1):
        wallet_short = h['wallet'][:10] + '...' + h['wallet'][-4:]
        pct_total = (h['balance'] / real_grand_total * 100) if real_grand_total > 0 else 0
        pct_side = (h['balance'] / yes_real_total * 100) if yes_real_total > 0 else 0
        badge = "👤"
        print(f"{i:<4} {wallet_short:<20} {h['balance']:>15,.0f} {pct_total:>11.1f}% {pct_side:>11.1f}% {badge:>8}")
    
    # Top NO holders (real only)
    print(f"\n🐋 Top {top} NO 持倉者")
    print("─"*80)
    print(f"{'#':<4} {'錢包地址':<20} {'持倉量':>15} {'市場佔比':>12} {'NO側佔比':>12} {'類型':>8}")
    print("─"*80)
    
    for i, h in enumerate(no_real[:top], 1):
        wallet_short = h['wallet'][:10] + '...' + h['wallet'][-4:]
        pct_total = (h['balance'] / real_grand_total * 100) if real_grand_total > 0 else 0
        pct_side = (h['balance'] / no_real_total * 100) if no_real_total > 0 else 0
        badge = "👤"
        print(f"{i:<4} {wallet_short:<20} {h['balance']:>15,.0f} {pct_total:>11.1f}% {pct_side:>11.1f}% {badge:>8}")
    
    # Concentration analysis (real holders only)
    print(f"\n📈 集中度分析 (真實持倉者)")
    print("─"*60)
    
    # Top 10 concentration
    yes_top10 = sum(h['balance'] for h in yes_real[:10])
    no_top10 = sum(h['balance'] for h in no_real[:10])
    yes_top10_pct = (yes_top10 / yes_real_total * 100) if yes_real_total > 0 else 0
    no_top10_pct = (no_top10 / no_real_total * 100) if no_real_total > 0 else 0
    
    print(f"   YES Top 10 佔比: {yes_top10_pct:.1f}% ({yes_top10:,.0f} shares)")
    print(f"   NO  Top 10 佔比: {no_top10_pct:.1f}% ({no_top10:,.0f} shares)")
    
    # Whale detection (>$10k position estimate)
    whale_threshold = 10000  # shares
    yes_whales = [h for h in yes_real if h['balance'] >= whale_threshold]
    no_whales = [h for h in no_real if h['balance'] >= whale_threshold]
    
    print(f"\n   YES 大戶 (>{whale_threshold:,} shares): {len(yes_whales)} 人")
    print(f"   NO  大戶 (>{whale_threshold:,} shares): {len(no_whales)} 人")
    
    # Signal hint
    print(f"\n💡 信號提示")
    print("─"*60)
    
    if yes_pct > 70:
        print("   ⚠️ YES 持倉高度集中，可能有回調風險")
    elif no_pct > 70:
        print("   ⚠️ NO 持倉高度集中，可能有回調風險")
    elif yes_top10_pct > 80:
        print("   ⚠️ YES 大戶集中度極高，留意大戶動向")
    elif no_top10_pct > 80:
        print("   ⚠️ NO 大戶集中度極高，留意大戶動向")
    else:
        print("   ✅ 持倉分佈相對分散")
    
    print("\n" + "="*80)
    
    # Return enhanced dist with system wallet info
    dist['yes']['real_holders'] = yes_real
    dist['yes']['system_holders'] = yes_system
    dist['no']['real_holders'] = no_real
    dist['no']['system_holders'] = no_system
    dist['real_ratio'] = {'yes_pct': yes_pct, 'no_pct': no_pct}
    
    return dist



# =============================================================================
# Market Analysis Functions
# =============================================================================

def get_holders(condition_id: str) -> list:
    """獲取市場所有持倉者（使用 holders API）"""
    try:
        resp = requests.get(
            f"{DATA_API}/holders",
            params={"market": condition_id, "limit": 1000},  # 提高到 1000
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            # Parse holders from both tokens
            all_holders = []
            for token_data in data:
                holders = token_data.get('holders', [])
                for h in holders:
                    all_holders.append({
                        'wallet': h.get('proxyWallet', ''),
                        'name': h.get('name', h.get('pseudonym', '')),
                        'amount': float(h.get('amount', 0)),
                        'outcomeIndex': h.get('outcomeIndex', 0)
                    })
            return all_holders
        return []
    except Exception as e:
        print(f"   ⚠️ 無法獲取持倉數據: {e}")
        return []


# Note: Activity API requires 'user' parameter, cannot get market-wide trades
# This function is kept for compatibility but will return empty list
def get_trades(condition_id: str, limit: int = 1000) -> list:
    """獲取市場交易記錄 (已停用 - API 需要 user 參數)"""
    return []


def get_historical_prices(condition_id: str, days: int = 7) -> dict:
    """獲取歷史價格"""
    try:
        # Try to get token ID first
        client = get_client(with_creds=False)
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        if not tokens:
            return {}
        
        # Get Yes token
        yes_token = None
        for t in tokens:
            if t.get('outcome', '').lower() == 'yes':
                yes_token = t['token_id']
                break
        
        if not yes_token:
            yes_token = tokens[0]['token_id']
        
        # Fetch price history with appropriate interval
        end_ts = int(datetime.now().timestamp())
        start_ts = end_ts - (days * 24 * 3600)
        
        # Use 1h interval for better resolution, increase fidelity
        interval = "1h" if days <= 7 else "1d"
        fidelity = min(days * 24, 500) if days <= 7 else min(days, 365)
        
        resp = requests.get(
            f"{CLOB_API}/prices-history",
            params={
                "market": yes_token,
                "interval": interval,
                "startTs": start_ts,
                "endTs": end_ts,
                "fidelity": fidelity
            },
            timeout=15
        )
        
        if resp.status_code == 200:
            return resp.json()
        return {}
    except:
        return {}


def analyze_market(condition_id: str, json_output: bool = False):
    """
    市場深度分析
    
    包含:
    - 市場基本信息
    - 持倉分佈
    - 交易模式
    - 價格趨勢
    """
    print(f"\n🔍 分析市場: {condition_id[:30]}...")
    print("="*80)
    
    # Get market info
    market = get_market_info(condition_id)
    if not market:
        print("❌ 找不到市場")
        return None
    
    question = market.get('question', 'Unknown')
    volume = float(market.get('volume', market.get('volumeNum', 0)))
    
    print(f"\n📊 {question}")
    print(f"   成交量: ${volume:,.0f}")
    
    # Get current prices (prefer cache data if available)
    best_bid = market.get('bestBid')
    best_ask = market.get('bestAsk')
    cache_spread = market.get('spread')
    
    # If cache has good data, use it; otherwise fallback to live orderbook
    if best_bid and best_ask and best_bid > 0.001 and best_ask < 0.999:
        spread = best_ask - best_bid if best_ask and best_bid else None
        spread_pct = (spread / best_ask * 100) if spread and best_ask else None
        print(f"\n💹 當前報價:")
        print(f"   Yes - Bid: ${best_bid:.2f} | Ask: ${best_ask:.2f}")
        print(f"   Spread: {spread_pct:.1f}%" if spread_pct else "")
        orderbook = {'best_bid': best_bid, 'best_ask': best_ask, 'spread_pct': spread_pct}
    else:
        orderbook = get_orderbook(condition_id, "Yes")
        if "error" not in orderbook:
            print(f"\n💹 當前報價:")
            print(f"   Yes - Bid: ${orderbook['best_bid']:.2f} | Ask: ${orderbook['best_ask']:.2f}")
            print(f"   Spread: {orderbook['spread_pct']:.1f}%")
    
    # Get holders
    print(f"\n📊 持倉分析...")
    holders = get_holders(condition_id)
    
    if holders:
        # Analyze distribution
        whale_threshold = 5000  # $5k
        current_price = orderbook.get('best_bid', 0.5) if "error" not in orderbook else 0.5
        
        yes_holders = []
        no_holders = []
        
        for h in holders:
            amount = h['amount']
            value = amount * current_price
            
            if h['outcomeIndex'] == 0:  # Yes
                yes_holders.append({'amount': amount, 'value': value, 'wallet': h['wallet'], 'name': h['name']})
            else:  # No
                no_holders.append({'amount': amount, 'value': value, 'wallet': h['wallet'], 'name': h['name']})
        
        total_yes_value = sum(h['value'] for h in yes_holders)
        total_no_value = sum(h['value'] for h in no_holders)
        total_value = total_yes_value + total_no_value
        
        whale_count = sum(1 for h in holders if h['amount'] * current_price > whale_threshold)
        
        print(f"   Top 持倉者: {len(holders)} (每側最多 20 個)")
        print(f"   總持倉價值: ${total_value:,.0f}")
        print(f"   鯨魚數量 (>${whale_threshold:,}): {whale_count}")
        if total_value > 0:
            yes_pct = total_yes_value/total_value*100
            no_pct = total_no_value/total_value*100
            print(f"   Yes 價值: ${total_yes_value:,.0f} ({yes_pct:.1f}%) | No 價值: ${total_no_value:,.0f} ({no_pct:.1f}%)")
    
    # Skip trades analysis (API requires user parameter)
    # print(f"\n📈 交易分析...")
    # print(f"   ⚠️ 交易記錄需要指定錢包地址")
    
    # Historical price (multiple timeframes)
    print(f"\n📅 價格歷史...")
    
    # Get 7-day history
    history_7d = get_historical_prices(condition_id, days=7)
    history_3d = get_historical_prices(condition_id, days=3)
    history_1d = get_historical_prices(condition_id, days=1)
    
    def calculate_change(history):
        if history and isinstance(history, dict):
            prices = history.get('history', [])
            if len(prices) >= 2:
                first = float(prices[0].get('p', 0))
                last = float(prices[-1].get('p', 0))
                if first > 0:
                    return (last - first) / first * 100, first, last
        return None, None, None
    
    change_7d, first_7d, last_7d = calculate_change(history_7d)
    change_3d, first_3d, last_3d = calculate_change(history_3d)
    change_1d, first_1d, last_1d = calculate_change(history_1d)
    
    if change_1d is not None:
        print(f"   1 日變化: {'+' if change_1d > 0 else ''}{change_1d:.1f}% (${first_1d:.3f} → ${last_1d:.3f})")
    if change_3d is not None:
        print(f"   3 日變化: {'+' if change_3d > 0 else ''}{change_3d:.1f}% (${first_3d:.3f} → ${last_3d:.3f})")
    if change_7d is not None:
        print(f"   7 日變化: {'+' if change_7d > 0 else ''}{change_7d:.1f}% (${first_7d:.3f} → ${last_7d:.3f})")
    
    if not any([change_1d, change_3d, change_7d]):
        print(f"   ⚠️ 無法獲取價格歷史")
    
    print("\n" + "="*80)
    
    if json_output:
        result = {
            "condition_id": condition_id,
            "question": question,
            "volume": volume,
            "positions_count": len(positions) if positions else 0,
            "trades_count": len(trades) if trades else 0
        }
        print(json.dumps(result, indent=2))
        return result
    
    return market


# =============================================================================
# Whale Analysis Functions
# =============================================================================

def analyze_whales(condition_id: str, min_value: float = 5000):
    """
    鯨魚分析
    
    通過 /holders?market= API 獲取所有持倉者數據
    """
    print(f"\n🐋 鯨魚分析: {condition_id[:30]}...")
    print(f"   最低門檻: ${min_value:,.0f}")
    print("="*80)
    
    # Get holders data using /holders?market= endpoint
    try:
        resp = requests.get(
            f"{DATA_API}/holders",
            params={"market": condition_id, "limit": 100},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"❌ API 錯誤: {resp.status_code}")
            return None
        
        data = resp.json()
        if not data:
            print("❌ 無法獲取持倉數據")
            return None
    except Exception as e:
        print(f"❌ 請求錯誤: {e}")
        return None
    
    # Parse holders from both tokens (Yes and No)
    all_holders = []
    for token_data in data:
        outcome_index = None
        holders = token_data.get('holders', [])
        for h in holders:
            outcome_index = h.get('outcomeIndex', 0)
            outcome = 'Yes' if outcome_index == 0 else 'No'
            amount = float(h.get('amount', 0))
            
            # Estimate value (assume mid price 0.5 for simplicity, or use actual price)
            # Note: For accurate value, we'd need current prices
            value = amount * 0.5  # Conservative estimate
            
            all_holders.append({
                'wallet': h.get('proxyWallet', h.get('user', '?')),
                'name': h.get('name', h.get('pseudonym', '')),
                'outcome': outcome,
                'shares': amount,
                'value': value
            })
    
    if not all_holders:
        print("❌ 無持倉者數據")
        return None
    
    # Aggregate by wallet
    wallet_stats = {}
    for h in all_holders:
        wallet = h['wallet']
        if wallet not in wallet_stats:
            wallet_stats[wallet] = {
                'name': h['name'],
                'yes_shares': 0,
                'no_shares': 0,
                'yes_value': 0,
                'no_value': 0,
                'total_value': 0
            }
        
        if h['outcome'] == 'Yes':
            wallet_stats[wallet]['yes_shares'] += h['shares']
            wallet_stats[wallet]['yes_value'] += h['value']
        else:
            wallet_stats[wallet]['no_shares'] += h['shares']
            wallet_stats[wallet]['no_value'] += h['value']
        wallet_stats[wallet]['total_value'] += h['value']
    
    # Find whales (wallets with value > min_value)
    whales = []
    for wallet, stats in wallet_stats.items():
        if stats['total_value'] >= min_value:
            direction = 'YES' if stats['yes_value'] > stats['no_value'] else 'NO'
            whales.append({
                'wallet': wallet,
                'name': stats['name'],
                'direction': direction,
                'yes_shares': stats['yes_shares'],
                'no_shares': stats['no_shares'],
                'total_value': stats['total_value']
            })
    
    whales.sort(key=lambda x: x['total_value'], reverse=True)
    
    print(f"\n找到 {len(whales)} 個鯨魚 (>${min_value:,.0f}):\n")
    print("正在分析鯨魚交易歷史...\n")
    
    # Import classification functions
    from utils.trader_classification import is_likely_market_maker, is_smart_money, classify_trader_role
    
    yes_value = 0
    no_value = 0
    smart_money_count = 0
    market_maker_count = 0
    
    for i, w in enumerate(whales[:15], 1):
        if w['direction'] == 'YES':
            emoji = "🟢"
            yes_value += w['total_value']
        else:
            emoji = "🔴"
            no_value += w['total_value']
        
        # Get wallet trade history for classification
        role_emoji = "👤"
        role_label = ""
        roi_display = ""
        try:
            # Fetch more trades for better accuracy (500 instead of 100)
            resp = requests.get(
                f"{DATA_API}/activity",
                params={"user": w['wallet'], "limit": 500, "type": "TRADE"},
                timeout=15
            )
            if resp.status_code == 200:
                trades = resp.json()
                if isinstance(trades, dict):
                    trades = trades.get('data', [])
                
                # Calculate basic stats for classification
                total_trades = len(trades)
                buy_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'BUY')
                sell_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'SELL')
                
                # Calculate PnL more accurately
                # Net PnL = sell proceeds - buy cost (for closed positions)
                # This doesn't account for current holdings value accurately
                net_realized_pnl = sell_volume - buy_volume
                
                # Show net PnL instead of ROI (more reliable)
                if abs(buy_volume) > 10:  # Only show if meaningful trade volume
                    if net_realized_pnl >= 0:
                        roi_display = f" (PnL: +${net_realized_pnl:,.0f})"
                    else:
                        roi_display = f" (PnL: -${abs(net_realized_pnl):,.0f})"
                    
                    # Determine if winning or losing based on PnL
                    estimated_pnl = net_realized_pnl
                else:
                    estimated_pnl = 0
                
                wallet_data = {
                    'market_trades': total_trades,
                    'global_trades': total_trades,
                    'market_pnl': estimated_pnl,
                    'total_value': w['total_value'],
                    'is_market_maker': False
                }
                
                is_mm, mm_conf, _ = is_likely_market_maker(wallet_data)
                wallet_data['is_market_maker'] = is_mm
                
                role = classify_trader_role(wallet_data)
                role_emoji = role['emoji']
                role_label = role['role']
                
                # Add trade count to ROI display
                roi_display = f"{roi_display} [{total_trades}筆]" if roi_display else f" [{total_trades}筆]"
                
                if role['role'] == 'SMART_MONEY':
                    smart_money_count += 1
                elif role['role'] == 'MARKET_MAKER':
                    market_maker_count += 1
        except:
            pass
        
        name_display = f" ({w['name']})" if w['name'] else ""
        role_display = f" {role_emoji} {role_label}{roi_display}" if role_label else ""
        print(f"{i:>2}. {emoji} {w['wallet']}{name_display}")
        print(f"    方向: {w['direction']} | Yes: {w['yes_shares']:,.0f} | No: {w['no_shares']:,.0f}")
        print(f"    估值: ${w['total_value']:,.0f}{role_display}")
        print()
    
    if len(whales) > 15:
        print(f"   ... 仲有 {len(whales) - 15} 個鯨魚")
    
    total_whale_value = yes_value + no_value
    
    print("="*80)
    print(f"\n🐋 鯨魚統計:")
    print(f"   總鯨魚數: {len(whales)}")
    print(f"   🧠 Smart Money: {smart_money_count} 個")
    print(f"   🏦 Market Maker: {market_maker_count} 個")
    
    whale_signal = "NEUTRAL"
    if total_whale_value > 0:
        print(f"   Yes 價值: ${yes_value:,.0f} ({yes_value/total_whale_value*100:.0f}%)")
        print(f"   No 價值: ${no_value:,.0f} ({no_value/total_whale_value*100:.0f}%)")
        
        if yes_value > no_value * 1.5:
            print(f"\n🐋 鯨魚偏向: 強烈看多 YES")
            whale_signal = "YES"
        elif no_value > yes_value * 1.5:
            print(f"\n🐋 鯨魚偏向: 強烈看多 NO")
            whale_signal = "NO"
        else:
            print(f"\n🐋 鯨魚偏向: 分歧")
            whale_signal = "NEUTRAL"
    else:
        print(f"   暫無明確方向")
    
    print("="*80 + "\n")
    
    return {'whales': whales, 'signal': whale_signal, 'yes_value': yes_value, 'no_value': no_value, 'smart_money_count': smart_money_count, 'market_maker_count': market_maker_count}

def analyze_distribution(condition_id: str):
    """
    分析市場持倉分佈 - 識別 Smart Money vs Losers vs Retailers
    找出 contrarian trading 機會
    """
    print(f"\n📊 市場持倉分佈分析: {condition_id[:30]}...")
    print("="*80 + "\n")
    
    # Import classification functions
    from utils.trader_classification import classify_trader_role, is_likely_market_maker
    
    # Get market info
    market = get_market_info(condition_id)
    if not market:
        print("❌ 無法獲取市場數據")
        return
    
    question = market.get('question', 'Unknown Market')
    print(f"市場: {question}\n")
    print("="*80 + "\n")
    
    # Get all holders (increased limit for better coverage)
    holders = get_holders(condition_id)
    if not holders:
        print("⚠️  暫無持倉數據")
        return
    
    print(f"正在分析 {len(holders)} 個持倉者...\n")
    
    # Statistics by trader type
    stats = {
        'SMART_MONEY': {'yes': 0, 'no': 0, 'wallets': []},
        'LOSER': {'yes': 0, 'no': 0, 'wallets': []},
        'RETAILER': {'yes': 0, 'no': 0, 'wallets': []},
        'MARKET_MAKER': {'yes': 0, 'no': 0, 'wallets': []},
        'WHALE': {'yes': 0, 'no': 0, 'wallets': []},
        'REGULAR': {'yes': 0, 'no': 0, 'wallets': []}
    }
    
    analyzed_count = 0
    
    # Group holders by wallet to get YES/NO positions
    wallet_positions = {}
    for holder in holders:
        wallet = holder.get('wallet')
        if not wallet:
            continue
        
        if wallet not in wallet_positions:
            wallet_positions[wallet] = {'yes': 0, 'no': 0, 'name': holder.get('name', '')}
        
        outcome_index = holder.get('outcomeIndex', 0)
        amount = holder.get('amount', 0)
        
        if outcome_index == 0:  # YES token
            wallet_positions[wallet]['yes'] += amount
        else:  # NO token
            wallet_positions[wallet]['no'] += amount
    
    print(f"正在分析 {len(wallet_positions)} 個唯一持倉者...\n")
    
    for wallet, position in wallet_positions.items():
        yes_value = position['yes']
        no_value = position['no']
        
        if yes_value == 0 and no_value == 0:
            continue
        
        # Get trade history for classification (limit for performance)
        try:
            resp = requests.get(
                f"{DATA_API}/activity",
                params={"user": wallet, "limit": 200, "type": "TRADE"},
                timeout=10
            )
            if resp.status_code == 200:
                trades = resp.json()
                if isinstance(trades, dict):
                    trades = trades.get('data', [])
                
                total_trades = len(trades)
                buy_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'BUY')
                sell_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'SELL')
                net_pnl = sell_volume - buy_volume
                
                wallet_data = {
                    'market_trades': total_trades,
                    'global_trades': total_trades,  # Approximation
                    'market_pnl': net_pnl,
                    'total_value': yes_value + no_value,
                    'yes_value': yes_value,  # 🆕 for MM balance check
                    'no_value': no_value,    # 🆕 for MM balance check
                    'is_market_maker': False
                }
                
                # Check if MM first
                is_mm, mm_conf, _ = is_likely_market_maker(wallet_data)
                wallet_data['is_market_maker'] = is_mm
                
                # Classify
                role = classify_trader_role(wallet_data)
                role_type = role['role']
                
                # Accumulate stats
                if role_type in stats:
                    if yes_value > no_value:
                        stats[role_type]['yes'] += yes_value
                        stats[role_type]['wallets'].append({'wallet': wallet, 'side': 'YES', 'value': yes_value})
                    else:
                        stats[role_type]['no'] += no_value
                        stats[role_type]['wallets'].append({'wallet': wallet, 'side': 'NO', 'value': no_value})
                
                analyzed_count += 1
                if analyzed_count % 10 == 0:
                    print(f"  已分析 {analyzed_count}/{len(holders)} 持倉者...", end='\r')
        except:
            pass
    
    print(f"\n✅ 完成分析 {analyzed_count} 個持倉者\n")
    print("="*80 + "\n")
    
    # Display results
    for role_type in ['SMART_MONEY', 'LOSER', 'RETAILER']:
        role_data = stats[role_type]
        total = role_data['yes'] + role_data['no']
        
        if total > 0:
            yes_pct = (role_data['yes'] / total) * 100
            no_pct = (role_data['no'] / total) * 100
            wallet_count = len(role_data['wallets'])
            
            emoji_map = {
                'SMART_MONEY': '🧠',
                'LOSER': '📉',
                'RETAILER': '🎰'
            }
            emoji = emoji_map.get(role_type, '👤')
            
            # 樣本數不足警告
            sample_warning = ""
            if wallet_count < 5:
                sample_warning = " ⚠️ 樣本數不足 (<5 錢包)"
            
            print(f"{emoji} {role_type}{sample_warning}")
            print(f"   YES: ${role_data['yes']:,.0f} ({wallet_count} wallets) [{yes_pct:.0f}%]")
            print(f"   NO:  ${role_data['no']:,.0f} ({wallet_count} wallets) [{no_pct:.0f}%]")
            
            if wallet_count >= 5:  # 只有樣本足夠才顯示偏向
                if yes_pct > 65:
                    print(f"   {'':>3}└─ 偏向 YES")
                elif no_pct > 65:
                    print(f"   {'':>3}└─ 偏向 NO")
            print()
    
    # Market Makers (excluded from signal)
    mm_data = stats['MARKET_MAKER']
    mm_total = mm_data['yes'] + mm_data['no']
    if mm_total > 0:
        mm_count = len(mm_data['wallets'])
        print(f"🏦 MARKET MAKERS (已過濾)")
        print(f"   共 {mm_count} 個做市商，總流動性: ${mm_total:,.0f}")
        print()
    
    print("="*80 + "\n")
    
    # Calculate contrarian signals
    def calculate_signal(target_side: str):
        """Calculate signal strength for target side (YES or NO)"""
        score = 0
        reasons = []
        
        sm_data = stats['SMART_MONEY']
        loser_data = stats['LOSER']
        retail_data = stats['RETAILER']
        
        sm_total = sm_data['yes'] + sm_data['no']
        loser_total = loser_data['yes'] + loser_data['no']
        retail_total = retail_data['yes'] + retail_data['no']
        
        # 樣本數檢查
        sm_wallets = len(sm_data['wallets'])
        loser_wallets = len(loser_data['wallets'])
        retail_wallets = len(retail_data['wallets'])
        
        MIN_SAMPLE = 5  # 最小樣本數
        
        # Smart Money alignment (max 40 points) - 需要足夠樣本
        if sm_total > 0 and sm_wallets >= MIN_SAMPLE:
            if target_side == 'YES':
                sm_pct = (sm_data['yes'] / sm_total) * 100
            else:
                sm_pct = (sm_data['no'] / sm_total) * 100
            
            if sm_pct > 50:
                points = int(40 * (sm_pct / 100))
                score += points
                reasons.append(f"Smart Money: {sm_pct:.0f}% {target_side} ✅ (+{points} 分)")
        
        # Losers contrarian (max 30 points) - 需要足夠樣本
        if loser_total > 0 and loser_wallets >= MIN_SAMPLE:
            opposite_side = 'NO' if target_side == 'YES' else 'YES'
            if opposite_side == 'YES':
                loser_pct = (loser_data['yes'] / loser_total) * 100
            else:
                loser_pct = (loser_data['no'] / loser_total) * 100
            
            if loser_pct > 50:
                points = int(30 * (loser_pct / 100))
                score += points
                reasons.append(f"Losers: {loser_pct:.0f}% {opposite_side} ✅ (+{points} 分)")
        
        # Retailers alignment with losers (max 20 points) - 需要足夠樣本
        if retail_total > 0 and loser_total > 0 and retail_wallets >= MIN_SAMPLE:
            opposite_side = 'NO' if target_side == 'YES' else 'YES'
            if opposite_side == 'YES':
                retail_pct = (retail_data['yes'] / retail_total) * 100
                loser_pct = (loser_data['yes'] / loser_total) * 100
            else:
                retail_pct = (retail_data['no'] / retail_total) * 100
                loser_pct = (loser_data['no'] / loser_total) * 100
            
            if retail_pct > 50 and loser_pct > 50:
                points = int(20 * (retail_pct / 100))
                score += points
                reasons.append(f"Retailers: {retail_pct:.0f}% {opposite_side} ✅ (+{points} 分)")
        
        # Divergence bonus (max 10 points) - 需要足夠樣本
        if sm_total > 0 and loser_total > 0 and sm_wallets >= MIN_SAMPLE and loser_wallets >= MIN_SAMPLE:
            if target_side == 'YES':
                sm_yes_pct = (sm_data['yes'] / sm_total) * 100
                loser_yes_pct = (loser_data['yes'] / loser_total) * 100
            else:
                sm_yes_pct = (sm_data['no'] / sm_total) * 100
                loser_yes_pct = (loser_data['no'] / loser_total) * 100
            
            divergence = abs(sm_yes_pct - loser_yes_pct)
            if divergence > 30:
                score += 10
                reasons.append(f"強烈分歧 ({divergence:.0f}%) ✅ (+10 分)")
        
        return score, reasons
    
    # Calculate both sides
    print("📈 Contrarian Signal 評分")
    print("="*80 + "\n")
    
    yes_score, yes_reasons = calculate_signal('YES')
    no_score, no_reasons = calculate_signal('NO')
    
    # Determine signal strength emoji
    def get_strength_emoji(score):
        if score >= 71:
            return "🔥"
        elif score >= 51:
            return "🟠"
        elif score >= 31:
            return "🟡"
        else:
            return "⚪"
    
    # Display YES signal
    print(f"⚡ YES 信號強度: {yes_score}/100 {get_strength_emoji(yes_score)}")
    if yes_reasons:
        print()
        for reason in yes_reasons:
            print(f"   {reason}")
        print()
        if yes_score >= 51:
            print("   🎯 建議: 考慮買入 YES")
        print()
    else:
        print("   (無明確信號)\n")
    
    # Display NO signal
    print(f"⚡ NO 信號強度: {no_score}/100 {get_strength_emoji(no_score)}")
    if no_reasons:
        print()
        for reason in no_reasons:
            print(f"   {reason}")
        print()
        if no_score >= 51:
            print("   🎯 建議: 考慮買入 NO")
        print()
    else:
        print("   (無明確信號)\n")
    
    print("="*80 + "\n")
    
    return {
        'stats': stats,
        'yes_score': yes_score,
        'no_score': no_score,
        'recommendation': 'YES' if yes_score > no_score and yes_score >= 51 else 'NO' if no_score > yes_score and no_score >= 51 else 'NEUTRAL'
    }

# =============================================================================
# Wallet Analysis Functions
# =============================================================================

def analyze_wallet(wallet_address: str, max_trades: int = 500):
    """
    錢包起底 v2.0
    
    整合功能:
    - Market Maker 識別
    - Smart Money 識別  
    - Win/Loss 追蹤
    - Market-by-Market PnL
    """
    from utils.trader_classification import is_likely_market_maker, is_smart_money, classify_trader_role
    from collections import defaultdict
    
    print(f"\n🔍 錢包起底: {wallet_address}")
    print("="*80)
    
    # Get wallet positions
    try:
        resp = requests.get(
            f"{DATA_API}/positions",
            params={"user": wallet_address},
            timeout=30
        )
        
        if resp.status_code != 200:
            print("❌ 無法獲取持倉")
            return None
        
        positions = resp.json()
    except Exception as e:
        print(f"❌ API 錯誤: {e}")
        return None
    
    # Get trade history
    print(f"\n📈 獲取交易歷史 (最近 {max_trades} 筆)...", end="", flush=True)
    
    try:
        resp = requests.get(
            f"{DATA_API}/activity",
            params={"user": wallet_address, "limit": max_trades, "type": "TRADE"},
            timeout=30
        )
        
        if resp.status_code == 200:
            trades = resp.json()
            if isinstance(trades, dict):
                trades = trades.get('data', [])
            print(f" Done ({len(trades)})")
        else:
            trades = []
            print(" Failed")
    except:
        trades = []
        print(" Failed")
    
    # Calculate global stats
    total_trades = len(trades)
    buy_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'BUY')
    sell_volume = sum(float(t.get('usdcSize', 0)) for t in trades if t.get('side') == 'SELL')
    
    # Market-by-Market Analysis
    market_stats = defaultdict(lambda: {
        'question': 'Unknown',
        'buys': 0,
        'sells': 0,
        'buy_volume': 0,
        'sell_volume': 0,
        'shares_held': 0,
        'cost_basis': 0,
        'sell_revenue': 0,
        'realized_pnl': 0,
        'trades_count': 0
    })
    
    for trade in trades:
        market_id = trade.get('conditionId', '')
        if not market_id:
            continue
            
        stats = market_stats[market_id]
        stats['question'] = trade.get('title', 'Unknown Market')
        stats['trades_count'] += 1
        
        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0)) if trade.get('price') else 0
        usdc_size = float(trade.get('usdcSize', 0)) if trade.get('usdcSize') else size * price
        side = trade.get('side', '').upper()
        
        if side == 'BUY':
            stats['buys'] += 1
            stats['buy_volume'] += usdc_size
            stats['cost_basis'] += usdc_size
            stats['shares_held'] += size
        elif side == 'SELL':
            stats['sells'] += 1
            stats['sell_volume'] += usdc_size
            stats['sell_revenue'] += usdc_size
            stats['shares_held'] -= size
    
    # Calculate PnL per market
    wins = 0
    losses = 0
    total_realized_pnl = 0
    
    market_results = []
    for market_id, stats in market_stats.items():
        # Realized PnL (simplified FIFO)
        if stats['sells'] > 0 and stats['buys'] > 0:
            avg_buy_price = stats['buy_volume'] / (stats['buy_volume'] / 0.5) if stats['buy_volume'] > 0 else 0
            realized_pnl = stats['sell_revenue'] - stats['cost_basis']
        else:
            realized_pnl = 0
        
        stats['realized_pnl'] = realized_pnl
        total_realized_pnl += realized_pnl
        
        if realized_pnl > 0:
            wins += 1
        elif realized_pnl < 0:
            losses += 1
        
        market_results.append({
            'market_id': market_id,
            'question': stats['question'],
            'trades': stats['trades_count'],
            'pnl': realized_pnl,
            'shares_held': stats['shares_held']
        })
    
    # Sort by PnL
    market_results.sort(key=lambda x: x['pnl'], reverse=True)
    
    # Calculate unrealized PnL from active positions
    active_positions = [p for p in positions if float(p.get('size', 0)) > 0.01]
    
    total_position_value = 0
    total_unrealized_pnl = 0
    
    for p in active_positions:
        size = float(p.get('size', 0))
        avg_price = float(p.get('avgPrice', 0))
        cur_price = float(p.get('curPrice', 0))
        
        cost = size * avg_price
        value = size * cur_price
        pnl = value - cost
        
        total_position_value += value
        total_unrealized_pnl += pnl
    
    # Trader Classification
    wallet_data = {
        'market_trades': total_trades,
        'global_trades': total_trades,  # Could fetch real global count via separate API
        'market_pnl': total_realized_pnl + total_unrealized_pnl,
        'total_value': total_position_value,
        'is_market_maker': False
    }
    
    is_mm, mm_conf, mm_reasons = is_likely_market_maker(wallet_data)
    wallet_data['is_market_maker'] = is_mm
    
    is_sm, sm_conf, sm_reasons = is_smart_money(wallet_data)
    
    trader_role = classify_trader_role(wallet_data)
    
    # ========== 輸出報告 ==========
    print(f"\n{trader_role['emoji']} 交易者類型: {trader_role['role']} (信心: {trader_role['confidence']})")
    if trader_role['reasons']:
        for reason in trader_role['reasons'][:3]:
            print(f"   • {reason}")
    
    print(f"\n📊 總體統計:")
    print(f"   總交易次數: {total_trades}")
    print(f"   買入總額: ${buy_volume:,.0f}")
    print(f"   賣出總額: ${sell_volume:,.0f}")
    print(f"   淨流向: {'買入' if buy_volume > sell_volume else '賣出'}")
    
    print(f"\n💰 盈虧統計:")
    print(f"   已實現盈虧: ${total_realized_pnl:+,.0f}")
    print(f"   未實現盈虧: ${total_unrealized_pnl:+,.0f}")
    print(f"   總盈虧: ${(total_realized_pnl + total_unrealized_pnl):+,.0f}")
    
    if wins + losses > 0:
        win_rate = wins / (wins + losses) * 100
        print(f"\n🎯 勝負記錄:")
        print(f"   勝: {wins} | 負: {losses}")
        print(f"   勝率: {win_rate:.1f}%")
    
    print(f"\n💼 目前持倉: {len(active_positions)} 個")
    print(f"   持倉價值: ${total_position_value:,.0f}")
    
    # Top Markets by PnL
    if market_results:
        print(f"\n📈 表現最好的市場 (Top 5):")
        for i, m in enumerate(market_results[:5], 1):
            if m['pnl'] > 0:
                print(f"   {i}. {m['question'][:50]}...")
                print(f"      PnL: ${m['pnl']:+,.2f} | Trades: {m['trades']}")
        
        print(f"\n📉 表現最差的市場 (Bottom 3):")
        for i, m in enumerate(market_results[-3:], 1):
            if m['pnl'] < 0:
                print(f"   {i}. {m['question'][:50]}...")
                print(f"      PnL: ${m['pnl']:+,.2f} | Trades: {m['trades']}")
    
    print("\n" + "="*80 + "\n")
    
    return {
        "wallet": wallet_address,
        "trader_role": trader_role['role'],
        "is_market_maker": is_mm,
        "is_smart_money": is_sm,
        "total_trades": total_trades,
        "total_pnl": total_realized_pnl + total_unrealized_pnl,
        "win_rate": wins / (wins + losses) * 100 if (wins + losses) > 0 else 0,
        "positions": len(active_positions),
        "total_value": total_position_value
    }


# =============================================================================
# Odds Analysis Functions
# =============================================================================

def analyze_odds(event_slug: str, lookback_days: list = [7, 14, 30]):
    """
    賠率分析 (含歷史回顧)
    
    分析 event 嘅所有子市場賠率變化
    """
    print(f"\n📊 賠率分析: {event_slug}")
    print("="*80)
    
    # Fetch event
    try:
        resp = requests.get(
            f"{GAMMA_API}/events",
            params={"slug": event_slug},
            timeout=15
        )
        
        if resp.status_code != 200:
            # Try as search
            resp = requests.get(
                f"{GAMMA_API}/events",
                params={"_q": event_slug, "limit": 1},
                timeout=15
            )
        
        if resp.status_code != 200:
            print("❌ 找不到 Event")
            return None
        
        events = resp.json()
        if not events:
            print("❌ 找不到 Event")
            return None
        
        event = events[0] if isinstance(events, list) else events
    except Exception as e:
        print(f"❌ API 錯誤: {e}")
        return None
    
    event_title = event.get('title', event_slug)
    print(f"\n📌 {event_title}")
    
    markets = event.get('markets', [])
    if not markets:
        print("❌ Event 無市場")
        return None
    
    print(f"   包含 {len(markets)} 個子市場\n")
    
    for i, m in enumerate(markets[:15], 1):
        question = m.get('question', m.get('groupItemTitle', 'Unknown'))[:50]
        
        # Get current price
        prices = m.get('outcomePrices')
        if prices:
            try:
                price_list = json.loads(prices) if isinstance(prices, str) else prices
                yes_price = float(price_list[0]) * 100
            except:
                yes_price = 50
        else:
            yes_price = 50
        
        # Price bar
        bar_len = int(yes_price / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        
        print(f"{i:>2}. {question}...")
        print(f"    Yes: {yes_price:>5.1f}% [{bar}]")
        print()
    
    if len(markets) > 15:
        print(f"   ... 仲有 {len(markets) - 15} 個市場")
    
    print("="*80 + "\n")
    
    return event


# =============================================================================
# Insider Analysis Functions
# =============================================================================

def get_historical_price_insider(clob_token_id: str, days_ago: int = 14) -> list:
    """獲取歷史價格數據 (用於 insider detection)
    
    Returns:
        List of dicts with 'timestamp', 'datetime', 'price'
    """
    try:
        from datetime import timedelta
        start_ts = int((datetime.now() - timedelta(days=days_ago + 3)).timestamp())
        
        url = f"{CLOB_API}/prices-history"
        params = {
            "market": clob_token_id,
            "interval": "1d",
            "fidelity": 100,
            "startTs": start_ts
        }
        
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        history = data.get('history', [])
        
        if not history:
            return []
        
        # Return list of {timestamp, datetime, price}
        price_data = []
        for entry in history:
            t = entry.get('t', 0)
            p = entry.get('p', 0)
            if t and p:
                price_data.append({
                    'timestamp': t,
                    'datetime': datetime.fromtimestamp(t),
                    'price': float(p)
                })
        
        # Sort by timestamp
        price_data.sort(key=lambda x: x['timestamp'])
        return price_data
    except:
        return []



def resolve_condition_id(input_str: str) -> tuple:
    """
    解析用戶輸入，支持:
    1. Condition ID (0x...)
    2. Event slug (e.g., "trump-2024")
    3. Polymarket URL
    
    Returns: (condition_id, market_name) or (None, None)
    """
    import re
    
    # Case 1: Already a condition ID
    if input_str.startswith('0x') and len(input_str) >= 60:
        return input_str, None
    
    # Case 2: URL - extract slug
    if 'polymarket.com' in input_str:
        # Extract slug from URL
        match = re.search(r'polymarket\.com/event/([^/?]+)', input_str)
        if match:
            slug = match.group(1)
        else:
            # Try to get the last part of the URL
            slug = input_str.rstrip('/').split('/')[-1]
    else:
        # Case 3: Direct slug
        slug = input_str
    
    # Fetch market from slug
    print(f"🔍 解析市場: {slug}...")
    urls = get_api_urls()
    
    try:
        resp = requests.get(f"{urls['gamma']}/markets", params={"slug": slug}, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            markets = data if isinstance(data, list) else [data]
            
            if markets:
                market = markets[0]
                condition_id = market.get('conditionId', market.get('id'))
                market_name = market.get('question', 'Unknown')
                
                if condition_id:
                    print(f"✅ 找到市場: {market_name}")
                    return condition_id, market_name
        
        print(f"❌ 找不到市場: {slug}")
        return None, None
        
    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        return None, None


def detect_insider_activity(condition_id: str, price_threshold: float = 10.0, trade_threshold: float = 5000):
    """
    🕵️ Insider Activity Detector v3.0 - 交易時間分析
    
    核心邏輯:
    1. 識別價格突變的時間點
    2. 分析哪些錢包在突變**之前**落大注
    3. 計算「時間關聯度」- 押注離價格變動有幾近
    
    重點：唔係睇持倉分佈（其他功能已做），係睇交易時機！
    """
    from datetime import timedelta
    from collections import defaultdict
    
    print(f"\n🕵️ Insider Activity Detector v3.0: 交易時間分析")
    print("="*80)
    
    # Step 0: Resolve condition_id (support slug/URL)
    resolved_id, resolved_name = resolve_condition_id(condition_id)
    
    if not resolved_id:
        print(f"\n❌ 無法解析市場: {condition_id}")
        return {"error": "無法解析市場"}
    
    condition_id = resolved_id
    print(f"   市場: {condition_id[:30]}...")
    
    # Step 1: Get market info
    print(f"\n📊 獲取市場資訊...", end="", flush=True)
    market_info = get_market_info(condition_id)
    
    if not market_info or not market_info.get('question'):
        print(" 失敗")
        print(f"\n❌ 無法獲取市場資訊")
        return {"error": "無法獲取市場資訊"}
    
    market_name = market_info.get('question', 'Unknown Market')
    clob_token_ids = market_info.get('clobTokenIds', [])
    
    if isinstance(clob_token_ids, str):
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except:
            clob_token_ids = []
    
    # Try to get from clobTokenIds first, then from tokens array
    clob_token_id = clob_token_ids[0] if clob_token_ids else None
    
    if not clob_token_id:
        # Fallback: extract from tokens array
        tokens = market_info.get('tokens', [])
        if tokens and len(tokens) > 0:
            clob_token_id = tokens[0].get('token_id')
    
    print(f" ✅")
    print(f"📛 {market_name[:70]}...")
    
    # Step 2: Get price history to identify spikes
    print(f"\n📈 Step 1/3: 識別價格突變時間點...")
    
    if not clob_token_id:
        print("   ❌ 無法獲取價格歷史（缺少 Token ID）")
        return {"error": "無法獲取價格歷史"}
    
    price_history = get_historical_price_insider(clob_token_id, 14)
    
    if not price_history or len(price_history) < 2:
        print("   ❌ 無法獲取價格歷史")
        return {"error": "無法獲取價格歷史"}
    
    # Identify price spikes (compare consecutive data points)
    price_spikes = []
    
    for i in range(1, len(price_history)):
        prev = price_history[i-1]
        curr = price_history[i]
        
        p1 = prev['price']
        p2 = curr['price']
        
        if p1 > 0.01:  # Skip very low prices
            change = ((p2 - p1) / p1) * 100
            if abs(change) >= price_threshold:
                price_spikes.append({
                    "timestamp": curr['timestamp'],
                    "date": curr['datetime'],
                    "from_price": p1,
                    "to_price": p2,
                    "change_pct": change,
                    "direction": "UP" if change > 0 else "DOWN"
                })
    
    if not price_spikes:
        print(f"   ✅ 無顯著價格突變 (閾值: {price_threshold}%)")
        print(f"   💡 呢個市場價格穩定，唔適合 insider 分析")
        return {
            "market": market_name,
            "insider_risk": "LOW",
            "message": "價格穩定，無明顯突變",
            "price_spikes": []
        }
    
    # Sort by date (oldest first) for chronological display
    price_spikes_sorted = sorted(price_spikes, key=lambda x: x['date'])
    
    print(f"   🚨 發現 {len(price_spikes)} 個價格突變時間點 (過去 14 天):")
    for spike in price_spikes_sorted[:5]:  # Show first 5 chronologically
        arrow = "📈" if spike['direction'] == "UP" else "📉"
        # Show actual prices and time
        from_pct = spike['from_price'] * 100
        to_pct = spike['to_price'] * 100
        time_str = spike['date'].strftime('%Y-%m-%d %H:%M')
        print(f"      {arrow} {time_str}: {from_pct:.1f}% → {to_pct:.1f}% ({spike['change_pct']:+.1f}%)")
    
    # Step 3: Fetch trade history
    print(f"\n💹 Step 2/3: 獲取交易歷史...")
    
    try:
        # Try to get recent trades via DATA API
        resp = requests.get(
            f"{DATA_API}/trades",
            params={"market": condition_id, "limit": 1000},
            timeout=30
        )
        
        if resp.status_code != 200 or not resp.json():
            print("   ⚠️ 無法獲取交易歷史（API 限制）")
            print("   💡 提示：DATA API 需要有交易記錄才能分析")
            return {"error": "無法獲取交易歷史"}
        
        trades = resp.json()
        print(f"   ✅ 已獲取 {len(trades)} 筆交易記錄")
        
    except Exception as e:
        print(f"   ❌ API 錯誤: {e}")
        return {"error": f"API 錯誤: {e}"}
    
    # Step 4: Analyze trades timing relative to price spikes
    print(f"\n🔍 Step 3/3: 分析交易時機...")
    
    # Check trade history coverage
    oldest_trade_ts = None
    for trade in trades:
        ts = trade.get('timestamp', 0)
        if isinstance(ts, str):
            try:
                ts = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp())
            except:
                continue
        if ts > 0 and (oldest_trade_ts is None or ts < oldest_trade_ts):
            oldest_trade_ts = ts
    
    if oldest_trade_ts:
        oldest_trade_date = datetime.fromtimestamp(oldest_trade_ts)
        print(f"   📅 交易歷史範圍: {oldest_trade_date.strftime('%Y-%m-%d %H:%M')} → 現在")
    
    suspicious_trades = []
    wallet_analysis = defaultdict(lambda: {
        'trades_before_spike': [],
        'total_value_before_spike': 0,
        'spike_count': 0,
        'suspicion_score': 0
    })
    
    # Window analysis for each spike
    window_stats = []
    uncovered_spikes = []  # Track spikes we can't analyze
    
    for spike in price_spikes:
        spike_timestamp = int(spike['date'].timestamp())
        
        # Look for trades 1-24 hours BEFORE the spike
        # Tighter window = more precise insider detection
        window_start = spike_timestamp - (24 * 3600)  # 24 hours before
        window_end = spike_timestamp - (1 * 3600)     # 1 hour before (exclude immediate reactions)
        
        # Check if we have trade data covering this window
        if oldest_trade_ts and window_start < oldest_trade_ts:
            uncovered_spikes.append({
                'date': spike['date'].strftime('%Y-%m-%d %H:%M'),
                'change': spike['change_pct'],
                'direction': spike['direction'],
                'window_start': datetime.fromtimestamp(window_start).strftime('%Y-%m-%d %H:%M'),
                'oldest_trade': datetime.fromtimestamp(oldest_trade_ts).strftime('%Y-%m-%d %H:%M')
            })
            continue  # Skip this spike
        
        # Track all trades in window (ALL trades, not just buys)
        window_trades = []
        yes_buy_count = 0
        no_buy_count = 0
        yes_sell_count = 0
        no_sell_count = 0
        yes_buy_volume = 0
        no_buy_volume = 0
        yes_sell_volume = 0
        no_sell_volume = 0
        
        for trade in trades:
            trade_ts = trade.get('timestamp', 0)
            if isinstance(trade_ts, str):
                try:
                    trade_ts = int(datetime.fromisoformat(trade_ts.replace('Z', '+00:00')).timestamp())
                except:
                    continue
            
            # Check if trade happened in window
            if window_start <= trade_ts <= window_end:
                size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
                price = float(trade.get('price', 0) or 0)
                value = size * price if price > 0 else size
                
                outcome = trade.get('outcome', '').upper()
                side = trade.get('side', '').upper()
                
                # Track all trades in window
                window_trades.append({
                    'value': value,
                    'outcome': outcome,
                    'side': side,
                    'timestamp': trade_ts
                })
                
                # Count ALL trades (BUY and SELL)
                if side == 'BUY':
                    if outcome == 'YES':
                        yes_buy_count += 1
                        yes_buy_volume += value
                    elif outcome == 'NO':
                        no_buy_count += 1
                        no_buy_volume += value
                elif side == 'SELL':
                    if outcome == 'YES':
                        yes_sell_count += 1
                        yes_sell_volume += value
                    elif outcome == 'NO':
                        no_sell_count += 1
                        no_sell_volume += value
                
                # Check for suspicious large trades
                if value >= trade_threshold:
                    wallet = trade.get('proxyWallet', trade.get('maker', trade.get('taker', 'unknown')))
                    
                    # Check if bet direction matches spike direction
                    is_aligned = (
                        (spike['direction'] == 'UP' and outcome == 'YES' and side == 'BUY') or
                        (spike['direction'] == 'DOWN' and outcome == 'NO' and side == 'BUY')
                    )
                    
                    if is_aligned:
                        days_before = (spike_timestamp - trade_ts) / 86400
                        
                        suspicious_trades.append({
                            'wallet': wallet[:12] + "..." if len(wallet) > 12 else wallet,
                            'full_wallet': wallet,
                            'value': value,
                            'outcome': outcome,
                            'side': side,
                            'days_before_spike': days_before,
                            'spike_date': spike['date'].strftime('%Y-%m-%d'),
                            'spike_change': spike['change_pct'],
                            'trade_timestamp': trade_ts
                        })
                        
                        # Update wallet analysis
                        wallet_analysis[wallet]['trades_before_spike'].append({
                            'value': value,
                            'days_before': days_before,
                            'spike_change': spike['change_pct']
                        })
                        wallet_analysis[wallet]['total_value_before_spike'] += value
                        wallet_analysis[wallet]['spike_count'] += 1
        
        # Store window stats
        if window_trades:
            avg_bet_size = sum(t['value'] for t in window_trades) / len(window_trades)
            window_stats.append({
                'spike_date': spike['date'].strftime('%Y-%m-%d %H:%M'),
                'spike_direction': spike['direction'],
                'spike_change': spike['change_pct'],
                'total_trades': len(window_trades),
                'yes_buy_count': yes_buy_count,
                'no_buy_count': no_buy_count,
                'yes_sell_count': yes_sell_count,
                'no_sell_count': no_sell_count,
                'yes_buy_volume': yes_buy_volume,
                'no_buy_volume': no_buy_volume,
                'yes_sell_volume': yes_sell_volume,
                'no_sell_volume': no_sell_volume,
                'avg_bet_size': avg_bet_size
            })
    
    # Calculate suspicion scores
    for wallet, data in wallet_analysis.items():
        # Score based on:
        # 2. Total value
        # 3. Multiple spikes
        
        if data['trades_before_spike']:
            avg_days_before = sum(t['days_before'] for t in data['trades_before_spike']) / len(data['trades_before_spike'])
            avg_hours_before = avg_days_before * 24
            
            # Timing score (48 hour window)
            # 1-6 hours before = 10 points (VERY suspicious)
            # 6-24 hours before = 5-8 points (suspicious)
            # 24-48 hours before = 2-5 points (moderately suspicious)
            if avg_hours_before <= 6:
                timing_score = 10
            elif avg_hours_before <= 24:
                timing_score = 10 - (avg_hours_before - 6) / 18 * 5  # 10 → 5
            else:
                timing_score = 5 - (avg_hours_before - 24) / 24 * 3   # 5 → 2
            
            timing_score = max(0, timing_score)
            
            # Value score
            value_score = min(30, data['total_value_before_spike'] / 1000)  # Max 30 points
            
            # Multiple spikes = pattern
            pattern_score = min(20, data['spike_count'] * 10)  # Max 20 points
            
            data['suspicion_score'] = timing_score + value_score + pattern_score
    
    # Sort wallets by suspicion score
    suspicious_wallets = sorted(
        [{'wallet': w, **d} for w, d in wallet_analysis.items()],
        key=lambda x: x['suspicion_score'],
        reverse=True
    )
    
    # Calculate overall risk
    if not suspicious_wallets:
        risk_level = "LOW"
        risk_score = 0
        print(f"   ✅ 未發現可疑交易模式")
    else:
        top_suspicion = suspicious_wallets[0]['suspicion_score']
        risk_score = min(100, int(top_suspicion))
        
        if risk_score >= 50:
            risk_level = "CRITICAL"
        elif risk_score >= 35:
            risk_level = "HIGH"
        elif risk_score >= 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        print(f"   🚨 發現 {len(suspicious_wallets)} 個可疑錢包")
        print(f"   💰 可疑交易總數: {len(suspicious_trades)} 筆")
    
    # Display results
    risk_emoji = "🚨" if risk_level == "CRITICAL" else "⚠️" if risk_level == "HIGH" else "⚡" if risk_level == "MEDIUM" else "✅"
    
    print(f"\n{'='*80}")
    print(f"{risk_emoji} INSIDER RISK: {risk_level} (分數: {risk_score}/100)")
    print(f"{'='*80}\n")
    
    # Show window analysis for each spike
    if window_stats:
        print(f"📊 窗口分析報告 (價格突變前 24 小時):")
        print()
        
        for i, stat in enumerate(window_stats[:5], 1):  # Show top 5 spikes
            arrow = "📈" if stat['spike_direction'] == "UP" else "📉"
            print(f"  {i}. {arrow} {stat['spike_date']} ({stat['spike_change']:+.1f}%)")
            print(f"     📝 窗口內交易: {stat['total_trades']} 筆")
            
            # Show buy/sell breakdown
            total_yes = stat['yes_buy_count'] + stat['yes_sell_count']
            total_no = stat['no_buy_count'] + stat['no_sell_count']
            
            if total_yes + total_no > 0:
                print(f"     📊 交易分布:")
                print(f"        YES: {stat['yes_buy_count']} 買 / {stat['yes_sell_count']} 賣")
                print(f"        NO:  {stat['no_buy_count']} 買 / {stat['no_sell_count']} 賣")
                
                # Net buying pressure
                yes_net = stat['yes_buy_count'] - stat['yes_sell_count']
                no_net = stat['no_buy_count'] - stat['no_sell_count']
                
                if yes_net > 0:
                    print(f"     � 淨買壓: YES +{yes_net} | NO {no_net:+d}")
                elif no_net > 0:
                    print(f"     🔥 淨買壓: NO +{no_net} | YES {yes_net:+d}")
                
                # Volume
                total_volume = stat['yes_buy_volume'] + stat['no_buy_volume'] + stat['yes_sell_volume'] + stat['no_sell_volume']
                if total_volume > 0:
                    yes_vol = stat['yes_buy_volume'] + stat['yes_sell_volume']
                    yes_vol_pct = yes_vol / total_volume * 100
                    print(f"     💰 交易量: YES ${yes_vol:,.0f} ({yes_vol_pct:.1f}%) | NO ${total_volume - yes_vol:,.0f} ({100-yes_vol_pct:.1f}%)")
                
                print(f"     📏 平均押注: ${stat['avg_bet_size']:,.0f}")
            print()
        
        print()
    else:
        print(f"📊 窗口分析: 無法獲取窗口內交易數據")
        print(f"   💡 API 限制：只能獲取最近 500-1000 筆交易")
        print(f"   💡 較舊的價格突變可能無法分析窗口內交易")
        print()
    
    # Show uncovered spikes warning
    if uncovered_spikes:
        print(f"⚠️  無法分析的價格突變 (交易歷史不足):")
        print()
        for i, spike in enumerate(uncovered_spikes[:5], 1):
            arrow = "📈" if spike['direction'] == "UP" else "📉"
            print(f"  {i}. {arrow} {spike['date']} ({spike['change']:+.1f}%)")
            print(f"     需要數據: {spike['window_start']} 開始")
            print(f"     實際最舊: {spike['oldest_trade']}")
            print(f"     ❌ 無法分析此突變前的交易")
        
        if len(uncovered_spikes) > 5:
            print(f"\n  ... 還有 {len(uncovered_spikes) - 5} 個突變無法分析")
        print()
    
    if suspicious_wallets:
        print(f"🕵️ 可疑錢包 (Top 10) - 在價格突變前 1-48 小時內落大注:")
        print()
        
        for i, w in enumerate(suspicious_wallets[:10], 1):
            wallet_short = w['wallet'][:12] + "..." if len(w['wallet']) > 12 else w['wallet']
            print(f"  {i}. {wallet_short}")
            print(f"     🎯 可疑度: {w['suspicion_score']:.0f}/60")
            print(f"     💰 突變前押注總額: ${w['total_value_before_spike']:,.0f}")
            print(f"     📊 命中 {w['spike_count']} 次價格突變")
            
            # Show example trades
            if w['trades_before_spike']:
                best_trade = min(w['trades_before_spike'], key=lambda x: x['days_before'])
                hours_before = best_trade['days_before'] * 24
                print(f"     ⏰ 最接近突變: {hours_before:.1f} 小時前 (突變: {best_trade['spike_change']:+.1f}%)")
            print()
        
        print(f"💡 分析說明:")
        print(f"   • 可疑度評分基於: 交易時機 + 押注金額 + 命中次數")
        print(f"   • 時機越接近突變 = 越可疑 (1-6小時內最高分)")
        print(f"   • 分析窗口: 價格突變前 1-24 小時")
        print(f"   • 多次命中價格突變 = 可能有內幕消息")
        print()
    
    print("="*80 + "\n")
    
    return {
        "market": condition_id,
        "market_name": market_name,
        "insider_risk": {
            "level": risk_level,
            "score": risk_score
        },
        "price_spikes": [{
            'date': s['date'].strftime('%Y-%m-%d'),
            'change': s['change_pct'],
            'direction': s['direction']
        } for s in price_spikes],
        "suspicious_wallets": [{
            'wallet': w['wallet'][:12] + "...",
            'full_wallet': w['wallet'],
            'suspicion_score': round(w['suspicion_score'], 1),
            'total_value': round(w['total_value_before_spike'], 2),
            'spike_hits': w['spike_count']
        } for w in suspicious_wallets[:20]],
        "suspicious_trades_count": len(suspicious_trades),
        "thresholds": {
            "price_change": f"{price_threshold}%",
            "trade_value": f"${trade_threshold:,.0f}"
        }
    }


# =============================================================================
# Kelly Criterion Functions
# =============================================================================

def kelly_criterion(win_prob: float, odds: float) -> float:
    """Kelly 公式"""
    if win_prob <= 0 or win_prob >= 1 or odds <= 0 or odds >= 1:
        return 0
    
    b = (1 - odds) / odds
    p = win_prob
    q = 1 - p
    
    f = (b * p - q) / b
    
    return max(0, f)


def calculate_kelly(condition_id: str, estimate: float, bankroll: float = None,
                    fraction: float = 0.5, outcome: str = "Yes"):
    """
    Kelly 倉位計算
    
    Args:
        estimate: 你估計嘅真實機率 (0-1)
        bankroll: 總資金
        fraction: Kelly 分數 (0.5 = Half Kelly)
    """
    print(f"\n📐 Kelly Criterion 計算")
    print("="*60)
    
    # Get current odds
    orderbook = get_orderbook(condition_id, outcome)
    
    if "error" in orderbook:
        print(f"❌ 無法獲取報價: {orderbook['error']}")
        return None
    
    current_odds = orderbook['best_ask'] if outcome.lower() == 'yes' else orderbook['best_bid']
    
    print(f"\n📈 市場資訊:")
    print(f"   Outcome: {outcome}")
    print(f"   當前價格: ${current_odds:.2f} ({current_odds*100:.1f}%)")
    
    print(f"\n🧠 你嘅估計:")
    print(f"   真實機率: {estimate*100:.1f}%")
    
    # Edge
    edge = estimate - current_odds
    
    print(f"\n💡 Edge 分析:")
    if edge > 0:
        print(f"   ✅ 正 Edge: +{edge*100:.1f}%")
    else:
        print(f"   ❌ 負 Edge: {edge*100:.1f}%")
        print(f"   ⚠️ 唔建議落注")
    
    # Kelly
    kelly_f = kelly_criterion(estimate, current_odds)
    
    print(f"\n📐 Kelly 結果:")
    print(f"   Full Kelly: {kelly_f*100:.1f}% 嘅總資金")
    print(f"   Half Kelly: {kelly_f*50:.1f}%")
    print(f"   Quarter Kelly: {kelly_f*25:.1f}%")
    
    if bankroll:
        actual_bet = bankroll * kelly_f * fraction
        print(f"\n💰 實際金額 (${bankroll:.0f} x {fraction}x Kelly):")
        print(f"   建議下注: ${actual_bet:.2f}")
    
    print("\n" + "="*60)
    
    return {
        "current_odds": current_odds,
        "estimate": estimate,
        "edge": edge,
        "kelly_fraction": kelly_f,
        "recommended_bet": bankroll * kelly_f * fraction if bankroll else None
    }


# =============================================================================
# Insider Analysis Functions
# =============================================================================

def get_historical_price_for_insider(clob_token_id: str, days_ago: int = 14) -> dict:
    """
    獲取歷史價格數據（用於 insider detection）
    
    Returns:
        dict: {days_ago: price, ...} 例如 {0: 0.65, 1: 0.63, 7: 0.55}
    """
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
    except Exception as e:
        print(f"⚠️  獲取歷史價格失敗: {e}", file=sys.stderr)
        return {}


def detect_insider_activity(condition_id: str, price_threshold: float = 10.0, trade_threshold: float = 5000):
    """
    🕵️ Insider Activity Detector - 異常交易偵測
    
    偵測邏輯:
    1. 價格突變 (>threshold% 單日變化)
    2. 大額交易 (>$threshold)
    3. 時間關聯 (價格突變前後±1天的大額交易)
    
    Args:
        condition_id: 市場 Condition ID
        price_threshold: 價格變化門檻 (%, 預設 10%)
        trade_threshold: 大額交易門檻 ($, 預設 5000)
    
    Returns:
        dict: 包含風險評分、可疑事件等資訊
    """
    print(f"\n🕵️ Insider Activity Scan")
    print("="*80)
    print(f"   市場: {condition_id[:20]}...")
    print(f"   價格門檻: {price_threshold}% | 交易門檻: ${trade_threshold:,.0f}")
    print()
    
    # Step 1: Get market info
    from utils.market import get_market_info
    
    market_data = get_market_info(condition_id)
    if not market_data:
        print("❌ 無法獲取市場資訊")
        return {"error": "無法獲取市場資訊"}
    
    market_name = market_data.get('question', 'Unknown Market')
    print(f"📊 {market_name[:60]}...\n")
    
    # Get clob token ID for price history
    clob_token_ids = market_data.get('clobTokenIds', [])
    if isinstance(clob_token_ids, str):
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except:
            clob_token_ids = []
    
    clob_token_id = clob_token_ids[0] if clob_token_ids else None
    
    # Step 2: Fetch trades
    print("📊 正在獲取交易記錄...", end="", flush=True)
    trades = []
    offset = 0
    limit = 500
    
    while True:
        try:
            resp = requests.get(
                f"{DATA_API}/trades",
                params={"market": condition_id, "limit": limit, "offset": offset},
                timeout=10
            )
            if resp.status_code != 200 or not resp.json():
                break
            data = resp.json()
            trades.extend(data)
            print(".", end="", flush=True)
            if len(data) < limit or offset > 5000:
                break
            offset += limit
        except:
            break
    
    print(f" {len(trades)} 筆\n")
    
    if len(trades) < 50:
        print("⚠️  交易量太少，無法進行分析")
        return {"error": "市場交易量太少"}
    
    # Step 3: Get price history and detect spikes
    print("📈 分析價格歷史...")
    price_spikes = []
    
    if clob_token_id:
        prices = get_historical_price_for_insider(clob_token_id, 14)
        
        if prices:
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
            
            print(f"   發現 {len(price_spikes)} 個價格突變 (>{price_threshold}%)")
        else:
            print("   ⚠️  無法獲取價格歷史")
    else:
        print("   ⚠️  無 CLOB Token ID，跳過價格分析")
    
    # Step 4: Find large trades
    print("\n💰 分析大額交易...")
    large_trades = []
    
    for trade in trades:
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        if size >= trade_threshold:
            ts = trade.get('timestamp', 0)
            trade_date = datetime.fromtimestamp(ts) if ts else None
            
            large_trades.append({
                "wallet": trade.get('proxyWallet', '?')[:12] + "...",
                "full_wallet": trade.get('proxyWallet', '?'),
                "size": round(size, 2),
                "side": trade.get('side', '?'),
                "outcome": trade.get('outcome', '?'),
                "timestamp": trade_date.strftime("%Y-%m-%d %H:%M") if trade_date else "?",
                "days_ago": (datetime.now() - trade_date).days if trade_date else 999
            })
    
    print(f"   發現 {len(large_trades)} 筆大額交易 (>${trade_threshold:,.0f})")
    
    # Step 5: Correlate spikes with large trades
    print("\n🔍 關聯分析 (價格突變 + 大額交易)...")
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
    
    print(f"   發現 {len(suspicious_events)} 個可疑事件\n")
    
    # Step 6: Calculate risk score
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
    
    # Wallet concentration check
    wallet_counts = {}
    for t in large_trades:
        wallet = t['full_wallet']
        wallet_counts[wallet] = wallet_counts.get(wallet, 0) + 1
    
    max_wallet_trades = max(wallet_counts.values()) if wallet_counts else 0
    if max_wallet_trades >= 3:
        risk_score += 10
        risk_reasons.append(f"單一錢包多次大額交易 ({max_wallet_trades} 次)")
    
    risk_level = "CRITICAL" if risk_score >= 60 else "HIGH" if risk_score >= 40 else "MEDIUM" if risk_score >= 20 else "LOW"
    
    # Print summary
    print("="*80)
    
    risk_emoji = "🚨" if risk_level == "CRITICAL" else "⚠️" if risk_level == "HIGH" else "⚡" if risk_level == "MEDIUM" else "✅"
    
    print(f"\n{risk_emoji} INSIDER RISK: {risk_level} (評分: {risk_score}/100)\n")
    
    if risk_reasons:
        print("📋 風險因素:")
        for reason in risk_reasons:
            print(f"   • {reason}")
        print()
    
    if suspicious_events:
        print("🕵️  可疑事件詳情:\n")
        for i, event in enumerate(suspicious_events[:5], 1):
            severity_emoji = "🔴" if event['severity'] == "HIGH" else "🟡"
            print(f"{i}. {severity_emoji} {event['date']}")
            print(f"   價格變化: {event['price_change']}")
            print(f"   相關交易: {event['related_trades']} 筆，總額 ${event['total_volume']:,.0f}")
            
            if event['trades']:
                print(f"   大額交易:")
                for t in event['trades'][:3]:
                    print(f"      - {t['wallet']}: ${t['size']:,.0f} {t['side']} {t['outcome']} @ {t['timestamp']}")
            print()
    
    if len(large_trades) > 0:
        print("💰 最大額交易 (Top 5):\n")
        sorted_trades = sorted(large_trades, key=lambda x: x['size'], reverse=True)
        for i, t in enumerate(sorted_trades[:5], 1):
            print(f"{i}. {t['wallet']}: ${t['size']:,.0f} {t['side']} {t['outcome']} @ {t['timestamp']}")
        print()
    
    print("="*80 + "\n")
    
    result = {
        "market": condition_id,
        "market_name": market_name,
        "insider_risk": {
            "level": risk_level,
            "score": risk_score,
            "reasons": risk_reasons
        },
        "price_spikes": price_spikes,
        "large_trades_count": len(large_trades),
        "large_trades": large_trades[:20],  # Top 20
        "suspicious_events": suspicious_events,
        "thresholds": {
            "price_change": f"{price_threshold}%",
            "trade_size": f"${trade_threshold:,.0f}"
        }
    }
    
    return result


# =============================================================================
# Insider Detection Functions
# =============================================================================

def get_historical_price_for_insider(clob_token_id: str, days_ago: int = 14) -> dict:
    """
    獲取歷史價格數據用於 insider detection
    
    Returns:
        Dict mapping days_ago to price: {0: 0.65, 1: 0.63, ...}
    """
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
    except Exception as e:
        print(f"⚠️  獲取歷史價格失敗: {e}")
        return {}


def detect_insider_activity(condition_id: str, price_threshold: float = 10.0, trade_threshold: float = 5000):
    """
    🕵️ Insider Activity Detector - 異常交易偵測
    
    偵測邏輯:
    1. 價格突變 (>threshold% 單日變化)
    2. 大額交易 (>$threshold)
    3. 時間關聯 (價格突變前後的大額交易)
    
    Args:
        condition_id: Market condition ID
        price_threshold: 價格變化門檻 (percent)
        trade_threshold: 大額交易門檻 (USD)
    
    Returns:
        Dict with insider risk analysis
    """
    from utils.market import get_market_info
    
    print(f"\n🕵️ Insider Activity Scan: {condition_id[:30]}...")
    print("="*80)
    
    # Step 1: Get market info
    print(f"\n📊 獲取市場資訊...", end="", flush=True)
    market_info = get_market_info(condition_id)
    
    if not market_info:
        print(" ❌ 失敗")
        return {"error": "無法獲取市場資訊"}
    
    market_name = market_info.get('question', 'Unknown Market')
    print(f" ✅")
    print(f"   📛 {market_name[:60]}...")
    
    # Get clob token ID for price history
    clob_token_ids = market_info.get('clobTokenIds', [])
    if isinstance(clob_token_ids, str):
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except:
            clob_token_ids = []
    
    clob_token_id = clob_token_ids[0] if clob_token_ids else None
    
    # Step 2: Fetch trades
    print(f"\n📈 獲取交易記錄...", end="", flush=True)
    trades = []
    offset = 0
    limit = 500
    
    while True:
        try:
            resp = requests.get(f"{DATA_API}/trades", params={
                "market": condition_id, "limit": limit, "offset": offset
            }, timeout=10)
            if resp.status_code != 200 or not resp.json():
                break
            data = resp.json()
            trades.extend(data)
            print(".", end="", flush=True)
            if len(data) < limit or offset > 5000:
                break
            offset += limit
        except:
            break
    
    print(f" ✅ ({len(trades)} 筆)")
    
    if len(trades) < 50:
        print("\n⚠️  交易量太少，無法進行分析")
        return {"error": "市場交易量太少"}
    
    # Step 3: Get price history and detect spikes
    print(f"\n📊 分析價格歷史...", end="", flush=True)
    price_spikes = []
    
    if clob_token_id:
        prices = get_historical_price_for_insider(clob_token_id, 14)
        
        if prices:
            # Detect spikes (>threshold% change between consecutive days)
            sorted_days = sorted(prices.keys())
            for i in range(1, len(sorted_days)):
                day1, day2 = sorted_days[i-1], sorted_days[i]
                p1, p2 = prices[day1], prices[day2]
                
                if p1 > 0:
                    # Calculate both relative and absolute changes
                    relative_change = ((p2 - p1) / p1) * 100
                    absolute_change = abs(p2 - p1) * 100  # in percentage points
                    
                    # Smart threshold: use absolute change for extreme probabilities
                    is_extreme_prob = (p1 < 0.05 or p1 > 0.95 or p2 < 0.05 or p2 > 0.95)
                    
                    is_spike = False
                    if is_extreme_prob:
                        # For extreme probabilities (<5% or >95%), use absolute threshold
                        # Require at least 2 percentage points change
                        if absolute_change >= 2.0:
                            is_spike = True
                    else:
                        # For normal probabilities, use relative threshold
                        if abs(relative_change) >= price_threshold:
                            is_spike = True
                    
                    if is_spike:
                        spike_date = datetime.now() - timedelta(days=day2)
                        price_spikes.append({
                            "days_ago": day2,
                            "date": spike_date.strftime("%Y-%m-%d"),
                            "from_price": round(p1 * 100, 2),
                            "to_price": round(p2 * 100, 2),
                            "change": round(relative_change, 2),
                            "absolute_change": round(absolute_change, 2),
                            "direction": "UP" if relative_change > 0 else "DOWN",
                            "is_extreme": is_extreme_prob
                        })
        print(f" ✅ (發現 {len(price_spikes)} 個價格突變)")
    else:
        print(" ⚠️  無法獲取價格歷史")
    
    # Step 4: Find large trades
    print(f"\n💰 分析大額交易...", end="", flush=True)
    large_trades = []
    
    for trade in trades:
        size = float(trade.get('usdcSize', 0) or trade.get('size', 0) or 0)
        if size >= trade_threshold:
            ts = trade.get('timestamp', 0)
            trade_date = datetime.fromtimestamp(ts) if ts else None
            
            large_trades.append({
                "wallet": trade.get('proxyWallet', '?')[:12] + "...",
                "full_wallet": trade.get('proxyWallet', '?'),
                "size": round(size, 2),
                "side": trade.get('side', '?'),
                "outcome": trade.get('outcome', '?'),
                "timestamp": trade_date.strftime("%Y-%m-%d %H:%M") if trade_date else "?",
                "days_ago": (datetime.now() - trade_date).days if trade_date else 999
            })
    
    print(f" ✅ (發現 {len(large_trades)} 筆大額交易)")
    
    # Step 5: Correlate spikes with large trades
    print(f"\n🔍 關聯分析...", end="", flush=True)
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
    
    print(f" ✅ (發現 {len(suspicious_events)} 個可疑事件)")
    
    # Step 6: Calculate risk score
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
    
    # Wallet concentration check
    wallet_volumes = {}
    for t in large_trades:
        wallet = t['full_wallet']
        wallet_volumes[wallet] = wallet_volumes.get(wallet, 0) + t['size']
    
    if wallet_volumes:
        top_wallet_volume = max(wallet_volumes.values())
        total_large_volume = sum(wallet_volumes.values())
        concentration = (top_wallet_volume / total_large_volume * 100) if total_large_volume > 0 else 0
        
        if concentration > 50:
            risk_score += 10
            risk_reasons.append(f"單一錢包集中度高 ({concentration:.0f}%)")
    
    risk_level = "CRITICAL" if risk_score >= 60 else "HIGH" if risk_score >= 40 else "MEDIUM" if risk_score >= 20 else "LOW"
    
    # Print summary
    print("\n" + "="*80)
    
    risk_emoji = "🚨" if risk_level == "CRITICAL" else "⚠️" if risk_level == "HIGH" else "⚡" if risk_level == "MEDIUM" else "✅"
    
    print(f"\n{risk_emoji} INSIDER RISK: {risk_level} (評分: {risk_score}/100)")
    print("="*80)
    
    if risk_reasons:
        print("\n📋 風險因素:")
        for reason in risk_reasons:
            print(f"   • {reason}")
    
    if suspicious_events:
        print(f"\n🕵️  可疑事件 (Top 5):")
        for i, event in enumerate(suspicious_events[:5], 1):
            print(f"\n   {i}. {event['date']} - {event['severity']} 嚴重性")
            print(f"      價格變化: {event['price_change']}")
            print(f"      相關交易: {event['related_trades']} 筆 (總額 ${event['total_volume']:,.0f})")
            
            if event['trades']:
                print(f"      大額交易:")
                for t in event['trades'][:3]:
                    print(f"         - {t['wallet']}: ${t['size']:,.0f} {t['side']} {t['outcome']} @ {t['timestamp']}")
    
    if large_trades:
        print(f"\n💰 最大額交易 (Top 10):")
        sorted_trades = sorted(large_trades, key=lambda x: x['size'], reverse=True)
        for i, t in enumerate(sorted_trades[:10], 1):
            print(f"   {i}. ${t['size']:,.0f} - {t['full_wallet']} {t['side']} {t['outcome']} @ {t['timestamp']}")
    
    print("\n" + "="*80)
    
    if risk_level in ["CRITICAL", "HIGH"]:
        print("\n⚠️  警告: 此市場存在異常交易模式，可能有內幕交易風險！")
        print("   建議: 謹慎參與，密切關注價格變化和大額交易動向。")
    elif risk_level == "MEDIUM":
        print("\n⚡ 提示: 發現一些異常交易活動，建議保持警惕。")
    else:
        print("\n✅ 此市場暫未發現明顯的異常交易模式。")
    
    print("="*80 + "\n")
    
    return {
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
        },
        "total_trades_analyzed": len(trades)
    }


# =============================================================================
# Trading Signal Functions
# =============================================================================

def generate_signal(condition_id: str):
    """
    生成交易信號
    
    綜合分析後給出建議
    """
    print(f"\n🎯 交易信號分析: {condition_id[:30]}...")
    print("="*80)
    
    signals = {
        "whale_signal": None,
        "momentum_signal": None,
        "volume_signal": None,
        "overall": None
    }
    
    # 1. Whale analysis (using /holders API)
    print("\n1️⃣ 鯨魚分析...")
    whale_result = analyze_whales(condition_id, min_value=5000)
    
    if whale_result:
        signals['whale_signal'] = whale_result.get('signal', 'NEUTRAL')
        yes_val = whale_result.get('yes_value', 0)
        no_val = whale_result.get('no_value', 0)
        print(f"   🐋 鯨魚信號: {signals['whale_signal']} (Yes: ${yes_val:,.0f} vs No: ${no_val:,.0f})")
    else:
        print("   ⚠️ 無法獲取鯨魚數據")
        signals['whale_signal'] = "NEUTRAL"
    
    # 2. Momentum analysis
    print("\n2️⃣ 動能分析...")
    history = get_historical_prices(condition_id, days=7)
    
    if history and isinstance(history, dict):
        prices = history.get('history', [])
        if len(prices) >= 2:
            first = float(prices[0].get('p', 0.5))
            last = float(prices[-1].get('p', 0.5))
            change = (last - first) / first * 100
            
            if change > 10:
                signals['momentum_signal'] = "YES"
                print(f"   📈 強勢上漲 +{change:.1f}%")
            elif change < -10:
                signals['momentum_signal'] = "NO"
                print(f"   📉 強勢下跌 {change:.1f}%")
            else:
                signals['momentum_signal'] = "NEUTRAL"
                print(f"   ➡️ 橫盤整理 {change:+.1f}%")
        else:
            print("   ⚠️ 價格歷史數據不足")
            signals['momentum_signal'] = "NEUTRAL"
    else:
        print("   ⚠️ 無法獲取價格歷史")
        signals['momentum_signal'] = "NEUTRAL"
    
    # 3. Recent trades analysis
    print("\n3️⃣ 交易流分析...")
    trades = get_trades(condition_id, limit=100)
    
    if trades:
        recent_buys = sum(1 for t in trades[:20] if t.get('side') == 'BUY')
        
        if recent_buys >= 14:
            signals['volume_signal'] = "YES"
            print(f"   💹 近期買盤強勁 ({recent_buys}/20 買入)")
        elif recent_buys <= 6:
            signals['volume_signal'] = "NO"
            print(f"   💹 近期賣壓沉重 ({recent_buys}/20 買入)")
        else:
            signals['volume_signal'] = "NEUTRAL"
            print(f"   💹 買賣平衡 ({recent_buys}/20 買入)")
    else:
        print("   ⚠️ 無法獲取交易記錄")
        signals['volume_signal'] = "NEUTRAL"
    
    # Overall signal
    print("\n" + "="*80)
    
    yes_votes = sum(1 for s in signals.values() if s == "YES")
    no_votes = sum(1 for s in signals.values() if s == "NO")
    
    if yes_votes >= 2:
        signals['overall'] = "BUY YES"
        print(f"\n🎯 綜合信號: 🟢 BUY YES ({yes_votes}/3 指標看多)")
    elif no_votes >= 2:
        signals['overall'] = "BUY NO"
        print(f"\n🎯 綜合信號: 🔴 BUY NO ({no_votes}/3 指標看空)")
    else:
        signals['overall'] = "NEUTRAL"
        print(f"\n🎯 綜合信號: ⚪ 觀望 (指標分歧)")
    
    print("\n⚠️ 風險提示: 以上信號僅供參考，唔構成投資建議!")
    print("="*80 + "\n")
    
    return signals


# =============================================================================
# Main Entry
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Analyzer - 統一市場分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法範例:
  python analyze.py market <ID>                      # 市場深度分析
  python analyze.py whales <ID>                      # 鯨魚分析
  python analyze.py whales <ID> --min-value 10000    # 鯨魚門檻 $10k
  python analyze.py wallet <address>                 # 錢包起底
  python analyze.py distribution <ID>                # 持倉分佈分析
  python analyze.py insider <ID>                     # Insider 活動偵測
  python analyze.py insider <ID> -p 15 -t 10000      # 自訂偵測門檻
  python analyze.py odds "trump"                     # 賠率分析
  python analyze.py kelly <ID> -e 0.6 -b 100         # Kelly 計算
  python analyze.py signal <ID>                      # 交易信號
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Market analysis
    market_parser = subparsers.add_parser("market", help="市場深度分析")
    market_parser.add_argument("condition_id", help="市場 Condition ID")
    market_parser.add_argument("--json", action="store_true", help="JSON 輸出")
    
    # Whale analysis
    whale_parser = subparsers.add_parser("whales", help="鯨魚分析")
    whale_parser.add_argument("condition_id", help="市場 Condition ID")
    whale_parser.add_argument("--min-value", type=float, default=5000, help="鯨魚門檻")
    
    # Wallet analysis
    wallet_parser = subparsers.add_parser("wallet", help="錢包起底")
    wallet_parser.add_argument("address", help="錢包地址")
    wallet_parser.add_argument("--max-trades", type=int, default=500, help="最多載入交易數")
    
    # Odds analysis (calls analyze_odds.py)
    odds_parser = subparsers.add_parser("odds", help="賠率分析 (歷史回顧)")
    odds_parser.add_argument("event", nargs="?", help="Event slug 或關鍵字")
    odds_parser.add_argument("--market", "-m", help="單一市場 Condition ID")
    odds_parser.add_argument("--lookback", "-l", default="7,14,30", help="回顧期間 (e.g. 7,14,30)")
    odds_parser.add_argument("--alert", action="store_true", help="只輸出警報 JSON")
    odds_parser.add_argument("--alert-threshold", type=float, default=10.0, help="警報門檻 (percent)")
    odds_parser.add_argument("--output", "-o", help="導出 Markdown 報告路徑")
    
    # Kelly calculation
    kelly_parser = subparsers.add_parser("kelly", help="Kelly 倉位計算")
    kelly_parser.add_argument("condition_id", help="市場 Condition ID")
    kelly_parser.add_argument("--estimate", "-e", type=float, required=True, help="估計機率 (0-1)")
    kelly_parser.add_argument("--bankroll", "-b", type=float, help="總資金")
    kelly_parser.add_argument("--fraction", "-f", type=float, default=0.5, help="Kelly 分數")
    kelly_parser.add_argument("--outcome", "-o", default="Yes", help="Outcome")
    
    # Signal
    signal_parser = subparsers.add_parser("signal", help="交易信號")
    signal_parser.add_argument("condition_id", help="市場 Condition ID")
    
    # Distribution analysis
    distribution_parser = subparsers.add_parser("distribution", help="市場分佈分析 (Smart Money vs Losers)")
    distribution_parser.add_argument("condition_id", help="市場 Condition ID")
    
    # Insider detection
    insider_parser = subparsers.add_parser("insider", help="內幕交易偵測 (價格突變 + 大額交易)")
    insider_parser.add_argument("condition_id", help="市場 Condition ID")
    insider_parser.add_argument("--price-threshold", "-p", type=float, default=10.0, 
                               help="價格變化門檻 (percent, 預設: 10)")
    insider_parser.add_argument("--trade-threshold", "-t", type=float, default=5000, 
                               help="大額交易門檻 (USD, 預設: 5000)")
    
    # Holders analysis (Goldsky Subgraph - NO 20 holder limit!)
    holders_parser = subparsers.add_parser("holders", help="完整持倉分佈 (Goldsky Subgraph, 無 20 人限制)")
    holders_parser.add_argument("condition_id", help="市場 Condition ID")
    holders_parser.add_argument("--top", "-n", type=int, default=30, help="顯示 Top N 持倉者 (預設: 30)")
    holders_parser.add_argument("--min-balance", "-m", type=float, default=1, help="最低持倉量過濾 (預設: 1)")
    holders_parser.add_argument("--ratio", action="store_true", help="只顯示 Yes/No 比例")

    
    args = parser.parse_args()
    
    if args.command == "market":
        analyze_market(args.condition_id, json_output=args.json)
    elif args.command == "whales":
        analyze_whales(args.condition_id, min_value=args.min_value)
    elif args.command == "wallet":
        analyze_wallet(args.address, max_trades=args.max_trades)
    elif args.command == "odds":
        # Call analyze_odds.py with all arguments
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(script_dir, "analyze_odds.py")]
        
        if args.market:
            cmd.extend(["--market", args.market])
        elif args.event:
            cmd.append(args.event)
        else:
            print("❌ 請提供 event slug 或 --market <ID>")
            sys.exit(1)
        
        if args.lookback:
            cmd.extend(["--lookback", args.lookback])
        if args.alert:
            cmd.append("--alert")
            cmd.extend(["--alert-threshold", str(args.alert_threshold)])
        if args.output:
            cmd.extend(["--output", args.output])
        
        subprocess.run(cmd)
    elif args.command == "kelly":
        calculate_kelly(
            args.condition_id, args.estimate,
            bankroll=args.bankroll, fraction=args.fraction, outcome=args.outcome
        )
    elif args.command == "signal":
        generate_signal(args.condition_id)
    elif args.command == "distribution":
        analyze_distribution(args.condition_id)
    elif args.command == "insider":
        detect_insider_activity(
            args.condition_id,
            price_threshold=args.price_threshold,
            trade_threshold=args.trade_threshold
        )
    elif args.command == "holders":
        analyze_holders(
            args.condition_id,
            top=args.top,
            min_balance=args.min_balance,
            ratio_only=args.ratio
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
