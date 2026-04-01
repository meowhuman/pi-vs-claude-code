#!/usr/bin/env python3
"""
WSP-V3 Rate Limiter — Unified rate limiting for all engines
"""

import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("wsp-v3")


# Rate limits per engine
RATE_LIMITS = {
    "brave": {"calls_per_minute": 60, "calls_per_hour": 1000},
    "tavily": {"calls_per_minute": 40, "calls_per_hour": 500},
    "bing": {"calls_per_minute": 30, "calls_per_hour": 500},
}


@dataclass
class Metrics:
    """API usage metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cache_hits: int = 0
    api_calls: Dict[str, int] = field(default_factory=lambda: {"brave": 0, "tavily": 0, "bing": 0})

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100

    @property
    def cache_hit_rate(self) -> float:
        total = self.total_calls + self.cache_hits
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100


class RateLimiter:
    """Rate limiting for API calls with sliding window."""

    def __init__(self, api_type: str):
        self.api_type = api_type
        self.calls = []
        self.hourly_calls = []
        self.config = RATE_LIMITS.get(api_type, {"calls_per_minute": 60, "calls_per_hour": 1000})

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Clean old entries
        self.calls = [t for t in self.calls if now - t < 60]
        self.hourly_calls = [t for t in self.hourly_calls if now - t < 3600]

        # Check minute limit
        if len(self.calls) >= self.config["calls_per_minute"]:
            wait_time = 60 - (now - self.calls[0])
            if wait_time > 0:
                logger.info(f"[{self.api_type}] Rate limit: waiting {wait_time:.1f}s")
                time.sleep(wait_time)

        # Check hourly limit
        if len(self.hourly_calls) >= self.config["calls_per_hour"]:
            wait_time = 3600 - (now - self.hourly_calls[0])
            if wait_time > 0:
                logger.warning(f"[{self.api_type}] Hourly limit: waiting {wait_time:.1f}s")
                time.sleep(min(wait_time, 60))

        self.calls.append(time.time())
        self.hourly_calls.append(time.time())


class UsageTracker:
    """File-based monthly usage tracker."""

    def __init__(self, api_name: str, storage_dir: Optional[str] = None):
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).resolve().parent.parent / ".usage_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.api_name = api_name
        self.file_path = self.storage_dir / f"{api_name}_usage.json"
        self._load_usage()

    def _load_usage(self):
        """Load or initialize usage data."""
        current_month = datetime.now().strftime("%Y-%m")
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    data = json.load(f)
                if data.get("month") != current_month:
                    self._create_new_month()
                else:
                    self.data = data
                    return
            except Exception:
                pass
        self._create_new_month()

    def _create_new_month(self):
        self.data = {
            "month": datetime.now().strftime("%Y-%m"),
            "calls": 0,
            "limit": 1000,
            "last_updated": datetime.now().isoformat()
        }
        self._save()

    def _save(self):
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save usage: {e}")

    def increment(self, count: int = 1):
        self.data["calls"] += count
        self.data["last_updated"] = datetime.now().isoformat()
        self._save()

    def get_usage(self) -> Dict:
        return {
            "calls": self.data["calls"],
            "limit": self.data["limit"],
            "remaining": max(0, self.data["limit"] - self.data["calls"]),
            "month": self.data["month"],
        }
