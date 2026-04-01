#!/usr/bin/env python3
"""
WSP-V3 Bing Search Engine — NEW in V3

Bing is superior to Brave for:
- Chinese mainland content (知乎, 微博, 百度贴吧, 小红书, etc.)
- Non-English content in general
- Microsoft indexes Chinese sites much better than Brave

Bing Web Search API v7:
  Free tier: 1,000 calls/month
  Paid: $3 per 1,000 calls
  Docs: https://learn.microsoft.com/en-us/bing/search-apis/bing-web-search/overview
"""

import os
import logging
import requests
from typing import List, Optional, Dict

from utils.config import get_api_key
from utils.rate_limiter import RateLimiter, UsageTracker
from utils.formatter import SearchResult

logger = logging.getLogger("wsp-v3")


class BingEngine:
    """Bing Web Search API wrapper — optimized for Chinese content."""

    BASE_URL = "https://api.bing.microsoft.com/v7.0"

    def __init__(self):
        self.rate_limiter = RateLimiter("bing")
        self.usage_tracker = UsageTracker("bing")

    @property
    def available(self) -> bool:
        return bool(get_api_key("BING_API_KEY", ["BING_SEARCH_KEY"]))

    def web_search(
        self,
        query: str,
        count: int = 10,
        market: str = "zh-CN",
        freshness: str = "",
    ) -> List[SearchResult]:
        """
        Bing web search — optimized for Chinese content.

        Args:
            query: Search query
            count: Number of results
            market: Market code (zh-CN for China, zh-TW for Taiwan, zh-HK for HK)
            freshness: Day, Week, Month (Bing format)
        """
        api_key = get_api_key("BING_API_KEY", ["BING_SEARCH_KEY"])
        if not api_key:
            raise RuntimeError("BING_API_KEY not configured. "
                             "Get one at https://portal.azure.com → Bing Search v7")

        self.rate_limiter.wait_if_needed()

        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": min(count, 50),
            "mkt": market,
            "textDecorations": False,
            "textFormat": "Raw",
        }

        if freshness:
            # Bing uses "Day", "Week", "Month" or date range "2024-01-01..2024-02-01"
            freshness_map = {"pd": "Day", "pw": "Week", "pm": "Month"}
            params["freshness"] = freshness_map.get(freshness, freshness)

        try:
            resp = requests.get(
                f"{self.BASE_URL}/search",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            self.usage_tracker.increment()

            data = resp.json()
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    description=item.get("snippet", ""),
                    source="bing",
                    metadata={
                        "date_last_crawled": item.get("dateLastCrawled", ""),
                        "language": item.get("language", ""),
                    },
                ))

            return results[:count]

        except requests.exceptions.RequestException as e:
            logger.error(f"Bing search failed: {e}")
            return []

    def news_search(
        self,
        query: str,
        count: int = 10,
        market: str = "zh-CN",
        freshness: str = "",
    ) -> List[SearchResult]:
        """Bing news search — better for Chinese news sources."""
        api_key = get_api_key("BING_API_KEY", ["BING_SEARCH_KEY"])
        if not api_key:
            raise RuntimeError("BING_API_KEY not configured")

        self.rate_limiter.wait_if_needed()

        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "count": min(count, 100),
            "mkt": market,
            "textFormat": "Raw",
        }

        if freshness:
            freshness_map = {"pd": "Day", "pw": "Week", "pm": "Month"}
            params["freshness"] = freshness_map.get(freshness, freshness)

        try:
            resp = requests.get(
                f"{self.BASE_URL}/news/search",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            self.usage_tracker.increment()

            data = resp.json()
            results = []
            for item in data.get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    source="bing-news",
                    metadata={
                        "provider": item.get("provider", [{}])[0].get("name", "") if item.get("provider") else "",
                        "datePublished": item.get("datePublished", ""),
                    },
                ))

            return results[:count]

        except requests.exceptions.RequestException as e:
            logger.error(f"Bing news search failed: {e}")
            return []
