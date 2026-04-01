---
name: web-research-pro
description: 專業級網頁研究工具整合 Brave Search、Tavily、Firecrawl、Reddit JSON API 同專業新聞搜尋。支援智能路由、速率限制、重試機制、緩存及指標追蹤。Use when user mentions deep research, comprehensive analysis, scrape multiple websites, market intelligence, Reddit search, Reddit posts, news search, latest news, breaking news, or needs multi-source web intelligence with rate limiting and caching.
---

# Web Research Pro - 專業級網頁研究套件

## 概述

整合多個強大搜尋引擎同全球論壇嘅專業級研究工具。

## Prerequisites

### Required Setup

1. **Python Environment**:
   ```bash
   cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/wsp
   source .venv/bin/activate
   ```

2. **API Keys** (在 `scripts/.env` 配置):
   - `BRAVE_SEARCH_API_KEY` - Brave Search
   - `TAVILY_API_KEY` - Tavily
   - `FIRECRAWL_API_KEY` - Firecrawl
   - `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` - Reddit

## Instructions

### 使用方法

透過 wrapper script 執行研究：

```bash
# 基本搜尋
python /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/wsp/scripts/search.py "your query"

# Reddit 搜尋
python /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/wsp/scripts/reddit_search.py "subreddit" "query"

# 新聞搜尋
python /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/wsp/scripts/news_search.py "query"
```

## Available Commands

- `search.py` - 綜合搜尋（Brave + Tavily）
- `reddit_search.py` - Reddit 論壇搜尋
- `news_search.py` - 新聞搜尋
- `scrape.py` - 網頁抓取（Firecrawl）
