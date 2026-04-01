#!/usr/bin/env python3
"""
Polymarket Arbitrage Position Manager
Tracks arbitrage positions and monitors for exit opportunities.
"""

import json
import os
from datetime import datetime
from pathlib import Path

POSITIONS_FILE = Path(__file__).parent / "cache" / "arb_positions.json"

def load_positions():
    """Load existing arb positions"""
    if POSITIONS_FILE.exists():
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return {"positions": [], "total_pnl": 0.0}

def save_positions(data):
    """Save positions to file"""
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def add_position(condition_id, question, yes_entry, no_entry, yes_shares, no_shares, total_cost):
    """
    Add a new arbitrage position.
    
    Args:
        condition_id: Market ID
        question: Market question
        yes_entry: Entry price for Yes
        no_entry: Entry price for No
        yes_shares: Shares bought for Yes
        no_shares: Shares bought for No
        total_cost: Total USDC spent
    """
    data = load_positions()
    
    position = {
        "id": f"arb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "condition_id": condition_id,
        "question": question,
        "entry_time": datetime.now().isoformat(),
        "yes_entry": yes_entry,
        "no_entry": no_entry,
        "yes_shares": yes_shares,
        "no_shares": no_shares,
        "total_cost": total_cost,
        "expected_payout": yes_shares,  # One side wins, payout = shares
        "expected_profit": yes_shares - total_cost,
        "status": "OPEN",
        "exit_time": None,
        "exit_price": None,
        "realized_pnl": None
    }
    
    data["positions"].append(position)
    save_positions(data)
    
    print(f"📝 Position recorded: {position['id']}")
    return position

def check_exit_opportunities(client):
    """
    Check all open positions for exit opportunities.
    Exit when winning leg Best Bid >= 0.95
    
    Returns: List of positions ready to exit
    """
    data = load_positions()
    ready_to_exit = []
    
    for pos in data["positions"]:
        if pos["status"] != "OPEN":
            continue
            
        try:
            market = client.get_market(pos["condition_id"])
            if not market:
                continue
                
            tokens = market.get("tokens", [])
            
            for t in tokens:
                token_id = t["token_id"]
                outcome = t["outcome"]
                
                ob = client.get_order_book(token_id)
                if not ob.bids:
                    continue
                    
                best_bid = float(ob.bids[0].price)
                
                # Check if this side is winning (price approaching $1.00)
                if best_bid >= 0.95:
                    ready_to_exit.append({
                        "position": pos,
                        "winning_side": outcome,
                        "token_id": token_id,
                        "exit_price": best_bid,
                        "shares": pos["yes_shares"] if outcome == "Yes" else pos["no_shares"],
                        "expected_pnl": (best_bid * pos["yes_shares"]) - pos["total_cost"]
                    })
                    break
                    
        except Exception as e:
            print(f"⚠️ Error checking {pos['condition_id']}: {e}")
            
    return ready_to_exit

def execute_exit(client, exit_info):
    """
    Execute exit trade (sell winning leg).
    
    Returns: (success, message)
    """
    from py_clob_client.clob_types import OrderArgs
    
    pos = exit_info["position"]
    
    try:
        # Create SELL order
        order_args = OrderArgs(
            price=round(exit_info["exit_price"], 3),
            size=exit_info["shares"],
            side="SELL",
            token_id=exit_info["token_id"],
        )
        
        resp = client.create_and_post_order(order_args)
        order_id = resp.orderID if hasattr(resp, 'orderID') else resp.get('orderID', '?')
        
        # Update position status
        data = load_positions()
        for p in data["positions"]:
            if p["id"] == pos["id"]:
                p["status"] = "CLOSED"
                p["exit_time"] = datetime.now().isoformat()
                p["exit_price"] = exit_info["exit_price"]
                p["realized_pnl"] = exit_info["expected_pnl"]
                data["total_pnl"] += exit_info["expected_pnl"]
                break
        save_positions(data)
        
        msg = f"✅ EXIT: {pos['question'][:30]}... | Sold {exit_info['winning_side']} @ ${exit_info['exit_price']:.2f} | PnL: ${exit_info['expected_pnl']:.2f}"
        print(msg)
        return True, msg
        
    except Exception as e:
        return False, f"❌ Exit failed: {e}"

def get_summary():
    """Get portfolio summary"""
    data = load_positions()
    
    open_positions = [p for p in data["positions"] if p["status"] == "OPEN"]
    closed_positions = [p for p in data["positions"] if p["status"] == "CLOSED"]
    
    total_invested = sum(p["total_cost"] for p in open_positions)
    realized_pnl = data.get("total_pnl", 0)
    unrealized_pnl = sum(p["expected_profit"] for p in open_positions)
    
    summary = f"""
📊 **Arbitrage Portfolio**
├─ Open Positions: {len(open_positions)}
├─ Closed Positions: {len(closed_positions)}
├─ Total Invested: ${total_invested:.2f}
├─ Realized P&L: ${realized_pnl:.2f}
└─ Unrealized P&L: ${unrealized_pnl:.2f}
"""
    return summary, data

if __name__ == "__main__":
    summary, _ = get_summary()
    print(summary)
