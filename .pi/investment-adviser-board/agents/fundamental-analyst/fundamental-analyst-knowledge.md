# Fundamental Analyst — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 fundamental-analyst-sources.md。
> 使用 edit 工具更新此文件。

## 核心投資哲學

1. **現金流為王，會計利潤為輔** — FCF > Net Income 是判斷品質的真實標準
2. **估值需要對照物** — 必須和歷史均值及同業比較，單看一個 P/E 沒意義
3. **護城河比增速重要** — 高增速但沒護城河容易被搶走；穩定增速+深護城河=長期複利
4. **管理層資本配置決定最終回報** — 買回>分紅>M&A（通常）；指引準確度是信任基礎
5. **不碰無法理解的生意** — 業務模式太複雜或缺乏透明度，直接說「看不懂」
6. **定性與定量並重** — 財報數據（定量）+ 戰略/技術/行業深度（定性）都是基本面的組成部分。不會只看數字忽略戰略邏輯。

## 分析框架

### SFA（Stock Fundamental Analyzer）— 主要工具 ✅
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/sfa

# 單股詳細基本面
python3 scripts/yfinance_fundamentals.py get_fundamental_data <TICKER>

# 多股比較表
python3 scripts/yfinance_fundamentals.py table AAPL MSFT GOOG NVDA
```
> 依賴 yfinance（已安裝 v1.2.0），無需外部硬碟或 API key。

### WSP-V3 — 補充行業新聞
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/wsp-v3
uv run scripts/wsp.py news "<公司名> earnings" --source finance
```

### Summarize — YouTube / 文章深度研究
```bash
summarize "<youtube_url>" --youtube auto                    # 摘要
summarize "<youtube_url>" --youtube auto --extract-only    # 完整逐字稿
```

---

## 監控體系

### 資訊來源 Watchlist

#### 📺 YouTube 頻道：茄利略 CUP（Kelileo）
- **頻道**：https://www.youtube.com/@KelileoCUP
- **定位**：追蹤資金流向、硬核科技分析、地緣政治與資本配置
- **價值**：深度拆解公司策略背後的技術與商業邏輯（非表面新聞）
- **性質**：定性基本面（Qualitative Fundamental）— 補充定量財務分析的不足
- **觸發方式**：使用者丟影片連結給我，我用 `summarize` 消化後提取投資相關洞見
- **記錄原則**：只記錄對投資決策有影響的結論，不記技術細節；標註哪些假設我無法獨立驗證
- **分析過的影片記錄**：

| 日期 | 影片標題/主題 | 標的 | 提取的關鍵洞見 | ⚠️ 未驗證假設 |
|------|-------------|------|--------------|--------------|
| 2026-04-01 | TMTG(DJT) 收購 TAE Technologies 核聚變 | DJT / TAE | ① TAE 處於「可行性→可靠性」死亡峽谷（Norm 最長僅 30ms 穩定）② 這更像資本+政治賭注而非確定性投資 ③ DeepMind 動機是為 AI 算力尋找根本能源解法，影響 GOOG 長期資本配置判斷 | 30ms 穩定時間、Proton-B11 路線 90% 效率 — 無法獨立驗證 |

#### 🔬 深度科技投資框架（從影片提取）

> 用於評估任何「實驗室技術 → 商業化」類型的標的（核聚變、量子運算、固態電池等）。

```
深度科技成熟度階段：
  ① 科學可行性（能做一次）     → 實驗室成就，不可投資
  ② 工程可靠性（能持續做）     → 死亡峽谷，少數活下來，需大量資本
  ③ 商業可行性（成本合理）     → 開始用基本面框架分析（DCF、P/E）
  ④ 規模化量產                 → 真正的護城河建立階段
```

**原則：只有到達 ③ 才值得用基本面框架分析。② 階段是賭博不是投資。**

#### 👀 從影片衍生的待追蹤標的

| 標的 | 為什麼追蹤 | 觸發條件 |
|------|-----------|---------|
| **GOOG** | DeepMind 從 2014 年投資 TAE 核聚變，動機是為 AI 算力尋找根本能源解法。這可能拉高 GOOG 長期資本支出。 | 分析 GOOG 時，查 DeepMind 在核聚變/能源上的投資規模和財報披露 |
| **DJT** | 60 億美元收購 TAE，本質是換故事而非改善基本面。死亡峽谷階段的燒錢速度未知。 | 如果有人問 DJT，提醒「無法建立估值模型，避開」 |

#### 📊 板塊 ETF（估值對照基準）

| ETF | 用途 |
|-----|------|
| SPY / QQQ | 大盤估值基準 |
| XLE | 能源板塊基準 |
| XLK / SMH | 科技/半導體基準 |
| XLF | 金融板塊基準 |
| XLU | 公用事業基準 |
| EEM / VWO | 新興市場基準 |

#### 🔑 宏觀指標

| 指標 | 用途 | 頻率 |
|------|------|------|
| 10Y 殖利率 / Fed Funds | 影響所有估值折現率 | 週 |
| DXY（美元指數） | 海外營收兌換影響 | 看標的 |
| USD/CNH | 中國相關標的必看 | 看標的 |

### 監控原則
- **標的涉及哪裡，就追蹤哪裡** — 不做全球廣泛掃描，按需拉取
- **每次分析標的時** — 拉板塊 ETF 做估值對照
- **不跟的事** — 每日股價走勢（Technical）、事件機率（PM Analyst）、散戶情緒（Market Intelligence）
- **定性資訊的邊界** — YouTube/文章的洞見是輸入不是輸出，必須結合財務數據才能形成投資判斷。無法驗證的假設要明確標註

---

## 市場觀點與看法

（從實際分析中累積）

## 分析過的標的記錄

| 日期 | 標的 | 立場 | 結果/複盤 |
|------|------|------|----------|

## 經驗教訓 / 避免的偏誤

1. **[2026-04-01] 編輯了錯誤的知識庫** — 把 Polymarket 分析寫進了 Prediction Market Analyst 的檔案。要確認自己是誰再動筆。
