# AI Tools Board — 快捷方式

> **重要：** 所有 `just ext-ai-tools-board-*` 指令都啟動**同一個 extension**。
> Preset（委員組合）是在 session 內透過 **tool 參數** 傳入，不是 env var。

---

## Just 快捷方式

```bash
# Mode A — 自動模式（全自動研究，用 board_begin 啟動）
just ext-ai-tools-board          # 啟動 extension，session 內呼叫 board_begin

# Mode B — 互動模式（你坐進委員會，用 board_discuss 啟動）
just ext-ai-tools-board-discuss  # 啟動 extension，session 內呼叫 board_discuss

# 以下為「有語意標籤」的快捷方式，啟動後傳入對應 preset 即可
just ext-ai-tools-board-discovery  # 啟動後用 preset="discovery"
just ext-ai-tools-board-coding     # 啟動後用 preset="coding"
just ext-ai-tools-board-music      # 啟動後用 preset="music"
just ext-ai-tools-board-video      # 啟動後用 preset="video"
just ext-ai-tools-board-github     # 啟動後用 preset="github"
just ext-ai-tools-board-systems    # 啟動後用 preset="systems"
```

---

## Mode A — 自動模式

```
# 全員研究
board_begin brief="本週 AI 工具有哪些重大更新？"

# 指定 preset（在工具參數傳入）
board_begin brief="Suno vs Udio 最新比較" preset="music"
board_begin brief="Veo 3 有什麼突破？" preset="video"
board_begin brief="Claude Code 新功能分析" preset="coding"
board_begin brief="追蹤 pi-coding-agent 最新 commit" preset="github"
board_begin brief="哪些新工具可以整合進現有系統？" preset="systems"
board_begin brief="本週 AI 工具全面掃描" preset="discovery"
```

→ 主席框架 → 所有 preset 委員並行研究 → 主席整合 → 輸出 .md + .html 報告

---

## Mode B — 互動模式（精確控制誰發言）

```bash
# 1. 開始討論（主席框架 + 介紹委員）
board_discuss brief="分析 Cursor 和 Claude Code 的最新競爭態勢"
board_discuss brief="Veo 3 剛發布，對我的工作流有影響嗎？" preset="video"

# 2. 讓下一位委員自動發言（按 preset 順序）
board_next

# 3. 加入你的觀點
board_next user_input="我覺得 Suno v4 的音質已經達到商業水準，你認為呢？"

# 4. 指定特定委員發言
board_next member="github-researcher"
board_next member="system-analyst"
board_next member="coding-ai-scout" user_input="請特別關注 agentic 功能的進展"
board_next member="music-ai-scout"

# 5. 結束 → 生成報告
board_report
```

→ 輸出 .md + .html 報告（路徑加 `-discussion` 後綴）

---

## 只召喚特定委員（精確模式）

**場景：** 只想問 `github-researcher` 和 `coding-ai-scout`

```bash
# 啟動
just ext-ai-tools-board-discuss

# 開始討論
board_discuss brief="追蹤 overstory AI coding 最新 repo 動態" preset="full"

# 只點名你要的人
board_next member="github-researcher"
board_next member="coding-ai-scout"

# 不叫其他人，直接結束
board_report
```

---

## Slash Commands

```bash
/board-preset              # 列出所有可用 preset
/board-preset discovery    # 切換到 discovery preset
/board-preset coding       # 切換到 coding preset
/board-status              # 查看當前活躍委員
```

---

## 委員列表

| 委員 ID | 角色 | 專責領域 |
|---------|------|---------|
| `director` | 主席（Opus 4.6） | 協調討論、整合洞見 |
| `music-ai-scout` | 音樂 AI 偵察員 | Suno、Udio、Stable Audio |
| `video-ai-scout` | 影片 AI 偵察員 | Veo、Seedance、Runway、Kling |
| `coding-ai-scout` | 程式 AI 偵察員 | Claude Code、Pi、Codex、Overstory |
| `system-analyst` | 系統分析師 | 用戶系統整合評估 |
| `github-researcher` | GitHub 研究員 | Repo 追蹤、私有 repo 讀取 |

---

## Preset 對照表

| Preset | 成員 |
|--------|------|
| `full` | 全 6 人 |
| `discovery` | director, music-ai-scout, video-ai-scout, coding-ai-scout |
| `music` | director, music-ai-scout |
| `video` | director, video-ai-scout |
| `coding` | director, coding-ai-scout |
| `github` | director, github-researcher |
| `systems` | director, system-analyst |
| `quick` | director, coding-ai-scout |

---

## 一對一成員會話（Member Session）

用獨立 extension 直接與單一成員深度對話：

```bash
# 啟動（互動選單選成員）
just ext-ai-tools-member

# 直接載入特定成員
just ext-ai-tools-member-coding    # coding-ai-scout
just ext-ai-tools-member-music     # music-ai-scout
just ext-ai-tools-member-video     # video-ai-scout
just ext-ai-tools-member-github    # github-researcher
```

### Member Session 指令

```bash
/member-select                    # 互動選單選擇成員
/member-select coding-ai-scout    # 直接切換成員
/member-status                    # 查看當前成員 + 知識庫狀態
/member-equip wsp-v3              # 將 skill 用法裝備到成員知識庫
/member-learn <url>               # 從 URL 學習並更新知識庫
```

### 運作原理

選擇成員後，Pi 本身就成為那個成員的身份：
- 成員的系統提示 + 個人知識庫自動注入到每次對話
- 用戶直接與「coding-ai-scout」或「github-researcher」對話
- 成員可以用 edit 工具即時更新自己的 knowledge.md
- 下次打開 board_begin 時，更新的知識庫會自動帶入委員會

---

## 報告輸出

- Mode A：`.pi/ai-tools-board/memos/<slug>-<timestamp>.md` + `.html`
- Mode B：`.pi/ai-tools-board/memos/<slug>-<timestamp>-discussion.md` + `.html`
