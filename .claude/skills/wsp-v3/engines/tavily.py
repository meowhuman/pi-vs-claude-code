#!/usr/bin/env python3
"""
WSP-V3 Tavily Search Engine

Best for:
- Deep content extraction
- Chinese content (better than Brave for Chinese sites)
- Site-specific searches (site: queries)
"""

import os
import logging
import requests
from typing import List, Optional, Dict

from utils.config import get_api_key
from utils.rate_limiter import RateLimiter, UsageTracker
from utils.formatter import SearchResult

logger = logging.getLogger("wsp-v3")


class TavilyEngine:
    """Tavily Search API wrapper."""

    BASE_URL = "https://api.tavily.com"

    def __init__(self):
        self.rate_limiter = RateLimiter("tavily")
        self.usage_tracker = UsageTracker("tavily")

    @property
    def available(self) -> bool:
        return bool(get_api_key("TAVILY_API_KEY"))

    def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Tavily search with optional domain filtering."""
        api_key = get_api_key("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not configured")

        self.rate_limiter.wait_if_needed()

        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": min(max_results, 20),
            "search_depth": search_depth,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            resp = requests.post(
                f"{self.BASE_URL}/search",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            self.usage_tracker.increment()

            data = resp.json()
            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("content", ""),
                    source="tavily",
                ))

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    def extract(self, urls: List[str]) -> List[Dict]:
        """Extract content from specific URLs using Tavily."""
        api_key = get_api_key("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not configured")

        self.rate_limiter.wait_if_needed()

        try:
            resp = requests.post(
                f"{self.BASE_URL}/extract",
                json={
                    "api_key": api_key,
                    "urls": urls[:5],
                },
                timeout=30,
            )
            resp.raise_for_status()
            self.usage_tracker.increment()
            return resp.json().get("results", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Tavily extract failed: {e}")
            return []
