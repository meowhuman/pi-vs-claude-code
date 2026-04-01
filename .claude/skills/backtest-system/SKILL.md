# 📈 Backtest System Skill v2.1

獨立回測系統 — Tiingo (股票) + CCXT/Binance (加密貨幣)，**無需外接硬碟**。純 pandas/numpy 引擎，6 種策略，支持網格搜索優化、風險管理、圖表視覺化。

---

## 🚀 Quick Commands

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/backtest-system

# 1. 狀態檢查
uv run scripts/status_check.py

# 2. 單次回測
uv run scripts/quick_backtest.py --symbol SPY --strategy sma_crossover --days 365
uv run scripts/quick_backtest.py --symbol BTC --strategy rsi --crypto --days 180

# 3. 策略掃描（多標的多策略）
uv run scripts/strategy_scanner.py --symbols SPY,QQQ,AAPL --top 5

# 4. 參數優化
uv run scripts/optimize_params.py --symbol AAPL --strategy rsi --top 10
```

---

## 🛡 Risk Management (new in v2.1)

### Take Profit / Stop Loss / Trailing Stop

```bash
# Take Profit: 獲利 15% 自動平倉
uv run scripts/quick_backtest.py --symbol AAPL --strategy rsi --take-profit 0.15

# Stop Loss: 虧損 5% 自動平倉
uv run scripts/quick_backtest.py --symbol AAPL --strategy rsi --stop-loss 0.05

# Trailing Stop: 從最高點回撤 8% 平倉
uv run scripts/quick_backtest.py --symbol BTC --strategy macd --crypto --trailing-stop 0.08

# 組合使用
uv run scripts/quick_backtest.py --symbol AAPL --strategy rsi \
  --take-profit 0.20 --stop-loss 0.05 --trailing-stop 0.10
```

**邏輯說明：**
- TP：close >= entry × (1 + take_profit) 時平倉
- SL：close <= entry × (1 - stop_loss) 時平倉
- Trail：close <= 持倉最高點 × (1 - trailing_stop) 時平倉
- 強制平倉後等待原始信號重置（回 0 再回 1）才重新進場，防止雙重計算

### --min-trades 過濾

```bash
# 只看交易次數 ≥ 10 的結果（避免偶然表現）
uv run scripts/quick_backtest.py --symbol AAPL --strategy rsi --min-trades 10
uv run scripts/strategy_scanner.py --symbols SPY,QQQ,AAPL --min-trades 5
uv run scripts/optimize_params.py --symbol AAPL --strategy rsi --min-trades 10
```

---

## 📊 Charts (new in v2.1)

### Equity Curve + Drawdown Chart

```bash
# 開窗顯示（互動式）
uv run scripts/quick_backtest.py --symbol SPY --strategy sma_crossover --chart

# 儲存圖片
uv run scripts/quick_backtest.py --symbol AAPL --strategy rsi --chart --save-chart aapl_rsi.png

# 加上風控再看圖
uv run scripts/quick_backtest.py --symbol BTC --strategy macd --crypto \
  --trailing-stop 0.08 --chart --save-chart btc_trail.png
```

圖表包含：
- **上圖：Equity Curve** — 策略資金曲線 vs Buy & Hold
- **下圖：Drawdown Chart** — 回撤幅度隨時間變化

### 參數優化 Heatmap

```bash
# bollinger_bands: X=bb_period, Y=bb_std, 顏色=Sharpe（自動偵測軸）
uv run scripts/optimize_params.py --symbol SPY --strategy bollinger_bands --heatmap

# RSI: X=rsi_period, Y=rsi_lower
uv run scripts/optimize_params.py --symbol AAPL --strategy rsi --heatmap

# 自訂軸 + 儲存圖片
uv run scripts/optimize_params.py --symbol SPY --strategy rsi \
  --heatmap --heatmap-x rsi_period --heatmap-y rsi_upper --save-heatmap rsi_hm.png

# 用不同 metric 上色（預設 sharpe，可換 return / calmar / win_rate）
uv run scripts/optimize_params.py --symbol AAPL --strategy sma_crossover \
  --heatmap --heatmap-metric return
```

**Heatmap 預設軸對應：**

| Strategy | X 軸 | Y 軸 |
|----------|------|------|
| `sma_crossover` | short_ma | long_ma |
| `ema_crossover` | short_ema | long_ema |
| `rsi` | rsi_period | rsi_lower |
| `bollinger_bands` | bb_period | bb_std |
| `macd` | fast | slow |
| `momentum` | lookback | threshold |

---

## 📊 Available Strategies (6)

| Strategy | Description | Parameters |
|----------|-------------|------------|
| `sma_crossover` | SMA 黃金/死叉 | `short_ma`, `long_ma` |
| `ema_crossover` | EMA 黃金/死叉 | `short_ema`, `long_ema` |
| `rsi` | RSI 均值回歸 | `rsi_period`, `rsi_lower`, `rsi_upper` |
| `bollinger_bands` | Bollinger Bands 反轉 | `bb_period`, `bb_std` |
| `macd` | MACD 交叉 | `fast`, `slow`, `signal_period` |
| `momentum` | N 日動量 | `lookback`, `threshold` |

---

## 📡 Data Sources

| Source | Assets | Timeframes | API Key |
|--------|--------|-----------|---------| 
| Tiingo API | 股票 (AAPL, SPY, QQQ 等) | 日線 (up to 5y) | Built-in demo key |
| Tiingo FX API | 外匯 (EURUSD, XAUUSD 等) | 日線 | Built-in demo key |
| CCXT / Binance | 加密貨幣 (BTC, ETH, SOL) | 1m-1d | Free public API |

> Forex pairs (6-char alpha codes like EURUSD) are auto-detected. You can also pass `--forex` explicitly.

---

## 🔧 Usage Examples

### Single Backtest

```bash
# 股票 SMA 交叉回測
uv run scripts/quick_backtest.py --symbol SPY --strategy sma_crossover --short-ma 10 --long-ma 30

# 加密貨幣 RSI 策略
uv run scripts/quick_backtest.py --symbol BTC --strategy rsi --crypto --rsi-lower 25 --rsi-upper 75

# 外匯 RSI 策略（自動偵測 or --forex）
uv run scripts/quick_backtest.py --symbol EURUSD --strategy rsi --days 365
uv run scripts/quick_backtest.py --symbol XAUUSD --strategy macd --forex --days 180

# 指定回測期間（天）
uv run scripts/quick_backtest.py --symbol TSLA --strategy macd --days 730
```

### Strategy Scanner

```bash
# 掃描 3 個標的 × 6 個策略，過濾低交易次數
uv run scripts/strategy_scanner.py --symbols SPY,QQQ,AAPL --min-trades 5

# 只看特定策略
uv run scripts/strategy_scanner.py --symbols BTC,ETH --strategies rsi,macd --crypto

# 外匯掃描
uv run scripts/strategy_scanner.py --symbols EURUSD,GBPUSD,XAUUSD --forex --top 5

# 輸出 CSV
uv run scripts/strategy_scanner.py --symbols SPY,TSLA,NVDA --export scan_results.csv
```

### Parameter Optimization

```bash
# 網格搜索最佳參數
uv run scripts/optimize_params.py --symbol SPY --strategy sma_crossover

# 優化 RSI 參數（最少 10 次交易）+ Heatmap
uv run scripts/optimize_params.py --symbol AAPL --strategy rsi --metric sharpe --min-trades 10 --heatmap

# 加密貨幣參數優化 + 儲存 Heatmap
uv run scripts/optimize_params.py --symbol BTC --strategy bollinger_bands --crypto \
  --heatmap --save-heatmap btc_bb_heatmap.png
```

### Compose Strategy (Multi-Indicator)

```bash
# 多指標組合策略：RSI 超賣 + MACD 金叉 → 做多，RSI 超買 → 平倉
uv run scripts/quick_backtest.py --symbol AAPL --compose "rsi<30:buy" "macd_cross==1:buy" "rsi>70:sell"

# 加上止損 + 看圖
uv run scripts/quick_backtest.py --symbol SPY \
  --compose "rsi<40:buy" "adx>20:buy" "rsi>75:sell" \
  --stop-loss 0.05 --trailing-stop 0.08 --chart
```

> **Rule format**: `indicator<value:action` — Buy rules use AND logic (all must be true), Sell rules use OR logic (any triggers exit).

---

## 📈 Performance Metrics

- **Total Return**: 累積收益率
- **Annualized Return**: 年化收益率
- **Sharpe Ratio**: 夏普比率 (target > 1.0)
- **Max Drawdown**: 最大回撤 (負數越小越好)
- **Win Rate**: 勝率
- **Profit Factor**: 盈虧比
- **Calmar Ratio**: 年化收益 / 最大回撤
- **Total Trades**: 總交易次數

---

## 🏗️ Architecture

```
scripts/
├── data.py              # 數據層 (Tiingo stocks + Tiingo FX forex + CCXT crypto)
├── strategies.py        # 策略庫 (6 單指標策略 + compose 多指標組合器)
├── engine.py            # 回測引擎 (TP/SL/trailing stop + equity curve series)
├── charts.py            # 圖表 (equity curve, drawdown, heatmap)
├── quick_backtest.py    # CLI 單次回測 (--take-profit/--stop-loss/--trailing-stop/--chart)
├── strategy_scanner.py  # 批量掃描 (--min-trades)
├── optimize_params.py   # 網格搜索 (--min-trades + --heatmap)
└── status_check.py      # 連接測試
```

**Key Features:**
- 純 pandas/numpy，無需 TA-Lib 或 PostgreSQL
- Tiingo API 內建 demo key，即開即用
- CCXT 支持加密貨幣 intraday 數據
- TP/SL/Trailing Stop（強制平倉後防重入）
- `--min-trades` 過濾統計意義不足的參數組合
- matplotlib 圖表：Equity Curve、Drawdown、Heatmap

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | 在 skill 目錄運行 `uv sync` |
| Tiingo rate limit | 使用自帶 key，偶爾會限速，稍後重試 |
| CCXT timeout | 網絡問題，重試即可 |
| No data for symbol | 確認標的是否存在（如 GOOG → GOOGL）|
| 圖表不顯示 | headless 環境下用 `--save-chart chart.png` |

---

**Version**: 2.1  
**Last Updated**: 2026-03-31  
**Data Sources**: Tiingo API, Binance via CCXT
