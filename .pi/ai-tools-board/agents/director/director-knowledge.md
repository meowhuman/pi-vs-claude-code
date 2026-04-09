# Director — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 director-sources.md。

## AI 工具生態全局觀

### 2026-04-06 第三次全委員會整合報告（v3 — 最終版）

**方法論**：8 位委員（director + coding-ai-scout + github-researcher + system-analyst + eval-engineer + cost-performance-analyst）分工研究。GitHub API ✅、新聞 ⚠️ 二手信源、WSP-V3 ❌ 不可用。

**本週特徵**：近期信息密度最高的一週——Anthropic 築牆、OpenAI 拆牆、四線 frontier model 同時曝光、AI 安全攻守失衡。

---

## 🏆 本週最值得關注的 3 件事

### 1. 🏗️ Anthropic Walled Garden 成型 vs OpenAI 拆牆 — 生態戰略的根本分歧 [src:001-005]
- Anthropic 4/4 封殺 Claude Code 訂閱對第三方 harness 覆蓋（OpenClaw 等），HN **1,070 pts** 爆發反彈
- DMCA 連鎖：誤殺 fork → 承認撤回 → 推收費牆；同時 ~$4B 收購 Coefficient Bio、成立 PAC、目標 10 月 IPO
- **OpenAI 反向操作**：官方 `codex-plugin-cc` 讓 Claude Code 用戶直接呼叫 Codex review/adversarial-testing，**2 天 11,910 stars**
- **主席判斷**：一家在築牆（IPO 盈利壓力），一家在拆牆（生態滲透）。Claude Code 佔 GitHub 全部 commits 的 4%（日均 135K），OpenAI 的算帳邏輯清楚：「與其搶用戶，不如成為每個用戶的第二個模型」。Pi 的多 provider 支援是正確對沖。

### 2. ⚡ AI 安全攻守嚴重失衡 — 從 supply chain 到 autonomous exploit [src:006-008]
- Claude 自主構建 FreeBSD kernel root shell（CVE-2026-4747），4hr 完成，同一 pipeline 量產 500 個高嚴重性漏洞
- Langflow 成為首個列入 CISA KEV 的 AI agent 框架（公開 20hr 即被攻擊）
- AgentSeal：66% MCP server 有安全問題；CrewAI 披露 Docker sandbox 逃逸 CVE
- 研究證實「認知投降」（cognitive surrender）— 人類不批判地接受 AI 錯誤答案（HN 817pts）
- **主席判斷**：對策不是更複雜的架構，而是更簡單的邊界——單 agent + 明確 tool scope + human-in-the-loop checkpoint。

### 3. 🌍 四線 Frontier Model 軍備賽 — Spud、Mythos、DeepSeek V4、Gemma 4 [src:009-013]
- **GPT-5.5 "Spud"**：預訓練完成（Altman: weeks away），知識工作 83%，Polymarket 70-75% 機率 4/30 前發佈
- **Claude Mythos**：洩漏為「史上最強模型」，因成本/安全暫緩
- **DeepSeek V4**：完全華為 Ascend 訓練（~1T params, 1M context, $0.30/MTok），美國出口管制被實質突破
- **Gemma 4**：首次 Apache 2.0，iPhone 本地可跑，RTX 3090 + FP4 量化 100+ tok/s
- **主席判斷**：成本敏感的 agent 工作流最大受益者是 Gemma 4（本地免費）和 DeepSeek V4（$0.30/MTok）。Spud 仍是最大變數。

---

## 📊 分領域關鍵動態

### Coding Agent（coding-ai-scout + github-researcher）
- **Codex Plugin for Claude Code**（11.9K stars/2 天）— 跨平台互操作範式確立
- **MCP + A2A v1.0 同時定稿**（146 成員、9700 萬 SDK downloads/月）— Agent 工具層「HTTP 標準化時刻」
- **Cursor 3** Agent-first 重構（multi-agent orchestration）
- **Claude Code v2.1.92**：Bedrock 設定向導 + MCP 500K result + Write/Edit 60% 加速 + `/cost` per-model breakdown
- **Codex** 出現 `gpt-5.3-codex` 專用模型 — coding agent 走向「專用模型」時代

### 開源生態（github-researcher）
- Claw Code **170.8K**（4 天 +47K，歷史級增速）、OpenClaw 349K、Gemini CLI 突破 **100K**
- OpenClaw 進軍多模態：音樂生成 + ComfyUI + Bedrock 嵌入（同一小時 3 個 feat commit）

### 政策法規（system-analyst）
- Meta/Google Section 230 首次被突破（30 年來首次）、Writers Guild 4 年協議
- Apple 批准 Nvidia eGPU 驅動（歷史性合作）、Samsung DRAM Q2 +30%
- OpenAI 高層大地震：AGI 負責人休假、COO 轉任特殊專案

---

## 🔀 委員間主要分歧

### 分歧 1：Anthropic 收費牆影響範圍
- **coding-ai-scout**：🔴 高危 — 影響所有 Claude Code + 第三方工作流
- **agentic-architect**：🟡 觀察 — Pi extension 不受影響
- **主席裁決**：短期影響有限，但 Anthropic 方向明確——**盈利壓力下的 lock-in**。API 層面是否跟進是關鍵監控點。

### 分歧 2：Gemma 4 本地部署優先級
- **eval-engineer**：🟢 立即採用 — 零成本 eval baseline，2hr 可完成
- **agentic-architect**：🟡 觀察 — 等社區 benchmark
- **主席裁決**：**先跑 3 個真實 task 的 head-to-head baseline 再決定**。無 benchmark 不換模型。

### 分歧 3：Agent 安全對策方向
- **coding-ai-scout**：🔴 框架安全脆弱，需大幅加固
- **agentic-architect**：🟡 單 agent + tool scope 已是最好的安全邊界
- **主席裁決**：不要用複雜框架換取安全感。單 agent + 明確 scope + human checkpoint 足夠。

---

## Current System Review

**做對了什麼**：
- ✅ ai-tools-board 全 glm-5-turbo，零 Claude 依賴 — Anthropic 收費牆完全免疫
- ✅ 多 provider 策略 — Claude/Gemini/DeepSeek 可切換
- ✅ 單 agent + 明確 tool scope — 最簡安全邊界

**哪裡缺失**：
- ❌ 無本地 eval pipeline — 每次換模型都是「賭博」
- ❌ 無不同意見校驗機制 — cognitive surrender 風險
- ❌ Scout 層 glm extraction 品質未量化

**哪裡過度複雜**：
- 無。當前架構簡潔度合適。

---

## Recommended Architecture

**最簡方案（維持現狀 + 一個補丁）**：
```
Scout (glm-5-turbo) → Director synthesis (Claude/Gemini)
                         ↑ 新增：不同意見校驗（codex:review 模式）
```
成本不變，安全 +1。

**平衡方案（eval 基礎設施）**：
```
Scout (glm) + Gemma 4 local fallback
    ↓
Eval pipeline (3 個真實 task head-to-head)
    ↓
Director synthesis (Claude → Gemini fallback)
```
+2hr 建置，獲得量化決策基礎。

**不建議**：多 agent 互操作（MCP/A2A 標準雖定稿但 Pi 不需）、升 Opus（5x 成本邊際不明顯）。

---

## Cost / Performance Tradeoff

| | 最省 💰 | 平衡 ⭐ | 最強 🚀 |
|---|---|---|---|
| **Scout** | glm ✅ 現狀 | glm + Gemma 4 eval | 全升 k2p5 |
| **Synthesis** | 降 Gemini | 維持 Claude | 升 Opus |
| **成本比** | **0.3x** | **1x** | **3-5x** |
| **建議** | 可行但無 eval | ✅ 推薦 | 邊際遞減 |

---

## Adopt Now / Watch / Ignore

### 🟢 立即採用
1. **codex-plugin-cc** — 免費第二意見 code review，與 Claude 互補
2. **Claude Code v2.1.92** — Write/Edit 60% 加速 + `/cost` breakdown
3. **Gemma 4 eval baseline** — 3 個真實 Pi extension task，零成本建立量化基礎

### 🟡 密切觀察
1. **Spud 進展** — 70-75% 機率 4/30 前發佈，可能顛覆性價比
2. **DeepSeek V4** — $0.30/MTok 如果效能達標，mid-layer 成本 -60%
3. **MCP + A2A v1.0** — 標準已定稿，Pi 需評估支援時機
4. **Claude Mythos** — 如上線可能改變 synthesis 層選擇

### 🔵 暫時忽略
- OpenAI 收購 TBPN、融資新聞、新 TUI 工具（cmux/ctux/leo）
- 大部分中腰部 startup 動態

---

## 下一步行動

1. **建立 Gemma 4 local eval baseline**（2hr）— 3 個 Pi extension task，測 success rate vs Sonnet
2. **量化 glm-5-turbo extraction 品質**（1hr）— 用 k2p5 做 judge，測 10 個 scout task
3. **Pi extension 權限隔離審計**（1hr）— 確認 tool scope 邊界清晰
4. **安裝 codex-plugin-cc**（15min）— 獲得免費 adversarial review
5. **準備 DeepSeek V4 評估框架**（等上線）— $0.30/MTok 可能重設定價地板

---

## 值得追蹤的核心趨勢

1. **Walled Garden vs 拆牆** ⬆️：Anthropic lock-in vs OpenAI 生態滲透，定義下一階段競爭
2. **安全攻守失衡** ⬆️（新）：AI 自主 exploit 量產化 + cognitive surrender + MCP 66% 有安全問題
3. **Agent 雙協議標準** ⬆️（新）：MCP + A2A v1.0 = agent 互操作的「HTTP 時刻」
4. **模型能力溢出** ➡️：四線 frontier model，但成本敏感場景受益者是開源/低成本模型
5. **專用模型時代** ⬆️（新）：gpt-5.3-codex 出現，coding agent 走向模型特化

---

## 委員會運作模式

### 2026-04-06 第三次全委員會議（最終版）
- 8 位委員全部提交報告（+eval-engineer, cost-performance-analyst）
- 數據品質：GitHub API ✅ + 新聞交叉引用 ⚠️ + WSP-V3 ❌
- 3 處跨委員分歧，均完成主席裁決
- **新增**：eval pipeline 建議、cost model layering 分析

### 過往討論摘要

| 日期 | 議題 | 結論 | 後續行動 |
|------|------|------|---------|
| 2026-04-06 | AI 產業 48hr 全面掃描 v3 | Anthropic walled garden vs OpenAI 拆牆、AI 安全攻守失衡、四線 frontier model 同時曝光、MCP+A2A v1.0 定稿；Gemma 4 eval baseline 為最高 ROI 行動 | Gemma 4 eval baseline、glm extraction 品質量化、Pi 權限審計、codex-plugin-cc 安裝、DeepSeek V4 評估框架準備 |
| 2026-04-02 | AI 產業 48hr 全面掃描 v2 | 洩漏連鎖72hr、Agent Plugin OS 共識、Sora 死亡+Grok Imagine 盈利證明新商業模式；Spud 懸而未決是最大變數 | 研究AutoDream記憶架構、評估Gemini CLI sandbox為安全標準、監控MCP跨agent plugin、追蹤Lyria 3對Suno衝擊、建立LiteLLM替代方案評估 |
