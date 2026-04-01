# 投資顧問委員會 — 知識庫

## 委員會運作規則

### 會議流程
1. **CEO 框架階段**：CEO 接收用戶 brief，提煉核心問題、分析標的、市場背景
2. **委員並行分析**：各委員同時進行獨立分析，使用各自分配的工具
3. **CEO 整合階段**：CEO 綜合所有委員觀點，輸出最終交易建議報告

### 委員職責分工
| 委員 | 職責 | 主要工具 |
|------|------|----------|
| CEO | 框架 + 整合 + 最終決策 | — |
| Macro Strategist | 宏觀環境判斷 | wsp-v3（geopolitics, finance news）+ FRED |
| Fundamental Analyst | 基本面深度分析 | sfa + wsp-v3 |
| Technical Analyst | 動量技術指標（股票+外匯+加密）| sta-v2（股票/Forex）+ ccxt（加密）|
| Risk Officer | 風險評估 + 倉位管理 | bash計算 + sta-v2 |
| Market Intelligence | 即時情報 + 情緒 | wsp-v3 + summarize |
| Prediction Market Analyst | 事件機率 + 大戶追蹤 | pt（Polymarket）|
| Backtest Officer | 策略回測驗證 | backtest-system（股票+外匯+加密）+ sta-v2 + ccxt |

### 跨資產日線數據流（Day Timeframe）
| 資產類別 | 數據源 | 技術分析工具 | 回測工具 |
|---------|-------|------------|---------|
| 美股 (AAPL, SPY) | Tiingo daily | sta-v2 `combined` | backtest `--symbol AAPL` |
| 外匯 (EURUSD, XAUUSD) | Tiingo FX daily | sta-v2 `combined` | backtest `--symbol EURUSD` (自動偵測) |
| 加密貨幣 (BTC, ETH) | CCXT/Binance 1d | ccxt `get_indicators` | backtest `--symbol BTC --crypto` |
| 預測市場 | Polymarket API | pt `odds` / `insider` | 不適用（非 OHLCV）|

---

## 兩種交易風格定義

### 長期宏觀部位（Macro Long-term Position）
- **持倉週期**：數月至數年（通常 3-18 個月）
- **分析重心**：宏觀經濟週期 + 基本面價值
- **進場條件**：宏觀趨勢確認 + 估值合理 + 基本面支撐
- **止損邏輯**：基本面惡化或宏觀假設被推翻
- **典型情境**：Fed 轉鴿做多科技股、衰退前期做空週期股

### 搖擺交易（Swing Trading）
- **持倉週期**：數天至數週（通常 3-30 天）
- **分析重心**：技術形態 + 動量/反轉信號
- **進場條件**：技術確認 + 成交量配合 + 催化劑支撐
- **止損邏輯**：關鍵技術位失守（通常 3-8% 止損）
- **典型情境**：突破整理區間做多、反彈失敗後做空

---

## 工具使用參考

### SFA（Stock Fundamental Analyzer）
```bash
cd /Volumes/Ketomuffin_mac/AI/mcpserver/stock-sa && source .venv/bin/activate
python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa/scripts/analyze.py <TICKER>
```
輸出：財務報表、估值指標、成長率、競爭力評分

### STA（Stock Technical Analyzer）
通過 MCP tools：
- `mcp__stock_ta_server__get_stock_data` — 獲取 OHLCV 數據
- `mcp__stock_ta_server__calculate_indicators` — 計算技術指標（RSI, MACD, EMA, ATR 等）
- `mcp__stock_ta_server__identify_patterns` — 識別形態（momentum, reversal, breakout）

### WSP-V3（Web Search Pro）
```bash
cd /Volumes/Ketomuffin_mac/AI/clawdbot/skills/wsp-v3
uv run scripts/wsp.py news "<query>" --source finance
uv run scripts/wsp.py geopolitics "<query>" --type expert_commentary
uv run scripts/wsp.py trading "<ticker>" --forum stocktwits
```

### Summarize（文章摘要）
```bash
summarize "https://example.com/url" --model google/gemini-3-flash-preview
```

---

## 輸出格式要求

### CEO 最終報告必須包含

```
## Final Decision（最終建議）
## Board Member Stances（各委員立場）
## Dissent & Tensions（分歧與張力）
## Trade-offs（風險/機會權衡）
## Next Actions（具體操作步驟）
## Deliberation Summary（討論摘要）
```

### 各委員立場格式
每位委員的分析輸出必須包含：
- **立場**：明確的方向性判斷
- **關鍵論點**：支撐立場的核心依據
- **主要顧慮**：最大的反向風險

### 交易建議格式
最終建議必須區分：
1. 長期宏觀部位（方向、進場區間、目標價、止損位、倉位比例）
2. 搖擺交易操作（進場點、出場目標、止損位、持倉時間）

---

## 風險管理原則

1. **1% 規則**：每筆交易最大虧損不超過帳戶資本的 1-2%
2. **風險回報比**：至少 1:2（建議 1:3）才值得入場
3. **分散原則**：相關性高的部位（如科技股集中）需縮小個別倉位
4. **停損紀律**：止損位一旦設定，不可隨意上移（做多）或下移（做空）
5. **倉位管理**：依據信心程度和市場條件，採用 25%-50%-100% 倉位分段建立

---

## 常用術語

| 中文 | 英文/縮寫 |
|------|-----------|
| 支撐位 | Support |
| 阻力位 | Resistance |
| 止損 | Stop-loss |
| 止盈 | Take-profit |
| 倉位大小 | Position sizing |
| 風險回報比 | Risk/Reward Ratio |
| 波動率 | Volatility |
| 動量 | Momentum |
| 背離 | Divergence |
| 均線 | Moving Average (MA/EMA/SMA) |
