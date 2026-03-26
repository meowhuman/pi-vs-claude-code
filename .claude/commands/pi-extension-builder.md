---
description: Build custom Pi coding agent extensions — single agent tools, UI widgets, event hooks, or full multi-agent pipelines. Reads the live codebase and generates ready-to-run .ts files.
argument-hint: [extension-name] [one-line description]
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Purpose

Guide the user through designing and generating a Pi extension. Study the live codebase first, then interview the user, then produce a working `.ts` file plus all required wiring (themeMap, justfile, agent YAML if needed).

## Variables

```
EXTENSION_NAME: $1  (kebab-case, e.g. "focus-timer")
DESCRIPTION:    $2  (one-line, e.g. "Pomodoro timer with footer countdown")
EXTENSIONS_DIR: /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions
COMMANDS_DIR:   /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/commands
AGENTS_DIR:     /Users/terivercheung/Documents/AI/pi-vs-claude-code/.pi/agents
JUSTFILE:       /Users/terivercheung/Documents/AI/pi-vs-claude-code/justfile
THEMEMAP:       /Users/terivercheung/Documents/AI/pi-vs-claude-code/extensions/themeMap.ts
```

---

## Step 1 — Load Codebase Context

Read these files to ground yourself in the live codebase before generating anything:

```
Read: EXTENSIONS_DIR/themeMap.ts          # theme assignments + applyExtensionDefaults
Read: EXTENSIONS_DIR/tool-counter.ts      # footer pattern, session traversal
Read: EXTENSIONS_DIR/purpose-gate.ts      # input blocking, widget, before_agent_start
Read: EXTENSIONS_DIR/tilldone.ts          # registerTool, custom TUI component, state reconstruction
Read: EXTENSIONS_DIR/agent-chain.ts       # multi-agent spawn, YAML parsing, subprocess, footer widget
Read: JUSTFILE                             # existing entry points
Read: AGENTS_DIR/agent-chain.yaml         # YAML chain format
Bash: ls EXTENSIONS_DIR/*.ts              # see all existing extensions
```

---

## Step 2 — Gather Requirements

If $1 / $2 are missing, ask:

1. **Name** — what to call it (kebab-case)
2. **Purpose** — one sentence: what problem does it solve?
3. **Type** — which pattern fits best? (show the menu below)
4. **Tools needed** — does it expose tools the agent can call? What do they do?
5. **UI surfaces** — footer? widget? status line? commands? shortcuts?
6. **State** — does it need persistent state across branch switches?
7. **Multi-agent** — if yes: how many agents, what role, what model each?

### Extension Type Menu

```
A) Tool extension      — registers one or more agent-callable tools (like polymarket.ts)
B) UI extension        — footer / widget / status overlay (like tool-counter.ts)
C) Gate extension      — blocks or transforms agent input/output (like purpose-gate.ts)
D) Discipline ext.     — enforces a workflow (like tilldone.ts)
E) Multi-agent chain   — sequential pipeline of specialist agents (like agent-chain.ts)
F) Multi-agent team    — parallel team with dispatcher (like agent-team.ts)
G) Hybrid              — combination of the above
```

---

## Step 3 — Architecture Plan

Based on type, outline:

- Which events to hook (`session_start`, `before_agent_start`, `agent_end`, `input`, `tool_call`, `tool_execution_end`)
- Which tools to register (name, parameters, execute logic)
- Which UI surfaces to build
- State variables needed
- For multi-agent: agent .md files needed + chain YAML or team config

Show the plan to the user and confirm before writing code.

---

## Step 4 — Generate the Extension

### 4a. Write `extensions/<name>.ts`

Use this skeleton — fill in only what's needed, omit empty sections:

```typescript
/**
 * <ExtensionName> — <one-line description>
 *
 * <longer description if needed>
 *
 * Commands:  /<cmd>  — description
 * Shortcuts: Ctrl+X  — description
 *
 * Usage: pi -e extensions/<name>.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";               // for enum params
import { Type } from "@sinclair/typebox";                        // for tool params
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui"; // for TUI
import { spawn } from "child_process";                           // for subprocesses
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";

// ── State ──────────────────────────────────────────────────────────────────────

// (module-level state — survives branch switches, reconstructed from session if needed)

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Boot ──────────────────────────────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    // reconstruct state from session history if needed
    // ctx.ui.setStatus / setFooter / setWidget / setTitle
  });

  // ── State reconstruction (branch switch) ─────────────────────────────────
  // pi.on("session_switch", async (_event, ctx) => { /* same as session_start */ });
  // pi.on("session_fork",   async (_event, ctx) => { /* same as session_start */ });
  // pi.on("session_tree",   async (_event, ctx) => { /* same as session_start */ });

  // ── Tools ─────────────────────────────────────────────────────────────────
  pi.registerTool({
    name: "tool_name",
    label: "Human Label",
    description: "What the agent should call this for",
    parameters: Type.Object({
      param: Type.String({ description: "..." }),
      optional: Type.Optional(Type.Number({ description: "..." })),
      choice: Type.Optional(StringEnum(["a", "b", "c"])),
    }),
    async execute(toolCallId, params: any, signal, onUpdate, ctx) {
      // ... do work ...
      return {
        content: [{ type: "text" as const, text: "result" }],
        details: { /* serialized to session, used for state reconstruction */ },
      };
    },
    renderCall(args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("tool_name ")) + theme.fg("dim", String((args as any).param ?? "")), 0, 0);
    },
    renderResult(result, options, theme) {
      const text = result.content?.[0]?.text ?? "";
      return new Text(theme.fg("muted", text), 0, 0);
    },
  });

  // ── System Prompt ─────────────────────────────────────────────────────────
  pi.on("before_agent_start", async (_event, _ctx) => {
    return {
      appendSystemPrompt: `\n\n## <Extension Context>\n...`,
      // OR: systemPrompt: "full replacement" (replaces Pi default + CLAUDE.md)
    };
  });

  // ── Input gate ────────────────────────────────────────────────────────────
  // pi.on("input", async (_event, ctx) => {
  //   if (blocked) { ctx.ui.notify("...", "warning"); return { action: "handled" }; }
  //   return { action: "continue" };
  // });

  // ── Tool gate ─────────────────────────────────────────────────────────────
  // pi.on("tool_call", async (event, _ctx) => {
  //   if (shouldBlock(event)) return { block: true, reason: "..." };
  // });

  // ── Post-agent nudge ──────────────────────────────────────────────────────
  // pi.on("agent_end", async (_event, ctx) => { /* nudge if tasks remain */ });

  // ── Commands ──────────────────────────────────────────────────────────────
  pi.registerCommand("cmd-name", {
    description: "What /cmd-name does",
    handler: async (args, ctx) => {
      // ctx.ui.select / input / confirm / notify / custom
    },
  });

  // ── Shortcuts ─────────────────────────────────────────────────────────────
  // pi.registerShortcut("ctrl+x", { description: "...", handler: async (ctx) => {} });
}
```

### Key API Reference (encode this to avoid re-reading)

**Events & return shapes:**
```
session_start          → return {}  (or nothing)
before_agent_start     → return { systemPrompt? } | { appendSystemPrompt? }
agent_end              → return {}
input                  → return { action: "continue" | "handled" }
tool_call              → return { block: true, reason: string } | {}
tool_execution_end     → return {}
session_switch/fork/tree → return {}
```

**ctx.ui API:**
```typescript
ctx.ui.setFooter((tui, theme, footerData) => ({
  dispose: footerData.onBranchChange(() => tui.requestRender()),
  invalidate() {},
  render(width: number): string[] { return [line1, line2]; }
}))

ctx.ui.setWidget("name", () => ({
  render(width: number): string[] { return lines; },
  invalidate() {}
}), { placement: "belowEditor", dismissAfter: 3000 })

ctx.ui.setStatus("key", "label text")
ctx.ui.setTitle("π - name")
ctx.ui.notify("message", "info" | "warning" | "error" | "success")
await ctx.ui.select("Label", ["option1", "option2"])      // → string | undefined
await ctx.ui.input("Label", "placeholder")                // → string | undefined
await ctx.ui.confirm("Label", "message", timeoutMs)       // → boolean
await ctx.ui.custom<T>(component)                         // custom TUI component

// Theme colors: accent | success | warning | error | dim | muted | borderMuted | toolTitle
theme.fg("accent", text)
theme.bold(text)
footerData.getGitBranch()
footerData.onBranchChange(cb) // returns unsubscribe fn
```

**Session traversal (state reconstruction):**
```typescript
for (const entry of ctx.sessionManager.getBranch()) {
  if (entry.type === "tool_result" && entry.toolName === "my_tool") {
    const details = entry.result.details as MyDetails;
    // restore state
  }
}
```

**TUI imports:**
```typescript
import { Text, Container, DynamicBorder, truncateToWidth, visibleWidth, matchesKey } from "@mariozechner/pi-tui";
import { StringEnum } from "@mariozechner/pi-ai";
import { Type } from "@sinclair/typebox";
```

---

### 4b. Multi-Agent: Write agent `.md` files

Each agent in `.pi/agents/<name>.md`:

```markdown
---
name: agent-name
description: What this agent does
tools: read,grep,find,ls,bash,edit,write
model: anthropic/claude-sonnet-4-6   (optional — override per agent)
---

You are a specialist in X. Your role is Y.
Guidelines:
- ...
```

### 4c. Multi-Agent Chain: Add to `agent-chain.yaml`

```yaml
my-chain:
  description: "What this pipeline does"
  steps:
    - agent: planner
      prompt: "Plan the implementation for: $INPUT"
    - agent: builder
      prompt: "Implement this plan:\n\n$INPUT"
    - agent: reviewer
      prompt: "Review this implementation:\n\nOriginal: $ORIGINAL\n\nWork:\n$INPUT"
```

Variables: `$INPUT` = previous step output, `$ORIGINAL` = user's original prompt.

---

## Step 5 — Wire It Up

### 5a. Add theme to `themeMap.ts`

```typescript
// In THEME_MAP object:
"<extension-name>": "cyberpunk",  // or: midnight-ocean | dracula | everforest | gruvbox
                                   //     ocean-breeze | rose-pine | catppuccin-mocha
                                   //     nord | synthwave | tokyo-night
```

Choose theme by vibe:
| Theme | Best for |
|-------|----------|
| `cyberpunk` | data terminals, trading, metrics |
| `midnight-ocean` | pipelines, sequential, focused |
| `dracula` | orchestration, team agents |
| `everforest` | calm discipline, task tracking |
| `tokyo-night` | gates, intent, focus |
| `synthwave` | general purpose, techy |
| `rose-pine` | creative, warm |
| `gruvbox` | safety, auditing |

### 5b. Add entry to `justfile`

```makefile
# <N+1>. <Extension name>: <one-line description>
ext-<name>:
    pi -e extensions/<name>.ts

# Or stacked with common companions:
ext-<name>:
    pi -e extensions/<name>.ts -e extensions/theme-cycler.ts
```

---

## Step 6 — Validate

Run these checks after writing:

```bash
# Count registered surface calls
node --input-type=module --eval "
import { readFileSync } from 'fs';
const s = readFileSync('extensions/<name>.ts', 'utf8');
console.log('registerTool:', (s.match(/registerTool\(/g)||[]).length);
console.log('registerCommand:', (s.match(/registerCommand\(/g)||[]).length);
console.log('pi.on:', (s.match(/pi\.on\(/g)||[]).length);
console.log('lines:', s.split('\n').length);
"
```

Confirm with user before finishing.

---

## Report

```
=== Pi Extension Built ===

✓ Extension:  extensions/<name>.ts  (<N> lines)
✓ Theme:      themeMap.ts → "<theme>"
✓ Justfile:   just ext-<name>
✓ Agents:     .pi/agents/<name>.md  (if multi-agent)
✓ Chain YAML: .pi/agents/agent-chain.yaml  (if chain)

Tools registered:     <N>
Commands registered:  <N>
Events hooked:        <N>

Run with:
  just ext-<name>
  pi -e extensions/<name>.ts

Next: restart Pi and test each tool / command
```

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module` | Missing import | Check import path, use `@mariozechner/pi-*` |
| Tool not showing up | Not called at top level of export fn | Move `registerTool` out of event handlers |
| State lost on branch switch | No reconstruction logic | Add `session_switch` handler, use `details` in tool results |
| Theme not applying | Name not in THEME_MAP | Add entry to themeMap.ts |
| Footer not rendering | Missing `dispose` or `render` | Return `{ dispose, invalidate, render }` object |
| Multi-agent not finding agent | Wrong name in YAML | Agent name in YAML must match `name:` field in .md frontmatter |

---

## Patterns Quick Reference

### Pattern A — Minimal Tool Extension
Hooks: `session_start`, `before_agent_start`
Registers: N tools
No UI beyond status line

### Pattern B — Footer + Status Extension
Hooks: `session_start`, `tool_execution_end`
UI: `setFooter` (2 lines), `setStatus`
No tools

### Pattern C — Gate Extension
Hooks: `session_start`, `input` (blocks until condition met), `before_agent_start` (injects purpose)
UI: `setWidget` (persistent purpose display)

### Pattern D — Discipline Extension
Hooks: `session_start`, `before_agent_start`, `agent_end`, `tool_call` (blocks non-task tools)
Registers: 1 tool (task manager)
UI: footer (task list) + widget (current task) + status (count)

### Pattern E — Multi-Agent Chain (via agent-chain.ts)
Uses: existing `agent-chain.ts` extension + new agents in `.pi/agents/` + new chain in YAML
No new .ts file needed — just add agents and chain config

### Pattern F — New Multi-Agent Orchestrator
Hooks: `session_start`, `before_agent_start`
Registers: 1 tool (`run_pipeline` or similar) that spawns `pi` subprocesses
UI: footer showing step progress
Needs: agent .md files + subprocess spawning via `child_process.spawn`

---

## Examples

### Example 1: Simple tool extension
```
/pi-extension-builder stock-ticker "Live stock price tool using yfinance"
```
→ Generates tool extension with `get_price`, `get_history` tools, minimal footer

### Example 2: Gate extension
```
/pi-extension-builder scope-lock "Forces agent to declare scope before any file edits"
```
→ Generates gate that blocks `tool_call` for edit/write until scope is declared

### Example 3: Multi-agent pipeline
```
/pi-extension-builder research-pipeline "Scout → Summarize → Draft → Review research pipeline"
```
→ Generates 4 agent .md files + agent-chain.yaml entry (uses existing agent-chain.ts)
