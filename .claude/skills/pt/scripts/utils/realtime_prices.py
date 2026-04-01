#!/usr/bin/env python3
"""
Polymarket Realtime Prices - 實時價格獲取工具

用於繞過緩存，直接獲取最新嘅市場價格數據。
適用於交易決策前嘅價格確認。
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .client import get_client, get_api_urls


def get_realtime_price(condition_id: str, timeout: int = 10) -> Dict[str, Any]:
    """
    獲取單個市場嘅實時價格
    
    直接從 CLOB API 獲取 orderbook，完全繞過緩存
    如果 orderbook 唔可用，會 fallback 到 market token 價格
    
    Args:
        condition_id: 市場 Condition ID
        timeout: 超時時間 (秒)
    
    Returns:
        Dict with:
        - yes_bid: Yes 最高買價
        - yes_ask: Yes 最低賣價
        - no_bid: No 最高買價
        - no_ask: No 最低賣價
        - yes_mid: Yes 中間價
        - no_mid: No 中間價
        - spread_pct: Spread 百分比
        - fetched_at: 獲取時間
        - source: 'orderbook' or 'token_price'
        - error: 錯誤信息 (如有)
    """
    try:
        client = get_client(with_creds=False)
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        result = {
            'condition_id': condition_id,
            'fetched_at': datetime.now().isoformat(),
            'yes_bid': None,
            'yes_ask': None,
            'no_bid': None,
            'no_ask': None,
            'yes_mid': None,
            'no_mid': None,
            'spread_pct': None,
            'source': None,
            'market_status': 'active',  # or 'resolved'
            'error': None
        }
        
        yes_success = False
        no_error = None
        
        # Check if market is resolved (has a winner)
        for t in tokens:
            if t.get('winner') == True:
                result['market_status'] = 'resolved'
                # Use token prices for resolved markets
                for tok in tokens:
                    if tok['outcome'].lower() == 'yes':
                        result['yes_mid'] = float(tok.get('price', 0))
                    else:
                        result['no_mid'] = float(tok.get('price', 0))
                result['source'] = 'resolved'
                yes_success = True
                break
        
        # Skip orderbook fetch if market is resolved
        if result['market_status'] == 'resolved':
            return result
        
        for t in tokens:
            outcome = t['outcome'].lower()
            token_id = t['token_id']
            token_price = float(t.get('price', 0)) if t.get('price') else None
            
            try:
                ob = client.get_order_book(token_id)
                
                best_bid = float(ob.bids[0].price) if ob.bids else 0
                best_ask = float(ob.asks[0].price) if ob.asks else 1
                
                # Calculate spread percentage
                spread_pct = round((best_ask - best_bid) / best_ask * 100, 2) if best_ask > 0 else 100
                
                # Smart mid-price: prefer token price when spread is too wide (>50%)
                # Wide spreads indicate low liquidity where orderbook mid is unreliable
                if spread_pct > 50 and token_price is not None:
                    mid = token_price
                    source = 'token_price_fallback'
                else:
                    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else token_price
                    source = 'orderbook'
                
                if outcome == 'yes':
                    result['yes_bid'] = best_bid
                    result['yes_ask'] = best_ask
                    result['yes_mid'] = mid
                    result['source'] = source
                    result['raw_spread_pct'] = spread_pct  # Keep raw for debugging
                    yes_success = True
                    
                    # Use actual spread or 2% estimate if using token price
                    result['spread_pct'] = 2.0 if source == 'token_price_fallback' else spread_pct
                else:
                    result['no_bid'] = best_bid
                    result['no_ask'] = best_ask
                    result['no_mid'] = mid
                    
            except Exception as e:
                if outcome == 'yes':
                    # Fallback: Use token price from market data
                    token_price = t.get('price')
                    if token_price:
                        price = float(token_price)
                        result['yes_mid'] = price
                        result['yes_bid'] = price * 0.99  # Estimate
                        result['yes_ask'] = price * 1.01  # Estimate
                        result['source'] = 'token_price'
                        yes_success = True
                    else:
                        result['error'] = f"Yes orderbook error: {str(e)}"
                else:
                    token_price = t.get('price')
                    if token_price:
                        price = float(token_price)
                        result['no_mid'] = price
                    no_error = str(e)
        
        # Only report error if Yes-side failed completely
        if yes_success:
            result['error'] = None
        elif no_error and not result['error']:
            result['error'] = f"No orderbook error: {no_error}"
        
        return result
        
    except Exception as e:
        # Fallback to Gamma API for price data
        try:
            import requests
            urls = get_api_urls()
            resp = requests.get(
                f"{urls['gamma']}/markets",
                params={"conditionId": condition_id},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    market = data[0]
                elif isinstance(data, dict):
                    market = data
                else:
                    market = None
                
                if market:
                    import json as json_mod
                    outcome_prices = market.get('outcomePrices')
                    if outcome_prices:
                        prices = json_mod.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                        if len(prices) >= 2:
                            # Gamma 格式: [Yes_Price, No_Price]
                            yes_price = float(prices[0])
                            no_price = float(prices[1])
                            return {
                                'condition_id': condition_id,
                                'fetched_at': datetime.now().isoformat(),
                                'yes_bid': yes_price * 0.99,
                                'yes_ask': yes_price * 1.01,
                                'yes_mid': yes_price,
                                'no_bid': no_price * 0.99,
                                'no_ask': no_price * 1.01,
                                'no_mid': no_price,
                                'spread_pct': 2.0,  # Estimated
                                'source': 'gamma_api',
                                'error': None
                            }
        except:
            pass
        
        return {
            'condition_id': condition_id,
            'fetched_at': datetime.now().isoformat(),
            'source': None,
            'error': str(e)
        }


def get_realtime_prices_batch(condition_ids: List[str], max_workers: int = 5) -> Dict[str, Dict[str, Any]]:
    """
    批量獲取多個市場嘅實時價格 (並行)
    
    Args:
        condition_ids: 市場 Condition ID 列表
        max_workers: 並行獲取數量 (預設 5，避免 rate limit)
    
    Returns:
        Dict mapping condition_id -> price data
    """
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cid = {
            executor.submit(get_realtime_price, cid): cid 
            for cid in condition_ids
        }
        
        for future in as_completed(future_to_cid):
            cid = future_to_cid[future]
            try:
                results[cid] = future.result()
            except Exception as e:
                results[cid] = {
                    'condition_id': cid,
                    'error': str(e),
                    'fetched_at': datetime.now().isoformat()
                }
            
            # Small delay to avoid rate limiting
            time.sleep(0.05)
    
    return results


def enrich_markets_with_realtime_prices(markets: List[Dict[str, Any]], max_markets: int = 20) -> List[Dict[str, Any]]:
    """
    為市場列表注入實時價格數據
    
    會覆蓋緩存中嘅價格數據，添加 `realtime_` 前綴嘅欄位
    
    Args:
        markets: 市場列表 (來自緩存)
        max_markets: 最多處理幾個市場
    
    Returns:
        帶有實時價格嘅市場列表
    """
    # Limit to avoid too many API calls
    markets_to_process = markets[:max_markets]
    
    # Extract condition IDs
    cids = [m.get('conditionId', m.get('condition_id')) for m in markets_to_process if m.get('conditionId') or m.get('condition_id')]
    
    if not cids:
        return markets
    
    print(f"   📡 正在獲取 {len(cids)} 個市場嘅實時價格...")
    
    # Fetch realtime prices
    realtime_data = get_realtime_prices_batch(cids)
    
    # Merge into markets
    success_count = 0
    for m in markets_to_process:
        cid = m.get('conditionId', m.get('condition_id'))
        if cid and cid in realtime_data:
            price_data = realtime_data[cid]
            
            if not price_data.get('error'):
                # Add realtime fields
                m['realtime_yes_bid'] = price_data.get('yes_bid')
                m['realtime_yes_ask'] = price_data.get('yes_ask')
                m['realtime_yes_mid'] = price_data.get('yes_mid')
                m['realtime_no_bid'] = price_data.get('no_bid')
                m['realtime_no_ask'] = price_data.get('no_ask')
                m['realtime_no_mid'] = price_data.get('no_mid')
                m['realtime_spread_pct'] = price_data.get('spread_pct')
                m['realtime_fetched_at'] = price_data.get('fetched_at')
                m['price_is_realtime'] = True
                success_count += 1
            else:
                m['price_is_realtime'] = False
                m['realtime_error'] = price_data.get('error')
    
    print(f"   ✅ 成功獲取 {success_count}/{len(cids)} 個市場嘅實時價格")
    
    return markets


def compare_cached_vs_realtime(condition_id: str, cached_price: float) -> Dict[str, Any]:
    """
    比較緩存價格同實時價格嘅差異
    
    用於驗證緩存數據嘅準確性
    
    Args:
        condition_id: 市場 Condition ID
        cached_price: 緩存中嘅 Yes 價格 (0-1)
    
    Returns:
        Dict with comparison results
    """
    realtime = get_realtime_price(condition_id)
    
    if realtime.get('error'):
        return {
            'condition_id': condition_id,
            'cached_price': cached_price,
            'error': realtime['error']
        }
    
    realtime_mid = realtime.get('yes_mid', 0)
    
    if realtime_mid and cached_price:
        diff = abs(realtime_mid - cached_price)
        diff_pct = (diff / cached_price * 100) if cached_price > 0 else 0
        
        # Determine if difference is significant
        is_stale = diff_pct > 5  # >5% difference considered stale
        
        return {
            'condition_id': condition_id,
            'cached_price': cached_price,
            'realtime_price': realtime_mid,
            'difference': diff,
            'difference_pct': diff_pct,
            'is_stale': is_stale,
            'fetched_at': realtime['fetched_at']
        }
    
    return {
        'condition_id': condition_id,
        'cached_price': cached_price,
        'realtime_price': realtime_mid,
        'error': 'Unable to compare prices'
    }
