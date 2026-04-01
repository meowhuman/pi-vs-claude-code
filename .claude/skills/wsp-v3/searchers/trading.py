#!/usr/bin/env python3
"""
WSP-V3 Trading Searcher — StockTwits, Bitcointalk, 4chan /biz/

Replaces: search_stocktwits.py, search_bitcointalk.py, search_4chan_biz.py
"""

import sys
import logging
from typing import List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.brave import BraveEngine
from engines.tavily import TavilyEngine
from utils.formatter import SearchResult, print_results

logger = logging.getLogger("wsp-v3")

TRADING_FORUMS = {
    "stocktwits": {"name": "StockTwits", "emoji": "📈", "domain": "stocktwits.com"},
    "bitcointalk": {"name": "Bitcointalk", "emoji": "₿", "domain": "bitcointalk.org"},
    "4chan_biz": {"name": "4chan /biz/", "emoji": "🐸", "domain": "boards.4chan.org/biz"},
    "xueqiu": {"name": "雪球 (Xueqiu)", "emoji": "⚪", "domain": "xueqiu.com"},
}


def search_trading(
    query: str,
    forum: str = "all",
    freshness: str = "pw",
    count: int = 15,
) -> List[SearchResult]:
    """Search trading-specific forums."""
    if forum != "all" and forum not in TRADING_FORUMS:
        print(f"❌ 未知交易論壇: {forum}")
        print(f"可用: {', '.join(TRADING_FORUMS.keys())}")
        return []

    if forum == "all":
        targets = list(TRADING_FORUMS.items())
        print(f"📊 交易論壇搜尋: {query}")
    else:
        targets = [(forum, TRADING_FORUMS[forum])]
        info = TRADING_FORUMS[forum]
        print(f"{info['emoji']} {info['name']} 搜尋: {query}")

    print("=" * 80)
    print()

    all_results = []
    brave = BraveEngine()
    tavily = TavilyEngine()

    for forum_key, info in targets:
        domain = info["domain"]
        search_query = f"site:{domain} {query}"
        results = []

        if brave.available:
            results = brave.web_search(search_query, count=count // max(len(targets), 1), freshness=freshness)
            results = [r for r in results if domain.split("/")[0] in r.url]

        if not results and tavily.available:
            try:
                results = tavily.search(search_query, max_results=count // max(len(targets), 1))
                results = [r for r in results if domain.split("/")[0] in r.url]
            except Exception:
                pass

        all_results.extend(results)

    print_results(all_results[:count], "交易論壇")
    return all_results[:count]
