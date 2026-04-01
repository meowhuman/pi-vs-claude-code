#!/usr/bin/env python3
"""
WSP-V3 China Searcher — Improved Chinese mainland search

V2 Problem:
  Only used site: queries via Brave/Tavily, which poorly index Chinese content
  behind the GFW (Great Firewall).

V3 Improvement:
  1. Bing API as primary (Microsoft indexes Chinese sites much better)
  2. Tavily as secondary
  3. Brave as last resort
  4. Clear documentation of limitations

Supported forums:
  知乎 (Zhihu), 微博 (Weibo), 百度贴吧 (Tieba), 小红书 (Xiaohongshu),
  雪球 (Xueqiu), 豆瓣 (Douban)
"""

import sys
import logging
from typing import List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.brave import BraveEngine
from engines.tavily import TavilyEngine
from engines.bing import BingEngine
from utils.formatter import SearchResult, print_results

logger = logging.getLogger("wsp-v3")


CHINA_FORUMS = {
    "zhihu": {"name": "知乎", "emoji": "🔵", "domain": "zhihu.com", "desc": "問答社區", "bing_ok": True},
    "weibo": {"name": "微博", "emoji": "🔴", "domain": "weibo.com", "desc": "社交媒體", "bing_ok": True},
    "tieba": {"name": "百度贴吧", "emoji": "🟢", "domain": "tieba.baidu.com", "desc": "論壇社區", "bing_ok": True},
    "xiaohongshu": {"name": "小红书", "emoji": "📕", "domain": "xiaohongshu.com", "desc": "生活分享", "bing_ok": False},
    "xueqiu": {"name": "雪球", "emoji": "⚪", "domain": "xueqiu.com", "desc": "投資社區", "bing_ok": True},
    "douban": {"name": "豆瓣", "emoji": "🟤", "domain": "douban.com", "desc": "文化社區", "bing_ok": True},
    "bilibili": {"name": "B站", "emoji": "🔵", "domain": "bilibili.com", "desc": "影視社區", "bing_ok": True},
    "toutiao": {"name": "頭條", "emoji": "🔴", "domain": "toutiao.com", "desc": "新聞聚合", "bing_ok": True},
}


def search_china(
    query: str,
    forum: str = "all",
    freshness: str = "pw",
    count: int = 20,
) -> List[SearchResult]:
    """
    Search Chinese forums with multi-engine strategy.

    Engine priority:
    1. Bing (best for Chinese content)
    2. Tavily (OK for some Chinese sites)
    3. Brave (worst for Chinese, last resort)
    """
    if forum != "all" and forum not in CHINA_FORUMS:
        print(f"❌ 未知論壇: {forum}")
        list_china_forums()
        return []

    # Determine which forums to search
    if forum == "all":
        targets = list(CHINA_FORUMS.items())
        forum_name = "所有大陸論壇"
    else:
        targets = [(forum, CHINA_FORUMS[forum])]
        info = CHINA_FORUMS[forum]
        forum_name = f"{info['emoji']} {info['name']} — {info['desc']}"

    print(f"🇨🇳 中國大陸搜尋")
    print(f"💬 關鍵字: {query}")
    print(f"📂 論壇: {forum_name}")
    print("=" * 80)
    print()

    all_results = []

    # Try engines in order of Chinese content quality
    bing = BingEngine()
    tavily = TavilyEngine()
    brave = BraveEngine()

    for forum_key, info in targets:
        domain = info["domain"]
        search_query = f"site:{domain} {query}"

        results = []

        # 1. Bing (best for Chinese)
        if bing.available and info.get("bing_ok", True):
            results = bing.web_search(search_query, count=count // max(len(targets), 1), market="zh-CN", freshness=freshness)
            results = [r for r in results if domain in r.url]

        # 2. Tavily fallback
        if not results and tavily.available:
            try:
                results = tavily.search(search_query, max_results=count // max(len(targets), 1))
                results = [r for r in results if domain in r.url]
            except Exception:
                pass

        # 3. Brave last resort
        if not results and brave.available:
            results = brave.web_search(search_query, count=count // max(len(targets), 1), freshness=freshness)
            results = [r for r in results if domain in r.url]

        if results:
            print(f"{info['emoji']} {info['name']}: 找到 {len(results)} 個結果")
        all_results.extend(results)

    print()
    print_results(all_results[:count], "中國搜尋結果")
    return all_results[:count]


def search_xueqiu(
    query: str,
    count: int = 20,
    freshness: str = "pw",
) -> List[SearchResult]:
    """Xueqiu (雪球) specific search for investment content."""
    print(f"⚪ 雪球 (Xueqiu) — 投資社區")
    return search_china(query, forum="xueqiu", freshness=freshness, count=count)


def list_china_forums():
    """List supported Chinese forums with search effectiveness."""
    print("🇨🇳 中國大陸論壇列表\n")
    print("=" * 60)
    print(f"{'論壇':10s} {'名稱':8s} {'域名':25s} {'Bing':5s}")
    print("-" * 60)
    for key, info in CHINA_FORUMS.items():
        bing_status = "✅" if info.get("bing_ok") else "⚠️"
        print(f"{info['emoji']} {key:10s} {info['name']:6s}  {info['domain']:25s} {bing_status}")
    print("=" * 60)
    print()
    print("⚠️ 搜尋限制說明:")
    print("   • 小红书 (Xiaohongshu) 大部分內容係 GFW 後面，搜尋效果差")
    print("   • 微博 (Weibo) 實時內容較難搜到（需要用 Weibo Open API）")
    print("   • 百度贴吧 部分內容唔俾外部爬蟲索引")
    print("   • Bing API 係搜尋中國內容最好嘅「外部」搜尋引擎")
    print("   • 如需深度搜尋大陸內容，建議配合 VPN + 直接訪問")
