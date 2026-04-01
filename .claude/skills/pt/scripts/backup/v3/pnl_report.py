#!/usr/bin/env python3
"""
Polymarket Historical P&L Report Generator
- 完整交易歷史
- 勝率統計
- 盈虧分析
- Markdown 報表輸出
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DATA_API = "https://data-api.polymarket.com"


def fetch_trade_history(wallet_address: str, limit: int = 1000) -> list:
    """獲取交易歷史"""
    trades = []
    offset = 0
    
    print(f"📥 正在獲取交易歷史...", file=sys.stderr)
    
    while True:
        try:
            resp = requests.get(
                f"{DATA_API}/trades",
                params={"maker": wallet_address, "limit": min(limit, 500), "offset": offset},
                timeout=15
            )
            if resp.status_code != 200:
                break
            
            data = resp.json()
            if not data:
                break
            
            trades.extend(data)
            print(f"   已獲取 {len(trades)} 筆...", file=sys.stderr)
            
            if len(data) < 500 or len(trades) >= limit:
                break
            
            offset += 500
            
        except Exception as e:
            print(f"   ⚠️ 錯誤: {e}", file=sys.stderr)
            break
    
    return trades


def analyze_trades(trades: list) -> dict:
    """分析交易數據"""
    if not trades:
        return {}
    
    # Group by market
    markets = defaultdict(lambda: {
        "buys": [],
        "sells": [],
        "total_cost": 0,
        "total_revenue": 0,
        "shares_bought": 0,
        "shares_sold": 0,
        "outcomes": set()
    })
    
    total_volume = 0
    total_trades = len(trades)
    
    for trade in trades:
        market_id = trade.get("market", trade.get("conditionId", "?"))
        title = trade.get("title", "Unknown")[:50]
        side = trade.get("side", "?").upper()
        outcome = trade.get("outcome", "?")
        size = float(trade.get("size", 0))
        price = float(trade.get("price", 0))
        value = size * price
        
        total_volume += value
        markets[market_id]["title"] = title
        markets[market_id]["outcomes"].add(outcome)
        
        if side == "BUY":
            markets[market_id]["buys"].append(trade)
            markets[market_id]["total_cost"] += value
            markets[market_id]["shares_bought"] += size
        else:
            markets[market_id]["sells"].append(trade)
            markets[market_id]["total_revenue"] += value
            markets[market_id]["shares_sold"] += size
    
    # Calculate P&L per market
    market_pnl = []
    for mid, data in markets.items():
        realized_pnl = data["total_revenue"] - data["total_cost"]
        net_shares = data["shares_bought"] - data["shares_sold"]
        
        market_pnl.append({
            "market_id": mid,
            "title": data.get("title", "?"),
            "outcomes": list(data["outcomes"]),
            "trades": len(data["buys"]) + len(data["sells"]),
            "total_cost": round(data["total_cost"], 2),
            "total_revenue": round(data["total_revenue"], 2),
            "realized_pnl": round(realized_pnl, 2),
            "net_shares": round(net_shares, 2),
            "is_closed": net_shares < 0.01
        })
    
    market_pnl.sort(key=lambda x: x["realized_pnl"], reverse=True)
    
    # Overall stats
    total_realized_pnl = sum(m["realized_pnl"] for m in market_pnl if m["is_closed"])
    winners = [m for m in market_pnl if m["is_closed"] and m["realized_pnl"] > 0]
    losers = [m for m in market_pnl if m["is_closed"] and m["realized_pnl"] < 0]
    
    win_rate = len(winners) / (len(winners) + len(losers)) * 100 if (winners or losers) else 0
    
    return {
        "total_trades": total_trades,
        "total_volume": round(total_volume, 2),
        "unique_markets": len(markets),
        "closed_positions": len([m for m in market_pnl if m["is_closed"]]),
        "open_positions": len([m for m in market_pnl if not m["is_closed"]]),
        "total_realized_pnl": round(total_realized_pnl, 2),
        "win_rate": round(win_rate, 1),
        "winners": len(winners),
        "losers": len(losers),
        "best_trade": market_pnl[0] if market_pnl else None,
        "worst_trade": market_pnl[-1] if market_pnl else None,
        "markets": market_pnl
    }


def generate_report(wallet_address: str, output_file: str = None, 
                    limit: int = 1000, json_output: bool = False):
    """生成報表"""
    trades = fetch_trade_history(wallet_address, limit)
    
    if not trades:
        print("📭 沒有交易記錄")
        return
    
    analysis = analyze_trades(trades)
    
    if json_output:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        return
    
    # Generate Markdown report
    lines = []
    lines.append(f"# 📊 Polymarket 交易報表")
    lines.append(f"")
    lines.append(f"**錢包**: `{wallet_address}`")
    lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    
    lines.append(f"## 📈 總體統計")
    lines.append(f"")
    lines.append(f"| 指標 | 數值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 總交易次數 | {analysis['total_trades']} |")
    lines.append(f"| 總交易量 | ${analysis['total_volume']:,.2f} |")
    lines.append(f"| 不同市場 | {analysis['unique_markets']} |")
    lines.append(f"| 已平倉 | {analysis['closed_positions']} |")
    lines.append(f"| 未平倉 | {analysis['open_positions']} |")
    lines.append(f"")
    
    lines.append(f"## 💰 盈虧分析")
    lines.append(f"")
    pnl_emoji = "📈" if analysis['total_realized_pnl'] >= 0 else "📉"
    lines.append(f"- **已實現盈虧**: {pnl_emoji} ${analysis['total_realized_pnl']:+,.2f}")
    lines.append(f"- **勝率**: {analysis['win_rate']:.1f}% ({analysis['winners']}W / {analysis['losers']}L)")
    lines.append(f"")
    
    if analysis['best_trade']:
        lines.append(f"### 🏆 最佳交易")
        lines.append(f"- **{analysis['best_trade']['title']}...**")
        lines.append(f"- P&L: +${analysis['best_trade']['realized_pnl']:.2f}")
        lines.append(f"")
    
    if analysis['worst_trade'] and analysis['worst_trade']['realized_pnl'] < 0:
        lines.append(f"### 💔 最差交易")
        lines.append(f"- **{analysis['worst_trade']['title']}...**")
        lines.append(f"- P&L: ${analysis['worst_trade']['realized_pnl']:.2f}")
        lines.append(f"")
    
    lines.append(f"## 📋 市場明細 (Top 10)")
    lines.append(f"")
    lines.append(f"| 市場 | 交易數 | 成本 | 收入 | P&L | 狀態 |")
    lines.append(f"|------|--------|------|------|-----|------|")
    
    for m in analysis['markets'][:10]:
        status = "✅" if m['is_closed'] else "🔓"
        pnl_str = f"+${m['realized_pnl']:.2f}" if m['realized_pnl'] >= 0 else f"${m['realized_pnl']:.2f}"
        lines.append(f"| {m['title'][:30]}... | {m['trades']} | ${m['total_cost']:.2f} | ${m['total_revenue']:.2f} | {pnl_str} | {status} |")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*Generated by Polymarket Trader v3.0*")
    
    report = "\n".join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"💾 報表已保存: {output_file}")
    else:
        print(report)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Historical P&L Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 生成報表 (預設錢包)
  python pnl_report.py
  
  # 指定錢包
  python pnl_report.py --wallet 0x...
  
  # 輸出到檔案
  python pnl_report.py --output report.md
  
  # JSON 格式
  python pnl_report.py --json
        """
    )
    
    parser.add_argument("--wallet", "-w", help="錢包地址")
    parser.add_argument("--output", "-o", help="輸出檔案 (Markdown)")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="最大交易數")
    parser.add_argument("--json", action="store_true", help="JSON 輸出")
    
    args = parser.parse_args()
    
    wallet = args.wallet or os.getenv("BUILDER_WALLET_ADDRESS") or os.getenv("WALLET_ADDRESS")
    
    if not wallet:
        print("❌ 請指定錢包地址或設定環境變數")
        sys.exit(1)
    
    generate_report(wallet, args.output, args.limit, args.json)


if __name__ == "__main__":
    main()
