#!/usr/bin/env python3
"""
Polymarket Take Profit / Stop Loss Monitor
- 監控持倉價格
- 自動觸發平倉
- 支援 TP (Take Profit) 和 SL (Stop Loss)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Store active alerts
ALERTS_FILE = os.path.join(os.path.dirname(__file__), ".tp_sl_alerts.json")


def load_alerts() -> list:
    """載入已設定的警報"""
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []


def save_alerts(alerts: list):
    """儲存警報"""
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)


def get_current_price(condition_id: str, outcome: str) -> float:
    """從 CLOB 獲取當前 Best Bid (賣出價)"""
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
            return 0
        
        ob = client.get_order_book(token_id)
        best_bid = float(ob.bids[0].price) if ob.bids else 0
        
        return best_bid
        
    except Exception as e:
        print(f"   ⚠️ 價格獲取失敗: {e}")
        return 0


def set_alert(condition_id: str, outcome: str, alert_type: str, 
              trigger_price: float, shares: float = None):
    """
    設定 TP/SL 警報
    
    Args:
        condition_id: 市場 ID
        outcome: Yes/No
        alert_type: TP (Take Profit) 或 SL (Stop Loss)
        trigger_price: 觸發價格
        shares: 平倉股數 (None = 全部)
    """
    alerts = load_alerts()
    
    # Check for duplicates
    for a in alerts:
        if a['condition_id'] == condition_id and a['alert_type'] == alert_type:
            print(f"⚠️ 已存在相同的 {alert_type} 警報，將覆蓋...")
            alerts.remove(a)
            break
    
    alert = {
        "id": f"{condition_id[:8]}_{alert_type}_{int(time.time())}",
        "condition_id": condition_id,
        "outcome": outcome,
        "alert_type": alert_type,
        "trigger_price": trigger_price,
        "shares": shares,
        "created_at": datetime.now().isoformat(),
        "triggered": False
    }
    
    alerts.append(alert)
    save_alerts(alerts)
    
    print(f"\n✅ {alert_type} 警報已設定!")
    print(f"   市場: {condition_id[:20]}...")
    print(f"   方向: {outcome}")
    print(f"   觸發價: ${trigger_price:.2f}")
    print(f"   股數: {'全部' if shares is None else shares}")
    print(f"\n💡 執行 `python tp_sl.py monitor` 開始監控")


def list_alerts():
    """列出所有警報"""
    alerts = load_alerts()
    
    if not alerts:
        print("📭 沒有設定任何警報")
        return
    
    active = [a for a in alerts if not a.get('triggered')]
    triggered = [a for a in alerts if a.get('triggered')]
    
    print(f"\n📋 警報列表:")
    print("="*80)
    
    if active:
        print(f"\n🔔 活動中 ({len(active)} 個):")
        for a in active:
            emoji = "🎯" if a['alert_type'] == "TP" else "🛑"
            print(f"   {emoji} [{a['alert_type']}] {a['outcome']} @ ${a['trigger_price']:.2f}")
            print(f"      ID: {a['condition_id'][:20]}...")
            print(f"      設定時間: {a['created_at'][:16]}")
            print()
    
    if triggered:
        print(f"\n✅ 已觸發 ({len(triggered)} 個):")
        for a in triggered:
            print(f"   [{a['alert_type']}] @ ${a['trigger_price']:.2f} - {a.get('triggered_at', '?')}")
    
    print("="*80)


def remove_alert(alert_id: str = None, all_alerts: bool = False):
    """移除警報"""
    alerts = load_alerts()
    
    if all_alerts:
        save_alerts([])
        print("🗑️ 所有警報已清除")
        return
    
    if not alert_id:
        print("❌ 請指定警報 ID 或使用 --all")
        return
    
    new_alerts = [a for a in alerts if not a['id'].startswith(alert_id[:8])]
    
    if len(new_alerts) == len(alerts):
        print(f"❌ 找不到警報: {alert_id}")
    else:
        save_alerts(new_alerts)
        print(f"🗑️ 警報已移除")


def execute_close(condition_id: str, outcome: str, shares: float = None):
    """執行平倉"""
    import subprocess
    
    portfolio_script = os.path.join(os.path.dirname(__file__), "portfolio.py")
    
    cmd = [
        sys.executable, portfolio_script,
        "close", condition_id,
        "--auto"
    ]
    
    if shares:
        cmd.extend(["--shares", str(shares)])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def monitor(interval: int = 30, once: bool = False):
    """
    監控警報並自動執行
    
    Args:
        interval: 檢查間隔 (秒)
        once: 只檢查一次
    """
    print(f"\n🔍 開始監控 TP/SL 警報...")
    print(f"   檢查間隔: {interval} 秒")
    print(f"   按 Ctrl+C 停止\n")
    
    while True:
        alerts = load_alerts()
        active = [a for a in alerts if not a.get('triggered')]
        
        if not active:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📭 沒有活動警報")
            if once:
                return
            time.sleep(interval)
            continue
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 檢查 {len(active)} 個警報...")
        
        for alert in active:
            cid = alert['condition_id']
            outcome = alert['outcome']
            trigger = alert['trigger_price']
            alert_type = alert['alert_type']
            
            current_price = get_current_price(cid, outcome)
            
            if current_price <= 0:
                print(f"   ⚠️ 無法獲取 {cid[:10]}... 價格")
                continue
            
            triggered = False
            
            if alert_type == "TP":
                # Take Profit: 觸發當價格 >= 目標
                if current_price >= trigger:
                    triggered = True
                    print(f"\n   🎯 TP 觸發! {outcome} @ ${current_price:.2f} >= ${trigger:.2f}")
            else:  # SL
                # Stop Loss: 觸發當價格 <= 目標
                if current_price <= trigger:
                    triggered = True
                    print(f"\n   🛑 SL 觸發! {outcome} @ ${current_price:.2f} <= ${trigger:.2f}")
            
            if triggered:
                print(f"   🚀 執行平倉...")
                success = execute_close(cid, outcome, alert.get('shares'))
                
                # Mark as triggered
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                alert['triggered_price'] = current_price
                alert['execution_success'] = success
                save_alerts(alerts)
                
                if success:
                    print(f"   ✅ 平倉成功!")
                else:
                    print(f"   ❌ 平倉失敗，請手動處理")
            else:
                diff = current_price - trigger
                diff_pct = (diff / trigger * 100) if trigger > 0 else 0
                emoji = "📈" if diff > 0 else "📉"
                print(f"   {emoji} {outcome}: ${current_price:.2f} (距離 {alert_type}: {diff_pct:+.1f}%)")
        
        if once:
            return
        
        print()
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Take Profit / Stop Loss Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 設定 Take Profit (價格升到 $0.70 時賣出)
  python tp_sl.py set <ID> --outcome Yes --tp 0.70
  
  # 設定 Stop Loss (價格跌到 $0.30 時止損)
  python tp_sl.py set <ID> --outcome Yes --sl 0.30
  
  # 同時設定 TP 和 SL
  python tp_sl.py set <ID> --outcome Yes --tp 0.70 --sl 0.30
  
  # 列出所有警報
  python tp_sl.py list
  
  # 開始監控
  python tp_sl.py monitor
  
  # 清除所有警報
  python tp_sl.py remove --all
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Set alert
    set_parser = subparsers.add_parser("set", help="設定 TP/SL 警報")
    set_parser.add_argument("condition_id", help="市場 Condition ID")
    set_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    set_parser.add_argument("--tp", type=float, help="Take Profit 價格")
    set_parser.add_argument("--sl", type=float, help="Stop Loss 價格")
    set_parser.add_argument("--shares", "-s", type=float, help="平倉股數 (預設全部)")
    
    # List alerts
    subparsers.add_parser("list", help="列出所有警報")
    
    # Remove alert
    remove_parser = subparsers.add_parser("remove", help="移除警報")
    remove_parser.add_argument("alert_id", nargs="?", help="警報 ID")
    remove_parser.add_argument("--all", action="store_true", help="移除所有")
    
    # Monitor
    monitor_parser = subparsers.add_parser("monitor", help="開始監控")
    monitor_parser.add_argument("--interval", "-i", type=int, default=30, help="檢查間隔 (秒)")
    monitor_parser.add_argument("--once", action="store_true", help="只檢查一次")
    
    args = parser.parse_args()
    
    if args.command == "set":
        if args.tp:
            set_alert(args.condition_id, args.outcome, "TP", args.tp, args.shares)
        if args.sl:
            set_alert(args.condition_id, args.outcome, "SL", args.sl, args.shares)
        if not args.tp and not args.sl:
            print("❌ 請指定 --tp 或 --sl")
    elif args.command == "list":
        list_alerts()
    elif args.command == "remove":
        remove_alert(args.alert_id, args.all)
    elif args.command == "monitor":
        try:
            monitor(args.interval, args.once)
        except KeyboardInterrupt:
            print("\n\n👋 監控已停止")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
