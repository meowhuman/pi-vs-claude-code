#!/usr/bin/env python3
"""
Goldsky Subgraph Client for Polymarket

Provides access to complete holder data without the 20-holder API limit.
Uses Polymarket's official positions-subgraph hosted on Goldsky.
"""

import requests
from typing import Optional

# Goldsky Subgraph endpoint
GOLDSKY_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"

# Token balance decimals (USDC-based, 6 decimals)
BALANCE_DECIMALS = 6

# =============================================================================
# System Wallet Detection
# =============================================================================

# Known system/reserve wallets (hardcoded)
KNOWN_SYSTEM_WALLETS = {
    '0xa5ef39c3d3e10d0b270233af41cac69796b12966',  # Polymarket Minting Reserve
}

# Threshold for detecting "too large" positions (likely system wallets)
SYSTEM_WALLET_THRESHOLD = 100_000_000  # 100M shares


def is_system_wallet(wallet: str, balance: float = 0, market_volume: float = 0) -> tuple:
    """
    Detect if a wallet is likely a system/reserve wallet.
    
    Heuristics:
    1. Known system wallet addresses
    2. Extremely large positions (>100M shares)
    3. Position exceeds 10x market volume (if provided)
    
    Returns:
        (is_system: bool, reason: str)
    """
    wallet_lower = wallet.lower()
    
    # Heuristic 1: Known system wallets
    if wallet_lower in KNOWN_SYSTEM_WALLETS:
        return True, "Known system wallet"
    
    # Heuristic 2: Extremely large position
    if balance >= SYSTEM_WALLET_THRESHOLD:
        return True, f"Position >{SYSTEM_WALLET_THRESHOLD/1_000_000:.0f}M shares"
    
    # Heuristic 3: Position >> market volume
    if market_volume > 0 and balance > market_volume * 10:
        return True, "Position >10x market volume"
    
    return False, ""


def filter_system_wallets(holders: list, market_volume: float = 0) -> tuple:
    """
    Filter out system wallets from holder list.
    
    Returns:
        (filtered_holders: list, system_wallets: list)
    """
    filtered = []
    system = []
    
    for h in holders:
        is_sys, reason = is_system_wallet(
            h.get('wallet', ''), 
            h.get('balance', 0),
            market_volume
        )
        
        if is_sys:
            h['is_system'] = True
            h['system_reason'] = reason
            system.append(h)
        else:
            h['is_system'] = False
            filtered.append(h)
    
    return filtered, system


def query_subgraph(query: str, variables: Optional[dict] = None) -> dict:
    """Execute a GraphQL query against the Goldsky subgraph."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    resp = requests.post(
        GOLDSKY_URL,
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"}
    )
    resp.raise_for_status()
    return resp.json()


def get_all_holders(
    condition_id: str,
    min_balance: float = 0,
    max_holders: int = 10000
) -> list:
    """
    Get ALL holders for a market using cursor pagination.
    
    Args:
        condition_id: Market condition ID (with or without 0x prefix)
        min_balance: Minimum balance in shares (default: 0)
        max_holders: Maximum holders to fetch (default: 10000)
    
    Returns:
        List of holder dicts with: wallet, balance, outcome (0=Yes, 1=No)
    """
    # Ensure condition_id has 0x prefix and is lowercase
    if not condition_id.startswith("0x"):
        condition_id = "0x" + condition_id
    condition_id = condition_id.lower()
    
    all_holders = []
    last_id = ""
    page_size = 1000  # Subgraph max per query
    
    while len(all_holders) < max_holders:
        # Build query with cursor pagination
        where_clause = f'asset_: {{ condition: "{condition_id}" }}'
        if last_id:
            where_clause = f'id_gt: "{last_id}", {where_clause}'
        
        query = f"""
        {{
            userBalances(
                first: {page_size},
                where: {{ {where_clause} }},
                orderBy: id
            ) {{
                id
                user
                balance
                asset {{
                    outcomeIndex
                }}
            }}
        }}
        """
        
        result = query_subgraph(query)
        balances = result.get("data", {}).get("userBalances", [])
        
        if not balances:
            break
        
        for b in balances:
            balance_raw = int(b.get("balance", 0))
            balance = balance_raw / (10 ** BALANCE_DECIMALS)
            
            # Skip if below minimum
            if balance < min_balance:
                continue
            
            all_holders.append({
                "wallet": b.get("user", ""),
                "balance": balance,
                "balance_raw": balance_raw,
                "outcome": int(b.get("asset", {}).get("outcomeIndex", 0)),
                "id": b.get("id", "")
            })
        
        # Update cursor for next page
        last_id = balances[-1]["id"]
        
        # If we got less than page_size, we've reached the end
        if len(balances) < page_size:
            break
    
    return all_holders[:max_holders]


def get_position_distribution(condition_id: str, min_balance: float = 0) -> dict:
    """
    Get Yes/No position distribution for a market.
    
    Returns:
        {
            "yes": {"total_balance": float, "holder_count": int, "holders": list},
            "no": {"total_balance": float, "holder_count": int, "holders": list},
            "ratio": {"yes_pct": float, "no_pct": float}
        }
    """
    holders = get_all_holders(condition_id, min_balance=min_balance)
    
    yes_holders = [h for h in holders if h["outcome"] == 0]
    no_holders = [h for h in holders if h["outcome"] == 1]
    
    yes_total = sum(h["balance"] for h in yes_holders)
    no_total = sum(h["balance"] for h in no_holders)
    grand_total = yes_total + no_total
    
    return {
        "yes": {
            "total_balance": yes_total,
            "holder_count": len(yes_holders),
            "holders": sorted(yes_holders, key=lambda x: x["balance"], reverse=True)
        },
        "no": {
            "total_balance": no_total,
            "holder_count": len(no_holders),
            "holders": sorted(no_holders, key=lambda x: x["balance"], reverse=True)
        },
        "ratio": {
            "yes_pct": (yes_total / grand_total * 100) if grand_total > 0 else 0,
            "no_pct": (no_total / grand_total * 100) if grand_total > 0 else 0
        },
        "total_holders": len(holders),
        "total_balance": grand_total
    }


def get_holder_count(condition_id: str) -> int:
    """Quick count of holders for a market (uses single query)."""
    if not condition_id.startswith("0x"):
        condition_id = "0x" + condition_id
    condition_id = condition_id.lower()
    
    query = f"""
    {{
        userBalances(
            first: 1000,
            where: {{ asset_: {{ condition: "{condition_id}" }} }},
            orderBy: id
        ) {{
            id
        }}
    }}
    """
    
    result = query_subgraph(query)
    balances = result.get("data", {}).get("userBalances", [])
    
    # If exactly 1000, there might be more
    if len(balances) == 1000:
        return len(get_all_holders(condition_id))
    
    return len(balances)


# Quick test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python subgraph.py <condition_id>")
        print("\nExample: python subgraph.py 0xa95aa8fe6aaaaefefa78d0bcb8eb6541086b294929ae2303af0e673ab00eca07")
        sys.exit(1)
    
    cid = sys.argv[1]
    print(f"🔍 Fetching holders for: {cid[:20]}...")
    
    dist = get_position_distribution(cid, min_balance=1)
    
    print(f"\n📊 Position Distribution")
    print("=" * 50)
    print(f"Total Holders: {dist['total_holders']}")
    print(f"Total Balance: {dist['total_balance']:,.2f} shares")
    print()
    print(f"✅ YES: {dist['yes']['holder_count']} holders | {dist['yes']['total_balance']:,.2f} shares ({dist['ratio']['yes_pct']:.1f}%)")
    print(f"❌ NO:  {dist['no']['holder_count']} holders | {dist['no']['total_balance']:,.2f} shares ({dist['ratio']['no_pct']:.1f}%)")
    
    print(f"\n🐋 Top 10 YES Holders:")
    for i, h in enumerate(dist['yes']['holders'][:10], 1):
        print(f"   {i}. {h['wallet'][:12]}... : {h['balance']:,.2f}")
    
    print(f"\n🐋 Top 10 NO Holders:")
    for i, h in enumerate(dist['no']['holders'][:10], 1):
        print(f"   {i}. {h['wallet'][:12]}... : {h['balance']:,.2f}")
