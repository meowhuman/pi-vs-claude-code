# Coding AI Scout — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 coding-ai-scout-sources.md。

---

## 📰 2026-04-02（第 2 次全委員會議）：48hr 增量掃描

### 🔴 信號一（升級）：OpenAI $122B 融資 + Sora 關閉 + Spud 預告 — 「算力戰爭」全面升級

**OpenAI 完成史上最大私募融資輪 $122B**，估值達 $852B（5 個月前為 $500B）[src:024]。投資者陣容：Amazon $50B、Nvidia $30B、SoftBank $30B，加上 Microsoft、a16z、TPG、D.E. Shaw、MGX、T. Rowe Price。OpenAI 月收入約 $2B，企業佔 40%，將於 2026 年底前 IPO。

**關鍵連鎖效應**：
1. **Sora 關閉 = 算力重分配信號**：OpenAI 被曝給全公司放假一周重新分配 GPU 算力 [src:035]。Sora 雖有百萬用戶但無法盈利，在算力稀缺下被犧牲。Greg Brockman 同期預告 **Spud（GPT 5.5）**：新 pre-train base，號稱「兩年研究成果匯聚」，具備「big model smell」（模型顯著更聰明的質變體驗）[src:025]。
2. **Google 立刻補位**：趁 Sora 退出，Google 發佈 **Veo 3.1 Lite**，API 成本不到 Veo 3.1 Fast 的一半 [src:029]。業界解讀為「趁你病要你命」的戰略性定價。
3. **Oracle AI 裁員**：Oracle 同日裁員 **30,000 人**（18% 全球員工），Q1 收入 $17.2B（+22% YoY），但將資源全面轉向 AI 基礎設施 [src:028]。

**解讀**：這不僅是融資新聞，而是一個**算力稀缺時代來臨的明確信號**。OpenAI 寧可關掉百萬用戶的 Sora，也要把 GPU 騰給 Spud。$122B 融資的錢大部分會流向 GPU 採購（data center + chip）。對 coding agent 的影響：**算力成本可能進一步下降（規模效應），但 API 限速可能更嚴格**。

### 🔴 信號二（新）：Coding Agent 生態爆發性分化 — 四條路線清晰可見

過去 48hr 確認了 coding agent 市場正在沿四條路線分化：

**路線 A：全能 CLI（Claude Code / Codex / Gemini CLI）**
- Claude Code v2.1.89/90：洩漏修復 + 安全硬化 + 性能修復（SSE O(n²)→O(n)、autocompact thrash）[src:013][src:014]
- Codex v0.119.0-alpha.2：Rust port 繼續、inter-agent communication via spawn v2 [src:016]
- Gemini CLI v0.36.0 + v0.37.0-preview：**三平台完整 sandbox**（業界首次）、subagent 工具隔離、Plan mode stable、A2A 協議、unified context management [src:017][src:018]
- Codex CLI 達 **71,834 stars**（GitHub API 驗證 2026-04-02）
- Gemini CLI 達 **99,908 stars**（逼近 100K）

**路線 B：多 Agent 編排（Overstory）**
- Overstory 穩定 1,162 stars，Pi adapter 仍為 experimental [src:004]

**路線 C：跨平台移動化（Litter）**
- **Litter beta**：將 OpenAI Codex 原生搬到 iOS + Android，使用 Rust UniFFI 橋接（非 WebView），支援 Bonjour 局域網發現和 Tailscale 遠端連接。5 週 900 stars [src:031][src:032]
- **解讀**：Coding agent 開始走向「隨時隨地」使用場景，與 Cursor 的桌面化路線互補。

**路線 D：洩漏驅動的開源替代（Claw Code）**
- Claw Code 達 **123,765 stars**（GitHub API 驗證 2026-04-02，48hr 內從 64K 翻倍），clean-room Rust 重寫進行中
- NanmiCoder/claude-code-haha 維持 3,072 stars，未被 DMCA 下架 [src:002]
- Grok 分析指出洩漏使 Anthropic 的「dev tools moat」縮小 [src:036]

### 🔴 信號五（新增）：Anthropic 錯誤 DMCA 攻擊開發者 — 信任危機升級 [src:043][src:044][src:045]

**事件**：Anthropic DMCA takedown 了 **Theo（@theo，t3.gg）** 的 Claude Code public plugins repo fork — 該 repo **不包含任何洩漏的 Claude Code 原始碼**，僅包含一個數週前提交的 skill 編輯 PR。社群確認這不是孤立事件，多位用戶的合法 fork 也被波及 [src:045]。

**關鍵引述**：
- Theo：「Absolutely pathetic」[src:043]
- Emad Ghorbaninia：「Anthropic's DMCA wave is catching repos with zero leaked source code. Automatic takedowns at this scale are collateral damage machines.」[src:044]
- 日文開發者 taisei__desu：「開源的信任被他們自己破壞了。我的 CLAUDE.md 和 Skills 都在 GitHub 上管理，突然被消掉的風險必須考慮。」[src:043]

**解讀**：洩漏事件已從「安全事件」正式升級為「生態信任危機」。Anthropic 的 DMCA 策略是自動化批量處理，**誤殺合法 fork 暴露了反應過度**。這直接威脅到所有依賴 Claude Code Skills + GitHub 工作流的開發者——包括我們。與信號四（開源信任危機）形成共振。

### 🔴 信號六（新增）：Cursor Automations — Coding Agent 從互動式走向事件驅動 [src:046]

**Cursor 正式推出 Automations**：event-triggered coding agents 在雲端運行，支援觸發器包括：
- Code commits
- Merged PRs
- Slack messages
- PagerDuty incidents
- Timers（定時執行）

功能：自動 review PR、標記漏洞、提出修復建議。據稱已運行數百個 automation。

**解讀**：這是 coding agent 範式的關鍵轉變——**從「人驅動 agent」到「事件驅動 agent」**。過去所有 agent（Claude Code、Codex、Gemini CLI）都需要人類啟動對話，Cursor Automations 則是讓 agent 成為 CI/CD pipeline 的一部分。這與 Overstory 的 multi-agent 編排理念互補：Overstory 管人類指派的任務，Cursor Automations 管自動化工作流。

**對 Pi 的影響**：Pi 的 extension 系統天然支援事件驅動模式（isToolCallEventType），可以考慮類似的 automation 功能。

### 🟡 信號三（新）：Computer-Use 模型突圍 — Holo3 超越 GPT-5.4 和 Opus 4.6

**H Company**（巴黎 AI Lab）發佈 **Holo3**：78.9% OSWorld-Verified，超越 GPT-5.4 和 Claude Opus 4.6，成本僅 1/10 [src:026]。

- Holo3-122B（API）：$0.40/M input、$3.00/M output
- **Holo3-35B-A3B（Apache 2.0 開源）**：MoE 架構，僅 3B active params，$0.25/M input、$1.80/M output
- 已上線 Hugging Face
- ** caveat**：社群指出 OSWorld benchmark 可能已飽和（「basic shit」），實際 real-world 任務能力待驗證 [src:047]

**解讀**：Computer-use（GUI 操作）能力正從閉源前沿模型向開源擴散。Holo3 的開源 35B 模型可能被整合進 Overstory 等多 agent 編排框架，大幅降低 autonomous agent 的成本。

### 🟡 信號四：開源生態的「信任危機」加速

- **Pliny the Liberator**（知名 AI jailbreak 工具作者）將所有專案（L1B3RT4S 等）轉為 private/paywalled，原因是被企業 fork 卻無回饋 [src:030]
- **LiteLLM** 切斷與 Delve 的關係，理由是隱私和運營問題 [src:033]
- **OpenClaw v2026.4.1** 持續擴展但用戶抱怨更新頻率太高導致不穩定（「breaks so often」）[src:034]
- **OpenClaw** 達 **344,715 stars**（GitHub API 驗證 2026-04-02）

**解讀**：AI 開源工具的「使用者即免費 QA」模式開始產生反效果。Pliny 的轉向最具象徵意義 — 當開源作者被企業白嫖到無法忍受時，生態會加速閉源化。

### 🔵 雜訊

- **Meta Hyper Agents**：開源自進化 AI agent [src:027]，但缺乏技術細節，暫列觀察
- **Gemini Flash 3.1 Lite**：已在 Gemini CLI v0.37.0-preview 中以 experiment flag 出現，但未正式發佈
- **Google 多模態大更新**：Gemini real-time audio、Lyria 3 音樂、Veo 3.1 Lite 視頻 [src:029] — 對 coding agent 影響有限
- **vishalojha_me Claude Code 架構分析**（12-part thread）：公開了 scratchpad（專屬思考空間）和 memdir（flat file 記憶系統）等架構細節，來自洩漏的 source map [src:048]

---

## 📊 工具最新數據快照（2026-04-02 GitHub API 驗證）

| 工具 | Stars | 48hr 變化 | 狀態 |
|------|-------|----------|------|
| OpenClaw | 344,715 | +~1,600 | v2026.4.1 |
| Claw Code | 123,765 | +~60K（翻倍） | Rust 重寫中 |
| Claude Code | 101,526 | — | v2.1.90 |
| Gemini CLI | 99,908 | +~3,000（逼近 100K） | v0.36.0 stable |
| OpenAI Codex CLI | 71,834 | +~2,300 | Rust v0.119.0-alpha |
| Cursor | 32,550 | — | Automations 上線 |
| NanmiCoder/claude-code-haha | 3,072 | 微增 | 未被 DMCA |
| Overstory | ~1,162 | 穩定 | Pi experimental |

---

## 工具能力比較

### Overstory — Multi-Agent Orchestration（2026-04-01 研究）[src:004][src:005][src:006]

**概述**：Overstory 是一個多 agent 編排框架，把單一 coding session 轉變為 multi-agent 團隊。透過 git worktree + tmux 隔離每個 worker agent，用自建 SQLite mail system 協調通訊，最後以 tiered conflict resolution 合併結果。

**核心能力**：
- **11 個 runtime adapter**（可插拔）：Claude Code（stable）、Pi（experimental）、Copilot、Codex、Gemini CLI、Cursor、Aider、Goose、Amp、Sapling、OpenCode
- **SQLite mail system**：WAL mode，~1-5ms 查詢，8 種 typed protocol messages + broadcast
- **4-tier watchdog**：Tier 0 機械 daemon → Tier 1 AI triage → Tier 2 monitor agent → Tier 3（未實作？）
- **完整 observability**：37 個 CLI 子指令，含 TUI dashboard、costs 分析

**Agent 層級架構**：
```
Orchestrator（multi-repo）
  → Coordinator（per-project，persistent）
    → Supervisor / Lead（team lead）
      → Workers: Scout（readonly）、Builder（read-write）、Reviewer（readonly）、Merger（read-write）
```

**風險分析**（來自 STEELMAN.md）：
1. Error rate 複合效應：平行 agent 的錯誤率相乘而非相加
2. 成本放大：20-agent swarm 6hr 消耗 8M tokens（~$60），單 agent 8hr 只需 1.2M（~$9）
3. 推理碎片化：缺少全局 coherence
4. Merge conflict 地獄

**對 Pi Agent 的意義**：Pi 被視為一等公民 runtime，in-process extension 能力可能比 Claude Code hooks 更適合 orchestration

### Cursor Automations — 事件驅動 Coding Agent（2026-04-02 新增）[src:046]

**概述**：Cursor Automations 將 coding agent 從「人類啟動的 CLI session」轉變為「CI/CD pipeline 中的自動化組件」。Agent 可被 git events、Slack messages、PagerDuty incidents、timers 觸發，在雲端自主運行。

**與其他工具的差異化**：
- Claude Code / Codex / Gemini CLI：互動式、人類在迴圈中
- Overstory：人類指派任務給 agent 團隊
- Cursor Automations：**零人類介入、事件驅動**

**潛在風險**：
- 成本不可控（autonomous agent 可能消耗大量 tokens）
- 品質保證（無人審核的自動修復可能引入 bug）
- 安全性（agent 對 repo 的寫入權限需嚴格限制）

## Agentic 趨勢觀察

### OpenClaw — 個人 AI 助手平台 [src:007][src:008][src:019][src:034]

**規模**：344,715 stars / 68K forks，MIT，創建 2025-11-24

**v2026.4.1 新增**：`/tasks` task board、SearXNG 搜尋、Bedrock Guardrails、GLM-5.1、Feishu Drive、Voice Wake

**社群反應兩極**：正面評價認為 Bedrock Guardrails 和 cron per-job allowlists 是「game changer」；負面評價抱怨更新頻率過高導致不穩定，「no QA/QC」[src:034]

### Claude Code 原始碼洩漏事件（2026-03-31 → 2026-04-02）[src:001][src:002][src:003][src:010][src:011][src:012][src:036][src:043][src:044][src:045]

**72hr 演變**：
- Claw Code 從 64K → 123.7K stars（翻倍），加速 Rust clean-room 重寫
- NanmiCoder 仍存活（3K stars），未被 DMCA
- Anthropic ~16hr 從發現到修復（v2.1.89）
- Grok 分析：洩漏使 Anthropic 的「dev tools moat」縮小，但核心價值仍在基礎模型 + scaling [src:036]
- **新發展**：Anthropic 的自動化 DMCA 誤殺合法 fork（Theo 事件），引發開發者信任危機 [src:043][src:044][src:045]
- DMCA 風波從「合理维权」升级為「生態信任問題」

## Coding AI 工具更新追蹤

### Claude Code（Anthropic）[src:013][src:014]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v2.1.89 | 04-01 | 洩漏修復 + 40+ fixes、defer hooks、PermissionDenied hook、autocompact thrash 修復 |
| v2.1.90 | 04-01 | /powerup 互動教學、SSE O(n)、PowerShell 安全、/buddy 彩蛋 |

### OpenAI Codex CLI [src:015][src:016][src:020]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v0.118.0 | 03-31 | Windows sandbox、spawn v2 inter-agent、device code flow |
| v0.119.0-alpha.2 | 04-01 | Rust port、interrupted state、spawn_agent/send_message API |
| Copilot CLI v1.0.15 | 04-01 | **移除 gpt-5.1-codex 系列**、postToolUseFailure hooks |

### Gemini CLI（Google）[src:017][src:018]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v0.36.0 | 04-01 | **三平台完整 sandbox**、subagent 工具隔離、A2A、Plan mode stable |
| v0.37.0-preview.0 | 04-01 | unified context management、tool distillation、topic chapters |

### Cursor [src:046]

| 功能 | 日期 | 關鍵變更 |
|------|------|---------|
| Automations | 04-02 | **事件驅動雲端 agent**：commit/PR/Slack/PagerDuty/Timer 觸發 |

## 分析過的工具

| 日期 | 工具 | 版本 | 評分 | 備註 |
|------|------|------|------|------|
| 2026-04-02 | Claude Code | v2.1.90 | ⭐⭐⭐⭐ | 洩漏後快速反應，安全+性能並重；DMCA 誤殺扣分 |
| 2026-04-02 | Gemini CLI | v0.36.0 | ⭐⭐⭐⭐⭐ | 三平台 sandbox + subagent 隔離最完整 |
| 2026-04-02 | OpenAI Codex | v0.118.0 | ⭐⭐⭐⭐ | Rust port 進展順利，71.8K stars 動能強 |
| 2026-04-02 | GitHub Copilot CLI | v1.0.15 | ⭐⭐⭐ | MCP OAuth 有用，移除 coding 模型策略不明 |
| 2026-04-02 | OpenClaw | v2026.4.1 | ⭐⭐⭐⭐ | 迭代快速但穩定性受疑，企業功能擴展佳 |
| 2026-04-02 | Claw Code | — | ⭐⭐⭐ | 123.7K stars 但仍重寫中，實際可用性存疑 |
| 2026-04-02 | Holo3 | 35B/122B | ⭐⭐⭐⭐ | Computer-use SOTA，開源 Apache 2.0，成本 1/10 |
| 2026-04-02 | Litter | beta | ⭐⭐⭐ | Codex 移動化首創，但早期階段 |
| 2026-04-02 | Cursor Automations | 新 | ⭐⭐⭐⭐ | 範式轉變：事件驅動 agent，但成本/品質風險待觀察 |
