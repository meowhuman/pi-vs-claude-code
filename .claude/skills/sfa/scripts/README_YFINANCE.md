# YFinance 基本面分析工具

## 概述

完全免費的 Yahoo Finance API 替代方案，支援所有美股基本面數據分析。

## 快速開始

### 基本用法

```bash
# 單個股票分析
python3 yfinance_fundamentals.py get_fundamental_data AAPL

# 多個股票比較
python3 yfinance_fundamentals.py get_multiple_tickers GOOG AMZN NVDA

# 表格輸出
python3 yfinance_fundamentals.py table GOOG AMZN NVDA RDW ASTS
```

### 輸出格式選項

```bash
# JSON 格式（默認）
python3 yfinance_fundamentals.py get_multiple_tickers AAPL MSFT --format json

# 表格格式
python3 yfinance_fundamentals.py get_multiple_tickers AAPL MSFT --format table
```

## 优势 vs Tiingo

- ✅ **免费使用** - 无 API 限制
- ✅ **覆盖所有美股** - 不限 DOW 30
- ✅ **实时数据** - Yahoo Finance 数据
- ✅ **丰富指标** - PE, PB, PS, ROE, ROA 等

## 支持的指标

- **估值指标**: PE, PB, PS, EV/EBITDA
- **盈利能力**: ROE, ROA, 毛利率, 营运利率, 净利率
- **财务健康**: 负债权益比, 流动比率, 速动比率
- **成长指标**: 营收增长, 盈利增长, 季度增长
- **分红信息**: 股息率, 派息比率

## 太空股示例

```bash
# 获取所有太空股数据
python3 yfinance_fundamentals.py table \
  GOOG AMZN NVDA CRS PH ETN RDW RTX STM MCHP LITE COHR RKLB ASTS
```

## 注意事项

- 数据来自 Yahoo Finance，可能有短暂延迟
- 小市值股波动大，财务指标仅供参考
- 亏损公司（如 RDW, RKLB, ASTS）无 PE 比率
