"""中國宏觀經濟資料 — NBS (國家統計局) + PBOC (人民銀行) via AKShare"""
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


def _print_table(title: str, df, max_rows: int = 24) -> None:
    if df is None or df.empty:
        console.print(f"[yellow]{title}: 無資料[/yellow]")
        return
    table = Table(title=f"[bold]{title}[/bold]")
    for col in df.columns:
        table.add_column(str(col), justify="right")
    for _, row in df.tail(max_rows).iterrows():
        table.add_row(*[str(v) for v in row])
    console.print(table)
    console.print(f"[dim]共 {len(df)} 筆，顯示最近 {min(max_rows, len(df))} 筆[/dim]")


# ── CPI ─────────────────────────────────────────────────────────────────────

def cpi() -> None:
    """消費者物價指數 (月度)"""
    _require_ak()
    console.print("[cyan]獲取 CPI 資料 (NBS)...[/cyan]")
    try:
        df = _retry(lambda: ak.macro_china_cpi_monthly())
        _print_table("中國 CPI 月度 (同比/環比)", df)
    except AttributeError:
        console.print("[red]API 名稱已更新，嘗試備用...[/red]")
        try:
            df = _retry(lambda: ak.macro_china_cpi())
            _print_table("中國 CPI", df)
        except Exception as e2:
            console.print(f"[red]CPI 獲取失敗: {e2}[/red]")
    except Exception as e:
        console.print(f"[red]CPI 獲取失敗: {e}[/red]")


# ── PPI ─────────────────────────────────────────────────────────────────────

def ppi() -> None:
    """工業生產者出廠價格指數 (月度)"""
    _require_ak()
    console.print("[cyan]獲取 PPI 資料 (NBS)...[/cyan]")
    try:
        df = _retry(lambda: ak.macro_china_ppi_monthly())
        _print_table("中國 PPI 月度", df)
    except AttributeError:
        try:
            df = _retry(lambda: ak.macro_china_ppi())
            _print_table("中國 PPI", df)
        except Exception as e2:
            console.print(f"[red]PPI 獲取失敗: {e2}[/red]")
    except Exception as e:
        console.print(f"[red]PPI 獲取失敗: {e}[/red]")


# ── PMI ─────────────────────────────────────────────────────────────────────

def pmi() -> None:
    """採購經理人指數 (製造業 + 服務業)"""
    _require_ak()
    console.print("[cyan]獲取 PMI 資料 (NBS)...[/cyan]")

    # 製造業 PMI
    try:
        df_mfg = _retry(lambda: ak.macro_china_pmi_yearly())
        _print_table("中國製造業 PMI", df_mfg)
    except Exception as e:
        console.print(f"[yellow]製造業 PMI 獲取失敗: {e}[/yellow]")

    # 非製造業 PMI
    try:
        df_svc = _retry(lambda: ak.macro_china_non_man_pmi())
        _print_table("中國非製造業 PMI", df_svc)
    except Exception as e:
        console.print(f"[yellow]非製造業 PMI 獲取失敗: {e}[/yellow]")

    # 財新 PMI
    try:
        df_cx = _retry(lambda: ak.macro_china_cx_pmi_yearly())
        _print_table("財新製造業 PMI", df_cx)
    except Exception as e:
        console.print(f"[yellow]財新 PMI 獲取失敗: {e}[/yellow]")


# ── GDP ─────────────────────────────────────────────────────────────────────

def gdp() -> None:
    """國內生產總值 (季度)"""
    _require_ak()
    console.print("[cyan]獲取 GDP 資料 (NBS)...[/cyan]")
    try:
        df = _retry(lambda: ak.macro_china_gdp_yearly())
        _print_table("中國 GDP (季度/年度)", df, max_rows=20)
    except Exception as e:
        console.print(f"[red]GDP 獲取失敗: {e}[/red]")


# ── M2 貨幣供應 ──────────────────────────────────────────────────────────────

def m2() -> None:
    """廣義貨幣供應量 M2 (PBOC)"""
    _require_ak()
    console.print("[cyan]獲取 M2 資料 (PBOC)...[/cyan]")
    try:
        df = _retry(lambda: ak.macro_china_money_supply())
        _print_table("中國貨幣供應量 (M0/M1/M2)", df)
    except Exception as e:
        console.print(f"[red]M2 獲取失敗: {e}[/red]")


# ── 外匯 ─────────────────────────────────────────────────────────────────────

def fx() -> None:
    """外匯儲備 + 人民幣匯率"""
    _require_ak()
    console.print("[cyan]獲取外匯資料...[/cyan]")

    # 外匯儲備
    try:
        df_reserve = _retry(lambda: ak.macro_china_fx_reserves_yearly())
        _print_table("中國外匯儲備 (億美元)", df_reserve, max_rows=24)
    except Exception as e:
        console.print(f"[yellow]外匯儲備獲取失敗: {e}[/yellow]")

    # 人民幣中間價
    try:
        df_rmb = _retry(lambda: ak.currency_boc_safe())
        _print_table("人民幣匯率中間價 (國家外匯管理局)", df_rmb, max_rows=10)
    except Exception as e:
        console.print(f"[yellow]人民幣匯率獲取失敗: {e}[/yellow]")


# ── 利率 ─────────────────────────────────────────────────────────────────────

def rates() -> None:
    """貸款市場報價利率 (LPR) + SHIBOR"""
    _require_ak()
    console.print("[cyan]獲取利率資料 (PBOC)...[/cyan]")

    # LPR
    try:
        df_lpr = _retry(lambda: ak.macro_china_lpr())
        _print_table("貸款市場報價利率 LPR", df_lpr, max_rows=24)
    except Exception as e:
        console.print(f"[yellow]LPR 獲取失敗: {e}[/yellow]")

    # SHIBOR
    try:
        df_shibor = _retry(lambda: ak.macro_china_shibor_all())
        _print_table("上海銀行間同業拆放利率 SHIBOR", df_shibor, max_rows=10)
    except Exception as e:
        console.print(f"[yellow]SHIBOR 獲取失敗: {e}[/yellow]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
