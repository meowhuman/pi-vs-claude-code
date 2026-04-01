#!/usr/bin/env python3
"""
Polymarket Portfolio Rebalancer
- 檢查倉位偏離度
- 計算再平衡交易
- 自動執行再平衡
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_API = "https://data-api.polymarket.com"


def get_wallet_positions(wallet_address: str) -> list:
    """獲取錢包持倉"""
    try:
        resp = requests.get(f"{DATA_API}/positions", params={"user": wallet_address}, timeout=15)
        if resp.status_code == 200:
            positions = resp.json()
            return [p for p in positions if float(p.get("size", p.get("shares", 0))) > 0.001]
        return []
    except:
        return []


def analyze_portfolio(max_position_pct: float = 20.0):
    """
    分析投資組合並找出需要再平衡嘅倉位
    
    Args:
        max_position_pct: 單一倉位最大佔比 (%)
    """
    control_wallet = os.getenv("WALLET_ADDRESS")
    builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
    
    all_positions = []
    for wallet in [control_wallet, builder_wallet]:
        if wallet:
            all_positions.extend(get_wallet_positions(wallet))
    
    if not all_positions:
        print("📭 沒有持倉")
        return None
    
    # Calculate total value
    positions = []
    total_value = 0
    
    for pos in all_positions:
        market_info = pos.get("market", {})
        if isinstance(market_info, dict):
            market_name = market_info.get("question", pos.get("title", "?"))[:40]
            condition_id = market_info.get("conditionId", pos.get("conditionId", "?"))
        else:
            market_name = pos.get("title", "?")[:40]
            condition_id = pos.get("conditionId", "?")
        
        outcome = pos.get("outcome", pos.get("side", "?"))
        shares = float(pos.get("size", pos.get("shares", 0)))
        cur_price = float(pos.get("curPrice", pos.get("current_price", 0)))
        value = shares * cur_price
        
        total_value += value
        positions.append({
            "condition_id": condition_id,
            "market_name": market_name,
            "outcome": outcome,
            "shares": shares,
            "price": cur_price,
            "value": value
        })
    
    # Calculate weights and deviations
    print(f"\n📊 投資組合再平衡分析")
    print("="*80)
    print(f"\n💰 總持倉價值: ${total_value:.2f}")
    print(f"📏 最大單一倉位: {max_position_pct}%")
    print(f"📋 持倉數量: {len(positions)}")
    
    # Target: equal weight or max cap
    target_weight = min(100 / len(positions), max_position_pct) / 100
    target_value = total_value * target_weight
    
    print(f"\n🎯 目標權重: {target_weight*100:.1f}% (${target_value:.2f})")
    
    # Check each position
    overweight = []
    underweight = []
    balanced = []
    
    print(f"\n📋 倉位分析:")
    print("-"*80)
    
    for p in positions:
        weight = p["value"] / total_value if total_value > 0 else 0
        deviation = (weight - target_weight) / target_weight * 100 if target_weight > 0 else 0
        
        p["weight"] = weight
        p["target_weight"] = target_weight
        p["deviation"] = deviation
        
        if weight > max_position_pct / 100:
            status = "🔴 超重"
            excess_value = p["value"] - target_value
            p["action"] = "SELL"
            p["action_value"] = excess_value
            overweight.append(p)
        elif weight < target_weight * 0.8:  # 20% below target
            status = "🟡 偏輕"
            deficit_value = target_value - p["value"]
            p["action"] = "BUY"
            p["action_value"] = deficit_value
            underweight.append(p)
        else:
            status = "🟢 正常"
            p["action"] = None
            balanced.append(p)
        
        print(f"   {status} {p['market_name']}...")
        print(f"      {p['outcome']} | ${p['value']:.2f} ({weight*100:.1f}%) | 偏離: {deviation:+.1f}%")
    
    print("-"*80)
    
    # Summary
    print(f"\n📊 總結:")
    print(f"   🔴 超重倉位: {len(overweight)}")
    print(f"   🟡 偏輕倉位: {len(underweight)}")
    print(f"   🟢 正常倉位: {len(balanced)}")
    
    if overweight:
        print(f"\n⚠️ 需要減倉嘅市場:")
        for p in overweight:
            print(f"   • {p['market_name']}... → 賣出 ${p['action_value']:.2f}")
    
    if underweight:
        print(f"\n💡 可以加倉嘅市場:")
        for p in underweight:
            print(f"   • {p['market_name']}... → 買入 ${p['action_value']:.2f}")
    
    print("="*80)
    
    return {
        "total_value": total_value,
        "target_weight": target_weight,
        "positions": positions,
        "overweight": overweight,
        "underweight": underweight,
        "balanced": balanced
    }


def execute_rebalance(max_position_pct: float = 20.0, auto_confirm: bool = False):
    """執行再平衡"""
    import subprocess
    
    analysis = analyze_portfolio(max_position_pct)
    
    if not analysis:
        return
    
    if not analysis["overweight"]:
        print("\n✅ 投資組合已平衡，無需操作")
        return
    
    if not auto_confirm:
        print(f"\n⚠️ 將執行以下再平衡操作:")
        for p in analysis["overweight"]:
            print(f"   SELL {p['outcome']} @ {p['market_name'][:30]}... (${p['action_value']:.2f})")
        
        confirm = input("\n確認執行? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return
    
    # Execute sells for overweight positions
    portfolio_script = os.path.join(os.path.dirname(__file__), "portfolio.py")
    
    for p in analysis["overweight"]:
        shares_to_sell = p["action_value"] / p["price"] if p["price"] > 0 else 0
        
        print(f"\n🔄 賣出 {shares_to_sell:.2f} shares of {p['market_name'][:30]}...")
        
        cmd = [
            sys.executable, portfolio_script,
            "close", p["condition_id"],
            "--shares", str(round(shares_to_sell, 2)),
            "--auto"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"   ✅ 成功")
            else:
                print(f"   ❌ 失敗")
                print(result.stdout)
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
    
    print("\n🎯 再平衡完成！")


def set_allocation(allocations: dict, total_usdc: float = None):
    """
    設定目標配置
    
    Args:
        allocations: {"condition_id": weight, ...}
        total_usdc: 總資金
    """
    print(f"\n🎯 目標配置:")
    print("="*60)
    
    total_weight = sum(allocations.values())
    if abs(total_weight - 1.0) > 0.01:
        print(f"⚠️ 權重總和 {total_weight*100:.1f}% ≠ 100%")
    
    for cid, weight in allocations.items():
        target_value = total_usdc * weight if total_usdc else 0
        print(f"   {cid[:20]}... → {weight*100:.1f}%", end="")
        if total_usdc:
            print(f" (${target_value:.2f})")
        else:
            print()
    
    print("="*60)
    print("\n💡 執行: python rebalance.py execute --max-position 20")


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Portfolio Rebalancer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 分析當前組合 (預設最大 20%)
  python rebalance.py analyze
  
  # 設定最大單一倉位 10%
  python rebalance.py analyze --max-position 10
  
  # 執行再平衡
  python rebalance.py execute --max-position 20
  
  # 自動執行 (唔問)
  python rebalance.py execute --max-position 20 --auto
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Analyze
    analyze_parser = subparsers.add_parser("analyze", help="分析組合")
    analyze_parser.add_argument("--max-position", "-m", type=float, default=20.0,
                                help="最大單一倉位 %% (預設 20)")
    
    # Execute
    execute_parser = subparsers.add_parser("execute", help="執行再平衡")
    execute_parser.add_argument("--max-position", "-m", type=float, default=20.0,
                                help="最大單一倉位 %%")
    execute_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        analyze_portfolio(args.max_position)
    elif args.command == "execute":
        execute_rebalance(args.max_position, args.auto)
    else:
        # Default: analyze
        analyze_portfolio(20.0)


if __name__ == "__main__":
    main()
