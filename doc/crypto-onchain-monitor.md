# Crypto Onchain Monitor — User Guide

A Pi extension that turns your terminal into a live cross-chain capital flow
intelligence terminal. Uses 100% free public APIs — no API keys required.

---

## Overview

**File:** `extensions/crypto-onchain-monitor.ts`
**Theme:** cyberpunk
**APIs:** DeFiLlama · DexScreener · CoinGecko (all free, no keys)

Monitors:
- Chain TVL rankings and 24h/7d changes across all major chains
- Cross-chain bridge volumes and net capital flows
- Stablecoin supply, chain distribution, and peg health (USDT, USDC, DAI, FRAX…)
- Real World Asset (RWA) protocols (Ondo, Centrifuge, Maple, Superstate…)
- DEX trading activity and hot pairs
- Protocol-level capital inflows and outflows

---

## Quick Start

```bash
# Standalone extension
just ext-onchain

# With agent-chain pipeline
just ext-onchain-chain
```

Or directly:
```bash
pi -e extensions/crypto-onchain-monitor.ts
```

---

## Tools Reference

| Tool | Description | Key Params |
|------|-------------|-----------|
| `get_chain_tvl` | TVL rankings for all chains (DeFiLlama) | `top_n`, `chain` |
| `get_bridge_flows` | Cross-chain bridge volumes (DeFiLlama Bridges) | `top_n` |
| `get_stablecoin_data` | Stablecoin supply and peg health | `focus` |
| `get_rwa_protocols` | RWA protocol TVL and metrics | `min_tvl_usd` |
| `get_dex_activity` | Hot DEX pairs (DexScreener) | `query`, `chain` |
| `get_protocol_flows` | Protocol inflow/outflow ranking | `category`, `sort_by`, `top_n` |
| `spawn_monitor_team` | Launch 5-pane tmux monitoring team | `session`, `model` |

### `get_stablecoin_data` focus modes
| Mode | Shows |
|------|-------|
| `by-stablecoin` (default) | Top stablecoins by supply with peg price |
| `by-chain` | Stablecoin supply distributed across chains |
| `peg-deviations` | Stablecoins deviating from $1.00 |

### `get_dex_activity` chains
`ethereum` · `bsc` · `arbitrum` · `base` · `polygon` · `solana` · `all`

### `get_protocol_flows` categories
`Lending` · `DEX` · `Liquid Staking` · `Bridge` · `Yield`

---

## Commands

| Command | Description |
|---------|-------------|
| `/onchain-status` | Fetch live TVL + stablecoin snapshot |
| `/onchain-refresh` | Force-refresh cached data (cache TTL: 5 min) |

---

## Footer

The footer shows a live bar with:
```
⛓ ONCHAIN  TVL: $123.4B  SC: $175.2B  Ethereum · Tron · BSC       5m ago
```

- **TVL** — Total DeFi TVL across all chains
- **SC** — Total stablecoin market cap
- **Top 3 chains** by TVL
- **Cache age** — how stale the data is

---

## Tmux Monitor Team

`spawn_monitor_team` creates a tmux session with 5 parallel Pi agent windows:

| Window | Name | Focus |
|--------|------|-------|
| 0 | `chain-tvl` | DeFiLlama chain TVL, 24h changes, rotation trends |
| 1 | `bridge-flows` | Bridge volumes, net chain flows, unusual activity |
| 2 | `stablecoin-rwa` | Stablecoin peg health, RWA protocol TVL |
| 3 | `dex-activity` | DexScreener pairs, CoinGecko global stats |
| 4 | `orchestrator` | Synthesis — executive briefing (uses Claude Sonnet) |

```bash
# Attach to the team session
tmux attach -t onchain-monitor

# Switch windows: Ctrl+B then 0–4
# Detach: Ctrl+B then d
```

Default model: `anthropic/claude-haiku-4-5-20251001` (fast + cheap for monitoring)
Override: pass `model` param to `spawn_monitor_team`

---

## Agent Chain Pipeline

Two chains are available via `just ext-onchain-chain` + `/chain` selector:

### `onchain-monitor` (4 steps)
```
onchain-scout → capital-flow-analyst → rwa-stable-monitor → chain-reporter
```
1. **onchain-scout** — Fetches raw data from all APIs via bash/curl
2. **capital-flow-analyst** — Cross-chain rotation, bridge nets, protocol flows
3. **rwa-stable-monitor** — Stablecoin peg health, RWA institutional signals
4. **chain-reporter** — Synthesizes full onchain intelligence report

### `onchain-quick` (2 steps)
```
onchain-scout → chain-reporter
```
Fast 2-step version for quick snapshots.

---

## Agent Files

| File | Role |
|------|------|
| `.pi/agents/onchain-scout.md` | Data fetcher — curl + python3 API calls |
| `.pi/agents/capital-flow-analyst.md` | Flow analyst — rotation & bridge analysis |
| `.pi/agents/rwa-stable-monitor.md` | RWA/stablecoin specialist |
| `.pi/agents/chain-reporter.md` | Report writer — structured intelligence output |

---

## Claude Code Skill

Use `/crypto-onchain-monitor` in Claude Code for CC-based monitoring.

```
/crypto-onchain-monitor              # Full onchain report
/crypto-onchain-monitor rwa          # Focus on RWA protocols
/crypto-onchain-monitor stablecoin   # Focus on peg health
/crypto-onchain-monitor bridge       # Focus on bridge flows
/crypto-onchain-monitor spawn team   # Launch tmux team via Bash
```

The skill uses `WebFetch` to call the same free APIs and produces an identical
structured report without needing the Pi extension running.

---

## Free API Reference

All APIs require no registration or API keys.

| Service | Base URL | Rate Limit |
|---------|----------|-----------|
| DeFiLlama TVL | `https://api.llama.fi` | ~300 req/5min |
| DeFiLlama Bridges | `https://bridges.llama.fi` | ~300 req/5min |
| DeFiLlama Stablecoins | `https://stablecoins.llama.fi` | ~300 req/5min |
| DexScreener | `https://api.dexscreener.com` | ~300 req/min |
| CoinGecko | `https://api.coingecko.com/api/v3` | ~30 req/min |

Data freshness: DeFiLlama updates ~hourly, DexScreener is near real-time.
Extension cache TTL: 5 minutes (configurable via `CACHE_TTL` in source).

---

## Analysis Framework

### Capital Flow Signals

| Observation | Interpretation |
|-------------|---------------|
| DeFi TVL rising + stablecoin supply stable | Risk-on: capital deploying into DeFi |
| Stablecoin supply growing fast | Risk-off: cash accumulation |
| Bridge volume spike >3x normal | Major cross-chain capital movement event |
| L2 TVL gaining vs. Ethereum L1 | Layer 2 migration in progress |
| RWA TVL growing >10%/week | Institutional crypto adoption accelerating |
| Lending protocol TVL rising | Leverage increasing, risk appetite up |
| Stable peg deviation >0.5% | Stablecoin stress — monitor closely |

### Alert Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Stablecoin peg deviation | >0.5% | ALERT — potential depeg risk |
| Protocol TVL drop | >20% in 24h | INVESTIGATE — possible exploit |
| Bridge volume | >$5B/day | NOTABLE — major capital event |
| Chain TVL drop | >15% in 7d | ECOSYSTEM CONCERN |
| RWA TVL spike | >20% in 30d | INSTITUTIONAL SIGNAL |

---

## Example Agent Prompts

```
# Quick market snapshot
"Show me the current state of DeFi — chain TVL, stablecoin supply, and any anomalies"

# Capital flow analysis
"Where is capital moving in the last 24 hours? Which chains are gaining vs losing?"

# Stablecoin health check
"Check all major stablecoin peg prices and flag any deviations"

# RWA institutional intelligence
"What's the current state of RWA protocols? Any significant TVL changes?"

# Full pipeline via spawn_monitor_team
"Launch the monitor team and watch all chains in parallel"
```

---

## Architecture

```
crypto-onchain-monitor.ts
├── session_start        → apply theme, boot cache refresh, set footer
├── before_agent_start   → inject onchain expert system prompt
├── get_chain_tvl        → DeFiLlama /v2/chains
├── get_bridge_flows     → DeFiLlama bridges.llama.fi/bridges
├── get_stablecoin_data  → stablecoins.llama.fi/stablecoins + /stablecoinchains
├── get_rwa_protocols    → DeFiLlama /protocols (filtered)
├── get_dex_activity     → DexScreener /latest/dex/search
├── get_protocol_flows   → DeFiLlama /protocols (sorted by change)
├── spawn_monitor_team   → tmux 5-window session via spawnSync
├── /onchain-status      → live quick snapshot command
└── /onchain-refresh     → force cache clear + refetch
```
