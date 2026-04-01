---
name: stock-technical-analyzer
description: Professional stock technical analysis with 12+ indicators, momentum analysis, volume analysis, breakout detection, and reversal patterns. Provides comprehensive technical insights for trading and market analysis. Powered by MCP stock_ta_server.
---

# Stock Technical Analyzer Skill

Professional-grade stock technical analysis tool powered by MCP stock_ta_server.

## Prerequisites

### Required Setup

1. **MCP Server**: stock_ta_server must be configured
   - Location: `/Volumes/Ketomuffin_mac/AI/mcpserver/mcp-stock-ta`

2. **MCP Tools Available**:
   - `mcp__stock_ta_server__get_stock_data`
   - `mcp__stock_ta_server__calculate_indicators`
   - `mcp__stock_ta_server__identify_patterns`

## Instructions

### 使用方法

此 skill 主要透過 MCP tools 直接操作。

### MCP Tools Usage

```
# 獲取股票數據
mcp__stock_ta_server__get_stock_data({ "symbol": "AAPL", "period": "1mo" })

# 計算技術指標
mcp__stock_ta_server__calculate_indicators({
  "symbol": "AAPL",
  "indicators": ["RSI", "MACD", "BB"]
})

# 識別圖形形態
mcp__stock_ta_server__identify_patterns({ "symbol": "AAPL" })
```

### 參考完整文檔

詳細使用說明請參考：`/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sta/skill.md`
