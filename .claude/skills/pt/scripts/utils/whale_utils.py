#!/usr/bin/env python3
"""
Whale Monitoring Utilities
Shared functions for whale_alert.py and holder_tracker.py
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
import json
from collections import defaultdict

# Add to path for trader_classification
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.trader_classification import classify_trader_role


# Alert roles - only notify these
ALERT_ROLES = {'SMART_MONEY', 'WHALE', 'LOSER'}


def send_notification(title: str, message: str):
    """Send Mac desktop notification."""
    message = message.replace('"', '\\"').replace("'", "\\'")
    title = title.replace('"', '\\"').replace("'", "\\'")

    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "{title}" sound name "Glass"'
    ], capture_output=True)


def load_state(state_file: Path) -> dict:
    """Load state from JSON file."""
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}


def save_state(state_file: Path, state: dict):
    """Save state to JSON file."""
    state_file.write_text(json.dumps(state, indent=2))


def classify_wallet(wallet: str, volume: float, trade_count: int, pnl: float = 0) -> dict:
    """
    Classify a wallet using trader_classification module.
    
    Args:
        wallet: Wallet address
        volume: Trading volume or position value
        trade_count: Number of trades
        pnl: Profit/Loss (optional)
    
    Returns:
        Classification dict with role, emoji, confidence, reasons
    """
    wallet_data = {
        'total_value': volume,
        'market_trades': trade_count,
        'global_trades': max(trade_count * 10, 10),  # Estimate
        'market_pnl': pnl,
        'is_market_maker': False  # Will be determined by classify function
    }
    
    return classify_trader_role(wallet_data)


def should_alert(classification: dict) -> bool:
    """Check if classification warrants an alert."""
    return classification['role'] in ALERT_ROLES


def format_wallet_short(wallet: str) -> str:
    """Format wallet address to short form."""
    return wallet[:10] + '...' + wallet[-4:]


def build_notification_message(activities: list, max_display: int = 3) -> str:
    """
    Build notification message from activities.
    
    Args:
        activities: List of dicts with 'classification', 'wallet', 'value'
        max_display: Max number of activities to display
    
    Returns:
        Formatted message string
    """
    # Group by role
    by_role = defaultdict(list)
    for activity in activities:
        role = activity['classification']['role']
        by_role[role].append(activity)
    
    # Build summary
    summary_parts = []
    for role in ['SMART_MONEY', 'WHALE', 'LOSER']:
        if role in by_role:
            items = by_role[role][:max_display]
            for item in items:
                emoji = item['classification']['emoji']
                wallet_short = format_wallet_short(item['wallet'])
                value = item['value']
                summary_parts.append(f"{emoji} {wallet_short}: ${value:,.0f}")
    
    return " | ".join(summary_parts[:max_display])


def print_classification(wallet: str, classification: dict):
    """Print classification result."""
    emoji = classification['emoji']
    role = classification['role']
    confidence = classification['confidence']
    wallet_short = format_wallet_short(wallet)
    
    print(f"  {emoji} {wallet_short}: {role} ({confidence})")


def print_filtered_message(role: str):
    """Print message for filtered out role."""
    print(f"    ↳ Skipping {role} (filtered out)")
