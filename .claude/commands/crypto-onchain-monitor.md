# Crypto Onchain Monitor — Claude Code Meta-Skill

Monitor cross-chain crypto activity and capital flows using free public APIs.
Spawns a tmux agent team for parallel monitoring when requested.

## Usage

```
/crypto-onchain-monitor [focus]
```

Examples:
- `/crypto-onchain-monitor` — full onchain report
- `/crypto-onchain-monitor chain tvl` — chain TVL focus
- `/crypto-onchain-monitor stablecoin peg health` — stablecoin monitor
- `/crypto-onchain-monitor rwa institutional` — RWA protocol focus
- `/crypto-onchain-monitor spawn team` — launch tmux parallel team

---

## Step 1 — Parse Intent

Based on `$ARGUMENTS`:
- **No args / "full"** → run complete onchain intelligence report
- **"chain" / "tvl"** → focus on chain TVL analysis
- **"bridge" / "flow"** → focus on cross-chain bridge flows
- **"stablecoin" / "peg"** → focus on stablecoin health
- **"rwa" / "institutional"** → focus on RWA protocols
- **"dex" / "trading"** → focus on DEX activity
- **"spawn" / "team" / "tmux"** → spawn tmux agent team

---

## Step 2 — Fetch Live Data

Use WebFetch to call these free APIs (no API keys required):

### Chain TVL (DeFiLlama)
```
https://api.llama.fi/v2/chains
```
Parse: sort by tvl descending, show top 20 with name, tvl, change_1d, change_7d

### Bridge Activity (DeFiLlama Bridges)
```
https://bridges.llama.fi/bridges?includeChains=true
```
Parse: sort by volumePrevDay, show top 15 with displayName, volumePrevDay, chains

### Stablecoin Data (DeFiLlama)
```
https://stablecoins.llama.fi/stablecoins?includePrices=true
https://stablecoins.llama.fi/stablecoinchains
```
Parse: sort by circulating.peggedUSD, show price deviation from $1.00

### Protocol Flows (DeFiLlama)
```
https://api.llama.fi/protocols
```
Parse: filter tvl > $100M, sort by change_1d for top gainers/losers

### Global Market (CoinGecko)
```
https://api.coingecko.com/api/v3/global
```
Parse: total_market_cap.usd, total_value_locked.usd, market_cap_percentage

### DEX Activity (DexScreener)
```
https://api.dexscreener.com/latest/dex/search?q=WETH
https://api.dexscreener.com/latest/dex/search?q=USDC
```
Parse: sort pairs by volume.h24, show priceUsd, priceChange.h24, liquidity.usd

---

## Step 3 — Analysis Framework

Apply this framework to interpret the data:

### Capital Flow Signals
| Observation | Signal |
|-------------|--------|
| DeFi TVL rising + stablecoin supply stable | Risk-on: capital deploying |
| Stablecoin supply growing fast | Risk-off: cash accumulation |
| Bridge volume spike >3x | Major capital movement event |
| L2 gaining TVL vs Ethereum | Layer 2 migration in progress |
| RWA TVL growing >10%/week | Institutional adoption accelerating |

### Alert Thresholds
- Stablecoin peg deviation > 0.5% → **ALERT**
- Protocol TVL drop > 20% in 24h → **INVESTIGATE** (exploit?)
- Bridge volume > $5B/day → **NOTABLE** event
- Chain TVL drop > 15% in 7d → **ECOSYSTEM CONCERN**

---

## Step 4 — Spawn tmux Team (if requested)

If user wants "spawn team" or "tmux", use Bash to:

```bash
# Kill existing session
tmux kill-session -t onchain-monitor 2>/dev/null || true

# Create session
tmux new-session -d -s onchain-monitor -n chain-tvl

# Window 0: Chain TVL monitor
tmux send-keys -t onchain-monitor:0 "pi -p --no-extensions --model anthropic/claude-haiku-4-5-20251001 --tools bash,read 'Fetch https://api.llama.fi/v2/chains via curl, show top 20 chains by TVL with 24h changes, then analyze capital rotation trends' ; read" Enter

# Window 1: Bridge flows
tmux new-window -t onchain-monitor -n bridge-flows
tmux send-keys -t "onchain-monitor:1" "pi -p --no-extensions --model anthropic/claude-haiku-4-5-20251001 --tools bash,read 'Fetch https://bridges.llama.fi/bridges?includeChains=true via curl, analyze top 15 bridges by volume, identify net capital flows between chains' ; read" Enter

# Window 2: Stablecoin/RWA
tmux new-window -t onchain-monitor -n stablecoin-rwa
tmux send-keys -t "onchain-monitor:2" "pi -p --no-extensions --model anthropic/claude-haiku-4-5-20251001 --tools bash,read 'Fetch stablecoin data from https://stablecoins.llama.fi/stablecoins?includePrices=true and RWA from https://api.llama.fi/protocols (filter for ondo centrifuge maple superstate). Report peg health and institutional adoption signals' ; read" Enter

# Window 3: DEX activity
tmux new-window -t onchain-monitor -n dex-activity
tmux send-keys -t "onchain-monitor:3" "pi -p --no-extensions --model anthropic/claude-haiku-4-5-20251001 --tools bash,read 'Fetch DEX pairs from https://api.dexscreener.com/latest/dex/search?q=WETH and https://api.dexscreener.com/latest/dex/search?q=USDC via curl. Show top pairs by 24h volume with price changes. Identify unusual activity.' ; read" Enter

# Window 4: Orchestrator
tmux new-window -t onchain-monitor -n orchestrator
tmux send-keys -t "onchain-monitor:4" "pi -p --no-extensions --model anthropic/claude-sonnet-4-6 --tools bash,read 'You are the onchain orchestrator. Fetch comprehensive data: (1) https://api.llama.fi/protocols - top 10 by TVL, top 5 gainers/losers. (2) https://api.coingecko.com/api/v3/global - global stats. Produce a 5-bullet executive onchain intelligence briefing.' ; read" Enter

# Select orchestrator window
tmux select-window -t onchain-monitor:4

echo "Team launched! Attach with: tmux attach -t onchain-monitor"
echo "Switch windows: Ctrl+B then 0-4"
```

---

## Step 5 — Output Report

Generate this structured report:

```markdown
# 🔗 Onchain Intelligence Report
**Generated:** [UTC timestamp]
**Source:** DeFiLlama · DexScreener · CoinGecko

---

## Executive Summary
[3-4 sentences: current DeFi state, key flows, market phase]
**Market Phase:** [Risk-on / Risk-off / Neutral / Rotation]

---

## Chain TVL Rankings (Top 10)
| Rank | Chain | TVL | 24h | 7d |
[table]

## Bridge Activity (Top 5)
| Bridge | 24h Vol | Routes |
[table]

## Stablecoin Health
Total: $XXB
| Asset | Supply | Peg | Status |
[table — flag any deviation >0.2%]

## RWA Protocols
Total RWA TVL: $XXM
[Top protocols with TVL and changes]

## Protocol Flows
📈 Top Inflows: [3 protocols with %]
📉 Top Outflows: [3 protocols with %]

## Key Signals
1. [Actionable insight with $ data]
2. [Actionable insight with $ data]
3. [Actionable insight with $ data]

## 🚨 Alerts
[Any issues — or "No alerts ✓"]
```

---

## Free API Reference

| API | Endpoint | Data |
|-----|----------|------|
| DeFiLlama | api.llama.fi/v2/chains | Chain TVL |
| DeFiLlama | api.llama.fi/protocols | Protocol TVL/flows |
| DeFiLlama | bridges.llama.fi/bridges | Bridge volumes |
| DeFiLlama | stablecoins.llama.fi/stablecoins | Stablecoin supply |
| DeFiLlama | stablecoins.llama.fi/stablecoinchains | Chain SC distribution |
| DexScreener | api.dexscreener.com/latest/dex/search?q=TOKEN | DEX pairs |
| CoinGecko | api.coingecko.com/api/v3/global | Global market |
| CoinGecko | api.coingecko.com/api/v3/simple/price | Token prices |

All APIs are completely free with no authentication required.
Rate limits: DeFiLlama ~300 req/5min, CoinGecko ~30 req/min (free tier), DexScreener ~300 req/min.
