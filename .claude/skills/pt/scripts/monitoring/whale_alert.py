#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Polymarket Whale Alert System v2.0
Monitors top wallets for new activity using Polymarket API.
Filters by trader role: Smart Money, Whale winners, Whale losers.
Excludes Market Makers and Retailers.
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

# Polymarket Data API
DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# State file to track last seen trades
STATE_FILE = Path(__file__).parent.parent / 'state' / 'whale_alert_state.json'

# Minimum trade value to track (USD)
MIN_TRADE_VALUE = 2000  # Increased from 500 to filter small retail trades


def get_recent_large_trades(limit: int = 500) -> list:
    """Get recent large trades across all markets."""
    # Get trades from multiple active markets
    resp = requests.get(
        f"{DATA_API}/trades",
        params={"limit": limit}
    )

    if resp.status_code != 200:
        raise Exception(f"Failed to get trades: {resp.status_code}")

    return resp.json()


def get_gamma_markets(active: bool = True, limit: int = 20) -> list:
    """Get active markets from Gamma API."""
    resp = requests.get(
        "https://gamma-api.polymarket.com/markets",
        params={"active": active, "limit": limit, "order": "volume", "ascending": False}
    )

    if resp.status_code == 200:
        return resp.json()
    return []


def get_wallet_classification(wallet_address: str, session_volume: float = 0, session_trade_count: int = 0) -> dict:
    """
    Get wallet classification using trader_classification module.
    
    Args:
        wallet_address: Wallet address to classify
        session_volume: Volume from current session
        session_trade_count: Trade count from current session
    
    Returns:
        Classification dict with role, emoji, confidence, reasons
    """
    try:
        # Try to get wallet activity data from CLOB API
        resp = requests.get(
            f"{CLOB_API}/activity",
            params={"user": wallet_address, "limit": 100},
            timeout=5
        )
        
        global_trades = 0
        total_value = session_volume  # Start with session data
        market_pnl = 0  # We can't easily calculate PnL without full position data
        
        if resp.status_code == 200:
            activity = resp.json()
            if isinstance(activity, list):
                global_trades = len(activity)
                # Estimate total value from recent activity
                for trade in activity[:20]:  # Sample recent trades
                    size = float(trade.get('size', 0))
                    price = float(trade.get('price', 0))
                    total_value += size * price
        
        # Use shared classify_wallet function
        return classify_wallet(
            wallet_address,
            volume=total_value,
            trade_count=max(session_trade_count, global_trades),
            pnl=market_pnl
        )
        
    except Exception as e:
        print(f"  ⚠️ Classification failed for {wallet_address[:10]}...: {e}")
        # Return default classification
        return {
            'role': 'REGULAR',
            'emoji': '👤',
            'confidence': 'N/A',
            'reasons': ['Unable to classify']
        }


def analyze_trades(trades: list) -> dict:
    """Analyze trades and identify whale activity."""
    wallet_stats = defaultdict(lambda: {
        'total_volume': 0,
        'trade_count': 0,
        'markets': set(),
        'recent_trades': []
    })

    large_trades = []

    for trade in trades:
        wallet = trade.get('proxyWallet', '')
        if not wallet:
            continue

        size = float(trade.get('size', 0))
        price = float(trade.get('price', 0))
        value = size * price

        wallet_stats[wallet]['total_volume'] += value
        wallet_stats[wallet]['trade_count'] += 1
        wallet_stats[wallet]['markets'].add(trade.get('conditionId', ''))

        if value >= MIN_TRADE_VALUE:
            trade_info = {
                'wallet': wallet,
                'value': value,
                'side': trade.get('side', ''),
                'outcome': trade.get('outcome', ''),
                'title': trade.get('title', ''),
                'timestamp': trade.get('timestamp', 0),
                'tx_hash': trade.get('transactionHash', '')
            }
            large_trades.append(trade_info)
            wallet_stats[wallet]['recent_trades'].append(trade_info)

    # Sort by volume to find whales
    sorted_wallets = sorted(
        wallet_stats.items(),
        key=lambda x: x[1]['total_volume'],
        reverse=True
    )

    return {
        'whale_wallets': sorted_wallets[:20],
        'large_trades': sorted(large_trades, key=lambda x: x['value'], reverse=True)[:20],
        'total_volume': sum(w[1]['total_volume'] for w in sorted_wallets)
    }

def check_active_markets():
    """Check active markets for whale activity."""
    print(f"[{datetime.now()}] Checking whale activity...")

    state = load_state(STATE_FILE)
    if not state:
        state = {'last_check': None, 'seen_txs': [], 'whale_wallets': {}}
    seen_txs = set(state.get('seen_txs', []))

    try:
        # Get recent trades
        trades = get_recent_large_trades(500)

        if not trades:
            print("No trades found")
            return

        # Analyze trades
        analysis = analyze_trades(trades)

        # Find new large trades
        new_large_trades = []
        for trade in analysis['large_trades']:
            tx_hash = trade.get('tx_hash', '')
            if tx_hash and tx_hash not in seen_txs:
                new_large_trades.append(trade)
                seen_txs.add(tx_hash)

        if new_large_trades:
            # Classify wallets and filter by role
            wallet_classifications = {}
            filtered_trades = []
            
            print(f"\n🔍 Classifying {len(new_large_trades)} new large trades...")
            
            for trade in new_large_trades:
                wallet = trade['wallet']
                
                # Get or cache classification
                if wallet not in wallet_classifications:
                    # Get wallet stats from analysis
                    wallet_stats = next(
                        (stats for w, stats in analysis['whale_wallets'] if w == wallet),
                        {'total_volume': trade['value'], 'trade_count': 1}
                    )
                    
                    classification = get_wallet_classification(
                        wallet,
                        session_volume=wallet_stats['total_volume'],
                        session_trade_count=wallet_stats['trade_count']
                    )
                    wallet_classifications[wallet] = classification
                    
                    role = classification['role']
                    emoji = classification['emoji']
                    confidence = classification['confidence']
                    
                    wallet_short = wallet[:10] + '...' + wallet[-4:]
                    print(f"  {emoji} {wallet_short}: {role} ({confidence})")
                
                # Filter: only keep trades from wallets with alert-worthy roles
                classification = wallet_classifications[wallet]
                if classification['role'] in ALERT_ROLES:
                    trade['classification'] = classification
                    filtered_trades.append(trade)
                else:
                    role = classification['role']
                    print(f"    ↳ Skipping {role} (filtered out)")
            
            if filtered_trades:
                # Group by wallet with role info
                wallet_activity = defaultdict(lambda: {
                    'count': 0, 
                    'total': 0, 
                    'markets': [],
                    'classification': None
                })

                for trade in filtered_trades:
                    wallet = trade['wallet'][:10] + '...' + trade['wallet'][-4:]
                    wallet_activity[wallet]['count'] += 1
                    wallet_activity[wallet]['total'] += trade['value']
                    wallet_activity[wallet]['classification'] = trade['classification']
                    if trade['title'] not in wallet_activity[wallet]['markets']:
                        wallet_activity[wallet]['markets'].append(trade['title'][:30])

                # Build notification with role indicators
                sorted_activity = sorted(
                    wallet_activity.items(),
                    key=lambda x: x[1]['total'],
                    reverse=True
                )[:3]

                summary_parts = []
                for wallet, data in sorted_activity:
                    emoji = data['classification']['emoji']
                    role = data['classification']['role']
                    summary_parts.append(f"{emoji} {wallet}: ${data['total']:,.0f}")

                message = " | ".join(summary_parts)

                send_notification(
                    "🐋 Polymarket Whale Alert",
                    f"{len(filtered_trades)} trades! {message}"
                )

                print(f"\n✅ Found {len(filtered_trades)} trades from {len(wallet_activity)} notable wallets:")
                for trade in filtered_trades[:5]:
                    wallet_short = trade['wallet'][:10] + '...'
                    ts = datetime.fromtimestamp(trade['timestamp']).strftime('%H:%M:%S')
                    emoji = trade['classification']['emoji']
                    role = trade['classification']['role']
                    print(f"  - [{ts}] {emoji} {wallet_short} ({role}) {trade['side']} ${trade['value']:,.2f} on {trade['title'][:40]}")
            else:
                print(f"✋ {len(new_large_trades)} trades found but filtered out (Market Makers/Retailers)")
        else:
            print(f"No new large trades (>=${MIN_TRADE_VALUE})")

        # Update whale wallets in state
        whale_wallets = {}
        for wallet, stats in analysis['whale_wallets']:
            whale_wallets[wallet] = {
                'volume': stats['total_volume'],
                'trades': stats['trade_count']
            }

        # Save state
        state['last_check'] = datetime.now(timezone.utc).isoformat()
        state['seen_txs'] = list(seen_txs)[-2000:]  # Keep last 2000
        state['whale_wallets'] = whale_wallets
        save_state(STATE_FILE, state)

        if analysis['whale_wallets'] and len(analysis['whale_wallets']) > 0:
            top_wallet = analysis['whale_wallets'][0][0]
            top_volume = analysis['whale_wallets'][0][1]['total_volume']
            print(f"\nTop whale this session: {top_wallet[:16]}... (${top_volume:,.2f})")
            print(f"🔗 Polygonscan: https://polygonscan.com/address/{top_wallet}")
            print(f"📊 Total session volume: ${analysis['total_volume']:,.2f}")

    except Exception as e:
        error_msg = str(e)[:80]
        print(f"Error: {e}")
        send_notification("⚠️ Whale Alert Error", error_msg)

def main():
    check_active_markets()

if __name__ == "__main__":
    main()
