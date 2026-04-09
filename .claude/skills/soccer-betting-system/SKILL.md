---
name: soccer-betting-system
description: 足球投注研究系統。用於五大聯賽資料整理、賠率分析、模型預測、回測驗證、CLV 檢查與 bankroll risk control。
---

# Soccer Betting System

單一 skill，整合以下能力：
- odds / line movement
- match modeling
- backtest / walk-forward validation
- news / context features
- bankroll / exposure control

## When to use

當你要做以下事情時使用此 skill：
- 分析五大聯賽賽前投注機會
- 建立或更新足球預測模型
- 驗證某策略是否真的有 edge
- 檢查 closing line value（CLV）
- 控制 stake sizing、drawdown、exposure
- 產出 matchday betting memo

## Core principles

1. 先驗證，再擴張
2. 沒有 out-of-sample，不叫 winning system
3. 沒有風控，不叫 system
4. 證據不足時應輸出 `no-bet`

## Layout

```text
.claude/skills/soccer-betting-system/
  SKILL.md
  .env.sample
  scripts/
    fetch_odds.py
    import_historical.py
    run_predictions.py
    run_backtest.py
    kelly.py
  src/
    config.py
    db.py
    models/
      poisson.py
      elo.py
    pricing/
      margin.py
      value.py
    risk/
      bankroll.py
  data/
    raw/
    processed/
    reports/
  legacy/
    football-data/
```

## Current status

目前此 skill 已建立為**統一入口**，並吸收舊原型作為 `legacy/football-data/` 參考來源。

## Recommended build model

此 skill 後續開發與重構，預設使用你目前的 **Codex GPT-5.4** 工作流。
這一點屬於開發/重構執行層，不影響 Python 腳本本身的執行。

短期策略：
- 保留舊原型，避免直接破壞現有腳本
- 所有新開發移到此 skill
- 逐步把舊能力重構進 `scripts/` + `src/`

## Environment

先複製：

```bash
cp .claude/skills/soccer-betting-system/.env.sample \
  .claude/skills/soccer-betting-system/.env
```

設定：
- `SOCCER_BETTING_DB_PATH`
- `ODDS_API_KEY`
- `SPORTAPI7_API_KEY`

## Recommended commands

### 1. Historical data
```bash
python3 .claude/skills/soccer-betting-system/scripts/import_historical.py
```

這會把 football-data.co.uk 的五大聯賽歷史資料匯入到此 skill 自己的統一 DB。

### 2. Predictions
```bash
python3 .claude/skills/soccer-betting-system/scripts/run_predictions.py \
  --league epl --home Arsenal --away Liverpool
```

### 3. Backtest
```bash
python3 .claude/skills/soccer-betting-system/scripts/run_backtest.py --league epl
python3 .claude/skills/soccer-betting-system/scripts/run_backtest.py \
  --league epl --mode walk-forward --season 2024-25
```

### 4. Risk sizing
```bash
python3 .claude/skills/soccer-betting-system/scripts/kelly.py \
  --prob 0.54 --odds 2.10 --bankroll 10000 --fraction 0.25
```

## Output expectations

使用此 skill 時，輸出盡量包含：
- market
- model probability
- implied / fair probability
- edge
- stake suggestion
- uncertainty / no-bet reason

## MVP roadmap

### Phase 1
- 完成 `.env` 化
- 移除舊原型硬編碼 API keys
- 建立統一 DB/config 入口
- 讓 prediction / backtest / risk command 可從同一 skill 執行

### Phase 2
- 加入 walk-forward validation
- 加入 CLV tracking
- 加入 line movement tracking
- 加入 context/news features

### Phase 3
- league-specific tuning
- model ensemble
- market-specific strategy selection

## Guardrails

- 不應把單場高信心視為系統優勢
- 不應在未驗證前放大 stake
- 不應把 narrative 當成 edge
- 若資料缺失或來源衝突，優先 `no-bet`
