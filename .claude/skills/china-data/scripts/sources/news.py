"""財經新聞 — 東方財富 + 新浪財經 + 央視 + 財聯社 via AKShare"""
from __future__ import annotations

# 壓制 AKShare 的 tqdm 進度條（必須在 import akshare 之前設置）
import os
os.environ["TQDM_DISABLE"] = "1"

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    ak = None  # type: ignore

from rich.console import Console
from rich.table import Table

console = Console()
logging.getLogger("akshare").setLevel(logging.WARNING)


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


def _fetch_with_timeout(fn, timeout: float = 15.0):
    """帶超時的 API 呼叫，超時返回 None"""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_retry, fn)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            return None
        except Exception:
            return None


# ── Market news ───────────────────────────────────────────────────────────────

def market(count: int = 20) -> None:
    """市場要聞 (東方財富)"""
    _require_ak()
    console.print("[cyan]獲取市場要聞...[/cyan]")

    tried = False

    # 方法 1: 東方財富全球財經快訊
    try:
        df = _retry(lambda: ak.stock_news_em(symbol="000001"))
        # Reuse as general market news
        if df is not None and not df.empty:
            _print_news(df, "東方財富市場要聞", count)
            tried = True
    except Exception:
        pass

    # 方法 2: 新浪財經頭條
    if not tried:
        try:
            today = datetime.now().strftime("%Y%m%d")
            df = _retry(lambda: ak.news_cctv(date=today))
            if df is not None and not df.empty:
                _print_news(df, "新聞聯播要聞", count)
                tried = True
        except Exception as e:
            console.print(f"[yellow]新浪財經備援失敗: {e}[/yellow]")

    if not tried:
        console.print("[red]無法獲取市場要聞，請檢查網路連接或更新 akshare[/red]")


# ── Flash news ────────────────────────────────────────────────────────────────

def flash(count: int = 30) -> None:
    """市場快訊 / 重大公告"""
    _require_ak()
    console.print("[cyan]獲取市場快訊...[/cyan]")

    # 重大事項公告 (symbol="全部", date=今天)
    try:
        today = datetime.now().strftime("%Y%m%d")
        df = _retry(lambda: ak.stock_notice_report(symbol="全部", date=today))
        if df is not None and not df.empty:
            _print_news(df, "滬深京重大事項公告", count)
            return
    except Exception as e:
        console.print(f"[yellow]重大事項獲取失敗: {e}[/yellow]")

    # 備援: 財聯社全球財經快訊
    try:
        df = _retry(lambda: ak.stock_info_global_cls())
        if df is not None and not df.empty:
            _print_news(df, "財聯社全球財經快訊", count)
    except Exception as e:
        console.print(f"[red]快訊獲取失敗: {e}[/red]")


# ── CCTV national news ────────────────────────────────────────────────────────

def cctv(count: int = 20) -> None:
    """央視新聞聯播 — 一般政治/社會/經濟新聞（非純財經）"""
    _require_ak()
    console.print("[cyan]獲取央視新聞聯播...[/cyan]")

    today = datetime.now().strftime("%Y%m%d")
    fetched = False

    # 嘗試今日新聞
    for date_str in [today]:
        try:
            df = _retry(lambda d=date_str: ak.news_cctv(date=d))
            if df is not None and not df.empty:
                _print_news(df, f"央視新聞聯播 {date_str}", count)
                fetched = True
                break
        except Exception as e:
            console.print(f"[yellow]央視新聞獲取失敗 ({date_str}): {e}[/yellow]")

    if not fetched:
        console.print("[red]無法獲取央視新聞，請確認網路連接[/red]")
        console.print("[dim]提示: 新聞聯播通常在晚間更新，白天可能無當日數據[/dim]")


# ── Global financial news ─────────────────────────────────────────────────────

def global_news(count: int = 30) -> None:
    """全球財經快訊 — 財聯社 + 東方財富（美股、歐股、大宗商品動態）"""
    _require_ak()
    console.print("[cyan]獲取全球財經快訊...[/cyan]")

    fetched = False

    # 財聯社全球財經電報（最即時）
    try:
        df = _retry(lambda: ak.stock_info_global_cls())
        if df is not None and not df.empty:
            _print_news(df, "財聯社全球財經電報", count)
            fetched = True
    except Exception as e:
        console.print(f"[yellow]財聯社全球電報失敗: {e}[/yellow]")

    # 東方財富全球財經快訊
    try:
        df = _retry(lambda: ak.stock_info_global_em())
        if df is not None and not df.empty:
            _print_news(df, "東方財富全球財經快訊", count)
            fetched = True
    except Exception as e:
        console.print(f"[yellow]東方財富全球快訊失敗: {e}[/yellow]")

    # 新浪財經全球快訊備援
    try:
        df = _retry(lambda: ak.stock_info_global_sina())
        if df is not None and not df.empty:
            _print_news(df, "新浪財經全球快訊", count)
            fetched = True
    except Exception as e:
        console.print(f"[yellow]新浪全球快訊失敗: {e}[/yellow]")

    if not fetched:
        console.print("[red]全球財經快訊獲取失敗，請更新 akshare: uv add akshare --upgrade[/red]")


# ── Search news ───────────────────────────────────────────────────────────────

def search(keyword: str, count: int = 20) -> None:
    """跨源關鍵字搜尋新聞（標題 + 內容，並行拉取，15秒超時）"""
    _require_ak()
    console.print(f"[cyan]跨源搜尋新聞: 「{keyword}」...[/cyan]")

    def _extract_rows(df, source_name: str) -> list[dict]:
        """從 DataFrame 提取包含關鍵字的行（搜尋標題 + 內容）"""
        if df is None or df.empty:
            return []
        rows = []
        # 標題欄位候選
        title_col = next(
            (c for c in df.columns if "标题" in c or "title" in c.lower()),
            None,
        )
        # 內容欄位候選
        content_col = next(
            (c for c in df.columns if "内容" in c or "内容" in c or "content" in c.lower()),
            None,
        )
        # 時間欄位候選
        time_col = next(
            (c for c in df.columns if "时间" in c or "time" in c.lower() or "date" in c.lower() or "日期" in c),
            None,
        )

        for _, row in df.iterrows():
            title = str(row.get(title_col, "")) if title_col else ""
            content = str(row.get(content_col, "")) if content_col else ""
            if keyword in title or keyword in content:
                display = title if title else (content[:60] + "..." if len(content) > 60 else content)
                rows.append({
                    "來源": source_name,
                    "時間": str(row.get(time_col, ""))[:19] if time_col else "",
                    "標題": display,
                })
        return rows

    # 定義所有源（並行執行，每個 15s 超時）
    sources = [
        ("東方財富", lambda: ak.stock_news_em(symbol="000001")),
        ("財聯社", lambda: ak.stock_info_global_cls()),
        ("央視新聞", lambda: ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))),
    ]

    all_rows: list[dict] = []
    sources_checked = 0

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_fetch_with_timeout, fn, 15.0): name
            for name, fn in sources
        }
        for future in as_completed(futures):
            name = futures[future]
            sources_checked += 1
            try:
                df = future.result()
                if df is not None:
                    rows = _extract_rows(df, name)
                    all_rows.extend(rows)
                    if rows:
                        console.print(f"  [dim]{name}: 找到 {len(rows)} 條[/dim]")
            except Exception:
                pass

    if all_rows:
        # 按時間排序（最新在前）
        all_rows.sort(key=lambda r: r["時間"], reverse=True)
        table = Table(title=f"[bold]跨源搜尋結果 — 「{keyword}」({len(all_rows)} 條)[/bold]")
        table.add_column("來源", style="dim", width=10)
        table.add_column("時間", style="dim", width=19)
        table.add_column("標題", no_wrap=False)
        for row in all_rows[:count]:
            table.add_row(row["來源"], row["時間"], row["標題"])
        console.print(table)
    else:
        console.print(f"[yellow]在 {sources_checked} 個源中未找到「{keyword}」相關內容[/yellow]")
        console.print("[dim]提示: 搜尋基於今日即時數據。非財經/政治關鍵字可改用 WSP-V3[/dim]")

    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_news(df, title: str, count: int) -> None:
    table = Table(title=f"[bold]{title}[/bold]")

    # 動態偵測欄位
    time_cols = ["发布时间", "time", "公告日期", "日期", "datetime", "DATE"]
    title_cols = ["新闻标题", "title", "公告标题", "标题", "TITLE"]
    source_cols = ["文章来源", "source", "来源", "SOURCE"]

    time_col = next((c for c in time_cols if c in df.columns), None)
    title_col = next((c for c in title_cols if c in df.columns), None)
    source_col = next((c for c in source_cols if c in df.columns), None)

    if time_col:
        table.add_column("時間", style="dim", width=20)
    if title_col:
        table.add_column("標題", style="bold", no_wrap=False)
    if source_col:
        table.add_column("來源", style="dim", width=12)

    if not title_col:
        # 顯示全部欄位
        for col in df.columns:
            table.add_column(str(col))
        for _, row in df.head(count).iterrows():
            table.add_row(*[str(v) for v in row])
    else:
        for _, row in df.head(count).iterrows():
            vals = []
            if time_col:
                vals.append(str(row.get(time_col, "")))
            if title_col:
                vals.append(str(row.get(title_col, "")))
            if source_col:
                vals.append(str(row.get(source_col, "")))
            table.add_row(*vals)

    console.print(table)
    console.print(f"[dim]資料時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
