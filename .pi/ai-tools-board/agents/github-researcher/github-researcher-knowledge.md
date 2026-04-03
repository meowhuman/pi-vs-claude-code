# GitHub Researcher — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 github-researcher-sources.md。

---

## 🔥 第二次全委員會議 — 增量洞見 (2026-04-02T02:18 更新)

### 三大核心信號

#### 信號 1：洩漏碼「DMCA 誤殺」事件 — Anthropic 法律行動的預期外衝擊 [src:016-017]
- **事實**：Anthropic 針對洩漏碼 fork 發出 DMCA takedown，但 GitHub 處理時**誤殺了官方 repo 的合法 fork** (mbailey/claude-code-fork)
- **影響**：合法 fork 用戶面臨「聲譽威脅」，社群出現對 Anthropic 法律策略的不滿
- **同時**：社群開始自行舉報授權繞過的 repo（nilupulk/claude-code-free，使用假 API key + OpenRouter 代理）
- **判斷**：DMCA 是雙面刃。過度使用會傷害合法開發者信任，但洩漏碼的衍生版（如 openclaude、better-clawd）仍在快速增長。法律手段無法阻擋開源社區的「知識擴散」。

#### 信號 2：「洩漏碼生態系」48 小時內從洩漏→分析→重構→替代品完整成型 [src:018-023]
過去 72 小時出現了令人震驚的衍生速度：

| 衍生品 | Stars | Forks | 用途 |
|--------|-------|-------|------|
| x1xhlol/system-prompts-and-models-of-ai-tools | **134,031** | 33,785 | 全 AI 工具 system prompt 彙整 |
| shareAI-lab/learn-claude-code | **46,517** | 7,343 | 從零重建 nano agent harness |
| Gitlawb/openclaude | 3,734 | 1,457 | Claude Code 接入任何 LLM |
| Leonxlnx/agentic-ai-prompt-research | 1,762 | 860 | AI coding assistant prompt 模式研究 |
| motiful/cc-gateway | 1,743 | 342 | API 指紋正常化閘道 |
| openedclaude/claude-reviews-claude | 1,008 | 549 | Claude 讀自己的原始碼（17 章架構深度剖析） |
| farion1231/cc-switch | 37,141 | 2,239 | 多 agent 桌面統一工具 |
| router-for-me/CLIProxyAPI | 22,058 | 3,640 | CLI → API 代理服務 |

**關鍵觀察**：
- `system-prompts-and-models-of-ai-tools` (134K stars) 成為洩漏事件的最大受益者，不只限於 Claude Code，而是匯集了 **27+ 個 AI 工具的 system prompt**
- `learn-claude-code` (46.5K stars) 證明了「教育復刻」路線的成功 — 從零重建比 fork 更容易獲得社群認同
- `cc-switch` (37.1K stars) 和 `CLIProxyAPI` (22K stars) 代表了「多 agent 切換」和「API 代理」這兩個新興基礎設施需求

**判斷**：洩漏事件的長期影響不是某個 fork 的生存，而是整個社群對 agent harness 架构的理解深度大幅提升。這等於一次強制性的「open source education」。

#### 信號 3：五大 Agent 同步進入「架構重構期」 — Plugin 生態大戰即將開打 [src:024, 036-043]
- **Claude Code**：v2.1.90 引入 `/powerup` 教學系統 + EvalView plugin（AI agent 回歸測試），顯示正在建設 plugin 生態
- **Codex**：48 小時內抽出 `codex-tools`、`codex-mcp`、移除 `client_common` re-exports 三個 crate，為 plugin 架構做模組化準備 [src:036-038]
- **Gemini CLI**：v0.36.0→v0.37.0-preview.0，同日發佈 3 個版本，sandbox 可用性修復 + ADK session 設定 [src:039-041]
- **OpenClaw**：exec approvals 統一化 + memory 性能優化（trim matrix imports）+ plugin docs [src:057-058]
- **Goose**：mesh binary 每次啟動下載新版本 + `~/.agents/skills/` 標準化技能路徑 [src:042-043]

**判斷**：所有主要 agent 都在同時做同一件事 — **把核心拆成模組，為第三方 plugin 打基礎**。這意味著未來 30 天內我們可能看到第一波「跨 agent 通用 plugin」的出現。

---

## 📊 追蹤 Repo 狀態快照（2026-04-02T02:18Z）

> 與首次會議基線比較。Δ 為與首次會議快照的差值。

### 程式 AI — 主力工具

| Repo | Stars (Δ) | Forks | Last Push | 活躍度 |
|------|-----------|-------|-----------|--------|
| openclaw/openclaw | 344,703 (+16) | 68,403 | 02:17Z | 🔴 極高 |
| ollama/ollama | **166,712** (新) | 15,258 | 23:59Z | 🟡 中 |
| instructkr/claw-code | 123,579 (+648) | 102,067 | 00:06Z | 🟡 中高 |
| anthropics/claude-code | 101,484 (+106) | 15,768 | 23:41Z | 🟡 中高 |
| google-gemini/gemini-cli | **99,908** (+2) | 12,815 | 02:16Z | 🟠 高 |
| openai/codex | 71,829 (+20) | 10,038 | 02:16Z | 🔴 極高 |
| block/goose | 33,913 (+1) | 3,172 | 01:59Z | 🟡 中高 |
| Yeachan-Heo/oh-my-codex | 8,786 (+34) | 806 | 01:47Z | 🟢 中 |

### 洩漏衍生生態

| Repo | Stars (Δ) | Forks | Last Push | 備註 |
|------|-----------|-------|-----------|------|
| x1xhlol/system-prompts-and-models-of-ai-tools | 134,032 (+1) | 33,785 | 03-28Z | 27+ 工具 prompt 彙整 |
| asgeirtj/system_prompts_leaks | 35,729 | 5,875 | 01:35Z | 定期更新 |
| farion1231/cc-switch | 37,141 (+12) | 2,239 | 01:25Z | 桌面統一工具 |
| shareAI-lab/learn-claude-code | 46,517 (+18) | 7,343 | 01:00Z | 教育 harness |
| Gitlawb/openclaude | 3,734 (+27) | 1,457 | 01:40Z | 多 LLM 接入 |
| NanmiCoder/claude-code-haha | 3,098 | 3,755 | 04-01Z | 🔵 趨緩 |
| can1357/oh-my-pi | 2,552 | 228 | 23:07Z | Pi fork |

### Claude Code 生態圈（新追蹤）🆕

| Repo | Stars | Forks | 用途 |
|------|-------|-------|------|
| **affaan-m/everything-claude-code** | **131,251** | 18,805 | 跨 agent harness 性能優化系統 |
| **garrytan/gstack** | **60,950** | 8,043 | Garry Tan 個人 Claude Code 配置 |
| **thedotmack/claude-mem** | **44,434** | 3,340 | 自動記憶壓縮插件 |
| **musistudio/claude-code-router** | 31,132 | 2,436 | Claude Code 基礎設施路由 |
| sickn33/antigravity-awesome-skills | 29,837 | 4,980 | 1340+ agentic skills 安裝庫 |
| ruvnet/ruflo | 29,216 | 3,193 | 多 agent swarm 編排平台 |

### 其他重要追蹤

| Repo | Stars | Pushed | 備註 |
|------|-------|--------|------|
| Wan-Video/Wan2.1 | 15,732 | 03-05Z | 影片生成 |
| HKUDS/DeepCode | 15,064 | 活躍 | Paper2Code |
| deepseek-ai/FlashMLA | 12,548 | 03-31Z | MLA kernels |
| deepseek-ai/3FS | 9,786 | 03-30Z | 分散式檔案系統 |
| deepseek-ai/DeepEP | 9,091 | 03-31Z | MoE 通信 |
| facebookresearch/audiocraft | 23,141 | 03-03Z | Meta MusicGen |
| suno-ai/bark | 39,069 | 08-2024 | Bark TTS |

---

## 📈 Star 增長速率分析（累計自首次會議以來）

| Repo | 累計 Δ Stars | 速率 | 判斷 |
|------|-------------|------|------|
| claw-code | +648 | 快速但趨穩 | v0.1.0 合併後穩定增長 |
| claude-code (官方) | +106 | 健康 | 不受洩漏影響，持續增長 |
| learn-claude-code | +18 | 穩定 | 教育 harness 持續吸引用戶 |
| oh-my-codex | +34 | 穩定 | OmX 工具層 |
| openclaw | +16 | 穩定 | 企業功能持續強化 |
| openclaude | +27 | 活躍 | 多 LLM 需求強烈 |

---

## 趨勢觀察

### 1. 🏗️ Claude Code 生態圈規模驚人 — 131K stars 的「everything-claude-code」被低估 [src:044] ⬆️ 新信號
- `affaan-m/everything-claude-code` 以 **131,251 stars** 成為 Claude Code 生態中最大的專案
- 搭配 `gstack` (60.9K)、`claude-mem` (44.4K)、`antigravity-awesome-skills` (29.8K)
- **Claude Code 生態圈的總 star 數（含衍生）已超過 500K**
- **判斷**：Claude Code 已不再只是一個 CLI 工具，它形成了一個完整的「agent 開發平台」。這個生態的規模甚至超過了很多獨立 AI 工具。

### 2. 🏗️ Coding Agent 從「CLI 工具」升級為「Agent 作業系統」 [src:001-005] ⬆️ 加速確認
48 小時前識別的趨勢正在加速：
- **Plugin 生態建設**：Claude Code 的 EvalView PR、Codex 的 crate 抽取、Goose 的技能路徑標準化
- **Agent 互通需求爆發**：cc-switch (37.1K)、cc-connect (3.9K)、CLIProxyAPI (22K) 的快速增長證明了「多 agent 共存」已成現實

### 3. ⚡ Claw Code 從爆發進入「產品化」階段 [src:007] ⬅️ 狀態更新
- 最新 commits：CLI redesign、REPL hardening、first-run 引導優化、OmX/OmO README 信用重平衡
- Star 累計增長 +648（相較於首次快照），進入穩態
- **信號**：從「現象級 fork」轉為「有明確產品方向的開源專案」

### 4. 🦞 OpenClaw 持續記憶性能優化 [src:057-058] 🆕
- 連續多個 `perf(memory): trim matrix ... imports` commits
- 持續高頻開發（每 5-10 分鐘一個 commit）
- **判斷**：OpenClaw 作為唯一超過 344K stars 的個人 AI 助手，正在對 20+ channels 進行記憶管理的深度優化

### 5. 🔧 Codex 三連發模組化 — MCP + Tools + Re-exports [src:036-038] 🆕
- `codex-mcp` crate：MCP runtime/server 獨立
- `codex-tools` crate：update_plan spec 獨立
- 移除 `client_common` re-exports：解耦內部依賴
- **判斷**：Codex 的模組化速度最快且最有系統性。三個 crate 的抽出時間間隔不到 4 小時。

### 6. 🐧 oh-my-pi 持續追趕 — 新增 ZIP 工具 + Anthropic 超時強化 [src:053-054] 🆕
- 新增 ZIP archive writing support（fflate 庫）
- Anthropic first-event timeouts 硬化修復
- 版本升級至 13.17.5→13.17.6
- **判斷**：oh-my-pi 作為 Pi 的 fork，功能密度正在快速追上主線，但 2,552 stars 顯示社群接受度仍有限

### 7. 🎯 Gemini CLI 100K 里程碑 [src:005, 039-041] 📊 觀察中
- 目前 99,908 stars，距離 100K 僅差 92
- 同日 v0.36.0 正式 + v0.37.0-preview.0
- sandbox 可用性修復 + agent 停止條件修正 + ADK session 設定
- **判斷**：v0.36.0 正式版的發佈可能在未來 24 小時內推動突破 100K

### 8. 🦙 Ollama 本地推理擴展 [src:025] ⬅️ 狀態確認
- 166,712 stars，穩定
- Kimi-K2.5、GLM-5、MiniMax 支援
- v0.19.0 MLX 後端（Apple Silicon）
- **信號意義**：本地推理生態正在快速擴展模型覆蓋範圍

### 9. 🔐 洩漏碼安全分析生態成型 [src:018-019] ⬅️ 穩定
- `Marwane-Haddane/Claude_code_leak`：網路安全視角
- `Leonxlnx/agentic-ai-prompt-research`：prompt 模式研究
- `openedclaude/claude-reviews-claude`：架構剖析
- `claude-code-haha`：3,098 stars，活躍度降至幾乎零（最後 push 4/1 05:59Z）

---

## 🔍 新興項目雷達

| 專案 | Stars | 為什麼值得關注 |
|------|-------|--------------|
| **affaan-m/everything-claude-code** | 131K | 跨 agent 性能優化系統，Claude 生態基石 |
| **ColeMurray/background-agents** | 1.4K | 開源背景 agent 系統 — agent 不需人工啟動 |
| **abshkbh/arrakis** | 792 | MicroVM sandboxing + backtracking — agent 安全執行的關鍵基礎設施 |
| **shamcleren/CodePal** | 新 | 多 IDE/agent 統一監控面板 |
| **HKUDS/DeepCode** | 15.1K | Paper2Code — 從論文自動生成可運行代碼 |

---

## 洩漏碼生態演變追蹤（最終更新）

| 階段 | 時間 | 事件 |
|------|------|------|
| 洩漏 | 2026-03-31 04:00 | NanmiCoder/claude-code-haha 公開洩漏碼 |
| Clean-room 重寫 | 2026-03-31 | instructkr 用 OmX 完成 Python 重寫 |
| 爆發 | 2026-04-01 | claw-code 突破 50K stars（2 小時） |
| Rust port | 2026-04-01 | Rust 工作區開始開發 |
| v0.1.0 合併 | 2026-04-01 21:05 | release/0.1.0 合併進 main |
| DMCA 誤殺 | 2026-04-01 | GitHub 處理 DMCA 時誤殺官方 repo 合法 fork |
| 分析潮 | 2026-04-01~02 | 安全研究、架構剖析、prompt 重建專案大量湧現 |
| 替代品潮 | 2026-04-01~02 | openclaude、better-clawd、openharness 等替代品出現 |
| 趨穩 | 2026-04-02 | claude-code-haha 活躍度降至零，社群轉向建設性專案 |

**最終判斷**：洩漏事件的影響已遠超 Claude Code 本身。它催化了：
1. **AI agent 安全研究**的公開化
2. **Agent harness 架構**的民主化知識
3. **跨 LLM 代理**的基礎設施需求（openclaude、CLIProxyAPI）
4. **多 agent 管理**工具的爆發（cc-switch、cc-connect）
5. **Claude Code 生態圈**的全面爆發（everything-claude-code 131K、gstack 61K、claude-mem 44K）

---

## Repo 活躍度追蹤（更新）

| Repo | 48h Commits | 活躍度 | 趨勢 |
|------|------------|--------|------|
| openclaw/openclaw | ~30+ | 🔴 極高 | 記憶優化 + 企業功能強化 |
| openai/codex | ~20+ | 🔴 極高 | 三 crate 抽出 + 架構重構 |
| google-gemini/gemini-cli | ~15+ | 🟠 高 | v0.36→0.37 快速迭代 |
| anthropics/claude-code | ~8 | 🟡 中高 | 穩定迭代，plugin 生態建設 |
| block/goose | ~10 | 🟡 中高 | mesh 動態更新 + 技能標準化 |
| instructkr/claw-code | ~10 | 🟡 中高 | v0.1.0 合併後產品化 |
| Yeachan-Heo/oh-my-codex | ~5 | 🟢 中 | 穩定更新 |
| can1357/oh-my-pi | ~8 | 🟢 中 | 功能追趕 |
| NanmiCoder/claude-code-haha | ~0 | 🔵 停滯 | 活躍度歸零 |
