---
name: ccxt
description: Fetch live crypto prices and calculate 26+ technical indicators using CCXT. Supports intraday timeframes (1m-12h) that Tiingo free doesn't have. Use for crypto price checks, OHLCV data, and technical analysis.
---

# CCXT Crypto Technical Analysis

Fetch real-time crypto prices and calculate technical indicators from any CCXT-supported exchange. Pre-configured with top 50 coins and Solana ecosystem tokens.

## When to Use

- "What's the price of BTC/ETH/SOL?"
- "Show me crypto prices"
- "Get Solana ecosystem token prices"
- "Technical analysis for BTC on 1h timeframe"
- "Calculate RSI/MACD for ETH"
- "Check Bollinger Bands for SOL"
- "Intraday analysis (1m, 5m, 15m, 1h) for crypto"

## Quick Start

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/ccxt

# Setup (first time only)
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Commands

### 1. Get Prices

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/ccxt

# All configured coins
uv run scripts/get_prices.py

# Specific coins
uv run scripts/get_prices.py BTC ETH SOL

# By group
uv run scripts/get_prices.py --group top50
uv run scripts/get_prices.py --group solana
uv run scripts/get_prices.py --group defi

# From specific exchange
uv run scripts/get_prices.py BTC --exchange coinbase

# JSON output
uv run scripts/get_prices.py BTC --json
```

### 2. Get OHLCV Data

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/ccxt

# 1 hour candles (default)
uv run scripts/get_ohlcv.py BTC

# Different timeframes
uv run scripts/get_ohlcv.py BTC --timeframe 5m
uv run scripts/get_ohlcv.py BTC --timeframe 15m
uv run scripts/get_ohlcv.py BTC --timeframe 1h
uv run scripts/get_ohlcv.py BTC --timeframe 4h
uv run scripts/get_ohlcv.py BTC --timeframe 1d

# More candles
uv run scripts/get_ohlcv.py BTC --timeframe 1h --limit 200

# Save to CSV
uv run scripts/get_ohlcv.py BTC --csv btc_ohlcv.csv

# JSON output
uv run scripts/get_ohlcv.py BTC --json
```

**Available Timeframes** (Tiingo free doesn't have these intraday):

- `1s` - 1 second (limited exchanges)
- `1m`, `3m`, `5m`, `15m`, `30m` - Minutes
- `1h`, `2h`, `4h`, `6h`, `8h`, `12h` - Hours
- `1d`, `3d`, `1w`, `1M` - Days/Weeks/Months

### 3. Technical Indicators

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/ccxt

# All indicators for BTC on 1h
uv run scripts/get_indicators.py BTC

# Different timeframes
uv run scripts/get_indicators.py BTC --timeframe 5m
uv run scripts/get_indicators.py ETH --timeframe 15m
uv run scripts/get_indicators.py SOL --timeframe 4h

# Specific category
uv run scripts/get_indicators.py BTC --category trend
uv run scripts/get_indicators.py BTC --category momentum
uv run scripts/get_indicators.py BTC --category volume

# List all indicators
uv run scripts/get_indicators.py --list

# JSON output
uv run scripts/get_indicators.py BTC --json
```

## Available Indicators (26 Total)

### Trend (6)
SMA_20, EMA_20, MACD, Parabolic_SAR, TRIX, Ichimoku_Cloud

### Momentum (4)
RSI_14, Stochastic_14, Williams_R_14, CCI_20

### Volatility (4)
Bollinger_Bands_20, ATR_14, ADX_14, Keltner_Channels_20

### Volume (8)
VWAP, OBV, MFI_14, Volume_Oscillator, AD_Line, Chaikin_Oscillator, VWMA_20, Klinger_Oscillator

### Price-Volume (4)
Force_Index, Ease_of_Movement, NVI, PVI

## Signal Interpretation

- **RSI < 30**: Oversold  |  **RSI > 70**: Overbought
- **MACD > Signal**: Bullish momentum
- **Price > VWAP**: Buy pressure
- **ADX > 25**: Strong trend
- **Bollinger squeeze**: Breakout incoming

## Exchange Reference

| Exchange | ID | Best For |
|---|---|---|
| Binance | `binance` | Most coins (default) |
| Coinbase | `coinbase` | US-focused |
| Bybit | `bybit` | Derivatives |
| OKX | `okx` | Wide selection |
| Gate.io | `gate` | Altcoins / Solana memes |
| KuCoin | `kucoin` | Small cap |
| Kraken | `kraken` | EUR pairs |

## Resources

- `scripts/get_prices.py` — Live price fetcher
- `scripts/get_ohlcv.py` — OHLCV candlestick data
- `scripts/get_indicators.py` — 26 technical indicators
- `scripts/coins_config.json` — Coin groups (top50/solana/defi/meme/layer1/layer2)
- `references/ccxt_guide.md` — Exchange IDs and timeframe reference
