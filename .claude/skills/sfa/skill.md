---
name: stock-fundamental-analyzer
description: Professional stock fundamental analysis with financial statements, valuation metrics, profitability ratios, and growth analysis. Provides comprehensive fundamental insights for investment decisions using Tiingo API.
---

# Stock Fundamental Analyzer Skill

Professional-grade stock fundamental analysis tool.

## Prerequisites

### Required Setup

1. **Environment Variables** configured in `/Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa/.env`:
   - `TIINGO_API_KEY` - Get from https://www.tiingo.com/

2. **Python Environment**:
   ```bash
   cd /Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa
   source .venv/bin/activate
   ```

## Instructions

### 使用方法

```bash
# 基本面分析
cd /Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa
source .venv/bin/activate
python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa/scripts/analyze.py AAPL

# 比較分析
python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa/scripts/analyze.py AAPL MSFT GOOGL

# 財務報表
python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa/scripts/statements.py AAPL
```

### 參考完整文檔

詳細使用說明請參考：`/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa/skill.md`
