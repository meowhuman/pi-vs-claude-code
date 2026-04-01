#!/usr/bin/env python3
"""
Polymarket Positions - Shared position functions
"""

import os
import sys
import requests
from dotenv import load_dotenv
from .client import get_api_urls, get_wallets

load_dotenv()


def get_wallet_positions(wallet_address: str) -> list:
    """
    獲取錢包所有持倉
    
    Args:
        wallet_address: 錢包地址
    
    Returns:
        List of positions with size > 0.001
    """
    urls = get_api_urls()
    
    try:
        resp = requests.get(
            f"{urls['data']}/positions", 
            params={"user": wallet_address}, 
            timeout=15
        )
        if resp.status_code == 200:
            positions = resp.json()
            return [p for p in positions if float(p.get("size", p.get("shares", 0))) > 0.001]
        return []
    except Exception as e:
        print(f"❌ API 錯誤: {e}", file=sys.stderr)
        return []


def get_all_positions() -> list:
    """
    獲取所有錢包嘅持倉 (Control + Builder)
    
    Returns:
        List of positions with wallet type label
    """
    wallets = get_wallets()
    all_positions = []
    
    for wallet_type, wallet_addr in wallets.items():
        if not wallet_addr:
            continue
        
        positions = get_wallet_positions(wallet_addr)
        for p in positions:
            p['_wallet_type'] = wallet_type.capitalize()
            p['_wallet'] = wallet_addr
        all_positions.extend(positions)
    
    return all_positions


def get_positions_by_condition(condition_id: str) -> list:
    """
    獲取指定市場嘅所有持倉
    
    Args:
        condition_id: 市場 Condition ID
    
    Returns:
        List of positions for this market
    """
    all_pos = get_all_positions()
    result = []
    
    for p in all_pos:
        p_cid = p.get("conditionId", "") or (p.get("market", {}) or {}).get("conditionId", "")
        if p_cid == condition_id:
            result.append(p)
    
    return result


def parse_position(pos: dict) -> dict:
    """
    解析持倉數據為統一格式
    
    Args:
        pos: Raw position from API
    
    Returns:
        Parsed position dict
    """
    market_info = pos.get("market", {})
    if isinstance(market_info, dict):
        market_name = market_info.get("question", pos.get("title", "Unknown"))
        condition_id = market_info.get("conditionId", pos.get("conditionId", "?"))
    else:
        market_name = pos.get("title", "Unknown")
        condition_id = pos.get("conditionId", "?")
    
    outcome = pos.get("outcome", pos.get("side", "?"))
    shares = float(pos.get("size", pos.get("shares", 0)))
    avg_price = float(pos.get("avgPrice", pos.get("avg_price", 0)))
    cur_price = float(pos.get("curPrice", pos.get("current_price", 0)))
    
    cost = shares * avg_price
    value = shares * cur_price
    pnl = value - cost
    pnl_pct = (pnl / cost * 100) if cost > 0 else 0
    
    return {
        "market_name": market_name[:60] + "..." if len(market_name) > 60 else market_name,
        "market_name_full": market_name,
        "condition_id": condition_id,
        "outcome": outcome,
        "shares": round(shares, 2),
        "avg_price": round(avg_price, 4),
        "current_price": round(cur_price, 4),
        "cost": round(cost, 2),
        "value": round(value, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 1),
        "wallet_type": pos.get('_wallet_type', '?'),
        "slug": pos.get("slug", market_info.get("slug", "")),
        "event_slug": pos.get("eventSlug", (pos.get("event", {}) or {}).get("slug", ""))
    }
