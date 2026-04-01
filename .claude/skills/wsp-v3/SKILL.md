---
name: wsp-v3
description: Web Search Pro V3 — Unified modular web research suite. Dual-engine (Brave + Tavily) with optional Bing for Chinese content. Use when user mentions deep research, web search, forum search, Reddit, LIHKG, news search, geopolitics, trading forums, or Chinese mainland search. Replaces wsp-v2 with modular architecture and unified CLI.
---

# Web Search Pro V3

## Overview

Professional web research suite with modular architecture. Single CLI entry point replacing 31 separate V2 scripts.

### Engines

| Engine           | Purpose         | Strengths                                      |
| ---------------- | --------------- | ---------------------------------------------- |
| **Brave**        | Discovery       | Fast web/news search, good for English content |
| **Tavily**       | Extraction      | Deep content extraction, OK for Chinese sites  |
| **Bing** _(new)_ | Chinese content | Best external engine for mainland China sites  |

> Firecrawl has been **removed** (out of credit, only used in V2's layered research Layer 3).

### What You Can Search

| Category        | Coverage                                                                        |
| --------------- | ------------------------------------------------------------------------------- |
| **News**        | 15+ regional sources (tech, finance, world, HK, China, Japan, Korea, crypto...) |
| **Forums**      | Reddit, HN, LIHKG, PTT, V2EX, SO, GitHub, Quora, Product Hunt, Twitter          |
| **China**       | 知乎, 微博, 百度贴吧, 小红书, 雪球, 豆瓣, B站, 頭條                             |
| **Geopolitics** | Think tanks, expert commentary, academic, Asia-Pacific, Middle East             |
| **Trading**     | StockTwits, Bitcointalk, 4chan /biz/, 雪球                                      |

---

## Prerequisites

### API Keys (.env)

```bash
# Required (at least one search engine)
BRAVE_API_KEY_1=your_key
BRAVE_API_KEY_2=your_backup_key  # Optional
TAVILY_API_KEY=your_key

# Optional (for Chinese content)
BING_API_KEY=your_key  # Azure Bing Search v7
```

The `.env` file is auto-discovered by searching up from the skill directory.

---

## Usage — Unified CLI

All commands use `uv run scripts/wsp.py <subcommand>`.

**Working directory**: `/Volumes/Ketomuffin_mac/AI/clawdbot/skills/wsp-v3`

### News Search

```bash
# General news
uv run scripts/wsp.py news "AI breakthrough"

# By source
uv run scripts/wsp.py news "OpenAI" --source tech
uv run scripts/wsp.py news "Fed rate" --source finance
uv run scripts/wsp.py news "樓市" --source hk
uv run scripts/wsp.py news "半導體" --source china  # → Uses Bing/Tavily

# By region and freshness
uv run scripts/wsp.py news "香港" --region hk --freshness pd

# List all news sources
uv run scripts/wsp.py news --list-sources
```

### Forum Search

```bash
# Reddit (direct API — real-time, no delay)
uv run scripts/wsp.py forum reddit ClaudeCode --keyword "MCP"
uv run scripts/wsp.py forum reddit ClaudeCode --sort hot --hours 24

# Hacker News
uv run scripts/wsp.py forum hackernews --type top --count 10
uv run scripts/wsp.py forum hackernews "Claude AI" --count 10

# LIHKG, PTT, V2EX, etc. (via Brave/Tavily site: queries)
uv run scripts/wsp.py forum lihkg "AI"
uv run scripts/wsp.py forum ptt "AI"
uv run scripts/wsp.py forum v2ex "Python"

# Multi-forum search with presets
uv run scripts/wsp.py forum multi --preset tech --query "Claude AI"
uv run scripts/wsp.py forum multi --preset asia --query "AI"

# List all forums
uv run scripts/wsp.py forum --list-forums
```

### China Mainland Search

```bash
# All Chinese forums
uv run scripts/wsp.py china "AI"

# Specific forum
uv run scripts/wsp.py china "Python" --forum zhihu
uv run scripts/wsp.py china "穿搭" --forum xiaohongshu
uv run scripts/wsp.py china "A股" --forum xueqiu

# Xueqiu shortcut (investment)
uv run scripts/wsp.py china "茅台" --xueqiu

# List Chinese forums with search effectiveness
uv run scripts/wsp.py china --list-forums
```

### Geopolitics Search

```bash
# Think tanks
uv run scripts/wsp.py geopolitics "Taiwan" --type think_tanks

# Expert commentary
uv run scripts/wsp.py geopolitics "US China" --type expert_commentary

# By predefined topic
uv run scripts/wsp.py geopolitics --topic taiwan
uv run scripts/wsp.py geopolitics --topic south_china_sea

# List sources
uv run scripts/wsp.py geopolitics --list-sources
```

### Trading Forums

```bash
# All trading forums
uv run scripts/wsp.py trading "Bitcoin"

# Specific forum
uv run scripts/wsp.py trading "AAPL" --forum stocktwits
uv run scripts/wsp.py trading "BTC" --forum bitcointalk
```

### General Search

```bash
uv run scripts/wsp.py search "Claude AI"
uv run scripts/wsp.py search "AI" --freshness pd --count 5
```

### API Status Check

```bash
uv run scripts/wsp.py status
```

---

## Architecture

```
wsp-v3/
├── SKILL.md                 # This file (Agent interface)
├── .gitignore               # EBADF prevention
├── pyproject.toml
├── scripts/
│   └── wsp.py               # Single unified CLI
├── engines/
│   ├── brave.py              # Brave Search
│   ├── tavily.py             # Tavily
│   └── bing.py               # Bing (Chinese content)
├── searchers/
│   ├── news.py               # News search
│   ├── forums.py             # All forum search
│   ├── china.py              # China-specific
│   ├── geopolitics.py        # Expert analysis
│   └── trading.py            # Trading forums
└── utils/
    ├── config.py             # Dynamic .env loading
    ├── rate_limiter.py       # Rate limiting + usage tracking
    ├── cache.py              # In-memory cache
    └── formatter.py          # Output formatting
```

---

## China Search Limitations

| Platform | Bing | Tavily | Brave | Notes                  |
| -------- | ---- | ------ | ----- | ---------------------- |
| 知乎     | ✅   | ⚠️     | ❌    | Bing best              |
| 微博     | ✅   | ⚠️     | ❌    | Real-time content hard |
| 百度贴吧 | ✅   | ❌     | ❌    | Behind Baidu           |
| 小红书   | ⚠️   | ❌     | ❌    | Mostly behind GFW      |
| 雪球     | ✅   | ✅     | ⚠️    | Investment content OK  |
| 豆瓣     | ✅   | ⚠️     | ⚠️    | Cultural content       |
| B站      | ✅   | ⚠️     | ❌    | Video descriptions     |
| 頭條     | ✅   | ⚠️     | ❌    | News aggregation       |

For deep mainland content, consider VPN + direct access.

---

## Changes from V2

| Aspect       | V2                              | V3                              |
| ------------ | ------------------------------- | ------------------------------- |
| Entry point  | 31 separate scripts             | Single `wsp.py` CLI             |
| Engines      | Brave + Tavily + Firecrawl      | Brave + Tavily + Bing           |
| China search | site: queries via Brave only    | Bing → Tavily → Brave cascade   |
| Config       | Hardcoded `/Users/mac/...` path | Dynamic `.env` resolution       |
| Core         | 2,686-line monolith             | Modular engines/searchers/utils |
| EBADF        | ❌ No `.gitignore`              | ✅ `.gitignore` included        |
| VPS portable | ❌                              | ✅                              |

---

## Troubleshooting

**No search engine available?**

- Check `uv run scripts/wsp.py status` for API key status

**China search returns no results?**

- Ensure `BING_API_KEY` is set (best for Chinese content)
- Try English keywords (Chinese sites' English versions are better indexed)

**Rate limit errors?**

- Add `BRAVE_API_KEY_2` for automatic rotation
- Reduce `--count` to save API calls
