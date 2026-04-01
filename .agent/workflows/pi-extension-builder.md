---
description: 建立客製化的 Pi 程式碼 Agent 擴充功能（工具、UI 小工具、事件掛鉤或完整多 Agent 管線）。用法：/pi-extension-builder [extension-name] [description]
---

# Pi 擴充功能建置器 (Pi Extension Builder)

引導你設計並生成一個 Pi 擴充功能。先研習現成的程式碼，之後訪談使用者並生成準備就緒的 `.ts` 檔案，以及所有必要的連結 (themeMap, justfile, 或 agent YAML)。

## 變數定義

```
EXTENSION_NAME: $1  (kebab-case, 例如 "focus-timer")
DESCRIPTION:    $2  (一句話, 例如 "具有底部倒數計時的番茄計時器")
EXTENSIONS_DIR: /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions
COMMANDS_DIR:   /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/commands
AGENTS_DIR:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi/agents
JUSTFILE:       /Users/terivercheung/Documents/AI/pi-vs-claude-code/justfile
THEMEMAP:       /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions/themeMap.ts
```

---

## 第 1 步 — 載入程式碼庫上下文

在生成前，先讀取以下檔案以熟悉實踐方式：

```
讀取: EXTENSIONS_DIR/themeMap.ts          # 主題指派 + applyExtensionDefaults
讀取: EXTENSIONS_DIR/tool-counter.ts      # 底部狀態列模式, 會話遍歷
讀取: EXTENSIONS_DIR/purpose-gate.ts      # 輸入攔截, 小工具, before_agent_start
讀取: EXTENSIONS_DIR/tilldone.ts          # registerTool, 客製化 TUI 元件, 狀態重建
讀取: EXTENSIONS_DIR/agent-chain.ts       # 多 Agent 生成, YAML 解析, 子行程, 底部小工具
讀取: JUSTFILE                             # 現有的進入點
讀取: AGENTS_DIR/agent-chain.yaml         # YAML 鏈格式
Bash: ls EXTENSIONS_DIR/*.ts              # 查看現有所有擴充功能
```

---

## 第 2 步 — 收集需求

如果缺少參數，請詢問：

1. **名稱 (Name)** — 如何稱呼它（kebab-case）
2. **目的 (Purpose)** — 一句話：它解決什麼問題？
3. **類型 (Type)** — 哪種模式最合適？ (參考下表)
4. **所需工具 (Tools)** — 是否需要對 Agent 暴露工具？功能為何？
5. **UI 介面 (UI surfaces)** — 底部狀態列？小工具？狀態覆蓋？指令？快捷鍵？
6. **狀態 (State)** — 在分支切換時是否需要持久化狀態？
7. **多 Agent (Multi-agent)** — 如果是：有多少個 Agent？什麼角色？什麼模型？

### 擴充功能類型清單

```
A) 工具擴充 (Tool extension) — 註冊一個或多個 Agent 可點用的工具 (如 polymarket.ts)
B) UI 擴充 (UI extension) — 底部狀態列 / 小工具 / 狀態覆蓋 (如 tool-counter.ts)
C) 門禁擴充 (Gate extension) — 攔截或轉換 Agent 的輸入/輸出 (如 purpose-gate.ts)
D) 流程擴充 (Discipline ext.) — 強制執行工作流 (如 tilldone.ts)
E) 多 Agent 鏈 (Multi-agent chain) — 循序性管線 (如 agent-chain.ts)
F) 多 Agent 團隊 (Multi-agent team) — 具有調度員的平行團隊 (如 agent-team.ts)
G) 混合型 (Hybrid) — 結合上述特性
```

---

## 第 3 步 — 架構規劃

根據類型，大綱其結構：

- 要掛鉤哪些事件 (`session_start`, `before_agent_start`, `agent_end`, `input`, `tool_call`, `tool_execution_end`)
- 要註冊哪些工具 (名稱, 參數, 執行邏輯)
- 要建立哪些 UI 介面
- 需要的狀態變數
- 對於多 Agent：需要的 Agent .md 檔案 + 鏈 YAML 或團隊配置

展示計劃給使用者並在寫入程式碼前獲得確認。

---

## 第 4 步 — 生成擴充功能

### 4a. 寫入 `extensions/<name>.ts`

使用此骨架 — 僅填寫需要的部分，省略空白區塊：

```typescript
/**
 * <ExtensionName> — <一句話描述>
 *
 * <詳細描述>
 *
 * 指令:  /<cmd>  — 描述
 * 快捷鍵: Ctrl+X  — 描述
 *
 * 用法: pi -e extensions/<name>.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";               // 用於列舉參數
import { Type } from "@sinclair/typebox";                        // 用於工具參數
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui"; // 用於 TUI
import { spawn } from "child_process";                           // 用於子行程
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";

// ── 狀態 (State) ──────────────────────────────────────────────────────────────

// (模組層級狀態 — 在分支切換後仍會保留，可視需求從會話歷史中重建)

// ── 擴充功能主體 (Extension) ─────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── 啟動 (Boot) ──────────────────────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    // ctx.ui.setStatus / setFooter / setWidget / setTitle
  });

  // ── 狀態重建 (分支切換) ─────────────────────────────────
  // pi.on("session_switch or session_fork", ...)

  // ── 工具註冊 (Tools) ─────────────────────────────────────────────────────
  pi.registerTool({
    name: "tool_name",
    label: "Human Label",
    description: "Agent 應在何時呼叫此工具",
    parameters: Type.Object({
      param: Type.String({ description: "..." }),
    }),
    async execute(toolCallId, params: any, signal, onUpdate, ctx) {
      // ... 執行邏輯 ...
      return {
        content: [{ type: "text" as const, text: "結果" }],
        details: { /* 序列化至會話，用於狀態重建 */ },
      };
    },
    renderCall(args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("tool_name ")) + theme.fg("dim", String((args as any).param ?? "")), 0, 0);
    },
    renderResult(result, options, theme) {
      const text = result.content?.[0]?.text ?? "";
      return new Text(theme.fg("muted", text), 0, 0);
    },
  });

  // ── 系統提示詞 (System Prompt) ─────────────────────────────────────────────
  pi.on("before_agent_start", async (_event, _ctx) => {
    return {
      appendSystemPrompt: `\n\n## <Extension Context>\n...`,
    };
  });

  // ── 指令 (Commands) ────────────────────────────────────────────────────────
  pi.registerCommand("cmd-name", {
    description: "/cmd-name 的功能",
    handler: async (args, ctx) => {
      // ctx.ui.select / input / confirm / notify / custom
    },
  });
}
```

---

## 第 5 步 — 連結與配置

### 5a. 在 `themeMap.ts` 中新增主題

在 `THEME_MAP` 物件中加入：
`"<extension-name>": "cyberpunk"` (或其他主題如 `midnight-ocean`, `dracula` 等)

### 5b. 在 `justfile` 中新增進入點

```makefile
# <名稱>: <描述>
ext-<name>:
    pi -e extensions/<name>.ts
```

---

## 第 6 步 — 驗證

// turbo
寫入後執行：

```bash
# 檢查註冊的工具與指令數量
node --input-type=module --eval "
import { readFileSync } from 'fs';
const s = readFileSync('extensions/<name>.ts', 'utf8');
console.log('registerTool:', (s.match(/registerTool\(/g)||[]).length);
console.log('registerCommand:', (s.match(/registerCommand\(/g)||[]).length);
console.log('pi.on:', (s.match(/pi\.on\(/g)||[]).length);
"
```

完成前與使用者確認。
