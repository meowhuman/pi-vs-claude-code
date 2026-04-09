# Coding AI Scout — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 coding-ai-scout-sources.md。

---

## 📰 2026-04-06 第 2 輪掃描（第 3 次全委員會議）：Agent 互操作 + 平台戰

### 🔴 信號十（重大）：OpenAI 官方 Codex Plugin for Claude Code — 跨平台互操作範式確立 [src:066][src:067][src:068]

**事件**：OpenAI 釋出官方 `openai/codex-plugin-cc`（**11,910 stars / 2 天**），讓 Claude Code 用戶可以直接在 Claude Code session 內呼叫 OpenAI Codex 進行 code review 和 adversarial testing。

**安裝**（3 條指令）：
```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins → /codex:setup
```

**三個核心命令**：
- `/codex:review` — 只讀 code review（第二意見）
- `/codex:adversarial-review` — 壓力測試，專抓 Claude 自己漏掉的 bug
- `/codex:rescue` — 任務委託/接手（可背景執行，Claude 同時繼續工作）

**社群反應**（極度正面）：
- @MakeAI_CEO（日本）：「OpenAI 自らAnthropicの軍門に下った？いや、実態はもっと戦略的だ。Claude Code は GitHub コミット全体の 4% を担い、年収益 25 億ドル。無視できないエコシステム。」
- @LyashchMaxim：「Claude Code found the bugs it introduced itself. Codex caught them in one review pass. The weakness of each model is basically the strength of the other.」
- @justic_hot：「the #5 post on HN right now is a Claude Code plugin that makes the AI talk like a caveman. to save tokens. same week OpenAI moved Codex to pay-per-token. we hit the 'AI coding actually costs money' phase.」
- @Timur_Yessenov：「openai open-sourced a codex plugin for claude code. so now you can run openai agents inside anthropics tool. the moat is disappearing faster than people realize.」

**關鍵數據**：
- Claude Code 承擔 GitHub 整體 commits 的 4%（每日 135,000 次貢獻），年化收入超過 $2.5B
- Codex review 部分用 **ChatGPT 免費方案即可使用**，不需付費 API

**解讀**：這是 coding agent 產業的**互操作性里程碑**。OpenAI 不是在承認失敗，而是在執行精準的生態滲透——「你用 Claude Code 沒關係，但我保證你一定也會用 Codex」。與 Anthropic 封殺 OpenClaw 形成強烈對比：**OpenAI 在拆牆，Anthropic 在築牆**。已有第三方開始做 gemini-plugin-cc（Gemma 進 Claude Code），跨平台插件生態正在形成。

**對 Pi 的影響**：Pi 的 extension 系統應考慮支援類似的「外部位 provider 注入」模式。不需要自己造模型，但可以成為**統一的 agent 調度層**。

### 🔴 信號十一（重大）：MCP + A2A 雙協議 v1.0 同時定稿 — Agent 標準戰實質化 [src:069]

**事件**：在 MCP Dev Summit 上，**MCP（Model Context Protocol）** 和 **A2A（Agent-to-Agent Protocol）** 同時宣布 v1.0。

**關鍵數據**：
- **146 個成員組織**
- **每月 9700 萬次 SDK 下載**
- MCP + A2A 雙協議架構確立

**解讀**：Agent 工具層正在快速標準化。MCP 管工具調用，A2A 管跨 agent 通訊。這對 Overstory 的 SQLite mail system 構成替代壓力——如果 A2A 成為標準，自建通訊機制就變成技術債。Gemini CLI v0.36.0 已原生支援 A2A [src:017]。

**與 OpenClaw 訂閱封殺的關聯** [src:049]：Anthropic 封殺第三方 harness 的策略，與 MCP/A2A 開放標準形成矛盾。MCP Dev Summit 的 146 家成員中有多少會被 Anthropic 的 walled garden 排擠？這是觀察重點。

### 🔴 信號十二（升級）：Cursor 3 發佈 — 直接挑戰 Claude Code [src:070][src:071]

**事件**：Cursor 發佈 Cursor 3，定位為「simpler and more powerful for the agent code era」，推出 multi-agent orchestration 功能。

**關鍵引述**（@ShabbatMonster）：「claude code was so viral and a competitor being created by cursor is insane. its getting tweeted every minute.」

**與前次 Automations 的疊加**：Cursor 在一週內同時推出 Automations（事件驅動）+ Cursor 3（multi-agent 編排），從 IDE 廠商正式轉型為 agent 平台。

**對 Overstory 的影響**：Cursor 3 的 multi-agent orchestration 直接與 Overstory 競爭，但 Cursor 的優勢在於已有大量用戶基礎。Overstory 的差異化在於 CLI-first 和跨 runtime adapter（Claude Code + Pi + Codex 等），而 Cursor 3 只在自己的 IDE 內運行。

### 🟡 信號十三（新）：Claude Code v2.1.91 + v2.1.92 — 快速迭代修復 [src:072][src:073]

**v2.1.91（04-03）關鍵變更**：
- MCP tool result 持久化覆蓋（`_meta["anthropic/maxResultSizeChars"]`，最高 500K chars）
- `disableSkillShellExecution` 設定——禁用 skills 中的 inline shell 執行（安全加固）
- Plugins 可在 `bin/` 下附帶可執行檔，Bash tool 可直接呼叫
- `--resume` 修復（transcript chain breaks 不再丟失歷史）
- Edit tool 使用更短的 `old_string` anchors，減少 output tokens
- Bun 原生 `Bun.stripANSI` 加速

**v2.1.92（04-04）關鍵變更**：
- **Bedrock 互動式設定精靈**（login screen 選 3rd-party platform）
- `/cost` 現在顯示**每個模型的 breakdown**（含 cache hit）——對成本追蹤極有用
- **Write tool diff 計算速度提升 60%**（大檔案含 tabs/&/$）
- `forceRemoteSettingsRefresh` policy（fail-closed 安全設定）
- Remote Control session 名稱使用 hostname prefix
- Pro 用戶在 prompt cache 過期後看到 footer hint（下次 turn 需重新傳送多少 tokens）
- 移除 `/tag` 和 `/vim`（併入 `/config`）

**解讀**：Claude Code 在洩漏後進入密集修復期。v2.1.91 的安全加固（disableSkillShellExecution、forceRemoteSettingsRefresh）和 v2.1.92 的 Bedrock 精靈顯示 Anthropic 在同時推進企業部署和安全性。Write/Edit 60% 速度提升直接改善日常開發體驗。

### 🟡 信號十四（新）：Claude Chat 互動式圖表 — Beta 上線所有方案 [src:074][src:075]

**事件**：Claude 新增**互動式圖表/圖表生成功能**，beta 階段，所有方案（含免費）可用。圖表直接在聊天中渲染，支援資料視覺化、職涯規劃、3D 解釋等。

**與 Anthropic 16 天內 5 大產品更新的關聯**：
1. 07/03：Claude Code auto mode（自主執行，不需逐步許可）
2. 12/03：互動式視覺化（mobile 也支援）
3. 13/03：1M context window
4. 17/03：Dispatch（手機派任務，桌面完成）
5. 23/03：Computer Use（Claude Code 可操控桌面）

**解讀**：Anthropic 正在快速拓展 Claude 從「純文字助手」到「多模態工作伙伴」。對 coding 的間接影響：未來 agent 可能直接在聊天中生成架構圖、流程圖、性能分析圖。

### 🟡 信號十五（新）：Codex CLI Rust port 密集迭代 — 4 天 11 個 alpha [src:076]

**事件**：OpenAI Codex CLI Rust 版在 4/3-4/4 四天內釋出 **11 個 alpha 版本**（v0.119.0-alpha.1 到 alpha.11），顯示 Rust port 進入收尾階段。

**背景**：Codex CLI 在上週突破 **73,304 stars**，Gemini CLI 則突破 **100,316 stars**（正式破 100K）。

### 🔵 Spud 動態更新：Polymarket 70-75% 機率 4/30 前發佈 [src:077][src:078]

**市場預期**：
- Polymarket：「GPT-5.5 by April 30」機率 70-75%；「by June 30」機率 94%
- Manifold：Spud 是否在 Anthropic Mythos 之前發佈
- 市場押注：**四月中下旬**

**社群爭論**：
- @slow_developer：「如果 Spud 真的比 GPT-5.4 好很多，為什麼只叫 5.5 不叫 6？」
- @aquiffoo（日期預測）：「GPT-5.5 + GPT-Image-2 by April 15, GPT-6 (Spud) by June. Claude 5 (Mythos), Gemini 3.5 Pro Preview, Grok 5 by June.」
- @acombo_yt：「leo said it's for sure going to be called gpt-5.5 (the next release, maybe it's not spud)」→ Spud 和 GPT-5.5 可能是不同產品

**解讀**：Spud 命名混亂持續——社群開始區分「GPT-5.5」（可能近期發佈的小升級）和「GPT-6 / Spud」（更大的跳躍）。無論如何，四月下旬是關鍵觀察窗口。

---

## 📰 2026-04-06（增量掃描）：AI 地緣政治 + 安全 + 產品三重震盪

### 🔴 信號一（升級）：Anthropic 封殺 OpenClaw 訂閱 — 平台鎖定戰開打 [src:049][src:050][src:051]

**事件**：4 月 4 日中午（Pacific），Anthropic 正式切斷 Claude Code 訂閱對第三方 harness（包括 OpenClaw）的支援。Claude Pro/Max 用戶不能再以訂閱額度使用 OpenClaw，必須轉為 pay-as-you-go 或使用 Claude Code Channels。Anthropic 提供一次性 credit（等值一個月訂閱）+ 折扣預付 bundle 作為緩衝。

**關鍵人物**：
- **Boris Cherny**（Anthropic Claude Code 負責人）：稱訂閱「不是為第三方工具的使用模式設計的」，承諾提供全額退款給不知情的用戶
- **Peter Steinberger**（OpenClaw 創辦人，已加入 OpenAI）：表示與 Anthropic 協商僅爭取到一周延遲
- 政策適用範圍不限 OpenClaw，涵蓋**所有第三方 harness**，更多 rollout 即將到來 [src:050]

**解讀**：這是繼 DMCA 誤殺事件後，Anthropic 對開源生態的又一次打擊。時機高度敏感——OpenClaw 創辦人 2 月加入 OpenAI。Anthropic 的官方理由是「工程限制」，但社群普遍認為這是競爭性封鎖。信號很清楚：**Anthropic 正在建立 walled garden，Claude Code 訂閱只涵蓋官方工具鏈**。

**對用戶的影響**：依賴 Claude Code + OpenClaw 的團隊成本模型瞬間改變。Overstory 等多 agent 編排框架如果以 Claude Code 為 runtime，也面臨成本飆升風險。

### 🔴 信號二（新）：Claude 自主突破 FreeBSD 核心漏洞 — AI 安全范式轉變 [src:052][src:053]

**事件**：研究人員 Nicholas Carlini 使用 Claude 發現了 FreeBSD 核心遠端程式碼執行漏洞 CVE-2026-4747（RPCSEC_GSS 模組 stack buffer overflow）。隨後，另一組研究人員讓 Claude 自主構建完整的 root shell exploit——**4 小時即完成**，期間人類幾乎全程 AFK。

Claude 自動解決了六個連續技術挑戰：
1. 搭建 FreeBSD VM + Kerberos + NFS 遠端環境
2. 設計 15 輪多封包 shellcode 傳遞策略（payload 不適合單封包）
3. 執行乾淨的 thread exit 保持伺服器存活
4. 從 crash dump 除錯核心 offset
5. 對 live remote target 驗證
6. 兩種不同的 exploit 策略，首次嘗試都成功

**更嚴重的是**：Carlini 隨後用同一 pipeline 自動生成了 **500 個驗證過的高嚴重性漏洞**，跨多個程式碼庫。這不是一次性事件，而是**可重複的進攻能力**。

**同週安全事件串聯** [src:054]：
- **Langflow** 成為首個被列入 CISA KEV（Known Exploited Vulnerabilities）清單的 AI agent 框架（CVE-2026-33017，CVSS 9.3），公開後 20 小時內被攻擊
- **CrewAI** 披露 4 個 CVE，含 Docker sandbox 逃逸
- **Adversa AI** 發現 93% agent 框架使用 unscoped API keys
- **AgentSeal**：1,808 個 MCP server 中 66% 有安全問題

**解讀**：AI agent 安全已從理論風險變為實際威脅。Claude 4 小時突破核心漏洞 vs 企業 patch cycle 以週計——攻守時差太大。對我們的意義：**Pi 的 extension 系統需要嚴格的權限隔離和安全審計**。

### 🔴 信號三（新）：DeepSeek V4 完全拋棄 NVIDIA — 華為 Ascend 獨立運行 [src:055][src:056]

**事件**：DeepSeek V4（~1T params，多模態，1M context）完全基於華為 Ascend 晶片開發，NVIDIA 和 AMD 被排除在早期測試之外。阿里巴巴、字節跳動、騰訊已預訂數十萬顆華為晶片。訓練成本僅 $5.2M。定價 $0.30/MTok（coding）。

**關鍵意義**：
- 美國出口管制政策被實質性突破
- 中國 AI 生態與西方硬體正式解耦
- 數週內即將發佈

### 🟡 信號四（新）：GPT-Image-2 洩漏 + 灰度測試 — OpenAI 圖像生成大躍進 [src:057][src:058][src:059]

**事件**：OpenAI 的下一代圖像生成模型 GPT-Image-2 在 LMArena 上以 codenames（maskingtape-alpha、gaffertape-alpha、packingtape-alpha）洩漏，隨後 ChatGPT 開始對部分用戶進行 A/B 測試。

**社群反應**：
- 文字渲染能力大幅提升，「曲面上的文字也不崩」
- 寫實性達到「與實拍無法區別」的水準
- 在盲測中擊敗 Nano Banana Pro（此前圖像生成 SOTA）
- 日本語等多語言支援改善
- 部分 A/B 測試用戶未能觸發，品質不一致
- 一位開發者稱其 UI 生成能力「crazy」，甚至可以 live 生成 app UI

**解讀**：GPT-Image-2 正式發佈迫在眉睫。這不僅是圖像工具的升級，更重要的是**對 UI/UX 設計工作流的衝擊**——未來 coding agent 可能直接生成介面視覺稿。

### 🟡 信號五（新）：OpenAI CFO 對 $600B 基礎設施支出表達擔憂 [src:060]

**事件**：OpenAI CFO Sarah Friar 據報對公司未來 5 年 $6000 億的基礎設施支出計畫「表達擔憂」。此消息在 PolymarketMoney 上爆出，引發廣泛討論。

**背景脈絡**：OpenAI 剛完成 $122B 融資（$852B 估值），月收入約 $2B，2026 年底前 IPO。$600B 基礎設施支出計畫與財務現實之間的巨大缺口，加上 CFO 的公開擔憂，暴露了 AI 算力軍備競賽的財務可持續性問題。

### 🟡 信號六（新）：OpenAI + Guardian Media Group 內容合作夥伴 + OpenAI for Greece [src:061][src:062]

**事件**：OpenAI 持續擴大媒體合作版圖：
- 與英國 Guardian Media Group 簽署內容合作夥伴關係
- 與希臘政府聯合推出「OpenAI for Greece」計畫

**解讀**：OpenAI 在 IPO 前積極建立內容授權關係，同時向各國政府拋出合作計畫。這是平台化戰略的一部分——與 Google 搜索的廣告模式不同，OpenAI 走的是「AI 基礎設施國家合作」路線。

### 🟡 信號七（新）：Meta TRIBE v2 — 大腦預測基礎模型開源 [src:063]

**事件**：Meta FAIR 釋出 TRIBE v2（Trimodal Brain Encoder），一個基礎模型能預測人類大腦對幾乎任何視覺/聽覺/語言刺激的反應。基於 1,000+ 小時 fMRI 資料、720+ 志願者訓練，支援 zero-shot 預測。已開源（非商業授權）。

**解讀**：這是神經科學的重大工具，但對 coding agent 的直接影響有限。長期來看，如果大腦反應預測能指導 AI UI/UX 設計，可能間接影響開發者工具。

### 🟡 信號八（新）：Stargate 阿布達比資料中心遭伊朗威脅 [src:064]

**事件**：伊朗 IRGC 中校 Ebrahim Zolfaghari 發布影片，威脅若美國打擊伊朗電網，將攻擊 OpenAI 在阿布達比的 $30B Stargate AI 資料中心（G42/OpenAI/Microsoft/Nvidia/Apollo 合建，1GW，屬 5GW 計畫的一部分）。

**解讀**：AI 基礎設施正在成為地緣政治目標。Stargate 資料中心的首期 200MW 預計 2026 年上線。這不僅是安全問題，也是 AI 供應鏈韌性的新維度。

### 🔵 信號九（新）：Google Gemma 4 開源 + NVIDIA FP4 量化版 [src:065]

**事件**：Google 開源 Gemma 4（4 個尺寸：Pico、Nano、Pro、Ultra，Apache 2.0，256K context，140+ 語言），NVIDIA 隨即發布 31B 模型的 FP4 量化版（~4x 更小權重），支援本地推理。

**社群反應**：
- @arsh_goyal：「Gemma 4 ranked third globally across all models, outperforming models literally double its size」
- @frontierbeat：「400M+ downloads since Gemma 1. The open-source AI race just got serious.」
- @rebelcrayon：「open source/local models might soon be competent for many tasks going to frontier models」

**解讀**：Gemma 4 將 Gemini 3 技術開源化，加上 NVIDIA 的量化優化，使本地部署前沿模型的門檻大幅降低。RTX 3090 即可跑出 100+ tok/s。直接回答了 DeepSeek V4 和 Qwen 的開源競爭。

### 🔵 雜訊（本輪）

- **NVIDIA PersonaPlex 7B 開源**：即時語音對話模型，支援中斷和重疊，對 coding 無直接影響 [src:079]
- **crag CLI**（@Whitehat_D）：一個 20 行設定檔編譯成 12 個 AI coding 工具的配置（.cursorrules、Copilot、Gemini、Cline 等），SHA-verified deterministic，零依賴 [src:080]
- **Prompt Line**（nkmr-jp）：macOS app 改善 CLI AI agent 的 prompt 輸入體驗 [src:081]
- **LunaRoute**（erans）：Claude Code / Codex / OpenCode 的本地 proxy，提供完整 LLM 互動可見性 [src:082]

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

### 🔵 雜訊（第 2 次會議）

- **Meta Hyper Agents**：開源自進化 AI agent [src:027]，但缺乏技術細節，暫列觀察
- **Gemini Flash 3.1 Lite**：已在 Gemini CLI v0.37.0-preview 中以 experiment flag 出現，但未正式發佈
- **Google 多模態大更新**：Gemini real-time audio、Lyria 3 音樂、Veo 3.1 Lite 視頻 [src:029] — 對 coding agent 影響有限
- **vishalojha_me Claude Code 架構分析**（12-part thread）：公開了 scratchpad（專屬思考空間）和 memdir（flat file 記憶系統）等架構細節，來自洩漏的 source map [src:048]

---

## 📊 工具最新數據快照（2026-04-06 GitHub API 驗證）

| 工具 | Stars | 4/2→4/6 變化 | 狀態 |
|------|-------|-------------|------|
| OpenClaw | 349,035 | +4,320 | Anthropic 切斷訂閱支援 |
| Claw Code | — | 未更新追蹤 | Rust 重寫中 |
| Claude Code | 109,378 | +7,852 | v2.1.92（4 天 2 版） |
| Gemini CLI | 100,316 | +408 | 🎉 **突破 100K** | v0.36.0 stable / v0.37.0-preview |
| OpenAI Codex CLI | 73,304 | +1,470 | Rust v0.119.0-alpha.11（11 alphas/4天） |
| Cursor | 32,550 | — | Cursor 3 + Automations |
| NanmiCoder/claude-code-haha | 3,072 | 穩定 | 未被 DMCA |
| Overstory | ~1,187 | +25 | Pi experimental |
| codex-plugin-cc | 11,910 | 新（2天） | 跨平台互操作範例 |
| everything-claude-code | 140,507 | — | Claude Code 技能合集 |
| system-prompts | 134,471 | +440 | AI 工具 system prompts |

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

**對 Pi Agent 的意義**：Pi 被視為一等公民 runtime，in-process extension 能力可能比 Claude Code hooks 更適合 orchestration。⚠️ Anthropic 封殺第三方 harness 可能影響 Claude Code adapter 的成本。

### codex-plugin-cc — 跨平台互操作範例（2026-04-06 新增）[src:066]

**概述**：OpenAI 官方釋出的 Claude Code plugin，允許在 Claude Code session 內直接使用 Codex。安裝後提供 /codex:review、/codex:adversarial-review、/codex:rescue 三個命令。

**戰略意義**：證明跨 provider agent 互操作的可行性。開啟了「Claude Code 作為 agent 總線」的可能性——不同模型在不同任務上各有優勢，統一在一個 CLI 內調度。

**潛在風險**：Anthropic 的 walled garden 策略可能導致此類 plugin 被限制。

### Cursor Automations + Cursor 3 — 事件驅動 + Multi-Agent（2026-04-02→06 更新）[src:046][src:070]

**概述**：Cursor 在一週內同時推出 Automations（事件驅動雲端 agent）+ Cursor 3（multi-agent orchestration），從 IDE 廠商正式轉型為 agent 平台。

**與其他工具的差異化**：
- Claude Code / Codex / Gemini CLI：互動式、人類在迴圈中
- Overstory：人類指派任務給 agent 團隊
- Cursor Automations：**零人類介入、事件驅動**
- Cursor 3：IDE 內 multi-agent（與 Overstory 類似但封閉）

## Agentic 趨勢觀察

### OpenClaw — 個人 AI 助手平台 [src:007][src:008][src:019][src:034]

**規模**：349,035 stars / 68K forks，MIT，創建 2025-11-24

**Anthropic 訂閱封殺後**：OpenClaw 用戶需轉向 pay-as-you-go。SentientDawn 提出 Instar 替代方案（每個 agent 作為獨立 Claude Code CLI process 運行，使用原生訂閱認證），區分「wrapping the API vs extending Claude Code directly」。

### Claude Code 原始碼洩漏事件（2026-03-31 → 2026-04-06）[src:001][src:002][src:003][src:010][src:011][src:012][src:036][src:043][src:044][src:045]

**一週演變**：
- Claw Code 從 64K → 123.7K stars（翻倍），加速 Rust clean-room 重寫
- NanmiCoder 仍存活（3K stars），未被 DMCA
- Anthropic ~16hr 從發現到修復（v2.1.89）
- Grok 分析：洩漏使 Anthropic 的「dev tools moat」縮小，但核心價值仍在基礎模型 + scaling [src:036]
- Anthropic 自動化 DMCA 誤殺合法 fork（Theo 事件）[src:043][src:044][src:045]
- Anthropic 封殺 OpenClaw 訂閱支援，建立 walled garden [src:049][src:050][src:051]
- 洩漏碼被下載 41,500 次 [src:083]

## Coding AI 工具更新追蹤

### Claude Code（Anthropic）[src:013][src:014][src:072][src:073]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v2.1.89 | 04-01 | 洩漏修復 + 40+ fixes、defer hooks、PermissionDenied hook、autocompact thrash 修復 |
| v2.1.90 | 04-01 | /powerup 互動教學、SSE O(n)、PowerShell 安全、/buddy 彩蛋 |
| v2.1.91 | 04-03 | MCP 500K result override、disableSkillShellExecution、plugins bin/ exec、Edit shorter anchors |
| v2.1.92 | 04-04 | **Bedrock 精靈**、/cost per-model breakdown、**Write/Edit 60% faster**、移除 /tag /vim |

### OpenAI Codex CLI [src:015][src:016][src:020][src:076]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v0.118.0 | 03-31 | Windows sandbox、spawn v2 inter-agent、device code flow |
| v0.119.0-alpha.2 | 04-01 | Rust port、interrupted state、spawn_agent/send_message API |
| v0.119.0-alpha.11 | 04-04 | Rust port 密集迭代（4天11個 alpha） |
| Codex Plugin for CC | 04-03 | **跨平台互操作**：Claude Code 內使用 Codex review/rescue |

### Gemini CLI（Google）[src:017][src:018]

| 版本 | 日期 | 關鍵變更 |
|------|------|---------|
| v0.36.0 | 04-01 | 三平台 sandbox、subagent 工具隔離、A2A、Plan mode stable |
| v0.37.0-preview.1 | 04-02 | unified context、tool distillation、topic chapters |

### Cursor [src:046][src:070]

| 功能 | 日期 | 關鍵變更 |
|------|------|---------|
| Automations | 04-02 | 事件驅動雲端 agent：commit/PR/Slack/PagerDuty/Timer |
| Cursor 3 | 04-04 | Multi-agent orchestration，直接挑戰 Claude Code |

## 分析過的工具

| 日期 | 工具 | 版本 | 評分 | 備註 |
|------|------|------|------|------|
| 2026-04-06 | Codex Plugin for CC | 新 | ⭐⭐⭐⭐⭐ | 跨平台互操作里程碑，2天 12K stars |
| 2026-04-06 | Claude Code | v2.1.92 | ⭐⭐⭐⭐ | 封殺 OpenClaw 訂閱扣分；Write/Edit 60% 加速；Bedrock 精靈加分 |
| 2026-04-06 | Cursor 3 | 新 | ⭐⭐⭐⭐ | IDE 內 multi-agent，與 Overstory 競爭 |
| 2026-04-06 | MCP + A2A v1.0 | v1.0 | ⭐⭐⭐⭐⭐ | 標準定稿，146 成員，97M SDK downloads |
| 2026-04-06 | Gemini CLI | v0.36.0 | ⭐⭐⭐⭐⭐ | 突破 100K stars，三平台 sandbox 最完整 |
| 2026-04-06 | GPT-Image-2 | 灰度中 | ⭐⭐⭐⭐ | 圖像生成質量躍進，UI 生成尤其強 |
| 2026-04-06 | DeepSeek V4 | 預發佈 | ⭐⭐⭐⭐⭐ | 華為晶片獨立運行，$0.30/MTok |
| 2026-04-06 | Gemma 4 | 開源 | ⭐⭐⭐⭐ | Apache 2.0 + NVIDIA FP4，本地推理可行 |
| 2026-04-06 | OpenAI Codex CLI | v0.119.0-alpha | ⭐⭐⭐⭐ | Rust port 進入收尾，73.3K stars |
| 2026-04-06 | OpenClaw | — | ⭐⭐⭐ | 被 Anthropic 切斷訂閱，但 stars 持續增長 |
