# System Analyst — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 system-analyst-sources.md。

## 2026-04-02 第 2 次全委員會議 — System Analyst 最終報告（v3）

### 🔥 三大核心信號（System Analyst 裁決）

#### 信號 1：AI 產業「潮浪高度分化」— 不是全面泡沫，而是生態位重組

**事實層**：
- Q1 2026 全球創投 $297B 歷史紀錄，但 63% 集中在 4 筆巨型交易 [src:032]
- OpenAI $122B（估值 $852B）、Anthropic $30B（估值 $380B）吸走絕大多數資金 [src:004][src:035]
- Yupp 拿了 $33M 後不到一年倒閉 [src:010]
- Oracle 同日裁員 30,000 人轉向 AI（主席報告補充）

**System Analyst 評估**：
資本市場正在做一件事：**把中腰部 startup 的氧氣抽給巨頭**。這不是「AI 泡沫破裂」，而是「泡沫結構化」——資金不再灑胡椒面，而是集中押注能贏的玩家。對用戶系統的意義：pi-vs-claude-code 處於「開源 agent 框架」生態位，這個位置目前仍有空間，但窗口期可能在 6-12 個月內收窄。

#### 信號 2：Agent OS 化 + 安全信任鏈崩塌 — 技術進步與治理落後的致命落差

**事實層**：
- 48hr 內五大 agent（Claude Code、Gemini CLI、Codex、Goose、OpenClaw）同步模組化（主席報告）
- LiteLLM 供應鏈攻擊 → Mercor 數千家公司受害 → Lapsus$ 勒索介入 [src:021][src:033]
- Delve 被揭發盜用開源工具當自研產品，違反 Apache 授權 [src:034]
- Pliny the Liberator 將 jailbreak 工具轉為 private（coding-ai-scout 報告）
- Anthropic DMCA 誤刪 8,100 個 repo [src:028]

**System Analyst 評估**：
技術層面，agent 正在從「工具」變成「作業系統」——plugin layer 成為新戰場。但治理層面完全跟不上：LiteLLM 事件證明開源 AI infra 的信任鏈極度脆弱，DMCA 誤殺事件證明大廠的法律武器化風險。**這是一個「先蓋摩天大樓再打地基」的產業**。對用戶系統的意義：任何依賴外部 AI gateway 或未審計開源依賴的工作流，都需要立即進行安全審計。

#### 信號 3：Sora 死亡 + 分發渠道勝出 — AI 產品從「獨立工具」轉向「平台嵌入」

**事實層**：
- OpenAI 關閉 Sora，全壽命僅賺 $2.14M，日均燒損 $1M（主席報告數據）
- Disney 隨之取消 $1B OpenAI 投資 [src:006]
- Grok Imagine 30 天 55 億生成量、正毛利——「平台嵌入 + 免費」打敗「獨立付費」（主席報告）
- Google Lyria 3 Pro 嵌入 Google 生態（music-ai-scout 報告）

**System Analyst 評估**：
Sora 的死亡不是影片 AI 的失敗，而是**「獨立 AI 產品」商業模式的失敗**。當影片生成成本降到接近零（Grok Imagine 證明），獨立定價就失去意義——獲勝的是能將 AI 嵌入現有分發渠道的玩家（X、Google、Netflix）。這對所有 AI 工具創作者都是警訊：如果你在做獨立 AI 產品，你需要一個平台護城河。

---

### 🔀 跨領域連結（System Analyst 特有視角）

| 連結 | 說明 |
|------|------|
| **Claude Code 洩漏 → 所有 AI 工具** | Agent 架構知識民主化意味著競品進入門檻大幅降低，48hr 內湧現的 10+ 分析專案就是證明。這會加速所有 AI 工具領域的開源競爭 |
| **LiteLLM 事件 → 用戶技能生態** | 用戶的 `.claude/skills/` 和 `.pi/` 架構目前直接調用 API，不經過 LiteLLM。**已確認**：investment-adviser-board 和其他 board 均無 LiteLLM/Delve 相關依賴 ✅ |
| **Sora 死亡 → 音樂/影片 AI** | 「模型層商品化」趨勢確認：影片模型（Sora→Veo/Kling）和音樂模型都將趨向利潤趨零。差異化不在模型本身，而在分發渠道和後生成編輯體驗 |
| **Oracle 裁員 30,000 → AI 工具採用** | 傳統工程師被替代加速，意味著 AI coding 工具的市場會持續擴大，但同時也意味著「會用 AI 工具」從競爭優勢變成基本門檻 |
| **Claw Code 123K stars → 開源 agent 標準化** | 48hr 內從 0 到 123K+ stars + 102K forks，史上最快。Rust 實作證明「高性能 agent」是市場真實需求。這意味著 agent 工具的性能基線正在被快速拉高 |
| **OpenClaude → 模型無關化** | Claude Code 開放至 200+ 模型的 shim 層出現，說明「agent harness 與 LLM 解耦」已成為社群共識 |

---

### 📋 對用戶系統的具體建議

| 優先級 | 行動 | 預估成本 | 說明 |
|--------|------|---------|------|
| **P0** | 審計所有 board 的外部依賴 | ✅ 已完成 | 確認無 LiteLLM/Delve 依賴，系統安全 |
| **P0** | 研究 AutoDream/Kairos 記憶架構 | 1 天 | 參考 `claude-code-from-scratch`（541 stars）和 `how-claude-code-works`（949 stars），評估跨 session 持久化的可行方案 |
| **P0** | 追蹤 AutoHarness 專案 | 持續 | 2026-04-02 剛建立，Agent Harness 自動化工程，與用戶系統直接相關 [src:045] |
| **P1** | 整合 Ollama MLX | 2 小時 | 直接可用，Mac 本地模型加速，提升測試效率 |
| **P1** | 監控 Gemini CLI sandbox 架構 | 持續 | Gemini CLI v0.36.0 的三平台原生 sandbox 可能成為 agent 安全標準 |
| **P1** | 評估 OpenClaude shim 方案 | 3 小時 | 模型無關化對 pi-vs-claude-code 的 multi-agent 架構有直接參考價值 [src:046] |
| **P2** | 評估 MCP 協議整合 | 1 週 | Codex 獨立抽出 `codex-mcp` crate，MCP 正成為跨 agent 互通事實標準。Pi extension 是否需要 MCP 支援？ |
| **P2** | 建立 WSP-V3 替代研究管線 | 3 天 | WSP-V3 持續不可用嚴重影響委員會研究能力，需要建立備用方案（如 GitHub Trending API + HN API） |
| **P2** | 評估 cc-gateway 隱私方案 | 2 小時 | API 指紋隱藏 gateway，對需要 API 代理的場景有參考價值 [src:047] |

### 🏥 系統健康檢查（更新）

| 項目 | 狀態 | 備註 |
|------|------|------|
| WSP-V3 研究工具 | 🔴 不可用 | 嚴重影響委員會運作，需立即建立替代方案 |
| 外部依賴安全 | 🟢 已審計 | 確認無 LiteLLM/Delve 依賴，系統安全 |
| Board 架構現代化 | 🟡 可改進 | AutoDream 記憶架構 + AutoHarness 提供了升級路線圖 |
| 開源 agent 生態追蹤 | 🟢 正常 | GitHub Trending + 委員會分工運作良好 |
| 本地推理能力 | 🟡 可提升 | Ollama MLX 整合後可大幅改善 |

---

## 2026-04-02 第 2 次全委員會議 — 增量更新（保留）

### 🔥 48 小時內最關鍵的新信號（System Analyst 觀點）

#### 1. Claude Code 洩漏 72hr 演變：開源生態爆發式成長 [src:028][src:029][src:030]
- **8,100 個 repo 被 DMCA takedown**，Anthropic 事後承認「意外」，已撤回大部分通知，僅保留 1 repo + 96 forks [src:028]
- **開源社群反制力道驚人**：洩漏後 48hr 內湧現大量分析專案——
  - `openedclaude/claude-reviews-claude`：Claude 讀自己的源碼，17 章中英雙語架構深度剖析，1,009 stars [src:029]
  - `lintsinghua/claude-code-book`：42 萬字拆解 AI Agent 架構，15 章完整教程，1,004 stars [src:029]
  - `Leonxlnx/agentic-ai-prompt-research`：研究 agentic AI 的 prompt 模式與安全隱患，1,763 stars [src:029]
  - `tvytlx/ai-agent-deep-dive`：AI Agent 源碼深度研究，3,194 stars（最熱門）[src:029]
- **系統分析**：洩漏的代碼已成為開源社群的「AI Agent 教科書」。Kairos/AutoDream 架構被大量拆解分析，這大幅降低了競品實作類似功能的門檻。**對用戶系統的直接影響**：這些開源分析專案是學習 agent 架構的極佳資源，建議參考 `how-claude-code-works` 和 `claude-code-from-scratch` 來改進 pi-vs-claude-code 的 board 架構。
- **Claude 撰寫 FreeBSD 遠端 kernel RCE**：HN 上 254pts 的熱門貼文，Claude 成功找到並撰寫 FreeBSD kgssapi.ko 的完整遠端權限提升漏洞利用（CVE-2026-4747）[src:031]。這顯示 AI coding 工具已能獨立完成安全研究級任務。

#### 2. Q1 2026 創投市場：史詩級泡沫還是新紀元？ [src:032]
- **全球 Q1 創投達 $297B，打破歷史紀錄**，較 Q4 2025 的 $118B 成長 2.5 倍
- **4 筆巨型交易佔 $188B（63%）**：OpenAI $122B、Anthropic $30B、另外兩筆未知（可能是 xAI 或其他）
- AI seed 階段 startup 正在「commanding bigger dollars and higher valuations」
- **系統分析**：資金高度集中在前 4 筆交易，**頭部效應極端化**。Yupp $33M 融資後不到一年倒閉 [src:010] 與此同時發生，形成強烈對比。這不是「潮退」而是「潮浪高度分化」——巨頭拿到史無前例的資金，但中腰部 startup 生存壓力加劇。
- **對用戶系統的影響**：用戶的 pi-vs-claude-code 作為 agent 基礎設施實驗倉庫，正好處於「開源 agent 框架」這個蓬勃發展的生態位。

#### 3. LiteLLM 供應鏈事件升級：Delve 醜聞 + Lapsus$ 介入 [src:033][src:034]
- **LiteLLM 惡意代碼事件的連鎖反應擴大**：Mercor 確認成為「數千家公司」之一受害 [src:033]
- **Lapsus$ 勒索集團介入**：聲稱取得 Mercor 資料，包含 Slack 對話錄影和 AI 系統與承包商的對話影片
- **Delve 醜聞升級**：匿名吹哨人 DeepDelver 揭露 Delve（LiteLLM 母公司）將開源工具 Sim.ai 的 SimStudio 改裝後當作自研產品 Pathways 銷售，違反 Apache 授權。Delve 的網站多個頁面已下線，媒體聯絡方式失效 [src:034]
- **系統分析**：這是一起**「合規公司違反合規」**的典型諷刺案例。Delve 作為 LiteLLM 的合作方，其治理問題進一步動搖了 LiteLLM 生態的信任基礎。
- **對用戶系統的影響**：如果用戶的任何工作流依賴 LiteLLM 作為 AI gateway，需要評估替代方案（如直接調用 API 或使用其他 gateway）。

### 📊 新增融資 / 市場數據

| 事件 | 關鍵數字 | 來源 |
|------|---------|------|
| **全球 Q1 2026 創投** | $297B（歷史紀錄），較 Q4 成長 2.5x | [src:032] |
| **OpenAI 最新營收** | 月收入 $2B，2025 年總收入 $13.1B（仍未獲利） | [src:035] |
| **OpenAI ChatGPT 用戶** | 5,000+ 萬訂閱用戶 | [src:035] |
| **Anthropic Claude 消費者受歡迎度** | 付費用戶人數「skyrocketing」 | [src:036] |
| **Mercor** | $350M Series C（2025/10），日處理 $2M+ 支付，被 Lapsus$ 入侵 | [src:033] |
| **Mercor 合作夥伴** | 與 OpenAI 和 Anthropic 合作訓練 AI 模型 | [src:033] |

### ⚖️ 新增政策法規 / 安全動態

| 事件 | 關鍵點 | 來源 |
|------|--------|------|
| **法官阻止政府封鎖 Anthropic** | 國防部長 Hegseth 和川普無權將 Anthropic 列入黑名單 | [src:011] |
| **Reddit 強制人機驗證** | 「可疑帳號」需驗證真人身份，針對 AI bot 泛濫 | [src:037] |
| **Apple DarkSword 修補** | 針對已洩漏的強大駭客工具組，影響 iOS 18.4-18.7 用戶 | [src:038] |
| **Dolby 起訴 Snapchat** | AV1 開源免費承諾受質疑 | [src:039] |
| **DOJ 確認 FBI 局長個人 email 被黑** | Kash Patel 的個人 email 遭入侵 | [src:040] |
| **百度無人計程車癱瘓** | 武漢 100+ 輛 robotaxi 突然凍結，乘客被困最長 2 小時 | [src:041] |
| **Oracle 裁員 30,000 人** | 轉向 AI，傳統工程師被替代加速 | 主席報告 |

### 🏢 新增商業動態

| 事件 | 關鍵點 | 來源 |
|------|--------|------|
| **Sora 關閉** | 全壽命僅賺 $2.14M，日均燒損 $1M，成本收入比 100:1 | 主席報告 + [src:005] |
| **Grok Imagine 盈利** | 30 天 55 億生成量、正毛利，「平台嵌入+免費」勝出 | 主席報告 |
| **Netflix 收購 InterPositive** | Ben Affleck 的 AI 影片製作公司 | [src:017] |
| **Salesforce Slack AI 大改版** | 30 項新功能，全面 AI 化 | [src:018] |
| **Cloudflare EmDash** | AI agent 從零重建 WordPress，插件安全沙盒化 | [src:042] |
| **Claude Code Agent 觀測工具** | `agents-observe`：多 agent 即時監控 dashboard | [src:043] |

### 🔗 開源生態更新

| 專案 | Stars | 說明 | 來源 |
|------|-------|------|------|
| `ultraworkers/claw-code` | 123,789 | 史上最快到 100K stars，Rust agent，102K forks | [src:044] |
| `tvytlx/ai-agent-deep-dive` | 3,218 | AI Agent 源碼深度研究（最熱門分析） | [src:029] |
| `Gitlawb/openclaude` | 3,743 | Claude Code 開放至 200+ 模型（OpenAI/Gemini/DeepSeek/Ollama） | [src:046] |
| `Leonxlnx/agentic-ai-prompt-research` | 1,765 | Agent prompt 模式 + 安全研究 | [src:029] |
| `openedclaude/claude-reviews-claude` | 1,010 | Claude 自評源碼，17 章雙語 | [src:029] |
| `lintsinghua/claude-code-book` | 1,011 | 42 萬字拆解，15 章教程 | [src:029] |
| `Windy3f3f3f3f/how-claude-code-works` | 949 | Claude Code 內部架構深度解析 | [src:029] |
| `Windy3f3f3f3f/claude-code-from-scratch` | 541 | ~1300 行 TypeScript 從零構建 Claude Code | [src:029] |
| `motiful/cc-gateway` | 1,752 | AI API 身份 gateway，反向代理隱藏設備指紋 | [src:047] |
| `aiming-lab/AutoHarness` | 7 | Agent Harness 自動化工程（2026-04-02 新建，需追蹤） | [src:045] |
| OpenClaw | 344K | v2026.4.1 突破 344K stars | [src:027] |

---

## 用戶系統地圖（最新）

### 核心系統
- **pi-vs-claude-code**：Pi coding agent 擴充實驗倉庫
  - extensions/：Pi 擴充模組（.ts）
  - .pi/：agent 定義、主題、boards
  - .claude/：技能、指令、記憶、agent 定義

### 已知技術債 / 痛點
- 🔴 WSP-V3 研究工具不可用，降低了委員會新聞掃描能力
- ⚠️ Claude Code 洩漏事件顯示源碼安全風險
- 🟢 外部依賴安全已審計通過（無 LiteLLM/Delve 依賴）
- 🟡 Board 架構缺少跨 session 記憶持久化（AutoDream 概念可參考）

### 整合機會記錄

| 日期 | 工具 | 整合可行性 | 優先級 | 備註 |
|------|------|-----------|-------|------|
| 2026-04-02 | Ollama MLX | 直接可用 | **P1** | Mac 用戶立即受益，可整合至 local testing workflow |
| 2026-04-02 | `agents-observe` | 直接可用 | **P1** | Claude Code 多 agent 即時監控 dashboard |
| 2026-04-02 | `claude-code-from-scratch` | 參考學習 | **P1** | ~1300 行從零構建 agent，架構參考價值極高 |
| 2026-04-02 | Kairos/AutoDream 概念 | 需研究 | **P0** | 記憶整合模式可應用於 board system 的跨 session 持久化 |
| 2026-04-02 | AutoHarness | 需追蹤 | **P0** | Agent Harness 自動化，與用戶系統直接相關 |
| 2026-04-02 | OpenClaude shim | 需研究 | **P1** | 模型無關化對 multi-agent 架構有參考價值 |
| 2026-04-02 | cc-gateway | 需評估 | **P2** | API 指紋隱藏 gateway |
| 2026-04-02 | TurboQuant (Google) | 需適配 | P2 | 本地模型壓縮，6x 記憶體降低 |
| 2026-04-02 | Codex MCP crate | 需研究 | P2 | MCP 協議成跨 agent 互通標準，Pi 是否需要支援？ |
| 2026-04-02 | Gemini CLI sandbox | 需研究 | P1 | 三平台原生 sandbox 架構，可能成為 agent 安全標準 |
| 2026-04-02 | Mozilla C/Q | 需觀察 | P3 | Agent 知識共享平台，概念階段 |
| 2026-04-02 | Cloudflare EmDash | 需觀察 | P3 | 插件沙盒化架構值得借鑑 |
