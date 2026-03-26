# Polymarket Agent — User Guide

A specialized Pi extension that turns your terminal into a full Polymarket trading
terminal. Wraps `pm.py`, `trade.py`, `search.py`, `analyze.py`, and monitoring scripts
into typed Pi tools with a live footer, expert system prompt, and keyboard-friendly UI.

---

## Prerequisites

1. **Pi Coding Agent** installed and on your `$PATH` (`pi --version` should work)
2. **polymarket-trader** project cloned locally with its Python venv set up:
   ```bash
   cd /path/to/polymarket-trader
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. A `.env` file inside polymarket-trader with your keys:
   ```
   POLYGON_PRIVATE_KEY=your_key
   BUILDER_WALLET_ADDRESS=0x...
   WALLET_ADDRESS=0x...
   MAX_AUTO_AMOUNT=50
   ```

---

## Setup

### Option A — Environment variable (recommended)

```bash
export POLYMARKET_DIR=/path/to/polymarket-trader
pi -e extensions/polymarket.ts
```

Add the export to your shell profile (`~/.zshrc` or `~/.bashrc`) so it persists.

### Option B — justfile shortcut

```bash
just ext-polymarket
```

This runs `pi -e extensions/polymarket.ts -e extensions/theme-cycler.ts`.

### Option C — Configure at runtime

Launch without setting `POLYMARKET_DIR`, then inside Pi:

```
/pm-config
```

A prompt will appear — paste the full path to your polymarket-trader directory and press Enter.

---

## The Footer

When running, a two-line footer appears at the bottom of the terminal:

```
◆ Polymarket | ~/path/to/polymarket-trader     tools: 7 | last: analyze_market (12s ago)
ctx [######----] 61%                                                            (main)
```

- **Line 1**: scripts directory + running tool call count + most recently used tool
- **Line 2**: context window usage meter + current git branch

---

## Commands

| Command | What it does |
|---------|-------------|
| `/pm-config` | Interactively set the polymarket-trader directory |
| `/pm-help` | Show a quick reference overlay of all tools |
| `/theme` | Cycle through themes (if theme-cycler is stacked) |

---

## All Tools

### Portfolio

| Tool | Description |
|------|-------------|
| `portfolio_dashboard` | Current positions, unrealized P&L, account balance |
| `portfolio_close` | Exit a position (built-in liquidity check) |
| `portfolio_report` | Full P&L breakdown with win/loss rates |
| `portfolio_rebalance` | Equal-weight rebalancing suggestions |
| `portfolio_liquidity` | Check bid-ask spread before trading |

**Examples:**

```
Show me my portfolio
Close position 0xabc123... automatically
Give me a detailed P&L report for account 2
How liquid is 0xabc123... on the Yes side?
```

---

### Trading

| Tool | Description |
|------|-------------|
| `trade_market` | Market buy or sell at current price |
| `trade_limit` | Place a limit order at a specific price |
| `trade_orders` | View all open/pending orders |
| `trade_cancel` | Cancel one order or all orders |
| `trade_set_alert` | Set a Take Profit or Stop Loss level |

**Examples:**

```
Buy $25 of Yes on market 0xabc123...
Place a limit buy on 0xabc123... Yes at $0.42 for $50
Set a take profit at $0.75 for my Yes position on 0xabc123...
Set a stop loss at $0.25 for my Yes position on 0xabc123...
Cancel all open orders
```

> **Note:** TP/SL alerts are stored in `scripts/cache/tp_sl_alerts.json`.
> To auto-execute them, run `python scripts/trade.py monitor` separately —
> the agent itself does not start a background monitor.

---

### Search

| Tool | Description |
|------|-------------|
| `search_markets` | Search by keyword, category, filters |
| `market_detail` | Full info for a condition ID or URL slug |

**Search categories:** `crypto` `sports` `politics` `economy` `tech` `world` `entertainment`

**Examples:**

```
Search for Trump markets closing in the next 14 days with volume over $50k
Find crypto markets with probability between 20% and 80%
Get details for market 0xabc123...
Get details for the slug "will-bitcoin-hit-100k-2025"
```

---

### Analysis

Always analyze before entering a position.

| Tool | Description |
|------|-------------|
| `analyze_market` | Order book depth, trade history, price chart |
| `analyze_whales` | Large holders and their direction |
| `analyze_wallet` | Profile a wallet: Smart Money / Market Maker / Whale / Loser / Retail |
| `analyze_odds` | Historical probability over 7/14/30 day periods |
| `analyze_kelly` | Kelly Criterion optimal position size |
| `analyze_signal` | Composite signal: whale direction + momentum + buy ratio |
| `analyze_distribution` | Contrarian score 0–100 (>70 = strong contrarian edge) |
| `analyze_insider` | Detect suspicious pre-spike trading (CRITICAL/HIGH/MEDIUM/LOW) |
| `analyze_holders` | Full holder distribution via Goldsky subgraph (no 20-person cap) |

**Examples:**

```
Do a deep analysis of market 0xabc123...
Who are the whales on 0xabc123... with positions over $5k?
Profile wallet 0xdef456...
Show me historical odds for event slug "us-election-2026"
How much should I bet on 0xabc123... if I think there's a 65% chance? My bankroll is $500.
What's the trading signal for 0xabc123...?
Check the distribution score on 0xabc123...
Is there any insider activity on 0xabc123...?
Show me the complete holder breakdown for 0xabc123...
```

---

### Monitoring

| Tool | Description |
|------|-------------|
| `scan_insider_bulk` | Async scan of hundreds of markets for insider activity |
| `insider_detail` | ASCII price chart + insider timeline for one market |

**Examples:**

```
Scan the top 200 politics markets for insider activity, minimum volume $100k
Show me the insider detail chart for 0xabc123... around December 9th
```

---

## Recommended Workflow

### Before entering a trade

```
1. search_markets       — find candidate markets
2. market_detail        — confirm the market is active and liquid
3. analyze_market       — check order book, price history
4. analyze_whales       — see what large holders are doing
5. analyze_insider      — confirm no suspicious pre-position activity
6. analyze_signal       — get the composite directional signal
7. analyze_distribution — check contrarian score if signal is mixed
8. analyze_kelly        — calculate position size (use quarter-Kelly to start)
```

### Entering a position

```
9.  trade_market or trade_limit   — execute the trade
10. trade_set_alert (tp)          — set take profit
11. trade_set_alert (sl)          — set stop loss
```

### Managing positions

```
portfolio_dashboard     — check current state
portfolio_liquidity     — before closing, check the spread
portfolio_close         — exit with --auto flag for non-interactive
portfolio_report        — review P&L
```

---

## Multi-Account Setup

Add accounts to your `.env`:

```
# Account 1 (default)
POLYGON_PRIVATE_KEY=...
BUILDER_WALLET_ADDRESS=0x...

# Account 2
POLYGON_PRIVATE_KEY_2=...
BUILDER_WALLET_ADDRESS_2=0x...
```

Then specify the account in your request:

```
Show portfolio for account 2
Buy $10 Yes on 0xabc123... using account 2
```

---

## Kelly Criterion — Position Sizing

The Kelly formula is the *theoretical maximum* bet. In practice:

| Fraction | Risk level | Recommended for |
|----------|-----------|-----------------|
| Full Kelly | Aggressive | Never |
| Half Kelly | Moderate | Experienced traders only |
| Quarter Kelly | Conservative | Default starting point |

Ask the agent:
```
Calculate Kelly for 0xabc123... — I estimate 60% chance, bankroll $200, use quarter Kelly
```

---

## Insider Risk Levels

| Level | Score | Action |
|-------|-------|--------|
| CRITICAL | 70–100 | Avoid — strong insider signal |
| HIGH | 50–69 | Proceed with extreme caution |
| MEDIUM | 30–49 | Investigate further |
| LOW | 0–29 | Normal market activity |

---

## Troubleshooting

**"POLYMARKET_DIR not configured"**
Run `/pm-config` and enter the path to your polymarket-trader directory.

**"Script not found"**
The extension expects scripts at `$POLYMARKET_DIR/scripts/pm.py` etc.
Verify the directory structure matches polymarket-trader v4.x.

**"venv not found" / import errors**
Activate the venv manually once to install deps:
```bash
cd $POLYMARKET_DIR && source venv/bin/activate && pip install -r requirements.txt
```
The extension auto-detects and uses `venv/bin/python` if present.

**Trade not executing**
- Check balance: `portfolio_dashboard`
- Minimum trade: $1 USDC
- Check market is still active: `market_detail`

**TP/SL not triggering**
The agent sets alerts but does not run the background monitor.
Start it in a separate terminal:
```bash
cd $POLYMARKET_DIR && source venv/bin/activate && python scripts/trade.py monitor
```
