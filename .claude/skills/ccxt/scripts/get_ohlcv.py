#!/usr/bin/env python3
"""
CCXT OHLCV Data Fetcher
Fetch candlestick/OHLCV data for technical analysis.
Supports all CCXT timeframes including intraday (1m, 5m, 15m, 1h, etc.)

Usage: python get_ohlcv.py <SYMBOL> [--timeframe TF] [--limit N] [--exchange EXCHANGE]
"""

import json
import sys
import asyncio
import argparse
from datetime import datetime
from typing import Optional

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: uv pip install -r requirements.txt")
    sys.exit(1)

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Default timeframes available on most exchanges
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


def timeframe_to_seconds(timeframe: str) -> int:
    """Convert timeframe string to seconds."""
    unit = timeframe[-1]
    value = int(timeframe[:-1])

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
        'M': 2592000  # 30 days
    }

    return value * multipliers.get(unit, 3600)


async def fetch_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
    since: Optional[int] = None
) -> dict:
    """Fetch OHLCV data from exchange."""

    exchange_class = getattr(ccxt, exchange_id, None)
    if not exchange_class:
        return {"error": f"Unknown exchange '{exchange_id}'"}

    exchange = exchange_class({"enableRateLimit": True})

    try:
        await exchange.load_markets()

        # Normalize symbol
        symbol = symbol.upper()
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"

        if symbol not in exchange.markets:
            return {"error": f"Symbol '{symbol}' not found on {exchange_id}"}

        # Check if timeframe is supported
        if exchange.timeframes and timeframe not in exchange.timeframes:
            available = list(exchange.timeframes.keys()) if exchange.timeframes else []
            return {
                "error": f"Timeframe '{timeframe}' not supported",
                "available_timeframes": available
            }

        # Fetch OHLCV data
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since, limit)

        if not ohlcv:
            return {"error": "No data returned"}

        # Convert to structured format
        candles = []
        for row in ohlcv:
            candles.append({
                "timestamp": row[0],
                "datetime": datetime.fromtimestamp(row[0] / 1000).isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5])
            })

        return {
            "symbol": symbol,
            "exchange": exchange_id,
            "timeframe": timeframe,
            "candles": candles,
            "count": len(candles)
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        await exchange.close()


def convert_to_dataframe(data: dict) -> Optional[pd.DataFrame]:
    """Convert OHLCV data to pandas DataFrame."""
    if not HAS_PANDAS or "candles" not in data:
        return None

    df = pd.DataFrame(data["candles"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    return df


async def main():
    parser = argparse.ArgumentParser(description="CCXT OHLCV Fetcher")
    parser.add_argument("symbol", help="Trading pair (e.g., BTC, ETH, BTC/USDT)")
    parser.add_argument("--timeframe", default="1h", help="Candle timeframe (default: 1h)")
    parser.add_argument("--limit", type=int, default=100, help="Number of candles (default: 100)")
    parser.add_argument("--exchange", default="binance", help="Exchange ID (default: binance)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", type=str, help="Save to CSV file")
    args = parser.parse_args()

    result = await fetch_ohlcv(
        exchange_id=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit
    )

    if "error" in result:
        print(json.dumps(result, indent=2))
        sys.exit(1)

    # Save to CSV if requested
    if args.csv and HAS_PANDAS:
        df = convert_to_dataframe(result)
        if df is not None:
            df.to_csv(args.csv)
            print(f"Saved {len(df)} candles to {args.csv}")
            return

    # JSON output
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    # Table output
    candles = result["candles"]
    print(f"\n{'═' * 80}")
    print(f"  OHLCV Data │ {result['symbol']} │ {result['exchange']} │ {result['timeframe']}")
    print(f"{'═' * 80}")
    print(f"{'Time':<20} {'Open':>12} {'High':>12} {'Low':>12} {'Close':>12} {'Volume':>12}")
    print(f"{'-' * 80}")

    for c in candles[-20:]:  # Show last 20
        dt = c['datetime'][:19]
        print(f"{dt:<20} {c['open']:>12.4f} {c['high']:>12.4f} {c['low']:>12.4f} "
              f"{c['close']:>12.4f} {c['volume']:>12.4f}")

    print(f"{'-' * 80}")
    print(f"Total: {len(candles)} candles from {candles[0]['datetime']} to {candles[-1]['datetime']}")


if __name__ == "__main__":
    asyncio.run(main())
