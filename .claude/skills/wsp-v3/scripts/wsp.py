#!/usr/bin/env python3
"""
WSP-V3 — Unified Web Search Pro CLI

Single entry point replacing 31 separate scripts from V2.

Usage:
    uv run scripts/wsp.py news "AI" --source tech
    uv run scripts/wsp.py forum reddit ClaudeCode --keyword "MCP"
    uv run scripts/wsp.py forum hackernews --type top
    uv run scripts/wsp.py china "投資" --forum xueqiu
    uv run scripts/wsp.py geopolitics "Taiwan" --type think_tanks
    uv run scripts/wsp.py trading "Bitcoin" --forum bitcointalk
    uv run scripts/wsp.py search "Claude AI"
    uv run scripts/wsp.py status
"""

import sys
import argparse
from pathlib import Path

# Add wsp-v3 root to path for imports
WSP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WSP_ROOT))

# Ensure config is loaded
from utils.config import load_env
load_env(str(WSP_ROOT))


def cmd_news(args):
    """News search subcommand."""
    from searchers.news import search_news, list_sources
    if args.list_sources:
        list_sources()
        return
    search_news(
        query=args.query,
        source=args.source,
        region=args.region,
        freshness=args.freshness,
        count=args.count,
    )


def cmd_forum(args):
    """Forum search subcommand."""
    from searchers.forums import (
        search_reddit, search_hackernews, search_forum_site,
        search_multi_forum, list_forums,
    )

    if args.list_forums:
        list_forums()
        return

    forum = args.forum_name

    if forum == "reddit":
        search_reddit(
            subreddit=args.subreddit or "all",
            keyword=args.keyword,
            sort=args.sort or "new",
            hours=args.hours or 168,
            count=args.count,
        )
    elif forum == "hackernews":
        search_hackernews(
            query=args.query,
            hn_type=args.type or "top",
            count=args.count,
            hours=args.hours or 168,
        )
    elif forum == "multi":
        search_multi_forum(
            query=args.query or "",
            preset=args.preset,
            freshness=args.freshness,
            count_per_forum=args.count,
        )
    else:
        search_forum_site(
            forum=forum,
            query=args.query or "",
            freshness=args.freshness,
            count=args.count,
        )


def cmd_china(args):
    """China search subcommand."""
    from searchers.china import search_china, search_xueqiu, list_china_forums

    if args.list_forums:
        list_china_forums()
        return

    if args.xueqiu:
        search_xueqiu(args.query, count=args.count, freshness=args.freshness)
    else:
        search_china(
            query=args.query,
            forum=args.forum or "all",
            freshness=args.freshness,
            count=args.count,
        )


def cmd_geopolitics(args):
    """Geopolitics search subcommand."""
    from searchers.geopolitics import (
        search_geopolitics, search_by_topic, list_geopolitics_sources,
    )

    if args.list_sources:
        list_geopolitics_sources()
        return

    if args.topic:
        search_by_topic(
            topic=args.topic,
            source_type=args.type or "think_tanks",
            freshness=args.freshness,
            count=args.count,
        )
    else:
        search_geopolitics(
            query=args.query,
            source_type=args.type or "think_tanks",
            freshness=args.freshness,
            count=args.count,
        )


def cmd_trading(args):
    """Trading forum search subcommand."""
    from searchers.trading import search_trading
    search_trading(
        query=args.query,
        forum=args.forum or "all",
        freshness=args.freshness,
        count=args.count,
    )


def cmd_search(args):
    """General search subcommand."""
    from engines.brave import BraveEngine
    from engines.tavily import TavilyEngine
    from utils.formatter import print_results

    print(f"🔍 通用搜尋: {args.query}")
    print("=" * 80)
    print()

    brave = BraveEngine()
    if brave.available:
        results = brave.web_search(args.query, count=args.count, freshness=args.freshness)
        if results:
            print_results(results, "搜尋結果")
            return

    tavily = TavilyEngine()
    if tavily.available:
        results = tavily.search(args.query, max_results=args.count)
        print_results(results, "搜尋結果 (Tavily)")
        return

    print("❌ 無可用搜尋引擎。請設定 BRAVE_API_KEY_1 或 TAVILY_API_KEY。")


def cmd_status(args):
    """Check API status and usage."""
    import os
    from engines.brave import BraveEngine
    from engines.tavily import TavilyEngine
    from engines.bing import BingEngine

    print("=" * 60)
    print("📊 WSP-V3 API 狀態")
    print("=" * 60)

    # Brave
    brave = BraveEngine()
    status = "✅ 已配置" if brave.available else "❌ 未配置"
    print(f"\n🦁 Brave Search: {status}")
    if brave.available:
        usage = brave.usage_tracker.get_usage()
        print(f"   本月用量: {usage['calls']}/{usage['limit']} ({usage['remaining']} 剩餘)")
        print(f"   可用鑰匙: {len(brave.key_manager.keys)} 個")

    # Tavily
    tavily = TavilyEngine()
    status = "✅ 已配置" if tavily.available else "❌ 未配置"
    print(f"\n🔬 Tavily: {status}")
    if tavily.available:
        usage = tavily.usage_tracker.get_usage()
        print(f"   本月用量: {usage['calls']}/{usage['limit']} ({usage['remaining']} 剩餘)")

    # Bing
    bing = BingEngine()
    status = "✅ 已配置" if bing.available else "❌ 未配置 (BING_API_KEY)"
    print(f"\n🔵 Bing (中國搜尋): {status}")
    if bing.available:
        usage = bing.usage_tracker.get_usage()
        print(f"   本月用量: {usage['calls']}/{usage['limit']} ({usage['remaining']} 剩餘)")

    # Firecrawl removed
    print(f"\n🔥 Firecrawl: ❌ 已移除 (V3 唔再使用)")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        prog="wsp",
        description="WSP-V3 — Web Search Pro 統一搜尋工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="搜尋類別")

    # ==================== news ====================
    p_news = subparsers.add_parser("news", help="新聞搜尋")
    p_news.add_argument("query", nargs="?", help="搜尋關鍵字")
    p_news.add_argument("--source", "-s", help="新聞源 (tech, finance, world, hk, china, ai, crypto...)")
    p_news.add_argument("--region", "-r", default="global", help="地區 (hk, us, uk, cn, global)")
    p_news.add_argument("--freshness", "-f", default="pw", help="時間 (pd, pw, pm, py)")
    p_news.add_argument("--count", "-c", type=int, default=20, help="結果數量")
    p_news.add_argument("--list-sources", action="store_true", help="列出新聞源")
    p_news.set_defaults(func=cmd_news)

    # ==================== forum ====================
    p_forum = subparsers.add_parser("forum", help="論壇搜尋")
    p_forum.add_argument("forum_name", nargs="?", default="multi", help="論壇 (reddit, hackernews, lihkg, ptt, v2ex, stackoverflow, multi...)")
    p_forum.add_argument("subreddit", nargs="?", help="Subreddit 名稱 (Reddit only)")
    p_forum.add_argument("query", nargs="?", help="搜尋關鍵字")
    p_forum.add_argument("--keyword", "-k", help="關鍵字過濾 (Reddit)")
    p_forum.add_argument("--sort", help="排序 (new, hot, top, rising)")
    p_forum.add_argument("--type", "-t", help="HN 類型 (top, new, best, ask, show)")
    p_forum.add_argument("--preset", "-p", help="多論壇預設 (tech, asia, global, dev, product)")
    p_forum.add_argument("--hours", type=int, help="時間範圍 (小時)")
    p_forum.add_argument("--freshness", "-f", default="pw", help="時間")
    p_forum.add_argument("--count", "-c", type=int, default=15, help="結果數量")
    p_forum.add_argument("--list-forums", action="store_true", help="列出所有論壇")
    p_forum.set_defaults(func=cmd_forum)

    # ==================== china ====================
    p_china = subparsers.add_parser("china", help="中國大陸搜尋")
    p_china.add_argument("query", nargs="?", help="搜尋關鍵字")
    p_china.add_argument("--forum", help="指定論壇 (zhihu, weibo, tieba, xiaohongshu, xueqiu, douban, bilibili, all)")
    p_china.add_argument("--xueqiu", "-x", action="store_true", help="雪球投資搜尋")
    p_china.add_argument("--freshness", "-f", default="pw", help="時間")
    p_china.add_argument("--count", "-c", type=int, default=20, help="結果數量")
    p_china.add_argument("--list-forums", action="store_true", help="列出中國論壇")
    p_china.set_defaults(func=cmd_china)

    # ==================== geopolitics ====================
    p_geo = subparsers.add_parser("geopolitics", help="地緣政治搜尋")
    p_geo.add_argument("query", nargs="?", help="搜尋關鍵字")
    p_geo.add_argument("--type", "-t", default="think_tanks", help="來源 (think_tanks, expert_commentary, academic, asia_pacific, middle_east, news_sources)")
    p_geo.add_argument("--topic", help="預設主題 (taiwan, south_china_sea, ukraine, us_china, iran, trade)")
    p_geo.add_argument("--freshness", "-f", default="pw", help="時間")
    p_geo.add_argument("--count", "-c", type=int, default=15, help="結果數量")
    p_geo.add_argument("--list-sources", action="store_true", help="列出來源")
    p_geo.set_defaults(func=cmd_geo)

    # ==================== trading ====================
    p_trade = subparsers.add_parser("trading", help="交易論壇搜尋")
    p_trade.add_argument("query", help="搜尋關鍵字")
    p_trade.add_argument("--forum", help="論壇 (stocktwits, bitcointalk, 4chan_biz, xueqiu, all)")
    p_trade.add_argument("--freshness", "-f", default="pw", help="時間")
    p_trade.add_argument("--count", "-c", type=int, default=15, help="結果數量")
    p_trade.set_defaults(func=cmd_trading)

    # ==================== search ====================
    p_search = subparsers.add_parser("search", help="通用搜尋")
    p_search.add_argument("query", help="搜尋關鍵字")
    p_search.add_argument("--freshness", "-f", default="", help="時間 (pd, pw, pm, py)")
    p_search.add_argument("--count", "-c", type=int, default=10, help="結果數量")
    p_search.set_defaults(func=cmd_search)

    # ==================== status ====================
    p_status = subparsers.add_parser("status", help="檢查 API 狀態")
    p_status.set_defaults(func=cmd_status)

    # Parse and run
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if hasattr(args, "func"):
        args.func(args)


def cmd_geo(args):
    """Wrapper for geopolitics to handle naming."""
    cmd_geopolitics(args)


if __name__ == "__main__":
    main()
