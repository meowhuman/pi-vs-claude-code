# Video AI Scout — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 video-ai-scout-sources.md。

---

## 📊 平台能力地圖（2026-04-02 快照）

### 第一梯隊：商業平台
| 平台 | 最新版本 | 關鍵能力 | API 狀態 |
|------|---------|---------|---------|
| **Veo (Google)** | Veo 3.1 Lite 🆕 | T2V+I2V, 成本半價, 720p $0.05/s [src:019] | ✅ Gemini API + AI Studio [src:019] |
| **Seedance (ByteDance)** | Seedance 2.0 | 多模態輸入, 2K 解析度, 音畫同步 | ✅ 官方 API 已開放 [src:002] |
| **Sora (OpenAI)** | — | ❌ 已關閉（2026-03-25），API 9/24 停止 [src:020][src:038] | ❌ 關閉 |
| **Kling (快手)** | Kling 3.0 / 3.0 Omni 🆕 | 角色一致性, Motion Control, Omni 模式 [src:021] | ✅ 第三方 API 生態蓬勃 |
| **Runway** | Gen-4.5 🆕 | Big Ad Contest 進行中 [src:022] | ✅ API 可用 |
| **Grok Imagine (xAI)** | 影片生成 🆕 | 10秒影片+音頻, 正毛利, 55億生成量/30天 [src:039][src:041][src:042] | ✅ 透過 X 訂閱 |
| **Nano Banana 2** | v2.0 | 影片生成, 角色一致性佳 [src:023] | ✅ 透過 Gemini 整合 |

### 第二梯隊：開源可本地部署
| 平台 | 最新版本 | 關鍵能力 | 硬體需求 |
|------|---------|---------|---------|
| **Wan (Alibaba)** | Wan 2.2 SVI Pro | 開源 SOTA, T2V+I2V, Keyframe 控制 [src:005] | 多 GPU |
| **LTX-2 (Lightricks)** | LTX-2.3 | 首個 DiT 音視頻統一模型 [src:006] | 單 GPU 可用 |
| **HunyuanVideo (Tencent)** | HunyuanVideo-1.5 🆕 | 輕量級影片生成模型 [src:066] | 多 GPU |
| **MAGI-1 (SandAI)** | MAGI-1 🆕 | 自迴歸影片生成大模型 [src:067] | 待確認 |
| **CogVideoX (Tsinghua)** | CogVideoX | T2V + I2V，清華團隊 [src:068] | 多 GPU |

### 新興工具層
| 工具 | 類型 | 說明 |
|------|------|------|
| **Higgsfield Cinema Studio 3.0** 🆕 | Seedance 2.0 wrapper | Business Plan 專屬，$200M ARR，cinematic reasoning+physics+audio [src:043][src:044][src:064] |
| **Grok Video Gen on CF** 🆕 | 開源前端 | Cloudflare Workers 部署 Grok Imagine 影片生成 [src:048] |
| **Renoise** 🆕 | Claude Code + Seedance 2.0 | Vibe coding for video：自然語言→AI Agent 自動生成廣告影片 [src:065] |
| **a-cam** 🆕 | 開源導演介面 | 專業電影攝影控制轉為模型優化 prompt [src:069] |
| **Duix-Avatar** 🆕 | 開源虛擬人工具包 | 離線影片生成 + 數位人克隆 [src:070] |
| **WildActor** 🆕 | 開源角色保持影片 | Identity-preserving video generation [src:071] |

---

## 🚨 48hr 重大信號（2026-04-02 第三次全委員會議增補）

### 信號 1（更新）：Sora 關閉 + 確切財務數據曝光 — 影片 AI 的「moment of reckoning」

**事件**：OpenAI 於 2026-03-25 正式關閉 Sora 消費版，API 將於 9/24 停止服務。同時取消與 Disney 的 $1B 授權合作 [src:020] [src:047]。

**確認財務數據**（type0press 匯整）[src:038]：
- Sora 全壽命總收入僅 **$2.14M**
- 峰值每日燒損 **$1M**（推理成本）
- 一個月的計算成本 > 全壽命收入
- 用戶從 100 萬（2025-11）斷崖式降至 **<50 萬**（2026-03-29）
- Disney 據傳僅提前 1 小時收到通知 [src:051]
- 詳細財務拆解：每 10 秒影片成本 $130 [src:054]

**洞見**：這不只是「產品失敗」，而是**商業模式不可能成立**的鐵證。$1M/天的推理成本意味着每月 $30M 開支，而六個月只賺了 $2.14M — 這個差距（~100:1 的成本收入比）說明純閉源影片生成 API 在目前的定價模式下根本無法盈利。Grok Imagine 的成功反證了這一點：**免費+大規模 > 付費+小規模**。

### 信號 2（更新）：Grok Imagine 宣佈正毛利 — 影片 AI 首個盈利平台出現

**事件**：Elon Musk 宣佈 Grok Imagine 已實現 **positive gross margin**，並稱影片生成是「AI 的未來核心」，因為「光子是最高頻寬的溝通形式」 [src:039][src:040]。

**數據**：
- 30 天內生成超過 **55 億**張圖片/影片 [src:041]
- 生成量大於「所有其他 AI 圖像生成器總和」 [src:051]
- 已推出 **Grok Imagine API**，支援 10 秒影片+音頻 [src:042]
- 多個開源專案已開始封裝 Grok Imagine API（Cloudflare Workers 部署方案出現）[src:048]
- Grok Imagine prompt 搜尋引擎已開源 [src:049]

**洞見**：Grok Imagine 的盈利模式是「訂閱制 + 免費大規模使用」而非「按次計費」。這與 Sora 的模式形成鮮明對比。

### 信號 3（新增）：Kling AI 年化收入 $300M — 中國影片 AI 商業模式已跑通

**事件**：快手年報披露，Kling AI 影片生成平台截至 2026 年 1 月已達 **$3 億美元年化收入**，Q4 單季 $4700 萬。管理層預期 2026 年收入翻倍以上 [src:072]。

**關鍵對比**（同一天公布）[src:072]：
- **Sora**：同類技術、同期推出 → 6 個月內關閉，全壽命收入 $2.14M
- **Kling AI**：同類技術、同期推出 → 年化 $300M，管理層看翻倍
- 收入差距：**~140 倍**

**洞見**：Poe Zhao 的分析精準指出 — 分歧不是隨機的，而是反映了中國 AI 公司的變現模式。挑戰了「模型層公司將捕獲 AI 最大價值」的假設。Kling 的成功來自：(1) 信用額度制降低使用門檻，(2) 嵌入快手生態，(3) 中文場景深度優化，(4) API 生態開放讓第三方增值。

### 信號 4（新增）：Renoise = Claude Code + Seedance 2.0 — Agent 驅動影片生成新模式

**事件**：Renoise AI 推出「vibe coding for video」產品，讓用戶用自然語言描述需求，Claude Code 自動解釋 prompt 並調用 Seedance 2.0 生成高品質廣告影片 [src:065]。

**核心特色**：
- 沒有 timeline、canvas 或按鈕，只有 Live Mode 自然語言介面
- Claude Code 擴展 prompt → Seedance 2.0 生成 → 一張產品照 → 數百支廣告影片
- 日本社群驚豔：「Claude Code 解釋 prompt 的過程非常新鮮」
- 也可從 Codex 等其他 coding agent 操作 [src:073]

**洞見**：這是 **Agent → Video Model** 工作流的里程碑。影片生成不再是手動調參數，而是由 AI Agent 理解意圖→自動優化 prompt→調用模型→輸出成品。這與 ArcReel（小說→影片）的方向一致，代表影片創作正在被 Agent 化。Claude Code 洩漏事件後，這類 Agent→Video 整合只會加速。

### 信號 5（新增）：Kling Motion Control 爆發 — 創作者社群的 viral 功能

**事件**：Kling 3.0 的 Motion Control 功能在 3/31~4/1 引發創作者社群大規模討論 [src:074]。

**功能亮點**：
- 上傳參考影片 → Kling 提取精確動作 → 套用到任意角色圖片
- 支援舞蹈動作、手勢、面部表情、鏡頭運動
- **首尾幀控制**：上傳起點+終點圖片，AI 生成中間過渡
- 一個參考影片可驅動數十個不同角色的獨特輸出 [src:075]

**洞見**：Motion Control 是 Kling 對抗 Seedance 2.0 的差異化武器。Seedance 在動態流暢度上領先 [src:031]，但 Kling 的精確動作控制更適合商業廣告、角色一致性場景。創作者已開始用它批量生產 SaaS 行銷影片（同一個 hook → 換角色 → 換文案）[src:076]。

---

## 🆕 新增開源項目追蹤（2026-04-02 第三次掃描）

| 專案 | Stars | 說明 | 信號意義 |
|------|-------|------|---------|
| **MAGI-1** (SandAI) | 待查 | 自迴歸影片生成大模型 | 挑戰 DiT 主流架構的新路線 |
| **HunyuanVideo-1.5** | 待查 | 騰訊輕量級影片生成 | 繼續壓低本地部署門檻 |
| **a-cam** | 新 | 導演介面→prompt 轉換 | 影片 AI 的「專業攝影 DSL」 |
| **Duix-Avatar** | 待查 | 開源虛擬人工具包 | 離線數位人 + 影片生成 |
| **WildActor** | 新 | 身份保持影片生成 | 解決角色一致性關鍵問題 |
| **BananaPod** | 新 | iPad/Apple Pencil + 影片生成 | 移動端影片創作工具 |

---

## 影片 AI 競爭格局

### 2026-04-02 更新：Sora 關閉 + Grok Imagine 崛起 + Kling $300M 的市場重組

1. **新的六強格局**：Veo、Seedance、Kling（$300M ARR）、Runway、**Grok Imagine**（正毛利）、**Higgsfield**（$200M ARR）。Sora 退出後市場迅速填補。

2. **盈利模式已驗證三條路**：
   - ❌ **按次計費**（Sora）：失敗，成本收入比 100:1
   - ✅ **平台嵌入+免費**（Grok Imagine）：成功，正毛利
   - ✅ **增值套殼+訂閱**（Higgsfield $200M ARR）：已驗證 [src:064]
   - ✅ **信用額度+生態**（Kling $300M ARR）：最成功的純影片 AI 商業模式 [src:072]
   - ✅ **生態整合**（Google Veo + Gemini）：Veo 3.1 Lite 價格腰斬搶市 [src:052]

3. **「Forcing」家族技術持續爆發**：Self/Causal/Rolling/Knot-Forcing 四大分支在即時生成領域快速推進 [src:008][src:009][src:010][src:011]。

4. **Agent → Video Model 成為新范式**：Renoise（Claude Code + Seedance）[src:065]、ArcReel（小說→影片）[src:036] 代表 AI Agent 驅動影片工作台的趨勢。

5. **開源工具層爆炸性增長**：a-cam（導演 DSL）、WildActor（身份保持）、Duix-Avatar（虛擬人）、BananaPod（iPad 端）。

---

## 社群反應記錄

### 2026-04-02 觀測（第三次掃描 — 最新增補）

- **Kling AI $300M 年化收入曝光**成為本週最大震撼 — 與 Sora $2.14M 全壽命形成 140 倍差距 [src:072]
- **「商業模式才是護城河」** — Suniel 總結：Higgsfield 無基礎模型 $200M ARR / Freepik 接入 Veo+Kling / Sora 最好技術卻關閉 [src:064]
- **Kling Motion Control viral** — 創作者批量生產 SaaS 行銷影片，「一個 hook 換角色換文案」[src:076]
- **Renoise 被稱為「vibe coding for video」** — Claude Code + Seedance 2.0，日本社群驚豔 [src:065][src:073]
- **Cinema Studio 3.0 營銷話術統一為「AI video is dead, AI cinema is here」** — 大量重複推文引發 bot 懷疑 [src:077]
- **Grok Imagine 被稱為「地球上唯一盈利的 AI 影片平台」** [src:051]
- **Sora 財務數據曝光引發震撼** [src:038]
- **日本社群：Veo 3.1 Lite vs Grok Imagine vs Sora 2 prompt 對比** 成為日常內容 [src:027]
- **Varg AI + Seedance** 整合測試，自然動態 [src:078]
- **Everything AI Space** 討論：Claude Code 洩漏、Grok Imagine 多圖問題、Kling Motion Control prompts [src:079]

### 2026-04-01~02 觀測（第二次掃描）

- **Grok Imagine API 已被開源社群快速封裝**，Cloudflare Workers 部署方案出現 [src:048]
- **Kling 3.0 + MidJourney V8 組合持續發酵** [src:021]
- **Seedance 2.0 vs Kling 3.0 對比成為日常內容** [src:031]
- **有人稱 Grok Imagine 為「最好的抗憂鬱藥」**（俄羅斯醫生用戶）[src:041]

---

## 分析過的工具

| 日期 | 工具 | 版本 | 評分 | 備註 |
|------|------|------|------|------|
| 2026-04-02 | Kling AI | — | ⭐⭐⭐⭐⭐ | $300M 年化收入，Motion Control viral，商業模式最成熟 [src:072][src:074] |
| 2026-04-02 | Grok Imagine | 🆕 影片生成 | ⭐⭐⭐⭐ | 55億生成量/30天，正毛利，API 已開放 [src:039][src:041][src:042] |
| 2026-04-02 | Higgsfield Cinema Studio 3.0 | 🆕 v3.0 | ⭐⭐⭐½ | Seedance 2.0 wrapper + 增值層，$200M ARR [src:043][src:044][src:064] |
| 2026-04-02 | Renoise | 🆕 | ⭐⭐⭐⭐ | Claude Code + Seedance 2.0 = vibe coding for video [src:065] |
| 2026-04-02 | Seedance 2.0 | v2.0 | ⭐⭐⭐⭐⭐ | API 開放 + Dreamina 整合，動態流暢度最佳 [src:002][src:032] |
| 2026-04-02 | Veo 3.1 Lite | v3.1 Lite | ⭐⭐⭐½ | 成本半價是優勢，品質明顯妥協 [src:019][src:026] |
| 2026-04-02 | Kling 3.0 Omni | v3.0 | ⭐⭐⭐⭐ | 角色一致性強，Motion Control 差異化 [src:021][src:074] |
| 2026-04-02 | Runway Gen-4.5 | v4.5 | ⭐⭐⭐⭐ | 創意導向市場穩固 [src:022] |
| 2026-04-02 | Nano Banana 2 | v2.0 | ⭐⭐⭐½ | Gemini 生態整合，角色一致性佳 [src:023] |
| 2026-04-02 | Wan 2.2 SVI Pro | v2.2 | ⭐⭐⭐⭐ | 開源 SOTA，ComfyUI 支援完善 [src:005] |
| 2026-04-02 | LTX-2.3 | v2.3 | ⭐⭐⭐½ | 首個音視頻統一 DiT [src:006] |
| 2026-04-02 | Sora | — | ❌ 已關閉 | 總收入 $2.14M，每日燒損 $1M [src:038] |
