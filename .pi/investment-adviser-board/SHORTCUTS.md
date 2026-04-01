# Investment Adviser Board — 快捷方式

> **重要：** 所有 `just ext-inv-board-*` 指令都啟動**同一個 extension**。
> Preset（委員組合）是在 session 內透過 **tool 參數** 傳入，不是 env var。

---

## Just 快捷方式

```bash
# Mode A — 自動模式（你不在迴圈中，用 board_begin 啟動）
just ext-inv-board          # 啟動 extension，session 內呼叫 board_begin

# Mode B — 互動模式（你坐進委員會，用 board_discuss 啟動）
just ext-inv-board-discuss  # 啟動 extension，session 內呼叫 board_discuss

# 以下為「有語意標籤」的快捷方式，啟動後直接參考 preset 名稱傳入工具即可
just ext-inv-board-swing    # 啟動後用 preset="swing-trade"
just ext-inv-board-macro    # 啟動後用 preset="macro-focus"
just ext-inv-board-quick    # 啟動後用 preset="quick"
just ext-inv-board-pm       # 啟動後用 preset="pm-macro"
```

---

## Mode A — 自動模式

```
# 全員 + 自動 preset
board_begin brief="分析 AAPL，考慮是否做多"

# 指定 preset（在工具參數傳入）
board_begin brief="分析 AAPL" preset="swing-trade"
board_begin brief="分析宏觀風險" preset="macro-focus"
board_begin brief="快速看 BTC" preset="quick"
board_begin brief="判斷 Polymarket 事件賠率" preset="pm-macro"
board_begin brief="path/to/brief.md" preset="event-driven"
```

→ CEO 框架 → 所有 preset 委員並行分析 → CEO 整合 → 輸出 .md + .html 報告

---

## Mode B — 互動模式（精確控制誰發言）

```bash
# 1. 開始討論（CEO 框架 + 第一位委員發言）
board_discuss brief="分析 AAPL，考慮是否做多"
board_discuss brief="分析 AAPL" preset="swing-trade"

# 2. 讓下一位委員自動發言（按 preset 順序）
board_next

# 3. 你有觀點加入
board_next context="我認為 RSI 已超賣，短線反彈機率高，你怎麼看？"

# 4. 指定特定委員發言（跳過其他人）
board_next member="backtest"
board_next member="technical-analyst"
board_next member="risk-officer" context="請特別評估下行風險"
board_next member="macro-strategist"

# 5. 結束 → 生成報告
board_report
board_report user_final_take="我傾向做多，但只用 20% 倉位試水"
```

→ 輸出 .md + .html 報告（路徑加 `-discussion` 後綴）

---

## 只召喚 2 個特定委員（精確模式）

**場景：** 我只想問 `backtest` 和 `technical-analyst`，其他人跳過。

```bash
# Step 1 — 啟動
just ext-inv-board-discuss

# Step 2 — 開始討論，用最小 preset（CEO + technical-analyst + risk-officer）
board_discuss brief="SPY RSI 策略回測" preset="quick"

# Step 3 — 第一個委員自動發言（technical-analyst）

# Step 4 — 點名 backtest（不走 board_next 輪序，直接指定）
board_next member="backtest"

# Step 5 — 不叫 risk-officer，直接結束
board_report user_final_take="只看技術面和回測，其他略"
```

或者更極端的 2-人版本：

```bash
# 開始（用 full preset），然後只點名你要的人
board_discuss brief="AAPL 回測" preset="full"

board_next member="backtest"
board_next member="technical-analyst"

board_report  # 其他委員不發言
```

---

## 委員列表

| 委員 ID | 角色 | 工具 |
|---------|------|------|
| `ceo` | CEO（框架 + 整合） | bash |
| `macro-strategist` | 宏觀策略師 | wsp-v3 |
| `fundamental-analyst` | 基本面分析師 | sfa + wsp-v3 |
| `technical-analyst` | 技術分析師 | sta (MCP) |
| `reversal-strategist` | 反轉策略師 | sta + wsp-v3 |
| `risk-officer` | 風險官 | bash + sta |
| `market-intelligence` | 市場情報官 | wsp-v3 + summarize |
| `prediction-market-analyst` | 預測市場分析師 | wsp-v3 |
| `backtest` | 回測驗證員 | bash |

---

## Preset 對照表

| Preset | 成員 |
|--------|------|
| `full` | 全 8 人 |
| `macro-focus` | ceo, macro-strategist, fundamental-analyst, risk-officer, prediction-market-analyst, backtest |
| `swing-trade` | ceo, technical-analyst, risk-officer, backtest |
| `quick` | ceo, technical-analyst, risk-officer |
| `event-driven` | ceo, macro-strategist, prediction-market-analyst, risk-officer, backtest |
| `pm-macro` | ceo, macro-strategist, prediction-market-analyst, backtest |

---

## 報告輸出

- Mode A：`.pi/investment-adviser-board/memos/<slug>-<timestamp>.md` + `.html`
- Mode B：`.pi/investment-adviser-board/memos/<slug>-<timestamp>-discussion.md` + `.html`
