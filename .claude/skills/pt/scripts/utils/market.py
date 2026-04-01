#!/usr/bin/env python3
"""
Polymarket Market - Shared market data functions
"""

import os
import json
import requests
from .client import get_api_urls, get_client


def get_market_info(condition_id: str) -> dict:
    """
    獲取市場詳情
    
    優先從緩存讀取數據（volume 等），再從 API 獲取實時數據
    
    Args:
        condition_id: 市場 Condition ID
    
    Returns:
        Market info dict
    """
    urls = get_api_urls()
    
    # Try to load from cache first (for volume data)
    cache_data = None
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
    cache_files = [
        os.path.join(cache_dir, 'all_markets_cache_active.json'),
        os.path.join(cache_dir, 'all_markets_cache_closed.json')
    ]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                    markets = cache.get('markets', [])
                    for m in markets:
                        if m.get('conditionId') == condition_id:
                            cache_data = m
                            break
                if cache_data:
                    break
            except:
                pass
    
    try:
        # Try Gamma API (better for links/slugs)
        resp = requests.get(
            f"{urls['gamma']}/markets", 
            params={"conditionId": condition_id}, 
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            api_data = None
            if isinstance(data, list):
                for m in data:
                    if m.get('conditionId') == condition_id:
                        api_data = m
                        break
            elif isinstance(data, dict) and data.get('conditionId') == condition_id:
                api_data = data
            
            # Merge cache data (prioritize cache for volume)
            if api_data and cache_data:
                # Use volume from cache if available
                if cache_data.get('volume') or cache_data.get('volumeNum'):
                    api_data['volume'] = cache_data.get('volume', cache_data.get('volumeNum', 0))
                    api_data['volumeNum'] = cache_data.get('volumeNum', cache_data.get('volume', 0))
                return api_data
            elif api_data:
                return api_data
            elif cache_data:
                return cache_data

        # Fallback to CLOB Client
        try:
            client = get_client(with_creds=False)
            market = client.get_market(condition_id)
            if market and market.get('question'):
                # Merge with cache data if available
                if cache_data:
                    if cache_data.get('volume') or cache_data.get('volumeNum'):
                        market['volume'] = cache_data.get('volume', cache_data.get('volumeNum', 0))
                        market['volumeNum'] = cache_data.get('volumeNum', cache_data.get('volume', 0))
                return market
        except:
            pass
        
        # Return cache data if nothing else works
        if cache_data:
            return cache_data
        
        return {}
    except Exception as e:
        print(f"⚠️ get_market_info error: {e}")
        # Return cache data on error
        if cache_data:
            return cache_data
        return {}


def get_token_id(condition_id: str, outcome: str) -> str:
    """
    獲取 Token ID
    
    Args:
        condition_id: 市場 Condition ID
        outcome: Yes/No
    
    Returns:
        Token ID string
    """
    try:
        client = get_client(with_creds=False)
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        for t in tokens:
            if t['outcome'].lower() == outcome.lower():
                return t['token_id']
        
        return None
    except Exception as e:
        print(f"❌ 無法獲取 Token ID: {e}")
        return None


def get_orderbook(condition_id: str, outcome: str) -> dict:
    """
    從 CLOB API 獲取 orderbook
    
    Args:
        condition_id: 市場 Condition ID
        outcome: Yes/No
    
    Returns:
        Dict with best_bid, best_ask, spread, etc.
    """
    try:
        client = get_client(with_creds=False)
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        token_id = None
        for t in tokens:
            if t['outcome'].lower() == outcome.lower():
                token_id = t['token_id']
                break
        
        if not token_id:
            return {"error": f"找不到 {outcome} outcome"}
        
        ob = client.get_order_book(token_id)
        
        best_bid = float(ob.bids[0].price) if ob.bids else 0
        best_ask = float(ob.asks[0].price) if ob.asks else 0
        bid_size = float(ob.bids[0].size) if ob.bids else 0
        ask_size = float(ob.asks[0].size) if ob.asks else 0
        
        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "spread": round(best_ask - best_bid, 4) if best_ask and best_bid else None,
            "spread_pct": round((best_ask - best_bid) / best_ask * 100, 1) if best_ask and best_bid else None
        }
    except Exception as e:
        return {"error": str(e)}


def search_markets_by_query(query: str, limit: int = 10) -> list:
    """
    搜尋市場 (使用 Gamma API)
    
    Args:
        query: 搜尋關鍵字
        limit: 結果數量
    
    Returns:
        List of markets
    """
    urls = get_api_urls()
    
    try:
        resp = requests.get(
            f"{urls['gamma']}/public-search",
            params={"query": query, "limit": limit},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get('markets', []) if isinstance(data, dict) else data
        return []
    except Exception as e:
        print(f"❌ 搜尋錯誤: {e}")
        return []


def get_market_prices(condition_id: str) -> dict:
    """
    獲取市場目前價格
    
    Args:
        condition_id: 市場 Condition ID
    
    Returns:
        Dict with Yes/No prices
    """
    try:
        client = get_client(with_creds=False)
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        prices = {}
        for t in tokens:
            outcome = t['outcome']
            token_id = t['token_id']
            
            ob = client.get_order_book(token_id)
            
            if ob.bids:
                prices[outcome] = {
                    "bid": float(ob.bids[0].price),
                    "ask": float(ob.asks[0].price) if ob.asks else None
                }
            else:
                prices[outcome] = {"bid": None, "ask": None}
        
        return prices
    except Exception as e:
        return {"error": str(e)}
