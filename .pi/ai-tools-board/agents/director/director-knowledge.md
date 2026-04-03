# Director — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 director-sources.md。

## AI 工具生態全局觀

### 2026-04-02 全委員會整合報告（v2 — 完整版）

**方法論**：6 位委員（director + 5 scout）分工研究。數據源涵蓋 GitHub API、社群討論、新聞報導、融資公告、政策法規。

**數據品質評分**：GitHub releases ✅ 高品質即時數據 | 新聞/融資 ⚠️ 二手信源為主 | WSP-V3 ❌ 不可用為主要限制

---

## 🏆 本週最值得關注的 3 件事

### 1. 🧠 Claude Code 洩漏 72hr 連鎖反應 — Agent 架構知識民主化
- Claw Code 48hr 內從 64K→123K stars（翻倍），clean-room Rust 重寫進行中
- System Prompts 合集 134K stars，收錄 30+ AI 工具的內部 prompt
- 8,100 個 repo 被 DMCA 誤刪（Anthropic 事後承認並撤回）
- 洩漏催生 10+ 高 star 分析專案（`ai-agent-deep-dive` 3,194 stars 最高）
- **AutoDream/Kairos 記憶架構**被完整拆解 — persistent agent 設計藍圖公開
- Claude 獨立完成 FreeBSD kernel RCE 漏洞利用 — AI coding 已達安全研究級

### 2. ⚔️ 五大 Agent 同步進入「Plugin OS」時代 + Gemini 架構超車
48hr 內 Claude Code、Gemini CLI、Codex、Goose、OpenClaw 全部模組化拆分：
- **Gemini CLI v0.36.0** 業界首創三平台原生 sandbox（macOS/Linux/Windows）
- Codex 獨立抽出 `codex-mcp` crate — MCP 協議成跨 agent 互通事實標準
- Goose `~/.agents/skills/` 標準化 + Sigstore/SLSA 驗證
- 新創工具鏈爆發：qwopus（本地 Qwen agent）、hive（多 agent TUI）、openskills（跨 agent skill loader）
- **Litter beta** 首創 coding agent 移動化（iOS/Android + Rust UniFFI）

### 3. 💰 OpenAI $122B + Sora 死亡 + Grok Imagine 盈利 — 商業模式之戰落幕
- OpenAI 史上最大融資 $122B（$852B 估值），寧砍 Sora 也要養 Spud（GPT 5.5）
- **Sora 全壽命僅賺 $2.14M，日均燒損 $1M** — 成本收入比 100:1，API 9/24 關閉
- **Grok Imagine 反證**：30 天 55 億生成量、正毛利，「平台嵌入+免費」打敗「獨立付費」
- Q1 全球創投 $297B 歷史紀錄，但 63% 集中在 4 筆巨額交易
- LiteLLM 供應鏈攻擊 + Delve 醜聞 — AI infra 信任鏈脆弱

---

## 📊 分領域關鍵動態

### 音樂 AI（music-ai-scout）
- **Suno v5.5** 持續霸權（700 萬首/日），但 Google **Lyria 3 Pro** 正式殺入（3 分鐘完整歌曲 + 圖片驅動）
- UMAW 推動「Living Wage for Musicians Act」— 監管從訓練延伸到生成內容稀釋
- Melogen 差異化：可編輯 Piano Roll + MIDI export，切入「後生成編輯」利基

### 影片 AI（video-ai-scout）
- **Sora 關閉確定** — 影片 AI 五強格局重組：Veo、Seedance、Kling、Runway、Grok Imagine
- Higgsfield Cinema Studio 3.0 被拆穿是 Seedance 2.0 wrapper — 模型層已商品化
- Veo 3.1 Lite 價格腰斬搶市、Cloudflare Workers 已封裝 Grok Imagine API

### Coding Agent（coding-ai-scout）
- **Holo3**（H Company）78.9% OSWorld 超越 GPT-5.4 和 Opus 4.6，開源 35B Apache 2.0
- Codex 移除 gpt-5.1-codex 系列 — 暗示 Spud 將直接取代
- Pliny the Liberator 將 jailbreak 工具轉為 private — 開源信任危機信號

### 開源生態（github-researcher）
- OpenClaw 344K、Claw Code 123K、Gemini CLI 99.9K（數小時內破 100K）
- DeepSeek 三連發（3FS + FlashMLA + DeepEP）建立完整開源訓練棧
- 開源天平：⬅️ 略傾開源，但 trust 層面出現裂痕

### 政策法規（system-analyst）
- 美國法官阻止政府封鎖 Anthropic — 司法制衡確立
- Reddit 強制人機驗證、百度 robotaxi 武漢癱瘓 2hr — AI 實體風險
- Oracle 同日裁員 30,000 人轉向 AI — 傳統工程師被替代加速

---

## 🔀 委員間主要分歧

### 分歧 1：開源天平方向
- **github-researcher**：⬅️ 略傾開源（Claw Code 123K、Holo3 Apache 2.0、DeepSeek 三連發）
- **coding-ai-scout**：開源信任危機升溫（Pliny 轉 private、LiteLLM 事件、OpenClaw 穩定性受疑）
- **主席裁決**：技術層面開源勝出，但信任/治理層面出現裂痕。開源的「勝利」可能質變為「開源代碼 + 商業信任層」的新模式。

### 分歧 2：AI 競賽核心在哪？
- **coding-ai-scout**：模型能力仍是核心（Spud 可能顛覆格局）
- **github-researcher**：Agent OS plugin layer 才是新戰場
- **video-ai-scout**：成本結構和分發渠道才是決勝因素（Sora 死亡證明）
- **主席裁決**：三者層層遞進——模型能力決定下限，分發渠道決定規模，plugin layer 決定生態鎖定。短期看 Spud，中期看 agent OS，長期看分發。

### 分歧 3：泡沫風險程度
- **system-analyst**：Yupp 倒閉 + $297B 創投 = 極端頭部化的泡沫信號
- **coding-ai-scout**：OpenAI 月收 $2B + 5000 萬訂閱 = 基本面支撐
- **主席裁決**：不是全面泡沫，而是「潮浪高度分化」。巨頭有真實營收支撐，但中腰部 AI startup 的生存窗口正在快速關閉。

---

## 值得追蹤的核心趨勢

1. **Agent OS 化**：五大 agent 同步模組化 → 30 天內預期出現第一批跨 agent 通用 plugin
2. **記憶持久化**：AutoDream 概念公開 → 跨 session agent 記憶成為新戰場
3. **模型層商品化**：Sora 死亡 + Higgsfield wrapper 現象 → 影片/音樂模型利潤趨零
4. **分發渠道勝出**：Grok Imagine（嵌入 X）、Lyria 3（嵌入 Google 生態）→ 平台嵌入 > 獨立產品
5. **安全供應鏈風險**：LiteLLM + DMCA 誤殺 + Pliny 轉向 → 開源 AI infra 的信任基礎動搖

---

## 委員會運作模式

### 2026-04-02 第二次全委員會議
- 5 位委員全部提交完整報告，數據品質提升
- 發現 3 處跨委員分歧，均完成主席裁決
- WSP-V3 不可用仍為主要限制，未來需建立備用研究管線

## 過往討論摘要

| 日期 | 議題 | 結論 | 後續行動 |
|------|------|------|---------|
| 2026-04-02 | AI 產業 48hr 全面掃描 v2 | 洩漏連鎖72hr、Agent Plugin OS 共識、Sora 死亡+Grok Imagine 盈利證明新商業模式；Spud 懸而未決是最大變數 | 研究AutoDream記憶架構、評估Gemini CLI sandbox為安全標準、監控MCP跨agent plugin、追蹤Lyria 3對Suno衝擊、建立LiteLLM替代方案評估 |
