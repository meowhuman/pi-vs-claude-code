#!/usr/bin/env python3
"""
Polymarket Arbitrage Monitor
Checks for 'Risk-Free' Arbitrage where Sum(BestAsk) < 1.00.
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add parent scripts dir to path
sys.path.append(os.path.dirname(__file__))

from utils.client import get_client
from utils.market import get_orderbook
from search import fetch_all_markets

def execute_arbitrage_trade(client, market_data, test_amount=1.0):
    """
    Execute an arbitrage trade by buying both Yes and No.
    
    Args:
        client: Polymarket client with credentials
        market_data: Market dict from API
        test_amount: Total USDC to spend (split between Yes/No)
    
    Returns:
        (success, message)
    """
    from py_clob_client.clob_types import OrderArgs
    
    cid = market_data.get('conditionId') or market_data.get('condition_id')
    question = market_data.get('question', 'Unknown')
    
    # Fetch full market info from API (includes minimum_order_size)
    market = client.get_market(cid)
    if not market:
        return False, "Market not found"
    
    min_size = market.get('minimum_order_size', 1)
    tokens = market.get('tokens', [])
    
    if len(tokens) != 2:
        return False, "Not a binary market"
    
    print(f"📊 Market: {question[:50]}...")
    print(f"   Min Order Size: {min_size} shares")
    
    orders = []
    total_cost = 0.0
    
    for t in tokens:
        token_id = t['token_id']
        outcome = t['outcome']
        
        # Get best ask
        ob = client.get_order_book(token_id)
        if not ob.asks:
            return False, f"No asks for {outcome}"
        
        best_ask = float(ob.asks[0].price)
        
        # Calculate size: use minimum required, or more if test_amount allows
        size_from_amount = (test_amount / 2) / best_ask
        size = max(min_size, size_from_amount)
        
        cost = size * best_ask
        total_cost += cost
        
        orders.append({
            'token_id': token_id,
            'outcome': outcome,
            'price': best_ask,
            'size': size,
            'cost': cost
        })
        
        print(f"   {outcome}: {size} shares @ ${best_ask:.3f} = ${cost:.2f}")
    
    print(f"   💰 Total Cost: ${total_cost:.2f}")
    print(f"   📈 Expected Return: $1.00 (one side wins)")
    print(f"   🎯 Profit: ${1.0 - total_cost:.4f}")
    
    # Only proceed if profitable
    if total_cost >= 1.0:
        return False, f"Not profitable (Cost ${total_cost:.2f} >= $1.00)"
    
    # Execute both orders
    success_count = 0
    yes_entry = no_entry = 0
    yes_shares = no_shares = 0
    
    for order in orders:
        try:
            order_args = OrderArgs(
                price=round(order['price'], 3),
                size=order['size'],
                side="BUY",
                token_id=order['token_id'],
            )
            
            resp = client.create_and_post_order(order_args)
            order_id = resp.orderID if hasattr(resp, 'orderID') else resp.get('orderID', '?')
            print(f"   ✅ {order['outcome']} order placed: {order_id}")
            success_count += 1
            
            # Track entry prices
            if order['outcome'] == 'Yes':
                yes_entry = order['price']
                yes_shares = order['size']
            else:
                no_entry = order['price']
                no_shares = order['size']
                
        except Exception as e:
            print(f"   ❌ {order['outcome']} order failed: {e}")
    
    if success_count == 2:
        # Record position for exit monitoring
        from arb_positions import add_position
        add_position(
            condition_id=cid,
            question=question,
            yes_entry=yes_entry,
            no_entry=no_entry,
            yes_shares=yes_shares,
            no_shares=no_shares,
            total_cost=total_cost
        )
        return True, f"Arbitrage executed! Cost: ${total_cost:.2f}"
    else:
        return False, f"Partial execution ({success_count}/2)"

def check_market_arbitrage(client, condition_id, market_name):
    """
    Check a single market for arbitrage opportunity.
    Returns: (profit_potential, details_str)
    """
    try:
        # We need to fetch orderbooks for both/all outcomes
        # Simplify: assume Binary (Yes/No) for now which is most common for 15m markets
        # We need the Token IDs.
        # Since we might not have them, we use the client to fetch market details first if needed, 
        # but that's slow. 
        # Optimized: detailed searching usually provides token IDs.
        
        # Taking a shortcut: use our get_orderbook util which handles Token ID lookup if we pass market ID?
        # get_orderbook(condition_id) -> returns {outcome: {bids:[], asks:[]}}
        
        # Actually get_orderbook in utils/market.py might need looking at.
        # Let's assume we can fetch it.
        
        # For speed, we want to just check "Yes" and "No" asks.
        # Let's rely on the `get_orderbook` function from `utils.market`.
        pass
    except Exception as e:
        return -1, f"Error: {e}"

def scan_all_markets(limit=200, min_vol=1000, category=None, threshold=1.98):
    """
    Scan top active markets for arbitrage.
    
    Args:
        limit: Max markets to scan (default: 200)
        min_vol: Minimum volume filter (default: $1000)
        category: Optional category filter (crypto, politics, sports, etc.)
        threshold: Arbitrage threshold - Sum(Yes_Ask + No_Ask) < threshold means opportunity
                   Polymarket Sum is ~$2.00 normally (not $1.00 like some DEXs)
                   Default: 1.98 = 1% profit (buy both for <$1.98, guaranteed $2 payout)
    """
    from datetime import datetime
    start_time = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"🔍 POLYMARKET ARBITRAGE SCANNER")
    print(f"{'='*60}")
    print(f"⏰ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Scan limit: {limit} markets | Min Vol: ${min_vol:,} | Threshold: {threshold}")
    if category:
        print(f"🏷️ Category filter: {category}")
    print(f"{'='*60}\n")
    
    markets = fetch_all_markets(use_cache=True, fast=False)
    
    # Filter
    active_markets = [m for m in markets if m.get('active', True) or m.get('closed') is False]
    active_markets = [m for m in active_markets if float(m.get('volume', 0)) >= min_vol]
    
    if category:
        from search import filter_by_category
        active_markets = filter_by_category(active_markets, category)
    
    # Sort by volume (highest first) for better opportunities
    active_markets = sorted(active_markets, key=lambda x: float(x.get('volume', 0)), reverse=True)
        
    total_available = len(active_markets)
    to_scan = min(limit, total_available)
    print(f"📉 Found {total_available} markets matching criteria, scanning top {to_scan}...\n")
    
    # Stats tracking
    opportunities = []
    near_misses = []  # Markets close to threshold
    checked_count = 0
    skipped_non_binary = 0
    skipped_no_asks = 0
    errors = 0
    all_costs = []
    
    client = get_client(with_creds=False)
    
    for i, m in enumerate(active_markets[:limit]):
        cid = m.get('conditionId') or m.get('condition_id')
        question = m.get('question', 'Unknown')
        volume = float(m.get('volume', 0))
        slug = m.get('slug', '')
        
        try:
            # Get clobTokenIds from Gamma API cache
            clob_token_ids = m.get('clobTokenIds', [])
            
            # Parse if string (JSON array)
            if isinstance(clob_token_ids, str):
                import json as _json
                try:
                    clob_token_ids = _json.loads(clob_token_ids)
                except:
                    clob_token_ids = []
            
            # Binary markets have exactly 2 token IDs (Yes, No)
            if len(clob_token_ids) != 2:
                skipped_non_binary += 1
                continue
                
            cost = 0.0
            details = []
            outcomes = ['Yes', 'No']
            
            valid = True
            for idx, token_id in enumerate(clob_token_ids):
                outcome = outcomes[idx] if idx < len(outcomes) else f"Outcome{idx}"
                
                ob = client.get_order_book(token_id)
                
                if not ob.asks:
                    valid = False
                    skipped_no_asks += 1
                    break
                    
                best_ask = float(ob.asks[0].price)
                cost += best_ask
                details.append(f"{outcome}: ${best_ask:.3f}")
                
            if valid:
                checked_count += 1
                all_costs.append(cost)
                # Polymarket payout is $2.00 for winning side (you bought both Yes and No, one wins)
                profit = 2.0 - cost
                profit_pct = (profit / cost) * 100 if cost > 0 else 0
                
                # ARBITRAGE FOUND!
                if cost < threshold: 
                    opp = {
                        "question": question,
                        "cost": cost,
                        "profit": profit,
                        "profit_pct": profit_pct,
                        "details": ", ".join(details),
                        "volume": volume,
                        "id": cid,
                        "slug": slug
                    }
                    opportunities.append(opp)
                    print(f"🚨 ARBITRAGE FOUND!")
                    print(f"   📌 {question[:60]}...")
                    print(f"   💰 Cost: ${cost:.4f} | Profit: ${profit:.4f} ({profit_pct:.2f}%)")
                    print(f"   📊 {', '.join(details)}")
                    print(f"   🔗 https://polymarket.com/event/{slug}")
                    print()
                
                # Near-miss (Sum < $2.00 = break-even)
                elif cost < 2.00:
                    near_misses.append({
                        "question": question[:50],
                        "cost": cost,
                        "profit_pct": profit_pct,
                        "volume": volume
                    })
                
                # Progress indicator every 20 markets
                if i % 20 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"   ⏳ Progress: {i}/{to_scan} checked ({elapsed:.1f}s) | Best so far: ${min(all_costs) if all_costs else 2:.4f}")
                        
            time.sleep(0.03)  # Slightly faster rate limit
                
        except Exception as e:
            errors += 1
            # Log first few errors for debugging
            if errors <= 3:
                print(f"   ⚠️ Error on {question[:30]}...: {str(e)[:50]}")
    
    # === SUMMARY REPORT ===
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n{'='*60}")
    print(f"📊 SCAN COMPLETE - SUMMARY")
    print(f"{'='*60}")
    print(f"⏱️ Duration: {elapsed:.1f} seconds")
    print(f"✅ Markets checked: {checked_count}/{to_scan}")
    print(f"⏭️ Skipped (non-binary): {skipped_non_binary}")
    print(f"⏭️ Skipped (no asks): {skipped_no_asks}")
    print(f"❌ Errors: {errors}")
    
    if all_costs:
        avg_cost = sum(all_costs) / len(all_costs)
        min_cost = min(all_costs)
        max_cost = max(all_costs)
        print(f"\n💹 Price Distribution:")
        print(f"   Min Sum: ${min_cost:.4f} (Best)")
        print(f"   Avg Sum: ${avg_cost:.4f}")
        print(f"   Max Sum: ${max_cost:.4f}")
    
    print(f"\n🎯 RESULTS:")
    print(f"   🚨 Arbitrage opportunities: {len(opportunities)}")
    print(f"   📍 Near-misses (Sum < $1.00): {len(near_misses)}")
    
    if near_misses:
        print(f"\n📍 Top Near-Misses (closest to threshold):")
        sorted_near = sorted(near_misses, key=lambda x: x['cost'])[:5]
        for nm in sorted_near:
            print(f"   • {nm['question']}... | Sum: ${nm['cost']:.4f} | Profit: {nm['profit_pct']:.2f}%")
    
    print(f"{'='*60}\n")
            
    return opportunities, {
        "checked": checked_count,
        "errors": errors,
        "near_misses": len(near_misses),
        "min_cost": min(all_costs) if all_costs else None,
        "avg_cost": sum(all_costs) / len(all_costs) if all_costs else None,
        "elapsed_seconds": elapsed
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polymarket Arbitrage Monitor")
    parser.add_argument("--scan", action="store_true", help="Scan top markets")
    parser.add_argument("--limit", type=int, default=200, help="Max markets to scan (default: 200)")
    parser.add_argument("-c", "--category", help="Category filter (crypto, politics, sports, etc.)")
    parser.add_argument("--threshold", type=float, default=1.98, help="Arb threshold, e.g. 1.98 = 1%% profit (default: 1.98)")
    parser.add_argument("--min-vol", type=int, default=1000, help="Minimum volume filter (default: $1000)")
    parser.add_argument("--watch", help="Watch specific Condition ID")
    parser.add_argument("--execute", action="store_true", help="Execute trades on found arb")
    parser.add_argument("--test-trade", help="Test trade on a specific market ID")
    parser.add_argument("--amount", type=float, default=1.0, help="Test trade amount in USDC")
    parser.add_argument("--monitor-exits", action="store_true", help="Check open positions for exit opportunities")
    parser.add_argument("--status", action="store_true", help="Show portfolio status")
    
    args = parser.parse_args()
    
    if args.status:
        # Show portfolio summary
        from arb_positions import get_summary
        summary, data = get_summary()
        print(summary)
        for p in data.get("positions", []):
            if p["status"] == "OPEN":
                print(f"  📍 {p['question'][:40]}... | Cost: ${p['total_cost']:.2f}")
                
    elif args.monitor_exits:
        # Check for exit opportunities
        from arb_positions import check_exit_opportunities, execute_exit
        client = get_client(with_creds=True)
        exits = check_exit_opportunities(client)
        
        if exits:
            print(f"🎯 Found {len(exits)} exit opportunities!")
            for exit_info in exits:
                success, msg = execute_exit(client, exit_info)
                print(f"   {msg}")
        else:
            print("📊 No exit opportunities yet. Positions still open.")
            
    elif args.test_trade:
        # Test trade on specific market
        print(f"🧪 Testing trade on market: {args.test_trade}")
        client = get_client(with_creds=True)
        market = client.get_market(args.test_trade)
        if market:
            success, msg = execute_arbitrage_trade(client, market, test_amount=args.amount)
            print(f"Result: {msg}")
        else:
            print("❌ Market not found")
    elif args.scan:
        opps, stats = scan_all_markets(
            limit=args.limit, 
            min_vol=args.min_vol,
            category=args.category,
            threshold=args.threshold
        )
        if args.execute and opps:
            print(f"\n🚀 Executing trades on {len(opps)} opportunities...")
            client = get_client(with_creds=True)
            for opp in opps:
                success, msg = execute_arbitrage_trade(client, opp, test_amount=args.amount)
                print(f"   {msg}")
    elif args.watch:
        print(f"Watching {args.watch}...")
        # TODO: Implement loop
    else:
        parser.print_help()


