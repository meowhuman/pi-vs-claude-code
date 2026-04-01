#!/usr/bin/env python3
"""
CCXT Crypto Price Tracker
Fetches live prices from any CCXT-supported exchange.
Usage: python get_prices.py [coins...] [--group GROUP] [--exchange EXCHANGE] [--quote QUOTE] [--json] [--limit N]
"""

import json
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: uv pip install -r requirements.txt")
    sys.exit(1)

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "coins_config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"groups": {}}


def get_coins(args, config: dict) -> list[str]:
    if args.coins:
        return [c.upper() for c in args.coins]

    groups = config.get("groups", {})
    if args.group == "all":
        seen = set()
        coins = []
        for g in groups.values():
            for c in g:
                if c not in seen:
                    seen.add(c)
                    coins.append(c)
        return coins

    return groups.get(args.group, [])


async def fetch_tickers(exchange, symbols: list[str]) -> dict:
    """Batch fetch tickers where possible, fallback to individual."""
    try:
        # Try batch fetch first (much faster)
        tickers = await exchange.fetch_tickers(symbols)
        return tickers
    except Exception:
        # Fallback: fetch individually
        tickers = {}
        tasks = [exchange.fetch_ticker(s) for s in symbols if s in exchange.markets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for symbol, result in zip(symbols, results):
            if not isinstance(result, Exception):
                tickers[symbol] = result
        return tickers


async def get_prices(
    exchange_id: str,
    quote: str,
    coins: list[str],
) -> list[dict]:
    exchange_class = getattr(ccxt, exchange_id, None)
    if not exchange_class:
        print(f"ERROR: Unknown exchange '{exchange_id}'")
        sys.exit(1)

    exchange = exchange_class({"enableRateLimit": True})
    results = []

    try:
        await exchange.load_markets()

        # Build valid symbols
        valid_symbols = []
        missing = []
        for coin in coins:
            symbol = f"{coin}/{quote}"
            if symbol in exchange.markets:
                valid_symbols.append(symbol)
            else:
                missing.append(coin)

        # Fetch valid tickers
        tickers = await fetch_tickers(exchange, valid_symbols)

        for coin in coins:
            symbol = f"{coin}/{quote}"
            if coin in missing:
                results.append({"symbol": coin, "error": f"Not on {exchange_id}"})
                continue

            ticker = tickers.get(symbol)
            if not ticker:
                results.append({"symbol": coin, "error": "No data returned"})
                continue

            results.append({
                "symbol": coin,
                "price": ticker.get("last"),
                "change_24h": ticker.get("percentage"),
                "volume_24h": ticker.get("quoteVolume"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
            })

    finally:
        await exchange.close()

    return results


def fmt_price(price) -> str:
    if price is None:
        return "N/A"
    if price >= 1000:
        return f"${price:,.2f}"
    if price >= 1:
        return f"${price:.4f}"
    if price >= 0.0001:
        return f"${price:.6f}"
    return f"${price:.8f}"


def fmt_change(change) -> str:
    if change is None:
        return "N/A"
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change):.2f}%"


def fmt_volume(volume) -> str:
    if volume is None:
        return "N/A"
    if volume >= 1_000_000_000:
        return f"${volume/1_000_000_000:.2f}B"
    if volume >= 1_000_000:
        return f"${volume/1_000_000:.2f}M"
    return f"${volume:,.0f}"


def print_table(results: list[dict], exchange: str, quote: str, limit: int = None):
    if limit:
        results = results[:limit]

    rows = []
    errors = []

    for r in results:
        if "error" in r:
            errors.append(r)
            continue
        change = r.get("change_24h")
        rows.append([
            r["symbol"],
            fmt_price(r.get("price")),
            fmt_change(change),
            fmt_volume(r.get("volume_24h")),
            fmt_price(r.get("high_24h")),
            fmt_price(r.get("low_24h")),
        ])

    print(f"\n{'═' * 72}")
    print(f"  Crypto Prices  │  Exchange: {exchange}  │  Quote: {quote}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═' * 72}")

    headers = ["Symbol", "Price", "24h Change", "Volume", "24h High", "24h Low"]
    if HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="simple", stralign="right", numalign="right"))
    else:
        print(f"{'Symbol':<10} {'Price':>14} {'24h Change':>12} {'Volume':>14} {'High':>14} {'Low':>14}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<10} {row[1]:>14} {row[2]:>12} {row[3]:>14} {row[4]:>14} {row[5]:>14}")

    if errors:
        print(f"\n⚠️  Not found on {exchange}: {', '.join(e['symbol'] for e in errors)}")

    print(f"\nTotal: {len(rows)} coins fetched, {len(errors)} not found")


async def main():
    parser = argparse.ArgumentParser(description="CCXT Crypto Price Tracker")
    parser.add_argument("coins", nargs="*", help="Coin symbols (e.g. BTC ETH SOL)")
    parser.add_argument("--exchange", default="binance", help="CCXT exchange ID (default: binance)")
    parser.add_argument("--quote", default="USDT", help="Quote currency (default: USDT)")
    parser.add_argument(
        "--group",
        choices=["top50", "solana", "defi", "meme", "layer1", "layer2", "all"],
        default="all",
        help="Predefined coin group (default: all)",
    )
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output as JSON")
    parser.add_argument("--limit", type=int, help="Limit number of results")
    args = parser.parse_args()

    config = load_config()
    coins = get_coins(args, config)

    if not coins:
        print("No coins found. Use --group or specify coins directly.")
        sys.exit(1)

    if args.limit:
        coins = coins[: args.limit]

    print(f"Fetching {len(coins)} coins from {args.exchange}...", file=sys.stderr)

    results = await get_prices(args.exchange, args.quote, coins)

    if args.json_out:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_table(results, args.exchange, args.quote)


if __name__ == "__main__":
    asyncio.run(main())
