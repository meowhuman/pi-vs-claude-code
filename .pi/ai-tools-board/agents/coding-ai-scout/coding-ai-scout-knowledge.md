# Coding AI Scout — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 coding-ai-scout-sources.md。

## 工具能力比較

### Overstory — Multi-Agent Orchestration（2026-04-01 研究）[src:004][src:005][src:006]

**概述**：Overstory 是一個多 agent 編排框架，把單一 coding session 轉變為 multi-agent 團隊。透過 git worktree + tmux 隔離每個 worker agent，用自建 SQLite mail system 協調通訊，最後以 tiered conflict resolution 合併結果。

**核心能力**：
- **11 個 runtime adapter**（可插拔）：Claude Code（stable）、Pi（experimental）、Copilot、Codex、Gemini CLI、Cursor、Aider、Goose、Amp、Sapling、OpenCode
- **SQLite mail system**：WAL mode，~1-5ms 查詢，8 種 typed protocol messages + broadcast（`@all`, `@builders`）
- **4-tier watchdog**：Tier 0 機械 daemon → Tier 1 AI triage → Tier 2 monitor agent → Tier 3（未實作？）
- **4-tier conflict resolution**：FIFO merge queue，SQLite-backed
- **完整 observability**：37 個 CLI 子指令，含 TUI dashboard、costs 分析、trace/replay/logs
- **os-eco 生態系**：Mulch（API wrapper）、Seeds（task tracker）、Canopy（prompt rendering）、Overstory（orchestrator）

**Agent 層級架構**：
```
Orchestrator（multi-repo）
  → Coordinator（per-project，persistent）
    → Supervisor / Lead（team lead）
      → Workers: Scout（readonly）、Builder（read-write）、Reviewer（readonly）、Merger（read-write）
```

**版本進展**（2026-02-12 ~ 2026-03-23）：
- v0.9.3（2026-03-23）：tmux socket isolation
- v0.9.2（2026-03-23）：+ Aider、Goose、Amp runtime adapters
- v0.9.1（2026-03-13）：discover command 改為 coordinator-driven
- v0.8.7（2026-03-10）：+ Cursor CLI adapter
- v0.8.6（2026-03-06）：coordinator completion protocol
- 創建僅 7 週，已發佈多個版本，1250+ commits（主要來自作者 Jaymin West）

**風險分析**（來自 STEELMAN.md）：
1. **Error rate 複合效應**：平行 agent 的錯誤率相乘而非相加
2. **成本放大**：20-agent swarm 6hr 消耗 8M tokens（~$60），單 agent 8hr 只需 1.2M（~$9）
3. **推理碎片化**：缺少全局 coherence，命名不一致、重複工具、架構假設衝突
4. **Merge conflict 地獄**：語義不相容在 merge 時才浮現

**對 Pi Agent 的意義**：
- Overstory 已支援 Pi 作為 runtime adapter（`src/runtimes/pi.ts`），透過 `.pi/extensions/` guard extension 強制執行工具權限
- 這代表 Pi 被視為一等公民 runtime，與 Claude Code 並列
- Pi 的 in-process extension 能力可能比 Claude Code 的 hooks 更適合 agent orchestration

**作者**：Jaymin West（@jayminwest），同時維護 os-eco 生態系、Sapling（headless coding agent）、Agentic Engineering Book

**監控重點**：
- Pi adapter 從 Experimental → Stable 的進展
- 成本/效率 benchmark 數據是否改善
- 社群採用率（目前 1.15K stars，203 forks）
- 是否出現企業級用戶案例

## Agentic 趨勢觀察

### OpenClaw — 個人 AI 助手平台（2026-04-01 研究）[src:007][src:008]

**概述**：OpenClaw 是一個開源個人 AI 助手，MIT 授權，你跑在自己的設備上，透過你已有的通訊管道（WhatsApp、Telegram、Slack、Discord、Signal、iMessage、Teams、LINE、WeChat 等 20+ channels）與你互動。Gateway 只是控制平面，產品是助手本身。

**規模**（截至 2026-04-01）：
- **⭐ 343K stars / 🍴 68K forks** — GitHub 上最大的 AI 助手專案之一
- TypeScript，MIT，369MB，16,880 open issues
- 作者 Peter Steinberger（@steipete）：14,725 commits，主要開發者
- 贊助商：OpenAI、NVIDIA、Vercel、Blacksmith、Convex
- 創建於 2025-11-24，不到 5 個月達到 343K stars

**最新版本 v2026.3.31（2026-03-31）**：
- 🇨🇳 內建 QQ Bot — 私聊、群聊、公會 + media
- 📹 LINE 支援傳送圖片、影片、音訊
- **Breaking**：移除 `nodes.run` shell wrapper，統一走 `exec host=node`
- **Breaking**：Plugin SDK 淘汰舊版 provider compat subpaths
- **安全**：Skills/Plugins install 對 `critical` dangerous-code 積極 fail closed
- **Gateway/auth**：`trusted-proxy` 拒絕 mixed shared-token configs
- **新任務系統**：更可靠的 subagents/crons 等（Peter 在 X 上重點提及）

**近期版本軌跡**：
- v2026.3.28（03-29）：移除 Qwen portal OAuth、xAI provider 轉 Responses API + `x_search`、MiniMax image generation（`image-01`）、async `requireApproval` hooks for plugins
- v2026.3.24（03-25）：Gateway OpenAI 相容性（`/v1/models`, `/v1/embeddings`）、`/tools` 即時顯示 agent 可用工具

**Peter Steinberger（@steipete）近期 X/Twitter 動態（2026-03-31 ~ 04-01）** [src:009]：
1. **CC 洩漏事件**：諷刺 GitHub 的 takedown request 可能誤砍 Anthropic 自己的 public repo fork（「are they vibing the takedown requests too?」）— 144 likes
2. **OpenClaw v2026.3.31 發佈**：新 beta 版上線，強調 reliability + security 改進 + 新 task system — 467 likes
3. **Microsoft 整合**：轉推 Omar Shahine 加入 Microsoft 將 OpenClaw + personal agents 帶入 M365（已有 Teams plugin），評論「creating new jobs right here 🦞」— 735 likes（原推）
4. **安全重視**：回覆「a lot of work is going into each release to making it more secure and stable」
5. **擴展性考量**：承認「too much to do」，呼籲更多 maintainers 加入
6. **建議用 Codex**：建議用戶在 codebase 上用 Codex 本地跑，而非依賴 OpenClaw 內建

**對 Pi Agent 的意義**：
- OpenClaw 定位是「個人 AI 助手」而非 coding agent，與 Pi 直接競爭關係較低
- 但 OpenClaw 的通訊 channel 整合（20+ messaging platforms）和 plugin/skill 系統是值得觀察的架構
- Microsoft + OpenClaw 整合（Omar Shahine 加入 M365）顯示企業端對 personal agent 的強烈需求

**監控重點**：
- Star 增長率（343K 且仍在快速增長，已超越大多數 AI coding tools）
- Microsoft M365 整合進展
- 安全事件（skills/plugins install fail-closed 機制是否有效）
- Peter 對 CC 洩漏事件進一步評論

### Claude Code 原始碼洩漏事件（2026-03-31）[src:001][src:002][src:003]

**事件概述**：2026-03-31 凌晨（KST），Claude Code 完整原始碼被暴露到網路上。`instructkr/claw-code` 在 2 小時內突破 50K stars，創 GitHub 歷史紀錄。截至 2026-04-01：64K+ stars, 65K+ forks。

**主要社群反應**：
- 大量 mirror repo 湧現（GitHub 搜尋 "claude code leaked" 約 221 結果）
- Claw Code 作者 Sigrid Jin 為規避法律風險，移除原始碼改為 clean-room Python/Rust 重寫
- `NanmiCoder/claude-code-haha` 聲稱為 locally runnable version（TypeScript）

**架構洩漏影響**：
- Claude Code 的 tool wiring、agent workflow、harness 設計模式被完整暴露
- Claw Code Rust port 正在快速開發（`dev/rust` branch）：已有 API client、SSE streaming、sandbox isolation、git integration、init command
- 使用 oh-my-codex (OmX) 搭配 OpenAI Codex 進行自動化 clean-room 重寫

**關鍵人物**：Sigrid Jin（@instructkr）— 韓國開發者，被 WSJ 2026-03-21 報導，去年用了 250 億 Claude Code tokens

**監控重點**：
- Anthropic 是否發出 DMCA 或法律行動
- Claw Code Rust port 何時合併到 main
- 是否影響 Pi Agent 的競爭定位（CC 架構透明後，其他工具更容易複製類似模式）
- Mirror repo 存活率

## 社群反應記錄

（尚未記錄）

## 分析過的工具

| 日期 | 工具 | 版本 | 評分 | 備註 |
|------|------|------|------|------|
