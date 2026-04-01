#!/usr/bin/env python3
"""
Polymarket Trade Engine - 統一交易入口
整合: execute_trade.py, limit_order.py, tp_sl.py

用法:
    python trade.py buy <ID> --amount 10
    python trade.py sell <ID> --shares 5
    python trade.py limit <ID> --price 0.50 --amount 10
    python trade.py tp <ID> --price 0.70
    python trade.py sl <ID> --price 0.30
    python trade.py orders                    # 查看未成交訂單
    python trade.py cancel <order_id>         # 取消訂單
    python trade.py alerts                    # 查看 TP/SL 警報
    python trade.py monitor                   # 監控 TP/SL
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.client import get_client, get_api_urls
from utils.market import get_orderbook, get_token_id

load_dotenv()

# TP/SL Alerts file
ALERTS_FILE = os.path.join(os.path.dirname(__file__), "cache", "tp_sl_alerts.json")


# =============================================================================
# Core Trading Functions
# =============================================================================

def execute_market_order(condition_id: str, outcome: str, amount: float,
                         trade_side: str = "BUY", auto_confirm: bool = False) -> bool:
    """
    執行市價單
    
    Args:
        condition_id: 市場 ID
        outcome: Yes/No
        amount: USDC (BUY) 或 Shares (SELL)
        trade_side: BUY / SELL
        auto_confirm: 跳過確認
    """
    from py_clob_client.clob_types import OrderArgs
    
    print(f"\n🔐 初始化交易客戶端...")
    
    try:
        client = get_client(with_creds=True)
        
        # Get market info
        market = client.get_market(condition_id)
        if not market:
            print("❌ 找不到市場")
            return False
        
        if market.get('closed'):
            print("❌ 市場已關閉")
            return False
        
        # Find token ID
        tokens = market.get('tokens', [])
        token_id = None
        for t in tokens:
            if t['outcome'].lower() == outcome.lower():
                token_id = t['token_id']
                break
        
        if not token_id:
            print(f"❌ 找不到 {outcome} outcome")
            return False
        
        # Use get_price() instead of get_order_book() - orderbook returns stale data!
        # See: https://github.com/Polymarket/py-clob-client/issues/180
        try:
            buy_price_resp = client.get_price(token_id, side='BUY')
            sell_price_resp = client.get_price(token_id, side='SELL')
            real_buy_price = float(buy_price_resp.get('price', 0))
            real_sell_price = float(sell_price_resp.get('price', 0))
            
            print(f"💰 實時報價 (from get_price API):")
            print(f"   Buy @ ${real_buy_price:.3f}")
            print(f"   Sell @ ${real_sell_price:.3f}")
            print(f"   Spread: {(real_sell_price - real_buy_price)*100:.1f}%")
        except Exception as e:
            print(f"⚠️ get_price() 失敗: {e}")
            # Fallback to token price
            real_buy_price = None
            real_sell_price = None
        
        # Get token price as additional reference
        token_price = None
        for t in tokens:
            if t['outcome'].lower() == outcome.lower():
                token_price = float(t.get('price', 0))
                break
        
        if trade_side.upper() == "SELL":
            # For SELL, use the buy price (what buyers are willing to pay)
            if real_buy_price and real_buy_price > 0.01:
                best_price = real_buy_price
            elif token_price:
                best_price = round(token_price * 0.98, 2)  # 2% discount
                print(f"💡 Using token price fallback: ${best_price:.2f}")
            else:
                print("❌ 無法獲取準確價格")
                return False
            
            size = amount  # For SELL, amount = shares
        else:
            # For BUY, use the sell price (what sellers are asking)
            if real_sell_price and real_sell_price < 0.99:
                best_price = real_sell_price
            elif token_price:
                best_price = round(token_price * 1.02, 2)  # 2% premium
                print(f"💡 Using token price fallback: ${best_price:.2f}")
            else:
                print("❌ 無法獲取準確價格")
                return False
            
            size = round(amount / best_price, 2)
        
        execution_price = round(best_price, 2)
        
        if size < 0.1:
            print("❌ Size 太小 (最少 0.1 shares)")
            return False
        
        # Show summary
        print(f"\n📝 交易摘要:")
        print(f"   市場: {market.get('question', condition_id)[:50]}...")
        print(f"   動作: {trade_side.upper()} {outcome}")
        
        if trade_side.upper() == "SELL":
            print(f"   股數: {size}")
            print(f"   預計價格: ${execution_price:.2f} (Best Bid)")
            print(f"   預計收入: ${size * execution_price:.2f}")
        else:
            print(f"   金額: ${amount:.2f}")
            print(f"   預計價格: ${execution_price:.2f} (Best Ask)")
            print(f"   預計獲得: {size:.2f} shares")
        
        # Confirmation
        max_auto = float(os.getenv("MAX_AUTO_AMOUNT", "1.0"))
        if amount > max_auto and not auto_confirm:
            print(f"\n⚠️ 金額 (${amount}) 超過自動限額 (${max_auto})")
            confirm = input("確認交易? (yes/no): ").strip().lower()
            if confirm not in ["yes", "y"]:
                print("❌ 已取消")
                return False
        
        # Execute
        print("\n🚀 執行交易...")
        
        order_args = OrderArgs(
            price=execution_price,
            size=size,
            side=trade_side.upper(),
            token_id=token_id,
        )
        
        resp = client.create_and_post_order(order_args)
        
        order_id = resp.orderID if hasattr(resp, 'orderID') else resp.get('orderID', '?')
        
        print(f"✅ 交易已提交!")
        print(f"   Order ID: {order_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 交易失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Limit Order Functions
# =============================================================================

def place_limit_order(condition_id: str, outcome: str, side: str, price: float,
                      size: float = None, amount: float = None, 
                      auto_confirm: bool = False) -> bool:
    """
    掛 Limit Order
    
    Args:
        condition_id: 市場 ID
        outcome: Yes/No
        side: BUY/SELL
        price: 掛單價格 (0.01 - 0.99)
        size: 股數 (SELL 用)
        amount: USDC (BUY 用)
    """
    from py_clob_client.clob_types import OrderArgs
    
    print(f"\n📝 準備 Limit Order...")
    print(f"   市場: {condition_id[:30]}...")
    print(f"   方向: {side} {outcome}")
    print(f"   價格: ${price:.2f}")
    
    if side.upper() == "BUY":
        if not amount:
            print("❌ BUY 訂單需要指定 --amount")
            return False
        size = round(amount / price, 2)
        print(f"   金額: ${amount:.2f} USDC")
        print(f"   預計獲得: {size:.2f} shares")
    else:
        if not size:
            print("❌ SELL 訂單需要指定 --shares")
            return False
        estimated_value = size * price
        print(f"   股數: {size:.2f}")
        print(f"   預計收入: ${estimated_value:.2f} USDC")
    
    if not auto_confirm:
        confirm = input(f"\n確認掛單? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    
    try:
        client = get_client(with_creds=True)
        token_id = get_token_id(condition_id, outcome)
        
        if not token_id:
            print(f"❌ 找不到 {outcome} outcome")
            return False
        
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side.upper(),
            token_id=token_id,
        )
        
        print(f"\n🚀 正在掛單...")
        resp = client.create_and_post_order(order_args)
        
        order_id = resp.orderID if hasattr(resp, 'orderID') else resp.get('orderID', '?')
        
        print(f"\n✅ Limit Order 已提交!")
        print(f"   Order ID: {order_id}")
        print(f"   狀態: 等待成交...")
        
        return True
        
    except Exception as e:
        print(f"❌ 掛單失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_open_orders():
    """列出所有未成交訂單"""
    print(f"\n📋 查詢未成交訂單...")
    
    try:
        client = get_client(with_creds=True)
        orders = client.get_orders()
        
        if not orders:
            print("📭 沒有未成交訂單")
            return
        
        print(f"\n找到 {len(orders)} 個訂單:\n")
        print("="*80)
        
        for i, order in enumerate(orders, 1):
            order_id = order.get('id', '?')[:20]
            side = order.get('side', '?')
            price = order.get('price', 0)
            size = order.get('original_size', order.get('size', 0))
            filled = order.get('size_matched', 0)
            status = order.get('status', '?')
            
            print(f"{i}. [{status}] {side} @ ${price}")
            print(f"   Size: {size} (Filled: {filled})")
            print(f"   ID: {order_id}...")
            print()
        
        print("="*80)
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")


def cancel_order(order_id: str = None, cancel_all: bool = False):
    """取消訂單"""
    try:
        client = get_client(with_creds=True)
        
        if cancel_all:
            print(f"\n🗑️ 取消所有訂單...")
            client.cancel_all()
            print(f"✅ 所有訂單已取消")
        elif order_id:
            print(f"\n🗑️ 取消訂單: {order_id[:20]}...")
            client.cancel(order_id)
            print(f"✅ 訂單已取消")
        else:
            print("❌ 請指定 order_id 或使用 --all")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 取消失敗: {e}")
        return False


# =============================================================================
# TP/SL Functions
# =============================================================================

def load_alerts() -> list:
    """載入 TP/SL 警報"""
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_alerts(alerts: list):
    """儲存警報"""
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)


def set_tp_sl_alert(condition_id: str, outcome: str, alert_type: str,
                    trigger_price: float, shares: float = None):
    """
    設定 TP/SL 警報
    
    Args:
        alert_type: TP (Take Profit) 或 SL (Stop Loss)
        trigger_price: 觸發價格
        shares: 平倉股數 (None = 全部)
    """
    alerts = load_alerts()
    
    # Generate alert ID
    import hashlib
    alert_id = hashlib.md5(
        f"{condition_id}{outcome}{alert_type}{trigger_price}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:8]
    
    alert = {
        "id": alert_id,
        "condition_id": condition_id,
        "outcome": outcome,
        "type": alert_type.upper(),
        "trigger_price": trigger_price,
        "shares": shares,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    alerts.append(alert)
    save_alerts(alerts)
    
    emoji = "🎯" if alert_type.upper() == "TP" else "🛑"
    print(f"\n{emoji} {alert_type.upper()} 警報已設定!")
    print(f"   ID: {alert_id}")
    print(f"   市場: {condition_id[:30]}...")
    print(f"   Outcome: {outcome}")
    print(f"   觸發價格: ${trigger_price:.2f}")
    if shares:
        print(f"   股數: {shares}")
    else:
        print(f"   股數: 全部")
    
    print(f"\n💡 用 `python trade.py monitor` 監控警報")
    
    return alert_id


def list_tp_sl_alerts():
    """列出所有 TP/SL 警報"""
    alerts = load_alerts()
    active = [a for a in alerts if a.get('status') == 'active']
    
    if not active:
        print("📭 沒有活動中嘅警報")
        return
    
    print(f"\n🔔 活動中警報 ({len(active)} 個):")
    print("="*80)
    
    for a in active:
        emoji = "🎯" if a['type'] == "TP" else "🛑"
        shares_str = f"{a['shares']} shares" if a['shares'] else "全部"
        
        print(f"\n{emoji} [{a['id']}] {a['type']}")
        print(f"   市場: {a['condition_id'][:30]}...")
        print(f"   Outcome: {a['outcome']} @ ${a['trigger_price']:.2f}")
        print(f"   股數: {shares_str}")
        print(f"   設定時間: {a['created_at']}")
    
    print("\n" + "="*80)


def remove_tp_sl_alert(alert_id: str = None, all_alerts: bool = False):
    """移除警報"""
    alerts = load_alerts()
    
    if all_alerts:
        save_alerts([])
        print("✅ 所有警報已清除")
        return True
    
    if not alert_id:
        print("❌ 請指定 alert_id 或使用 --all")
        return False
    
    new_alerts = [a for a in alerts if a.get('id') != alert_id]
    
    if len(new_alerts) == len(alerts):
        print(f"❌ 找不到警報: {alert_id}")
        return False
    
    save_alerts(new_alerts)
    print(f"✅ 警報 {alert_id} 已移除")
    return True


def get_current_bid_price(condition_id: str, outcome: str) -> float:
    """獲取當前 Best Bid 價格"""
    orderbook = get_orderbook(condition_id, outcome)
    
    if "error" in orderbook:
        return None
    
    return orderbook.get("best_bid", 0)


def monitor_alerts(interval: int = 30, once: bool = False):
    """
    監控 TP/SL 警報
    
    Args:
        interval: 檢查間隔 (秒)
        once: 只檢查一次
    """
    print(f"\n🔍 開始監控 TP/SL 警報...")
    print(f"   檢查間隔: {interval} 秒")
    print("   按 Ctrl+C 停止\n")
    
    try:
        while True:
            alerts = load_alerts()
            active = [a for a in alerts if a.get('status') == 'active']
            
            if not active:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 沒有活動警報")
                if once:
                    break
                time.sleep(interval)
                continue
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 檢查 {len(active)} 個警報...")
            
            triggered = []
            
            for alert in active:
                current_price = get_current_bid_price(
                    alert['condition_id'], 
                    alert['outcome']
                )
                
                if current_price is None:
                    print(f"   ⚠️ [{alert['id']}] 無法獲取價格")
                    continue
                
                trigger_price = alert['trigger_price']
                should_trigger = False
                
                if alert['type'] == "TP":
                    # Take Profit: trigger when price >= target
                    if current_price >= trigger_price:
                        should_trigger = True
                        print(f"   🎯 [{alert['id']}] TP 觸發! ${current_price:.2f} >= ${trigger_price:.2f}")
                else:
                    # Stop Loss: trigger when price <= target
                    if current_price <= trigger_price:
                        should_trigger = True
                        print(f"   🛑 [{alert['id']}] SL 觸發! ${current_price:.2f} <= ${trigger_price:.2f}")
                
                if should_trigger:
                    triggered.append(alert)
                    # Execute sell
                    print(f"   🚀 正在執行平倉...")
                    success = execute_market_order(
                        alert['condition_id'],
                        alert['outcome'],
                        alert['shares'] if alert['shares'] else 9999,  # Large number = all
                        trade_side="SELL",
                        auto_confirm=True
                    )
                    
                    if success:
                        alert['status'] = 'triggered'
                        alert['triggered_at'] = datetime.now().isoformat()
                        alert['triggered_price'] = current_price
                    else:
                        print(f"   ❌ 平倉失敗!")
                else:
                    print(f"   ⏳ [{alert['id']}] {alert['type']} - 現價 ${current_price:.2f}, 目標 ${trigger_price:.2f}")
            
            # Update alerts
            if triggered:
                save_alerts(alerts)
            
            if once:
                break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 監控已停止")


# =============================================================================
# Main Entry
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Trade Engine - 統一交易入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法範例:
  # 市價單
  python trade.py buy <ID> --outcome Yes --amount 10
  python trade.py sell <ID> --outcome Yes --shares 5
  
  # Limit Order
  python trade.py limit <ID> --outcome Yes --side BUY --price 0.50 --amount 10
  python trade.py limit <ID> --outcome No --side SELL --price 0.60 --shares 5
  
  # 訂單管理
  python trade.py orders              # 查看未成交訂單
  python trade.py cancel <order_id>   # 取消訂單
  python trade.py cancel --all        # 取消所有訂單
  
  # TP/SL
  python trade.py tp <ID> --outcome Yes --price 0.70       # Take Profit
  python trade.py sl <ID> --outcome Yes --price 0.30       # Stop Loss
  python trade.py alerts                                    # 查看警報
  python trade.py monitor                                   # 監控警報
  python trade.py remove <alert_id>                         # 移除警報
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Buy command
    buy_parser = subparsers.add_parser("buy", help="市價買入")
    buy_parser.add_argument("condition_id", help="市場 Condition ID")
    buy_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    buy_parser.add_argument("--amount", "-a", type=float, required=True, help="USDC 金額")
    buy_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    
    # Sell command
    sell_parser = subparsers.add_parser("sell", help="市價賣出")
    sell_parser.add_argument("condition_id", help="市場 Condition ID")
    sell_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    sell_parser.add_argument("--shares", "-s", type=float, required=True, help="股數")
    sell_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    
    # Limit order command
    limit_parser = subparsers.add_parser("limit", help="掛 Limit Order")
    limit_parser.add_argument("condition_id", help="市場 Condition ID")
    limit_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    limit_parser.add_argument("--side", "-S", required=True, choices=["BUY", "SELL"], help="買/賣")
    limit_parser.add_argument("--price", "-p", type=float, required=True, help="掛單價格")
    limit_parser.add_argument("--amount", type=float, help="USDC (BUY 用)")
    limit_parser.add_argument("--shares", type=float, help="股數 (SELL 用)")
    limit_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    
    # Orders command
    subparsers.add_parser("orders", help="查看未成交訂單")
    
    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="取消訂單")
    cancel_parser.add_argument("order_id", nargs="?", help="Order ID")
    cancel_parser.add_argument("--all", action="store_true", help="取消所有")
    
    # TP command
    tp_parser = subparsers.add_parser("tp", help="設定 Take Profit")
    tp_parser.add_argument("condition_id", help="市場 Condition ID")
    tp_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    tp_parser.add_argument("--price", "-p", type=float, required=True, help="觸發價格")
    tp_parser.add_argument("--shares", "-s", type=float, help="股數 (預設全部)")
    
    # SL command
    sl_parser = subparsers.add_parser("sl", help="設定 Stop Loss")
    sl_parser.add_argument("condition_id", help="市場 Condition ID")
    sl_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    sl_parser.add_argument("--price", "-p", type=float, required=True, help="觸發價格")
    sl_parser.add_argument("--shares", "-s", type=float, help="股數 (預設全部)")
    
    # Alerts command
    subparsers.add_parser("alerts", help="查看 TP/SL 警報")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="監控 TP/SL")
    monitor_parser.add_argument("--interval", "-i", type=int, default=30, help="檢查間隔 (秒)")
    monitor_parser.add_argument("--once", action="store_true", help="只檢查一次")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="移除警報")
    remove_parser.add_argument("alert_id", nargs="?", help="Alert ID")
    remove_parser.add_argument("--all", action="store_true", help="移除所有")
    
    args = parser.parse_args()
    
    if args.command == "buy":
        execute_market_order(
            args.condition_id, args.outcome, args.amount,
            trade_side="BUY", auto_confirm=args.auto
        )
    elif args.command == "sell":
        execute_market_order(
            args.condition_id, args.outcome, args.shares,
            trade_side="SELL", auto_confirm=args.auto
        )
    elif args.command == "limit":
        place_limit_order(
            args.condition_id, args.outcome, args.side, args.price,
            size=args.shares, amount=args.amount, auto_confirm=args.auto
        )
    elif args.command == "orders":
        list_open_orders()
    elif args.command == "cancel":
        cancel_order(args.order_id, cancel_all=args.all)
    elif args.command == "tp":
        set_tp_sl_alert(
            args.condition_id, args.outcome, "TP",
            args.price, shares=args.shares
        )
    elif args.command == "sl":
        set_tp_sl_alert(
            args.condition_id, args.outcome, "SL",
            args.price, shares=args.shares
        )
    elif args.command == "alerts":
        list_tp_sl_alerts()
    elif args.command == "monitor":
        monitor_alerts(interval=args.interval, once=args.once)
    elif args.command == "remove":
        remove_tp_sl_alert(args.alert_id, all_alerts=args.all)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
