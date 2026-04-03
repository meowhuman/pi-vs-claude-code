"""市場情緒資料 — 雪球熱榜 + 微博熱搜 + 市場情緒指數 via AKShare"""
from __future__ import annotations

import time
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    ak = None  # type: ignore

from rich.console import Console
from rich.table import Table

console = Console()


def _require_ak() -> None:
    if ak is None:
        raise ImportError("akshare not installed. Run: uv sync")


def _retry(fn, retries: int = 2, delay: float = 2.0):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(delay)


# ── Xueqiu (雪球) ─────────────────────────────────────────────────────────────

def xueqiu() -> None:
    """雪球熱門股票討論榜"""
    _require_ak()
    console.print("[cyan]獲取雪球熱門榜...[/cyan]")

    # 東方財富人氣榜 (代替雪球，更穩定)
    tried = False
    try:
        df = _retry(lambda: ak.stock_hot_rank_em())
        if df is not None and not df.empty:
            table = Table(title="[bold]東方財富人氣榜 (實時)[/bold]")
            for col in df.columns[:6]:
                table.add_column(str(col), justify="right")
            for _, row in df.head(20).iterrows():
                table.add_row(*[str(v) for v in list(row)[:6]])
            console.print(table)
            tried = True
    except Exception as e:
        console.print(f"[yellow]東方財富人氣榜失敗: {e}[/yellow]")

    # 雪球熱門追蹤股票
    try:
        df_xq = _retry(lambda: ak.stock_hot_follow_xq(symbol="最热门"))
        if df_xq is not None and not df_xq.empty:
            table = Table(title="[bold]雪球最熱門追蹤股票[/bold]")
            for col in df_xq.columns[:6]:
                table.add_column(str(col), justify="right")
            for _, row in df_xq.head(20).iterrows():
                table.add_row(*[str(v) for v in list(row)[:6]])
            console.print(table)
            tried = True
    except Exception as e:
        console.print(f"[yellow]雪球熱門榜失敗: {e}[/yellow]")

    if not tried:
        console.print("[red]熱門榜資料獲取失敗，請更新 akshare: uv add akshare --upgrade[/red]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


# ── Weibo hot search ──────────────────────────────────────────────────────────

def weibo() -> None:
    """微博財經熱搜"""
    _require_ak()
    console.print("[cyan]獲取微博財經熱搜...[/cyan]")

    # 財經關鍵字過濾
    finance_keywords = [
        "股市", "A股", "港股", "美股", "基金", "理財", "經濟", "貨幣", "利率",
        "通脹", "GDP", "美聯儲", "人民幣", "匯率", "大盤", "牛市", "熊市",
        "IPO", "ETF", "期貨", "黃金", "原油", "比特幣", "加密", "財報",
        "央行", "降息", "加息", "CPI", "PMI", "貿易", "關稅",
    ]

    # 微博財經報告 (stock_js_weibo_report)
    try:
        df = _retry(lambda: ak.stock_js_weibo_report(time_period="CNHOUR12"))
        if df is not None and not df.empty:
            table_all = Table(title="[bold]微博財經熱點 (近12小時)[/bold]")
            for col in df.columns[:5]:
                table_all.add_column(str(col), justify="right")
            for _, row in df.head(20).iterrows():
                table_all.add_row(*[str(v) for v in list(row)[:5]])
            console.print(table_all)

            # 財經相關過濾
            title_col = next((c for c in df.columns if "名" in c or "title" in c.lower() or "word" in c.lower()), None)
            if title_col:
                mask = df[title_col].astype(str).apply(
                    lambda x: any(kw in x for kw in finance_keywords)
                )
                df_finance = df[mask]
                if not df_finance.empty:
                    table_fin = Table(title="[bold yellow]財經關鍵詞熱點[/bold yellow]")
                    for col in df_finance.columns[:5]:
                        table_fin.add_column(str(col), justify="right")
                    for _, row in df_finance.iterrows():
                        table_fin.add_row(*[str(v) for v in list(row)[:5]])
                    console.print(table_fin)
        return
    except Exception as e:
        console.print(f"[yellow]微博財經報告失敗: {e}[/yellow]")

    # 備援: 微博 NLP 時序
    try:
        df2 = _retry(lambda: ak.stock_js_weibo_nlp_time())
        if df2 is not None and not df2.empty:
            table_all = Table(title="[bold]微博財經 NLP 情緒[/bold]")
            for col in df2.columns[:5]:
                table_all.add_column(str(col), justify="right")
            for _, row in df2.head(20).iterrows():
                table_all.add_row(*[str(v) for v in list(row)[:5]])
            console.print(table_all)
    except Exception as e:
        console.print(f"[red]微博資料獲取失敗: {e}[/red]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


# ── Market sentiment index ────────────────────────────────────────────────────

def index() -> None:
    """市場情緒指數 (恐懼貪婪、市場活躍度)"""
    _require_ak()
    console.print("[cyan]獲取市場情緒指數...[/cyan]")

    # A股市場活躍度
    try:
        df = _retry(lambda: ak.stock_market_activity_legu())
        if df is not None and not df.empty:
            table = Table(title="[bold]樂咕樂股市場情緒[/bold]")
            for col in df.columns:
                table.add_column(str(col), justify="right")
            for _, row in df.iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)
    except Exception as e:
        console.print(f"[yellow]市場活躍度獲取失敗: {e}[/yellow]")

    # 北向資金匯總 (外資情緒)
    try:
        df_north = _retry(lambda: ak.stock_hsgt_fund_flow_summary_em())
        if df_north is not None and not df_north.empty:
            table = Table(title="[bold]滬深港通北向資金匯總[/bold]")
            for col in df_north.columns[:6]:
                table.add_column(str(col), justify="right")
            for _, row in df_north.head(10).iterrows():
                table.add_row(*[str(v) for v in list(row)[:6]])
            console.print(table)
    except Exception as e:
        console.print(f"[yellow]北向資金獲取失敗: {e}[/yellow]")

    # 漲跌統計 (市場廣度)
    try:
        df_spot = _retry(lambda: ak.stock_zh_a_spot_em())
        if df_spot is not None and not df_spot.empty:
            import pandas as pd
            df_spot["涨跌幅_num"] = pd.to_numeric(df_spot["涨跌幅"], errors="coerce")
            up = (df_spot["涨跌幅_num"] > 0).sum()
            down = (df_spot["涨跌幅_num"] < 0).sum()
            flat = (df_spot["涨跌幅_num"] == 0).sum()
            limit_up = (df_spot["涨跌幅_num"] >= 9.9).sum()
            limit_down = (df_spot["涨跌幅_num"] <= -9.9).sum()

            table = Table(title="[bold]A股市場廣度[/bold]", show_header=False)
            table.add_column("指標", style="dim")
            table.add_column("數值", style="bold")
            table.add_row("上漲家數", f"[red]{up}[/red]")
            table.add_row("下跌家數", f"[green]{down}[/green]")
            table.add_row("平盤家數", str(flat))
            table.add_row("漲停家數", f"[bold red]{limit_up}[/bold red]")
            table.add_row("跌停家數", f"[bold green]{limit_down}[/bold green]")
            if up + down > 0:
                ratio = up / (up + down) * 100
                color = "red" if ratio > 50 else "green"
                table.add_row("上漲比率", f"[{color}]{ratio:.1f}%[/{color}]")
            console.print(table)
    except Exception as e:
        console.print(f"[yellow]市場廣度統計失敗: {e}[/yellow]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
