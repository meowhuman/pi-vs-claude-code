# Pi Just 快捷指令總覽

所有可用的 `just` 指令，用於啟動 Pi 擴展。

擴展已依功能分類至 `extensions/` 子目錄：
`ui/` · `control/` · `agents/` · `finance/` · `boards/` · `tools/`

---

## 核心指令

| 指令 | 說明 |
|------|------|
| `just pi` | 預設 Pi（無擴展） |
| `just pi-dc` | Pi + 損害控制 + 極簡模式 |
| `just pi-multi-agent` | 代理鏈 + 工具計數器 + 損害控制 + 會話回放 |

---

## UI 擴展 (`extensions/ui/`)

| 指令 | 說明 |
|------|------|
| `just ext-pure-focus` | 完全移除頁腳和狀態列，純淨模式 |
| `just ext-minimal` | 顯示模型名稱 + 10 格上下文進度條 |
| `just ext-tool-counter` | 自訂頁腳：模型、分支、目錄、Token 用量、費用 |
| `just ext-tool-counter-widget` | 在編輯器下方顯示工具呼叫次數小部件 |
| `just ext-session-replay` | 可滾動的會話歷史時間軸覆蓋層 |
| `just ext-theme-cycler` | `Ctrl+X` 向前切換主題、`Ctrl+Q` 向後、`/theme` 選擇器 |
| `just ext-subagent-widget` | `/sub <任務>` 並即時串流子代理進度 |

---

## Control 擴展 (`extensions/control/`)

| 指令 | 說明 |
|------|------|
| `just ext-cross-agent` | 載入 `.claude/`、`.gemini/`、`.codex/` 目錄中的指令 |
| `just ext-purpose-gate` | 工作前先宣告意圖，持續顯示目的小部件 |
| `just ext-damage-control` | 安全審查 — 攔截破壞性操作 |
| `just ext-tilldone` | 任務導向紀律管理 — 先定義任務再開始工作 |

---

## Agents 擴展 (`extensions/agents/`)

| 指令 | 說明 |
|------|------|
| `just ext-agent-team` | 調度員協調器，含團隊選擇與網格儀表板 |
| `just ext-system-select` | `/system` 選擇代理人格作為系統提示 |
| `just ext-agent-chain` | 循序管道協調器 |
| `just ext-pi-pi` | 元代理 — 透過平行專家研究來建構 Pi 代理 |

---

## Finance 擴展 (`extensions/finance/`)

| 指令 | 說明 |
|------|------|
| `just ext-polymarket` | 預測市場交易代理 |
| `just ext-onchain` | 跨鏈資金流向與 DeFi 追蹤（DeFiLlama + DexScreener） |
| `just ext-onchain-chain` | 鏈上管道：偵察 → 分析 → RWA → 報告 |

---

## Drip Music 策略董事會 (`extensions/boards/drip-board.ts`)

| 指令 | 預設模式 | 說明 |
|------|----------|------|
| `just ext-drip-board` | 完整版 | 完整策略董事會（全體成員） |
| `just ext-drip-board-quick` | — | 快速版，2 人理智檢查 |
| `just ext-drip-board-marketing` | `marketing-campaign` | 行銷活動決策 |
| `just ext-drip-board-grants` | `grants-funding` | 資金申請與政府關係決策 |
| `just ext-drip-board-programming` | `programming` | 節目規劃與藝人決策 |

---

## 投資顧問委員會 (`extensions/boards/`)

### Mode A — 全自動委員會 (`investment-adviser-board.ts`)

> Mode A 成員均以 **無工具模式** 快速給出立場（不執行 bash/搜尋），速度最快。
> 需要成員實際執行研究工具，請改用 Mode C 一對一會話。

| 指令 | Preset | 說明 |
|------|--------|------|
| `just ext-inv-board` | `full` | 全員自動模式（7 人並行） |
| `just ext-inv-board-macro` | `macro-focus` | CEO + 宏觀策略師 + 基本面分析師 + 風險官 + PMA |
| `just ext-inv-board-swing` | `swing-trade` | CEO + 技術分析師 + 風險官 |
| `just ext-inv-board-quick` | `quick` | 快速版：CEO + 技術分析師 + 風險官 |
| `just ext-inv-board-discuss` | 討論 | Mode B — 互動討論（你坐進委員會） |

**自訂 Preset（`/board-preset` 選擇）：**

| Preset | 成員 |
|--------|------|
| `pm-macro` | CEO + Macro Strategist + Prediction Market Analyst |
| `event-driven` | CEO + Macro Strategist + PMA + Risk Officer |

### Mode C — 一對一成員會話 (`inv-board-member-session.ts`)

成員可透過聊天更新自己的個人知識庫（`.pi/investment-adviser-board/agents/<name>-knowledge.md`）。

| 指令 | 成員 | 職責 |
|------|------|------|
| `just ext-inv-member` | 互動選擇 | `/member-select` 彈出選單 |
| `just ext-inv-member-ceo` | CEO | 委員會主席 — 整合分析、最終建議 |
| `just ext-inv-member-macro` | Macro Strategist | 宏觀經濟 — 全球週期、央行、地緣政治 |
| `just ext-inv-member-fundamental` | Fundamental Analyst | 基本面 — 財務報表、估值、競爭護城河 |
| `just ext-inv-member-technical` | Technical Analyst | 技術分析 — 圖形形態、動量、進出場時機 |
| `just ext-inv-member-risk` | Risk Officer | 風險管理 — 部位規模、止損、尾部風險 |
| `just ext-inv-member-intel` | Market Intelligence | 情報 — 資金流向、新聞催化劑、情緒 |

> `ext-inv-member-reversal` 已移除（成員不存在）。預測市場請用 `ext-inv-member` 選 `prediction-market-analyst`。

#### 成員會話指令

| 指令 | 說明 |
|------|------|
| `/member-select [name]` | 選擇或切換成員（可直接帶名稱） |
| `/member-status` | 顯示當前成員資訊和知識庫狀態 |
| `/member-equip <skill>` | 將 skill 用法寫入成員知識庫（下次會話生效） |
| `/member-learn <url>` | 從 URL（YouTube / X / 文章）學習並更新知識庫 |

---

## AI 工具 (`extensions/tools/`)

| 指令 | 說明 |
|------|------|
| `just ext-pi-extension-builder` | 自動生成新的 Pi 擴展 |
| `just ext-youtube-video-processor` | 搜尋 YouTube、檢查字幕、擷取/轉錄逐字稿、摘要 SRT |

---

## Claude

| 指令 | 說明 |
|------|------|
| `just cldsp` | Claude 跳過權限確認模式（無 MCP） |
| `just cldsp-figma` | Claude + 臨時 Figma MCP（退出後自動移除） |

---

## 工具指令

| 指令 | 說明 |
|------|------|
| `just open <ext> [ext2...]` | 在新的終端機視窗開啟擴展（支援 `ui/minimal` 或裸名 `minimal`） |
