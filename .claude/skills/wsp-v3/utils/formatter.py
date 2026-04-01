#!/usr/bin/env python3
"""
WSP-V3 Formatter — Unified output formatting for all searchers
"""

from datetime import datetime, timezone
from typing import List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Standard search result format."""
    title: str
    url: str
    description: str = ""
    source: str = ""  # "brave", "tavily", "bing"
    metadata: Optional[dict] = None
    timestamp: Optional[datetime] = None


def format_time_ago(ts) -> str:
    """Convert timestamp to 'X hours ago' format."""
    try:
        now = datetime.now(timezone.utc)
        if isinstance(ts, (int, float)):
            post_time = datetime.fromtimestamp(ts, timezone.utc)
        elif isinstance(ts, datetime):
            post_time = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        else:
            return "未知時間"

        seconds = (now - post_time).total_seconds()
        if seconds < 60:
            return f"{int(seconds)} 秒前"
        elif seconds < 3600:
            return f"{int(seconds / 60)} 分鐘前"
        elif seconds < 86400:
            return f"{int(seconds / 3600)} 小時前"
        elif seconds < 604800:
            return f"{int(seconds / 86400)} 天前"
        elif seconds < 2592000:
            return f"{int(seconds / 604800)} 週前"
        else:
            return f"{int(seconds / 2592000)} 月前"
    except Exception:
        return "未知時間"


def get_freshness_name(freshness: str) -> str:
    """Convert freshness code to Chinese description."""
    mapping = {
        "pd": "最近 24 小時",
        "pw": "最近一週",
        "pm": "最近一個月",
        "py": "最近一年",
        "": "所有時間"
    }
    return mapping.get(freshness, freshness)


def print_results(results: List[SearchResult], title: str = "搜尋結果"):
    """Print search results in a consistent format."""
    if not results:
        print("❌ 沒有找到相關結果")
        return

    print(f"✅ 找到 {len(results)} 個結果\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   🔗 {result.url}")
        if result.source:
            print(f"   📡 引擎: {result.source}")
        if result.description:
            desc = result.description[:200] + "..." if len(result.description) > 200 else result.description
            print(f"   📝 {desc}")
        if result.metadata and "age" in result.metadata:
            print(f"   ⏰ {result.metadata['age']}")
        print()
