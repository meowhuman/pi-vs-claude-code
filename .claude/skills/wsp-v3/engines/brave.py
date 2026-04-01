#!/usr/bin/env python3
"""
WSP-V3 Brave Search Engine

Supports:
- Web search
- News search
- Multiple API key rotation
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any

from utils.config import get_api_key, get_storage_dir
from utils.rate_limiter import RateLimiter, UsageTracker
from utils.formatter import SearchResult

logger = logging.getLogger("wsp-v3")


class BraveKeyManager:
    """Manages multiple Brave API keys with automatic rotation."""

    def __init__(self):
        self.keys = []
        self.current_index = 0
        self.state_file = get_storage_dir() / "brave_keys.json"

        # Gather all keys
        for i in range(1, 5):
            key = os.getenv(f"BRAVE_API_KEY_{i}")
            if key:
                self.keys.append(key)

        # Also check BRAVE_API_KEY (without number)
        fallback = os.getenv("BRAVE_API_KEY")
        if fallback and fallback not in self.keys:
            self.keys.insert(0, fallback)

        # Load state
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    idx = state.get("current_index", 0)
                    if idx < len(self.keys):
                        self.current_index = idx
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump({"current_index": self.current_index}, f)
        except Exception:
            pass

    @property
    def current_key(self) -> Optional[str]:
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate(self):
        """Rotate to next key."""
        if len(self.keys) > 1:
            self.current_index = (self.current_index + 1) % len(self.keys)
            self._save_state()
            logger.info(f"Brave key rotated to index {self.current_index}")

    @property
    def available(self) -> bool:
        return len(self.keys) > 0


class BraveEngine:
    """Brave Search API wrapper."""

    BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(self):
        self.key_manager = BraveKeyManager()
        self.rate_limiter = RateLimiter("brave")
        self.usage_tracker = UsageTracker("brave")

    @property
    def available(self) -> bool:
        return self.key_manager.available

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make authenticated request to Brave API."""
        key = self.key_manager.current_key
        if not key:
            raise RuntimeError("No Brave API key configured")

        self.rate_limiter.wait_if_needed()

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": key,
        }

        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)

            if resp.status_code == 429:
                logger.warning("Brave 429 — rotating key")
                self.key_manager.rotate()
                # Retry once with new key
                headers["X-Subscription-Token"] = self.key_manager.current_key
                resp = requests.get(url, headers=headers, params=params, timeout=15)

            resp.raise_for_status()
            self.usage_tracker.increment()
            return resp.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Brave request failed: {e}")
            return None

    def web_search(
        self,
        query: str,
        count: int = 10,
        freshness: str = "",
        country: str = "US",
    ) -> List[SearchResult]:
        """Brave web search."""
        params = {
            "q": query,
            "count": min(count, 20),
        }
        if freshness:
            params["freshness"] = freshness
        if country:
            params["country"] = country

        data = self._make_request("web/search", params)
        if not data:
            return []

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=item.get("description", ""),
                source="brave",
                metadata={"age": item.get("age", "")},
            ))

        return results[:count]

    def news_search(
        self,
        query: str,
        count: int = 10,
        freshness: str = "",
        country: str = "US",
    ) -> List[SearchResult]:
        """Brave news search."""
        params = {
            "q": query,
            "count": min(count, 20),
        }
        if freshness:
            params["freshness"] = freshness
        if country:
            params["country"] = country

        data = self._make_request("news/search", params)
        if not data:
            return []

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=item.get("description", ""),
                source="brave-news",
                metadata={"age": item.get("age", "")},
            ))

        return results[:count]
