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
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync } from "fs";
import { join, resolve } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

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
    .replace(/[^\w\u4e00-\u9fff\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
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

// ── HTML Report Generator ─────────────────────────────────────────────────────

function extractMemoSection(memo: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}[^\n]*\n([\\s\\S]*?)(?=\n##\\s|$)`, "i");
  const m = memo.match(re);
  return m ? m[1].trim() : "";
}

function parseStanceCard(stance: string): { position: string; argument: string; concern: string } {
  const extract = (labels: string[]) => {
    for (const lbl of labels) {
      const re = new RegExp(`${lbl}[：:：]\\s*([^\n]+(?:\n(?!立場|位置|關鍵|論點|顧慮|主要|Your|Position|Argument|Concern)[^\n]+)*)`, "i");
      const m = stance.match(re);
      if (m) return m[1].replace(/\*+/g, "").trim();
    }
    return "";
  };
  return {
    position: extract(["立場", "位置", "我的立場", "Position", "你的立場"]),
    argument: extract(["關鍵論點", "論點", "Key argument", "關鍵理由"]),
    concern: extract(["主要顧慮", "顧慮", "Key concern", "擔憂"]),
  };
}

function parseActionsList(text: string): string[] {
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  const items: string[] = [];
  for (const line of lines) {
    const m = line.match(/^(?:\d+[.)]\s*|-\s*)(.+)/);
    if (m) items.push(m[1].replace(/\*+/g, "").trim());
    else if (items.length > 0 && !line.startsWith("#")) {
      items[items.length - 1] += " " + line.replace(/\*+/g, "");
    }
  }
  return items.slice(0, 6);
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function generateHtmlReport(opts: {
  date: string;
  preset: string;
  memberNames: string[];
  briefText: string;
  ceoFrame: string;
  boardResults: { name: string; stance: string; error: boolean }[];
  memo: string;
}): string {
  const { date, preset, memberNames, briefText, ceoFrame, boardResults, memo } = opts;

  const finalDecision = escapeHtml(extractMemoSection(memo, "Final Decision|最終決定|最终决定"));
  const dissent = escapeHtml(extractMemoSection(memo, "Dissent.*Tensions|Dissent|分歧|張力|张力"));
  const tradeoffs = extractMemoSection(memo, "Trade.offs|Trade-offs|權衡|取捨|权衡");
  const nextActionsRaw = extractMemoSection(memo, "Next Actions|下一步行動|下一步|後續行動|后续行动");
  const actions = parseActionsList(nextActionsRaw);

  // Brief: render full text with section headings and paragraphs
  const briefHtml = briefText.split("\n").map(line => {
    if (line.startsWith("## ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^##\s*/, ""))}</div>`;
    if (line.startsWith("# ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^#\s*/, ""))}</div>`;
    if (line.trim() === "") return `<div class="brief-spacer"></div>`;
    return `<div class="brief-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  // Stance cards
  const stanceCards = boardResults.filter(r => !r.error).map(r => {
    const parsed = parseStanceCard(r.stance);
    const name = r.name.charAt(0).toUpperCase() + r.name.slice(1);
    const pos = escapeHtml(parsed.position || r.stance.split("\n").find(l => l.trim()) || "");
    const arg = escapeHtml(parsed.argument);
    const con = escapeHtml(parsed.concern);
    return `
      <div class="stance-card">
        <div class="card-header">${escapeHtml(name)}</div>
        ${pos ? `<div class="micro-label">立場</div><div class="micro-content">${pos}</div>` : ""}
        ${arg ? `<div class="micro-label">關鍵論點</div><div class="micro-content">${arg}</div>` : ""}
        ${con ? `<div class="micro-label">主要顧慮</div><div class="micro-content">${con}</div>` : ""}
      </div>`;
  }).join("\n");

  // Trade-offs: try to split gain/lose; fallback to single block
  const gainMatch = tradeoffs.match(/(?:得到|Gain|得)[：:\n]?([\s\S]*?)(?=(?:放棄|Lose|失去|損失)[：:\n]|$)/i);
  const loseMatch = tradeoffs.match(/(?:放棄|Lose|失去|損失)[：:\n]?([\s\S]*?)$/i);
  const gainItems = gainMatch ? parseActionsList(gainMatch[1]) : [];
  const loseItems = loseMatch ? parseActionsList(loseMatch[1]) : [];
  const tradeoffHtml = (gainItems.length > 0 || loseItems.length > 0)
    ? `<div class="tradeoff-grid">
        <div class="gain">
          <div class="tradeoff-label">得到</div>
          <ul>${gainItems.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
        </div>
        <div class="lose">
          <div class="tradeoff-label">放棄</div>
          <ul>${loseItems.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
        </div>
      </div>`
    : `<div class="dissent-block">${escapeHtml(tradeoffs)}</div>`;

  const actionItems = actions.map(a => `<li>${escapeHtml(a)}</li>`).join("\n");
  const memberTags = memberNames.map(n =>
    `<span class="dissent-tag">${escapeHtml(n.charAt(0).toUpperCase() + n.slice(1))}</span>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Drip Music — Decision Board Memo</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #1e2235; --card-bg: #252a3d; --accent: #f472b6; --secondary: #c4b5fd;
      --text: #e8e8e8; --muted: #9ca3af; --border: rgba(244,114,182,0.2);
      --border-accent: #f472b6; --success: #4ade80; --divider: rgba(255,255,255,0.08);
    }
    body { background: var(--bg); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px; line-height: 1.7; min-height: 100vh; }
    .container { max-width: 900px; margin: 0 auto; padding: 0 2rem; }
    header { text-align: center; padding: 4rem 2rem 2.5rem; border-bottom: 1px solid var(--divider); }
    .logo { font-size: 2.4rem; font-weight: 800; letter-spacing: 0.25em; color: var(--accent); text-transform: uppercase; margin-bottom: 0.4rem; }
    .subtitle { font-size: 0.85rem; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; color: var(--secondary); margin-bottom: 1.2rem; }
    .meta { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; justify-content: center; gap: 0.5rem; flex-wrap: wrap; }
    .dot { opacity: 0.4; }
    section { padding: 2.5rem 0; border-bottom: 1px solid var(--divider); }
    section:last-of-type { border-bottom: none; }
    .section-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--secondary); margin-bottom: 1.2rem; }
    .brief-section { background: rgba(196,181,253,0.04); padding: 2.5rem 2rem; }
    .brief-heading { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin: 1rem 0 0.4rem; }
    .brief-heading:first-child { margin-top: 0; }
    .brief-line { color: var(--muted); font-size: 0.9rem; line-height: 1.8; max-width: 680px; }
    .brief-spacer { height: 0.5rem; }
    .ceo-framing { margin-top: 1rem; padding: 1rem 1.2rem; border-left: 3px solid rgba(196,181,253,0.4); background: rgba(196,181,253,0.05); border-radius: 0 6px 6px 0; font-size: 0.88rem; color: var(--muted); line-height: 1.8; }
    .ceo-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--secondary); font-weight: 600; margin-bottom: 0.5rem; }
    .decision-section { background: rgba(244,114,182,0.04); padding: 2.5rem 2rem; }
    .decision-block { border-left: 4px solid var(--accent); padding: 1.2rem 1.5rem; background: rgba(244,114,182,0.06); border-radius: 0 8px 8px 0; }
    .decision-text { font-size: 1.05rem; font-weight: 600; color: var(--text); line-height: 1.75; }
    .stances-section { padding: 2.5rem 2rem; }
    .stances-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; }
    @media (max-width: 700px) { .stances-grid { grid-template-columns: repeat(2,1fr); } }
    @media (max-width: 420px) { .stances-grid { grid-template-columns: 1fr; } }
    .stance-card { background: var(--card-bg); border: 1px solid var(--border); border-top: 3px solid var(--border-accent); border-radius: 8px; padding: 1.2rem; }
    .card-header { font-size: 0.9rem; font-weight: 700; color: var(--accent); margin-bottom: 1rem; letter-spacing: 0.05em; }
    .micro-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin-top: 0.8rem; margin-bottom: 0.3rem; }
    .micro-content { font-size: 0.82rem; color: var(--text); line-height: 1.65; }
    .dissent-section, .tradeoffs-section, .actions-section { padding: 2.5rem 2rem; }
    .dissent-block { background: rgba(244,114,182,0.05); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem 1.4rem; font-size: 0.9rem; line-height: 1.75; color: var(--text); }
    .dissent-members { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
    .dissent-tag { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; background: rgba(244,114,182,0.15); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 4px; }
    .tradeoff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    @media (max-width: 500px) { .tradeoff-grid { grid-template-columns: 1fr; } }
    .gain, .lose { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem 1.4rem; }
    .gain { border-top: 3px solid var(--success); }
    .lose { border-top: 3px solid rgba(244,114,182,0.5); }
    .tradeoff-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin-bottom: 0.8rem; }
    .gain ul, .lose ul { list-style: none; padding: 0; }
    .gain ul li, .lose ul li { font-size: 0.88rem; color: var(--text); line-height: 1.6; padding: 0.3rem 0; display: flex; align-items: flex-start; gap: 0.6rem; }
    .gain ul li::before { content: '+'; color: var(--success); font-weight: 700; flex-shrink: 0; }
    .lose ul li::before { content: '−'; color: var(--accent); font-weight: 700; flex-shrink: 0; }
    .actions-list { list-style: none; padding: 0; counter-reset: actions; }
    .actions-list li { counter-increment: actions; display: flex; align-items: flex-start; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--divider); font-size: 0.9rem; line-height: 1.65; }
    .actions-list li:last-child { border-bottom: none; }
    .actions-list li::before { content: counter(actions, decimal-leading-zero); color: var(--accent); font-weight: 700; font-size: 0.82rem; letter-spacing: 0.05em; flex-shrink: 0; margin-top: 0.1rem; min-width: 2rem; }
    footer { text-align: center; padding: 2.5rem 2rem; display: flex; flex-direction: column; gap: 0.3rem; border-top: 1px solid var(--divider); }
    footer span { font-size: 0.82rem; font-style: italic; color: var(--secondary); opacity: 0.7; }
  </style>
</head>
<body>
  <header>
    <div class="logo">Drip Music</div>
    <div class="subtitle">Decision Board Memo</div>
    <div class="meta">
      <span>${escapeHtml(date)}</span><span class="dot">·</span>
      <span>${escapeHtml(preset)}</span><span class="dot">·</span>
      <span>${memberNames.length} members</span><span class="dot">·</span>
      <span>kimi-coding/k2p5</span>
    </div>
  </header>

  <section class="brief-section">
    <div class="section-label">Brief</div>
    <div class="brief-body">${briefHtml}</div>
    <div class="ceo-framing">
      <div class="ceo-label">CEO Framing</div>
      ${escapeHtml(ceoFrame)}
    </div>
  </section>

  <section class="decision-section">
    <div class="section-label">Final Decision</div>
    <div class="decision-block">
      <p class="decision-text">${finalDecision || escapeHtml(memo.split("\n").find(l => l.trim() && !l.startsWith("#")) || "")}</p>
    </div>
  </section>

  <section class="stances-section">
    <div class="section-label">Board Stances</div>
    <div class="stances-grid">${stanceCards}</div>
  </section>

  ${dissent ? `<section class="dissent-section">
    <div class="section-label">Dissent &amp; Tensions</div>
    <div class="dissent-block">
      <div class="dissent-members">${memberTags}</div>
      ${dissent}
    </div>
  </section>` : ""}

  <section class="tradeoffs-section">
    <div class="section-label">Trade-offs</div>
    ${tradeoffHtml}
  </section>

  ${actionItems ? `<section class="actions-section">
    <div class="section-label">Next Actions</div>
    <ol class="actions-list">${actionItems}</ol>
  </section>` : ""}

  <footer>
    <span>往無界處，隨點滴流動。</span>
    <span>Beyond the defined, let the drip flow.</span>
  </footer>
</body>
</html>`;
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: any;
  let boardConfig: BoardConfig = { meeting: { discussion_time_minutes: 5 }, board: [], presets: {} };
  let activePreset: string | null = null;
  let memberStates: MemberState[] = [];
  let boardPhase: "idle" | "framing" | "deliberating" | "synthesizing" | "done" = "idle";
  let ceoFramingText = "";
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
    // Strip markdown bold/italic so raw **text** doesn't appear in card
    const stripMd = (s: string) => s.replace(/\*+([^*]+)\*+/g, "$1").replace(/_{1,2}([^_]+)_{1,2}/g, "$1");

    const statusColor = state.status === "pending" ? "dim"
      : state.status === "running" ? "accent"
        : state.status === "done" ? "success" : "error";
    const statusIcon = state.status === "pending" ? "○"
      : state.status === "running" ? "◉"
        : state.status === "done" ? "✓" : "✗";

    const name = displayName(state.name);
    const nameStr = theme.fg("accent", theme.bold(truncate(name, w)));
    const nameVisible = Math.min(name.length, w);

    const statusStr = `${statusIcon} ${state.status}`;
    const timeStr = state.status !== "pending" ? ` ${Math.round(state.elapsed / 1000)}s` : "";
    const statusLine = theme.fg(statusColor, statusStr + timeStr);
    const statusVisible = statusStr.length + timeStr.length;

    const workRaw = stripMd(state.lastWork || "");
    const workText = workRaw ? truncate(workRaw, Math.min(55, w - 1)) : "";
    const workLine = workText ? theme.fg("muted", workText) : theme.fg("dim", "—");
    const workVisible = workText ? workText.length : 1;

    // Accent-coloured top border, dim sides/bottom
    const top = "┌" + "─".repeat(w) + "┐";
    const bot = "└" + "─".repeat(w) + "┘";
    const sideBorder = (content: string, visLen: number) =>
      theme.fg("borderMuted", "│") + content + " ".repeat(Math.max(0, w - visLen)) + theme.fg("borderMuted", "│");

    return [
      theme.fg("accent", top),
      sideBorder(" " + nameStr, 1 + nameVisible),
      sideBorder(" " + statusLine, 1 + statusVisible),
      sideBorder(" " + workLine, 1 + workVisible),
      sideBorder(" ", 1),                                    // breathing room
      theme.fg("borderMuted", bot),
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

          // During framing, stream CEO output instead of empty card grid
          if (boardPhase === "framing" && ceoFramingText) {
            const preview = ceoFramingText.split("\n").filter((l: string) => l.trim()).slice(-3).join(" · ");
            const truncated = preview.length > width - 4 ? preview.slice(0, width - 7) + "..." : preview;
            text.setText(headerLine + "\n\n" + theme.fg("muted", truncated));
            return text.render(width);
          }

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
    knowledgeBase: string = "",
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

    // Agent's persona + knowledge base = system prompt; task context = user prompt
    const memberSystemPrompt = memberDef.systemPrompt + knowledgeBase;

    const prompt =
      `The CEO has framed this decision for the board:\n\n${ceoFrame}\n\n` +
      `Original Brief:\n${briefText}\n\n` +
      `Give your stance as ${displayName(memberConfig.name)}. Include:\n` +
      `- Your position (what you recommend)\n` +
      `- Your key argument (why)\n` +
      `- Your key concern (what worries you)\n` +
      `- One question you'd ask the other board members\n\n` +
      `Be direct, stay in character, 150-250 words.\n\n` +
      `IMPORTANT: Write entirely in Traditional Chinese (繁體中文). Technical terms, artist names, and system keywords may stay in English.`;

    return runSubagent(memberSystemPrompt, prompt, (chunk) => {
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

      // Validate all member paths exist before starting
      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return {
          content: [{ type: "text", text: `Missing agent files:\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }],
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

      // 4. CEO Framing (sequential, with streaming to widget)
      ceoFramingText = "";
      const ceoSystemPrompt =
        `You are the CEO facilitator for Drip Music's strategic decision board. ` +
        `Drip Music Limited is a Hong Kong independent jazz/fusion music company.` +
        knowledgeBase;

      const framingPrompt =
        `Read this brief and frame the decision for the board. Identify:\n` +
        `1. The core tension\n` +
        `2. What each board perspective should focus on\n` +
        `3. The key question they must answer\n\n` +
        `Brief:\n${briefText}\n\n` +
        `Output your framing in 200-300 words. Be direct and sharp.\n\n` +
        `IMPORTANT: Write entirely in Traditional Chinese (繁體中文). Technical terms, artist names, and system keywords may stay in English.`;

      const framingResult = await runSubagent(ceoSystemPrompt, framingPrompt, (chunk) => {
        ceoFramingText += chunk;
        updateWidget();
      });
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
          return runMember(member, def, ceoFrame, briefText, i, knowledgeBase);
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

      const validResults = boardResults.filter(r => !r.error);
      const allStances = validResults
        .map(r => `### ${displayName(r.name)}\n${r.stance}`)
        .join("\n\n");
      const errorNote = boardResults.length > validResults.length
        ? `\n\n（注意：${boardResults.length - validResults.length} 位成員回應失敗，未納入此次綜合。）`
        : "";

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
        `IMPORTANT: Write the entire memo in Traditional Chinese (繁體中文). Keep section headings in English exactly as listed above so they can be parsed. Technical terms, artist names, and keywords may stay in English.${errorNote}`;

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

      // 8. Save HTML report
      const htmlPath = memoPath.replace(/\.md$/, ".html");
      const htmlContent = generateHtmlReport({
        date: new Date().toISOString().slice(0, 10),
        preset: preset || activePreset || "custom",
        memberNames: activeMembers.map(m => m.name),
        briefText,
        ceoFrame,
        boardResults,
        memo,
      });
      writeFileSync(htmlPath, htmlContent, "utf-8");

      boardPhase = "done";
      updateWidget();

      const truncated = memo.length > 8000 ? memo.slice(0, 8000) + "\n\n... [truncated — see memo file]" : memo;

      return {
        content: [{ type: "text", text: `Memo saved:\n  📄 ${memoPath}\n  🌐 ${htmlPath}\n\n${truncated}` }],
        details: {
          status: "done",
          memoPath,
          htmlPath,
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

  pi.registerCommand("board-history", {
    description: "List recent decision board memos",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const memosDir = join(cwd, ".pi", "drip-board", "memos");
      if (!existsSync(memosDir)) {
        ctx.ui.notify("No memos yet. Run board_begin to create your first deliberation.", "info");
        return;
      }

      const files = readdirSync(memosDir)
        .filter(f => f.endsWith(".md"))
        .sort()
        .reverse()
        .slice(0, 10);

      if (files.length === 0) {
        ctx.ui.notify("No memos found in .pi/drip-board/memos/", "info");
        return;
      }

      const lines = files.map((f, i) => {
        const hasHtml = existsSync(join(memosDir, f.replace(/\.md$/, ".html")));
        return `${i + 1}. ${f}${hasHtml ? " 🌐" : ""}`;
      });

      ctx.ui.notify(
        `Recent deliberations (${files.length}):\n\n${lines.join("\n")}\n\n📁 ${memosDir}`,
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
