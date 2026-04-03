"""A股、B股、H股行情資料 — AKShare + BaoStock"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None  # type: ignore

try:
    import baostock as bs
except ImportError:
    bs = None  # type: ignore

from rich.console import Console
from rich.table import Table

console = Console()


def _require_ak() -> None:
    if ak is None:
        raise ImportError("akshare not installed. Run: uv sync")


def _require_bs() -> None:
    if bs is None:
        raise ImportError("baostock not installed. Run: uv sync")


def _retry(fn, retries: int = 2, delay: float = 2.0):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(delay)


# ── Realtime quote ──────────────────────────────────────────────────────────

def quote(symbol: str) -> None:
    """即時報價 (東方財富源)"""
    _require_ak()
    symbol = symbol.upper()

    # Detect market: HK stocks have .HK suffix or 5-digit starting with 0/2/3/6/8
    if symbol.endswith(".HK") or (symbol.isdigit() and len(symbol) == 5):
        _quote_hk(symbol.replace(".HK", ""))
    else:
        _quote_a(symbol)


def _quote_a(symbol: str) -> None:
    df = _retry(lambda: ak.stock_zh_a_spot_em())
    row = df[df["代码"] == symbol]
    if row.empty:
        console.print(f"[red]找不到股票代碼: {symbol}[/red]")
        return

    r = row.iloc[0]
    table = Table(title=f"[bold cyan]{r['名称']} ({symbol})[/bold cyan]", show_header=False)
    table.add_column("指標", style="dim")
    table.add_column("數值", style="bold")

    fields = [
        ("最新價", "最新价"), ("漲跌幅", "涨跌幅"), ("漲跌額", "涨跌额"),
        ("成交量(手)", "成交量"), ("成交額", "成交额"),
        ("今開", "今开"), ("昨收", "昨收"), ("最高", "最高"), ("最低", "最低"),
        ("市盈率(動)", "市盈率-动态"), ("市淨率", "市净率"), ("總市值", "总市值"),
    ]
    for label, col in fields:
        if col in r.index:
            val = r[col]
            color = ""
            if col == "涨跌幅" and isinstance(val, (int, float)):
                color = "red" if val > 0 else "green"
                val = f"[{color}]{val:.2f}%[/{color}]" if color else str(val)
            table.add_row(label, str(val))

    console.print(table)
    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


def _quote_hk(symbol: str) -> None:
    df = _retry(lambda: ak.stock_hk_spot_em())
    row = df[df["代码"] == symbol]
    if row.empty:
        console.print(f"[red]找不到港股代碼: {symbol}[/red]")
        return

    r = row.iloc[0]
    table = Table(title=f"[bold cyan]{r.get('名称', symbol)} ({symbol}.HK)[/bold cyan]", show_header=False)
    table.add_column("指標", style="dim")
    table.add_column("數值", style="bold")

    for col in r.index:
        table.add_row(col, str(r[col]))

    console.print(table)
    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


# ── Historical OHLCV ────────────────────────────────────────────────────────

def hist(symbol: str, days: int = 90, csv: bool = False) -> None:
    """歷史 OHLCV (後復權)"""
    _require_ak()
    end = datetime.now()
    start = end - timedelta(days=days)

    try:
        df = _retry(lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="hfq",
        ))
    except AttributeError:
        console.print("[yellow]AKShare API 名稱可能已更新，嘗試 BaoStock 備援...[/yellow]")
        _hist_baostock(symbol, days, csv)
        return

    if df is None or df.empty:
        console.print(f"[red]無法取得 {symbol} 歷史資料[/red]")
        return

    if csv:
        print(df.to_csv(index=False))
        return

    table = Table(title=f"[bold]{symbol} 歷史行情 (後復權, 近{days}天)[/bold]")
    for col in df.columns[:8]:  # 顯示主要欄位
        table.add_column(str(col), justify="right")

    for _, row in df.tail(20).iterrows():
        table.add_row(*[str(v) for v in list(row)[:8]])

    console.print(table)
    console.print(f"[dim]共 {len(df)} 筆，顯示最近 20 筆[/dim]")


def _hist_baostock(symbol: str, days: int, csv: bool) -> None:
    _require_bs()
    bs.login()
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        # BaoStock format: sh.600519 / sz.000001
        prefix = "sh" if symbol.startswith("6") else "sz"
        code = f"{prefix}.{symbol}"

        rs = bs.query_history_k_data_plus(
            code,
            "date,open,high,low,close,volume,amount,adjustflag",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d",
            adjustflag="2",  # 後復權
        )
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())

        df = pd.DataFrame(rows, columns=rs.fields)
        if csv:
            print(df.to_csv(index=False))
        else:
            console.print(df.tail(20).to_string())
    finally:
        bs.logout()


# ── Financial statements ─────────────────────────────────────────────────────

def financials(symbol: str) -> None:
    """財務報表摘要 (新浪財經源)"""
    _require_ak()

    console.print(f"[cyan]正在獲取 {symbol} 財務資料...[/cyan]")

    try:
        # 利潤表
        df_income = _retry(lambda: ak.stock_profit_sheet_by_yearly_em(symbol=symbol))
        if df_income is not None and not df_income.empty:
            table = Table(title=f"[bold]{symbol} 利潤表 (近4年)[/bold]")
            for col in df_income.columns:
                table.add_column(str(col), justify="right")
            for _, row in df_income.head(4).iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)
    except Exception as e:
        console.print(f"[yellow]利潤表獲取失敗: {e}[/yellow]")

    try:
        # 資產負債表
        df_balance = _retry(lambda: ak.stock_balance_sheet_by_yearly_em(symbol=symbol))
        if df_balance is not None and not df_balance.empty:
            table = Table(title=f"[bold]{symbol} 資產負債表 (近4年)[/bold]")
            for col in df_balance.columns:
                table.add_column(str(col), justify="right")
            for _, row in df_balance.head(4).iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)
    except Exception as e:
        console.print(f"[yellow]資產負債表獲取失敗: {e}[/yellow]")


# ── Stock news ───────────────────────────────────────────────────────────────

def news(symbol: str, count: int = 10) -> None:
    """個股相關新聞 (東方財富源)"""
    _require_ak()

    try:
        df = _retry(lambda: ak.stock_news_em(symbol=symbol))
    except AttributeError:
        console.print("[red]AKShare stock_news_em API 不可用，請更新: uv add akshare --upgrade[/red]")
        return

    if df is None or df.empty:
        console.print(f"[yellow]{symbol} 暫無新聞[/yellow]")
        return

    table = Table(title=f"[bold]{symbol} 相關新聞[/bold]")
    table.add_column("時間", style="dim", width=20)
    table.add_column("標題", style="bold")
    table.add_column("來源", style="dim", width=12)

    for _, row in df.head(count).iterrows():
        time_val = str(row.get("发布时间", row.get("time", "")))
        title = str(row.get("新闻标题", row.get("title", "")))
        source = str(row.get("文章来源", row.get("source", "")))
        table.add_row(time_val, title, source)

    console.print(table)


# ── Top movers ───────────────────────────────────────────────────────────────

def top(market: str = "A") -> None:
    """漲跌幅排行榜"""
    _require_ak()

    console.print("[cyan]正在獲取漲跌排行...[/cyan]")

    try:
        df = _retry(lambda: ak.stock_zh_a_spot_em())
        df["涨跌幅"] = pd.to_numeric(df["涨跌幅"], errors="coerce")

        gainers = df.nlargest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]
        losers = df.nsmallest(10, "涨跌幅")[["代码", "名称", "最新价", "涨跌幅", "成交额"]]

        table_g = Table(title="[bold red]漲幅榜 Top 10[/bold red]")
        for col in gainers.columns:
            table_g.add_column(col, justify="right")
        for _, row in gainers.iterrows():
            pct = float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else 0
            color = "red" if pct > 0 else "green"
            table_g.add_row(
                str(row["代码"]), str(row["名称"]),
                str(row["最新价"]),
                f"[{color}]{pct:.2f}%[/{color}]",
                str(row["成交额"]),
            )
        console.print(table_g)

        table_l = Table(title="[bold green]跌幅榜 Top 10[/bold green]")
        for col in losers.columns:
            table_l.add_column(col, justify="right")
        for _, row in losers.iterrows():
            pct = float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else 0
            color = "red" if pct > 0 else "green"
            table_l.add_row(
                str(row["代码"]), str(row["名称"]),
                str(row["最新价"]),
                f"[{color}]{pct:.2f}%[/{color}]",
                str(row["成交额"]),
            )
        console.print(table_l)

    except Exception as e:
        console.print(f"[red]排行榜獲取失敗: {e}[/red]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
