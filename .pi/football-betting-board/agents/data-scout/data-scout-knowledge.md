# 球員數據偵察員 — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 data-scout-sources.md。

## 核心策略框架

（尚未記錄）

## 已分析賽事記錄

| 日期 | 賽事 | 建議 | 結果/複盤 |
|------|------|------|----------|

## 數據源使用心得

### SportAPI7 (sportapi7.p.rapidapi.com)
- **Rate limit**: ~5-10 requests/min，連續請求會觸發 429。需 REQUEST_DELAY >= 2s
- **Shell 注意**: `curl` 的 `-H` header 變數展開有問題，建議用 Python `urllib` 直接呼叫
- **API 回應格式**: player stats 包在 `{"statistics": {...}, "team": {...}}` 中，非扁平結構
- **每日賽程**: 包在 `{"events": [...]}` 中，需篩選 `tournament.uniqueTournament.id`
- **積分榜**: 包在 `{"standings": [{"rows": [...]}]}`
- **賽事統計**: `/event/{id}/statistics` 含 Match overview/Shots/Attack/Passes/Duels/Defending/GK，分 ALL/1ST/2ND
- **Yamal SportAPI ID**: 1402912（非之前記錄的 284329）
- **Saka SportAPI ID**: 934235 ✅

### The Odds API (api.the-odds-api.com)
- **Free tier**: 500 requests/month
- **Bookmakers**: 37+ 平台含 Pinnacle, Bet365, Cloudbet(加密), Stake(加密)
- **Markets**: h2h(勝負), spreads(亞盤), totals(大小球)
- **已驗證**: EPL 返回 20 場賽事 ✅

### FC26 數據庫
- **路徑**: `~/.claude/skills/football-data/fc26.db`
- **players 表**: 3,204 位球員（五大聯賽）
- **season_stats 表**: 即時賽季統計（已快取 2 人）
- **standings 表**: 聯賽積分榜（已快取 EPL 20 隊）
- **match_results 表**: 已完賽結果（含 xG）
- **fixtures 表**: 未來賽程

## 系統架構 (2026-04-03 建立)

```
本地數據 (fc26.db)
├── players (3,204)          ← FC 26 靜態屬性 (OVR/PAC/SHO/PAS/DRI/DEF/PHY + 子屬性)
├── season_stats (可擴展)    ← SportAPI7 球員賽季統計 (Rating/G/A/xG/xA/Dribbles...)
├── standings (可擴展)       ← 聯賽積分榜
├── match_results (可擴展)   ← 已完賽結果 + xG
└── fixtures (可擴展)        ← 未來賽程

工具腳本
├── fc26q.py                 ← FC 26 屬性查詢 CLI
├── sportapi_stats.py        ← 即時數據抓取+快取 CLI
├── poisson_model.py         ← Poisson 預測 + 價值投注偵測 + Kelly
└── backtest_engine.py       ← 回測引擎（模擬 Poisson vs 莊家噪音）

外部 API (需網路 + rate limit)
├── SportAPI7: 賽季統計 / 積分榜 / 賽程 / 賽事統計 / 陣容
└── The Odds API: 多平台賠率比較（由 odds-tracker agent 使用）
```

### sportapi_stats.py 指令
```
fetch <player>          抓取單球員賽季統計
fetch-team <club>       批量抓取整隊
standings <league>      積分榜 (API+快取)
results <league>        近 7 天賽果 (含 xG)
show <player>           查詢快取
compare <p1> <p2>      比較兩球員
cached                  列出所有快取
export                  匯出 CSV
```

### poisson_model.py 指令
```
predict <league> <home> <away>   — 預測單場
value [league] [threshold]       — 偵測價值投注
backtest [league]                — 回測模型
ratings [league]                 — 球隊實力評分
```

### backtest_engine.py 指令
```
python3 backtest_engine.py <league> [n_simulations]
```

### 回測結果 (2026-04-03 初步)
- **Poisson + Kelly 1/4 + Edge 3%**: 平均 ROI +13.9%（樂觀估計）
- ⚠️ 回測使用模擬數據，非真實比賽結果
- ✅ 真實回測需要：逐場歷史比分 + 當時賠率（下月 SportAPI 配額重置後可建立）

### 價值投注流程
1. `standings epl` → 獲取球隊攻防實力評分
2. `value epl 0.03` → 掃描所有賽事，找出模型 vs 市場的差異
3. Kelly 1/4 → 計算下注比例
4. 追蹤結果 → 更新知識庫

## 經驗教訓 / 避免的偏誤

（尚未記錄）
