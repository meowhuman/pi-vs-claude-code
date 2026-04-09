# Soccer Betting Board Setup

## Goal

建立一個以 **歐洲足球五大聯賽**（Premier League、La Liga、Serie A、Bundesliga、Ligue 1）為起點的研究型多代理系統，目標不是「每場都猜中」，而是建立：

1. 可持續更新的資料管線
2. 可重複驗證的預測流程
3. 嚴格風控的 value betting system
4. 可持續淘汰無效假設的評測機制

> 核心原則：**先做有紀律的正期望系統，再談下注放大。**

---

## Why Pi Board / Group Fit

我研究了現有 board 成員設計後，結論是這個主題最適合採用：

- **Pi Board**：做每週/每日多視角研判、比賽日 decision meeting
- **Project skills**：承載資料抓取、特徵工程、回測、報表生成
- **Knowledge folders**：讓每位成員只維護自己的研究記憶，避免角色污染

現有 `AI Tools Board` 的優點可直接沿用：

- `director + specialists` 結構清楚
- 每位成員各自擁有 `knowledge.md` / `sources.md`
- preset 機制適合「賽前快掃 / 完整週報 / 回測檢討」
- `eval-engineer` / `cost-performance-analyst` 這種角色設計很值得保留

同時，專案裡已經有兩個可直接重用的基礎：

- `.claude/skills/football-data/`：已有足球資料、Poisson、簡易 value betting、SQLite
- `.claude/skills/backtest-system/`：已有回測思維、風控、報表化習慣

---

## Recommended Board

建議新建：

- Board name: `soccer-betting-board`
- Type: `board`
- Root: `.pi/soccer-betting-board/`

### Board Members

#### 1. director
**保留，必須有**

用途：
- 主持賽前會議
- 整合各專家結論
- 做 final shortlist，而不是自己做模型細節

文件重點：
- 明確要求不直接推薦「all-in」或高風險賭法
- 所有最終建議必須附：市場、模型 edge、樣本規模、風險標籤

技能依賴：
- 報告整合
- 讀取所有成員輸出
- 生成 matchday memo

#### 2. market-odds-analyst
**新增，優先級最高**

用途：
- 專注 bookmaker odds、closing line、margin、line movement
- 找出「模型好像有 edge，但其實只是吃到莊家抽水」的假象

文件重點：
- 只關注 market efficiency、vig removal、line drift
- 每次都要回答 opening vs current vs closing 的差異

技能依賴：
- odds fetcher
- margin remover
- line movement tracker

#### 3. football-modeler
**新增，核心量化角色**

用途：
- 管 Poisson、xG proxy、team strength、home advantage、injury adjustments
- 從「會講球」轉成「可計算的 pre-match distribution」

文件重點：
- 嚴禁只靠 narrative 下結論
- 所有判斷需附模型假設與特徵來源

技能依賴：
- feature builder
- poisson / dixon-coles / elo runner
- calibration report

#### 4. team-news-scout
**新增**

用途：
- 追蹤傷停、輪換、賽程密度、歐戰/杯賽分心、主帥變動
- 補模型最容易失真的地方

文件重點：
- 不要八卦化，只收集可量化新聞
- 每條資訊需標註 impact level（low/med/high）

技能依賴：
- web research
- team news extraction
- match context summarizer

#### 5. tactical-analyst
**新增**

用途：
- 判斷對位、節奏、壓迫、定位球、邊路 mismatch
- 補足純統計模型看不到的 matchup 層

文件重點：
- 專注 style clash，不做宏觀市場評論
- 必須回答：哪種比賽腳本最可能發生

技能依賴：
- tactical checklist
- matchup note template

#### 6. data-engineer
**新增**

用途：
- 維護資料品質、schema、抓取任務、ETL、資料落庫
- 防止 board 建在髒資料上

文件重點：
- 每次先報 data freshness / missingness / source conflicts
- 發現資料異常可直接阻止模型輸出

技能依賴：
- ingest pipelines
- sqlite maintenance
- data QA scripts

#### 7. backtest-eval-engineer
**由現有 eval-engineer 思路改造**

用途：
- 定義成功標準：CLV、ROI、Brier score、log loss、drawdown
- 專門打臉過度樂觀策略

文件重點：
- 沒有 out-of-sample，不准稱為 winning system
- 要區分 prediction quality 與 betting profitability

技能依賴：
- rolling backtest
- walk-forward validation
- benchmark comparison

#### 8. bankroll-risk-manager
**新增，必須有**

用途：
- 管 stake sizing、exposure cap、correlation、daily/weekly loss limit
- 這是把「模型」變成「系統」的關鍵角色

文件重點：
- 默認 fractional Kelly，且有上限
- 禁止同輪過度集中同一聯賽/同類市場

技能依賴：
- kelly calculator
- exposure ledger
- drawdown monitor

#### 9. systems-architect
**保留 agentic-architect 的精神，但縮窄到 betting workflow**

用途：
- 決定哪些流程自動化、哪些保留人工覆核
- 避免系統越做越複雜卻沒有 alpha

文件重點：
- 能單一 script 解決就不要多 agent
- agent 只負責 decision support，不直接代替 risk gate

技能依賴：
- workflow audit
- automation map

---

## Suggested Presets

```yaml
presets:
  quick-matchday:
    - director
    - market-odds-analyst
    - football-modeler
    - bankroll-risk-manager

  full-prematch:
    - director
    - market-odds-analyst
    - football-modeler
    - team-news-scout
    - tactical-analyst
    - bankroll-risk-manager

  weekly-research:
    - director
    - football-modeler
    - team-news-scout
    - tactical-analyst
    - data-engineer
    - backtest-eval-engineer
    - systems-architect

  model-lab:
    - football-modeler
    - data-engineer
    - backtest-eval-engineer
    - systems-architect

  risk-review:
    - director
    - market-odds-analyst
    - backtest-eval-engineer
    - bankroll-risk-manager
```

---

## Recommended Folder Structure

```text
.pi/soccer-betting-board/
  config.yaml
  agents/
    director/
      director.md
      director-knowledge.md
      director-sources.md
    market-odds-analyst/
      market-odds-analyst.md
      market-odds-analyst-knowledge.md
      market-odds-analyst-sources.md
    football-modeler/
      football-modeler.md
      football-modeler-knowledge.md
      football-modeler-sources.md
    team-news-scout/
      team-news-scout.md
      team-news-scout-knowledge.md
      team-news-scout-sources.md
    tactical-analyst/
      tactical-analyst.md
      tactical-analyst-knowledge.md
      tactical-analyst-sources.md
    data-engineer/
      data-engineer.md
      data-engineer-knowledge.md
      data-engineer-sources.md
    backtest-eval-engineer/
      backtest-eval-engineer.md
      backtest-eval-engineer-knowledge.md
      backtest-eval-engineer-sources.md
    bankroll-risk-manager/
      bankroll-risk-manager.md
      bankroll-risk-manager-knowledge.md
      bankroll-risk-manager-sources.md
    systems-architect/
      systems-architect.md
      systems-architect-knowledge.md
      systems-architect-sources.md
  memos/
  reports/
```

---

## Doc Template Standard

每位成員 `.md` 建議統一使用這種結構：

```md
---
name: <agent-name>
description: <one-line role>
tools: bash,read,write,grep,find
model: glm/glm-5-turbo
---

你是 Soccer Betting Board 的 <Role>。

## 任務
- 
- 
- 

## 邊界
- 你不能做什麼
- 哪些決策必須交給其他成員

## 你的資料夾
- `.pi/soccer-betting-board/agents/<agent-name>/`

## 你可編輯的檔案
- `<agent-name>-knowledge.md`
- `<agent-name>-sources.md`

## 輸出格式
```md
## 立場（<Role>）
**我的判斷：**

**Key Findings：**
- 

**Evidence：**
- 

**Risks / Uncertainty：**
- 

**Actionable Recommendation：**
- 
```
```

### 每位成員都應有的共通規則

1. 只能編輯自己資料夾
2. 所有結論都要盡量對應來源或資料表
3. 不得把「感覺」包裝成 edge
4. 若證據不足，要明確輸出 `no-bet` 或 `watchlist`

---

## Skill Setup Recommendation

同意你的方向：**所有能力收斂成 1 個 skill**，不要拆成多個 skills。

我建議直接做成：

- Skill name: `soccer-betting-system`
- Path: `.claude/skills/soccer-betting-system/`

這樣比較好，原因有 4 個：

1. **單一入口**：board 成員只要學 1 個 skill，不用判斷該裝哪個 skill
2. **共享資料模型**：odds、match、team、backtest、risk 可以共用同一套 schema
3. **避免重複腳本**：fetch / normalize / report / evaluate 不會散在 5 個資料夾
4. **更適合 MVP**：先做出可跑系統，比先拆模組更重要

### Reuse Existing Foundations

#### A. `.claude/skills/football-data/`
適合吸收進 `soccer-betting-system` 作為核心原型。

建議補強：
- 把 API key 移出程式，改用 `.env`
- 補正式 `SKILL.md`
- 把 `poisson_model.py` 重構成模組化檔案
- 補真正的 rolling backtest，而非只看 standings alignment

#### B. `.claude/skills/backtest-system/`
不必獨立接進 board；建議把其方法論吸收進同一 skill。

可借用：
- risk management 語言
- chart/report 輸出方式
- walk-forward / optimize 思路

---

## Unified Skill Design

### Suggested Structure

```text
.claude/skills/soccer-betting-system/
  SKILL.md
  .env.sample
  .gitignore
  data/
    raw/
    processed/
    reports/
  scripts/
    fetch_odds.py
    fetch_team_news.py
    import_historical.py
    build_features.py
    run_predictions.py
    run_backtest.py
    run_walk_forward.py
    report_roi.py
    report_clv.py
    calibration_report.py
    exposure_report.py
    risk_gate.py
    kelly.py
  src/
    config.py
    db.py
    schemas.py
    utils.py
    models/
      poisson.py
      dixon_coles.py
      elo.py
      ensemble.py
    pricing/
      margin.py
      value.py
      closing_line.py
    features/
      team_strength.py
      injuries.py
      schedule.py
      tactical_flags.py
    backtest/
      engine.py
      metrics.py
      walk_forward.py
    risk/
      bankroll.py
      exposure.py
      limits.py
```

### Capability Map Inside One Skill

這 1 個 skill 內部涵蓋 5 個能力層，但**仍然是同一個 skill**：

#### 1. Odds layer
用途：
- 抓 odds
- 去水位
- 計算 fair probability
- 追蹤 line movement
- 比較 opening / current / closing line

對應腳本：
- `scripts/fetch_odds.py`
- `src/pricing/margin.py`
- `src/pricing/closing_line.py`

#### 2. Modeling layer
用途：
- Poisson / Dixon-Coles / Elo / xG proxy
- calibration / Brier / log loss

對應腳本：
- `scripts/build_features.py`
- `scripts/run_predictions.py`
- `scripts/calibration_report.py`
- `src/models/*`

#### 3. Backtest layer
用途：
- walk-forward 回測
- value bet selection
- ROI / CLV / max drawdown
- market-specific breakdown（1x2、OU、AH）

對應腳本：
- `scripts/run_backtest.py`
- `scripts/run_walk_forward.py`
- `scripts/report_roi.py`
- `scripts/report_clv.py`

#### 4. News/context layer
用途：
- 擷取傷停、輪換、賽程資訊
- 將文字新聞轉為結構化特徵

對應腳本：
- `scripts/fetch_team_news.py`
- `src/features/injuries.py`
- `src/features/schedule.py`
- `src/features/tactical_flags.py`

#### 5. Risk layer
用途：
- Kelly fraction
- exposure limit
- correlation cap
- losing streak circuit breaker

對應腳本：
- `scripts/kelly.py`
- `scripts/exposure_report.py`
- `scripts/risk_gate.py`
- `src/risk/*`

---

## Skill Interface Recommendation

`SKILL.md` 應該讓 board 成員只記得幾個固定入口，不需要記全部內部模組。

建議固定入口：

```bash
# 1. 更新資料
python3 scripts/import_historical.py
python3 scripts/fetch_odds.py --league epl
python3 scripts/fetch_team_news.py --league epl

# 2. 建特徵 / 跑模型
python3 scripts/build_features.py --league epl --season 2025-26
python3 scripts/run_predictions.py --league epl

# 3. 驗證 / 回測
python3 scripts/run_backtest.py --league epl
python3 scripts/run_walk_forward.py --league epl
python3 scripts/calibration_report.py --league epl
python3 scripts/report_clv.py --league epl

# 4. 風控
python3 scripts/kelly.py --edge 0.06 --odds 2.10 --bankroll 10000
python3 scripts/exposure_report.py
python3 scripts/risk_gate.py --slip bets/today.json
```

---

## Mapping Board Members To One Skill

雖然 skill 只有 1 個，但每位 board 成員用的入口不同：

- `market-odds-analyst`
  - `fetch_odds.py`
  - `report_clv.py`
  - `pricing/*`

- `football-modeler`
  - `build_features.py`
  - `run_predictions.py`
  - `models/*`

- `team-news-scout`
  - `fetch_team_news.py`
  - `features/injuries.py`
  - `features/schedule.py`

- `backtest-eval-engineer`
  - `run_backtest.py`
  - `run_walk_forward.py`
  - `calibration_report.py`

- `bankroll-risk-manager`
  - `kelly.py`
  - `exposure_report.py`
  - `risk_gate.py`

也就是說：**角色分工保留，但工具包統一。**

---

## Metrics That Actually Matter

如果你的目標是「winning system」，我建議 board 成員不要只看命中率，要統一追這些：

### Prediction Metrics
- Brier score
- Log loss
- Calibration curve
- Closing line vs model line error

### Betting Metrics
- ROI
- Yield
- CLV（closing line value）
- Average edge captured
- Hit rate by market

### Risk Metrics
- Max drawdown
- Longest losing streak
- Daily / weekly exposure
- Correlation-adjusted exposure

### Process Metrics
- Data freshness
- Missing data rate
- Manual override rate
- No-bet discipline rate

---

## Decision Policy

建議把 board 的最終輸出分成 4 級：

1. `bet`
   - 模型 edge 明確
   - 市場價格可接受
   - 資訊風險低

2. `small-bet`
   - edge 存在，但資訊不完整或市場變動快

3. `watchlist`
   - 等 closing line 或隊伍消息更新

4. `no-bet`
   - 證據不足、抽水太高、模型衝突、新聞不確定

這很重要，因為真正的贏家系統通常包含大量 `no-bet`。

---

## Immediate Build Plan

### Phase 1 — Foundation
1. 建 `.pi/soccer-betting-board/` 基本骨架
2. 建 4 個核心成員：
   - director
   - market-odds-analyst
   - football-modeler
   - bankroll-risk-manager
3. 建立單一 skill：`.claude/skills/soccer-betting-system/`
4. 將 `.claude/skills/football-data/` 的有效程式吸收進新 skill
5. 移除硬編碼 API key

### Phase 2 — Validation
1. 在同一 skill 內補 historical odds + result ingestion
2. 在同一 skill 內建 rolling backtest
3. 加 CLV / drawdown / Kelly risk gate
4. 設 `quick-matchday` 與 `model-lab` presets

### Phase 3 — Edge Expansion
1. 加 team-news-scout
2. 加 tactical-analyst
3. 做 ensemble / market-specific models
4. 加聯賽分層策略，不要五大聯賽混成一個規則

---

## My CEO Recommendation

如果要真的朝「winning system」前進，我不建議一開始就開太多 board 成員。

**最小可行組合：**
- director
- market-odds-analyst
- football-modeler
- backtest-eval-engineer
- bankroll-risk-manager

這 5 個角色已經能構成一個完整閉環：

- 找價差
- 算概率
- 驗證假設
- 控制下注
- 輸出決策

而 `team-news-scout`、`tactical-analyst`、`systems-architect` 可以作為第二階段增強層。

---

## Next Step I Recommend

下一步最值得做的不是先寫更多 agent prompt，而是這 3 件事：

1. **建立單一 skill：`.claude/skills/soccer-betting-system/`，把 football-data / backtest 能力整合進去**
2. **建立 `.pi/soccer-betting-board/` 的最小 5 人 board**
3. **先做 EPL 單聯賽 walk-forward backtest，跑出第一版真實基線**

沒有這個基線，任何「winning system」都只是故事。
