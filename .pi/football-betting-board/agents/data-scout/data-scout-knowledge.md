# 球員數據偵察員 — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 data-scout-sources.md。

## 核心策略框架

（尚未記錄）

## 已分析賽事記錄

| 日期 | 賽事 | 建議 | 結果/複盤 |
|------|------|------|----------|

## 數據源使用心得

### 🥇 FC26 數據庫（主要數據源，無 Rate Limit）
- **路徑**: `/Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26.db`
- **CLI**: `fc26q.py`
- **players 表**: 3,204 位球員（五大聯賽）
  - 主屬性：overall, pace, shooting, passing, dribbling, defending, physic
  - 子屬性：acceleration, sprint_speed, finishing, vision, composure...
  - 聯賽欄位：league_name, club_name
- **查詢方式**: `$FC26Q player <name>` / `$FC26Q team <club>` / `$FC26Q compare A vs B`
- **優點**: 即時響應、無網絡延遲、無 API 配額限制
- **限制**: 靜態數據（FC 26 遊戲屬性），無即時賽季統計（進球/助攻/xG）

### 🥈 Kaggle FBref（備用，賽季統計）
- **數據集**: `hubertsidorowicz/football-players-stats-2025-2026`
- **更新**: 每週
- **包含**: xG, goals, assists, rating, minutes 等賽季統計
- **使用**: `kaggle datasets download -d hubertsidorowicz/football-players-stats-2025-2026`
- **狀態**: API Key 已配置，可隨時下載

### 🥉 football-data.org（備用，賽程/積分榜）
- **API Key**: ab57e456f0074b02b423a059c0c1bf42
- **配額**: 500 次/日
- **用途**: 賽程、積分榜、近期戰績
- **限制**: 無球員詳細數據，無 xG

### ⚠️ SportAPI7 (sportapi7.p.rapidapi.com) — 暫停使用
- **狀態**: ❌ Rate Limit 已達上限（每月 500 次已用完）
- **重置**: 下個月自動恢復
- **先前記錄**:
  - Rate limit: ~5-10 requests/min，連續請求會觸發 429
  - **Yamal SportAPI ID**: 1402912
  - **Saka SportAPI ID**: 934235 ✅

### The Odds API (api.the-odds-api.com) — 由 odds-tracker 使用
- **Free tier**: 500 requests/month（目前剩餘 483 次）
- **Bookmakers**: 37+ 平台含 Pinnacle, Bet365, Cloudbet, Stake
- **已驗證**: EPL 返回 20 場賽事 ✅

## 系統架構 (2026-04-03 更新)

```
🥇 本地數據（優先使用，無限制）
├── FC 26 DB (fc26.db)
│   ├── players (3,204)     ← 靜態屬性 (OVR/PAC/SHO/PAS/DRI/DEF/PHY + 子屬性)
│   └── CLI: fc26q.py
│
🥈 外部數據源（備用）
├── Kaggle FBref            ← 賽季統計 (xG/goals/assists)，每週更新
├── football-data.org       ← 賽程/積分榜，500次/日
│
⚠️ 暫停使用
└── SportAPI7               ← Rate limit 已達上限，下月恢復

工具腳本
├── fc26q.py                ← FC 26 屬性查詢 CLI（主要工具）
├── sportapi_stats.py       ← SportAPI7 快取 CLI（暫停）
├── poisson_model.py        ← Poisson 預測 + 價值投注偵測 + Kelly
└── backtest_engine.py      ← 回測引擎

使用優先級：
1. FC 26 DB → 球員屬性、陣容比較（即時、無限制）
2. Kaggle → 需要賽季統計時（xG、進球、助攻）
3. football-data → 賽程、近期戰績
4. SportAPI7 → 下月恢復後，即時數據補充
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

### 2026-04-03 Atletico vs Barcelona 分析複盤

**犯下的錯誤：**

1. ❌ **越界做其他agent的工作**
   - 抓了Cloudbet賠率（這是Odds-tracker的職責）
   - 算了EV和Kelly（這是Odds-tracker的職責）
   - 結果：混淆職責，效率低下

2. ❌ **沒有查傷兵名單**
   - 直接拿FC 26數據庫的先發XI假設
   - 沒確認Lewandowski、Pedri等是否真的上場
   - 結果：預測可能完全錯誤

3. ❌ **模型過度簡化**
   - 只用OVR算xG，沒考慮位置別權重
   - 主場加成固定15%，沒查歷史數據
   - 結果：預期進球1.72 vs 1.26可能不準

4. ❌ **沒有標註數據限制**
   - 應該一開始就說「這是靜態數據，未考慮近期狀態」
   - 結果：User可能誤以為這是可靠預測

5. ❌ **效率低下**
   - SQLite查詢只要0.5秒，但整個流程花了15+分鐘
   - 原因：不熟悉欄位名稱，反覆試錯

**改進方案：**

1. ✅ 建立SOP（已建立 /tmp/data_scout_sop.md）
2. ✅ 明確職責邊界（見下方「團隊分工」）
3. ✅ 強制檢查清單（必須查傷兵才能輸出報告）
4. ✅ 建立數據字典（避免runtime試錯）

---

## 團隊分工與職責邊界

### 我的職責（Data Scout）

**核心任務：**
- ✅ FC 26 球員屬性分析
- ✅ 球員能力對位比較
- ✅ 陣容深度評估
- ✅ 基礎xG模型（基於屬性）
- ✅ 輸出「純數據面」分析（必須標註限制）

**不該做的：**
- ❌ 賠率追蹤 → Odds-tracker
- ❌ 套利偵測 → Odds-tracker
- ❌ EV計算（基於賠率）→ Odds-tracker
- ❌ 市場趨勢分析 → Odds-tracker

**建議新增角色：情報整合員**
- 負責協調 Data Scout + Odds-tracker
- 查詢傷兵/新聞
- 解釋數據與市場的差異
- 給出最終綜合建議

---

## 標準分析流程（SOP）

見 /tmp/data_scout_sop.md

核心步驟：
1. 查傷兵名單（3分鐘）
2. 獲取FC 26數據（1分鐘）
3. 計算加權評分（2分鐘）
4. xG模型（2分鐘）
5. 輸出報告（2分鐘）

總計：10分鐘內完成，不再花15+分鐘除錯

---

## 數據限制聲明模板

每次分析必須附加：

> ⚠️ **本分析限制**：
> - 數據日期: {date}
> - 數據源: FC 26 靜態屬性
> - 未考慮因素: 傷兵名單/近期狀態/戰術變化
> - 信心度: {高/中/低}
> - 建議用途: 僅供參考，需結合Odds-tracker的市場分析
