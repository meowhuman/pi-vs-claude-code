/**
 * Pi Extension Builder — Generate new Pi extensions using GPT-5.4
 *
 * Spawns a GPT-5.4 subagent that reads the live codebase (themeMap, existing
 * extensions, justfile) and writes a complete new .ts extension file plus all
 * required wiring (themeMap entry, justfile entry, agent .md files if needed).
 *
 * Commands:  /builder-status  — show last build result
 *
 * Usage: pi -e extensions/pi-extension-builder.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Constants ──────────────────────────────────────────────────────────────────

const BUILDER_MODEL = "openai/gpt-5.4";
const BUILDER_TOOLS = "read,grep,find,ls,bash,edit,write";

// Embedded system prompt injected into the GPT-5.4 subagent
const BUILDER_SYSTEM_PROMPT = `You are a Pi Extension Builder — an expert in writing Pi Coding Agent extensions.

## Your Job
When given a description of a new extension, you will:
1. Read the existing codebase to understand patterns (themeMap.ts, existing .ts extensions, justfile)
2. Write a complete, working extensions/<name>.ts file
3. Add the extension to extensions/themeMap.ts THEME_MAP
4. Add a justfile entry for \`just ext-<name>\`
5. Write any required .pi/agents/<name>.md files if it's a multi-agent extension

## Key Files to Read First
- extensions/themeMap.ts — theme assignments, applyExtensionDefaults usage
- extensions/tool-counter.ts — footer pattern (setFooter, footerData, getBranch)
- extensions/purpose-gate.ts — input gate, widget, before_agent_start
- extensions/tilldone.ts — registerTool, custom TUI, state reconstruction
- extensions/agent-chain.ts — multi-agent spawn, subprocess, widget
- justfile — existing entry numbering and format

## Extension Skeleton

\`\`\`typescript
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
  });

  pi.registerTool({ name, label, description, parameters, execute, renderCall, renderResult });
  pi.registerCommand("cmd", { description, handler });
  pi.on("before_agent_start", async (_event, _ctx) => ({ appendSystemPrompt: "..." }));
  pi.on("agent_end", async (_event, _ctx) => {});
}
\`\`\`

## API Rules
- registerTool / registerCommand MUST be called at the TOP LEVEL of the export function (not inside event handlers)
- session_start → return nothing
- before_agent_start → return { systemPrompt? } or { appendSystemPrompt? }
- input → return { action: "continue" | "handled" }
- tool_call → return { block: true, reason: string } or {}

## ctx.ui API
\`\`\`
ctx.ui.setFooter((tui, theme, footerData) => ({ dispose, invalidate, render(width): string[] }))
ctx.ui.setWidget("name", (tui, theme) => ({ render(width): string[], invalidate }), { placement?, dismissAfter? })
ctx.ui.setStatus("key", "label")
ctx.ui.setTitle("π - name")
ctx.ui.notify("msg", "info"|"warning"|"error"|"success")
await ctx.ui.select("Label", ["opt1","opt2"])
await ctx.ui.input("Label", "placeholder")
await ctx.ui.confirm("Label", "msg", timeoutMs)
theme.fg("accent"|"success"|"warning"|"error"|"dim"|"muted"|"borderMuted"|"toolTitle", text)
theme.bold(text)
footerData.getGitBranch()
footerData.onBranchChange(cb)  // returns unsubscribe fn
\`\`\`

## Theme Choices
| Theme | Best for |
|-------|----------|
| cyberpunk | data terminals, trading, AI tools |
| midnight-ocean | pipelines, sequential, focused |
| dracula | orchestration, team agents |
| everforest | calm discipline, task tracking |
| tokyo-night | gates, intent, focus |
| synthwave | general purpose, techy |
| rose-pine | creative, warm |
| gruvbox | safety, auditing |

## Quality Checklist
- applyExtensionDefaults(import.meta.url, ctx) called in session_start
- All tools registered at top level (never inside event handlers)
- themeMap.ts updated with new extension name
- justfile entry added
- File ends with trailing newline
- 2-space indentation (TypeScript)`;

// ── State ──────────────────────────────────────────────────────────────────────

let buildStatus: "idle" | "building" | "done" | "error" = "idle";
let lastBuilt = "";
let lastElapsed = 0;
let footerInvalidate: (() => void) | null = null;

// ── Subprocess ────────────────────────────────────────────────────────────────

function runBuilder(
  task: string,
  cwd: string,
  onChunk: (text: string) => void,
): Promise<{ output: string; exitCode: number; elapsed: number }> {
  const args = [
    "--mode", "json",
    "-p",
    "--no-session",
    "--no-extensions",
    "--model", BUILDER_MODEL,
    "--tools", BUILDER_TOOLS,
    "--thinking", "off",
    "--append-system-prompt", BUILDER_SYSTEM_PROMPT,
    task,
  ];

  const textChunks: string[] = [];
  const startTime = Date.now();

  return new Promise((resolve) => {
    const proc = spawn("pi", args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });

    let buffer = "";

    proc.stdout!.setEncoding("utf-8");
    proc.stdout!.on("data", (chunk: string) => {
      buffer += chunk;
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.type === "message_update") {
            const delta = event.assistantMessageEvent;
            if (delta?.type === "text_delta") {
              const text = delta.delta || "";
              textChunks.push(text);
              onChunk(text);
            }
          }
        } catch { }
      }
    });

    proc.stderr!.setEncoding("utf-8");
    proc.stderr!.on("data", () => { });

    proc.on("close", (code) => {
      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer);
          if (event.type === "message_update") {
            const delta = event.assistantMessageEvent;
            if (delta?.type === "text_delta") textChunks.push(delta.delta || "");
          }
        } catch { }
      }
      resolve({
        output: textChunks.join(""),
        exitCode: code ?? 1,
        elapsed: Date.now() - startTime,
      });
    });

    proc.on("error", (err) => {
      resolve({
        output: `Error spawning builder: ${err.message}`,
        exitCode: 1,
        elapsed: Date.now() - startTime,
      });
    });
  });
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let ctx: any;

  function refreshUI() {
    if (ctx) ctx.ui.setStatus("builder", `Builder: ${buildStatus}`);
    if (footerInvalidate) footerInvalidate();
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  pi.on("session_start", async (_event, _ctx) => {
    applyExtensionDefaults(import.meta.url, _ctx);
    ctx = _ctx;
    buildStatus = "idle";
    lastBuilt = "";

    _ctx.ui.setStatus("builder", `Builder: ${BUILDER_MODEL.split("/").pop()}`);

    _ctx.ui.setFooter((_tui, theme, footerData) => {
      const unsub = footerData.onBranchChange(() => _tui.requestRender());
      footerInvalidate = () => _tui.requestRender();

      return {
        dispose: () => { unsub(); footerInvalidate = null; },
        invalidate() {},
        render(width: number): string[] {
          const modelShort = BUILDER_MODEL.split("/").pop() || BUILDER_MODEL;

          const statusColor =
            buildStatus === "idle" ? "dim"
            : buildStatus === "building" ? "accent"
            : buildStatus === "done" ? "success"
            : "error";
          const statusIcon =
            buildStatus === "idle" ? "○"
            : buildStatus === "building" ? "●"
            : buildStatus === "done" ? "✓"
            : "✗";

          const left =
            theme.fg("accent", " ext-builder") +
            theme.fg("dim", " · ") +
            theme.fg("muted", modelShort) +
            theme.fg("dim", " · ") +
            theme.fg(statusColor, `${statusIcon} ${buildStatus}`);

          const rightParts =
            (lastBuilt ? theme.fg("dim", lastBuilt + " ") : "") +
            (lastElapsed ? theme.fg("dim", `${Math.round(lastElapsed / 1000)}s `) : "");

          const pad = " ".repeat(
            Math.max(1, width - visibleWidth(left) - visibleWidth(rightParts))
          );

          return [truncateToWidth(left + pad + rightParts, width, "")];
        },
      };
    });

    _ctx.ui.notify(
      `Pi Extension Builder loaded\n` +
      `Model: ${BUILDER_MODEL}\n\n` +
      `Tell me what extension to build:\n` +
      `"Build a focus-timer extension — Pomodoro countdown in the footer"\n\n` +
      `/builder-status  — show last build result`,
      "info",
    );
  });

  // ── build_extension Tool ──────────────────────────────────────────────────
  pi.registerTool({
    name: "build_extension",
    label: "Build Extension",
    description:
      `Generate a complete Pi extension using GPT-5.4. ` +
      `The builder reads the live codebase (themeMap, existing extensions, justfile) ` +
      `then writes the .ts file, themeMap entry, and justfile entry. ` +
      `Use this when the user asks to create or build a new Pi extension.`,
    parameters: Type.Object({
      name: Type.String({
        description: "Extension name in kebab-case (e.g. focus-timer, stock-ticker)",
      }),
      description: Type.String({
        description: "One sentence: what problem does it solve and what does it do?",
      }),
      type: Type.Optional(StringEnum([
        "tool",
        "ui",
        "gate",
        "discipline",
        "multi-agent-chain",
        "multi-agent-team",
        "hybrid",
      ], {
        description: "Extension type (default: hybrid). tool=agent-callable tools, ui=footer/widget, gate=blocks input/output, discipline=workflow enforcement, multi-agent-chain=sequential pipeline, multi-agent-team=parallel team",
      })),
      extra: Type.Optional(Type.String({
        description: "Additional requirements: specific tools, UI surfaces, agent names, model preferences, shortcuts, etc.",
      })),
    }),

    async execute(_toolCallId, params: any, _signal, onUpdate, _ctx) {
      const { name, description, type = "hybrid", extra = "" } = params as {
        name: string;
        description: string;
        type?: string;
        extra?: string;
      };

      buildStatus = "building";
      lastBuilt = name;
      lastElapsed = 0;
      refreshUI();

      const task =
        `Build a complete Pi extension with these specs:\n\n` +
        `Name: ${name}\n` +
        `Description: ${description}\n` +
        `Type: ${type}\n` +
        (extra ? `Additional requirements: ${extra}\n` : "") +
        `\n` +
        `Steps:\n` +
        `1. Read extensions/themeMap.ts, extensions/tool-counter.ts, extensions/purpose-gate.ts, ` +
        `extensions/tilldone.ts, extensions/agent-chain.ts, and justfile to understand patterns\n` +
        `2. Run: ls extensions/*.ts  to see all existing extensions\n` +
        `3. Write the complete extension to extensions/${name}.ts\n` +
        `4. Add "${name}" entry to the THEME_MAP in extensions/themeMap.ts\n` +
        `5. Add a justfile entry: ext-${name}\n` +
        `6. If multi-agent: write required .pi/agents/*.md files\n` +
        `7. Confirm all files are written and report what was created`;

      let lastChunk = "";
      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `Building "${name}" with ${BUILDER_MODEL}…` }],
          details: { name, description, type, status: "building" },
        });
      }

      const result = await runBuilder(task, _ctx.cwd, (chunk) => {
        lastChunk = chunk;
        if (onUpdate) {
          onUpdate({
            content: [{ type: "text", text: lastChunk }],
            details: { name, description, type, status: "building" },
          });
        }
      });

      buildStatus = result.exitCode === 0 ? "done" : "error";
      lastElapsed = result.elapsed;
      refreshUI();

      const truncated =
        result.output.length > 8000
          ? result.output.slice(0, 8000) + "\n\n… [truncated]"
          : result.output;

      const summary =
        `[ext-builder] ${name} — ${buildStatus} in ${Math.round(result.elapsed / 1000)}s`;

      return {
        content: [{ type: "text", text: `${summary}\n\n${truncated}` }],
        details: {
          name,
          description,
          type,
          status: buildStatus,
          elapsed: result.elapsed,
          fullOutput: result.output,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const name = a.name || "?";
      const type = a.type || "hybrid";
      return new Text(
        theme.fg("toolTitle", theme.bold("build_extension ")) +
        theme.fg("accent", name) +
        theme.fg("dim", ` [${type}] `) +
        theme.fg("muted", a.description?.slice(0, 50) || ""),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (!details) {
        const t = result.content?.[0];
        return new Text(t?.type === "text" ? t.text : "", 0, 0);
      }

      if (options.isPartial || details.status === "building") {
        return new Text(
          theme.fg("accent", `● building`) +
          theme.fg("dim", ` ${details.name || "extension"}…`),
          0, 0,
        );
      }

      const icon = details.status === "done" ? "✓" : "✗";
      const color = details.status === "done" ? "success" : "error";
      const elapsed = typeof details.elapsed === "number"
        ? Math.round(details.elapsed / 1000)
        : 0;

      const header =
        theme.fg(color, `${icon} ${details.name}`) +
        theme.fg("dim", ` [${details.type}] ${elapsed}s`);

      if (options.expanded && details.fullOutput) {
        const out =
          details.fullOutput.length > 4000
            ? details.fullOutput.slice(0, 4000) + "\n… [truncated]"
            : details.fullOutput;
        return new Text(header + "\n" + theme.fg("muted", out), 0, 0);
      }

      return new Text(header, 0, 0);
    },
  });

  // ── System Prompt ─────────────────────────────────────────────────────────
  pi.on("before_agent_start", async (_event, _ctx) => {
    return {
      appendSystemPrompt:
        `\n\n## Pi Extension Builder\n` +
        `You have access to the \`build_extension\` tool which generates complete Pi extensions.\n\n` +
        `Use \`build_extension\` when the user asks to:\n` +
        `- Build, create, or generate a new Pi extension\n` +
        `- Add a new feature as a Pi extension\n` +
        `- Make a tool/gate/footer/multi-agent extension\n\n` +
        `Builder model: ${BUILDER_MODEL}\n` +
        `The builder reads the live codebase and writes all required files automatically.\n` +
        `After building, suggest the user run: just ext-<name>`,
    };
  });

  // ── /builder-status Command ───────────────────────────────────────────────
  pi.registerCommand("builder-status", {
    description: "Show last build status and timing",
    handler: async (_args, _ctx) => {
      const msg = lastBuilt
        ? `Last build: ${lastBuilt}\nStatus: ${buildStatus}\nTime: ${Math.round(lastElapsed / 1000)}s\nModel: ${BUILDER_MODEL}`
        : `No builds yet.\nModel: ${BUILDER_MODEL}`;
      _ctx.ui.notify(msg, buildStatus === "error" ? "error" : "info");
    },
  });
}
