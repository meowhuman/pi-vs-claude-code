#!/usr/bin/env python3
"""
WSP-V3 Geopolitics Searcher — Think tanks, expert analysis, academic research

Replaces: search_geopolitics.py (757 lines → modular)
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


EXPERT_SOURCES = {
    "think_tanks": {
        "name": "智庫研究",
        "sources": [
            "cfr.org", "brookings.edu", "csis.org", "rand.org",
            "chathamhouse.org", "carnegieendowment.org", "hudson.org",
        ],
    },
    "expert_commentary": {
        "name": "專家評論",
        "sources": [
            "project-syndicate.org", "foreignaffairs.com", "foreignpolicy.com",
            "theatlantic.com", "economist.com",
        ],
    },
    "academic": {
        "name": "學術研究",
        "sources": [
            "scholar.google.com", "arxiv.org", "ssrn.com",
            "jstor.org", "nature.com",
        ],
    },
    "asia_pacific": {
        "name": "亞太分析",
        "sources": [
            "lowyinstitute.org", "eastasiaforum.org", "rsis.edu.sg",
            "asiasociety.org", "iseas.edu.sg",
        ],
    },
    "middle_east": {
        "name": "中東分析",
        "sources": [
            "mei.edu", "al-monitor.com", "crisisgroup.org",
        ],
    },
    "news_sources": {
        "name": "政治新聞",
        "sources": [
            "reuters.com", "apnews.com", "bbc.com",
            "aljazeera.com", "politico.com",
        ],
    },
}

TOPIC_KEYWORDS = {
    "taiwan": ["Taiwan", "Taiwan Strait", "cross-strait"],
    "south_china_sea": ["South China Sea", "SCS", "Nine-Dash Line"],
    "ukraine": ["Ukraine", "Russia-Ukraine", "NATO"],
    "us_china": ["US-China", "trade war", "semiconductor"],
    "iran": ["Iran", "nuclear deal", "JCPOA"],
    "trade": ["trade war", "semiconductor", "export controls"],
}


def search_geopolitics(
    query: str,
    source_type: str = "think_tanks",
    freshness: str = "pw",
    count: int = 15,
) -> List[SearchResult]:
    """Search geopolitics expert sources."""
    if source_type not in EXPERT_SOURCES:
        print(f"❌ 未知來源類型: {source_type}")
        print(f"可用: {', '.join(EXPERT_SOURCES.keys())}")
        return []

    info = EXPERT_SOURCES[source_type]
    sources = info["sources"]

    print(f"🌍 地緣政治搜尋: {query}")
    print(f"📂 來源: {info['name']}")
    print("=" * 80)
    print()

    # Build site-restricted query
    site_filters = " OR ".join([f"site:{s}" for s in sources[:5]])
    search_query = f"{query} ({site_filters})"

    brave = BraveEngine()
    if brave.available:
        results = brave.web_search(search_query, count=count, freshness=freshness)
        if results:
            print_results(results, info['name'])
            return results

    tavily = TavilyEngine()
    if tavily.available:
        results = tavily.search(search_query, max_results=count, search_depth="advanced")
        print_results(results, f"{info['name']} (Tavily)")
        return results

    return []


def search_by_topic(
    topic: str,
    source_type: str = "think_tanks",
    freshness: str = "pw",
    count: int = 15,
) -> List[SearchResult]:
    """Search by predefined geopolitics topic."""
    if topic not in TOPIC_KEYWORDS:
        print(f"❌ 未知主題: {topic}")
        print(f"可用: {', '.join(TOPIC_KEYWORDS.keys())}")
        return []

    keywords = TOPIC_KEYWORDS[topic]
    query = " OR ".join(keywords[:3])
    return search_geopolitics(query, source_type, freshness, count)


def list_geopolitics_sources():
    """List available geopolitics sources and topics."""
    print("🌍 地緣政治來源\n")
    for key, info in EXPERT_SOURCES.items():
        print(f"  {key:20s} — {info['name']}")
        for src in info['sources'][:3]:
            print(f"                         • {src}")
    print()
    print("📋 預設主題:")
    for key in TOPIC_KEYWORDS:
        print(f"  • {key}")
