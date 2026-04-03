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

## Music Study Board (`extensions/boards/music-study.ts`)

| 指令 | Preset | 說明 |
|------|--------|------|
| `just ext-music-study` | `full` | 四位研究員全員（深度研究 + YouTube + 流派史 + 聆聽導師） |
| `just ext-music-study-jazz` | `jazz-deep` | 深度研究員 + 流派史學家（Jazz 分析） |
| `just ext-music-study-discovery` | `discovery` | YouTube 策展 + 聆聽導師（找新音樂） |

> 研究員使用真實工具（wsp-v3、summarize、bash）。執行時間較長，請耐心等候。

**指令：**

| 指令 | 說明 |
|------|------|
| `/study-preset` | 切換研究組合（互動選單） |
| `/study-status` | 顯示目前研究員 |
| `/study-history` | 列出最近報告 |

---

## Meta-Orchestrator 跨域戰略系統 (`extensions/boards/meta-orchestrator.ts`)

| 指令 | Preset | 說明 |
|------|--------|------|
| `just ext-meta` | `full` | 全域分析（投資 + Drip + AI工具） |
| `just ext-meta-strategic` | `strategic` | 投資 + Drip（商業策略類問題） |
| `just ext-meta-tech` | `tech-policy` | AI工具 + 投資（科技政策類問題） |
| `just ext-meta-creative` | `tech-creative` | Drip + AI工具（創意科技類問題） |

**執行流程：** Orchestrator 路由 → 地緣政治分析 → 各委員會 CEO 並行 → 跨域綜合報告

**指令：**

| 指令 | 說明 |
|------|------|
| `/orchestrate-preset [name]` | 切換委員會組合 |
| `/orchestrate-status` | 顯示目前委員會配置 |

### Intel Board — 群組 + 1-on-1 (`extensions/boards/intel-board.ts`)

> 三位情報專家的統一入口：群組並行分析 + `/select` 切換 1-on-1。含 Damage Control 規則。

| 指令 | 說明 |
|------|------|
| `just ext-intel` | 啟動 Intel Board（預設群組模式） |

**工具：**

| 工具 | 說明 |
|------|------|
| `intel_brief` | 提交問題 → 三位專家並行分析 → `.md` 備忘錄 |

**指令：**

| 指令 | 說明 |
|------|------|
| `/select [name]` | 切換 1-on-1（`geo` / `markets` / `military`）；空白 = 選單；`/select off` 回群組 |
| `/intel-preset [name]` | 切換專家組合（full / geo-markets / geo-military / markets-military） |
| `/intel-status` | 顯示當前模式與活躍專家 |

**Presets：**

| Preset | 成員 |
|--------|------|
| `full` | 地緣政治 + 全球市場 + 軍事 |
| `geo-markets` | 地緣政治 + 全球市場 |
| `geo-military` | 地緣政治 + 軍事 |
| `markets-military` | 全球市場 + 軍事 |

---

### Meta Shared Expert — 獨立一對一會話 (`extensions/boards/meta-expert-session.ts`)

> 直接與 Meta-Orchestrator 的共享專家 1-on-1 對話，支援知識庫更新。

| 指令 | 專家 | 說明 |
|------|------|------|
| `just ext-geo` | 地緣政治分析師 | 1-on-1：地緣政治風險、大國競爭、政策影響 |
| `just ext-markets` | 全球市場專家 | 1-on-1：亞太/美洲/歐洲/中東市場信號轉化 |
| `just ext-military` | 軍事戰略專家 | 1-on-1：衝突態勢、台海風險、國防科技擴散 |

**指令：**

| 指令 | 說明 |
|------|------|
| `/expert-status` | 顯示當前專家資訊和知識庫狀態 |
| `/expert-learn` | 提示專家將對話洞見寫入知識庫 |

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
| `/member-meeting [preset]` | 召開董事會，與其他成員一起分析（預設 full） |

---

## 足球博彩情報中心 (`extensions/boards/fb-board-member-session.ts`)

> 8 位專家 1-on-1 對話。每位成員有完整工具（bash/read/write），可執行 API 查詢、FC26 DB、Poisson 模型計算。
> 成員知識庫路徑：`.pi/football-betting-board/agents/<name>/<name>-knowledge.md`

### Mode A — 全自動委員會 (`football-betting-board.ts`)

| 指令 | Preset | 說明 |
|------|--------|------|
| `just ext-fb-board` | `full` | 全員自動模式（8 人並行） |
| `just ext-fb-board-quick` | `quick` | 快速版：Director + Stats Modeler + Risk Manager |
| `just ext-fb-board-pre-match` | `pre-match` | 賽前分析：Director + Data Scout + Form Analyst + Stats Modeler + Risk Manager |
| `just ext-fb-board-live` | `live` | 即時監控：Director + Odds Tracker + Market Intel + Value Hunter |

**工具：**

| 工具 | 說明 |
|------|------|
| `board_begin` | 提交 brief → AI 全自動運行 → 輸出 HTML 報告 |
| `board_discuss` | 開始互動討論模式，用戶作為「人類委員」坐入委員會 |

### Mode C — 一對一成員會話 (`fb-board-member-session.ts`)

| 指令 | 成員 | 職責 |
|------|------|------|
| `just ext-fb-member` | 互動選擇 | `/member-select` 彈出選單，選任意成員 |
| `just ext-fb-member-director` | **Director 總監** | 協調所有分析，給出最終投注建議 |
| `just ext-fb-member-data-scout` | **Data Scout 偵察員** | FC26 屬性 + SportAPI7 球員統計 |
| `just ext-fb-member-form-analyst` | **Form Analyst 狀態師** | 近6場、傷兵、停賽、主客場差異 |
| `just ext-fb-member-stats-modeler` | **Stats Modeler 模型師** | Poisson xG 勝率、EV 計算 |
| `just ext-fb-member-odds-tracker` | **Odds Tracker 賠率員** | The Odds API 多平台賠率比較 |
| `just ext-fb-member-market-intel` | **Market Intel 情報員** | Sharp money、reverse line movement |
| `just ext-fb-member-value-hunter` | **Value Hunter 獵手** | 正EV識別、套利機會、加密平台 |
| `just ext-fb-member-risk-manager` | **Risk Manager 風控** | Kelly criterion、倉位管理、止損 |

#### 成員會話指令

| 指令 | 說明 |
|------|------|
| `/member-select [name]` | 選擇或切換成員（可直接帶名稱） |
| `/member-status` | 顯示當前成員資訊和知識庫狀態 |
| `/member-equip <skill>` | 將 skill 用法寫入成員知識庫 |
| `/member-learn <url>` | 從 URL 學習並更新知識庫 |
| `/member-meeting [preset]` | 召開董事會，與其他成員一起分析（預設 full） |

**Presets（`/member-meeting <preset>`）：**

| Preset | 成員組合 | 用途 |
|--------|---------|------|
| `full` | 全8人 | 大場賽事深度分析 |
| `pre-match` | Director + Data Scout + Form Analyst + Stats Modeler + Risk Manager | 賽前快速報告 |
| `live` | Director + Odds Tracker + Market Intel + Value Hunter | 即時賠率監控 |
| `value-scan` | Director + Value Hunter + Odds Tracker + Risk Manager | 搜尋 value bet |
| `quick` | Director + Stats Modeler + Risk Manager | 快速決策 |

### FC26 快捷查詢（任何成員會話中可用）

```bash
FC26Q="python3 /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/football-data/fc26q.py"

$FC26Q player <name>              # 完整屬性（pace/shoot/pass/drib/def/phys + 子屬性）
$FC26Q team <club>                # 全隊陣容 + 平均 OVR
$FC26Q compare <club1> vs <club2> # 並排比較兩隊
$FC26Q top <league> [N]           # 聯賽最強排名（EPL/LaLiga/SerieA/Bundesliga/Ligue1）
$FC26Q search <name>              # 跨聯賽模糊搜尋
```

### API 快速參考

| API | Key | 用途 |
|-----|-----|------|
| The Odds API | `7cb32f9dd8d62dc575d80b11fad88c3b` | 多平台賠率（500次/月） |
| football-data.org | `ab57e456f0074b02b423a059c0c1bf42` | 賽果、積分榜 |
| SportAPI7 | `aaa356cce0msh0f0bc8f65f2c1cep1d908bjsnbfa00eae96b5` | 球員評分、球隊陣容 |

### Presets（`config.yaml`）

| Preset | 成員組合 | 用途 |
|--------|---------|------|
| `full` | 全8人 | 大場賽事深度分析 |
| `pre-match` | director + data-scout + form-analyst + stats-modeler + risk-manager | 賽前快速報告 |
| `live` | director + odds-tracker + market-intel + value-hunter | 即時賠率監控 |
| `value-scan` | director + value-hunter + odds-tracker + risk-manager | 搜尋 value bet |
| `quick` | director + stats-modeler + risk-manager | 快速決策 |

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
