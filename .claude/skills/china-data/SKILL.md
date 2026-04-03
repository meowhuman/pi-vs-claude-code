---
name: china-data
description: 中國市場資料統一 CLI — A股即時報價/歷史行情/財報、宏觀指標(CPI/PPI/PMI/GDP/M2/LPR)、財經新聞、市場情緒(雪球/微博)。零 API Key，使用 AKShare + BaoStock 完全免費。Use when user needs Chinese stock data, A-share quotes, China macro data, Chinese financial news, or market sentiment.
---

# China Data — 中國市場資料 CLI

統一 CLI 工具，整合 AKShare + BaoStock，覆蓋 A股、宏觀、新聞、情緒四大模組。**無需任何 API Key**。

## 資料來源

| 模組 | 來源 | 說明 |
|------|------|------|
| 股票行情 | AKShare (東方財富/新浪/雪球) | A/B/H 股，即時+歷史+財報 |
| 股票行情 (備援) | BaoStock | 長歷史資料，更穩定 |
| 宏觀經濟 | NBS (國家統計局) via AKShare | CPI/PPI/PMI/GDP |
| 貨幣/利率 | PBOC (人民銀行) via AKShare | M2/LPR/SHIBOR/外匯 |
| 財經新聞 | 東方財富 + 新浪財經 | 個股/市場新聞 |
| 市場情緒 | 雪球/微博/東方財富 | 熱榜/熱搜/市場廣度 |

## 前置作業

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/china-data
uv sync
```

無需設定 `.env`，核心功能完全免費。

## 工作目錄

**所有指令從此目錄執行：**
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/china-data
```

## 指令參考

### 股票 (stock)

```bash
uv run scripts/china_data.py stock quote 600519        # 貴州茅台即時報價
uv run scripts/china_data.py stock quote 00700         # 騰訊控股 (港股)
uv run scripts/china_data.py stock hist 000001         # 平安銀行 90 天歷史
uv run scripts/china_data.py stock hist 600519 --days 365  # 1 年歷史
uv run scripts/china_data.py stock hist 000001 --csv   # CSV 輸出 (可 pipe)
uv run scripts/china_data.py stock financials 600519   # 財務報表
uv run scripts/china_data.py stock news 600519         # 個股新聞
uv run scripts/china_data.py stock top                 # 漲跌排行榜
```

### 宏觀 (macro)

```bash
uv run scripts/china_data.py macro cpi     # 消費者物價指數 (月度)
uv run scripts/china_data.py macro ppi     # 工業生產者價格指數
uv run scripts/china_data.py macro pmi     # PMI 製造業+服務業+財新
uv run scripts/china_data.py macro gdp     # GDP 季度數據
uv run scripts/china_data.py macro m2      # 貨幣供應 M0/M1/M2
uv run scripts/china_data.py macro fx      # 外匯儲備 + 人民幣匯率
uv run scripts/china_data.py macro rates   # LPR + SHIBOR 利率
```

### 新聞 (news)

```bash
uv run scripts/china_data.py news market              # 市場要聞
uv run scripts/china_data.py news flash               # 重大公告快訊
uv run scripts/china_data.py news search "新能源"     # 關鍵字搜尋
uv run scripts/china_data.py news market --count 30   # 顯示 30 條
```

### 情緒 (sentiment)

```bash
uv run scripts/china_data.py sentiment xueqiu   # 雪球/東方財富人氣榜
uv run scripts/china_data.py sentiment weibo    # 微博財經熱搜
uv run scripts/china_data.py sentiment index    # 市場廣度+北向資金+情緒
```

### 狀態檢查

```bash
uv run scripts/china_data.py status   # 依賴版本 + 市場開閉狀態
```

## 更新 AKShare

AKShare 頻繁更新 API 介面，遇到 `AttributeError` 時：
```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/china-data
uv add akshare --upgrade
```

## 常見使用場景

**分析茅台基本面：**
```bash
uv run scripts/china_data.py stock quote 600519
uv run scripts/china_data.py stock financials 600519
uv run scripts/china_data.py stock hist 600519 --days 365 --csv
```

**中國宏觀概覽：**
```bash
uv run scripts/china_data.py macro cpi
uv run scripts/china_data.py macro pmi
uv run scripts/china_data.py macro rates
```

**市場情緒掃描：**
```bash
uv run scripts/china_data.py sentiment index
uv run scripts/china_data.py sentiment xueqiu
uv run scripts/china_data.py stock top
```
