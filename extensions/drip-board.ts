/**
 * Drip Board — Strategic Decision Board for Drip Music Limited
 *
 * A multi-agent deliberation system where a CEO facilitates discussion among
 * specialist board members on strategic questions. Board members run in parallel;
 * the CEO frames the question first and synthesizes stances into a final memo.
 *
 * Config: .pi/drip-board/config.yaml
 * Agents: .pi/drip-board/agents/<name>.md
 * Memos:  .pi/drip-board/memos/<slug>-<timestamp>.md
 *
 * Commands:
 *   /board-preset  — select a preset (full/programming/marketing-campaign/etc.)
 *   /board-status  — show which members are active
 *
 * Usage: pi -e extensions/drip-board.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BoardMemberConfig {
  name: string;
  path: string;
  active: boolean;
}

interface BoardConfig {
  meeting: {
    discussion_time_minutes: number;
  };
  board: BoardMemberConfig[];
  presets: Record<string, string[]>;
}

interface MemberDef {
  name: string;
  systemPrompt: string;
}

interface MemberState {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed: number;
  lastWork: string;
}

// ── YAML Parser ───────────────────────────────────────────────────────────────

function parseBoardConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = {
    meeting: { discussion_time_minutes: 5 },
    board: [],
    presets: {},
  };

  const lines = raw.split("\n");
  let section = "";
  let inBoardItem = false;
  let currentItem: Partial<BoardMemberConfig> = {};
  let inPresets = false;

  for (const line of lines) {
    // Top-level section detection
    if (line.match(/^meeting:\s*$/)) { section = "meeting"; inBoardItem = false; inPresets = false; continue; }
    if (line.match(/^board:\s*$/)) { section = "board"; inBoardItem = false; inPresets = false; continue; }
    if (line.match(/^presets:\s*$/)) {
      // flush any pending board item
      if (inBoardItem && currentItem.name) {
        config.board.push({
          name: currentItem.name!,
          path: currentItem.path || "",
          active: currentItem.active !== false,
        });
        currentItem = {};
      }
      section = "presets"; inBoardItem = false; inPresets = true; continue;
    }

    if (section === "meeting") {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) { config.meeting.discussion_time_minutes = parseInt(m[1], 10); }
      continue;
    }

    if (section === "board") {
      // New board item
      if (line.match(/^\s+-\s+name:/)) {
        if (inBoardItem && currentItem.name) {
          config.board.push({
            name: currentItem.name!,
            path: currentItem.path || "",
            active: currentItem.active !== false,
          });
        }
        currentItem = {};
        inBoardItem = true;
        const m = line.match(/^\s+-\s+name:\s*(.+)$/);
        if (m) currentItem.name = m[1].trim();
        continue;
      }
      if (inBoardItem) {
        const pathM = line.match(/^\s+path:\s*(.+)$/);
        if (pathM) { currentItem.path = pathM[1].trim(); continue; }
        const activeM = line.match(/^\s+active:\s*(true|false)/);
        if (activeM) { currentItem.active = activeM[1] === "true"; continue; }
      }
      continue;
    }

    if (section === "presets" && inPresets) {
      // Preset lines: "  full: [brand, marketing, ...]"
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        const presetName = m[1].trim();
        const members = m[2].split(",").map(s => s.trim()).filter(Boolean);
        config.presets[presetName] = members;
      }
      continue;
    }
  }

  // Flush last board item
  if (section === "board" && inBoardItem && currentItem.name) {
    config.board.push({
      name: currentItem.name!,
      path: currentItem.path || "",
      active: currentItem.active !== false,
    });
  }

  return config;
}

// ── Agent File Parser (frontmatter) ──────────────────────────────────────────

function parseMemberFile(filePath: string): MemberDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (match) {
      const fm: Record<string, string> = {};
      for (const line of match[1].split("\n")) {
        const idx = line.indexOf(":");
        if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
      const name = fm["name"] || filePath;
      return { name, systemPrompt: match[2].trim() };
    }
    // No frontmatter — treat entire file as system prompt
    return { name: filePath, systemPrompt: raw.trim() };
  } catch {
    return null;
  }
}

// ── Slug Helper ───────────────────────────────────────────────────────────────

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 40);
}

// ── Display Name Helper ───────────────────────────────────────────────────────

function displayName(name: string): string {
  return name.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

// ── Subprocess: run a Pi agent ephemerally ────────────────────────────────────

interface RunResult {
  output: string;
  exitCode: number;
  elapsed: number;
}

function runSubagent(
  systemPrompt: string,
  prompt: string,
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = [
    "--mode", "json",
    "-p",
    "--no-extensions",
    "--model", "kimi-coding/k2p5",
    "--tools", "none",
    "--thinking", "off",
    "--append-system-prompt", systemPrompt,
    "--no-session",
    prompt,
  ];

  const textChunks: string[] = [];
  const startTime = Date.now();

  return new Promise((resolve) => {
    const proc = spawn("pi", args, {
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
              const t = delta.delta || "";
              textChunks.push(t);
              if (onChunk) onChunk(t);
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
      resolve({ output: textChunks.join(""), exitCode: code ?? 1, elapsed: Date.now() - startTime });
    });

    proc.on("error", (err) => {
      resolve({ output: `Error spawning subprocess: ${err.message}`, exitCode: 1, elapsed: Date.now() - startTime });
    });
  });
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: any;
  let boardConfig: BoardConfig = { meeting: { discussion_time_minutes: 5 }, board: [], presets: {} };
  let activePreset: string | null = null;
  let memberStates: MemberState[] = [];
  let boardPhase: "idle" | "framing" | "deliberating" | "synthesizing" | "done" = "idle";
  let cwd = "";

  // ── Config Loader ──────────────────────────────────────────────────────────

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "drip-board", "config.yaml");
    if (!existsSync(configPath)) {
      return;
    }
    try {
      const raw = readFileSync(configPath, "utf-8");
      boardConfig = parseBoardConfigYaml(raw);
    } catch {
      // use defaults
    }
  }

  function getActiveMembers(presetOverride?: string): BoardMemberConfig[] {
    const preset = presetOverride || activePreset;
    if (preset && boardConfig.presets[preset]) {
      const names = new Set(boardConfig.presets[preset]);
      return boardConfig.board.filter(m => names.has(m.name));
    }
    return boardConfig.board.filter(m => m.active);
  }

  // ── Widget Rendering ───────────────────────────────────────────────────────

  function renderMemberCard(state: MemberState, colWidth: number, theme: any): string[] {
    const w = colWidth - 2;
    const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 3) + "..." : s;

    const statusColor = state.status === "pending" ? "dim"
      : state.status === "running" ? "accent"
        : state.status === "done" ? "success" : "error";
    const statusIcon = state.status === "pending" ? "○"
      : state.status === "running" ? "●"
        : state.status === "done" ? "✓" : "✗";

    const name = displayName(state.name);
    const nameStr = theme.fg("accent", theme.bold(truncate(name, w)));
    const nameVisible = Math.min(name.length, w);

    const statusStr = `${statusIcon} ${state.status}`;
    const timeStr = state.status !== "pending" ? ` ${Math.round(state.elapsed / 1000)}s` : "";
    const statusLine = theme.fg(statusColor, statusStr + timeStr);
    const statusVisible = statusStr.length + timeStr.length;

    const workRaw = state.lastWork || "";
    const workText = workRaw ? truncate(workRaw, Math.min(50, w - 1)) : "";
    const workLine = workText ? theme.fg("muted", workText) : theme.fg("dim", "—");
    const workVisible = workText ? workText.length : 1;

    const top = "┌" + "─".repeat(w) + "┐";
    const bot = "└" + "─".repeat(w) + "┘";
    const border = (content: string, visLen: number) =>
      theme.fg("dim", "│") + content + " ".repeat(Math.max(0, w - visLen)) + theme.fg("dim", "│");

    return [
      theme.fg("dim", top),
      border(" " + nameStr, 1 + nameVisible),
      border(" " + statusLine, 1 + statusVisible),
      border(" " + workLine, 1 + workVisible),
      theme.fg("dim", bot),
    ];
  }

  function updateWidget() {
    if (!widgetCtx) return;
    const members = memberStates;

    widgetCtx.ui.setWidget("drip-board", (_tui: any, theme: any) => {
      const text = new Text("", 0, 1);

      return {
        render(width: number): string[] {
          if (boardPhase === "idle" || members.length === 0) {
            text.setText(theme.fg("dim", "Drip Board idle. Use board_begin to start a deliberation."));
            return text.render(width);
          }

          // Phase header
          const phaseLabel = boardPhase === "framing" ? "● CEO Framing..."
            : boardPhase === "deliberating" ? "● Board Deliberating..."
              : boardPhase === "synthesizing" ? "● CEO Synthesizing..."
                : boardPhase === "done" ? "✓ Deliberation Complete" : "";
          const headerLine = theme.fg("accent", phaseLabel);

          // Grid: 4 cards per row
          const COLS = Math.min(4, members.length);
          const GAP = 2;
          const colWidth = Math.max(14, Math.floor((width - GAP * (COLS - 1)) / COLS));

          const rows: string[][] = [];
          for (let start = 0; start < members.length; start += COLS) {
            const rowMembers = members.slice(start, start + COLS);
            const cards = rowMembers.map(s => renderMemberCard(s, colWidth, theme));
            const cardHeight = cards[0].length;
            const rowLines: string[] = [];
            for (let line = 0; line < cardHeight; line++) {
              let rowStr = cards[0][line];
              for (let c = 1; c < rowMembers.length; c++) {
                rowStr += " ".repeat(GAP) + cards[c][line];
              }
              rowLines.push(rowStr);
            }
            rows.push(rowLines);
          }

          const outputLines: string[] = [headerLine, ""];
          for (const row of rows) {
            for (const line of row) outputLines.push(line);
            outputLines.push("");
          }

          text.setText(outputLines.join("\n"));
          return text.render(width);
        },
        invalidate() { text.invalidate(); },
      };
    });
  }

  // ── Run a single board member (for parallel execution) ─────────────────────

  function runMember(
    memberConfig: BoardMemberConfig,
    memberDef: MemberDef,
    ceoFrame: string,
    briefText: string,
    stateIndex: number,
  ): Promise<{ name: string; stance: string; error: boolean }> {
    const state = memberStates[stateIndex];
    state.status = "running";
    state.elapsed = 0;
    updateWidget();

    const startTime = Date.now();
    const timer = setInterval(() => {
      state.elapsed = Date.now() - startTime;
      updateWidget();
    }, 1000);

    const prompt =
      `${memberDef.systemPrompt}\n\n---\n\n` +
      `The CEO has framed this decision for the board:\n\n${ceoFrame}\n\n` +
      `Original Brief:\n${briefText}\n\n` +
      `Give your stance as ${displayName(memberConfig.name)}. Include:\n` +
      `- Your position (what you recommend)\n` +
      `- Your key argument (why)\n` +
      `- Your key concern (what worries you)\n` +
      `- One question you'd ask the other board members\n\n` +
      `Be direct, stay in character, 150-250 words.\n\n` +
      `IMPORTANT: Write entirely in Traditional Chinese (繁體中文). Technical terms, artist names, and system keywords may stay in English.`;

    const ceoSystemPrompt =
      `You are the ${displayName(memberConfig.name)} specialist on Drip Music's strategic decision board.`;

    return runSubagent(ceoSystemPrompt, prompt, (chunk) => {
      const full = (state.lastWork + chunk);
      const last = full.split("\n").filter((l: string) => l.trim()).pop() || "";
      state.lastWork = last;
      updateWidget();
    }).then(result => {
      clearInterval(timer);
      state.elapsed = Date.now() - startTime;
      state.status = result.exitCode === 0 ? "done" : "error";
      state.lastWork = result.output.split("\n").filter((l: string) => l.trim()).pop() || "";
      updateWidget();
      return { name: memberConfig.name, stance: result.output, error: result.exitCode !== 0 };
    }).catch(err => {
      clearInterval(timer);
      state.status = "error";
      state.lastWork = String(err);
      updateWidget();
      return { name: memberConfig.name, stance: `Error: ${err}`, error: true };
    });
  }

  // ── board_begin Tool ───────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_begin",
    label: "Board Begin",
    description:
      "Convene Drip Music's strategic decision board. Provide a brief (inline markdown or path to .md file). " +
      "The CEO frames the question, all board members deliberate in parallel, then the CEO writes a final decision memo.",
    parameters: Type.Object({
      brief: Type.String({
        description: "Inline brief text (markdown) OR a file path ending in .md",
      }),
      preset: Type.Optional(Type.String({
        description: "Override board preset for this deliberation (full/programming/marketing-campaign/grants-funding/creative/quick)",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };

      // 0. Load shared knowledge base
      const kbPath = join(cwd, ".pi", "drip-board", "knowledge-base.md");
      const knowledgeBase = existsSync(kbPath)
        ? `\n\n## Drip Music 知識庫（共享背景資料）\n\n${readFileSync(kbPath, "utf-8")}`
        : "";

      // 1. Resolve brief text
      let briefText = brief;
      if (brief.endsWith(".md")) {
        const briefPath = resolve(cwd, brief);
        if (existsSync(briefPath)) {
          briefText = readFileSync(briefPath, "utf-8");
        } else {
          return {
            content: [{ type: "text", text: `Brief file not found: ${briefPath}` }],
            details: { status: "error" },
          };
        }
      }

      // 2. Resolve active members
      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: "text", text: "No active board members. Check config or select a preset." }],
          details: { status: "error" },
        };
      }

      // Load member definitions
      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const memberPath = resolve(cwd, member.path);
        const def = parseMemberFile(memberPath);
        if (def) memberDefs.set(member.name, def);
      }

      // 3. Initialize widget state
      memberStates = activeMembers.map(m => ({
        name: m.name,
        status: "pending" as const,
        elapsed: 0,
        lastWork: "",
      }));
      boardPhase = "framing";
      updateWidget();

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `Starting deliberation with ${activeMembers.length} board members...` }],
          details: { status: "running", phase: "framing" },
        });
      }

      // 4. CEO Framing (sequential)
      const ceoSystemPrompt =
        `You are the CEO facilitator for Drip Music's strategic decision board. ` +
        `Drip Music Limited is a Hong Kong independent jazz/fusion music company.` +
        knowledgeBase;

      const framingPrompt =
        `You are the CEO facilitator for Drip Music's strategic decision board.\n\n` +
        `Read this brief and frame the decision for the board. Identify:\n` +
        `1. The core tension\n` +
        `2. What each board perspective should focus on\n` +
        `3. The key question they must answer\n\n` +
        `Brief:\n${briefText}\n\n` +
        `Output your framing in 200-300 words. Be direct and sharp.\n\n` +
        `IMPORTANT: Write entirely in Traditional Chinese (繁體中文). Technical terms, artist names, and system keywords may stay in English.`;

      const framingResult = await runSubagent(ceoSystemPrompt, framingPrompt);
      const ceoFrame = framingResult.output;

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `CEO framing complete. Board deliberating in parallel...` }],
          details: { status: "running", phase: "deliberating" },
        });
      }

      // 5. Board members in PARALLEL
      boardPhase = "deliberating";
      memberStates.forEach(s => { s.status = "pending"; });
      updateWidget();

      const boardResults = await Promise.all(
        activeMembers.map((member, i) => {
          const def = memberDefs.get(member.name);
          if (!def) {
            memberStates[i].status = "error";
            memberStates[i].lastWork = "Agent file not found";
            updateWidget();
            return Promise.resolve({ name: member.name, stance: `Error: agent file not found`, error: true });
          }
          return runMember(member, def, ceoFrame, briefText, i);
        })
      );

      // 6. CEO Synthesis (sequential)
      boardPhase = "synthesizing";
      updateWidget();

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `All stances collected. CEO synthesizing final memo...` }],
          details: { status: "running", phase: "synthesizing" },
        });
      }

      const allStances = boardResults
        .map(r => `### ${displayName(r.name)}\n${r.stance}`)
        .join("\n\n");

      const synthesisPrompt =
        `You are the CEO facilitator for Drip Music's strategic decision board.\n\n` +
        `Based on the original brief and all board member responses, write the final decision memo.\n\n` +
        `Brief:\n${briefText}\n\n` +
        `CEO Framing:\n${ceoFrame}\n\n` +
        `Board Responses:\n${allStances}\n\n` +
        `Write a structured memo with these sections:\n` +
        `## Final Decision\n` +
        `[Your synthesis and recommendation — be decisive]\n\n` +
        `## Board Member Stances\n` +
        `[One paragraph per member: their position + key argument + key concern]\n\n` +
        `## Dissent & Tensions\n` +
        `[Unresolved disagreements between board members]\n\n` +
        `## Trade-offs\n` +
        `[What we gain / what we lose with the recommended decision]\n\n` +
        `## Next Actions\n` +
        `[3-5 concrete steps]\n\n` +
        `## Deliberation Summary\n` +
        `[How the conversation unfolded, what shifted the thinking]\n\n` +
        `IMPORTANT: Write the entire memo in Traditional Chinese (繁體中文). Section headings, technical terms, artist names, and system keywords may stay in English.`;

      const synthResult = await runSubagent(ceoSystemPrompt, synthesisPrompt);
      const memo = synthResult.output;

      // 7. Save memo
      const memosDir = join(cwd, ".pi", "drip-board", "memos");
      mkdirSync(memosDir, { recursive: true });

      const briefFirstLine = briefText.split("\n").find(l => l.trim()) || "decision";
      const slug = slugify(briefFirstLine.replace(/^#+\s*/, ""));
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const memoFilename = `${slug}-${timestamp}.md`;
      const memoPath = join(memosDir, memoFilename);

      const memoContent =
        `# Drip Music Decision Memo\n\n` +
        `**Date:** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Preset:** ${preset || activePreset || "custom"}\n` +
        `**Members:** ${activeMembers.map(m => displayName(m.name)).join(", ")}\n` +
        `**Discussion Time:** ${boardConfig.meeting.discussion_time_minutes} min\n\n` +
        `---\n\n` +
        `## Original Brief\n\n${briefText}\n\n` +
        `---\n\n` +
        `## CEO Framing\n\n${ceoFrame}\n\n` +
        `---\n\n` +
        `## Individual Stances\n\n${allStances}\n\n` +
        `---\n\n` +
        `${memo}`;

      writeFileSync(memoPath, memoContent, "utf-8");

      boardPhase = "done";
      updateWidget();

      const truncated = memo.length > 8000 ? memo.slice(0, 8000) + "\n\n... [truncated — see memo file]" : memo;

      return {
        content: [{ type: "text", text: `Memo saved to: ${memoPath}\n\n${truncated}` }],
        details: {
          status: "done",
          memoPath,
          preset: preset || activePreset,
          memberCount: activeMembers.length,
          memo,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : "";
      const briefPreview = (a.brief || "").slice(0, 50).replace(/\n/g, " ");
      const preview = briefPreview.length > 47 ? briefPreview.slice(0, 47) + "..." : briefPreview;
      return new Text(
        theme.fg("toolTitle", theme.bold("board_begin")) +
        theme.fg("accent", presetLabel) +
        theme.fg("dim", " — ") +
        theme.fg("muted", preview),
        0, 0,
      );
    },

    renderResult(result, options, theme) {
      const details = result.details as any;
      if (!details) {
        const text = result.content[0];
        return new Text(text?.type === "text" ? text.text : "", 0, 0);
      }

      if (options.isPartial || details.status === "running") {
        const phase = details.phase || "running";
        return new Text(
          theme.fg("accent", `● drip-board`) +
          theme.fg("dim", ` ${phase}...`),
          0, 0,
        );
      }

      if (details.status === "error") {
        return new Text(theme.fg("error", `✗ board_begin failed`), 0, 0);
      }

      const header =
        theme.fg("success", `✓ drip-board`) +
        theme.fg("dim", ` · ${details.memberCount} members · `) +
        theme.fg("muted", details.memoPath || "");

      if (options.expanded && details.memo) {
        const output = details.memo.length > 4000
          ? details.memo.slice(0, 4000) + "\n... [truncated]"
          : details.memo;
        return new Text(header + "\n" + theme.fg("muted", output), 0, 0);
      }

      return new Text(header, 0, 0);
    },
  });

  // ── Commands ───────────────────────────────────────────────────────────────

  pi.registerCommand("board-preset", {
    description: "Select a preset for board deliberation",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const presetNames = Object.keys(boardConfig.presets);
      if (presetNames.length === 0) {
        ctx.ui.notify("No presets defined in config.yaml", "warning");
        return;
      }

      const options = presetNames.map(name => {
        const members = boardConfig.presets[name];
        return `${name} (${members.join(", ")})`;
      });

      const choice = await ctx.ui.select("Select Board Preset", options);
      if (choice === undefined) return;

      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];

      const members = boardConfig.presets[activePreset];
      ctx.ui.setStatus("drip-board", `Preset: ${activePreset} · ${members.length} members`);
      ctx.ui.notify(
        `Preset: ${activePreset}\nMembers: ${members.map(displayName).join(", ")}`,
        "info",
      );
      updateWidget();
    },
  });

  pi.registerCommand("board-status", {
    description: "Show active board members",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const active = getActiveMembers();
      const all = boardConfig.board;

      const lines = all.map(m => {
        const isActive = active.some(a => a.name === m.name);
        const icon = isActive ? "✓" : "○";
        return `${icon} ${displayName(m.name)}  (${m.path})`;
      });

      const presetInfo = activePreset ? `Preset: ${activePreset}` : "Using config active flags";
      const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 5), 10);

      ctx.ui.notify(
        `${presetInfo}\nDiscussion time: ${time} min (informational)\n\n` +
        lines.join("\n"),
        "info",
      );
    },
  });

  // ── before_agent_start ─────────────────────────────────────────────────────

  pi.on("before_agent_start", async (_event, _ctx) => {
    widgetCtx = _ctx;

    const active = getActiveMembers();
    const presetLabel = activePreset || "config defaults";
    const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 5), 10);

    const presetList = Object.keys(boardConfig.presets).join(", ");
    const memberList = active.map(m => `- **${displayName(m.name)}**`).join("\n");

    return {
      systemPrompt:
        `You are the facilitator for Drip Music's strategic Decision Board.\n\n` +
        `Drip Music Limited is a Hong Kong independent jazz/fusion music company specialising in jazz and fusion music.\n\n` +
        `## Your Role\n` +
        `You convene strategic deliberations using the \`board_begin\` tool. When the user wants to make a strategic decision:\n` +
        `1. Ask them to share a brief (or file path ending in .md)\n` +
        `2. Optionally ask which preset to use\n` +
        `3. Call \`board_begin\` with the brief and optional preset\n\n` +
        `The board will deliberate in parallel and produce a final decision memo.\n\n` +
        `## Current Board Config\n` +
        `Preset: ${presetLabel}\n` +
        `Discussion time: ${time} minutes (informational only)\n` +
        `Active members (${active.length}):\n${memberList}\n\n` +
        `## Available Presets\n` +
        `${presetList || "None defined"}\n` +
        `Use /board-preset to switch presets, /board-status to see all members.\n\n` +
        `## Brief Format\n` +
        `Encourage the user to structure their brief with:\n` +
        `- ## Situation\n` +
        `- ## Stakes\n` +
        `- ## Constraints\n` +
        `- ## Key Question\n\n` +
        `But accept any free-form text. If they have a .md file, pass the path directly.\n\n` +
        `## Commands\n` +
        `/board-preset    Select a board preset\n` +
        `/board-status    Show active board members\n\n` +
        `Start by welcoming the user and asking what strategic question they'd like the board to deliberate on.`,
    };
  });

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, _ctx) => {
    applyExtensionDefaults(import.meta.url, _ctx);

    if (widgetCtx) widgetCtx.ui.setWidget("drip-board", undefined);
    _ctx.ui.setWidget("drip-board", undefined);
    widgetCtx = _ctx;

    boardPhase = "idle";
    memberStates = [];
    activePreset = null;

    loadConfig(_ctx.cwd);

    const active = getActiveMembers();
    const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 5), 10);

    _ctx.ui.setStatus("drip-board", `Drip Board · ${active.length} members active`);
    _ctx.ui.notify(
      `Drip Music Decision Board\n` +
      `${active.length} active members · ${time} min discussions\n\n` +
      `/board-preset    Select preset\n` +
      `/board-status    Show members`,
      "info",
    );

    updateWidget();

    // Footer
    _ctx.ui.setFooter((_tui, theme, _footerData) => ({
      dispose: () => { },
      invalidate() { },
      render(width: number): string[] {
        const presetLabel = activePreset || "default";
        const memberCount = getActiveMembers().length;

        const left =
          theme.fg("dim", ` kimi-coding/k2p5`) +
          theme.fg("muted", " · ") +
          theme.fg("accent", "drip-board") +
          theme.fg("muted", " · ") +
          theme.fg("dim", presetLabel) +
          theme.fg("muted", " · ") +
          theme.fg("dim", `${memberCount} members active`);

        const right = theme.fg("dim", ` `);
        const pad = " ".repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));

        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });
}
