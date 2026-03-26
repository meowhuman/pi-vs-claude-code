---
description: Custom /just command to help organize and use pi extensions via just
---

# Pi Extensions & Just Commands Guide

這個工作流程（Workflow）可協助你了解 `pi-vs-claude-code/extensions` 目錄下提供的強大擴充功能，並教你如何透過 `just` 任務執行器來管理及啟動你的客製化 `pi` 環境。

## 🚀 如何使用 Just 啟動 Pi

在這個專案中，`just` 已經幫你綁定好了所有的基本指令，不僅能自動載入 `.env` 環境變數，還能協助你快速掛載單一或多個擴充功能：

- `just pi`: 啟動純淨版 Pi，不加任何擴充功能。
- `just ext-<extension_name>`: 啟動單一指定的擴充功能（參考下方的列表名稱）。
- `just open <ext1> <ext2>`: **最推薦的用法！** 開啟新終端機視窗，並結合你所需的多個擴充功能（輸入時不需要加上 `.ts`）。

## 🧩 可用的擴充功能清單 (位在 `extensions/`)

### 1. 介面與專注 (Focus & UI)
- **`pure-focus`** (`just ext-pure-focus`): 純淨專注模式，隱藏底部的狀態列與所有干擾，適合沉浸開發。
- **`minimal`** (`just ext-minimal`): 精簡模式，底部僅顯示模型名稱與 10 格上下文使用量進度。
- **`theme-cycler`** (`just ext-theme-cycler`): 佈景主題切換器，可透過 `/theme` 指令或快捷鍵（Ctrl+X/Ctrl+Q）切換自訂主題。
- **`session-replay`** (`just ext-session-replay`): 歷史回放，顯示目前對話的捲動時間軸，方便隨時追溯上下文。

### 2. 數據與追蹤 (Metrics & Tracking)
- **`tool-counter`** (`just ext-tool-counter`): 豐富的雙行狀態列，顯示模型明細、花費成本、目前 Git 分支與指令統計等。
- **`tool-counter-widget`** (`just ext-tool-counter-widget`): 在對話區下方展開一個面板，即時統計與追蹤各個工具的呼叫次數，適合關注花費的使用者。

### 3. 流程與任務管理 (Workflow & Task Management)
- **`tilldone`** (`just ext-tilldone`): 任務驅動模式，啟動前需定義待辦清單，並在畫面底部即時追蹤進度，適合防過度發散。
- **`purpose-gate`** (`just ext-purpose-gate`): 在開啟終端時強制要求宣告「對話目標」，提供目標提示小工具，時刻提醒 AI 保持專注。

### 4. 多 Agent 編排與協作 (Multi-Agent Orchestration)
- **`subagent-widget`** (`just ext-subagent-widget`): 輸入 `/sub <任務>` 可產出背景「子 Agent」來解決雜事，並顯示即時串流的小工具面板。
- **`agent-team`** (`just ext-agent-team`): 團隊主管模式，這個 Agent 會把任務分配給專門的領域專家（如：前端、後端），並帶有一個酷炫的協作網格儀表板。
- **`agent-chain`** (`just ext-agent-chain`): 管線編排器（Sequential Pipeline），讓任務照著特定順序流轉（如：規劃 -> 實作 -> 審查），自動帶入上個階段的結果。
- **`system-select`** (`just ext-system-select`): 新增了 `/system` 指令，讓你可以在對話途中熱切換 Agent 的角色（Persona / System Prompt）。
- **`pi-pi`** (`just ext-pi-pi`): 建置 Pi 專用的 Meta-Agent，透過多個平行專家來幫你研究與撰寫高階 Pi 擴充套件。

### 5. 安全管控 (Safety & Security)
- **`damage-control`** (`just ext-damage-control`): 即時安全審查，攔截並鎖定危險的環境變數讀取與 bash 指令（如 `rm -rf` 等），保護你的本機電腦不受失控行為破壞。

### 6. 跨 Agent 整合 (Interoperability)
- **`cross-agent`** (`just ext-cross-agent`): 掃描電腦裡其他 Agent 工具的目錄（如 `.claude/`, `.gemini/`）並將它們定義的 Custom Commands 等指令註冊到 Pi 供跨域使用。

---

## 💡 實用組合範例 (Quick Combos)

使用 `just open` 可以自由組合你的專屬超級開發環境：

- **🛡️ 安全追蹤組合包 (安全派):** 
  ```bash
  just open damage-control tilldone minimal
  ```
- **🤖 大主管監工模式 (指揮派):** 
  ```bash
  just open agent-team tool-counter-widget damage-control
  ```
- **⚡ 背景非同步發包 (分工派):** 
  ```bash
  just open subagent-widget damage-control pure-focus
  ```

當你呼叫 `/just` 此 Workflow 時，AI 可以協助你評估目前工作情境，並推薦給你合適的 `just open` 指令組合，或幫你進一步將喜歡的組合固化為 Custom Recipe（記錄至 Makefile 或 justfile）。
