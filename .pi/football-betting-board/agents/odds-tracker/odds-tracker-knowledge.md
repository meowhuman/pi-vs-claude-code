# 賠率追蹤員 — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 odds-tracker-sources.md。

## 核心策略框架

（尚未記錄）

## 已分析賽事記錄

| 日期 | 賽事 | 建議 | 結果/複盤 |
|------|------|------|----------|

## 數據源使用心得

### The Odds API（主要來源）
- API Key: 7cb32f9dd8d62dc575d80b11fad88c3b（免費 500 次/月）
- **不包含 Cloudbet、Stake.com、Betfury**（需另查）
- 包含 1xBet（key: `onexbet`），賠率普遍優於 Pinnacle
- Betfair、Smarkets、Matchbook 交易所 margin 最低（0-1%）
- Pinnacle margin 平均 3.8-5.5%，英國高街書商 7-9%

### Cloudbet API（✅ 已驗證 2026-04-03）
- 端點：`https://sports-api.cloudbet.com/pub/v2/odds/`
- 認證：`X-API-Key` header，無請求次數限制
- 覆蓋五大聯賽 + 歐冠 + 歐霸 + 小聯賽
- 支援市場：1X2、亞盤、大小球（多線）、BTTS、DNB、正確比分、半場/全場
- 與 The Odds API **互補**：The Odds API 不含 Cloudbet，Cloudbet API 補上這個盲區
- 可直接用 `fetch_cloudbet_odds.py` CLI 工具取賠率

### 加密平台賠率觀察（2026-04-03）
- 1xBet 在 29/30 個方向上賠率優於 Pinnacle
- 最大差異出現在大冷門賠率（如 Port Vale 客勝 50.00 vs 30.34）
- Cloudbet/Stake/Betfury 不在 The Odds API 中，是盲區

## 已分析賽事記錄

### 2026-04-04~05 FA Cup 週末
| 賽事 | 觀察 | 套利空間 |
|------|------|----------|
| Man City vs Liverpool | 1xBet 全方位優於 Pinnacle | -0.1%（$14.47/$10K）|
| Chelsea vs Port Vale | 巨大冷門賠率差異 | **-1.1%（$107/$10K）** |
| Southampton vs Arsenal | Betfair/Marchbook 交易所最低 margin | 0.0% |
| West Ham vs Leeds | 1xBet 全面優勢 | 0.0% |

### 2026-04-10~13 英超週末（10 場）
- 3 場賽事最佳組合 margin 為負值：Arsenal vs Bournemouth (-0.9%), Sunderland vs Tottenham (-0.3%), Man Utd vs Leeds (-0.7%)

## 經驗教訓 / 避免的偏誤

1. **賠率差異 ≠ 套利**：同一結果在不同平台的賠率差只是「選擇更好的價格」，不是套利
2. **真正的套利**：三個結果的最佳賠率組合 implied probability < 100%
3. **API 不覆蓋加密平台**：The Odds API 不含 Cloudbet、Stake、Betfury，但 Cloudbet API 可補上（已驗證）
4. **交易所（Betfair/Smarkets）margin 最低**：通常是 0-1%，但需付佣金
5. **本週末不一定有 EPL**：2026-04-04~05 是 FA Cup 週末，EPL 下一輪是 4/10 開始
