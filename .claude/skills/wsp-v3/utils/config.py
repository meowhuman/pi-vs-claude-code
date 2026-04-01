#!/usr/bin/env python3
"""
WSP-V3 Configuration — Dynamic .env resolution

Searches for .env file in multiple locations:
1. Skill directory (wsp-v3/)
2. Parent skills directory
3. Project root (clawdbot/)
4. Home directory (~/.env)
5. OpenClaw config directory (~/.openclaw/.env)

Never hardcodes absolute paths.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger("wsp-v3")


def find_env_file(start_dir: Optional[str] = None) -> Optional[Path]:
    """Find .env file by searching up from start_dir."""
    if start_dir:
        current = Path(start_dir).resolve()
    else:
        current = Path(__file__).resolve().parent.parent  # wsp-v3/

    # Search up 5 levels
    for _ in range(5):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        if current == current.parent:
            break
        current = current.parent

    # Also check common locations
    home = Path.home()
    for alt_path in [
        home / ".openclaw" / ".env",
        home / ".env",
    ]:
        if alt_path.exists():
            return alt_path

    return None


def load_env(start_dir: Optional[str] = None) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_path = find_env_file(start_dir)
    loaded = {}

    if env_path:
        logger.debug(f"Loading .env from: {env_path}")
        try:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):
                            os.environ[key] = value
                            loaded[key] = value
        except Exception as e:
            logger.warning(f"Failed to load .env: {e}")
    else:
        logger.debug("No .env file found, relying on environment variables")

    return loaded


def get_api_key(key_name: str, alternatives: Optional[list] = None) -> Optional[str]:
    """Get API key from environment, with fallback alternatives."""
    val = os.getenv(key_name)
    if val:
        return val

    if alternatives:
        for alt in alternatives:
            val = os.getenv(alt)
            if val:
                return val

    return None


def get_storage_dir() -> Path:
    """Get storage directory for usage data, caches, etc."""
    skill_dir = Path(__file__).resolve().parent.parent
    storage = skill_dir / ".usage_data"
    storage.mkdir(exist_ok=True)
    return storage


# Auto-load env on import
load_env()
