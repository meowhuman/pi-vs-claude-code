#!/usr/bin/env python3
"""
Data fetching layer — Tiingo (stocks + forex) + CCXT/Binance (crypto)
With local CSV cache (~24h TTL) to avoid redundant API calls.
"""

import os
import asyncio
import hashlib
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import pandas as pd

TIINGO_API_KEY = os.getenv('TIINGO_API_KEY', '2146105fde5488455a958c98755941aafb9d9c66')
CACHE_DIR = Path(__file__).parent.parent / '.cache'
CACHE_TTL_HOURS = 24

TICKER_MAP = {
    'GOOG': 'GOOGL',
    'GOOGLE': 'GOOGL',
    'AMAZON': 'AMZN',
}

# Known forex pairs (6-char alpha codes)
FOREX_PAIRS = {
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD',
    'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP', 'EURAUD', 'USDSGD',
    'USDHKD', 'USDCNY', 'XAUUSD', 'XAGUSD',
}


def is_forex(symbol: str) -> bool:
    """Auto-detect if a symbol is a forex pair (6-char alpha or known pair)"""
    s = symbol.strip().upper()
    if s in FOREX_PAIRS:
        return True
    return len(s) == 6 and s.isalpha()


def fetch_stock_data_tiingo(ticker: str, period_days: int = 365) -> pd.DataFrame:
    """從 Tiingo API 獲取股票日線 OHLCV 數據"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}',
    }
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=period_days + 50)).strftime('%Y-%m-%d')
    url = f'https://api.tiingo.com/tiingo/daily/{ticker}/prices'
    params = {'startDate': start_date, 'format': 'json'}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if resp.status_code == 404:
        raise ValueError(f'Symbol not found: {ticker}')
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, list) or not data:
        raise ValueError(f'No data returned for {ticker}')

    df = pd.DataFrame(data)
    cols = {'date': 'date', 'adjOpen': 'open', 'adjHigh': 'high',
            'adjLow': 'low', 'adjClose': 'close', 'adjVolume': 'volume'}
    # fallback if adjVolume missing
    if 'adjVolume' not in df.columns and 'volume' in df.columns:
        cols['volume'] = 'volume'
        cols.pop('adjVolume', None)
    df = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df.sort_values('date', inplace=True)
    df.set_index('date', inplace=True)

    cutoff = datetime.now() - timedelta(days=period_days)
    df = df[df.index >= cutoff]
    return df.dropna()


def fetch_stock_data_yfinance(ticker: str, period_days: int = 365) -> pd.DataFrame:
    """從 yfinance 獲取股票日線 OHLCV 數據（Tiingo fallback）"""
    import yfinance as yf

    start_date = (datetime.now() - timedelta(days=period_days + 5)).strftime('%Y-%m-%d')
    raw = yf.download(ticker, start=start_date, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f'yfinance: no data for {ticker}')

    # yfinance returns MultiIndex columns when downloading single ticker sometimes
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    raw.columns = [c.lower() for c in raw.columns]
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw.index.name = 'date'

    needed = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in raw.columns]
    return raw[needed].dropna()


def fetch_stock_data(ticker: str, period_days: int = 365) -> pd.DataFrame:
    """獲取股票日線數據：先試 Tiingo，失敗自動 fallback 到 yfinance"""
    ticker = TICKER_MAP.get(ticker.upper(), ticker.upper())
    try:
        return fetch_stock_data_tiingo(ticker, period_days)
    except Exception as tiingo_err:
        print(f'⚠️  Tiingo failed ({tiingo_err}), falling back to yfinance...')
        return fetch_stock_data_yfinance(ticker, period_days)


def fetch_forex_data(pair: str, period_days: int = 365) -> pd.DataFrame:
    """從 Tiingo FX API 獲取外匯日線 OHLCV 數據"""
    pair_lower = pair.strip().lower()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}',
    }
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=period_days + 50)).strftime('%Y-%m-%d')
    url = f'https://api.tiingo.com/tiingo/fx/{pair_lower}/prices'
    params = {'startDate': start_date, 'resampleFreq': '1Day'}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if resp.status_code == 404:
        raise ValueError(f'Forex pair not found: {pair_lower}')
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, list) or not data:
        raise ValueError(f'No data returned for forex pair {pair_lower}')

    df = pd.DataFrame(data)
    col_map = {'date': 'date', 'open': 'open', 'high': 'high',
               'low': 'low', 'close': 'close'}
    available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)
    df['volume'] = 0  # Forex has no volume data
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df.sort_values('date', inplace=True)
    df.set_index('date', inplace=True)

    cutoff = datetime.now() - timedelta(days=period_days)
    df = df[df.index >= cutoff]
    if len(df) < 20:
        raise ValueError(f'Insufficient forex data for {pair_lower}: only {len(df)} rows')
    return df.dropna()


async def _ccxt_fetch(symbol: str, timeframe: str, limit: int) -> list:
    import ccxt.async_support as ccxt
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        await exchange.load_markets()
        sym = symbol.upper()
        if '/' not in sym:
            sym = f'{sym}/USDT'
        if sym not in exchange.markets:
            raise ValueError(f'Symbol {sym} not found on Binance')
        return await exchange.fetch_ohlcv(sym, timeframe, limit=limit)
    finally:
        await exchange.close()


def fetch_crypto_data(symbol: str, timeframe: str = '1d', limit: int = 365) -> pd.DataFrame:
    """從 CCXT/Binance 獲取加密貨幣 OHLCV 數據"""
    raw = asyncio.run(_ccxt_fetch(symbol, timeframe, limit))
    df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    df.drop(columns=['timestamp'], inplace=True)
    df.sort_index(inplace=True)
    return df.dropna()


def _cache_key(symbol: str, crypto: bool, period_days: int, timeframe: str,
               forex: bool = False) -> Path:
    """Generate a cache file path based on request parameters"""
    asset_type = 'crypto' if crypto else ('forex' if forex else 'stock')
    tag = f'{symbol}_{asset_type}_{period_days}d_{timeframe}'
    h = hashlib.md5(tag.encode()).hexdigest()[:8]
    return CACHE_DIR / f'{tag}_{h}.csv'


def _read_cache(path: Path) -> Optional[pd.DataFrame]:
    """Read cached data if fresh enough"""
    if not path.exists():
        return None
    age = datetime.now().timestamp() - path.stat().st_mtime
    if age > CACHE_TTL_HOURS * 3600:
        return None
    try:
        df = pd.read_csv(path, index_col='date', parse_dates=True)
        return df if not df.empty else None
    except Exception:
        return None


def _write_cache(path: Path, df: pd.DataFrame) -> None:
    """Write data to cache"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)


def fetch_data(symbol: str, crypto: bool = False, forex: bool = False,
               period_days: int = 365, timeframe: str = '1d') -> pd.DataFrame:
    """統一入口：先查快取，miss 才打 API

    Args:
        symbol: Ticker symbol (e.g. AAPL, BTC, EURUSD)
        crypto: True for CCXT/Binance crypto data
        forex:  True for Tiingo FX forex data (auto-detected if not set)
        period_days: Lookback period in days
        timeframe: Candle timeframe (crypto only, e.g. 1h, 4h, 1d)
    """
    # Auto-detect forex if not explicitly set
    if not crypto and not forex and is_forex(symbol):
        forex = True

    cache_path = _cache_key(symbol, crypto, period_days, timeframe, forex=forex)
    cached = _read_cache(cache_path)
    if cached is not None:
        return cached

    if crypto:
        df = fetch_crypto_data(symbol, timeframe=timeframe, limit=period_days)
    elif forex:
        df = fetch_forex_data(symbol, period_days=period_days)
    else:
        df = fetch_stock_data(symbol, period_days=period_days)

    _write_cache(cache_path, df)
    return df
