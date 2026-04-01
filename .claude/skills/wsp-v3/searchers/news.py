#!/usr/bin/env python3
"""
WSP-V3 News Searcher — Professional news search with multi-source support

Replaces: search_news.py (786 lines → modular)
"""

import sys
import logging
from typing import List, Optional
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.brave import BraveEngine
from engines.tavily import TavilyEngine
from engines.bing import BingEngine
from utils.formatter import SearchResult, get_freshness_name, print_results

logger = logging.getLogger("wsp-v3")

# ==================== NEWS SOURCE CONFIGURATION ====================

NEWS_SOURCES = {
    "tech": {
        "name": "科技新聞",
        "sources": ["techcrunch.com", "theverge.com", "wired.com", "arstechnica.com", "engadget.com", "venturebeat.com"]
    },
    "finance": {
        "name": "財經新聞",
        "sources": ["bloomberg.com", "reuters.com", "ft.com", "wsj.com", "cnbc.com", "marketwatch.com"]
    },
    "world": {
        "name": "國際新聞",
        "sources": ["bbc.com", "cnn.com", "nytimes.com", "theguardian.com", "aljazeera.com", "apnews.com"]
    },
    "hk": {
        "name": "香港新聞",
        "sources": ["scmp.com", "hk01.com", "mingpao.com", "hket.com", "news.now.com"]
    },
    "china": {
        "name": "中國新聞",
        "sources": ["xinhuanet.com", "people.com.cn", "chinadaily.com.cn", "globaltimes.cn"]
    },
    "japan": {
        "name": "日本新聞",
        "sources": ["japantimes.co.jp", "nhk.or.jp", "asia.nikkei.com"]
    },
    "korea": {
        "name": "韓國新聞",
        "sources": ["koreaherald.com", "en.yna.co.kr"]
    },
    "taiwan": {
        "name": "台灣新聞",
        "sources": ["focustaiwan.tw", "taipeitimes.com"]
    },
    "europe": {
        "name": "歐洲新聞",
        "sources": ["dw.com", "france24.com", "politico.eu", "euronews.com"]
    },
    "ai": {
        "name": "AI/ML 新聞",
        "sources": ["venturebeat.com/ai", "techcrunch.com", "theverge.com"]
    },
    "crypto": {
        "name": "加密貨幣新聞",
        "sources": ["coindesk.com", "cointelegraph.com", "decrypt.co", "theblock.co"]
    },
    "russia": {
        "name": "俄羅斯新聞",
        "sources": ["rt.com", "tass.com"]
    },
    "middleeast": {
        "name": "中東新聞",
        "sources": ["timesofisrael.com", "haaretz.com", "alarabiya.net"]
    },
    "sports": {
        "name": "體育新聞",
        "sources": ["espn.com", "bbc.com/sport"]
    },
}

REGION_CONFIG = {
    "hk": {"name": "香港", "country": "HK"},
    "us": {"name": "美國", "country": "US"},
    "uk": {"name": "英國", "country": "GB"},
    "cn": {"name": "中國", "country": "CN"},
    "global": {"name": "全球", "country": "US"},
}


def search_news(
    query: str,
    source: Optional[str] = None,
    region: str = "global",
    freshness: str = "pw",
    count: int = 20,
) -> List[SearchResult]:
    """
    Unified news search.

    Strategy:
    - China sources → Tavily (Brave doesn't index well) or Bing
    - Everything else → Brave News Search
    """
    print(f"📰 新聞搜尋: {query}")
    if source:
        src_info = NEWS_SOURCES.get(source, {})
        print(f"🏷️  來源: {src_info.get('name', source)}")
    region_name = REGION_CONFIG.get(region, {}).get("name", region)
    print(f"🌍 地區: {region_name}")
    print(f"⏰ 時間: {get_freshness_name(freshness)}")
    print("=" * 80)
    print()

    # China sources → use Tavily or Bing (Brave can't index them)
    if source == "china":
        return _search_china_news(query, count, freshness)

    # Build query with source filtering
    search_query = query
    if source and source in NEWS_SOURCES:
        sources = NEWS_SOURCES[source]["sources"]
        site_filters = " OR ".join([f"site:{s}" for s in sources[:5]])
        search_query = f"{query} ({site_filters})"

    # Use Brave News Search as primary
    brave = BraveEngine()
    if brave.available:
        country = REGION_CONFIG.get(region, {}).get("country", "US")
        results = brave.news_search(search_query, count=count, freshness=freshness, country=country)
        if results:
            print_results(results, "新聞搜尋結果")
            return results

    # Fallback to Tavily
    tavily = TavilyEngine()
    if tavily.available:
        results = tavily.search(search_query, max_results=count)
        if results:
            print_results(results, "新聞搜尋結果 (Tavily)")
            return results

    print("❌ 無可用搜尋引擎")
    return []


def _search_china_news(query: str, count: int, freshness: str) -> List[SearchResult]:
    """Search Chinese official media — Bing first, Tavily fallback."""
    print("🇨🇳 中國新聞搜尋（Bing/Tavily — Brave 唔 index 中國官媒）")
    print()

    sources = NEWS_SOURCES["china"]["sources"]
    all_results = []

    # Try Bing first (best for Chinese content)
    bing = BingEngine()
    if bing.available:
        for src in sources[:4]:
            results = bing.web_search(f"site:{src} {query}", count=count // 4, market="zh-CN", freshness=freshness)
            all_results.extend([r for r in results if src in r.url])

    # Fallback to Tavily
    if not all_results:
        tavily = TavilyEngine()
        if tavily.available:
            for src in sources[:4]:
                try:
                    results = tavily.search(f"site:{src} {query}", max_results=count // 4)
                    all_results.extend([r for r in results if src in r.url])
                except Exception as e:
                    logger.warning(f"Tavily failed for {src}: {e}")

    print_results(all_results[:count], "中國新聞")
    return all_results[:count]


def list_sources():
    """List all available news sources."""
    print("📰 可用新聞源\n")
    print("=" * 50)
    for key, info in NEWS_SOURCES.items():
        print(f"  {key:15s} — {info['name']}")
        for src in info['sources'][:3]:
            print(f"                     • {src}")
    print("=" * 50)
