#!/usr/bin/env python3
"""
Polymarket Holder Tracker
Tracks top holders in high-volume markets and alerts on position changes.
Focuses on Smart Money, Whales, and Losers only.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import requests
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.whale_utils import (
    send_notification,
    load_state,
    save_state,
    classify_wallet,
    should_alert,
    format_wallet_short,
    build_notification_message,
    print_classification,
    print_filtered_message,
    ALERT_ROLES
)

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

# APIs
DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

# State file to track holders
STATE_FILE = Path(__file__).parent.parent / 'state' / 'holder_tracker_state.json'

# Minimum market volume to track (USD)
MIN_MARKET_VOLUME =  100000  # Only track markets with >$100k volume

# Minimum position value to track (USD)
MIN_POSITION_VALUE = 1000  # Lowered for testing, can increase to 5000 later


def load_markets_from_cache() -> list:
    """Load markets from search.py cache."""
    cache_file = Path(__file__).parent.parent / 'cache' / 'all_markets_cache_active.json'
    
    if not cache_file.exists():
        print("   ⚠️ 緩存不存在，請先運行 search.py 建立緩存")
        return []
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
            markets = data.get('markets', [])
            
            # Filter by minimum volume and sort by volume
            filtered = [
                m for m in markets
                if float(m.get('volumeNum', m.get('volume', 0)) or 0) >= MIN_MARKET_VOLUME
            ]
            
            # Sort by volume descending
            filtered.sort(key=lambda x: float(x.get('volumeNum', x.get('volume', 0)) or 0), reverse=True)
            
            return filtered
    except Exception as e:
        print(f"   ⚠️ 讀取緩存失敗: {e}")
        return []


def get_top_markets(limit: int = 100) -> list:
    """Get top markets by volume from cache."""
    markets = load_markets_from_cache()
    return markets[:limit] if markets else []


def get_market_holders(condition_id: str) -> list:
    """Get holders for a specific market."""
    try:
        resp = requests.get(
            f"{DATA_API}/holders",
            params={"market": condition_id, "limit": 1000},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Parse holders from both tokens
            all_holders = []
            if isinstance(data, list):
                for token_data in data:
                    holders = token_data.get('holders', [])
                    outcome_index = token_data.get('outcomeIndex', 0)
                    
                    for h in holders:
                        wallet = h.get('proxyWallet', '')
                        if not wallet:
                            continue
                        
                        all_holders.append({
                            'wallet': wallet,
                            'name': h.get('name', h.get('pseudonym', '')),
                            'amount': float(h.get('amount', 0)),
                            'outcomeIndex': outcome_index
                        })
            
            return all_holders
        return []
    except Exception as e:
        print(f"   ⚠️ Error fetching holders: {e}")
        return []

def track_holders():
    """Main tracking function."""
    print(f"🔍 Holder Tracker - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    state = load_state(STATE_FILE)
    if not state:
        state = {
            'last_check': None,
            'tracked_markets': {},
            'tracked_wallets': {}
        }
    previous_holders = state.get('tracked_wallets', {})
    
    # Get top markets
    print(f"\n📊 從緩存載入市場 (min volume: ${MIN_MARKET_VOLUME:,})...")
    markets = get_top_markets(100)  # Get top 100
    
    if not markets:
        print("❌ 無市場數據")
        return
    
    print(f"✅ 找到 {len(markets)} 個高成交量市場")
    
    # Track new holders
    current_holders = {}
    new_positions = []
    
    scan_limit = min(50, len(markets))  # Scan top 50
    print(f"📡 開始掃描前 {scan_limit} 個市場...\n")
    
    for i, market in enumerate(markets[:scan_limit], 1):
        condition_id = market.get('conditionId', market.get('id'))
        title = market.get('question', 'Unknown')[:50]
        volume = float(market.get('volumeNum', 0) or 0)
        
        print(f"\n[{i}/20] {title}... (${volume:,.0f})")
        
        # Get holders
        holders = get_market_holders(condition_id)
        
        if not holders:
            print(f"  ⚠️ No holders data")
            continue
        
        # Process each holder
        for holder in holders[:20]:  # Top 20 holders per market
            wallet = holder.get('wallet', '')
            if not wallet:
                continue
            
            # Get position value (amount is already in USD value)
            position_value = holder.get('amount', 0)
            
            if position_value < MIN_POSITION_VALUE:
                continue
            
            # Classify using shared function
            classification = classify_wallet(wallet, position_value, trade_count=1)
            role = classification['role']
            
            # Only track alert-worthy roles
            if role not in ALERT_ROLES:
                continue
            
            # Check if this is a new position
            wallet_key = f"{wallet}_{condition_id}"
            
            if wallet_key not in previous_holders:
                new_positions.append({
                    'wallet': wallet,
                    'market': title,
                    'condition_id': condition_id,
                    'value': position_value,
                    'classification': classification,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                emoji = classification['emoji']
                wallet_short = wallet[:10] + '...' + wallet[-4:]
                print(f"  🆕 {emoji} {wallet_short}: ${position_value:,.0f} ({role})")
            
            # Update current state
            current_holders[wallet_key] = {
                'wallet': wallet,
                'market': title,
                'value': position_value,
                'role': role,
                'last_seen': datetime.now(timezone.utc).isoformat()
            }
    
    # Send notifications for new positions
    if new_positions:
        print(f"\n📢 發現 {len(new_positions)} 個新倉位！")
        
        # Group by role
        by_role = defaultdict(list)
        for pos in new_positions:
            role = pos['classification']['role']
            by_role[role].append(pos)
        
        # Build notification message
        summary_parts = []
        for role in ['SMART_MONEY', 'WHALE', 'LOSER']:
            if role in by_role:
                count = len(by_role[role])
                total_value = sum(p['value'] for p in by_role[role])
                emoji = by_role[role][0]['classification']['emoji']
                summary_parts.append(f"{emoji} {count} {role}: ${total_value:,.0f}")
        
        message = " | ".join(summary_parts)
        
        send_notification(
            "🐋 Polymarket Holder Alert",
            f"{len(new_positions)} new positions! {message}"
        )
        
        # Print details
        for pos in new_positions[:5]:
            emoji = pos['classification']['emoji']
            wallet_short = pos['wallet'][:10] + '...'
            print(f"  • {emoji} {wallet_short} opened ${pos['value']:,.0f} on {pos['market']}")
    else:
        print(f"\n✅ 無新倉位（追蹤中: {len(current_holders)} 個倉位）")
    
    # Update state
    state['last_check'] = datetime.now(timezone.utc).isoformat()
    state['tracked_wallets'] = current_holders
    state['tracked_markets'] = {
        m.get('conditionId', m.get('id')): {
            'title': m.get('question', '')[:50],
            'volume': float(m.get('volumeNum', 0) or 0)
        }
        for m in markets[:20]
    }
    save_state(STATE_FILE, state)
    
    print(f"\n💾 狀態已保存: {len(current_holders)} 個追蹤中的倉位")
    print("=" * 70)


def main():
    try:
        track_holders()
    except Exception as e:
        print(f"❌ Error: {e}")
        send_notification("⚠️ Holder Tracker Error", str(e)[:80])


if __name__ == "__main__":
    main()
