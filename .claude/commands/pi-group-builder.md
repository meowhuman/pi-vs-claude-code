---
model: sonnet
description: Build and configure multi-agent group systems with YAML config and agent role files
argument-hint: [group-name] [board|council|team|squad]
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Purpose

Guide the user through designing a multi-agent group system. Define agents, roles, governance presets, and generate a ready-to-run group structure with config.yaml, individual agent .md files, and integration hooks.

## Variables

```
GROUP_NAME:      $1  (kebab-case, e.g. "drip-board")
GROUP_TYPE:      $2  (board|council|team|squad)
GROUPS_DIR:      /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi
EXTENSION_DIR:   /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions
AGENTS_DIR:      $GROUPS_DIR/<group-name>/agents
CONFIG_FILE:     $GROUPS_DIR/<group-name>/config.yaml
```

---

## Step 1 — Load Codebase Context

Study the **investment-adviser-board** (advanced financial system) to understand group architecture with knowledge management:

```
Read: .pi/investment-adviser-board/config.yaml
  - 8 agents (CEO + 7 specialists: macro-strategist, fundamental-analyst,
    technical-analyst, risk-officer, market-intelligence,
    prediction-market-analyst, backtest)
  - 10 presets (full, macro-focus, swing-trade, quick, event-driven, etc.)
  - 10-minute discussion timeframe

Read: extensions/boards/investment-adviser-board.ts
  - board_begin tool — auto-run analysis → HTML report (Mode A)
  - board_discuss tool — interactive discussion (Mode B, user as "human member")
  - board_next, board_report tools for orchestration

Read: extensions/boards/inv-board-member-session.ts
  - One-on-one member sessions with personal knowledge management
  - /member-select, /member-status, /member-equip <skill>, /member-learn <url>
  - Knowledge flow: member learns → writes to <name>-knowledge.md → auto-injected
  - Sources registered in <name>-sources.md (NOT auto-injected, keep context lean)

Read: extensions/themeMap.ts
  - investment-adviser-board → "cyberpunk" (financial trading terminal aesthetic)
  - inv-board-member-session → "cyberpunk" (matches board theme)
  - Theme consistency signals extension purpose + visual branding
```

Also review **drip-board** for simpler board pattern (creative, warm use case).

---

## Step 2 — Gather Requirements

If $1 / $2 are missing, ask:

1. **Name** — what to call it (kebab-case, e.g. "advisory-board", "dev-team", "ops-council")
2. **Type** — which best describes it?
   - **board** — strategic decision-making, mixed expertise, facilitator role
   - **council** — consensus-driven, peer roles, no chair
   - **team** — specialized units with manager, hierarchical
   - **squad** — flat, focused scope, self-organizing

3. **Agents** — list each agent:
   - Name (kebab-case)
   - Role (one-line description)
   - Tools available (read, write, bash, etc.)
   - Model preference (optional)
   - Active by default? (yes/no)

4. **Governance**
   - Discussion time per meeting (minutes)?
   - Any role with special authority (facilitator, manager, CEO, etc.)?
   - Language and tone guidelines?
   - Knowledge management? (agents learn from URLs, maintain personal knowledge bases?)

5. **Presets** — common team configurations?
   - Example: "full" = all agents, "quick" = 2-3 essential, "focused" = specific subset
   - For each preset: which agents included?

6. **Theme & Domain** — visual and functional identity
   - **Domain**: financial (→ "cyberpunk"), creative (→ "rose-pine"), research (→ "everforest"), etc.
   - Determines default Pi extension theme + visual signals to user about group purpose
   - See `extensions/themeMap.ts` for available themes and their meanings

---

## Step 3 — Architecture Plan

Generate a structure:

- **config.yaml** with:
  - `meeting` section (discussion_time_minutes, roles)
  - `board` section (agent list with paths and active status)
  - `presets` section (named team combinations for different use cases)

- **agents/** directory structure:
  - Each agent in its own folder: `agents/<agent-name>/`
    - `<agent-name>.md` — role definition (frontmatter + system prompt)
    - `<agent-name>-knowledge.md` — auto-created learning memory (auto-injected into context during discussions)
    - `<agent-name>-sources.md` — auto-created source registry (for traceability, NOT auto-injected, keeps context lean)

- **Theme integration** (for Pi extensions):
  - Add entry to `extensions/themeMap.ts`:
    ```
    "<group-name>": "<domain-theme>"
    // domain-theme examples: "cyberpunk" (financial), "rose-pine" (creative), "everforest" (research)
    ```
  - Extension will auto-load on session boot via `applyExtensionDefaults(import.meta.url, ctx)`

- **Extension hook** (optional, but recommended for complex groups):
  - **Simple mode**: Use existing `agent-team.ts` + theme mapping (minimal setup)
  - **Advanced mode** (like investment-adviser-board):
    - Create `extensions/boards/<group-name>.ts`
    - Implement tools: `board_begin` (auto-run), `board_discuss` (interactive), `board_next`, `board_report`
    - Optional: Create `extensions/boards/<group-name>-member-session.ts` for 1-on-1 member dialogs with personal knowledge updates

Show the plan and confirm before writing.

---

## Step 4 — Generate the Group

### 4a. Create `config.yaml`

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

### 4b. Create agent folder & files

For each agent, create folder `.pi/<group-name>/agents/<agent-name>/` with:

**1. `<agent-name>.md`** — Role definition:
```markdown
---
name: agent-name
description: One-line role summary
tools: bash,read,write,edit,grep
model: anthropic/claude-sonnet-4-6  (optional)
---

## Role

You are [title] on the [Group Name]. Your responsibility is [focus].

### Guidelines

- [Key principle 1]
- [Key principle 2]
- [Tone and communication style]

### Context

- [Who founded the group]
- [What decisions it makes]
- [Stakes and constraints]
```

**2. `<agent-name>-knowledge.md`** — Auto-created learning memory:
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

**3. `<agent-name>-sources.md`** — Auto-created source registry (NOT auto-injected):
```markdown
# Agent Name — 來源登記表

> 學習來源索引。knowledge.md 中的 [src:NNN] 對應此表的 ID 欄。
> 此檔不會自動注入 context，需要溯源時自行 read。

| ID | 日期 | 類型 | 來源 URL | 說明 |
|----|------|------|----------|------|
```

**Knowledge flow (advanced agents with learning capability):**

For groups supporting persistent learning (like investment-adviser-board):

1. **Agent learns** via:
   - `/member-learn <url>` — extract content, register source, update knowledge
   - `/member-equip <skill>` — write skill usage into knowledge base
   - Conversational updates: agent uses `edit` tool to append insights mid-discussion

2. **Knowledge storage**:
   - `<agent-name>-knowledge.md` — curated insights [src:NNN], frameworks, past analysis
     - Auto-injected into agent context during group discussions
     - Agent updates via `/member-learn` or direct `edit` tool calls
   - `<agent-name>-sources.md` — source registry (ID | Date | Type | URL | Description)
     - NOT auto-injected (keeps context lean)
     - Agents manually `read` for full traceability when needed

3. **Learning commands** (optional, requires member-session extension):
   - `/member-select <name>` — switch to 1-on-1 session with specific agent
   - `/member-learn <url>` — guide agent through learning & knowledge update workflow
   - `/member-equip <skill>` — inject skill documentation into agent's knowledge base
   - `/member-status` — show agent's knowledge base status

4. **Knowledge injection lifecycle**:
   - Agent participates in group meeting → `knowledge.md` injected as context
   - Agent learns between meetings → updates own `knowledge.md` + `sources.md`
   - Next meeting → fresh knowledge automatically included
   - (Sources file never auto-injected, stays clean)

### 4c. Governance & Language

If group uses non-English, add to each agent:

```markdown
**Language:** Always respond in [Language]. Technical terms, names, and system keywords may stay in English.
```

---

## Step 5 — Optional Extension Hook

### Simple Extension (Theme-Only)
- Add entry to `extensions/themeMap.ts` (already done in Step 3)
- Pi will auto-load theme + title on session boot
- Minimal setup, works with `pi -e extensions/boards/investment-adviser-board.ts`

### Custom Extension (Recommended for Complex Groups)

If user wants a full extension (like `drip-board.ts` or `investment-adviser-board.ts`):

Ask:
1. **Interaction model**?
   - **Auto-run mode** (Mode A): User provides brief → AI runs analysis → outputs report
   - **Interactive mode** (Mode B): User sits in as "human member", guides discussion round-by-round
   - **Both** (like investment-adviser-board): tools for both modes

2. **Output format**?
   - Terminal rendering (inline widget)?
   - HTML report file?
   - Markdown discussion memo?

3. **One-on-one workflows**?
   - Optional `<group-name>-member-session.ts` for 1-on-1 learnings with personal knowledge base updates
   - Useful if group members have individual specialization + learning curves

If yes, guide them to `/pi-extension-builder <group-name> "..."` to generate the companion extension.

After generation, **register the extension's theme** in `extensions/themeMap.ts`:
```typescript
// Add this entry
"<group-name>": "<domain-theme>",           // e.g. "investment-adviser-board": "cyberpunk"
"<group-name>-member-session": "<theme>",   // e.g. "inv-board-member-session": "cyberpunk"
```

Theme will auto-apply on session boot.

---

## Step 6 — Validate

After writing, check:

```bash
# Count agents
ls -1 .pi/<group-name>/agents/*.md | wc -l

# Verify config.yaml syntax
python3 -c "import yaml; yaml.safe_load(open('.pi/<group-name>/config.yaml'))"

# Check agent frontmatter
for file in .pi/<group-name>/agents/*.md; do
  grep -E "^(name|description|tools|model):" "$file"
done
```

Confirm with user before finishing.

---

## Report

```
=== Agent Group Created ===

✓ Group:       .pi/<group-name>/
✓ Type:        <board|council|team|squad>
✓ Agents:      <N> agents defined
✓ Config:      .pi/<group-name>/config.yaml
✓ Presets:     <names>  (e.g. full, quick, focused)

Agents:
  - agent-1   (active)
  - agent-2   (active)
  - agent-3   (inactive)

Presets:
  full     → [agent-1, agent-2, agent-3]
  quick    → [agent-1]
  focused  → [agent-1, agent-3]

Next steps:
1. Customize each agent's role prompt in .pi/<group-name>/agents/
2. (Optional) Build extension with: /pi-extension-builder <group-name> "<description>"
3. Test with: pi -e extensions/drip-board.ts (or relevant extension)
```

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| YAML parse error | Bad indentation or syntax | Use 2-space indent, wrap strings in quotes |
| Agent not in preset | Name mismatch | Check agent name in config matches `.md` filename |
| Missing tools | Agent can't execute | Add tool names to `tools:` field in frontmatter |
| Language inconsistency | Mixed instructions | Standardize language in all agent `.md` files |
| Extension not loading | Path not in config | Ensure agent paths relative to `.pi/` |

---

## Examples

### Example 1: Strategic board (like drip-board)

```
/pi-group-builder advisory-board board
```

Follow prompts:
- Agents: CEO, Strategy, Finance, Engineering, Product
- Presets: full, financial, technical
- Language: Mixed (English + internal domain language)

→ Generates 5 agent `.md` files + config.yaml with CEO as facilitator

### Example 2: Engineering team

```
/pi-group-builder dev-team team
```

Follow prompts:
- Agents: Lead, Backend, Frontend, DevOps
- Presets: full, backend-focus, ops-only
- Model: Different model per role (Lead = Opus, others = Sonnet)

→ Generates flat team structure with preset combinations

### Example 3: Quick advisory council

```
/pi-group-builder quick-council council
```

Minimal setup:
- Agents: Analyst, Contrarian, Synthesizer (3 agents)
- Presets: all (everyone)
- Language: English, neutral tone

→ Generates lightweight consensus council

### Example 4: Financial trading board (like investment-adviser-board)

```
/pi-group-builder trading-desk board
```

Advanced setup:
- Type: board (CEO coordinates, specialists contribute)
- Agents: CEO, Macro-Strategist, Technical-Analyst, Risk-Officer (+ optional: Fundamental-Analyst, Prediction-Market-Analyst)
- Presets: full, quick, swing-trade, macro-focus, etc.
- Theme: **cyberpunk** (financial trading terminal aesthetic)
- Knowledge management: YES (agents maintain personal knowledge bases, learn from URLs)
- Extension: Custom `trading-desk.ts` with `board_begin`, `board_discuss`, `board_report` tools
- Optional: Companion `trading-desk-member-session.ts` for 1-on-1 member skill training

→ Generates professional trading terminal with persistent learning capability

---

## Patterns & Archetypes

### Pattern A — Board (Strategic Decision)
- Roles: Facilitator, Specialized advisors (3-7 agents)
- Authority: Facilitator frames, board decides by consensus
- Language: Formal, structured, domain-specific
- Presets: full, executive, focused
- **Theme examples**: "cyberpunk" (investment board), "rose-pine" (creative board), "everforest" (research board)

### Pattern B — Council (Peer Consensus)
- Roles: All equal, rotating chair (optional)
- Authority: Consensus or majority
- Language: Collaborative, respectful disagreement
- Presets: full, core (essential members only)
- **Theme examples**: "everforest" (calm, peer-driven), "ocean-breeze" (open, collaborative)

### Pattern C — Team (Hierarchical)
- Roles: Manager + specialists
- Authority: Manager decides, team executes
- Language: Direct, efficient, results-focused
- Presets: full, standby, minimal
- **Theme examples**: "synthwave" (tech-focused), "dracula" (professional, rich palette)

### Pattern D — Squad (Flat & Focused)
- Roles: All equal, specialized focus
- Authority: Self-organized, decisions by discussion
- Language: Casual, pragmatic, outcome-oriented
- Presets: focused, on-call, shutdown
- **Theme examples**: "tokyo-night" (sharp, focused), "catppuccin-mocha" (warm, relaxed)

---

## Theme Guide (extends themeMap.ts)

Pick a theme that signals group purpose to the user:

| Domain | Use Case | Theme | Vibe |
|--------|----------|-------|------|
| **Financial** | Trading, investment, market analysis | `cyberpunk` | High-tech, data-driven, sharp edges |
| **Creative** | Music, design, content | `rose-pine` | Warm, creative, approachable |
| **Research** | Analysis, science, learning | `everforest` | Calm, focused, nature-inspired |
| **Operations** | DevOps, infrastructure, monitoring | `synthwave` | Retro-tech, neon, high energy |
| **Strategic** | Business, long-term planning | `dracula` | Professional, rich, authoritative |
| **Collaborative** | Cross-team, peer discussions | `ocean-breeze` | Open, connecting, light |
| **Focused** | Single-purpose, intentional | `tokyo-night` | Sharp, clean, professional |

**Selecting a theme:**
1. Identify group's primary domain/purpose
2. Pick matching theme from table above
3. Add to `extensions/themeMap.ts` during Step 3
4. When user launches group extension, Pi auto-loads theme on boot (via `applyExtensionDefaults`)

---

## Summary

The `/pi-group-builder` command:

✓ Guides creation of multi-agent group systems with rich governance
✓ Generates `config.yaml` with meeting settings, board roster, and presets
✓ Creates individual agent role files (.md) with optional knowledge base templates
✓ Supports flexible team configurations via presets
✓ Integrates with Pi themes via `extensions/themeMap.ts` (visual identity)
✓ Recommends extension patterns for advanced interaction models:
  - **Simple**: Theme-only integration (auto-loads on session boot)
  - **Advanced**: Full extension with `board_begin`, `board_discuss`, `board_report` tools (like investment-adviser-board)
  - **Learning-enabled**: Optional member-session extension for 1-on-1 skill training + persistent knowledge
✓ Validates YAML syntax and agent frontmatter
✓ Supports persistent learning workflows (agents update personal knowledge bases between meetings)

**Use to**:
- Build investment decision boards with persistent learning (theme: cyberpunk)
- Create creative team councils with shared decision-making (theme: rose-pine)
- Design research groups with deep analysis (theme: everforest)
- Organize dev teams with hierarchical structure (theme: synthwave)
- Launch specialized squads with flat self-organization (theme: tokyo-night)
