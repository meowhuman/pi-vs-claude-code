---
name: Polymarket Trader v4.0
description: 全方位 Polymarket 交易終端 - 整合版 CLI 工具。Use when user mentions polymarket trading, limit orders, automate profit taking/stop loss, portfolio management, market search, or whale analysis.
---

# Polymarket Trader v4.0 🚀

自動化 Polymarket 交易終端 - 使用 py-clob-client 直接連接 Polymarket CLOB API。

## 📁 目錄結構 (v4.2 重組版)

```
polymarket-trader/scripts/
├──  🎯 核心 CLI 工具
│   ├── pm.py                     # Portfolio Manager (持倉管理)
│   ├── trade.py                  # Trade Engine (交易引擎)
│   ├── search.py                 # Market Search (市場搜尋)
│   └── analyze.py                # Market Analyzer (分析工具)
│
├── 🔍 monitoring/                # 監控系統
│   ├── whale_alert.py            # Whale Alert System v2.0 (大戶監控) ✨
│   ├── holder_tracker.py         # Holder Tracker (倉位追蹤) ✨
│   ├── auto_insider_scan_async.py # Async Insider Scanner v3.0 ⚡
│   └── insider_detail.py         # Insider Detail Analyzer 🔬
│
├── 📊 analysis/                  # 分析工具
│   ├── analyze_odds.py           # Historical Odds Analysis
│   ├── batch_whale_classifier.py # Parallel Whale Classifier ✨ NEW
│   └── monitor_classification.py # Classification Monitor ✨ NEW
│
├── 🔧 utils/                     # 共用模組
│   ├── client.py                 # CLOB Client 初始化
│   ├── positions.py              # 持倉相關
│   ├── market.py                 # 市場數據
│   ├── trader_classification.py  # 交易者角色分類 ✨
│   └── whale_utils.py            # Whale 監控工具 ✨
│
├── 💾 state/                     # 狀態文件
├── 📝 logs/                      # 日誌文件
├── 🗂️ cache/                     # 緩存文件
└── 📦 backup/                    # 舊版備份
```

## Prerequisites

**虛擬環境設定** (必須):
```bash
# 虛擬環境已存在於 ./venv
# 每次使用前必須激活
source venv/bin/activate  # macOS / Linux
```

**環境變數設定** (在 `.env` 文件):
- `POLYGON_PRIVATE_KEY` - 你的 Polygon 私鑰
- `BUILDER_WALLET_ADDRESS` - Builder 錢包地址
- `WALLET_ADDRESS` - 簽名錢包地址
- `MAX_AUTO_AMOUNT` - 自動執行的最大金額 (USDC)

---

## 🎯 PM.py - Portfolio Manager

統一持倉管理入口，整合 dashboard、平倉、報表、再平衡功能。

### 用法

```bash
source venv/bin/activate

# 持倉儀表板
python scripts/pm.py                             # 預設帳戶 (#1)
python scripts/pm.py --account 2                 # 指定帳戶 #2
python scripts/pm.py -a 2                        # 簡寫

# 帳戶管理
python scripts/pm.py accounts                    # 列出所有已配置帳戶

# 平倉 (附流動性檢查)
python scripts/pm.py close <condition_id>
python scripts/pm.py close <condition_id> --auto       # 自動確認
python scripts/pm.py close <condition_id> -a 2         # 使用帳戶 #2

# 檢查流動性
python scripts/pm.py liquidity <condition_id> --outcome Yes

# P&L 報表
python scripts/pm.py report
python scripts/pm.py report --detailed                 # 包含詳細持倉
python scripts/pm.py report -a 2                       # 帳戶 #2 報表

# 再平衡建議
python scripts/pm.py rebalance
```

### 功能

| 指令 | 功能 |
|------|------|
| `pm.py` | 顯示持倉儀表板 (Dashboard) |
| `pm.py accounts` | 列出所有已配置帳戶 |
| `pm.py --account N` | 切換到帳戶 #N |
| `pm.py close <ID>` | 平倉指定市場 (附流動性警告) |
| `pm.py liquidity <ID>` | 檢查市場 Spread |
| `pm.py report` | P&L 盈虧報表 |
| `pm.py rebalance` | 等權重再平衡建議 |

### 多帳戶配置

在 `.env` 中添加多個帳戶：

```bash
# Account #1 (預設，使用原有變數名)
POLYGON_PRIVATE_KEY=your_private_key_here
BUILDER_WALLET_ADDRESS=0x...
WALLET_ADDRESS=0x...

# Account #2
POLYGON_PRIVATE_KEY_2=your_private_key_here
BUILDER_WALLET_ADDRESS_2=0x...
WALLET_ADDRESS_2=0x...

# Account #3
POLYGON_PRIVATE_KEY_3=your_private_key_here
BUILDER_WALLET_ADDRESS_3=0x...
```

**注意**：
- 支援最多 9 個帳戶
- `WALLET_ADDRESS` 可選（預設使用 `BUILDER_WALLET_ADDRESS`）
- 所有指令都支援 `--account` 參數

---

## 💰 Trade.py - Trade Engine

統一交易入口，整合市價單、限價單、TP/SL 功能。

### 用法

```bash
source venv/bin/activate

# === 市價單 ===
# 買入 $10 USDC 的 Yes
python scripts/trade.py buy <condition_id> --outcome Yes --amount 10

# 賣出 5 shares 的 Yes
python scripts/trade.py sell <condition_id> --outcome Yes --shares 5

# === Limit Order ===
# 以 $0.50 掛買單
python scripts/trade.py limit <condition_id> --outcome Yes --side BUY --price 0.50 --amount 10

# 以 $0.60 掛賣單
python scripts/trade.py limit <condition_id> --outcome No --side SELL --price 0.60 --shares 5

# === 訂單管理 ===
python scripts/trade.py orders              # 查看未成交訂單
python scripts/trade.py cancel <order_id>   # 取消訂單
python scripts/trade.py cancel --all        # 取消所有訂單

# === TP/SL 止盈止損 ===
python scripts/trade.py tp <condition_id> --outcome Yes --price 0.70   # Take Profit
python scripts/trade.py sl <condition_id> --outcome Yes --price 0.30   # Stop Loss
python scripts/trade.py alerts                                          # 查看警報
python scripts/trade.py monitor                                         # 啟動監控
python scripts/trade.py remove <alert_id>                               # 移除警報
```

### 功能

| 指令 | 功能 |
|------|------|
| `trade.py buy` | 市價買入 |
| `trade.py sell` | 市價賣出 |
| `trade.py limit` | 掛 Limit Order |
| `trade.py orders` | 查看未成交訂單 |
| `trade.py cancel` | 取消訂單 |
| `trade.py tp` | 設定 Take Profit |
| `trade.py sl` | 設定 Stop Loss |
| `trade.py monitor` | 監控 TP/SL 並自動執行 |

---

## 🔍 Search.py - Market Search

統一市場搜尋入口，支援進階篩選、日期範圍、增量緩存。

### 用法

```bash
source venv/bin/activate

# 基礎搜尋
python scripts/search.py "Trump"                  # Positional 參數
python scripts/search.py -q "Trump"               # 或用 -q flag
python scripts/search.py "NBA" --limit 20

# 類別搜尋（自動搜尋相關關鍵字）
python scripts/search.py -c crypto                # 加密貨幣市場
python scripts/search.py -c sports                # 體育市場
python scripts/search.py -c politics              # 政治市場
python scripts/search.py -c economy               # 經濟市場
python scripts/search.py -c tech                  # 科技市場
python scripts/search.py -c world                 # 世界大事
python scripts/search.py -c entertainment         # 娛樂市場

# 組合類別與其他篩選
python scripts/search.py -c crypto --prob 80:20   # Crypto + 機率 20-80%
python scripts/search.py -c sports --urgent 7     # 體育 + 7日內截止
python scripts/search.py -c politics -q "Trump"   # 政治 + Trump 關鍵字

# 進階篩選
python scripts/search.py -q "Trump" --prob 80:20           # 機率 20-80%
python scripts/search.py -q "Trump" --min-vol 50000        # 最低成交量 $50k
python scripts/search.py -q "Trump" --urgent 7             # 7 日內截止
python scripts/search.py -q "crypto" --sort volume         # 按成交量排序

# 日期範圍搜尋
python scripts/search.py -q "Trump" --date-to "2026-12-31"           # 到 2026 年底
python scripts/search.py -q "Trump" --date-from "2025-01-01"         # 從 2025 年開始
python scripts/search.py --date-from "2025-06-01" --date-to "2025-12-31"  # 指定範圍

# 市場狀態篩選
python scripts/search.py --active                           # 只顯示活躍市場 (預設)
python scripts/search.py --closed                           # 只顯示已結束市場

# 分佈分析
python scripts/search.py --analyze --prob 80:20

# 市場詳情
python scripts/search.py detail <condition_id>
python scripts/search.py url "trump-2024"                   # 從 URL slug

# 緩存管理
python scripts/search.py --fast                             # 快速模式 (只掃最新 1000 個市場)
python scripts/search.py --no-cache                         # 不使用緩存，強制刷新
python scripts/search.py --scan-min-vol 1000                # 降低掃描門檻（預設 $10,000）
# 批量 Insider 掃描 (✨ v4.5 新增)
python scripts/search.py --category politics --scan-insider                # 掃描政治市場
python scripts/search.py --min-vol 500000 --scan-insider --limit 20        # 掃描高成交量市場
python scripts/search.py --scan-insider --insider-min-risk HIGH            # 只看高風險市場
python scripts/search.py refresh                                           # 完整刷新緩存
```

### 參數 (Insider 相關)

| 參數 | 說明 |
|------|------|
| `--scan-insider` | 啟用批量 Insider Activity 掃描 |
| `--insider-price-threshold` | 價格突變門檻 (%) (預設: 10) |
| `--insider-trade-threshold` | 大額交易門檻 ($) (預設: 5000) |
| `--insider-min-risk` | 最低顯示風險等級 (LOW, MEDIUM, HIGH, CRITICAL) (預設: MEDIUM) |

### 參數

| 參數 | 說明 |
|------|------|
| `-q`, `--query` | 搜尋關鍵字 |
| `-c`, `--category` | 類別搜尋: crypto, sports, politics, economy, tech, world, entertainment |
| `--prob` | 機率範圍 (e.g., 80:20 = 20%~80%) |
| `--min-vol` | 最低成交量（搜尋結果篩選） |
| `--urgent` | N 日內截止 |
| `--date-from` | 結束日期範圍 - 開始 (YYYY-MM-DD) |
| `--date-to` | 結束日期範圍 - 結束 (YYYY-MM-DD) |
| `--active` | 只顯示活躍市場 |
| `--closed` | 只顯示已結束市場 |
| `--sort` | 排序: volume / prob / date |
| `--analyze` | 顯示分佈分析 |
| `--fast` | 快速模式 (只更新最新市場) |
| `--no-cache` | 不使用緩存 |
| `--scan-min-vol` | 掃描時最低成交量門檻（預設 $10,000） |
| `--json` | JSON 輸出 |

### 類別關鍵字

每個類別會自動搜尋以下相關關鍵字：

| 類別 | 關鍵字範例 |
|------|----------|
| **crypto** | bitcoin, ethereum, solana, usdt, defi, nft, microstrategy... |
| **politics** | trump, biden, election, president, congress, senate... |
| **sports** | nba, nfl, super bowl, premier league, ufc, olympics... |
| **economy** | fed, inflation, recession, stock, nasdaq, powell... |
| **tech** | apple, google, ai, chatgpt, tesla, spacex, nvidia... |
| **world** | china, russia, ukraine, taiwan, war, climate... |
| **entertainment** | movie, oscar, gta, netflix, spotify, game... |

### 緩存系統

搜尋功能使用增量緩存，避免每次重新掃描全部市場：

| 功能 | 說明 |
|------|------|
| **自動緩存** | 6 小時內使用緩存，無需重新掃描 |
| **增量更新** | 新數據與現有緩存合併，不覆蓋舊數據 |
| **`--fast`** | 只掃描最新 1000 個市場，幾秒完成 |
| **`--no-cache`** | 強制刷新緩存 |
| **`refresh`** | 完整刷新緩存 |

緩存檔案位置：
```
scripts/cache/all_markets_cache_active.json   # 活躍市場
scripts/cache/all_markets_cache_closed.json   # 已結束市場
```

### 輸出格式

搜尋結果會顯示：
- 市場問題
- Yes/No 機率
- 成交量
- 剩餘天數
- **完整 Condition ID**
- **Polymarket 連結**

---

## 📊 Analyze.py - Market Analyzer

統一分析入口，整合市場分析、鯨魚追蹤、錢包起底、賠率分析、Kelly 計算。

### 用法

```bash
source venv/bin/activate

# 市場深度分析
python scripts/analyze.py market <condition_id>

# 鯨魚分析 (找出大戶)
python scripts/analyze.py whales <condition_id>
python scripts/analyze.py whales <condition_id> --min-value 10000   # $10k 門檻

# 錢包起底 (含 MM/Smart Money 識別)
python scripts/analyze.py wallet <address>
python scripts/analyze.py wallet <address> --max-trades 1000

# 賠率分析 (歷史回顧) ✨ 新增完整功能
python scripts/analyze.py odds "EVENT_SLUG"                    # Event 所有子市場
python scripts/analyze.py odds --market <ID>                   # 單一市場
python scripts/analyze.py odds --market <ID> --lookback 3,7    # 自訂回顧期間
python scripts/analyze.py odds --market <ID> --alert           # 警報 JSON
python scripts/analyze.py odds "EVENT" --output report.md      # 導出報告

# Insider 偵測 (異常交易時機) ✨ 新增 v3.1
# 支持 3 種輸入格式: condition_id / event slug / URL
python scripts/analyze.py insider <condition_id>
python scripts/analyze.py insider "will-openai-have-the-best-ai-model"  # Event slug
python scripts/analyze.py insider "https://polymarket.com/event/..."    # URL
python scripts/analyze.py insider <condition_id> --price-threshold 5  # 自訂價格突變門檻
python scripts/analyze.py insider <condition_id> --trade-threshold 10000 # 自訂大額交易門檻
python scripts/analyze.py insider <condition_id> --detail           # 顯示詳細交易明細

# Kelly Criterion 倉位計算
python scripts/analyze.py kelly <condition_id> --estimate 0.6 --bankroll 100

# 交易信號 (綜合分析)
python scripts/analyze.py signal <condition_id>

# 市場持倉分佈 (Smart Money vs Losers) ✨ 新增
python scripts/analyze.py distribution <condition_id>

# 完整持倉分佈 (Goldsky Subgraph, 無 20 人限制!) ✨✨ v4.7 新增
python scripts/analyze.py holders <condition_id>                  # 完整持倉分佈
python scripts/analyze.py holders <condition_id> --top 50         # Top 50 持倉者
python scripts/analyze.py holders <condition_id> --ratio          # 只顯示 Yes/No 比例
python scripts/analyze.py holders <condition_id> --min-balance 1000  # 過濾最低持倉量
```

### 功能

| 指令 | 功能 |
|------|------|
| `analyze.py market` | 市場深度分析 (持倉、交易、價格) |
| `analyze.py whales` | 鯨魚追蹤 (大戶方向) |
| `analyze.py wallet` | 錢包起底 (MM/SM 識別、Win/Loss 追蹤) |
| `analyze.py odds` | 賠率歷史分析 (支持完整參數) ✨ |
| `analyze.py kelly` | Kelly Criterion 最優下注 |
| `analyze.py signal` | 綜合交易信號 |
| `analyze.py distribution` | 市場持倉分佈 & 逆向信號評分 ✨ |
| `analyze.py insider` | Insider 異常交易偵測 (時間規律分析) ✨ |
| `analyze.py holders` | ✨✨ **完整持倉分佈 (Subgraph, 無 20 人限制)** |

---

## 📈 Analyze_Odds.py - 歷史賠率分析器

專業級 Event 賠率分析工具，支持歷史回顧、趨勢追蹤、警報生成。

### 兩種使用方式

**方式1：通過 analyze.py 統一入口** (推薦)
```bash
python scripts/analyze.py odds "EVENT_SLUG"
python scripts/analyze.py odds --market <ID> --lookback 7,14,30
```

**方式2：直接運行獨立工具** (進階功能)
```bash
python scripts/analyze_odds.py "EVENT_SLUG" --lookback 7,14,30
python scripts/analyze_odds.py --market <ID> --alert --alert-threshold 5
python scripts/analyze_odds.py "EVENT" --output report.md --json
```

### 核心功能

- 📊 **多維度歷史回顧**: 同時對比 7天、14天、30天前的賠率變化
- 🚨 **價格突變偵測**: 自動識別 >5% 的顯著機率變化
- 📝 **專業報告導出**: 生成 Markdown 格式的分析報告
- 🔔 **警報 JSON 輸出**: 適合 webhook/Telegram Bot 整合
- 🎯 **趨勢分析總結**: 統計上升/下降市場數量與平均變化
- ✅ **實時價格整合**: 使用 `get_market_info` 獲取最新準確價格

### 參數

| 參數 | 說明 |
|------|------|
| `event` | Event slug (從 URL 取得) 或關鍵字 |
| `--market`, `-m` | 分析單一市場 (使用 Condition ID) |
| `--lookback`, `-l` | 回顧期間 (逗號分隔，預設: "7,14,30") |
| `--output`, `-o` | 導出 Markdown 報告路徑 |
| `--json` | 輸出完整 JSON 格式 |
| `--alert` | 只輸出警報 JSON (變化 >threshold) |
| `--alert-threshold` | 警報門檻百分比 (預設: 10) |

### 輸出範例

**控制台輸出**:
```
🚨==================================================================================🚨
⚠️  顯著變化警報 - 以下市場出現 >5% 機率變化
🚨==================================================================================🚨

1. 📈 Google (7天變化)
   55.20% → 64.50% (+9.30%, 相對變化 +16.85%)

====================================================================================================

1. 🏢 Google
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   當前 YES 價格: $0.6450 | 隱含機率: 64.50%
   當前賠率: 1.55x
   ────────────────────────────────────────────────────────────────────────────────────────
   📅 歷史回顧:
      🚨 7天前: 55.20% → 📈 +9.30% (相對 +16.85%) [2025-12-13]
         14天前: 58.00% → 📈 +6.50% (相對 +11.21%) [2025-12-06]
         30天前: 53.00% → 📈 +11.50% (相對 +21.70%) [2025-11-20]
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   24h 交易量: $12,456.00 | 總交易量: $220,188.00
   ⭐⭐⭐ 市場共識: 極高機會
```

**警報 JSON** (`--alert`):
```json
{
  "event": "Which company has best AI model end of June?",
  "timestamp": "2025-12-20T23:42:00",
  "alert_threshold": 10.0,
  "alert_count": 1,
  "alerts": [
    {
      "market": "Google",
      "period": "7d",
      "from_prob": 55.2,
      "to_prob": 64.5,
      "change": 9.3,
      "change_pct": 16.85,
      "direction": "UP",
      "current_odds": 1.55
    }
  ]
}
```

### 使用場景

1. **長期趨勢追蹤**: 監控多個候選項目的機率演變
2. **警報自動化**: 配合 Telegram Bot 自動通知顯著變化
3. **研究分析**: 導出專業報告進行深度研究
4. **套利機會**: 快速發現價格異常波動的市場

---

## 📊 Market Distribution Analysis - 市場分佈分析

分析市場中不同類型交易者的持倉分佈，並生成 **Contrarian Signal (逆向信號)** 評分。

### 指令
```bash
python scripts/analyze.py distribution <condition_id>
```

### 0-100 評分系統

該系統根據 Smart Money 與散戶/輸家的方向分歧進行評分：

- **0-30: 弱信號 ⚪** (市場共識一致或數據不足)
- **31-50: 中等信號 🟡** (存在輕微情緒分歧)
- **51-70: 強信號 🟠** (顯著分歧，Smart Money 與輸家方向相反)
- **71-100: 極強信號 🔥** (極端分歧，高勝率逆向機會)

### 交易者角色定義

| 角色 | 圖示 | 定義 |
|------|------|------|
| **Smart Money** | 🧠 | 盈利豐厚、交易經驗豐富的專業交易者 |
| **Market Maker** | 🏦 | 高頻交易、提供流動性、買賣平衡的機構/機器人 |
| **Losers** | 📉 | 顯著虧損 (> -$1,000) 的非專業交易者 |
| **Whale** | 🐋 | 大額持倉 (>$10,000) 但未必是 Smart Money |
| **Retailer** | 🎰 | 小額持倉 (<$1,000) 且交易經驗較少的新手/散戶 |
| **Regular** | 👤 | 一般普通交易者 |

- 👉 **結論**: 建議買入 **NO** (信號評分會大幅提升)

---

## 🕵️ Insider Activity Detector - 異常交易偵測 v3.1

專門用於偵測「春江水暖鴨先知」的交易模式。通過比對 **價格突變 (Price Spike)** 與其 **前 24 小時內** 的異常大額交易，識別潛在的內幕交易風險。

### 核心邏輯

1.  **精確突變識別**: 自動追蹤價格在短時間內的劇烈波動（例如 >10%）。
2.  **24 小時黃金窗口**: 焦點鎖定在價格突變前的 1-24 小時，這是內幕交易最集中的時間段。
3.  **大額交易關聯**: 自動過濾符合突變方向的大額買入/賣出操作。
4.  **詳細窗口分析**: 生成 24 小時內的交易分佈報告，包括淨買壓、多空比例和平均押注額。
5.  **覆蓋檢查系統**: 自動警告交易歷史不足的窗口，確保分析透明度。

### 評分機制 (0-60)

| 指標 | 最高分 | 說明 |
|------|------|------|
| **時機 (Timing)** | 10 | 1-6 小時內最可疑；越接近突變分數越高 |
| **金額 (Value)** | 30 | 單一錢包押注金額越大分數越高 ($1k = 1分) |
| **模式 (Pattern)** | 20 | 命中多次不同時間點的價格突變 = 慣犯模式 |

### 輸出報告內容

- **精確時間戳**: 顯示價格突變的精確到分鐘的時間（e.g., `06:00`）。
- **交易分佈**: 統計窗口內 Yes/No 的買賣筆數。
- **淨買壓 (Net Pressure)**: 識別是否有特定方向的瘋狂吸籌。
- **錢包起底**: 列出 Top 10 最可疑錢包及其歷史命中記錄。

---

## 🔧 Utils - 共用模組

如果你需要喺其他腳本 import 共用函數：

```python
from utils.client import get_client, get_api_urls, get_wallets
from utils.positions import get_all_positions, parse_position
from utils.market import get_market_info, get_orderbook
```

---

## 🚨 Auto Insider Scanner v3.0 - 全自動內幕掃描器 (異步並發版)

批量掃描數百個市場,自動識別可疑的內幕交易活動。使用 `asyncio` + `aiohttp` 實現並發請求,速度提升 **5-10 倍**。

### 核心功能

1. **異步並發掃描**: 同時處理多個市場,大幅提升速度
2. **智能價格突變檢測**: 自動識別顯著的價格變化 (>15%)
3. **持續性驗證**: 檢查突變後價格是否持續朝同方向移動
4. **大額交易關聯**: 自動抓取突變前 48 小時的大額交易 (>= $3,000)
5. **風險評分系統**: 0-100 分評分,分為 LOW/MEDIUM/HIGH/CRITICAL 四個等級
6. **斷點續傳**: 支援從指定市場索引繼續掃描
7. **香港時間顯示**: 所有時間自動轉換為 HKT (UTC+8)

### 使用方法

```bash
source venv/bin/activate

# 基本掃描 (掃描前 1500 個市場)
python scripts/auto_insider_scan_async.py

# 自訂參數
python scripts/auto_insider_scan_async.py --max 500 --min-vol 100000 --concurrency 30

# 從第 1102 個市場繼續掃描
python scripts/auto_insider_scan_async.py --start-index 1102 --max 398

# 跳過緩存更新 (更快)
python scripts/auto_insider_scan_async.py --no-cache-update

# 只顯示 HIGH 以上風險
python scripts/auto_insider_scan_async.py --min-risk HIGH
```

### 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--max` | 最多掃描市場數量 | 1500 |
| `--min-vol` | 最低成交量 (USD) | 50000 |
| `--threshold` | 相對價格變化門檻 (%) | 15.0 |
| `--abs-threshold` | 絕對價格變化門檻 (%) | 3.0 |
| `--min-risk` | 最低顯示風險等級 | MEDIUM |
| `--start-index` | 從第幾個市場開始掃描 | 0 |
| `--concurrency` | 並發請求數 | 20 |
| `--no-cache-update` | 跳過緩存更新 | False |

### 風險評分系統

**評分因素**:
1. **價格變化幅度** (0-30 分)
   - 極大變化 (>50%): 30 分
   - 大幅變化 (>30%): 20 分
   - 顯著變化 (>15%): 10 分

2. **價格持續性** (0-20 分)
   - 突變後持續朝同方向: +20 分

3. **突變前大額交易** (0-30 分)
   - 總金額 >$100,000: 30 分
   - 總金額 >$50,000: 20 分
   - 總金額 >$10,000: 10 分

4. **交易時間接近度** (0-20 分)
   - <6 小時: 20 分
   - <24 小時: 10 分

**風險等級**:
- **CRITICAL** (70-100 分): 🚨 極高風險,強烈懷疑內幕交易
- **HIGH** (50-69 分): ⚠️ 高風險,值得深入調查
- **MEDIUM** (30-49 分): ⚡ 中等風險,存在可疑跡象
- **LOW** (0-29 分): ✅ 低風險,可能是正常波動

### 輸出格式

```
🚨 全自動 Insider 掃描器 v3.0 (異步並發)
   最低成交量: $50,000
   掃描範圍: 0 ~ 1500
   相對門檻: 15.0%
   絕對門檻: 3.0% (極端市場)
   並發數: 20
================================================================================

📊 符合條件的市場: 1440 個
   將掃描 1440 個

[1/1440] Will Bitcoin reach $100k by 2025?... ⚠️ 3 Insider 事件 (HIGH)
[2/1440] Will Trump win 2024 election?... ✅ 無可疑
...

🎯 掃描完成!
================================================================================

發現 97 個市場符合風險門檻 (>= MEDIUM):

1. 🚨 SpaceX Starship Flight Test 12...
   風險: CRITICAL (評分: 80/100)
   成交量: $239,135
   Insider 事件: 5 次
   最可疑事件: 2025-12-09
      價格: 30.55% → 9.05% (-70.4%)
      突變前交易: $112,660 (20 筆)
   連結: https://polymarket.com/event/spacex-starship-flight-test-12
   ID: 0xc6853f...
   💡 查看詳細圖表: python3 insider_detail.py 0xc6853f... --start 12-09

💾 完整結果已保存到: /tmp/auto_insider_scan_async_20251221_130617.json
```

### 性能對比

| 版本 | 掃描 400 個市場 | 並發數 |
|------|----------------|--------|
| 同步版 (`auto_insider_scan.py`) | ~15-20 分鐘 | 1 |
| 異步版 (`auto_insider_scan_async.py`) | ~2-3 分鐘 | 20-30 |
| **速度提升** | **5-8 倍** | - |

---

## 🔬 Insider Detail Analyzer - 詳細圖表分析器

針對單個市場生成完整的價格走勢圖表和內幕交易分析報告。

### 核心功能

1. **ASCII 價格走勢圖**: 直觀顯示價格變化
2. **香港時間顯示**: 所有時間使用 HKT (UTC+8)
3. **交易標註**: 在圖表上標記大額交易位置
4. **突變分析**: 詳細列出每次價格突變的資訊
5. **錢包追蹤**: 識別並分組可疑錢包
6. **時間範圍篩選**: 可指定日期範圍查看

### 使用方法

```bash
source venv/bin/activate

# 基本用法
python scripts/insider_detail.py <condition_id>

# 指定日期範圍 (推薦)
python scripts/insider_detail.py <condition_id> --start 12-08 --end 12-12

# 查看更多天數
python scripts/insider_detail.py <condition_id> --days 30
```

### 參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `cid` | 市場的 Condition ID (必填) | - |
| `--days` | 查看過去多少天的數據 | 17 |
| `--start` | 起始日期 (格式: MM-DD) | None |
| `--end` | 結束日期 (格式: MM-DD) | None |

### 輸出範例

```
======================================================================
🔍 Polymarket 內幕掃描 - 詳細分析器
======================================================================

📌 市場: Will SpaceX Starship Flight Test 12 launch by December 31?
   成交量: $239,135
   連結: https://polymarket.com/event/spacex-starship-flight-test-12
   Condition ID: 0xc6853f6ca9bb4b31241069f0243326dda991661e173de4518b95483ec01c5a3c

📈 獲取價格歷史 (過去 17 天)...
   獲取到 50 個數據點

💼 獲取交易記錄...
   獲取到 38 筆大額交易 (>= $1,000)

⚡ 檢測到 14 次價格突變 (>= 15%)

📊 價格走勢圖 (香港時間 HKT)
──────────────────────────────────────────────────────────────────────

12-08 21:20   30.55%  ████████████████████████████████ ← ⬆️ +3115.8%
12-08 23:00   12.30%  █████████████
12-09 00:40   11.65%  ████████████
12-09 02:20    9.40%  ██████████
12-09 04:00    5.60%  ██████
12-09 05:40    9.05%  ██████████
12-09 07:20    5.90%  ██████
12-09 09:00    5.95%  ██████
12-09 10:40    5.70%  ██████  ← 💰 $9,760 BUY
12-09 12:20    5.60%  ██████
12-09 14:00    5.90%  ██████
12-09 15:40    4.60%  █████
12-09 17:20    6.40%  ███████
12-09 19:00    6.40%  ███████
12-09 20:40    3.85%  ████  ← ⬇️ -39.8%
12-09 22:20    2.45%  ███
12-10 00:00    2.40%  ███

──────────────────────────────────────────────────────────────────────

💰 大額交易記錄 (>= $1,000)
──────────────────────────────────────────────────────────────────────

時間                   金額 方向     結果     錢包
----------------------------------------------------------------------
12-09 01:57  $    9,630 BUY    No     0xac1c732b...
12-09 02:02  $    9,630 BUY    No     0xac1c732b...
12-09 02:05  $    9,630 BUY    No     0xac1c732b...
12-09 02:17  $    9,630 BUY    No     0xac1c732b...
12-09 02:22  $    9,720 BUY    No     0xac1c732b...
12-09 02:25  $    9,780 BUY    No     0xac1c732b...
12-09 02:26  $    9,780 BUY    No     0xac1c732b...
12-09 02:34  $    9,770 BUY    No     0xac1c732b...
12-09 02:37  $    9,770 BUY    No     0xac1c732b...
12-09 02:40  $    9,760 BUY    No     0xac1c732b...

🕵️ 內幕交易分析
──────────────────────────────────────────────────────────────────────

1. ⬇️ 突變: 12-09 05:40
   價格: 30.55% → 9.05% (-70.4%)

   📊 突變前 48 小時交易統計:
   總金額: $112,660
   交易筆數: 20
   涉及錢包: 1 個

   🔝 最大交易錢包:
   • 0xac1c732b02bc35...: $112,660 (20 筆)

======================================================================
```

### 使用場景

1. **深入調查**: 批量掃描發現可疑市場後,使用此工具深入分析
2. **時間線還原**: 完整還原價格變化和交易時間線
3. **錢包追蹤**: 識別重複出現的可疑錢包
4. **報告生成**: 生成詳細的分析報告

### 工作流程

```bash
# 步驟 1: 批量掃描找出可疑市場
python scripts/auto_insider_scan_async.py --max 1500

# 步驟 2: 從輸出中複製感興趣市場的命令
# 輸出會顯示: 💡 查看詳細圖表: python3 insider_detail.py 0xc6853f... --start 12-09

# 步驟 3: 運行詳細分析
python scripts/insider_detail.py 0xc6853f6ca9bb4b31241069f0243326dda991661e173de4518b95483ec01c5a3c --start 12-08 --end 12-12
```

---

## 📋 快速參考表

| 任務 | 指令 |
|------|------|
| 查看持倉 | `python scripts/pm.py` |
| 平倉 | `python scripts/pm.py close <ID>` |
| P&L 報表 | `python scripts/pm.py report` |
| 搜尋市場 | `python scripts/search.py "keyword"` |
| 市場詳情 | `python scripts/search.py detail <ID>` |
| 買入 | `python scripts/trade.py buy <ID> -o Yes -a 10` |
| 賣出 | `python scripts/trade.py sell <ID> -o Yes -s 5` |
| 限價單 | `python scripts/trade.py limit <ID> -o Yes -S BUY -p 0.50 --amount 10` |
| 設定止盈 | `python scripts/trade.py tp <ID> -o Yes -p 0.70` |
| 設定止損 | `python scripts/trade.py sl <ID> -o Yes -p 0.30` |
| 監控 TP/SL | `python scripts/trade.py monitor` |
| 市場分析 | `python scripts/analyze.py market <ID>` |
| 鯨魚分析 | `python scripts/analyze.py whales <ID>` |
| 錢包起底 | `python scripts/analyze.py wallet <ADDRESS>` |
| Kelly 計算 | `python scripts/analyze.py kelly <ID> -e 0.6` |
| 交易信號 | `python scripts/analyze.py signal <ID>` |
| 賠率回顧 (Event) | `python scripts/analyze.py odds "EVENT_SLUG"` |
| 賠率回顧 (單市場) | `python scripts/analyze.py odds --market <ID>` |
| 賠率警報 | `python scripts/analyze.py odds --market <ID> --alert` |
| Insider 偵測 | `python scripts/analyze.py insider <ID>` |

---

## 📦 舊版腳本 (Backup)

以下舊版腳本已整合並移至 `backup/`，但仍可獨立使用：

| 舊版腳本 | 新版對應 |
|----------|----------|
| `portfolio.py` | `pm.py` |
| `get_positions.py` | `pm.py` |
| `rebalance.py` | `pm.py rebalance` |
| `pnl_report.py` | `pm.py report` |
| `execute_trade.py` | `trade.py buy/sell` |
| `limit_order.py` | `trade.py limit` |
| `tp_sl.py` | `trade.py tp/sl/monitor` |
| `search_market.py` | `search.py` |
| `search_extended_markets.py` | `search.py` |
| `analyze_market.py` | `analyze.py market` |
| `kelly.py` | `analyze.py kelly` |

---

## Examples

### Example 1: 搜尋並買入

```bash
source venv/bin/activate

# 1. 搜尋市場
python scripts/search.py "Trump" --limit 5

# 2. 查看詳情
python scripts/search.py detail 0xabc123...

# 3. 買入
python scripts/trade.py buy 0xabc123... --outcome Yes --amount 10

# 4. 設定止盈止損
python scripts/trade.py tp 0xabc123... --outcome Yes --price 0.70
python scripts/trade.py sl 0xabc123... --outcome Yes --price 0.30

# 5. 啟動監控
python scripts/trade.py monitor
```

### Example 2: 分析後決策

```bash
source venv/bin/activate

# 1. 市場分析
python scripts/analyze.py market 0xabc123...

# 2. 鯨魚分析
python scripts/analyze.py whales 0xabc123...

# 3. Kelly 計算 (你估計 60% 機率)
python scripts/analyze.py kelly 0xabc123... --estimate 0.6 --bankroll 100

# 4. 綜合信號
python scripts/analyze.py signal 0xabc123...

# 5. Insider 偵測 (檢查是否有內幕人士提前佈局)
python scripts/analyze.py insider 0xabc123...
```

### Example 3: 持倉管理

```bash
source venv/bin/activate

# 查看持倉
python scripts/pm.py

# 查看報表
python scripts/pm.py report --detailed

# 平倉
python scripts/pm.py close 0xabc123...
```

---

## Security Notes

1. **私鑰安全**: `.env` 絕對不能 commit
2. **交易確認**: 大額交易會詢問確認
3. **最低金額**: Polymarket 最低 $1 USDC

---

## Troubleshooting

**搜尋找不到結果?**
- 試不同關鍵字
- 用 `--limit` 增加結果數

**交易失敗?**
- 檢查餘額: `python scripts/check_balance.py`
- 檢查市場狀態

**TP/SL 沒有觸發?**
- 確保 `trade.py monitor` 正在運行
- 用 `trade.py alerts` 檢查警報

---

**Version**: 4.7.0  
**Last Updated**: 2025-12-24  
**Author**: Polymarket Trading Skill

### 更新日誌

- **v4.7.0 (2025-12-24)**: 🚀 **Goldsky Subgraph 全持倉分析 (突破 20 人限制!)**
  - **新工具**: `analyze.py holders` 使用 Goldsky Subgraph 取得**完整**持倉分佈，無 20 人限制！
  - **新模組**: `utils/subgraph.py` Subgraph 客戶端，支援游標分頁。
  - **功能**: 顯示 Yes/No 持倉比例、Top N 持倉者、集中度分析、大戶數量。
  - **參數**: `--top N` 顯示 Top N 持倉者，`--ratio` 只顯示比例，`--min-balance` 過濾最低持倉量。
- **v4.6.0 (2025-12-21)**: ⚡ **Async Insider Scanner v3.0 + Detail Analyzer**
  - **新工具**: `auto_insider_scan_async.py` 異步並發版內幕掃描器,速度提升 5-10 倍。
  - **新工具**: `insider_detail.py` 詳細圖表分析器,生成 ASCII 價格走勢圖。
  - **修復**: 修正交易錢包抓取問題 (使用正確的 API 欄位 `size` 和 `price`)。
  - **改進**: 所有時間自動轉換為香港時間 (HKT = UTC+8)。
  - **改進**: 批量掃描器輸出中添加詳細分析命令提示。
  - **並發控制**: 支援自訂並發數 (`--concurrency` 參數)。
  - **視覺化**: ASCII 圖表直觀顯示價格走勢和交易標註。
- **v4.5.0 (2025-12-21)**: 🚀 **Full Auto Insider Detector v1.0**
  - **新工具**: `auto_insider_scan.py` 全自動全網內幕掃描器。
  - **改進偵測邏輯**: 加入「價格持續性分析」，自動檢測突變後 3 天的走勢。
  - **自動關聯系統**: 發現突變自動抓取並分析前 48 小時大額交易。
  - **智能門檻系統**: 解決極端概率市場 (如 0.5%) 的假陽性偵測問題。
  - **批量整合**: `search.py` 現在支持 `--scan-insider` 選項進行快速掃描。
  - **詳細報告**: 更新 Insider 報告格式，包含 Full Wallet 地址與活動 URL。
- **v4.4.0 (2025-12-21)**: 🕵️ **Insider Detector v3.1**
  - 新增 `analyze.py insider` 指令，專業偵測春江水暖交易。
  - 縮小分析窗口至 24 小時（更精確的 Insider 偵測黃金時段）。
  - 新增精確到分鐘的價格突變時間戳顯示。
  - 新增「窗口報告」：顯示前 24 小時內的交易分布、買賣壓力及金額。
  - 新增「數據覆蓋警告」：自動識別因 API 限制而無法分析的歷史突變。
  - 整合多空全量統計（買入 + 賣出），取代純買入統計。
- **v4.3.0 (2025-12-20)**: 💼 **多帳戶支援**
  - 新增多帳戶管理功能（最多 9 個帳戶）
  - 新增 `pm.py accounts` 指令列出所有帳戶
  - 新增 `--account` / `-a` 參數切換帳戶
  - 儀表板顯示帳戶編號和 Builder Wallet 地址
  - 向後兼容：Account #1 使用原有環境變數
  - 所有 PM 指令都支援多帳戶
- **v4.2.0 (2025-12-20)**: 🏷️ **類別搜尋**
  - 新增類別搜尋功能 (`-c`, `--category`)
  - 支援 7 大類別：crypto, sports, politics, economy, tech, world, entertainment
  - 每個類別包含 20-30 個相關關鍵字，自動匹配
  - 支援 positional query 參數（無需 `-q`）
  - 新增緩存資訊顯示（總市場數、成交量門檻）
  - 預設掃描門檻設為 $10,000（`--scan-min-vol`）
  - 修正 Polymarket 連結格式（使用 Event slug）
- **v4.1.0 (2025-12-20)**: 🔍 **搜尋增強**
  - 新增日期範圍搜尋 (`--date-from`, `--date-to`)
  - 新增市場狀態篩選 (`--active`, `--closed`)
  - 新增快速模式 (`--fast`) - 只掃描最新 1000 個市場
  - 實現增量緩存更新，避免重複掃描
  - 輸出顯示完整 Condition ID 和 Polymarket 連結
  - 修正機率篩選邏輯 (`--prob 80:20` = 20%-80%)
- **v4.2.0 (2025-12-21)**: 🐋 **Whale Alert System v2.0**
  - 從 `polymarket-analyzer` 遷移至 `polymarket-trader`
  - 整合 `trader_classification.py` 進行智能錢包分類
  - 過濾通知：只彈出 Smart Money、Whale、Loser
  - 自動排除 Market Maker 和散戶
  - 通知顯示交易者角色 emoji (🧠/🐋/📉)
- **v4.0.0 (2025-12-19)**: 🎉 **重大重構** - 整合所有腳本
  - 17 個腳本整合為 4 個主要 CLI 工具
  - 新增 `pm.py` (Portfolio Manager)
  - 新增 `trade.py` (Trade Engine)
  - 新增 `search.py` (Market Search)
  - 新增 `analyze.py` (Market Analyzer)
  - 新增 `utils/` 共用模組
  - 舊版腳本移至 `backup/`
- v3.0.0 (2025-12-19): 專業交易終端
- v2.5.0 (2025-12-19): 增強版擴展搜尋
- v2.0.0 (2025-12-05): 支持 SELL 交易


---

## 🐋 Whale Alert System v2.0 - 智能大戶監控

即時監控 Polymarket 大額交易，自動分類交易者角色，過濾出值得關注的 Smart Money、Whale 和 Loser。

### 核心功能

1. **智能分類**: 整合 `trader_classification.py`，自動識別交易者角色
2. **精準過濾**: 只通知 Smart Money(🧠)、Whale(🐋)、Loser(📉)
3. **自動排除**: 過濾掉 Market Maker(🏦) 和散戶(🎰)
4. **桌面通知**: Mac 原生通知，附帶錢包角色 emoji
5. **LaunchAgent**: 每小時自動掃描，無人值守運行

### 交易者角色定義

| 角色 | Emoji | 定義 | 是否通知 |
|------|-------|------|---------|
| **Smart Money** | 🧠 | 盈利 \u003e $0 + 適度交易頻率 + 豐富經驗 | ✅ **重點關注** |
| **Whale** | 🐋 | 持倉 \u003e $10k + 盈利中 | ✅ **值得關注** |
| **Loser** | 📉 | 虧損 \u003e $1k + 大資金 | ✅ **反向指標** |
| **Market Maker** | 🏦 | 超高頻交易 + 雙向報價 | ❌ 過濾掉 |
| **Retailer** | 🎰 | 小額 \u003c $3k + 經驗少 | ❌ 過濾掉 |
| **Regular** | 👤 | 普通交易者 | ❌ 過濾掉 |

### 使用方法

**手動執行**:
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt/scripts
python whale_alert.py
```

**自動執行 (LaunchAgent)**:
```bash
# 已自動配置，每小時運行一次
# 查看狀態
launchctl list | grep polymarket

# 手動觸發
launchctl start com.polymarket.whalealert

# 查看日誌
tail -f ~/Documents/Obsidian/logs/whale_alert.log
```

### 配置檔案

**LaunchAgent 設定**: `~/Library/LaunchAgents/com.polymarket.whalealert.plist`
- 執行頻率: 每小時
- 日誌位置: `~/Documents/Obsidian/logs/whale_alert.log`
- 錯誤日誌: `~/Documents/Obsidian/logs/whale_alert_error.log`
- 狀態檔案: `.whale_alert_state.json`

**狀態檔案**: `.whale_alert_state.json`
```json
{
  "last_check": "2025-12-21T09:00:14Z",
  "seen_txs": [...],        // 已見過的交易 hash (避免重複通知)
  "whale_wallets": {...}    // Top 20 大戶錢包追蹤
}
```

### 輸出範例

```
[2025-12-21 17:59:48] Checking whale activity...

🔍 Classifying 15 new large trades...
  🧠 0x1234...ab: SMART_MONEY (HIGH)
  🏦 0x5678...cd: MARKET_MAKER (HIGH)
    ↳ Skipping MARKET_MAKER (filtered out)
  🐋 0x9abc...ef: WHALE (MEDIUM)
  📉 0xdef0...12: LOSER (HIGH)

✅ Found 8 trades from 3 notable wallets:
  - [12:34:56] 🧠 0x1234...ab (SMART_MONEY) BUY $12,500.00 on Trump 2024 Election...
  - [12:35:20] 🐋 0x9abc...ef (WHALE) BUY $8,750.00 on Bitcoin $100k by 2025...
  - [12:36:10] 📉 0xdef0...12 (LOSER) SELL $5,200.00 on AI Leadership Q1...
```

### 通知範例

```
🐋 Polymarket Whale Alert
8 trades! 🧠 0x1234...ab: $12,500 | 🐋 0x9abc...ef: $8,750 | 📉 0xdef0...12: $5,200
```

### 參數調整

在 `whale_alert.py` 中可調整：

```python
# 最低交易金額門檻
MIN_TRADE_VALUE = 500  # USD

# 通知角色過濾
ALERT_ROLES = {'SMART_MONEY', 'WHALE', 'LOSER'}
```

### 與其他工具整合

```bash
# 發現可疑錢包後，深入分析
python analyze.py wallet 0x1234567890abcdef...

# 批次分析所有 whale 錢包
cat .whale_alert_state.json | jq -r '.whale_wallets | keys[]' | \
  while read wallet; do
    python analyze.py wallet "$wallet"
  done
```

### 常見問題

**Q: 為什麼有些大額交易沒有通知？**
A: 因為被分類為 Market Maker 或 Retailer 而過濾掉了。這是設計行為，避免噪音。

**Q: 如何調整分類標準？**
A: 編輯 `utils/trader_classification.py` 中的評分規則。

**Q: 狀態文件可以刪除嗎？**
A: 可以，刪除後會重新建立，但可能會收到重複的舊交易通知。

---

## 🤖 Trade Monitoring SDK Agent - 智能交易監控 v1.0

整合 SDK Agent 框架的進階交易監控系統，支持 Take Profit (TP) / Stop Loss (SL) 自動化與 LLM 報告生成。

### 核心功能

1. **自動化 TP/SL 執行**: 每 5 分鐘自動檢查活躍警報，達到觸發價時自動執行平倉。
2. **LLM 狀態報告**: 每次監控後使用 DeepSeek V3.2 分析價格變化，生成簡潔的狀態報告。
3. **LaunchAgent 整合**: 使用 macOS LaunchAgent 穩定運行，無需手動掛載。
4. **透明化日誌**: 所有監控記錄與交易結果均保存於 `sdk-agent/outputs`。

### 使用方法

**1. 設定警報 (經由 trade.py)**:
```bash
# 設定 70% 止盈
python scripts/trade.py tp <condition_id> --outcome Yes --price 0.70

# 設定 30% 止損 
python scripts/trade.py sl <condition_id> --outcome Yes --price 0.30
```

**2. 自動監控 (已讀取 LaunchAgent)**:
- Agent 名稱: `polymarket_trade_monitor`
- 執行頻率: 每 5 分鐘
- 報告路徑: `00_Command_Center/sdk-agent/outputs/polymarket-trade-monitor/trade-monitor-report.md`
- 日誌路徑: `~/Documents/Obsidian/logs/trade_monitor.log`

### 狀態管理

- **警報檔案**: `scripts/cache/tp_sl_alerts.json`
- **觸發後處理**: 成功執行平倉後，該警報狀態會標記為 `triggered`，避免重複執行。

---

## 📊 版本歷史
- **v4.8.0 (2025-12-31)**: 🤖 **Trade Monitoring SDK Agent**
  - 新增 `polymarket_trade_monitor_agent.py` 整合至 SDK Agent 框架。
  - 實現 5 分鐘間隔的自動化 TP/SL 監控。
  - 整合 LLM 生成交易狀態分析報告。
- v4.7.0 (2025-12-24): 🚀 **Goldsky Subgraph 全持倉分析**
- v4.0.0 (2025-12-19): 🎉 **重大重構** - 整合所有腳本
