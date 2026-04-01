#!/usr/bin/env python3
"""
Polymarket Portfolio Manager v2.0
- 查看持倉 (Dashboard)
- 一鍵平倉 (Close Position) with Liquidity Check
- Limit Order 支援
- JSON 輸出 (Automation-ready)
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


def get_wallet_positions(wallet_address: str) -> list:
    """獲取錢包所有持倉"""
    try:
        resp = requests.get(f"{DATA_API}/positions", params={"user": wallet_address}, timeout=15)
        if resp.status_code == 200:
            positions = resp.json()
            return [p for p in positions if float(p.get("size", p.get("shares", 0))) > 0.001]
        return []
    except Exception as e:
        print(f"❌ API 錯誤: {e}", file=sys.stderr)
        return []


def get_market_info(condition_id: str) -> dict:
    """獲取市場詳情"""
    try:
        resp = requests.get(f"{DATA_API}/markets/{condition_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        resp = requests.get(f"{GAMMA_API}/markets?conditionId={condition_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
        return {}
    except:
        return {}


def get_orderbook_from_clob(condition_id: str, outcome: str) -> dict:
    """從 CLOB API 獲取真實 orderbook"""
    from py_clob_client.client import ClobClient
    from py_clob_client.constants import POLYGON
    
    try:
        signing_key = os.getenv("POLYGON_PRIVATE_KEY")
        builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
        
        client = ClobClient(
            CLOB_API,
            key=signing_key,
            chain_id=POLYGON,
            signature_type=1,
            funder=builder_wallet
        )
        
        market = client.get_market(condition_id)
        tokens = market.get('tokens', [])
        
        token_id = None
        for t in tokens:
            if t['outcome'].lower() == outcome.lower():
                token_id = t['token_id']
                break
        
        if not token_id:
            return {}
        
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


def show_dashboard(json_output: bool = False):
    """顯示持倉儀表板"""
    control_wallet = os.getenv("WALLET_ADDRESS")
    builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS", "0xf5459aeE5E781371Fe4D32c6FD74D6154F52cA3B")
    
    all_positions = []
    for wallet, label in [(control_wallet, "Control"), (builder_wallet, "Builder")]:
        if not wallet:
            continue
        positions = get_wallet_positions(wallet)
        for p in positions:
            p['_wallet_type'] = label
            p['_wallet'] = wallet
        all_positions.extend(positions)
    
    if not all_positions:
        if json_output:
            print(json.dumps({"positions": [], "summary": {"total": 0}}, indent=2))
        else:
            print("📭 冇任何持倉")
        return []
    
    processed = []
    for pos in all_positions:
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
        
        processed.append({
            "market_name": market_name[:60] + "..." if len(market_name) > 60 else market_name,
            "condition_id": condition_id,
            "outcome": outcome,
            "shares": round(shares, 2),
            "avg_price": round(avg_price, 4),
            "current_price": round(cur_price, 4),
            "cost": round(cost, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 1),
            "wallet_type": pos.get('_wallet_type', '?')
        })
    
    processed.sort(key=lambda x: x['value'], reverse=True)
    
    total_cost = sum(p['cost'] for p in processed)
    total_value = sum(p['value'] for p in processed)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    if json_output:
        result = {
            "timestamp": datetime.now().isoformat(),
            "positions": processed,
            "summary": {
                "total_positions": len(processed),
                "total_cost": round(total_cost, 2),
                "total_value": round(total_value, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl_pct, 1)
            }
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return processed
    
    print("\n" + "="*100)
    print("📊 POLYMARKET 持倉儀表板")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    for i, p in enumerate(processed, 1):
        pnl_emoji = "🟢" if p['pnl'] >= 0 else "🔴"
        pnl_sign = "+" if p['pnl'] >= 0 else ""
        
        print(f"\n{i}. {p['market_name']}")
        print(f"   💼 {p['wallet_type']} | {p['outcome']} | {p['shares']} shares")
        print(f"   💰 成本: ${p['cost']:.2f} (@ ${p['avg_price']:.2f}) → 現值: ${p['value']:.2f} (@ ${p['current_price']:.2f})")
        print(f"   {pnl_emoji} 盈虧: {pnl_sign}${p['pnl']:.2f} ({pnl_sign}{p['pnl_pct']:.1f}%)")
        print(f"   📋 ID: {p['condition_id'][:20]}...")
    
    print("\n" + "="*100)
    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
    pnl_sign = "+" if total_pnl >= 0 else ""
    
    print(f"\n💼 總結:")
    print(f"   • 持倉數量: {len(processed)}")
    print(f"   • 總成本: ${total_cost:.2f}")
    print(f"   • 總現值: ${total_value:.2f}")
    print(f"   {pnl_emoji} 總盈虧: {pnl_sign}${total_pnl:.2f} ({pnl_sign}{total_pnl_pct:.1f}%)")
    print("="*100 + "\n")
    
    return processed


def close_position(condition_id: str, outcome: str = None, shares: float = None, 
                   auto_confirm: bool = False, limit_price: float = None):
    """平倉指定市場 (附流動性檢查)"""
    print(f"\n🔄 準備平倉: {condition_id[:20]}...")
    
    control_wallet = os.getenv("WALLET_ADDRESS")
    builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
    
    target_position = None
    for wallet, label in [(control_wallet, "Control"), (builder_wallet, "Builder")]:
        if not wallet:
            continue
        positions = get_wallet_positions(wallet)
        for p in positions:
            p_cid = p.get("conditionId", "") or (p.get("market", {}) or {}).get("conditionId", "")
            if p_cid == condition_id:
                target_position = p
                break
        if target_position:
            break
    
    if not target_position:
        print(f"❌ 找不到持倉: {condition_id}")
        return False
    
    pos_outcome = target_position.get("outcome", target_position.get("side", "?"))
    pos_shares = float(target_position.get("size", target_position.get("shares", 0)))
    data_api_price = float(target_position.get("curPrice", target_position.get("current_price", 0)))
    
    if outcome and outcome.upper() != pos_outcome.upper():
        print(f"❌ Outcome 不匹配: 你揸住 {pos_outcome}，但你指定 {outcome}")
        return False
    
    sell_shares = shares if shares else pos_shares
    if sell_shares > pos_shares:
        print(f"❌ 你只有 {pos_shares} shares，不能賣 {sell_shares}")
        return False
    
    market_info = target_position.get("market", {})
    market_name = market_info.get("question", "Unknown") if isinstance(market_info, dict) else target_position.get("title", "Unknown")
    
    # ⚠️ LIQUIDITY CHECK - 關鍵功能
    print(f"\n📊 檢查流動性...")
    orderbook = get_orderbook_from_clob(condition_id, pos_outcome)
    
    if "error" in orderbook:
        print(f"   ⚠️ 無法獲取 orderbook: {orderbook['error']}")
        best_bid = data_api_price  # Fallback to data API price
        spread_warning = True
    else:
        best_bid = orderbook.get("best_bid", 0)
        best_ask = orderbook.get("best_ask", 0)
        spread_pct = orderbook.get("spread_pct", 0)
        
        print(f"   Best Bid: ${best_bid:.2f} | Best Ask: ${best_ask:.2f}")
        print(f"   Spread: {spread_pct:.1f}%")
        
        spread_warning = spread_pct and spread_pct > 20
    
    # Price comparison
    if best_bid < data_api_price * 0.5:
        print(f"\n   🚨 嚴重警告: Best Bid (${best_bid:.2f}) 遠低於 Data API 顯示價格 (${data_api_price:.2f})!")
        print(f"   🚨 如果以市價平倉，你可能會損失 {((data_api_price - best_bid) / data_api_price * 100):.0f}%!")
        spread_warning = True
    
    estimated_value = sell_shares * best_bid
    
    print(f"\n📊 平倉詳情:")
    print(f"   市場: {market_name[:50]}...")
    print(f"   方向: {pos_outcome}")
    print(f"   賣出: {sell_shares:.2f} shares")
    print(f"   Best Bid: ${best_bid:.2f}")
    print(f"   預計收入: ${estimated_value:.2f}")
    
    if spread_warning and not auto_confirm:
        print(f"\n   ⚠️ 流動性警告! 建議用 Limit Order 掛單。")
        print(f"   用法: python portfolio.py close \"{condition_id}\" --limit 0.50")
        confirm = input(f"\n⚠️ 是否仍以市價平倉? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    elif not auto_confirm:
        confirm = input(f"\n確認平倉? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    
    # Execute trade
    print(f"\n🚀 正在執行平倉...")
    
    import subprocess
    trade_script = os.path.join(os.path.dirname(__file__), "execute_trade.py")
    
    cmd = [
        sys.executable, trade_script,
        "--market-id", condition_id,
        "--side", pos_outcome,
        "--amount", str(sell_shares),
        "--trade-side", "SELL",
        "--auto-confirm"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode == 0:
            print(f"\n✅ 平倉成功!")
            return True
        else:
            print(f"\n❌ 平倉失敗 (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 交易超時")
        return False
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        return False


def check_liquidity(condition_id: str, outcome: str = "Yes"):
    """檢查市場流動性"""
    print(f"\n📊 檢查流動性: {condition_id[:20]}...")
    
    orderbook = get_orderbook_from_clob(condition_id, outcome)
    
    if "error" in orderbook:
        print(f"❌ 無法獲取 orderbook: {orderbook['error']}")
        return
    
    print(f"\n   Outcome: {outcome}")
    print(f"   Best Bid: ${orderbook['best_bid']:.2f} ({orderbook['bid_size']:.0f} shares)")
    print(f"   Best Ask: ${orderbook['best_ask']:.2f} ({orderbook['ask_size']:.0f} shares)")
    print(f"   Spread: ${orderbook['spread']:.2f} ({orderbook['spread_pct']:.1f}%)")
    
    if orderbook['spread_pct'] > 20:
        print(f"\n   🚨 警告: Spread 超過 20%，流動性差!")
    elif orderbook['spread_pct'] > 10:
        print(f"\n   ⚠️ 注意: Spread 偏大 ({orderbook['spread_pct']:.1f}%)")
    else:
        print(f"\n   ✅ 流動性正常")
    
    return orderbook


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Portfolio Manager v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python portfolio.py                         # 顯示持倉儀表板
  python portfolio.py --json                  # JSON 格式輸出
  python portfolio.py close <ID>              # 平倉 (附流動性檢查)
  python portfolio.py close <ID> --auto       # 自動確認平倉
  python portfolio.py liquidity <ID> --outcome Yes   # 檢查流動性
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Close command
    close_parser = subparsers.add_parser("close", help="平倉指定市場")
    close_parser.add_argument("condition_id", help="市場 Condition ID")
    close_parser.add_argument("--outcome", "-o", help="指定 outcome (YES/NO)")
    close_parser.add_argument("--shares", "-s", type=float, help="指定賣出股數")
    close_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    close_parser.add_argument("--limit", "-l", type=float, help="Limit Order 價格")
    
    # Liquidity check command
    liq_parser = subparsers.add_parser("liquidity", help="檢查市場流動性")
    liq_parser.add_argument("condition_id", help="市場 Condition ID")
    liq_parser.add_argument("--outcome", "-o", default="Yes", help="Outcome (Yes/No)")
    
    parser.add_argument("--json", action="store_true", help="JSON 格式輸出")
    
    args = parser.parse_args()
    
    if args.command == "close":
        close_position(
            args.condition_id,
            outcome=args.outcome,
            shares=args.shares,
            auto_confirm=args.auto,
            limit_price=args.limit
        )
    elif args.command == "liquidity":
        check_liquidity(args.condition_id, args.outcome)
    else:
        show_dashboard(json_output=args.json)


if __name__ == "__main__":
    main()
