# Music AI Scout — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 music-ai-scout-sources.md。

---

## 平台能力地圖

### Suno
- **目前版本**：v5.5（2026-03-26 發布）[src:001]
- **三大新功能**：
  1. **Voices**：上傳或錄製自己的聲音，AI 用你的聲音生成歌曲（voice cloning）
  2. **Custom Models**：用自己的音樂庫微調模型，產出個人風格作品
  3. **My Taste**：AI 學習你的偏好，隨時間優化推薦
- **社群評價**：v5.5 被普遍稱為「game changer」，remix 品質大幅提升（50/50 混合即可 playlist-ready），音質更清晰，情感表現更自然 [src:003][src:004][src:008]
- **已知問題**：Voices 功能在長歌曲中偶爾出現音調偏移和音質不均 [src:003]
- **競爭優勢**：2025 年全年生成超過 5000 萬首歌曲 [src:003]
- **⚠️ 新數據（48hr）**：目前每天生成 **700 萬首歌曲**，大量 AI 內容涌入串流平台稀釋版稅池 [src:018]
- **定價**：免費版可用（但功能受限），付費版提供完整功能
- **⚠️ 利用規約悄悄更新**：2026-03-26 與 v5.5 同步更新利用規約，對 YouTube 等平台 AI 音樂收益化者「錢包直接相關」的重要規則隱藏其中 [src:041]
- **音質持續好評**：「Previous versions sounded like music in a tin can. Suno v5.5 sound quality is amazing!」「V5.5 seems like an upgrade, hasn't degraded in voice and presence」[src:034][src:042]
- **日本用戶注意**：v5→v5.5 工業系相容性差，出現嚴重点擊雜音（プチプチ音），部分用戶因此未追加課金 [src:035]

### Google Lyria 3 / Lyria 3 Pro（🆕 重大突破）
- **發布時間**：2026-03-31，Google AI Studio 開放 Lyria 3 專用 workspace [src:019]
- **能力**：
  - 從文字 prompt 生成完整歌曲，**最長 3 分鐘**（Lyria 3 Pro）[src:020]
  - 支援圖片驅動音樂生成（圖片作為音乐 brief）[src:021]
  - 48kHz studio-quality 匯出，royalty-free [src:021]
  - 18+ 語言的人聲與歌詞支援 [src:021]
  - Composer Mode：描述 → 聽取 → 匯出程式碼建構 [src:019]
- **生態整合**：已整合至 Freepik Audio Suite、Venice AI（多模型平台）[src:021][src:022]
- **社群評價**：被稱為「令人敬畏」，one-shot single-line prompt 即可產出高品質作品 [src:023]
- **定位**：不只是音樂生成工具，而是「multimodal creative model」——圖片、文字、影片都能驅動音樂 [src:021]
- **影響**：直接挑戰 Suno 的「prompt → song」霸主地位
- **⚠️ 48hr 新增**：Google 多模態陣容同步升級——Gemini real-time audio、Lyria 3 音樂、Veo 3.1 影片，形成完整多模態創意工具鏈 [src:043]

### ElevenLabs Music（⚠️ 動態升級）
- **Music Marketplace**：2026-03-19 正式上線，複製 Voice Marketplace 成功模式 [src:024]
- **Voice Marketplace 累計已付給創作者超過 $1,100 萬** [src:024]
- **累計生成**：自 2025-08 推出 Eleven Music 以來，已生成 1,400 萬首歌曲 [src:025]
- **AI Gateway App**：2026-04-01 宣布 music generation 正式上線 [src:026]
- **日本市場拓展**：贊助 J-WAVE 電台 Morning Research 節目，推出 AI 角色「ラボちゃん」[src:027]
- **Credit 爭議**：社群仍持續批評 credit 消耗設計 [src:010]
- **⚠️ Marketplace 封閉性爭議**：只接受 ElevenLabs 自家生成器產出的音樂，Suno/Udio 用戶被排除在外。Cambrian 等競品立刻推出「任何生成器皆可」的開放 Marketplace 作為差異化回應 [src:044]
- **⚠️ 商業模式驗證中**：AI Video Week Magazine 提醒「Read the Small Print First」，顯示市場對 ElevenLabs Marketplace 條款的審慎態度 [src:045]

### ACE-Step 1.5（開源）
- **GitHub**：ace-step/ACE-Step-1.5，8,392 stars，957 forks [src:005]
- **最新版本**：v0.1.5（2026-03-25）[src:028]
- **特色**：本地運行的開源音樂生成模型，支援 Mac/AMD/Intel/CUDA
- **生態擴展**：
  - Side-Step：訓練腳本 + CLI + GUI（93 stars）[src:007]
  - acestep-vst：VST 插件，可在 DAW 中使用 [src:008]
  - acestep.cpp：C++ GGML 實作（163 stars）[src:006]
  - generative-radio：Qwen3 + ACE-Step 的 AI 電台 [src:017]
  - banger-scorer：MERT embeddings 品質評分器
- **與 Suno 比較**：社群評價「仍不如 Suno v5」[src:009]

### Stable Audio / Stability AI
- stable-audio-tools：3,652 stars，最近更新 2026-04-01 [src:011]
- 維持活躍但無重大版本更新

### Udio
- 2026 年 2 月起嘗試與音樂產業和解（2024 年版權訴訟）[src:012]
- 無重大新版本發布消息

### Melogen（🆕 新競品）
- **定位**：「AI music is easy to generate, but hard to control」——主打可編輯性 [src:029]
- **核心差異**：image/video → music → **editable Piano Roll** → MIDI export [src:029]
- **功能**：即時旋律編輯、4-6 軌混音、直接匯出 MIDI 到任何 DAW [src:030]
- **策略**：不與 Suno 比生成品質，而是切入「post-generation editing」利基市場

### Audiera Web3 + AI A&R Agent（🆕 48hr 新增）
- **定位**：Web3 原生音樂 AI agent 平台，Binance AI Agent Challenge 參賽作品 [src:046]
- **核心功能**：OpenClaw agent + Audiera Lyrics/Music Skills → Telegram bot → $BEAT 代幣收益
- **工作流**：主題建議 → 風格選擇 → AI 寫詞 → 人工審核 → AI 作曲 → 交付連結 → 赚取 $BEAT
- **意義**：Web3 + AI Music Agent 的完整 loop 驗證，agent 具備獨立錢包和經濟能力 [src:046]

### 音樂 AI Agent 匯流
- Weavemuse：基於 smolagents 的多模態音樂 AI agent 系統 [src:013]
- kidskoding/music-ai-agent：Go 實作的 headless AI 音樂 agent，用 Databricks + Google Cloud 分析選擇 Spotify 曲目 [src:031]
- Audiera Web3 AI A&R Agent：Telegram bot + $BEAT 代幣經濟 [src:046]
- 音樂 AI 正從「單純生成工具」走向「agent 化」趨勢明確

### Suno API 生態（🆕 48hr 更新）
- **gcui-art/suno-api**：2,797 stars，最大非官方 API wrapper，支援 GPTs/agents 整合 [src:014]
- **SunoAI-API/Suno-API**：1,764 stars，商業 API 服務 [src:038]
- **yihong0618/SunoSongsCreator**：345 stars，反向工程 API，2026-03-27 最近更新（v5.5 後一天）[src:039]
- **wlhtea/Suno2openai**：以 OpenAI 格式包裝 Suno API，支援 newapi/oneapi 中轉站 [src:040]
- **趨勢觀察**：多個非官方 API 在 v5.5 發布後密集更新（3/26-4/1），顯示開發者社群正積極將 Suno 整合進 agent 工作流

### 音樂 AI Marketplace 競爭格局（🆕 48hr 新增）
- **ElevenLabs Music Marketplace**：封閉式，僅限自家生成器 [src:024][src:045]
- **Cambrian**：開放式，接受任何生成器的音樂，「Your tracks, your terms, your price」[src:044]
- **Audiera**：Web3 代幣經濟 + Agent 原生，$BEAT 代幣收益 [src:046]
- **趨勢**：音樂 AI 商業變現出現三條路徑——封閉平台市場、開放跨平台市場、Web3 代幣經濟

---

## 版權與法律動態

- **Suno vs 音樂產業訴訟**：2024 年被 major labels 起訴，仍在進行中 [src:012]
- **🆕 AI 牽版權戰爭升級**：出版商加入音樂訴訟陣營，「AI Copyright Battle Escalates as Publishers Join Music Lawsuit」（2026-04-01）[src:032]
- **🆕 UMAW 反擊 AI 泛濫**：美國音樂家聯盟（UMAW）指出 Suno 每天 700 萬首 AI 歌曲涌入串流平台，稀釋人類音樂家版稅收入，推動「Living Wage for Musicians Act」——新法案要求額外版權僅限人類音樂家領取 [src:018]
- **🆕 美國首宗 AI 刑事案件聚焦串流版稅**：Max Schoon 觀察指出「第一宗美國 AI 刑事案件不是 deepfakes 或虛假資訊，而是串流版稅。音樂產業花了 30 年建立版權執法基礎設施。AI 監管不會來自國會，而會來自已經有律師團隊的產業。」[src:047]
- **Voice Clone 合規性**：Suno v5.5 的 Voices 功能持續引發 deepfake 憂慮，有專家指出「content restrictions 存在但 creative workarounds 可行」[src:033]
- **ElevenLabs Credit 爭議**：社群發布審計報告指出 credit 消耗設計不合理 [src:010]
- **🆕 Suno 利用規約悄悄更新**：日本用戶指出 v5.5 同步更新了利用規約，其中包含對 AI 音樂收益化者「非常重要且有些可怕」的規則，直接影響 YouTube 等平台的商業化使用 [src:041]

---

## 社群反應記錄

### Suno v5.5 發布反應（2026-03-26 ~ 2026-04-02）
- **正面**：「game changer」「radio-ready」「比 V5 好太多了」[src:003][src:004][src:008]
- **正面持續**：「Suno V5.5 seems like an upgrade... hasn't degraded in voice and presence」（4/2）[src:034]
- **正面持續**：「Previous versions sounded like music in a tin can. Suno v5.5 sound quality is amazing!」（4/2）[src:042]
- **中性**：Voices 功能「聲音偶爾有問題」，v5→v5.5 偶爾有「點擊雜音」[src:035]
- **中性**：部分用戶反映 v5.5 音量控制問題，即使指定「優しい歌声」「靜かに」仍出現過強音量 [src:048]
- **日本社群**：非常活躍，「底辺AI音楽フェス」即將於 4/8-4/9 舉辦（Suno/Udio 用戶原創音樂發表會）[src:036]
- **專業評價**：MusicTech 雜誌引用「v5.5 is a model that doesn't just help create music, but fully reflects the person making it」（4/1）[src:037]
- **日本用戶深度反饋**：v5.5 是 v4.5+ 工業系的進化，與 v5 相容性不佳；Editor 功能改善——差替え音域特性與 ambient 更自然、接合點更平滑、Fixed 功能可用 [src:035][src:049]

### Google Lyria 3 社群反應（2026-03-31 ~ 2026-04-02）
- **正面**：「令人敬畏」「one shot single line prompt 即可」[src:023]
- **關注**：Google AI Studio 的 composer mode 被視為真正可用的創作工具 [src:019]
- **整合**：Freepik 的圖片驅動音樂工作流獲得正面評價 [src:021]
- **對比**：用戶指出 Lyria 3 在歌詞處理上失敗嚴重，Suno 5.5 在此方面「absolutely magical」[src:050]

### 日本社群現象（底辺AI音楽フェス）
- 4/8-4/9 預演、4月中旬正式活動，由 @DEN_MA 主辦 [src:036]
- 規則：每人至少一首「ネタ曲」（搞笑曲），自虐風格
- YouTube Premiere + Discord 同步，免費觀看
- 反映 AI 音樂創作者社群的活躍與自組織能力

### 日本 Suno 用戶 v5.5 實測詳細反饋
- **TailorGoh2024**：比較 Voices 功能與 Synthesizer V（ユーミン曾用過的工具）[src:051]
- **joshlee361**（音樂製作人）：Custom Models 可用 100 tokens 訓練，學習個人風格/模式/氛圍，大幅加速創意產出；唯一困難是 rap 中版權詞彙觸發內容限制 [src:052]
- **HtmlI57600**：v5.5 Editor 功能終於可用，替換音域特性更自然，接合處更平滑 [src:049]

### m-flo「Gateway」MV — AI 混合創作引發討論
- m-flo 新曲「Gateway」MV 大量使用 AI 生成影片，日本社群兩極反應
- 正面：「AI 的正確用法」「與真人拍攝平衡絕妙」「5 分鐘持續興奮的電子毒品」
- 負面：「看到 AI 就失望」「本來以為要花驚人製作費」
- **意義**：知名藝人正式採用 AI 生成 MV，標誌 AI 在主流音樂視覺創作中的接受度提升 [src:053][src:054][src:055]

---

## 第 2 次全委員會議 — 48hr 增量洞見（2026-04-02）

### 🔴 信號 1：Google Lyria 3 正式殺入音樂 AI 戰場
Google 在 3/31-4/1 連續動作——Lyria 3 上線 Google AI Studio、Lyria 3 Pro 支援 3 分鐘完整歌曲、Freepik 整合。這不只是新模型發布，而是 Google 將音樂 AI 嵌入其完整生態系（AI Studio → Vertex AI → 第三方整合）的戰略佈局。Suno 的「prompt → song」獨佔優勢正在被蝕食。

### 🟡 信號 2：Suno 700 萬首/日 引發版權政策反撲
UMAW 推動「Living Wage for Musicians Act」要求 AI 生成內容排除在版權報酬之外。加上出版商加入音樂訴訟陣營，監管壓力正在從「訓練資料合法性」延伸到「生成內容對市場的稀釋效應」。這是結構性威脅。

### 🟢 信號 3：音樂 AI Agent 生態持續萌芽
Go-based headless music agent、Gemini 3.1 Flash + Lyria 3 整合至機器人、Venice AI 提供統一 Agent API（chat/images/video/music）。Agent 化趨勢加速，但距離實用仍有距離。

### 🆕 信號 4：Suno API 生態爆發（48hr 新增）
v5.5 發布後一周內，多個非官方 API 同步更新。gcui-art/suno-api（2,797 stars）和 SunoAI-API（1,764 stars）形成了「雙頭 API」格局。wlhtea/Suno2openai 更直接將 Suno API 包裝成 OpenAI 格式，意味著現有的 LLM agent 框架可以零成本接入 Suno。**這與 coding-ai-scout 追蹤的 agent 工具趨勢直接交叉——音樂生成正在成為 agent 工作流的原語之一。**

### 🆕 信號 5：音樂 AI 商業變現三路競爭（48hr 新增）
ElevenLabs 封閉式 Marketplace vs Cambrian 開放式 Marketplace vs Audiera Web3 代幣經濟。三種截然不同的商業模式同時出現，顯示 AI 音樂的變現路徑仍在探索期。封閉 vs 開放的選擇將深刻影響生態發展方向。

### 🆕 信號 6：AI 監管從國會轉向法庭（48hr 新增）
美國首宗 AI 刑事案件聚焦串流版稅而非 deepfakes，顯示音樂版權體系可能成為 AI 監管的前哨戰。加上 Suno 利用規約悄悄更新對商業化用戶施加新限制，規範化壓力正在加速。

---

## 分析過的工具

| 日期 | 工具 | 版本 | 評分 | 備註 |
|------|------|------|------|------|
| 2026-04-02 | Suno | v5.5 | ⭐⭐⭐⭐⭐ | 700萬首/日，Voices + Custom Models + My Taste，但版權壓力升溫 |
| 2026-04-02 | Google Lyria 3 Pro | v3 | ⭐⭐⭐⭐ | 3分鐘完整歌曲、圖片驅動、生態整合，新競爭者 |
| 2026-04-02 | ACE-Step 1.5 | v0.1.5 | ⭐⭐⭐ | 開源王者，8.4K stars，生態蓬勃，但仍不如 Suno |
| 2026-04-02 | ElevenLabs Music | - | ⭐⭐⭐⭐ | Music Marketplace 上線，1,400萬首累計，Voice Marketplace 已付$1100萬 |
| 2026-04-02 | Melogen | 新產品 | ⭐⭐⭐ | 差異化策略：可編輯 Piano Roll + MIDI 匯出 |
| 2026-04-02 | stable-audio-tools | - | ⭐⭐⭐ | 維持活躍但無重大突破 |
| 2026-04-02 | Udio | - | ⭐⭐ | 法律困境中，無明顯新功能，被 Suno 拉開差距 |
| 2026-04-02 | Cambrian | 新產品 | ⭐⭐⭐ | 開放式音樂 Marketplace，接受任何生成器 |
| 2026-04-02 | Audiera | 新產品 | ⭐⭐ | Web3 + AI Music Agent，$BEAT 代幣經濟驗證中 |
