#!/usr/bin/env python3
"""China Data CLI — 中國市場資料統一入口

Usage:
    uv run scripts/china_data.py stock quote 600519
    uv run scripts/china_data.py stock hist 000001 --days 90
    uv run scripts/china_data.py stock financials 600519
    uv run scripts/china_data.py stock news 600519
    uv run scripts/china_data.py stock top
    uv run scripts/china_data.py macro cpi
    uv run scripts/china_data.py macro ppi
    uv run scripts/china_data.py macro pmi
    uv run scripts/china_data.py macro gdp
    uv run scripts/china_data.py macro m2
    uv run scripts/china_data.py macro fx
    uv run scripts/china_data.py macro rates
    uv run scripts/china_data.py news market
    uv run scripts/china_data.py news flash
    uv run scripts/china_data.py news cctv
    uv run scripts/china_data.py news global
    uv run scripts/china_data.py news search "晶片"
    uv run scripts/china_data.py sentiment xueqiu
    uv run scripts/china_data.py sentiment weibo
    uv run scripts/china_data.py sentiment index
    uv run scripts/china_data.py status
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add scripts dir to path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cmd_stock(args: argparse.Namespace) -> None:
    from sources import stocks
    sub = args.sub
    if sub == "quote":
        if not args.symbol:
            console.print("[red]用法: stock quote <代碼>[/red]")
            sys.exit(1)
        stocks.quote(args.symbol)
    elif sub == "hist":
        if not args.symbol:
            console.print("[red]用法: stock hist <代碼> [--days N] [--csv][/red]")
            sys.exit(1)
        stocks.hist(args.symbol, days=args.days, csv=args.csv)
    elif sub == "financials":
        if not args.symbol:
            console.print("[red]用法: stock financials <代碼>[/red]")
            sys.exit(1)
        stocks.financials(args.symbol)
    elif sub == "news":
        if not args.symbol:
            console.print("[red]用法: stock news <代碼>[/red]")
            sys.exit(1)
        stocks.news(args.symbol, count=args.count)
    elif sub == "top":
        stocks.top()
    else:
        console.print(f"[red]未知 stock 子命令: {sub}[/red]")
        console.print("可用: quote / hist / financials / news / top")
        sys.exit(1)


def cmd_macro(args: argparse.Namespace) -> None:
    from sources import macro
    sub = args.sub
    dispatch = {
        "cpi": macro.cpi,
        "ppi": macro.ppi,
        "pmi": macro.pmi,
        "gdp": macro.gdp,
        "m2": macro.m2,
        "fx": macro.fx,
        "rates": macro.rates,
    }
    fn = dispatch.get(sub)
    if fn is None:
        console.print(f"[red]未知 macro 子命令: {sub}[/red]")
        console.print("可用: cpi / ppi / pmi / gdp / m2 / fx / rates")
        sys.exit(1)
    fn()


def cmd_news(args: argparse.Namespace) -> None:
    from sources import news
    sub = args.sub
    if sub == "market":
        news.market(count=args.count)
    elif sub == "flash":
        news.flash(count=args.count)
    elif sub == "cctv":
        news.cctv(count=args.count)
    elif sub == "global":
        news.global_news(count=args.count)
    elif sub == "search":
        if not args.keyword:
            console.print("[red]用法: news search <關鍵字>[/red]")
            sys.exit(1)
        news.search(args.keyword, count=args.count)
    else:
        console.print(f"[red]未知 news 子命令: {sub}[/red]")
        console.print("可用: market / flash / cctv / global / search")
        sys.exit(1)


def cmd_sentiment(args: argparse.Namespace) -> None:
    from sources import sentiment
    sub = args.sub
    dispatch = {
        "xueqiu": sentiment.xueqiu,
        "weibo": sentiment.weibo,
        "index": sentiment.index,
    }
    fn = dispatch.get(sub)
    if fn is None:
        console.print(f"[red]未知 sentiment 子命令: {sub}[/red]")
        console.print("可用: xueqiu / weibo / index")
        sys.exit(1)
    fn()


def cmd_status(_args: argparse.Namespace) -> None:
    """檢查依賴、市場狀態"""
    table = Table(title="[bold]China Data — 環境狀態[/bold]", show_header=False)
    table.add_column("項目", style="dim")
    table.add_column("狀態", style="bold")

    # Check dependencies
    for pkg, import_name in [
        ("akshare", "akshare"),
        ("baostock", "baostock"),
        ("pandas", "pandas"),
        ("rich", "rich"),
    ]:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "?")
            table.add_row(pkg, f"[green]✓ {ver}[/green]")
        except ImportError:
            table.add_row(pkg, f"[red]✗ 未安裝[/red]")

    # Market hours check
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    total_min = hour * 60 + minute

    # A股: 09:30-11:30, 13:00-15:00 (周一到周五, 北京時間)
    morning = 9 * 60 + 30 <= total_min <= 11 * 60 + 30
    afternoon = 13 * 60 <= total_min <= 15 * 60
    weekday = now.weekday() < 5
    market_open = weekday and (morning or afternoon)

    table.add_row(
        "A股市場",
        f"[green]開市中[/green]" if market_open else f"[dim]休市 (下一交易日開盤: 09:30)[/dim]"
    )
    table.add_row("當前時間 (系統)", now.strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("資料來源", "AKShare (東方財富/新浪財經/雪球) + BaoStock")
    table.add_row("API Key 需求", "[green]無需 API Key (核心功能)[/green]")

    console.print(table)

    console.print(Panel(
        "[bold]快速開始:[/bold]\n"
        "  uv run scripts/china_data.py stock quote 600519   # 茅台即時報價\n"
        "  uv run scripts/china_data.py macro cpi            # 最新 CPI\n"
        "  uv run scripts/china_data.py sentiment index      # 市場情緒\n"
        "  uv run scripts/china_data.py stock top            # 漲跌排行\n\n"
        "[bold]新聞命令:[/bold]\n"
        "  uv run scripts/china_data.py news market          # 東方財富市場要聞\n"
        "  uv run scripts/china_data.py news flash           # 財聯社重大公告\n"
        "  uv run scripts/china_data.py news cctv            # 央視新聞聯播（一般政治/社會）\n"
        "  uv run scripts/china_data.py news global          # 財聯社+東財全球快訊\n"
        '  uv run scripts/china_data.py news search "晶片"   # 跨源關鍵字搜尋',
        title="使用說明",
        border_style="cyan",
    ))


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="china_data",
        description="中國市場資料統一 CLI — A股、宏觀、新聞、情緒",
    )
    subs = p.add_subparsers(dest="cmd")

    # stock
    stock_p = subs.add_parser("stock", help="A/B/H 股行情資料")
    stock_p.add_argument("sub", choices=["quote", "hist", "financials", "news", "top"])
    stock_p.add_argument("symbol", nargs="?", help="股票代碼 (如 600519, 000001, 00700)")
    stock_p.add_argument("--days", type=int, default=90, help="歷史天數 (hist 用, 預設 90)")
    stock_p.add_argument("--csv", action="store_true", help="輸出 CSV 格式 (hist 用)")
    stock_p.add_argument("--count", type=int, default=10, help="新聞條數 (news 用, 預設 10)")

    # macro
    macro_p = subs.add_parser("macro", help="宏觀經濟指標")
    macro_p.add_argument("sub", choices=["cpi", "ppi", "pmi", "gdp", "m2", "fx", "rates"])

    # news
    news_p = subs.add_parser("news", help="財經新聞")
    news_p.add_argument("sub", choices=["market", "flash", "cctv", "global", "search"])
    news_p.add_argument("keyword", nargs="?", help="搜尋關鍵字 (search 用)")
    news_p.add_argument("--count", type=int, default=20, help="新聞條數 (預設 20)")

    # sentiment
    sent_p = subs.add_parser("sentiment", help="市場情緒")
    sent_p.add_argument("sub", choices=["xueqiu", "weibo", "index"])

    # status
    subs.add_parser("status", help="檢查環境與市場狀態")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "stock": cmd_stock,
        "macro": cmd_macro,
        "news": cmd_news,
        "sentiment": cmd_sentiment,
        "status": cmd_status,
    }

    try:
        dispatch[args.cmd](args)
    except KeyboardInterrupt:
        console.print("\n[dim]已中斷[/dim]")
    except Exception as e:
        console.print(f"\n[red]錯誤: {e}[/red]")
        console.print("[dim]如果是 AttributeError，可能是 AKShare API 更新，請執行: uv add akshare --upgrade[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
