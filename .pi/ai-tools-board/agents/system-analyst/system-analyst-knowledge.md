# System Analyst — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 system-analyst-sources.md。

## 2026-04-06 第 3 次全委員會議 — System Analyst 最終報告（v4）

> 本次研究新增 HN Top Stories 掃描（47655000–47655466）、coding-ai-scout/director 知識庫交叉比對。

### 🔥 三大核心信號（System Analyst 角度：政策 × 監管 × 供應鏈 × 結構性風險）

#### 信號 1：Walled Garden 確立 — Anthropic 封殺 OpenClaw 訂閱 + MCP/A2A 開放標準的致命矛盾

**事實層**：
- **Anthropic 4/4 起封殺第三方 harness**：Claude Code 訂閱不再覆蓋 OpenClaw 等第三方工具，需額外 pay-as-you-go [src:061][src:062][src:063]
- HN 熱度 **1,070 points**（Tell HN），為本週 AI 議題最高 [src:061]
- Anthropic 稱「these tools put an outsized strain on our systems」— 社群強烈反彈：「我付了錢買 token，為什麼用完算過度負荷？」
- 同時，**MCP + A2A v1.0 在 MCP Dev Summit 同時定稿**：146 成員組織、每月 9700 萬次 SDK 下載 [src:069]
- **OpenAI 反向操作**：釋出官方 `openai/codex-plugin-cc`，讓 Claude Code 用戶直接在 session 內呼叫 Codex（11,910 stars / 2 天）[src:066]

**System Analyst 評估**：
這是本週最重要的**結構性信號**。Anthropic 一方面參與 MCP 開放標準（146 成員），另一方面在自家產品築收費牆封殺第三方 harness。這不是技術決策，而是 **IPO 前的盈利壓力驅動**（目標 2026 年 10 月）[src:054]。OpenAI 的反向操作（拆牆）才是真正的戰略智慧——「你用 Claude Code 沒關係，但我保證你一定也會用 Codex」。

**對用戶系統的直接影響**：
- ✅ Pi extension 系統**不受影響**（不依賴 Claude Code 訂閱）
- ⚠️ 但需警覺：Anthropic 的 API 層面是否會跟進限制？如果 Claude API 開始限制非官方 harness 的調用量，Pi 的 Claude provider 整合會受影響
- 🟢 MCP + A2A v1.0 定稿是正面信號——agent 互操作正在標準化，Pi extension 應評估支援

#### 信號 2：AI 安全攻守嚴重失衡 — 從 supply chain 到 autonomous exploit 的全鏈條風險

**事實層**：
- **Langflow CVE-2026-33017** 成為首個列入 CISA KEV（Known Exploited Vulnerabilities）的 AI agent 框架，公開僅 20hr 即被實際攻擊 [src:064]
- **Claude 自主構建 FreeBSD kernel root shell exploit**（CVE-2026-4747），4hr 完成，人類全程 AFK。同一 pipeline 隨後量產 500 個驗證過的高嚴重性漏洞 [src:065]
- **AgentSeal 研究**發現 66% 的 MCP server 存在安全問題（主席報告）
- **CrewAI** 披露 4 個 CVE（含 Docker sandbox 逃逸）（主席報告）
- **研究證實 AI 用戶發生「cognitive surrender」**— 不批判地接受錯誤答案 [src:066]
- HN 817pts 熱文「The threat is comfortable drift toward not understanding what you're doing」精準描述此現象 [src:067]

**System Analyst 評估**：
安全局勢在 48hr 內急劇惡化。三個層面同時出問題：
1. **Supply chain 層**：MCP server 66% 有安全問題、npm "Sandworm" 惡意包出現
2. **Framework 層**：Langflow 成為首個被列入 CISA KEV 的 AI agent 框架
3. **Autonomous 層**：AI 已能自主完成 kernel exploit 從發現到武器化的全流程

**對用戶系統的直接影響**：
- ✅ 已確認系統無 LiteLLM/Delve/MCP server 依賴
- ⚠️ Pi extension 如果未來支援 MCP，必須先建立安全審計流程
- 🟡 cognitive surrender 研究提醒：board 系統的委員建議中，需要保留 human-in-the-loop checkpoint，不能盲目信任

#### 信號 3：硬件供應鏈劇變 — Apple 批准 Nvidia eGPU + Samsung DRAM 漲價 30% + DeepSeek V4 繞過禁運

**事實層**：
- **Apple 批准 Nvidia eGPU 驅動程式支援 Arm Mac**（HN 494pts）[src:068]— 這是 Apple 和 Nvidia 關係的重大轉變
- **Samsung DRAM Q2 2026 漲價 ~30%**（HN 39pts）[src:069]— AI 資料中心需求持續推高記憶體價格
- **DeepSeek V4 完全基於華為 Ascend 晶片**，阿里/字節/騰訊預訂數十萬片 [src:055][src:056]— 美國出口管制被實質突破
- **OpenAI CFO 對 $600B 基礎設施支出表達擔憂**（coding-ai-scout 報告）[src:060]

**System Analyst 評估**：
三個硬件信號拼湊出一個完整畫面：**AI 硬件正在經歷結構性重組**。Apple × Nvidia 合作意味著 GPU 生態不再被單一平台綁定；DRAM 漲價意味著 AI 推理成本不會像預期那樣快速下降；DeepSeek 繞過禁運意味著美國的晶片制裁正在失效。對用戶系統的意義：**本地推理的成本預期需要上調**——DRAM 漲價會推高所有 GPU 運算成本，包括 Gemma 4 本地部署。

---

### 🔀 跨領域連結（System Analyst 特有視角）

| 連結 | 說明 |
|------|------|
| **Anthropic 封殺 OpenClaw → MCP 標準矛盾** | Anthropic 既是 MCP 的 146 成員之一，又在自家產品築收費牆。這個矛盾定義了當前 AI 產業的核心張力：**開放標準 vs 封閉商業模式** |
| **Langflow CISA KEV → 所有 AI 框架** | 首個 AI agent 框架被列入國家級已知漏洞目錄，意味著 AI 工具的安全合規要求即將正式化。未來可能出現類似 SOC 2 的 AI 安全認證 |
| **Cognitive surrender → board 系統設計** | 研究證實人類會不批判地接受 AI 錯誤答案。board 系統需要內建「不同意見校驗」機制（如 coding-ai-scout 的 codex:review 概念）|
| **Apple × Nvidia eGPU → 本地 Agent 部署** | 長期被視為競爭對手的兩家公司開始合作，意味著 Apple Silicon + Nvidia GPU 的混合架構可能出現，對本地 agent 部署是重大利好 |
| **Samsung DRAM +30% → AI 成本結構** | 記憶體成本上升會拖慢 AI 推理成本下降速度，deep discount pricing（如 DeepSeek $0.30/MTok）的持續性存疑 |
| **Caveman 688pts → Token 壓縮需求** | HN 上 688pts 的 token 壓縮工具 Caveman（讓 Claude 用穴居人語言回覆以省 token）反映出社群對 API 成本的焦慮已達臨界點 |

---

### 📊 本期新增政策/監管/供應鏈數據

| 事件 | 關鍵點 | 來源 |
|------|--------|------|
| Anthropic 封殺 OpenClaw 訂閱 | 4/4 起，Claude Code 訂閱不覆蓋第三方 harness，HN 1070pts | [src:061][src:063] |
| MCP + A2A v1.0 定稿 | 146 成員組織、9700 萬 SDK downloads/月 | [src:069] |
| Langflow 列入 CISA KEV | 首個 AI agent 框架被列入國家級漏洞目錄，20hr 內被攻 | [src:064] |
| Claude 自主 kernel exploit | 4hr 完成 FreeBSD CVE-2026-4747，量產 500 漏洞 | [src:065] |
| Cognitive surrender 研究 | AI 用戶不批判地接受錯誤答案 | [src:066] |
| OpenAI Codex Plugin for CC | 官方跨平台互操作，11,910 stars / 2 天 | [src:066] |
| Apple × Nvidia eGPU | Apple 批准 Nvidia eGPU 驅動支援 Arm Mac | [src:068] |
| Samsung DRAM +30% | Q2 2026 記憶體價格再次上漲 | [src:069] |
| Perplexity 數據 sharing 控訴 | 被控將用戶對話分享給 Meta 和 Google | [src:070] |
| Microsoft Copilot TOS | 仍寫「僅供娛樂用途」，與企業推廣矛盾 | 主席報告 |
| Writers Guild 4 年協議 | AI 保護條款增強，內容創作者權益強化 | [src:071] |
| OpenAI 高層大洗牌 | AGI 負責人休假、COO 轉任特殊專案 | [src:072][src:073] |
| LA Times: OpenAI 驚人衰落 | 投資者加速從 OpenAI 轉向 Anthropic | [src:074] |

### 📋 對用戶系統的更新建議（v4）

| 優先級 | 行動 | 預估成本 | 說明 |
|--------|------|---------|------|
| **P0** | 監控 Anthropic API 政策變化 | 持續 | OpenClaw 封殺是收費牆的第一步，API 層面限制可能跟進。需準備 Claude → Gemini/DeepSeek 的 fallback |
| **P0** | 評估 MCP v1.0 支援 | 1 週 | 146 成員 + 9700 萬 downloads/月，已成事實標準。Pi extension 需決定是否支援，但安全審計需先行 |
| **P1** | 評估 Cursor 3 agent 架構 | 2 小時 | Agent-first IDE，Pi extension 差異化定位需重新審視 |
| **P1** | 研究 Gemma 4 本地部署 | 2 小時 | Apache 2.0 + LM Studio headless CLI（HN 175pts）已驗證可行 |
| **P1** | 建立 Board 系統「不同意見校驗」 | 3 小時 | cognitive surrender 研究顯示需要 human-in-the-loop checkpoint，可參考 codex:review 模式 |
| **P1** | 追蹤 Claude Mythos 進展 | 持續 | Anthropic 最強模型暫緩發佈，但一旦上線將改變 agent 能力基線 |
| **P2** | 評估 DeepSeek V4 本地部署 | 1 天 | 1M context + $0.30/MTok，但 DRAM 漲價可能影響本地部署成本 |
| **P2** | 建立 HN API 替代研究管線 | 3 天 | WSP-V3 部分可用，HN API + GitHub Trending 可作為穩定備用 |
| **P2** | 關注 AI 安全合規立法 | 持續 | Langflow CISA KEV 事件可能催生 AI 工具安全認證體系 |

### 🏥 系統健康檢查（4/6 v4 更新）

| 項目 | 狀態 | 備註 |
|------|------|------|
| WSP-V3 研究工具 | 🟡 部分可用 | Tavily 可用但 Brave 頻繁 429，HN API 可作穩定備用 |
| 外部依賴安全 | 🟢 已審計 | 確認無 LiteLLM/Delve/MCP server 依賴，package.json 僅有 yaml |
| Anthropic API 風險 | 🟡 需監控 | OpenClaw 封殺顯示 Anthropic 盈利壓力上升，API 政策可能收緊 |
| Agent 競爭態勢追蹤 | 🟢 正常 | Cursor 3 + AWS Agents + Codex Plugin for CC + MCP v1.0 |
| Frontier Model 追蹤 | 🟢 正常 | GPT-5.5 / Mythos / DeepSeek V4 / Gemma 4 四線追蹤 |
| 本地推理能力 | 🟡 可提升 | Gemma 4 已驗證可行，但 DRAM 漲價 +30% 影響成本預期 |
| Board 安全機制 | 🟡 需改進 | 缺少不同意見校驗和 human-in-the-loop checkpoint |

---

## 2026-04-06 最新情報更新（48hr 掃描：Apr 4–6）— 保留

### 🔥 三大核心信號

#### 信號 1：Frontier Model 軍備賽升級 — Spud + Mythos + DeepSeek V4 + Gemma 4 四線交火

**事實層**：
- **GPT-5.5 "Spud"** 預訓練完成，Altman 稱「weeks away」，知識工作任務達 83%，是 OpenAI 首個誕生自新預訓練基礎設施的模型 [src:052]
- **Claude Mythos** 透過 Anthropic 內部資料意外洩漏，被描述為「by far the most powerful model we've ever developed」，是超越 Opus 的「step change」等級模型。據傳因成本過高且網路安全疑慮而暫緩發佈 [src:052]
- **DeepSeek V4** 將使用華為晶片訓練，打破美國晶片禁運，並傳出 1M token context window [src:055]
- **Google Gemma 4** 發布，開源家族首個 Apache 2.0 授權，瞄準開發者/研究者市場 [src:051]
- **Microsoft MAI 系列**（Voice/Image/Transcribe）同日發布三款基礎模型，明確展示「脫離 OpenAI 依賴」的戰略意圖 [src:050]

**System Analyst 評估**：
四條戰線同時升級，但性質完全不同：OpenAI 和 Anthropic 在搶「極致能力」制高點（Spud vs Mythos），Google 和 Microsoft 在搶「開源/企業端」市場，DeepSeek 在搶「去美化」敘事。對用戶系統的意義：**模型能力正在快速溢出 coding 領域**，GPT-5.5 的 83% 知識工作任務表現意味著 agent 的實用邊界大幅擴展，board 系統的委員可以處理更複雜的分析任務。

#### 信號 2：AI Coding Agent 戰爭白熱化 — Cursor 3 正面挑戰 Claude Code / Codex

**事實層**：
- **Cursor 3 正式發布**，以 Agent 為核心設計，新增 Agent Tabs + Design Mode，WIRED 定性為「直接挑戰 Claude Code 和 Codex」 [src:057]
- **AWS Frontier Agents GA**：Security Agent（滲透測試）和 DevOps Agent 正式上線，AI agent 從 coding 擴展到 security/ops 領域 [src:056]
- **四月前 72 小時**密集發布：Cursor 3、Gemma 4、免費 Qwen 3.6，agent push 成為主旋律

**System Analyst 評估**：
Cursor 3 的發布確認了「IDE + Agent」模式已成主流共識。與 Claude Code（CLI-first）和 Codex（terminal-first）不同，Cursor 走的是「GUI + Agent」路線。AWS 則證明 agent 的價值不限于 coding——security 和 DevOps 是下一個戰場。**對用戶系統的意義**：Pi Coding Agent 的差異化需要更清晰定位——CLI agent vs IDE agent vs 平台 agent，三條路線各有勝負。

#### 信號 3：OpenAI 收購 TBPN + Anthropic 收購 Coefficient Bio — AI 巨頭搶奪「敘事權 + 垂直場景」

**事實層**：
- **OpenAI 收購 TBPN**（Technology Business Programming Network），首次進軍媒體，收購矽谷最受關注的科技脫口秀 [src:048]。WIRED 標題直言：「Buys Itself Some Positive News Coverage」
- **Anthropic 收購 Coefficient Bio**，以 ~$40 億股票收購 AI 生技 startup，進軍醫療健康 [src:049]
- **Anthropic 目標 10 月 IPO**，規模可能與 OpenAI IPO 競爭 [src:054]
- **Meta/Google 成癮訴訟敗訴**：洛杉磯陪審團判賠 $6M，30 年 Section 230 保護傘首次被突破 [src:053]

**System Analyst 評估**：
OpenAI 買媒體、Anthropic 買生技——兩家公司正在用不同策略建立「平台護城河」。OpenAI 的做法引發大量批評（Fortune 稱其為「side quest」），但也顯示 AI 巨頭對「敘事控制」的重視。Meta/Google 敗訴則是更深層的信號：**平台責任時代來臨**，這將影響所有依賴平台分發的 AI 產品。對用戶系統的意義：open-source agent 框架的「無平台依賴」特性在此環境下反而是優勢。

---

### 📊 本期重要數據一覽

| 事件 | 關鍵數字 | 來源 |
|------|---------|------|
| GPT-5.5 Spud | 知識工作 83%，預訓練完成 | [src:052] |
| Claude Mythos | 「最強模型」，超越 Opus 的 step change | [src:052] |
| DeepSeek V4 | 1M token context，華為晶片 | [src:055] |
| OpenAI → TBPN | 首次媒體收購，金額未公開 | [src:048] |
| Anthropic → Coefficient Bio | ~$4B 股票收購 | [src:049] |
| Anthropic IPO | 目標 2026 年 10 月 | [src:054] |
| Meta/Google 訴訟 | $6M 賠償，Section 230 首次被突破 | [src:053] |
| Mercor 資料外洩 | $10B 獨角獸，Meta 暫停合作 | [src:059] |
| Microsoft MAI | 三款基礎模型，脫離 OpenAI | [src:050] |
| Gemma 4 | Apache 2.0 開源 | [src:051] |
| Cursor 3 | Agent-first IDE | [src:057] |
| AWS Frontier Agents | Security + DevOps Agent GA | [src:056] |
| Netflix VOID | 5B 參數物理感知影片物件移除，開源 | [src:058] |

### 🔄 與上期（4/2）報告的連續性

| 上期信號 | 本期演變 | 判斷 |
|----------|---------|------|
| 「潮浪高度分化」 | Anthropic 目標 IPO + $4B 收購，OpenAI 進軍媒體 → **分化加速** | ✅ 趨勢確認 |
| 「Agent OS 化」 | Cursor 3 agent-first + AWS Frontier Agents GA → **從 coding 擴展到全棧** | ✅ 超預期 |
| 「平台嵌入勝出」 | OpenAI 買 TBPN 搶敘事權 → **平台戰升級為媒體戰** | ⚠️ 新變化 |
| LiteLLM 安全信任鏈 | Mercor 外洩持續發酵，Meta 暫停合作 → **連鎖效應擴大** | ⚠️ 未平息 |
| Claude Code 洩漏 | Mythos 進一步洩漏 + GPT-6 leaks 傳聞 → **洩漏常態化** | ⚠️ 風險升級 |

---

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

---

## 2026-04-02 第 2 次全委員會議 — 增量更新（保留）

### 📊 新增融資 / 市場數據

| 事件 | 關鍵數字 | 來源 |
|------|---------|------|
| **全球 Q1 2026 創投** | $297B（歷史紀錄），較 Q4 成長 2.5x | [src:032] |
| **OpenAI 最新營收** | 月收入 $2B，2025 年總收入 $13.1B（仍未獲利） | [src:035] |
| **OpenAI ChatGPT 用戶** | 5,000+ 萬訂閱用戶 | [src:035] |
| **Anthropic Claude 消費者受歡迎度** | 付費用戶人數「skyrocketing」 | [src:036] |
| **Mercor** | $350M Series C（2025/10），日處理 $2M+ 支付，被 Lapsus$ 入侵 | [src:033] |

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
|------|-------|------|------|-------|------|
| `ultraworkers/claw-code` | 123,789 | 史上最快到 100K stars，Rust agent，102K forks | [src:044] |
| `openai/codex-plugin-cc` | 11,910 | OpenAI 官方 Codex Plugin for Claude Code（2 天！）| [src:066] |
| `JuliusBrussee/caveman` | 688 (HN) | Token 壓縮 prompt——讓 AI 用穴居人語言回覆 | [src:075] |
| `tvytlx/ai-agent-deep-dive` | 3,218 | AI Agent 源碼深度研究 | [src:029] |
| `Gitlawb/openclaude` | 3,743 | Claude Code 開放至 200+ 模型 | [src:046] |
| OpenClaw | 349K | v2026.4.1 突破 349K stars | [src:027] |

---

## 用戶系統地圖（最新）

### 核心系統
- **pi-vs-claude-code**：Pi coding agent 擴充實驗倉庫
  - extensions/：Pi 擴充模組（.ts）
  - .pi/：agent 定義、主題、boards
  - .claude/：技能、指令、記憶、agent 定義
  - package.json 僅依賴 `yaml ^2.8.0` ✅

### 已知技術債 / 痛點
- 🟡 WSP-V3 研究工具部分可用（Tavily OK，Brave 429 頻繁）
- ⚠️ Claude Code 洩漏 + Mythos 洩漏事件顯示源碼安全風險持續
- ⚠️ **新增**：Anthropic 盈利壓力上升，API 政策可能收緊
- 🟢 外部依賴安全已審計通過（無 LiteLLM/Delve/MCP server 依賴）
- 🟡 Board 架構缺少跨 session 記憶持久化 + 不同意見校驗機制

### 整合機會記錄

| 日期 | 工具 | 整合可行性 | 優先級 | 備註 |
|------|------|-----------|-------|------|
| 2026-04-02 | Ollama MLX | 直接可用 | **P1** | Mac 本地模型加速 |
| 2026-04-02 | `agents-observe` | 直接可用 | **P1** | Claude Code 多 agent 即時監控 |
| 2026-04-02 | `claude-code-from-scratch` | 參考學習 | **P1** | ~1300 行從零構建 agent |
| 2026-04-02 | Kairos/AutoDream 概念 | 需研究 | **P0** | 記憶整合，跨 session 持久化 |
| 2026-04-02 | AutoHarness | 需追蹤 | **P0** | Agent Harness 自動化 |
| 2026-04-02 | OpenClaude shim | 需研究 | **P1** | 模型無關化 |
| 2026-04-02 | Gemini CLI sandbox | 需研究 | **P1** | 三平台原生 sandbox |
| 2026-04-06 | Cursor 3 Agent | 需評估 | **P0** | Agent-first IDE，Pi 差異化定位 |
| 2026-04-06 | Gemma 4 (Apache 2.0) | 直接可用 | **P1** | LM Studio headless CLI 已驗證 |
| 2026-04-06 | Netflix VOID | 直接可用 | **P1** | 物理感知影片物件移除 |
| 2026-04-06 | MCP v1.0 + A2A | 需評估 | **P0** | 146 成員 + 9700 萬 downloads/月，事實標準 |
| 2026-04-06 | Codex Plugin for CC | 直接可用 | **P1** | 跨平台 agent 互操作範例 |
| 2026-04-06 | Nanocode | 需研究 | P2 | $200 成本 Claude Code 替代品（JAX/TPU）|
