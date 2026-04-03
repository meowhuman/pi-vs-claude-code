---
model: sonnet
description: Diagnose multi-agent use cases and guide setup of Claude Code, Pi, or Overstory systems
argument-hint: [usecase] (optional)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent
---

# Purpose

Understand your multi-agent workflow, recommend the best system (Claude Code Team, Pi Board/Group, or Overstory), and guide you through building it with proper scaffolding, configuration, and integration.

## Variables

```
USECASE:           $1  (optional brief description)
CC_AGENTS_DIR:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/agents
CC_TEAMS_JSON:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/teams/teams.json
CC_COMMANDS_DIR:   /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/commands
PI_AGENTS_DIR:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi/agents
PI_BOARDS_DIR:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi
EXTENSIONS_DIR:    /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions
```

## Instructions

### System Selection Logic

| System | Best For | Tier | Agents | Config | Entry |
|--------|----------|------|--------|--------|-------|
| **Claude Code** | Structured workflows, task-driven, internal tools | 3-tier (orchestrator → leads → workers) | 3-9 agents | teams.json + .md files | `/agent-system-build: claude-code` |
| **Pi Board** | Discovery, analysis, interactive exploration, multi-perspective | Director + scouts/experts | 2-6 agents | config.yaml + agents | `/agent-system-build: pi-board` |
| **Pi Group** | Large-scale coordination, domain-specific, multi-function | Board + member sessions | 4-15 agents | group config + knowledge | `/agent-system-build: pi-group` |
| **Overstory** | Real-time collab, synchronous coordination (research needed) | TBD | TBD | TBD | *Not yet implemented* |

---

## Workflow

### 1. Diagnose Your Use Case

Ask these discovery questions if USECASE is missing or vague:

1. **Goal** — What's the core task?
   - Structured planning & execution? → Claude Code
   - Research & discovery? → Pi Board
   - Large system analysis? → Pi Group
   
2. **Workflow Pattern** — How do agents collaborate?
   - Sequential (A → B → C)? → Claude Code (task handoff)
   - Parallel (all explore simultaneously)? → Pi Board (preset)
   - Hub-and-spoke (centralized orchestration)? → Pi Group
   
3. **Human Involvement** — Where do you fit?
   - Outside system, delegating tasks? → Claude Code (orchestrator role)
   - Inside system, as a participant? → Pi Board (human member in discussion)
   - Observing coordination? → Pi Group (passive monitoring)
   
4. **Agent Count** — How many agents needed?
   - 3-9 agents, hierarchical roles? → Claude Code
   - 2-6 agents, specialized scouts? → Pi Board
   - 4-15 agents, deep knowledge bases? → Pi Group

5. **Output Priority** — What matters most?
   - Documented decisions & artifacts? → Claude Code (specs, PRDs, tests)
   - Interactive exploration & insights? → Pi Board (discussion, real-time discovery)
   - Comprehensive analysis & knowledge graph? → Pi Group (reports, memory, signals)

---

### 2. Recommend System

Based on diagnosis, suggest the best fit with reasoning.

**Claude Code Team Example:**
```
✓ Recommended: Claude Code
- Reason: Structured 3-tier workflow for feature planning
- Leads: planning-lead, engineering-lead, validation-lead
- Workers: 3 planning (product-manager, ux-researcher), 4 engineering, 2 validation
- Config: .claude/teams/teams.json + agent role definitions
```

**Pi Board Example:**
```
✓ Recommended: Pi Board (coding-focused)
- Reason: Multi-perspective code analysis and design review
- Agents: director (orchestrator) + coding-ai-scout (code expert) + system-analyst
- Presets: quick, full, detailed
- Config: .pi/ai-tools-board/config.yaml with board + agents
```

**Pi Group Example:**
```
✓ Recommended: Pi Group (investment analysis)
- Reason: Deep domain expertise, knowledge memory, specialist coordintion
- Agents: 8 specialists (macro, fundamental, technical, risk, intelligence, prediction, backtest)
- Presets: full, swing-trade, macro-focus, event-driven, quick
- Config: .pi/investment-adviser-board/ with config.yaml + 8 agent definitions + knowledge management
```

---

### 3. Generate Build Plan

Once system is selected, show the build path:

#### Claude Code Path
```
Use the /cc-agent-team-setup command to:
1. Create lead agents (planning-lead, engineering-lead, validation-lead)
2. Create 2-7 worker agents based on needs
3. Register in teams.json with roles and permissions
4. Set up memory scopes (project, user)
5. Test team creation with TeamCreate tool
```

#### Pi Board Path
```
Use the /pi-group-builder command to:
1. Name the board (kebab-case, e.g., "ai-tools-board")
2. Define board type: "board" (analysis) or "council" (governance)
3. Create director agent (orchestrator)
4. Add 1-5 scout/expert agents
5. Define governance presets (quick, full, detailed, etc.)
6. Generate config.yaml + agent definitions + extension hooks
```

#### Pi Group Path
```
Use the /pi-group-builder command to:
1. Name the group (kebab-case, e.g., "investment-adviser-board")
2. Define group type: "group" (multi-agent) or "squad" (task force)
3. Create 4-15 specialist agents with knowledge bases
4. Set up member session extension for one-on-one coaching
5. Define presets and discussion timeframes
6. Auto-inject <agent>-knowledge.md into context for memory augmentation
```

---

### 4. Execute Build

Present step-by-step scaffolding:

**For Claude Code:**
```bash
# Step 1: Create agents
/cc-agent-team-setup your-agent "description"

# Step 2: Register team (auto-done by setup command)

# Step 3: Test with TaskCreate (in a task or manual testing)
```

**For Pi:**
```bash
# Step 1: Build board/group structure
/pi-group-builder your-board-name board

# Step 2: Create extension hooks (if needed)
/pi-extension-builder your-board-extension "description"

# Step 3: Wire into themeMap.ts (auto-suggested)

# Step 4: Run justfile entry
just your-board-name
```

---

### 5. Validate & Report

After scaffolding:

1. **Verify Agent Files** — Check all agents exist
2. **Validate Config** — Parse YAML/JSON for syntax
3. **Test Entry Point** — Run `pi -e extensions/board.ts` or invoke team
4. **Generate Report** — Show system summary

---

## Report

```
=== Agent System Built ===

✓ System Type: [Claude Code Team | Pi Board | Pi Group]
✓ Agent Count: [N agents]
✓ Tier/Presets: [3-tier | [quick, full, analysis]]
✓ Config Path: [path/to/config]
✓ Entry Point: [/your-team | pi -e extensions/board.ts]

✓ Next Steps:
  1. Customize agent role definitions in [config path]
  2. Test entry point with sample input
  3. For Pi: run `just [board-name]` to see it in action
  4. For Claude Code: create a task and invoke team

✓ Documentation:
  - Agent roles: [path/to/agents/*.md]
  - Configuration: [path/to/config]
  - Example usage: See README.md in [path]
```

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| System unclear | Conflicting requirements | Re-run discovery questions, clarify priority (structure vs. exploration) |
| Config syntax error | YAML/JSON parse fail | Review config template, validate with `yamllint` or JSON parser |
| Missing agent file | Setup incomplete | Re-run scaffold command, check agents/ directory exists |
| Command not found | /pi-group-builder or /cc-agent-team-setup missing | Verify skills are installed with `/help` |
| Circular dependencies | Agent A → B → A | Review team structure, break cycle with explicit task boundaries |

---

## Examples

### Example 1: Feature Planning (Claude Code)

```
User Input: /agent-system-build "We need to plan and build a new authentication system"

Discovery → Recommend Claude Code
  - Sequential workflow: requirements → design → implementation → review
  - 3 Leads + 6 Workers
  - Focus: documented specs, decisions, test coverage

Build Plan:
  1. Create planning-lead → delegates to product-manager, ux-researcher
  2. Create engineering-lead → delegates to frontend-dev, backend-dev
  3. Create validation-lead → delegates to qa-engineer, security-reviewer
  4. Register in teams.json
  5. Run /cc-agent-team-setup for each agent
  
Output: Ready-to-use 3-tier team, invoke with orchestrator role
```

### Example 2: Code Analysis (Pi Board)

```
User Input: /agent-system-build "We want multiple AI experts to analyze and review our Python codebase"

Discovery → Recommend Pi Board
  - Parallel exploration: different perspectives simultaneously
  - Director + 2-3 scouts
  - Focus: interactive discovery, real-time insights

Build Plan:
  1. Create board: ai-analysis-board
  2. Create director agent (orchestrator)
  3. Create coding-ai-scout (code patterns)
  4. Create system-analyst (architecture)
  5. Generate config.yaml + agent definitions
  6. Wire into extensions/

Output: Pi board with presets (quick, full, detailed)
```

### Example 3: Investment Analysis (Pi Group)

```
User Input: /agent-system-build "Multi-agent investment system with macro, technical, and fundamental analysis"

Discovery → Recommend Pi Group
  - Large coordinated team, deep domain knowledge
  - 8 specialists + knowledge memory
  - Focus: comprehensive analysis, memory augmentation, multiple perspectives

Build Plan:
  1. Create group: investment-analyse-board
  2. Create 8 agents: CEO, macro-strategist, fundamental-analyst, etc.
  3. Set up knowledge memory: <agent>-knowledge.md auto-injection
  4. Define presets: full, swing-trade, macro-focus, quick
  5. Generate member-session extension for coaching
  6. Wire discussion timeframe and damage-control rules

Output: Full investment analysis system with governance
```

---

## Summary

The `/agent-system-build` command helps you:

✓ **Diagnose** multi-agent needs through guided discovery  
✓ **Recommend** Claude Code, Pi Board, or Pi Group based on workflow patterns  
✓ **Scaffold** the system with agents, config, and extensions  
✓ **Integrate** with existing tools (/cc-agent-team-setup, /pi-group-builder, /pi-extension-builder)  
✓ **Validate** configuration and test entry points  
✓ **Report** system summary and next steps  

Use this command before building any multi-agent system to ensure you select the right architecture for your workflow.
