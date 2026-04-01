#!/usr/bin/env python3
"""
WSP-V3 Cache — Simple in-memory + file cache for search results
"""

import time
import json
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional, Dict

logger = logging.getLogger("wsp-v3")

# Cache TTL defaults (seconds)
CACHE_TTL = {
    "search": 1800,   # 30 minutes
    "scrape": 3600,   # 1 hour
}


class SearchCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cache: Dict[str, Dict] = {}

    def _make_key(self, *args) -> str:
        raw = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, *key_parts) -> Optional[Any]:
        if not self.enabled:
            return None
        key = self._make_key(*key_parts)
        entry = self._cache.get(key)
        if entry and time.time() - entry["time"] < entry["ttl"]:
            logger.debug(f"Cache hit: {key[:8]}")
            return entry["data"]
        return None

    def set(self, data: Any, *key_parts, ttl: int = 1800):
        if not self.enabled:
            return
        key = self._make_key(*key_parts)
        self._cache[key] = {
            "data": data,
            "time": time.time(),
            "ttl": ttl
        }

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
