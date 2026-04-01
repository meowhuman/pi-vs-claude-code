# Prediction Market Analyst — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 prediction-market-analyst-sources.md。
> 使用 edit 工具更新此文件。

---

## 宏觀分析 Playbook（Macro Investment Scan Protocol）

### ⚠️ 重要：search.py 速度問題

`search.py` 預設掃描所有活躍市場（1800+），速度慢（30-60 秒）。
**永遠加上 `--min-vol` 和 `-c` 來縮小範圍：**

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt
source venv/bin/activate

# ✅ 快速掃描（推薦）— 只看高流動性宏觀市場
python scripts/search.py -c economy --min-vol 50000 --urgent 90
python scripts/search.py -c politics --min-vol 50000 --urgent 90
python scripts/search.py -c world --min-vol 50000 --urgent 90

# ❌ 避免無參數裸跑（掃描全部 1800+ 市場，極慢）
# python scripts/search.py "Fed rate"
```

---

### Step 1：標準宏觀掃描順序

每次委員會分析前，按此順序檢查：

```bash
# 1. Fed / 利率政策（最影響科技股、成長股）
python scripts/search.py "Fed rate cut" -c economy --min-vol 100000 --urgent 90

# 2. 衰退 / 經濟放緩風險
python scripts/search.py "recession" -c economy --min-vol 50000 --urgent 180

# 3. 通脹走向
python scripts/search.py "CPI inflation" -c economy --min-vol 50000 --urgent 60

# 4. 地緣政治（影響能源、防禦股）
python scripts/search.py -c world --min-vol 50000 --urgent 60

# 5. 加密特定事件（Bitcoin ETF、監管）
python scripts/search.py -c crypto --min-vol 100000 --urgent 60
```

---

### Step 2：解讀機率的框架

| 機率範圍 | 含義 | 投資行動 |
|---------|------|---------|
| **> 85%** | 市場已定價，高確定性 | 關注「已定價後的走法」，不是方向，是幅度 |
| **60-85%** | 高傾向但未完全定價 | 有方向性優勢，可建立偏向性部位 |
| **40-60%** | 真正不確定區間 | 波動率機會，避開方向性賭注 |
| **15-40%** | 低機率但非尾部 | 監控但不重倉 |
| **< 15%** | 尾部風險 | 值得告知委員會的黑天鵝，倉位保護參考 |

**關鍵原則：Polymarket 機率 ≠ 資產會漲跌幾%**
- 它告訴你「事件發生機率」，不告訴你「資產反應幅度」
- 結合 macro-strategist 的分析才能轉化為交易信號

---

### Step 3：到期日篩選策略

```bash
# 近期催化劑（7 天內，最直接影響搖擺交易）
python scripts/search.py -c economy --urgent 7 --min-vol 50000

# 中期事件（30 天內，影響趨勢方向）
python scripts/search.py -c economy --urgent 30 --min-vol 50000

# 季度視野（90 天內，影響宏觀部位）
python scripts/search.py -c economy --urgent 90 --min-vol 100000
```

**原則：到期日越近，對短線交易越重要；到期日越遠，對宏觀部位越重要。**

---

### Step 4：Whale 信號判讀

```bash
# 找到市場 condition_id 後，看大戶動向
python scripts/analyze.py whales <condition_id> --min-value 5000

# 門檻參考
# $1,000-$5,000 = 普通參與者，雜訊多
# $5,000-$20,000 = 有意義的信號，值得關注
# > $20,000 = Smart Money 動作，高度關注
```

**Whale 信號的正確解讀：**
- Whale 大單買 YES → 他們認為事件「會發生」
- Whale 大單買 NO → 他們認為市場高估了機率
- 多個 Whale 同向 + 機率快速移動 = 強烈信號
- 單一 Whale 孤立大單 = 可能是對沖，不一定是方向性押注

---

### Step 5：把 Polymarket 信號轉化成委員會建議

完成掃描後，整合輸出：

1. **什麼事件在 30 天內到期且機率在 30-70%？** → 不確定性最高，波動最大
2. **哪個事件的 Whale 最近有異動？** → 早期信號
3. **目前宏觀賠率對正在討論的標的有何含義？**
   - Fed 不降息 (60%) → 成長股承壓
   - 衰退機率 (35%) → 防禦配置
   - 貿易衝突升溫 (55%) → 影響出口依賴型標的

---

## 核心分析框架

（從實際分析中累積，初始為空）

## 活躍監控市場（Active Watchlist）

### 🇮🇷 伊朗戰爭相關（2026-04-01 建檔）

> 背景：美軍 2/28 開始空襲伊朗，戰爭進入第 5 週。Rubio 表示不需要地面部隊。Hegseth 說「接下來幾天是決定性時刻」。300+ 美軍受傷。

| 事件 | 機率 | 7 日趨勢 | 成交量 | 到期日 | Condition ID |
|------|------|---------|--------|--------|-------------|
| **US forces enter Iran by 3/31** | 4% → ~1% | 📉 -90% | $38.4M | 已到期 | `0x306d10d4...` |
| **US forces enter Iran by 12/31** | 74% | 📈 +6.5% (1D -12.1%) | $6.2M | 12/31 | `0xe4b9a52d...` |
| **Iranian regime fall by 6/30** | 16% | 📉 -39% | $23.2M | 6/30 | `0x9352c559...` |
| **Iranian regime survive US strikes** | 84% | 📈 +8.1% | $449K | 6/30 | `0xefc69f5f...` |
| **US-Iran nuclear deal by 6/30** | 30% | 📉 -16.7% | $910K | 6/30 | `0xa70fc369...` |
| **Iran coup attempt by 6/30** | 21% | — | $339K | 6/30 | `0x17c9dead...` |
| **FR/UK/DE strike Iran by 6/30** | 7% | 📉 -23.5% | $531K | 6/30 | `0x0c38dd93...` |
| **Iran ends uranium enrichment by 6/30** | 28% | — | $148K | 6/30 | `0x9d3f0226...` |
| **Pezeshkian out by 6/30** | 32% | — | $102K | 6/30 | `0x3ed92a5a...` |

**快速掃描指令：**
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt
source venv/bin/activate
python scripts/search.py "US forces enter Iran" --min-vol 1000
python scripts/search.py "Iran" -c world --min-vol 5000 --urgent 90
```

**關鍵觀察（2026-04-01）：**
- 機率整體往「維持現狀」移動：政權存活↑、垮台↓、核協議↓
- 但 US forces enter Iran by 12/31 仍高達 74% → 市場認為長期升級機率高
- 短期（3/31）地面部隊進入已基本排除
- 鯨魚在「政權垮台」市場多空均勻（YES 63% vs NO 37%），雙方大戶都在虧損

---

## 市場觀點與看法

（從實際分析中累積）

## 分析過的事件記錄

| 日期 | 事件 | Polymarket 賠率 | 實際結果 | 複盤 |
|------|------|----------------|---------|------|
| 2026-04-01 | US forces enter Iran by 3/31 | ~1% (from 13% 7d ago) | ❌ 未發生 | 正確。Rubio 明確排除地面部隊 |
| 2026-04-01 | US forces enter Iran by 12/31 | 74% | 待定 | 長期升級風險仍被高機率定價 |
| 2026-04-01 | Iranian regime fall by 6/30 | 16% (from 20.5% 7d ago) | 待定 | 空襲未能顯著動搖政權 |

## 經驗教訓 / 避免的偏誤

1. **關鍵字搜尋陷阱**：「US troops Iran」搜不到，市場用詞是 "US forces enter Iran"。遇到搜不到時，嘗試同義詞（troops → forces、invade → enter、attack → strike）。
2. **裸搜全分類 vs 分類搜尋**：有些市場不在預期的 `-c` 分類下。如果 `-c world` 搜不到，嘗試不加 `-c` 裸搜（但加 `--min-vol` 避免太慢）。
3. **市場問法很重要**：「US strike Iran」= 空襲（已發生），「US forces enter Iran」= 地面部隊進入。不同措辭定義不同事件，機率天差地遠（0% vs 74%）。
