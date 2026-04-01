# CCXT Exchange Reference

## Common Exchange IDs

| Exchange    | ID         | Notes                |
| ----------- | ---------- | -------------------- |
| Binance     | `binance`  | Most coins, default  |
| Coinbase    | `coinbase` | US-focused           |
| Bybit       | `bybit`    | Good for derivatives |
| OKX         | `okx`      | Wide selection       |
| Gate.io     | `gate`     | Many altcoins        |
| KuCoin      | `kucoin`   | Small cap coins      |
| Kraken      | `kraken`   | EUR pairs            |
| HTX (Huobi) | `htx`      | Asia focus           |

## Timeframes

CCXT supports these timeframes (varies by exchange):

| Timeframe | Description | Use Case         |
| --------- | ----------- | ---------------- |
| `1s`      | 1 second    | High-frequency   |
| `1m`      | 1 minute    | Scalping         |
| `3m`      | 3 minutes   | Short-term       |
| `5m`      | 5 minutes   | Day trading      |
| `15m`     | 15 minutes  | Day trading      |
| `30m`     | 30 minutes  | Swing trading    |
| `1h`      | 1 hour      | Swing trading    |
| `2h`      | 2 hours     | Medium-term      |
| `4h`      | 4 hours     | Medium-term      |
| `6h`      | 6 hours     | Position trading |
| `8h`      | 8 hours     | Position trading |
| `12h`     | 12 hours    | Long-term        |
| `1d`      | 1 day       | Long-term        |
| `3d`      | 3 days      | Macro analysis   |
| `1w`      | 1 week      | Macro analysis   |
| `1M`      | 1 month     | Macro analysis   |

### Tiingo Free vs CCXT Timeframes

**Tiingo Free (Stocks):**

- Daily data only
- No intraday timeframes

**CCXT (Crypto):**

- Full intraday support: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h
- Daily and higher: 1d, 3d, 1w, 1M
- **Advantage**: Real-time intraday analysis for crypto

## Solana Token Notes

Many Solana meme coins (BONK, WIF, BOME, etc.) are listed on:

- Binance: most major ones
- Gate.io / KuCoin: smaller ones
- Use `--exchange gate` for obscure Solana tokens

## Adding New Coins

Edit `scripts/coins_config.json`:

```json
{
  "groups": {
    "custom": ["NEWCOIN1", "NEWCOIN2"]
  }
}
```

Then use: `python scripts/get_prices.py --group custom`

## Quote Currencies

- `USDT` — Tether (most liquid, default)
- `USDC` — USD Coin
- `BTC` — Bitcoin pairs
- `ETH` — Ethereum pairs
- `BNB` — BNB pairs (Binance only)

## Technical Indicators

All 26 indicators from STA are adapted for crypto:

### Trend

- SMA, EMA, MACD, Parabolic SAR, TRIX, Ichimoku Cloud

### Momentum

- RSI, Stochastic, Williams %R, CCI

### Volatility

- Bollinger Bands, ATR, ADX, Keltner Channels

### Volume

- VWAP, OBV, MFI, Volume Oscillator, AD Line, Chaikin Oscillator, VWMA, Klinger Oscillator

### Price-Volume

- Force Index, Ease of Movement, NVI, PVI

## Examples

```bash
# Single coins
python scripts/get_prices.py BTC ETH SOL

# Solana ecosystem
python scripts/get_prices.py --group solana

# Top 50 from Gate.io
python scripts/get_prices.py --group top50 --exchange gate

# BTC pairs on Kraken
python scripts/get_prices.py BTC --exchange kraken --quote EUR

# JSON for piping
python scripts/get_prices.py --group defi --json | jq '.[].price'

# Quick top 10
python scripts/get_prices.py --group top50 --limit 10

# OHLCV data
python scripts/get_ohlcv.py BTC --timeframe 1h --limit 100

# Technical indicators
python scripts/get_indicators.py BTC --timeframe 1h

# Intraday analysis (not available with Tiingo free)
python scripts/get_indicators.py BTC --timeframe 5m
python scripts/get_indicators.py ETH --timeframe 15m
```

## Data Format

### OHLCV Structure

```json
{
  "timestamp": 1709376000000,
  "datetime": "2024-03-02T08:00:00",
  "open": 66135.45,
  "high": 66219.77,
  "low": 65699.98,
  "close": 65979.61,
  "volume": 952.2
}
```

### Indicator Output

```json
{
  "RSI_14": {
    "value": 48.8,
    "signal": "NEUTRAL",
    "trend": "DOWN"
  },
  "MACD": {
    "macd": -72.34,
    "signal": -55.36,
    "histogram": -16.97,
    "direction": "BEARISH"
  }
}
```
