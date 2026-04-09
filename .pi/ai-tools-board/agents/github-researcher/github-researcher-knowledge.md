# GitHub Researcher — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 github-researcher-sources.md。

---

## 🔥 第三次全委員會議 — 增量洞見 (2026-04-06T01:00 更新)

### 四大核心信號

#### 信號 1：Claw Code 爆炸性增長 — 170K stars，48 小時 +47K，歷史最快 [src:new]
- **事實**：`instructkr/claw-code` 從第二次會議的 123,579 stars 飆升至 **170,854** — 4 天內增加 **47,275 stars**
- **fork 數同步暴增**：從 102,067 升至 **103,628**，近 1.6K 新 fork
- **產品化加速**：Rust 工作區 container 化（Containerfile）、tagged binary release workflow、clawability hardening backlog 完成
- **判斷**：Claw Code 已經從「洩漏碼重寫」徹底轉型為獨立開源專案。Rust 版本的持續重構 + OmX 工具層整合，使其具備了與 Claude Code 正面競爭的架構基礎。170K stars 的規模使其成為 GitHub 上最大的 coding agent 專案。

#### 信號 2：Claude Code 連續三天重大更新 — v2.1.90→91→92，進入「企業化攻堅期」 [src:059-060]
- **v2.1.91** (4/3)：MCP 工具結果上限提升至 **500K chars**（`_meta["anthropic/maxResultSizeChars"]`）、plugins 可在 `bin/` 放可執行檔、新增 `disableSkillShellExecution` 安全設定
- **v2.1.92** (4/4)：**互動式 Bedrock 設定向導**（3rd-party platform 登入時直接引導 AWS auth + region + credential）、`forceRemoteSettingsRefresh` 企業 policy（fail-closed 模式）、per-model `/cost` 明細
- **判斷**：三個版本的共同主題是「企業客戶」。Bedrock 向導降低了 AWS 部署門檻，fail-closed policy 滿足合規需求，500K MCP result 解鎖了大型 DB schema 等企業場景。Claude Code 正在從開發者工具轉型為企業平台。

#### 信號 3：OpenClaw 進軍多模態 — 音樂生成 + ComfyUI 工作流 + Bedrock 嵌入 [src:067-069]
- **音樂生成工具** (4/6)：`feat: add music generation tooling` — OpenClaw 新增原生音樂生成能力，含 async flow 文檔
- **ComfyUI 媒體支援** (4/6)：`feat: add comfy workflow media support` — 直接整合 ComfyUI 工作流
- **Bedrock 記憶嵌入** (4/6)：`feat(memory): add Bedrock embedding provider for memory search` — 使用 AWS Bedrock 做記憶搜尋的嵌入
- **Bedrock Mantle IAM auth** (4/6)：PR #61563 新增 IAM credential auth
- **判斷**：OpenClaw 正在從「聊天機器人」變成一個**通用多模態 agent 平台**。音樂生成 + ComfyUI 整合代表它不再局限於文字。Bedrock 嵌入則降低了 AWS 客戶的使用門檻。349K stars 的基數使這些功能有巨大的即時受眾。

#### 信號 4：五大 Agent 全面成熟 — 架構重構期進入「收成階段」 [src:059-073]
與第二次會議（4/2）的「同步 plugin 化」判斷對比，現在的狀態：

| Agent | 4/2 狀態 | 4/6 狀態 | 進展 |
|-------|---------|---------|------|
| Claude Code | Plugin 基礎建設 | **Plugin bin/ + 500K result + Bedrock 向導** | ⬆️ 企業化 |
| Codex | Crate 抽取 | **context-window lineage + subagent analytics + gpt-5.3-codex** | ⬆️ 可觀測性 |
| Gemini CLI | v0.36→0.37 | **100K stars ✅ + ACP /about + compact output 預設** | ⬆️ UX 精煉 |
| Goose | 技能路徑標準化 | **v1.30.0: MCP Roots + fast_model + ACP 並行載入** | ⬆️ 擴展性 |
| Claw Code | v0.1.0 合併 | **170K stars + Rust container 化 + binary release** | ⬆️⬆️ 爆發 |

**判斷**：從「為 plugin 打基礎」進入「收成階段」。各 agent 開始在自己的利基市場深挖：Claude Code 搶企業、Codex 做可觀測性、Gemini CLI 磨 UX、Goose 做擴展性、Claw Code 搶開源社群。

---

## 📊 追蹤 Repo 狀態快照（2026-04-06T01:00Z）

> Δ 為與第二次會議（4/2 02:18Z）快照的差值。ΔΔ 為與首次會議基線的差值。

### 程式 AI — 主力工具

| Repo | Stars (Δ / ΔΔ) | Forks | Last Push | 活躍度 |
|------|---------------|-------|-----------|--------|
| openclaw/openclaw | 349,034 (+4,331 / +4,347) | 69,895 | 00:50Z | 🔴 極高 |
| instructkr/claw-code | **170,854** (+47,275 / +47,923) | 103,628 | 00:30Z | 🔴 極高 ⚡ |
| ollama/ollama | 167,311 (+599 / 新追蹤) | 15,354 | 04-04Z | 🟡 中 |
| anthropics/claude-code | 109,378 (+7,894 / +8,000) | 18,129 | 04-04Z | 🟡 中高 |
| google-gemini/gemini-cli | **100,316** (+408 / +410) ✅ | 12,904 | 04-05Z | 🟠 高 |
| openai/codex | 73,303 (+1,474 / +1,494) | 10,302 | 04-06Z | 🔴 極高 |
| block/goose | 37,036 (+3,123 / +3,124) | 3,542 | 04-06Z | 🟡 中高 |
| Yeachan-Heo/oh-my-codex | 16,610 (+7,824 / +7,858) | 1,585 | 04-05Z | 🟠 高 ⚡ |

### Claude Code 生態圈

| Repo | Stars (Δ) | Forks | Pushed | 用途 |
|------|-----------|-------|--------|------|
| affaan-m/everything-claude-code | **140,507** (+9,256) | 21,152 | 00:51Z | 跨 agent 性能優化 |
| garrytan/gstack | ~63K (估) | — | 活躍 | Claude Code 配置 |
| thedotmack/claude-mem | ~47K (估) | — | 活躍 | 記憶壓縮插件 |
| sickn33/antigravity-awesome-skills | ~32K (估) | — | 活躍 | 1340+ skills |

### 洩漏衍生生態

| Repo | Stars (Δ) | Last Push | 狀態 |
|------|-----------|-----------|------|
| shareAI-lab/learn-claude-code | 48,618 (+2,101) | 04-01Z | 穩定 |
| x1xhlol/system-prompts-and-models-of-ai-tools | ~136K (估) | 03-28Z | 緩增 |
| can1357/oh-my-pi | 2,678 (+126) | 04-05Z | 穩定 |
| NanmiCoder/claude-code-haha | ~3.1K | 04-01Z | 🔵 停滯 |

### 其他追蹤

| Repo | Stars | 備註 |
|------|-------|------|
| Wan-Video/Wan2.1 | 15,732 | 影片生成 |
| HKUDS/DeepCode | 15,100 | Paper2Code |
| facebookresearch/audiocraft | 23,141 | Meta MusicGen |
| suno-ai/bark | 39,069 | Bark TTS |

---

## 📈 Star 增長速率分析（4/2→4/6，4 天）

| Repo | Δ Stars (4天) | 日均 | 判斷 |
|------|-------------|------|------|
| **claw-code** | **+47,275** | **~11.8K/天** | 🔴 超級爆發，歷史級增速 |
| **everything-claude-code** | **+9,256** | **~2.3K/天** | 🟠 快速增長，Claude 生態擴張 |
| claude-code (官方) | +7,894 | ~2K/天 | 🟠 健康加速，v2.1.91-92 企業化奏效 |
| oh-my-codex | +7,824 | ~2K/天 | 🟠 突然加速，OmX 工具層被發現 |
| goose | +3,123 | ~780/天 | 🟡 穩定 |
| openclaw | +4,331 | ~1.1K/天 | 🟡 穩定高位 |
| codex | +1,474 | ~370/天 | 🟢 穩定 |
| gemini-cli | +408 | ~100/天 | 🟢 突破 100K 後趨穩 |
| ollama | +599 | ~150/天 | 🟢 穩定 |
| oh-my-pi | +126 | ~32/天 | 🟢 緩增 |

---

## 趨勢觀察

### 1. ⚡ Claw Code +47K stars 是 GitHub 歷史上最快增長的 coding agent [src:new]
- 4 天 +47K stars，超越 Claude Code 的累計增長速度
- 同時 fork 數達 103K — 幾乎與 star 數 1:1，顯示開發者正在**實際 clone 和修改**
- Rust 工作區 + container 化 + binary release workflow，顯示正在建設正式的發布基礎設施
- **判斷**：Claw Code 已不再是 Claude Code 的 shadow — 它是獨立的開源 coding agent 品牌。

### 2. 🏢 Claude Code 三連發企業化 — Bedrock + Policy + MCP 大結果 [src:059-060]
- v2.1.91 的 `_meta["anthropic/maxResultSizeChars"]` 解鎖了一個關鍵瓶頸：大型 DB schema、長文件等場景之前會被截斷
- v2.1.92 的 Bedrock 向導直接在 CLI login 畫面提供引導，降低了 AWS 企業部署摩擦
- `forceRemoteSettingsRefresh` fail-closed policy 是為合規團隊設計的
- **判斷**：Anthropic 正在把 Claude Code 從「開發者玩具」推向「企業標配」。Bedrock 整合是攻入 AWS 生態的關鍵棋。

### 3. 🦞 OpenClaw 多模態擴張 — 音樂 + ComfyUI 是質變信號 [src:067-069]
- 音樂生成和 ComfyUI 支援不是 incremental feature — 它們代表了 OpenClaw 從「文字 agent」到「多模態 agent OS」的轉型
- Bedrock 嵌入用於記憶搜尋，意味著 AWS 客戶可以完全在 AWS 生態內運行 OpenClaw
- 349K stars 保證了這些新功能有巨大的即時使用者基礎
- **判斷**：OpenClaw 正在成為「通用 AI 助手平台」，類似於一個開源的 ChatGPT + plugin 系統。這對 coding agent 是間接影響 — 多模態能力將模糊 coding agent 和 general agent 的界線。

### 4. 🔧 Codex 深耕可觀測性 — context-window lineage + subagent analytics [src:061-063]
- `context-window lineage headers`：追蹤 context window 的完整傳承鏈
- `subagent analytics`：PR #15915 加入 subagent thread 分析事件
- `CODEX_SKIP_VENDORED_BWRAP`：為沒有 bubblewrap 的 Linux 環境提供建置選項
- `allow disabling environment context injection` + `allow disabling prompt instruction blocks`：讓進階用戶完全控制 prompt 結構
- **判斷**：Codex 的工程方向非常明確 — 不是追功能，而是做**最深度的可觀測性和可控性**。這對企業客戶（需要 audit trail 和成本控制）極具吸引力。

### 5. 🎯 Gemini CLI 突破 100K — UX 精煉階段 [src:064-066]
- **100,316 stars** ✅ 正式突破 100K 里程碑
- 新增：ACP `/about` command、compact tool output **預設啟用**、tool confirmation UI 改善、sandbox 全球 temp dir 修復、skill system 注入 subagent prompts
- 多個 Windows sandbox reliability 修復
- **判斷**：Gemini CLI 正在進入「打磨期」— 功能已足夠完整，重點轉向穩定性和 UX。compact output 預設啟用是重要的 UX 決策。

### 6. 🪿 Goose v1.30.0 — MCP Roots + fast_model + ACP 並行載入 [src:070]
- MCP Roots 文檔新增
- `fast_model` 設定用於 declarative providers
- ACP extension loading 並行化（`perf(acp): parallelize extension loading`）
- v1.29.1 修復 macOS Intel code signing
- **判斷**：Goose 的方向是「擴展性優先」— 讓更多 provider、更多 extension 同時運行。`fast_model` 設定暗示了推理成本優化的需求。

### 7. 🛠️ Oh-My-Codex v0.11.13 — OmX 從工具層升級為「agent 質量框架」 [src:069]
- v0.11.12→v0.11.13，48 小時內兩個版本
- 持續 CI 穩定性修復（tmux-heal、mailbox notifications、dispatch）
- **判斷**：oh-my-codex 的 7.8K Δ stars（4 天）顯示 OmX 工具層正在被更廣泛的社群發現。作為 Codex 的 orchestrator，它填補了 Codex 本身在 multi-agent 管理上的空白。

---

## 🆕 新興項目雷達（第三次會議）

| 專案 | Stars | 為什麼值得關注 |
|------|-------|--------------|
| **stablyai/orca** | 427 | 「Next-gen IDE for building with coding agents」— agent 原生 IDE，非傳統 IDE + plugin |
| **blackpaw-studio/leo** | 新 | Claude Code agents + Telegram + cron = 持久化 personal assistant |
| **Yabuku-xD/contextforge** | 新 | Context engine for code agents — MCP + retrieval + impact analysis |
| **kawarimidoll/guard-and-guide** | 新 | Guard coding agents from dangerous ops — agent 安全層 |
| **manaflow-ai/cmux** | 新 | Ghostty-based macOS terminal with vertical tabs for agents |
| **mikeroySoft/ctux** | 新 | btop-inspired TUI for managing multiple Claude Code agents |

**判斷**：「agent 管理和監控」類工具正在快速湧現。cmux（terminal）、ctux（TUI）、Leo（Telegram bridge）代表了開發者對「同時運行多個 agent」這一新現實的適應。

---

## 🔍 第二次會議信號追蹤更新

### 洩漏碼生態 — 趨穩確認 [src:056]
- `claude-code-haha`：活躍度完全歸零（最後 push 4/1），已被社群遺忘
- `learn-claude-code`：+2.1K stars，穩定增長
- `oh-my-pi`：+126 stars，緩增，社群接受度有限

### Plugin 生態大戰 — 已進入收成期
- 上次預測「30 天內看到跨 agent 通用 plugin」— 目前尚未出現
- 但各 agent 的 plugin 基礎設施已基本就緒（Claude Code bin/、Goose MCP Roots、Codex crate modularity）
- **修正判斷**：跨 agent plugin 的瓶頸不是技術基礎設施，而是 **prompt 和 tool call 格式的不統一**。MCP 協議可能成為共同語言，但各 agent 的 system prompt 差異太大。

### Gemini CLI 100K — ✅ 已達成
- 100,316 stars，比預測的「24 小時內」晚了約 3 天
- v0.36.0→v0.37.0-preview.1 的快速迭代提供了持續動力

---

## Repo 活躍度追蹤（第三次會議）

| Repo | 48h Commits (4/4-4/6) | 活躍度 | 趨勢 |
|------|----------------------|--------|------|
| openclaw/openclaw | ~30+ | 🔴 極高 | 音樂生成 + ComfyUI + Bedrock |
| openai/codex | ~15+ | 🔴 極高 | lineage + analytics + context control |
| google-gemini/gemini-cli | ~12 | 🟠 高 | UX 精煉 + sandbox 修復 |
| anthropics/claude-code | 2 (releases) | 🟡 中 | v2.1.91→92，品質優先 |
| block/goose | ~5 | 🟡 中 | MCP Roots + ACP 並行 |
| instructkr/claw-code | ~15 | 🟠 高 | Rust container + binary release |
| Yeachan-Heo/oh-my-codex | ~15 | 🟠 高 | v0.11.13 CI 穩定性 |
| can1357/oh-my-pi | ~5 | 🟢 中 | 穩定更新 |
| NanmiCoder/claude-code-haha | 0 | 🔵 停滯 | 已死 |

---

## 🎯 委員會行動建議

### 立即採用
1. **Claude Code v2.1.92 Bedrock 向導** — 如果團隊用 AWS，立即升級，設定摩擦大幅降低
2. **Gemini CLI v0.36.0** — 100K stars 里程碑版，compact output 預設啟用改善 UX

### 密切觀察
1. **Claw Code 170K stars 的後續** — 這個增速是否可持續？Rust 版本的成熟度如何？
2. **OpenClaw 多模態擴張** — 音樂生成 + ComfyUI 是否會吸引新使用者群？
3. **Codex 的 gpt-5.3-codex 模型** — PR #15915 中的 subagent analytics 暗示了新模型的使用

### 可忽略
1. **洩漏碼生態** — 已完全趨穩，不再有新的技術信號
2. **oh-my-pi** — 2,678 stars，社群接受度低，追蹤價值有限
3. **新出現的 agent 管理 TUI**（cmux、ctux、leo）— 過早，待觀察社群採用度
