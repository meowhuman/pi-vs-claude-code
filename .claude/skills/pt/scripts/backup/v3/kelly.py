#!/usr/bin/env python3
"""
Kelly Criterion Position Sizer
- 計算數學上最優嘅下注金額
- 避免 Over-betting 導致爆倉
- 支援 Full Kelly / Half Kelly / Quarter Kelly
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

DATA_API = "https://data-api.polymarket.com"


def get_current_odds(condition_id: str, outcome: str = "Yes") -> float:
    """獲取當前賠率 (機率)"""
    try:
        resp = requests.get(f"{DATA_API}/markets/{condition_id}", timeout=10)
        if resp.status_code == 200:
            market = resp.json()
            prices = market.get("outcomePrices", "[]")
            if isinstance(prices, str):
                prices = json.loads(prices)
            if prices and len(prices) >= 2:
                if outcome.lower() in ["yes", "y"]:
                    return float(prices[0])
                else:
                    return float(prices[1])
        return 0
    except:
        return 0


def kelly_criterion(win_prob: float, odds: float) -> float:
    """
    Kelly Criterion 公式
    
    f* = (bp - q) / b
    
    其中:
    - f* = 最優下注比例 (佔總資金)
    - b = 淨賠率 (odds - 1，例如賠率 2.0 即 b = 1)
    - p = 勝率 (你估計嘅真實機率)
    - q = 敗率 (1 - p)
    
    對於 Polymarket:
    - 如果你買 Yes @ $0.40，成功獲得 $1，淨賺 $0.60
    - b = (1 - price) / price = 0.60 / 0.40 = 1.5
    """
    if win_prob <= 0 or win_prob >= 1 or odds <= 0 or odds >= 1:
        return 0
    
    # For Polymarket binary outcomes:
    # If you buy at price p, you win (1-p) and lose p
    # b = net_win / stake = (1 - odds) / odds
    b = (1 - odds) / odds
    p = win_prob
    q = 1 - p
    
    # Kelly formula
    f = (b * p - q) / b
    
    return max(0, f)  # Never bet more than you have


def calculate_position(condition_id: str, your_estimate: float, 
                       bankroll: float = None, fraction: float = 1.0,
                       outcome: str = "Yes"):
    """
    計算最優下注金額
    
    Args:
        condition_id: 市場 ID
        your_estimate: 你估計嘅真實機率 (0-1)
        bankroll: 你嘅總資金 (USDC)
        fraction: Kelly 分數 (1.0 = Full, 0.5 = Half, 0.25 = Quarter)
        outcome: Yes/No
    """
    print(f"\n📊 Kelly Criterion 倉位計算器")
    print("="*60)
    
    # Get current market odds
    current_odds = get_current_odds(condition_id, outcome)
    
    if current_odds <= 0:
        print(f"❌ 無法獲取市場價格: {condition_id}")
        return None
    
    print(f"\n📈 市場資訊:")
    print(f"   Condition ID: {condition_id[:20]}...")
    print(f"   Outcome: {outcome}")
    print(f"   當前價格: ${current_odds:.2f} ({current_odds*100:.1f}%)")
    
    print(f"\n🧠 你嘅估計:")
    print(f"   真實機率: {your_estimate*100:.1f}%")
    
    # Calculate edge
    edge = your_estimate - current_odds
    edge_pct = edge * 100
    
    print(f"\n💡 Edge 分析:")
    if edge > 0:
        print(f"   ✅ 正 Edge: +{edge_pct:.1f}% (你認為市場低估咗)")
    elif edge < 0:
        print(f"   ❌ 負 Edge: {edge_pct:.1f}% (你認為市場高估咗)")
        print(f"   ⚠️ 唔建議買入，考慮買另一邊 (No)?")
    else:
        print(f"   ➡️ 零 Edge (市場定價正確)")
    
    # Calculate Kelly
    kelly_f = kelly_criterion(your_estimate, current_odds)
    
    print(f"\n📐 Kelly 公式結果:")
    print(f"   Full Kelly: {kelly_f*100:.1f}% 嘅總資金")
    print(f"   Half Kelly: {kelly_f*50:.1f}% 嘅總資金")
    print(f"   Quarter Kelly: {kelly_f*25:.1f}% 嘅總資金")
    
    # If bankroll provided, calculate exact amount
    if bankroll:
        full_bet = bankroll * kelly_f
        half_bet = bankroll * kelly_f * 0.5
        quarter_bet = bankroll * kelly_f * 0.25
        actual_bet = bankroll * kelly_f * fraction
        
        print(f"\n💰 實際金額 (總資金 ${bankroll:.2f}):")
        print(f"   Full Kelly: ${full_bet:.2f}")
        print(f"   Half Kelly: ${half_bet:.2f}")
        print(f"   Quarter Kelly: ${quarter_bet:.2f}")
        
        if fraction != 1.0:
            print(f"\n   🎯 你選擇嘅 {fraction}x Kelly: ${actual_bet:.2f}")
        
        # Expected value
        ev = actual_bet * (your_estimate * (1/current_odds - 1) - (1 - your_estimate))
        print(f"\n📈 預期價值 (EV):")
        print(f"   如果你嘅估計正確，長期預期回報: ${ev:.2f}")
    
    print("\n" + "="*60)
    
    # Recommendation
    if kelly_f <= 0:
        print("🚫 建議: 唔好落注 (冇正 Edge)")
    elif kelly_f > 0.25:
        print("⚠️ 建議: 用 Quarter Kelly 或更保守，因為 Full Kelly 波動太大")
    else:
        print("✅ 建議: 可以考慮用 Half Kelly 落注")
    
    return {
        "condition_id": condition_id,
        "outcome": outcome,
        "current_odds": current_odds,
        "your_estimate": your_estimate,
        "edge": edge,
        "kelly_fraction": kelly_f,
        "recommended_bet": bankroll * kelly_f * 0.5 if bankroll else None
    }


def interactive_mode():
    """互動模式"""
    print("\n🧮 Kelly Criterion 計算器 (互動模式)")
    print("="*60)
    
    condition_id = input("市場 Condition ID: ").strip()
    outcome = input("Outcome (Yes/No) [Yes]: ").strip() or "Yes"
    
    current_odds = get_current_odds(condition_id, outcome)
    if current_odds > 0:
        print(f"   當前市場價格: ${current_odds:.2f} ({current_odds*100:.1f}%)")
    
    your_estimate = float(input("你估計嘅真實機率 (0-100): ").strip()) / 100
    bankroll = float(input("你嘅總資金 (USDC): ").strip())
    
    calculate_position(condition_id, your_estimate, bankroll, 0.5, outcome)


def main():
    parser = argparse.ArgumentParser(
        description="Kelly Criterion Position Sizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 計算最優倉位 (你認為真實機率係 60%)
  python kelly.py calc "<ID>" --estimate 0.60 --bankroll 100
  
  # 用 Half Kelly (更保守)
  python kelly.py calc "<ID>" --estimate 0.60 --bankroll 100 --fraction 0.5
  
  # 互動模式
  python kelly.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Calculate
    calc_parser = subparsers.add_parser("calc", help="計算倉位")
    calc_parser.add_argument("condition_id", help="市場 Condition ID")
    calc_parser.add_argument("--estimate", "-e", type=float, required=True, 
                             help="你估計嘅真實機率 (0-1)")
    calc_parser.add_argument("--bankroll", "-b", type=float, 
                             help="總資金 (USDC)")
    calc_parser.add_argument("--fraction", "-f", type=float, default=1.0,
                             help="Kelly 分數 (1.0=Full, 0.5=Half)")
    calc_parser.add_argument("--outcome", "-o", default="Yes", help="Outcome")
    
    # Interactive
    subparsers.add_parser("interactive", help="互動模式")
    
    args = parser.parse_args()
    
    if args.command == "calc":
        calculate_position(
            args.condition_id,
            args.estimate,
            args.bankroll,
            args.fraction,
            args.outcome
        )
    elif args.command == "interactive":
        interactive_mode()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
