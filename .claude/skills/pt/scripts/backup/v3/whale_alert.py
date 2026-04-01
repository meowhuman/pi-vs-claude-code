#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Polymarket Whale Alert System
Monitors top wallets for new activity using Polymarket API.
Sends Mac desktop notifications.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / '.env')

# Polymarket Data API
DATA_API = "https://data-api.polymarket.com"

# State file to track last seen trades
STATE_FILE = Path(__file__).parent / '.whale_alert_state.json'

# Minimum trade value to track (USD)
MIN_TRADE_VALUE = 500

def send_notification(title: str, message: str):
    """Send Mac desktop notification."""
    message = message.replace('"', '\\"').replace("'", "\\'")
    title = title.replace('"', '\\"').replace("'", "\\'")

    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "{title}" sound name "Glass"'
    ], capture_output=True)

def load_state() -> dict:
    """Load last seen state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'last_check': None, 'seen_txs': [], 'whale_wallets': {}}

def save_state(state: dict):
    """Save state to file."""
    STATE_FILE.write_text(json.dumps(state, indent=2))

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

    state = load_state()
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
            # Group by wallet
            wallet_activity = defaultdict(lambda: {'count': 0, 'total': 0, 'markets': []})

            for trade in new_large_trades:
                wallet = trade['wallet'][:10] + '...' + trade['wallet'][-4:]
                wallet_activity[wallet]['count'] += 1
                wallet_activity[wallet]['total'] += trade['value']
                if trade['title'] not in wallet_activity[wallet]['markets']:
                    wallet_activity[wallet]['markets'].append(trade['title'][:30])

            # Build notification
            sorted_activity = sorted(
                wallet_activity.items(),
                key=lambda x: x[1]['total'],
                reverse=True
            )[:3]

            summary_parts = []
            for wallet, data in sorted_activity:
                summary_parts.append(f"{wallet}: ${data['total']:,.0f}")

            message = " | ".join(summary_parts)

            send_notification(
                "🐋 Polymarket Whale Alert",
                f"{len(new_large_trades)} large trades! {message}"
            )

            print(f"Found {len(new_large_trades)} new large trades (>=${MIN_TRADE_VALUE}):")
            for trade in new_large_trades[:5]:
                wallet_short = trade['wallet'][:10] + '...'
                ts = datetime.fromtimestamp(trade['timestamp']).strftime('%H:%M:%S')
                print(f"  - [{ts}] {wallet_short} {trade['side']} ${trade['value']:,.2f} on {trade['title'][:40]}")
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
        save_state(state)

        if analysis['whale_wallets'] and len(analysis['whale_wallets']) > 0:
            top_wallet = analysis['whale_wallets'][0][0]
            top_volume = analysis['whale_wallets'][0][1]['total_volume']
            print(f"Top whale this session: {top_wallet[:16]}... (${top_volume:,.2f})")
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
