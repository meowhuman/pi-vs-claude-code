---
name: sta-v2
description: Self-contained stock & forex technical analyzer with 26+ indicators (RSI, MACD, Bollinger, VWAP, Ichimoku, Parabolic SAR, etc). VPS-compatible — no external MCP server required. Use for stock/forex TA, trading signals, momentum analysis.
---

# Stock & Forex Technical Analyzer v2

Self-contained version of `sta`. Tools are **bundled** — no dependency on a local MCP server installation. Works on macOS and Linux VPS.

Supports both **US stocks / ETFs** and **forex currency pairs** (EURUSD, GBPUSD, XAUUSD, etc.) using the Tiingo API.

## Prerequisites

- `uv` installed (`pip install uv` or `brew install uv`)
- TA-Lib system library (see [references/vps-setup.md])
- `TIINGO_API_KEY` in `.env`

## Setup

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sta-v2

# First-time only
echo "TIINGO_API_KEY=your_key" > .env
uv sync
```

## Commands

All commands run from the skill root:

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sta-v2
```

| Command      | Stock Usage                                 | Forex Usage                                  | Description                      |
| ------------ | ------------------------------------------- | -------------------------------------------- | -------------------------------- |
| `indicators` | `uv run scripts/main.py indicators AAPL`    | `uv run scripts/main.py indicators EURUSD`   | All 26 indicators                |
| `momentum`   | `uv run scripts/main.py momentum TSLA`      | `uv run scripts/main.py momentum GBPUSD`     | Momentum score + BUY/SELL signal |
| `combined`   | `uv run scripts/main.py combined NVDA 180d` | `uv run scripts/main.py combined USDJPY 90d` | Full analysis                    |
| `volume`     | `uv run scripts/main.py volume MSFT`        | *(not supported, forex has no volume)*       | Volume indicators                |
| `trend`      | `uv run scripts/main.py trend GOOG`         | `uv run scripts/main.py trend XAUUSD`        | Parabolic SAR, Ichimoku, TRIX    |
| `price`      | `uv run scripts/main.py price AAPL`         | `uv run scripts/main.py price EURUSD`        | Current price data               |
| `list`       | `uv run scripts/main.py list`               | `uv run scripts/main.py list`                | List all indicators              |
| `health`     | `uv run scripts/main.py health`             | `uv run scripts/main.py health`              | Check config/tools               |

Optional 3rd argument: period (default `365d`). Options: `30d`, `90d`, `180d`, `365d`, `2y`.

## Examples

```bash
# Quick RSI/MACD check on Apple stock
uv run scripts/main.py indicators AAPL

# Full analysis for trade decision
uv run scripts/main.py combined TSLA 180d

# Momentum signal
uv run scripts/main.py momentum NVDA

# --- Forex Examples ---
# EUR/USD full technical analysis
uv run scripts/main.py indicators EURUSD

# GBP/USD momentum score
uv run scripts/main.py momentum GBPUSD

# USD/JPY combined analysis (90 days)
uv run scripts/main.py combined USDJPY 90d

# XAU/USD (Gold) trend indicators
uv run scripts/main.py trend XAUUSD
```

## Forex Support

- **Supported pairs**: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, EURGBP, EURAUD, USDSGD, USDHKD, USDCNY, XAUUSD, XAGUSD, and any valid 6-char Tiingo FX pair
- **Detection**: 6-character all-alpha tickers are auto-detected as forex (e.g. `EURUSD`)
- **Data source**: Tiingo FX API (`/tiingo/fx/{pair}/prices`)
- **Volume indicators skipped**: Forex has no volume data. The following are auto-skipped: OBV, MFI, Volume_Oscillator, AD_Line, Chaikin_Oscillator, Force_Index, NVI, PVI, VWMA, Klinger_Oscillator
- **Supported indicators**: All price-based indicators work normally (RSI, MACD, Bollinger, ATR, ADX, CCI, Stochastic, Williams%R, VWAP, TRIX, Parabolic SAR, Keltner Channels, Ichimoku, Ease of Movement)

## Differences from sta (v1)

|                | sta (v1)                                 | sta-v2                             |
| -------------- | ---------------------------------------- | ---------------------------------- |
| Tools source   | External MCP server (hardcoded Mac path) | Bundled in `scripts/tools/`        |
| VPS compatible | No                                       | Yes                                |
| venv location  | `venv/` (EBADF risk)                     | `.venv/` (gitignored)              |
| Entry pattern  | `os.execv` re-exec                       | Direct `uv run`                    |
| Config         | `.env` in skill root                     | `.env` in skill root               |
| Forex support  | No                                       | Yes (auto-detected, Tiingo FX API) |

## Resources

- `scripts/main.py` — Main entry point
- `scripts/tools/stock_ta_tool.py` — Core TA + data fetch
- `scripts/tools/advanced_indicators.py` — 16 advanced indicators
- `scripts/tools/volume_indicators.py` — Volume analysis
- `references/vps-setup.md` — VPS installation guide
