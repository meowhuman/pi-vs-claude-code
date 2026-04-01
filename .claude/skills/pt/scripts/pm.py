#!/usr/bin/env python3
"""
Polymarket Portfolio Manager (PM) - 統一持倉管理入口
整合: portfolio.py, get_positions.py, rebalance.py, pnl_report.py

用法:
    python pm.py                    # 儀表板
    python pm.py close <ID>         # 平倉
    python pm.py rebalance          # 再平衡
    python pm.py report             # P&L 報表
    python pm.py liquidity <ID>     # 檢查流動性
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.client import get_client, get_api_urls, get_wallets, get_available_accounts, get_account_config
from utils.positions import get_all_positions, get_positions_by_condition, parse_position
from utils.market import get_orderbook, get_market_info
from utils.cash import get_cash_balances

load_dotenv()

# Global account ID (can be overridden by CLI)
CURRENT_ACCOUNT_ID = 1


# =============================================================================
# Dashboard Functions
# =============================================================================

def show_dashboard(json_output: bool = False, account_id: int = 1):
    """顯示持倉儀表板"""
    # Get account info
    try:
        account_config = get_account_config(account_id)
        account_name = f"Account #{account_id}"
    except ValueError as e:
        print(f"❌ {e}")
        return None
    
    all_positions = get_all_positions()
    cash_data = get_cash_balances(account_id)
    
    processed = []
    if all_positions:
        for p in all_positions:
            parsed = parse_position(p)
            # If slug is missing, try to fetch it
            if not parsed.get('slug') and not parsed.get('event_slug'):
                m_info = get_market_info(parsed['condition_id'])
                if m_info:
                    parsed['slug'] = m_info.get('slug', '')
                    parsed['event_slug'] = m_info.get('eventSlug', m_info.get('event_slug', ''))
            processed.append(parsed)
        processed.sort(key=lambda x: x['value'], reverse=True)
    
    total_positions_value = sum(p['value'] for p in processed)
    total_cost = sum(p['cost'] for p in processed)
    
    total_cash = 0
    if isinstance(cash_data, dict) and "error" not in cash_data:
        total_cash = sum(c['usdc'] for c in cash_data.values())
    
    total_portfolio_value = total_positions_value + total_cash
    
    if json_output:
        result = {
            "account_id": account_id,
            "account_name": account_name,
            "builder_wallet": account_config["builder_wallet"],
            "timestamp": datetime.now().isoformat(),
            "positions": processed,
            "cash": cash_data,
            "summary": {
                "total_positions": len(processed),
                "total_cost": round(total_cost, 2),
                "total_positions_value": round(total_positions_value, 2),
                "total_cash": round(total_cash, 2),
                "total_portfolio_value": round(total_portfolio_value, 2),
                "total_pnl": round(total_positions_value - total_cost, 2)
            }
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return processed
    
    # Terminal output
    print("\n" + "="*100)
    print(f"📊 POLYMARKET 持倉儀表板 - {account_name}")
    print(f"💼 Builder Wallet: {account_config['builder_wallet'][:10]}...{account_config['builder_wallet'][-8:]}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    if not processed:
        print("\n📭 冇任何持倉")
    else:
        for i, p in enumerate(processed, 1):
            pnl_emoji = "🟢" if p['pnl'] >= 0 else "🔴"
            pnl_sign = "+" if p['pnl'] >= 0 else ""
            
            # Construct Link
            link = ""
            if p['slug']:
                link = f"https://polymarket.com/market/{p['slug']}"
            elif p['event_slug']:
                link = f"https://polymarket.com/event/{p['event_slug']}"
            
            print(f"\n{i}. {p['market_name']}")
            print(f"   💼 {p['wallet_type']} | {p['outcome']} | {p['shares']} shares")
            print(f"   💰 成本: ${p['cost']:.2f} (@ ${p['avg_price']:.2f}) → 現值: ${p['value']:.2f} (@ ${p['current_price']:.2f})")
            print(f"   {pnl_emoji} 盈虧: {pnl_sign}${p['pnl']:.2f} ({pnl_sign}{p['pnl_pct']:.1f}%)")
            print(f"   📋 ID: {p['condition_id']}")
            if link:
                print(f"   🔗 連結: {link}")
    
    print("\n" + "="*100)
    print("💵 現金餘額:")
    if isinstance(cash_data, dict) and "error" not in cash_data:
        for name, data in cash_data.items():
            print(f"   • {name.capitalize()}: ${data['usdc']:.2f} USDC | {data['matic']:.4f} MATIC")
    else:
        print(f"   ⚠️ 無法獲取現金餘額: {cash_data.get('error', 'Unknown error')}")
    
    print("\n" + "="*100)
    total_pnl = total_positions_value - total_cost
    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
    pnl_sign = "+" if total_pnl >= 0 else ""
    
    print(f"🏆 投資組合總結:")
    print(f"   • 持倉市值:   ${total_positions_value:,.2f}")
    print(f"   • 現金餘額:   ${total_cash:,.2f}")
    print(f"   • 組合總值:   ${total_portfolio_value:,.2f}")
    print(f"   {pnl_emoji} 持倉盈虧:   {pnl_sign}${total_pnl:,.2f} ({pnl_sign}{((total_pnl/total_cost*100) if total_cost > 0 else 0):.1f}%)")
    print("="*100 + "\n")
    
    return processed


# =============================================================================
# Close Position Functions
# =============================================================================

def close_position(condition_id: str, outcome: str = None, shares: float = None, 
                   auto_confirm: bool = False, limit_price: float = None):
    """平倉指定市場 (附流動性檢查)"""
    print(f"\n🔄 準備平倉: {condition_id[:30]}...")
    
    # Find position
    positions = get_positions_by_condition(condition_id)
    
    if not positions:
        print(f"❌ 找不到持倉: {condition_id}")
        return False
    
    target_position = positions[0]
    parsed = parse_position(target_position)
    
    pos_outcome = parsed['outcome']
    pos_shares = parsed['shares']
    
    if outcome and outcome.upper() != pos_outcome.upper():
        print(f"❌ Outcome 不匹配: 你揸住 {pos_outcome}，但你指定 {outcome}")
        return False
    
    sell_shares = shares if shares else pos_shares
    if sell_shares > pos_shares:
        print(f"❌ 你只有 {pos_shares} shares，不能賣 {sell_shares}")
        return False
    
    # Liquidity check
    print(f"\n📊 檢查流動性...")
    orderbook = get_orderbook(condition_id, pos_outcome)
    
    if "error" in orderbook:
        print(f"   ⚠️ 無法獲取 orderbook: {orderbook['error']}")
        best_bid = parsed['current_price']
        spread_warning = True
    else:
        best_bid = orderbook.get("best_bid", 0)
        best_ask = orderbook.get("best_ask", 0)
        spread_pct = orderbook.get("spread_pct", 0)
        
        print(f"   Best Bid: ${best_bid:.2f} | Best Ask: ${best_ask:.2f}")
        print(f"   Spread: {spread_pct:.1f}%")
        
        spread_warning = spread_pct and spread_pct > 20
    
    # Price comparison warning
    if best_bid < parsed['current_price'] * 0.5:
        print(f"\n   🚨 嚴重警告: Best Bid (${best_bid:.2f}) 遠低於顯示價格 (${parsed['current_price']:.2f})!")
        spread_warning = True
    
    estimated_value = sell_shares * best_bid
    
    print(f"\n📊 平倉詳情:")
    print(f"   市場: {parsed['market_name']}")
    print(f"   方向: {pos_outcome}")
    print(f"   賣出: {sell_shares:.2f} shares")
    print(f"   Best Bid: ${best_bid:.2f}")
    print(f"   預計收入: ${estimated_value:.2f}")
    
    # Confirmation
    if spread_warning and not auto_confirm:
        print(f"\n   ⚠️ 流動性警告! 建議用 Limit Order 掛單。")
        print(f"   用法: python pm.py close \"{condition_id}\" --limit 0.50")
        confirm = input(f"\n⚠️ 是否仍以市價平倉? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    elif not auto_confirm:
        confirm = input(f"\n確認平倉? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    
    # Execute via trade.py
    print(f"\n🚀 正在執行平倉...")
    
    import subprocess
    trade_script = os.path.join(os.path.dirname(__file__), "trade.py")
    
    # Check if trade.py exists, fallback to execute_trade.py
    if not os.path.exists(trade_script):
        trade_script = os.path.join(os.path.dirname(__file__), "execute_trade.py")
    
    cmd = [
        sys.executable, trade_script,
        "sell" if os.path.basename(trade_script) == "trade.py" else "--market-id", 
    ]
    
    # Build command based on script
    if os.path.basename(trade_script) == "trade.py":
        cmd = [
            sys.executable, trade_script,
            "sell", condition_id,
            "--outcome", pos_outcome,
            "--shares", str(sell_shares),
            "--auto"
        ]
    else:
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
    print(f"\n📊 檢查流動性: {condition_id[:30]}...")
    
    # Get Market Info for name and link
    m_info = get_market_info(condition_id)
    market_name = m_info.get("question", m_info.get("title", "Unknown Market"))
    slug = m_info.get("slug", "")
    event_slug = m_info.get("eventSlug", m_info.get("event_slug", ""))
    
    orderbook = get_orderbook(condition_id, outcome)
    
    if "error" in orderbook:
        print(f"❌ 無法獲取 orderbook: {orderbook['error']}")
        return None
    
    # Construct Link
    link = ""
    if slug:
        link = f"https://polymarket.com/market/{slug}"
    elif event_slug:
        link = f"https://polymarket.com/event/{event_slug}"

    print(f"\n   市場: {market_name}")
    print(f"   Outcome: {outcome}")
    print(f"   Best Bid: ${orderbook['best_bid']:.2f} ({orderbook['bid_size']:.0f} shares)")
    print(f"   Best Ask: ${orderbook['best_ask']:.2f} ({orderbook['ask_size']:.0f} shares)")
    print(f"   Spread: ${orderbook['spread']:.4f} ({orderbook['spread_pct']:.1f}%)")
    print(f"   📋 ID: {condition_id}")
    if link:
        print(f"   🔗 連結: {link}")
    
    if orderbook['spread_pct'] > 20:
        print(f"\n   🚨 警告: Spread 超過 20%，流動性差!")
    elif orderbook['spread_pct'] > 10:
        print(f"\n   ⚠️ 注意: Spread 偏大 ({orderbook['spread_pct']:.1f}%)")
    else:
        print(f"\n   ✅ 流動性正常")
    
    return orderbook


# =============================================================================
# P&L Report Functions
# =============================================================================

def pnl_report(json_output: bool = False, detailed: bool = False):
    """生成 P&L 報表"""
    all_positions = get_all_positions()
    
    if not all_positions:
        print("📭 冇任何持倉，無法生成報表")
        return None
    
    processed = [parse_position(p) for p in all_positions]
    
    # Group by wallet type
    by_wallet = {}
    for p in processed:
        wt = p['wallet_type']
        if wt not in by_wallet:
            by_wallet[wt] = []
        by_wallet[wt].append(p)
    
    # Calculate summaries
    report = {
        "generated_at": datetime.now().isoformat(),
        "wallets": {},
        "total": {
            "cost": 0,
            "value": 0,
            "pnl": 0,
            "positions": 0
        }
    }
    
    for wt, positions in by_wallet.items():
        wallet_cost = sum(p['cost'] for p in positions)
        wallet_value = sum(p['value'] for p in positions)
        wallet_pnl = wallet_value - wallet_cost
        
        report["wallets"][wt] = {
            "cost": round(wallet_cost, 2),
            "value": round(wallet_value, 2),
            "pnl": round(wallet_pnl, 2),
            "pnl_pct": round((wallet_pnl / wallet_cost * 100) if wallet_cost > 0 else 0, 1),
            "positions": len(positions)
        }
        
        if detailed:
            report["wallets"][wt]["details"] = positions
        
        report["total"]["cost"] += wallet_cost
        report["total"]["value"] += wallet_value
        report["total"]["pnl"] += wallet_pnl
        report["total"]["positions"] += len(positions)
    
    report["total"]["pnl_pct"] = round(
        (report["total"]["pnl"] / report["total"]["cost"] * 100) 
        if report["total"]["cost"] > 0 else 0, 1
    )
    
    if json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report
    
    # Terminal output
    print("\n" + "="*80)
    print("📈 POLYMARKET P&L 報表")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    for wt, data in report["wallets"].items():
        pnl_emoji = "🟢" if data['pnl'] >= 0 else "🔴"
        pnl_sign = "+" if data['pnl'] >= 0 else ""
        
        print(f"\n💼 {wt} Wallet")
        print(f"   持倉數: {data['positions']}")
        print(f"   成本: ${data['cost']:.2f}")
        print(f"   現值: ${data['value']:.2f}")
        print(f"   {pnl_emoji} 盈虧: {pnl_sign}${data['pnl']:.2f} ({pnl_sign}{data['pnl_pct']:.1f}%)")
    
    print("\n" + "-"*80)
    total = report["total"]
    pnl_emoji = "📈" if total['pnl'] >= 0 else "📉"
    pnl_sign = "+" if total['pnl'] >= 0 else ""
    
    print(f"\n🏆 總計:")
    print(f"   持倉數: {total['positions']}")
    print(f"   總成本: ${total['cost']:.2f}")
    print(f"   總現值: ${total['value']:.2f}")
    print(f"   {pnl_emoji} 總盈虧: {pnl_sign}${total['pnl']:.2f} ({pnl_sign}{total['pnl_pct']:.1f}%)")
    print("="*80 + "\n")
    
    return report


# =============================================================================
# Rebalance Functions
# =============================================================================

def rebalance(target_allocation: dict = None, auto_confirm: bool = False):
    """
    Portfolio 再平衡 (簡化版)
    
    Args:
        target_allocation: Dict of {condition_id: target_pct}
        auto_confirm: Skip confirmation
    """
    all_positions = get_all_positions()
    
    if not all_positions:
        print("📭 冇任何持倉")
        return
    
    processed = [parse_position(p) for p in all_positions]
    total_value = sum(p['value'] for p in processed)
    
    print("\n" + "="*80)
    print("🔄 PORTFOLIO 再平衡分析")
    print("="*80)
    
    print(f"\n📊 目前配置:")
    for p in sorted(processed, key=lambda x: x['value'], reverse=True):
        pct = (p['value'] / total_value * 100) if total_value > 0 else 0
        print(f"   {p['market_name'][:40]}...")
        print(f"   💰 ${p['value']:.2f} ({pct:.1f}%)")
        print()
    
    # Simple equal-weight suggestion
    equal_pct = 100 / len(processed) if processed else 0
    equal_value = total_value / len(processed) if processed else 0
    
    print(f"\n💡 等權重建議 (每個持倉 {equal_pct:.1f}%):")
    for p in processed:
        current_pct = (p['value'] / total_value * 100) if total_value > 0 else 0
        diff = current_pct - equal_pct
        
        if abs(diff) > 5:
            action = "減持" if diff > 0 else "加倉"
            emoji = "🔻" if diff > 0 else "🔺"
            print(f"   {emoji} {p['market_name'][:30]}... - {action} ${abs(p['value'] - equal_value):.2f}")
    
    print("\n" + "="*80)
    print("ℹ️  手動執行建議的交易:")
    print("   python trade.py buy <ID> --amount 10")
    print("   python trade.py sell <ID> --shares 5")
    print("="*80 + "\n")


# =============================================================================
# Main Entry
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Portfolio Manager (PM) - 統一持倉管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法範例:
  python pm.py                         # 顯示持倉儀表板
  python pm.py --json                  # JSON 格式輸出
  python pm.py close <ID>              # 平倉 (附流動性檢查)
  python pm.py close <ID> --auto       # 自動確認平倉
  python pm.py liquidity <ID>          # 檢查流動性
  python pm.py report                  # P&L 報表
  python pm.py report --detailed       # 詳細 P&L 報表
  python pm.py rebalance               # 再平衡建議
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
    
    # Liquidity check
    liq_parser = subparsers.add_parser("liquidity", help="檢查市場流動性")
    liq_parser.add_argument("condition_id", help="市場 Condition ID")
    liq_parser.add_argument("--outcome", "-o", default="Yes", help="Outcome (Yes/No)")
    
    # Report
    report_parser = subparsers.add_parser("report", help="P&L 報表")
    report_parser.add_argument("--json", action="store_true", help="JSON 格式")
    report_parser.add_argument("--detailed", "-d", action="store_true", help="包含詳細持倉")
    
    # Rebalance
    rebal_parser = subparsers.add_parser("rebalance", help="再平衡建議")
    rebal_parser.add_argument("--auto", "-y", action="store_true", help="自動執行")
    
    # Accounts list
    subparsers.add_parser("accounts", help="列出所有已配置的帳戶")
    
    # Global options
    parser.add_argument("--json", action="store_true", help="JSON 格式輸出")
    parser.add_argument("--account", "-a", type=int, default=1, 
                        help="帳戶編號 (預設: 1)")
    
    args = parser.parse_args()
    
    # Handle accounts list command
    if args.command == "accounts":
        available = get_available_accounts()
        print("\n" + "="*60)
        print("💼 已配置的帳戶")
        print("="*60)
        
        if not available:
            print("\n❌ 沒有找到任何已配置的帳戶")
            print("\n請在 .env 中配置:")
            print("  POLYGON_PRIVATE_KEY=xxx")
            print("  BUILDER_WALLET_ADDRESS=0x...")
        else:
            for acc_id in available:
                try:
                    config = get_account_config(acc_id)
                    print(f"\n✅ Account #{acc_id}")
                    print(f"   Builder: {config['builder_wallet'][:10]}...{config['builder_wallet'][-8:]}")
                    if config['wallet_address'] != config['builder_wallet']:
                        print(f"   Control: {config['wallet_address'][:10]}...{config['wallet_address'][-8:]}")
                except Exception as e:
                    print(f"\n❌ Account #{acc_id}: {e}")
        
        print("\n" + "="*60)
        print(f"\n用法: python pm.py --account 2")
        print("="*60 + "\n")
        return
    
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
    elif args.command == "report":
        pnl_report(json_output=args.json, detailed=args.detailed)
    elif args.command == "rebalance":
        rebalance(auto_confirm=args.auto)
    else:
        show_dashboard(json_output=args.json, account_id=args.account)


if __name__ == "__main__":
    main()
