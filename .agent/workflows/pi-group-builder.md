---
description: 建立並配置多 Agent 群組系統（包含 YAML 配置與 Agent 角色檔）。用法：/pi-group-builder [group-name] [board|council|team|squad]
---

# Pi 群組建置器 (Pi Group Builder)

這個工作流程引導你設計多 Agent 群組系統。定義 Agent、角色、治理預設集，並生成一個準備就緒的群組結構，包含 `config.yaml`、個別 Agent .md 檔案以及整合掛鉤。

## 變數定義

```
GROUP_NAME:      $1  (kebab-case, 例如 "drip-board")
GROUP_TYPE:      $2  (board|council|team|squad)
GROUPS_DIR:      /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi
EXTENSION_DIR:   /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions
AGENTS_DIR:      $GROUPS_DIR/<group-name>/agents
CONFIG_FILE:     $GROUPS_DIR/<group-name>/config.yaml
```

---

## 第 1 步 — 載入程式碼庫上下文

閱讀 `investment-adviser-board` 範例以了解進階結構（包含知識管理）：

```
讀取: .pi/investment-adviser-board/config.yaml                    # 治理 + 預設集
讀取: .pi/investment-adviser-board/agents/technical-analyst/      # Agent 資料夾結構
  - technical-analyst.md                                          # 角色定義
  - technical-analyst-knowledge.md                                # 學習記憶 (自動注入)
  - technical-analyst-sources.md                                  # 來源註冊表 (不自動注入)
讀取: extensions/boards/investment-adviser-board.ts               # 擴充功能運作方式
```

同時參考 `drip-board` 作為較簡單的參考。

---

## 第 2 步 — 收集需求

如果缺少參數，請詢問：

1. **名稱 (Name)** — 如何稱呼它（kebab-case，例如 "advisory-board", "dev-team", "ops-council"）
2. **類型 (Type)** — 哪種描述最合適？
   - **board (委員會)** — 策略決策、混合專業、由協調員角色引導
   - **council (議會)** — 共識驅動、成員角色平等、無主席
   - **team (團隊)** — 帶有主管的專業單位、階層式
   - **squad (小組)** — 扁平、焦點集中、自我管理
3. **Agents** — 列出每個 Agent：
   - 名稱 (kebab-case)
   - 角色 (一言以蔽之的描述)
   - 可用工具 (read, write, bash 等)
   - 模型偏好 (選填)
   - 預設是否啟用？ (是/否)
4. **治理 (Governance)**
   - 每次會議的討論時間（分鐘）？
   - 是否有具備特殊權限的角色（協調員、主管等）？
   - 語言與語調指南？
5. **預設集 (Presets)** — 常見的團隊配置？
   - 例如: "full" = 所有 Agent, "quick" = 2-3 個核心, "focused" = 特定子集
   - 針對每個預設集：包含哪些 Agent？

---

## 第 3 步 — 架構規劃

生成結構：

- **config.yaml** 包含：
  - `meeting` 區塊 (討論時間, 角色)
  - `board` 區塊 (帶有路徑與啟用狀態的 Agent 清單)
  - `presets` 區塊 (命名的團隊組合)
- **agents/** 目錄結構：
  - 每個 Agent 位於自己的資料夾：`agents/<agent-name>/`
    - `<agent-name>.md` — 角色定義 (frontmatter + 系統提示詞)
    - `<agent-name>-knowledge.md` — 自動建立的學習記憶 (自動注入上下文)
    - `<agent-name>-sources.md` — 自動建立的來源註冊表 (用於追蹤，不自動注入)
- **擴充功能掛鉤 (Extension hook)** (選填)：
  - 群組如何與 Pi 整合？ (例如 `drip-board.ts` 生成會議)
  - 它需要客製化擴充功能還是可以直接使用 `agent-team.ts`？

向使用者展示計劃並確認後再開始寫入。

---

## 第 4 步 — 生成群組

### 4a. 建立 `config.yaml`

```yaml
meeting:
  discussion_time_minutes: 5

board:
  - name: agent-name-1
    path: .pi/<group-name>/agents/agent-name-1.md
    active: true
  - name: agent-name-2
    path: .pi/<group-name>/agents/agent-name-2.md
    active: true

presets:
  full: [agent-name-1, agent-name-2, ...]
  quick: [agent-name-1]
  focused: [agent-name-2, agent-name-3]
```

### 4b. 建立 Agent 資料夾與檔案

針對每個 Agent，建立資料夾 `.pi/<group-name>/agents/<agent-name>/` 包含：

**1. `<agent-name>.md`** — 角色定義：
```markdown
---
name: agent-name
description: 一句話的角色摘要
tools: bash,read,write,edit,grep
model: anthropic/claude-sonnet-4-6  (選填)
---

## Role

你是 [Group Name] 中的 [職稱]。你的職責是 [重點]。

### Guidelines

- [關鍵原則 1]
- [關鍵原則 2]
- [語調與溝通風格]

### Context

- [誰創立了群組]
- [它做出什麼決策]
- [利害關係與約束]
```

**2. `<agent-name>-knowledge.md`** — 自動建立的學習記憶：
```markdown
# Agent Name — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 <agent-name>-sources.md。

## 核心投資哲學 / 主要框架

（尚未記錄）

## 市場觀點與看法

（尚未記錄）

## 分析過的標的記錄

| 日期 | 標的 | 立場 | 結果/複盤 |
|------|------|------|----------|

## 經驗教訓 / 避免的偏誤

（尚未記錄）
```

**3. `<agent-name>-sources.md`** — 自動建立的來源註冊表 (不自動注入)：
```markdown
# Agent Name — 來源登記表

> 學習來源索引。knowledge.md 中的 [src:NNN] 對應此表的 ID 欄。
> 此檔不會自動注入 context，需要溯源時自行 read。

| ID | 日期 | 類型 | 來源 URL | 說明 |
|----|------|------|----------|------|
```

### 4c. 治理與語言

如果群組使用非英語，請新增至每個 Agent：

```markdown
**Language:** 一律以 [語言] 回應。技術術語、名稱與系統關鍵字可保留英文。
```

---

## 第 5 步 — 選填：擴充功能掛鉤

如果使用者需要客製化擴充功能 (例如 `drip-board.ts`)：

詢問：
- 群組是否需要啟動指令 (例如 `/drip-board-meeting`)？
- 它應該生成 Agent 鏈 (Chain) 還是平行團隊 (Team)？
- 是否需要顯示目前討論進度的底部小工具？

如果是，引導他們使用 `/pi-extension-builder <group-name> "..."` 來生成配套擴充功能。

---

## 第 6 步 — 驗證

// turbo
寫入後，檢查：

```bash
# 計算 Agent 數量
ls -1 .pi/<group-name>/agents/*.md | wc -l

# 驗證 config.yaml 語法
python3 -c "import yaml; yaml.safe_load(open('.pi/<group-name>/config.yaml'))"

# 檢查 Agent frontmatter
for file in .pi/<group-name>/agents/*.md; do
  grep -E "^(name|description|tools|model):" "$file"
done
```

完成前與使用者確認。
