#!/usr/bin/env python3
"""
WSP-V3 Forum Searcher — Unified forum search

Replaces 10+ separate scripts from V2:
  search_reddit.py, search_hackernews.py, search_lihkg.py, search_ptt.py,
  search_v2ex.py, search_forums.py, search_quora.py, search_discord.py,
  search_stackoverflow.py, search_producthunt.py, search_github.py

Strategy:
- Reddit → Direct JSON API (no indexing delay, unlimited)
- Hacker News → Official API + Algolia (free, fast)
- Everything else → Brave/Tavily site: queries
"""

import sys
import json
import time
import logging
import requests
from typing import List, Optional, Dict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.brave import BraveEngine
from engines.tavily import TavilyEngine
from utils.formatter import SearchResult, format_time_ago, print_results

logger = logging.getLogger("wsp-v3")

# ==================== FORUM CONFIG ====================

FORUMS = {
    "reddit": {"name": "Reddit", "emoji": "🔴", "type": "direct_api"},
    "hackernews": {"name": "Hacker News", "emoji": "🟠", "type": "direct_api"},
    "lihkg": {"name": "LIHKG", "emoji": "🟡", "domain": "lihkg.com", "type": "site_search"},
    "ptt": {"name": "PTT", "emoji": "🟢", "domain": "ptt.cc", "type": "site_search"},
    "v2ex": {"name": "V2EX", "emoji": "🔵", "domain": "v2ex.com", "type": "site_search"},
    "stackoverflow": {"name": "Stack Overflow", "emoji": "🟧", "domain": "stackoverflow.com", "type": "site_search"},
    "github": {"name": "GitHub Discussions", "emoji": "⚫", "domain": "github.com", "type": "site_search"},
    "quora": {"name": "Quora", "emoji": "🔴", "domain": "quora.com", "type": "site_search"},
    "producthunt": {"name": "Product Hunt", "emoji": "🟤", "domain": "producthunt.com", "type": "site_search"},
    "twitter": {"name": "Twitter/X", "emoji": "🐦", "domain": "x.com", "type": "site_search"},
    "discord": {"name": "Discord", "emoji": "🟣", "domain": "discord.com", "type": "site_search"},
}

PRESETS = {
    "tech": ["hackernews", "reddit", "v2ex", "stackoverflow", "github"],
    "asia": ["lihkg", "ptt", "v2ex"],
    "global": ["hackernews", "reddit", "twitter", "quora"],
    "dev": ["stackoverflow", "github", "hackernews", "reddit"],
    "product": ["producthunt", "hackernews", "twitter"],
}


# ==================== DIRECT API SEARCHERS ====================

def search_reddit(
    subreddit: str,
    keyword: Optional[str] = None,
    sort: str = "new",
    hours: int = 168,  # 1 week
    count: int = 25,
) -> List[SearchResult]:
    """
    Reddit direct JSON API — real-time, no indexing delay.

    Args:
        subreddit: Subreddit name (without r/)
        keyword: Optional keyword filter
        sort: new, hot, top, rising
        hours: Filter posts within N hours
        count: Max results
    """
    print(f"🔴 Reddit r/{subreddit}")
    if keyword:
        print(f"🔍 關鍵字: {keyword}")
    print(f"📊 排序: {sort} | ⏰ 時間: {hours}h")
    print("=" * 80)
    print()

    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": min(count * 2, 100), "raw_json": 1}

    headers = {"User-Agent": "WSP-V3/3.0"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        now = time.time()
        cutoff = now - (hours * 3600)

        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})

            # Time filter
            created = d.get("created_utc", 0)
            if created < cutoff:
                continue

            # Keyword filter
            if keyword:
                title = d.get("title", "").lower()
                selftext = d.get("selftext", "").lower()
                if keyword.lower() not in title and keyword.lower() not in selftext:
                    continue

            results.append(SearchResult(
                title=d.get("title", ""),
                url=f"https://reddit.com{d.get('permalink', '')}",
                description=d.get("selftext", "")[:200] if d.get("selftext") else "",
                source="reddit",
                metadata={
                    "score": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "author": d.get("author", ""),
                    "age": format_time_ago(created),
                    "flair": d.get("link_flair_text", ""),
                },
            ))

            if len(results) >= count:
                break

        print_results(results, f"r/{subreddit}")
        return results

    except Exception as e:
        logger.error(f"Reddit search failed: {e}")
        print(f"❌ Reddit 搜尋失敗: {e}")
        return []


def search_hackernews(
    query: Optional[str] = None,
    hn_type: str = "top",
    count: int = 15,
    hours: int = 168,
) -> List[SearchResult]:
    """
    Hacker News — Official API for stories, Algolia for search.

    Args:
        query: Search query (uses Algolia). If None, fetches top/new/ask/show stories.
        hn_type: top, new, best, ask, show
        count: Max results
        hours: Filter within N hours
    """
    print(f"🟠 Hacker News")
    if query:
        print(f"🔍 搜尋: {query}")
    else:
        print(f"📊 類型: {hn_type}")
    print("=" * 80)
    print()

    results = []

    if query:
        # Algolia search
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": count,
        }
        if hours:
            params["numericFilters"] = f"created_at_i>{int(time.time()) - hours * 3600}"

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for hit in data.get("hits", []):
                results.append(SearchResult(
                    title=hit.get("title", ""),
                    url=hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"),
                    description=hit.get("story_text", "")[:200] if hit.get("story_text") else "",
                    source="hackernews",
                    metadata={
                        "points": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                        "author": hit.get("author", ""),
                        "age": format_time_ago(hit.get("created_at_i", 0)),
                        "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    },
                ))
        except Exception as e:
            logger.error(f"HN Algolia search failed: {e}")

    else:
        # Official API for story lists
        type_map = {
            "top": "topstories", "new": "newstories", "best": "beststories",
            "ask": "askstories", "show": "showstories",
        }
        endpoint = type_map.get(hn_type, "topstories")

        try:
            resp = requests.get(f"https://hacker-news.firebaseio.com/v0/{endpoint}.json", timeout=10)
            resp.raise_for_status()
            story_ids = resp.json()[:count]

            for sid in story_ids:
                try:
                    item_resp = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5)
                    item = item_resp.json()
                    if item:
                        results.append(SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            description="",
                            source="hackernews",
                            metadata={
                                "points": item.get("score", 0),
                                "comments": item.get("descendants", 0),
                                "author": item.get("by", ""),
                                "age": format_time_ago(item.get("time", 0)),
                                "hn_url": f"https://news.ycombinator.com/item?id={sid}",
                            },
                        ))
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"HN API failed: {e}")

    print_results(results, "Hacker News")
    return results


# ==================== SITE-BASED SEARCH ====================

def search_forum_site(
    forum: str,
    query: str,
    freshness: str = "pw",
    count: int = 15,
) -> List[SearchResult]:
    """
    Generic site-based forum search using Brave/Tavily.

    Works for: LIHKG, PTT, V2EX, Stack Overflow, GitHub, Quora, Product Hunt, etc.
    """
    if forum not in FORUMS:
        print(f"❌ 未知論壇: {forum}")
        list_forums()
        return []

    info = FORUMS[forum]
    domain = info.get("domain", "")

    print(f"{info['emoji']} {info['name']} 搜尋")
    print(f"🔍 關鍵字: {query}")
    print("=" * 80)
    print()

    search_query = f"{query} site:{domain}" if domain else query

    # Try Brave first
    brave = BraveEngine()
    if brave.available:
        results = brave.web_search(search_query, count=count, freshness=freshness)
        if results:
            # Filter to match domain
            filtered = [r for r in results if domain in r.url] if domain else results
            if filtered:
                print_results(filtered, info['name'])
                return filtered

    # Fallback to Tavily
    tavily = TavilyEngine()
    if tavily.available:
        results = tavily.search(search_query, max_results=count)
        filtered = [r for r in results if domain in r.url] if domain else results
        print_results(filtered, f"{info['name']} (Tavily)")
        return filtered

    print("❌ 無可用搜尋引擎")
    return []


def search_multi_forum(
    query: str,
    forums: Optional[List[str]] = None,
    preset: Optional[str] = None,
    freshness: str = "pw",
    count_per_forum: int = 5,
) -> List[SearchResult]:
    """
    Multi-forum search — searches across multiple forums.

    Args:
        query: Search query
        forums: List of forum keys
        preset: Preset name (tech, asia, global, dev, product)
        freshness: Time range
        count_per_forum: Results per forum
    """
    if preset and preset in PRESETS:
        forum_list = PRESETS[preset]
        print(f"🔍 預設: {preset} — {', '.join(forum_list)}")
    elif forums:
        forum_list = forums
    else:
        forum_list = ["hackernews", "reddit", "twitter"]

    print(f"🌐 多論壇搜尋: {query}")
    print(f"📂 論壇: {', '.join(forum_list)}")
    print("=" * 80)
    print()

    all_results = []
    for forum in forum_list:
        if forum == "reddit":
            # Reddit uses different API
            results = search_reddit("all", keyword=query, count=count_per_forum, hours=168)
        elif forum == "hackernews":
            results = search_hackernews(query=query, count=count_per_forum)
        else:
            results = search_forum_site(forum, query, freshness=freshness, count=count_per_forum)
        all_results.extend(results)

    return all_results


def list_forums():
    """List all supported forums."""
    print("🌐 支援嘅論壇\n")
    print("=" * 50)
    for key, info in FORUMS.items():
        api_note = "直接 API" if info["type"] == "direct_api" else f"site:{info.get('domain', '')}"
        print(f"  {info['emoji']} {key:15s} — {info['name']:20s} ({api_note})")
    print()
    print("📋 預設群組:")
    for key, forums in PRESETS.items():
        print(f"  {key:10s} — {', '.join(forums)}")
    print("=" * 50)
