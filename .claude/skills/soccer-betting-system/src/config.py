from __future__ import annotations

import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = SKILL_ROOT / 'data' / 'processed' / 'soccer-betting.db'


def get_db_path() -> Path:
    raw = os.getenv('SOCCER_BETTING_DB_PATH')
    return Path(raw).expanduser() if raw else DEFAULT_DB_PATH


def get_odds_api_key() -> str:
    return os.getenv('ODDS_API_KEY', '')


def get_sportapi7_api_key() -> str:
    return os.getenv('SPORTAPI7_API_KEY', '')


def get_sportapi7_api_host() -> str:
    return os.getenv('SPORTAPI7_API_HOST', 'sportapi7.p.rapidapi.com')


def get_cloudbet_api_token() -> str:
    return os.getenv('CLOUDBET_API_TOKEN', '')


def get_cloudbet_env() -> str:
    return os.getenv('CLOUDBET_ENV', 'live')


def get_cloudbet_currency() -> str:
    return os.getenv('CLOUDBET_CURRENCY', 'USDT')
