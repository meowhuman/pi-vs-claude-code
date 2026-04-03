/**
 * Music Study Board — 音樂研究小組多代理系統
 *
 * 4位專業研究員並行研究音樂主題，Research Lead 整合後輸出 HTML 報告。
 * 各成員使用真實工具（bash / wsp-v3 / summarize / bird-cli）。
 *
 * Config:  .pi/music-study/config.yaml
 * Agents:  .pi/music-study/agents/<name>/
 * Reports: .pi/music-study/reports/
 *
 * Commands:
 *   /study-preset   — 選擇研究組合（full/jazz-deep/discovery/quick）
 *   /study-status   — 顯示活躍成員
 *   /study-history  — 列出最近報告
 *
 * Tools:
 *   study_begin  — 提交主題 → 各成員並行研究 → HTML 報告
 *
 * Usage: pi -e extensions/boards/music-study.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync } from "fs";
import { join, resolve, dirname } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Types ──────────────────────────────────────────────────────────────────────

interface BoardMemberConfig {
  name: string;
  path: string;
  active: boolean;
}

interface BoardConfig {
  meeting: { discussion_time_minutes: number };
  board: BoardMemberConfig[];
  presets: Record<string, string[]>;
}

interface MemberDef {
  name: string;
  systemPrompt: string;
  model: string;
  tools: string;
  knowledgePath: string;
}

interface MemberState {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed: number;
  lastWork: string;
}

// ── YAML Parser ────────────────────────────────────────────────────────────────

function parseBoardConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = {
    meeting: { discussion_time_minutes: 10 },
    board: [],
    presets: {},
  };

  const lines = raw.split("\n");
  let section = "";
  let inBoardItem = false;
  let currentItem: Partial<BoardMemberConfig> = {};
  let inPresets = false;

  for (const line of lines) {
    if (line.match(/^meeting:\s*$/)) { section = "meeting"; inBoardItem = false; inPresets = false; continue; }
    if (line.match(/^board:\s*$/)) { section = "board"; inBoardItem = false; inPresets = false; continue; }
    if (line.match(/^presets:\s*$/)) {
      if (inBoardItem && currentItem.name) {
        config.board.push({ name: currentItem.name!, path: currentItem.path || "", active: currentItem.active !== false });
        currentItem = {};
      }
      section = "presets"; inBoardItem = false; inPresets = true; continue;
    }

    if (section === "meeting") {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) config.meeting.discussion_time_minutes = parseInt(m[1], 10);
      continue;
    }

    if (section === "board") {
      if (line.match(/^\s+-\s+name:/)) {
        if (inBoardItem && currentItem.name) {
          config.board.push({ name: currentItem.name!, path: currentItem.path || "", active: currentItem.active !== false });
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
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        config.presets[m[1].trim()] = m[2].split(",").map(s => s.trim()).filter(Boolean);
      }
      continue;
    }
  }

  if (section === "board" && inBoardItem && currentItem.name) {
    config.board.push({ name: currentItem.name!, path: currentItem.path || "", active: currentItem.active !== false });
  }

  return config;
}

// ── Agent File Parser ──────────────────────────────────────────────────────────

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
      const model = fm["model"] || "glm/glm-5-turbo";
      const tools = fm["tools"] || "bash,read,write,grep";
      const knowledgePath = join(dirname(filePath), `${name}-knowledge.md`);
      return { name, systemPrompt: match[2].trim(), model, tools, knowledgePath };
    }
    return { name: filePath, systemPrompt: raw.trim(), model: "glm/glm-5-turbo", tools: "bash,read,write,grep", knowledgePath: filePath + "-knowledge.md" };
  } catch {
    return null;
  }
}

function loadMemberKnowledge(member: MemberDef): string {
  if (!existsSync(member.knowledgePath)) return "";
  const content = readFileSync(member.knowledgePath, "utf-8").trim();
  if (!content) return "";
  return `\n\n## ${member.name} 個人知識庫\n\n${content}`;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^\w\u4e00-\u9fff\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 60);
}

function displayName(name: string): string {
  return name.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function extractSection(memo: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}[^\n]*\n([\\s\\S]*?)(?=\n##\\s|$)`, "i");
  const m = memo.match(re);
  return m ? m[1].trim() : "";
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

// ── Subprocess ─────────────────────────────────────────────────────────────────

interface RunResult { output: string; exitCode: number; elapsed: number; }

function runSubagent(
  systemPrompt: string,
  prompt: string,
  model: string = "glm/glm-5-turbo",
  tools: string = "bash,read,write,grep",
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = [
    "--mode", "json", "-p", "--no-extensions",
    "--model", model, "--tools", tools, "--thinking", "off",
    "--append-system-prompt", systemPrompt, "--no-session", prompt,
  ];

  const textChunks: string[] = [];
  const startTime = Date.now();

  return new Promise((res) => {
    const proc = spawn("pi", args, { stdio: ["ignore", "pipe", "pipe"], env: { ...process.env } });
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

    const stderrChunks: string[] = [];
    proc.stderr!.setEncoding("utf-8");
    proc.stderr!.on("data", (c: string) => { stderrChunks.push(c); });

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
      const stderr = stderrChunks.join("").trim();
      const output = textChunks.join("");
      res({ output: output || (stderr ? `[stderr] ${stderr}` : ""), exitCode: code ?? 1, elapsed: Date.now() - startTime });
    });

    proc.on("error", (err) => {
      res({ output: `Error spawning subprocess: ${err.message}`, exitCode: 1, elapsed: Date.now() - startTime });
    });
  });
}

// ── HTML Report ────────────────────────────────────────────────────────────────

function generateHtmlReport(opts: {
  date: string; preset: string; topic: string;
  memberNames: string[]; leadFrame: string;
  boardResults: { name: string; output: string; error: boolean }[];
  synthesis: string;
}): string {
  const { date, preset, topic, memberNames, leadFrame, boardResults, synthesis } = opts;

  const finalSection = escapeHtml(extractSection(synthesis, "綜合洞見|Final Synthesis|Summary"));
  const nextActionsRaw = extractSection(synthesis, "Next Steps|下一步|延伸學習|建議行動");
  const actions = parseActionsList(nextActionsRaw);

  const memberCards = boardResults.filter(r => !r.error).map(r => {
    const firstChunk = r.output.replace(/\*+/g, "").split("\n\n")[0] || r.output.slice(0, 280);
    return `
      <div class="member-card">
        <div class="member-header">${escapeHtml(displayName(r.name))}</div>
        <div class="member-body">${escapeHtml(firstChunk.trim())}</div>
      </div>`;
  }).join("\n");

  const memberTags = memberNames.map(n =>
    `<span class="member-tag">${escapeHtml(displayName(n))}</span>`
  ).join("");

  const actionItems = actions.map(a => `<li>${escapeHtml(a)}</li>`).join("\n");

  const synthesisHtml = synthesis.split("\n").map(line => {
    if (line.startsWith("## ")) return `<div class="syn-heading">${escapeHtml(line.replace(/^##\s*/, ""))}</div>`;
    if (line.startsWith("### ")) return `<div class="syn-subheading">${escapeHtml(line.replace(/^###\s*/, ""))}</div>`;
    if (line.startsWith("- ") || line.startsWith("• ")) return `<div class="syn-bullet">${escapeHtml(line.replace(/^[-•]\s*/, ""))}</div>`;
    if (line.trim() === "") return `<div class="spacer"></div>`;
    return `<div class="syn-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Music Study — ${escapeHtml(topic)}</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #1e1e2e; --surface: #2a2a3f; --card-bg: #252536;
      --accent: #cba6f7; --green: #a6e3a1; --blue: #89b4fa;
      --peach: #fab387; --yellow: #f9e2af; --red: #f38ba8;
      --text: #cdd6f4; --muted: #7f849c; --border: rgba(203,166,247,0.18);
      --divider: rgba(255,255,255,0.06);
    }
    body { background: var(--bg); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px; line-height: 1.7; min-height: 100vh; }
    .container { max-width: 960px; margin: 0 auto; padding: 0 2rem; }
    header { text-align: center; padding: 4rem 2rem 2.5rem; border-bottom: 1px solid var(--divider); background: linear-gradient(180deg, rgba(203,166,247,0.06) 0%, transparent 100%); }
    .logo { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.35em; color: var(--accent); text-transform: uppercase; margin-bottom: 0.5rem; }
    .title { font-size: 1.9rem; font-weight: 800; color: var(--text); margin-bottom: 0.4rem; }
    .subtitle { font-size: 0.8rem; font-weight: 500; letter-spacing: 0.15em; text-transform: uppercase; color: var(--muted); margin-bottom: 1.2rem; }
    .meta { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; justify-content: center; gap: 0.5rem; flex-wrap: wrap; }
    .dot { opacity: 0.4; }
    .meta-badge { background: rgba(203,166,247,0.14); color: var(--accent); padding: 0.15rem 0.7rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; }
    section { padding: 2.5rem 0; border-bottom: 1px solid var(--divider); }
    section:last-of-type { border-bottom: none; }
    .section-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--accent); margin-bottom: 1.2rem; }
    .lead-block { padding: 1.2rem 1.5rem; border-left: 3px solid rgba(203,166,247,0.5); background: rgba(203,166,247,0.05); border-radius: 0 8px 8px 0; font-size: 0.9rem; color: var(--muted); line-height: 1.8; white-space: pre-wrap; }
    .lead-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 0.6rem; }
    .members-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.1rem; }
    .member-card { background: var(--card-bg); border: 1px solid var(--border); border-top: 3px solid var(--accent); border-radius: 8px; padding: 1.2rem; }
    .member-header { font-size: 0.85rem; font-weight: 700; color: var(--accent); margin-bottom: 0.8rem; letter-spacing: 0.04em; }
    .member-body { font-size: 0.83rem; color: var(--muted); line-height: 1.7; }
    .member-tags { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.2rem; }
    .member-tag { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; background: rgba(203,166,247,0.12); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 4px; }
    .synthesis-section { padding: 2.5rem 2rem; background: rgba(203,166,247,0.03); }
    .syn-heading { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--blue); margin: 1.2rem 0 0.5rem; }
    .syn-heading:first-child { margin-top: 0; }
    .syn-subheading { font-size: 0.78rem; font-weight: 600; color: var(--peach); margin: 0.8rem 0 0.3rem; }
    .syn-bullet { padding-left: 1.2rem; position: relative; font-size: 0.88rem; color: var(--text); line-height: 1.75; margin: 0.2rem 0; }
    .syn-bullet::before { content: "♩"; position: absolute; left: 0; color: var(--accent); font-size: 0.75rem; top: 0.15rem; }
    .syn-line { font-size: 0.88rem; color: var(--muted); line-height: 1.75; }
    .spacer { height: 0.5rem; }
    .decision-block { border-left: 4px solid var(--accent); padding: 1.2rem 1.5rem; background: rgba(203,166,247,0.06); border-radius: 0 8px 8px 0; margin-bottom: 1.2rem; }
    .decision-text { font-size: 1.0rem; font-weight: 600; color: var(--text); line-height: 1.75; }
    .actions-list { list-style: none; padding: 0; counter-reset: actions; }
    .actions-list li { counter-increment: actions; display: flex; align-items: flex-start; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--divider); font-size: 0.9rem; line-height: 1.65; }
    .actions-list li:last-child { border-bottom: none; }
    .actions-list li::before { content: counter(actions, decimal-leading-zero); color: var(--accent); font-weight: 700; font-size: 0.82rem; flex-shrink: 0; margin-top: 0.1rem; min-width: 2rem; }
    footer { text-align: center; padding: 2.5rem 2rem; border-top: 1px solid var(--divider); }
    footer span { font-size: 0.82rem; font-style: italic; color: var(--muted); opacity: 0.6; display: block; }
  </style>
</head>
<body>
  <header>
    <div class="logo">Music Study Board</div>
    <div class="title">${escapeHtml(topic)}</div>
    <div class="subtitle">Multi-Agent Music Research</div>
    <div class="meta">
      <span>${escapeHtml(date)}</span><span class="dot">·</span>
      <span class="meta-badge">${escapeHtml(preset)}</span><span class="dot">·</span>
      <span>${boardResults.filter(r => !r.error).length} 位研究員</span>
    </div>
  </header>

  <div class="container">
    <section>
      <div class="section-label">研究方向框架</div>
      <div class="lead-block">
        <div class="lead-label">Research Lead</div>
        ${escapeHtml(leadFrame)}
      </div>
    </section>

    <section>
      <div class="section-label">各成員研究結果</div>
      <div class="member-tags">${memberTags}</div>
      <div class="members-grid" style="margin-top: 1rem">${memberCards}</div>
    </section>

    <section class="synthesis-section">
      <div class="section-label">整合洞見</div>
      ${finalSection ? `<div class="decision-block"><p class="decision-text">${finalSection}</p></div>` : ""}
      <div class="synthesis-body">${synthesisHtml}</div>
    </section>

    ${actionItems ? `<section>
      <div class="section-label">延伸學習</div>
      <ol class="actions-list">${actionItems}</ol>
    </section>` : ""}
  </div>

  <footer>
    <span>Music Study Board — Generated by Pi Multi-Agent System</span>
    <span>glm/glm-5-turbo · ${escapeHtml(date)}</span>
  </footer>
</body>
</html>`;
}

// ── Extension ──────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: any;
  let boardConfig: BoardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
  let activePreset: string | null = null;
  let memberStates: MemberState[] = [];
  let boardPhase: "idle" | "framing" | "researching" | "synthesizing" | "done" = "idle";
  let leadFrameText = "";
  let cwd = "";

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "music-study", "config.yaml");
    if (!existsSync(configPath)) return;
    try {
      const raw = readFileSync(configPath, "utf-8");
      boardConfig = parseBoardConfigYaml(raw);
    } catch { }
  }

  function getActiveMembers(presetOverride?: string): BoardMemberConfig[] {
    const preset = presetOverride || activePreset;
    if (preset && boardConfig.presets[preset]) {
      const names = new Set(boardConfig.presets[preset]);
      return boardConfig.board.filter(m => names.has(m.name));
    }
    return boardConfig.board.filter(m => m.active);
  }

  // ── Widget ───────────────────────────────────────────────────────────────────

  function renderMemberCard(state: MemberState, colWidth: number, theme: any): string[] {
    const w = colWidth - 2;
    const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 3) + "..." : s;
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

    const top = "┌" + "─".repeat(w) + "┐";
    const bot = "└" + "─".repeat(w) + "┘";
    const sideBorder = (content: string, visLen: number) =>
      theme.fg("borderMuted", "│") + content + " ".repeat(Math.max(0, w - visLen)) + theme.fg("borderMuted", "│");

    return [
      theme.fg("accent", top),
      sideBorder(" " + nameStr, 1 + nameVisible),
      sideBorder(" " + statusLine, 1 + statusVisible),
      sideBorder(" " + workLine, 1 + workVisible),
      sideBorder(" ", 1),
      theme.fg("borderMuted", bot),
    ];
  }

  function updateWidget() {
    if (!widgetCtx) return;
    const members = memberStates;

    widgetCtx.ui.setWidget("music-study", (_tui: any, theme: any) => {
      const text = new Text("", 0, 1);
      return {
        render(width: number): string[] {
          if (boardPhase === "idle" || members.length === 0) {
            text.setText(theme.fg("dim", "Music Study Board idle. Use study_begin to start research."));
            return text.render(width);
          }

          const phaseLabel = boardPhase === "framing" ? "● Research Lead 框架中..."
            : boardPhase === "researching" ? "● 研究員並行調查中...（工具使用中，請耐心等候）"
              : boardPhase === "synthesizing" ? "● 整合研究結果中..."
                : boardPhase === "done" ? "✓ 研究完成" : "";
          const headerLine = theme.fg("accent", phaseLabel);

          if (boardPhase === "framing" && leadFrameText) {
            const preview = leadFrameText.split("\n").filter((l: string) => l.trim()).slice(-2).join(" · ");
            const truncated = preview.length > width - 4 ? preview.slice(0, width - 7) + "..." : preview;
            text.setText(headerLine + "\n\n" + theme.fg("muted", truncated));
            return text.render(width);
          }

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
              for (let c = 1; c < rowMembers.length; c++) rowStr += " ".repeat(GAP) + cards[c][line];
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

  // ── Run a single member ───────────────────────────────────────────────────────

  function runMember(
    memberConfig: BoardMemberConfig,
    memberDef: MemberDef,
    leadFrame: string,
    topic: string,
    stateIndex: number,
  ): Promise<{ name: string; output: string; error: boolean }> {
    const state = memberStates[stateIndex];
    state.status = "running";
    state.elapsed = 0;
    updateWidget();

    const startTime = Date.now();
    const timer = setInterval(() => { state.elapsed = Date.now() - startTime; updateWidget(); }, 1000);

    const systemPrompt = memberDef.systemPrompt + loadMemberKnowledge(memberDef);

    const prompt =
      `Research Lead 已框架此次研究方向：\n\n${leadFrame}\n\n` +
      `研究主題：${topic}\n\n` +
      `請以 ${displayName(memberConfig.name)} 的角色進行研究，包含：\n` +
      `- 使用你的工具（wsp-v3、summarize、bash 等）進行實際研究\n` +
      `- 從你的專業角度提供最有深度的洞見\n` +
      `- 具體的資料、來源、或可行動的建議\n` +
      `- 你想問其他成員的一個問題\n\n` +
      `以你的輸出格式回應。全程使用繁體中文。`;

    return runSubagent(systemPrompt, prompt, memberDef.model, memberDef.tools, (chunk) => {
      const full = state.lastWork + chunk;
      const last = full.split("\n").filter((l: string) => l.trim()).pop() || "";
      state.lastWork = last;
      updateWidget();
    }).then(result => {
      clearInterval(timer);
      state.elapsed = Date.now() - startTime;
      state.status = result.exitCode === 0 ? "done" : "error";
      state.lastWork = result.output.split("\n").filter((l: string) => l.trim()).pop() || "";
      updateWidget();
      return { name: memberConfig.name, output: result.output, error: result.exitCode !== 0 };
    }).catch(err => {
      clearInterval(timer);
      state.status = "error";
      state.lastWork = String(err);
      updateWidget();
      return { name: memberConfig.name, output: `Error: ${err}`, error: true };
    });
  }

  // ── study_begin Tool ──────────────────────────────────────────────────────────

  pi.registerTool({
    name: "study_begin",
    label: "Study Begin",
    description:
      "啟動音樂研究小組。提供研究主題（inline 或 .md 路徑）。" +
      "Research Lead 框架問題後，各研究員並行使用工具調查，最後整合輸出 HTML 報告。",
    parameters: Type.Object({
      topic: Type.String({
        description: "研究主題或問題（inline 文字或 .md 檔案路徑）",
      }),
      preset: Type.Optional(Type.String({
        description: "覆蓋研究組合（full/jazz-deep/discovery/quick）",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const raw = params as { topic?: unknown; preset?: unknown };
      const topic = typeof raw.topic === "string" ? raw.topic : String(raw.topic ?? "");
      const preset = typeof raw.preset === "string" ? raw.preset : undefined;

      let topicText = topic;
      if (topic.trim().endsWith(".md")) {
        const topicPath = resolve(cwd, topic.trim());
        if (existsSync(topicPath)) {
          topicText = readFileSync(topicPath, "utf-8");
        } else {
          return { content: [{ type: "text", text: `主題檔案未找到：${topicPath}` }], details: { status: "error" } };
        }
      }

      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return { content: [{ type: "text", text: "沒有活躍的研究員。請檢查 config.yaml 或選擇 preset。" }], details: { status: "error" } };
      }

      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return {
          content: [{ type: "text", text: `缺少 agent 檔案：\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }],
          details: { status: "error" },
        };
      }

      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const def = parseMemberFile(resolve(cwd, member.path));
        if (def) memberDefs.set(member.name, def);
      }

      memberStates = activeMembers.map(m => ({ name: m.name, status: "pending" as const, elapsed: 0, lastWork: "" }));
      boardPhase = "framing";
      leadFrameText = "";
      updateWidget();

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `召集 ${activeMembers.length} 位研究員...` }], details: { status: "running", phase: "framing" } });

      // ── Research Lead framing ───────────────────────────────────────────────

      const leadSystemPrompt =
        `你是音樂研究小組的 Research Lead。你的小組包含：\n` +
        `- Deep Researcher：挖掘 niche 評論家與學術資料\n` +
        `- YouTube Curator：策展影片清單與演出記錄\n` +
        `- Genre Historian：追蹤流派脈絡與影響地圖\n` +
        `- Listening Guide：設計結構化聆聽路線\n\n` +
        `你負責框架研究問題，讓每位成員知道從哪個角度切入。`;

      const leadPrompt =
        `研究主題：${topicText}\n\n` +
        `請框架此次研究，為每位成員指定切入角度（各1-2句）：\n` +
        `- Deep Researcher 應該挖掘什麼？\n` +
        `- YouTube Curator 應該找什麼類型的影片？\n` +
        `- Genre Historian 應該追蹤什麼脈絡？\n` +
        `- Listening Guide 應該設計什麼學習路線？\n\n` +
        `150-200 字。全程繁體中文。`;

      const leadResult = await runSubagent(leadSystemPrompt, leadPrompt, "glm/glm-5-turbo", "none", (chunk) => {
        leadFrameText += chunk;
        updateWidget();
      });
      const leadFrame = leadResult.output;

      if (onUpdate) onUpdate({ content: [{ type: "text", text: "研究框架完成。各研究員並行調查中（使用工具，可能需要數分鐘）..." }], details: { status: "running", phase: "researching" } });

      // ── Members in parallel ─────────────────────────────────────────────────

      boardPhase = "researching";
      memberStates.forEach(s => { s.status = "pending"; });
      updateWidget();

      const boardResults = await Promise.all(
        activeMembers.map((member, i) => {
          const def = memberDefs.get(member.name);
          if (!def) {
            memberStates[i].status = "error";
            memberStates[i].lastWork = "Agent 檔案未找到";
            updateWidget();
            return Promise.resolve({ name: member.name, output: "Error: agent file not found", error: true });
          }
          return runMember(member, def, leadFrame, topicText, i);
        })
      );

      // ── Synthesis ───────────────────────────────────────────────────────────

      boardPhase = "synthesizing";
      updateWidget();

      if (onUpdate) onUpdate({ content: [{ type: "text", text: "研究完畢。整合洞見中..." }], details: { status: "running", phase: "synthesizing" } });

      const validResults = boardResults.filter(r => !r.error);
      const allOutputs = validResults.map(r => `### ${displayName(r.name)}\n${r.output}`).join("\n\n");

      const synthesisPrompt =
        `你是音樂研究小組的 Research Lead。整合以下四位研究員的發現，輸出結構化報告。\n\n` +
        `研究主題：${topicText}\n\n` +
        `各成員發現：\n${allOutputs}\n\n` +
        `輸出以下章節：\n\n` +
        `## 綜合洞見\n[整合所有成員觀點的核心結論，3-4句]\n\n` +
        `## 深度發現\n[最有價值的 insider 知識、歷史脈絡或分析]\n\n` +
        `## 推薦資源\n[YouTube 影片、專輯、文章的整合清單]\n\n` +
        `## Next Steps\n[3-5 條具體延伸學習行動]\n\n` +
        `## 成員觀點差異\n[不同成員之間有什麼有趣的觀點對比]\n\n` +
        `全程繁體中文。章節標題保持英文以便解析。`;

      const synthResult = await runSubagent(leadSystemPrompt, synthesisPrompt, "glm/glm-5-turbo", "none");
      const synthesis = synthResult.output;

      // ── Save report ─────────────────────────────────────────────────────────

      const reportsDir = join(cwd, ".pi", "music-study", "reports");
      mkdirSync(reportsDir, { recursive: true });

      const topicFirstLine = topicText.split("\n").find(l => l.trim()) || "music-research";
      const slug = slugify(topicFirstLine.replace(/^#+\s*/, ""));
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const reportFilename = `${slug}-${timestamp}`;
      const mdPath = join(reportsDir, `${reportFilename}.md`);
      const htmlPath = join(reportsDir, `${reportFilename}.html`);

      const mdContent =
        `# Music Study Report\n\n` +
        `**Date:** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Preset:** ${preset || activePreset || "custom"}\n` +
        `**Members:** ${activeMembers.map(m => displayName(m.name)).join(", ")}\n\n` +
        `---\n\n## Topic\n\n${topicText}\n\n` +
        `---\n\n## Research Lead Framing\n\n${leadFrame}\n\n` +
        `---\n\n## Member Research\n\n${allOutputs}\n\n` +
        `---\n\n${synthesis}`;

      writeFileSync(mdPath, mdContent, "utf-8");

      const htmlContent = generateHtmlReport({
        date: new Date().toISOString().slice(0, 10),
        preset: preset || activePreset || "custom",
        topic: topicFirstLine.replace(/^#+\s*/, ""),
        memberNames: activeMembers.map(m => m.name),
        leadFrame,
        boardResults,
        synthesis,
      });
      writeFileSync(htmlPath, htmlContent, "utf-8");

      boardPhase = "done";
      updateWidget();

      const truncated = synthesis.length > 8000 ? synthesis.slice(0, 8000) + "\n\n... [截斷 — 請查看報告檔案]" : synthesis;

      return {
        content: [{ type: "text", text: `報告已儲存：\n  📄 ${mdPath}\n  🌐 ${htmlPath}\n\n${truncated}` }],
        details: { status: "done", mdPath, htmlPath, preset: preset || activePreset, memberCount: activeMembers.length, synthesis },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : "";
      const topicPreview = (a.topic || "").slice(0, 50).replace(/\n/g, " ");
      const preview = topicPreview.length > 47 ? topicPreview.slice(0, 47) + "..." : topicPreview;
      return new Text(
        theme.fg("toolTitle", theme.bold("study_begin")) +
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
        const phaseZh = phase === "framing" ? "框架中" : phase === "researching" ? "研究員調查中" : phase === "synthesizing" ? "整合中" : phase;
        return new Text(theme.fg("accent", "● music-study") + theme.fg("dim", ` ${phaseZh}...`), 0, 0);
      }
      if (details.status === "error") return new Text(theme.fg("error", "✗ study_begin 失敗"), 0, 0);
      return new Text(
        theme.fg("success", "✓ music-study") +
        theme.fg("dim", ` · ${details.memberCount} 位研究員 · `) +
        theme.fg("muted", details.mdPath || ""),
        0, 0,
      );
    },
  });

  // ── Commands ──────────────────────────────────────────────────────────────────

  pi.registerCommand("study-preset", {
    description: "Select research preset (full/jazz-deep/discovery/quick)",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const presetNames = Object.keys(boardConfig.presets);
      if (presetNames.length === 0) { ctx.ui.notify("No presets defined in config.yaml", "warning"); return; }
      const options = presetNames.map(name => `${name} (${boardConfig.presets[name].join(", ")})`);
      const choice = await ctx.ui.select("Select Research Preset", options);
      if (choice === undefined) return;
      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];
      const members = boardConfig.presets[activePreset];
      ctx.ui.setStatus("music-study", `Preset: ${activePreset} · ${members.length} researchers`);
      ctx.ui.notify(`Preset: ${activePreset}\nResearchers: ${members.map(displayName).join(", ")}`, "info");
      updateWidget();
    },
  });

  pi.registerCommand("study-status", {
    description: "Show active researchers",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const active = getActiveMembers();
      const all = boardConfig.board;
      const lines = all.map(m => {
        const isActive = active.some(a => a.name === m.name);
        return `${isActive ? "✓" : "○"} ${displayName(m.name)}`;
      });
      const presetInfo = activePreset ? `Preset: ${activePreset}` : "Using config active flags";
      ctx.ui.notify(`${presetInfo}\n\n${lines.join("\n")}\n\nNote: Researchers use real tools (wsp-v3, summarize, bash). Expect longer run times.`, "info");
    },
  });

  pi.registerCommand("study-history", {
    description: "List recent research reports",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const reportsDir = join(cwd, ".pi", "music-study", "reports");
      if (!existsSync(reportsDir)) { ctx.ui.notify("No reports yet. Run study_begin to create the first research.", "info"); return; }
      const files = readdirSync(reportsDir).filter(f => f.endsWith(".md")).sort().reverse().slice(0, 10);
      if (files.length === 0) { ctx.ui.notify("No reports found in .pi/music-study/reports/", "info"); return; }
      const lines = files.map((f, i) => {
        const hasHtml = existsSync(join(reportsDir, f.replace(/\.md$/, ".html")));
        return `${i + 1}. ${f}${hasHtml ? " 🌐" : ""}`;
      });
      ctx.ui.notify(`Recent research (${files.length}):\n\n${lines.join("\n")}\n\n📁 ${reportsDir}`, "info");
    },
  });

  // ── Session Start ─────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);

    if (widgetCtx) widgetCtx.ui.setWidget("music-study", undefined);
    ctx.ui.setWidget("music-study", undefined);
    widgetCtx = ctx;

    boardPhase = "idle";
    memberStates = [];
    activePreset = null;

    loadConfig(ctx.cwd);

    const active = getActiveMembers();
    ctx.ui.setStatus("music-study", `Music Study · ${active.length} researchers`);
    ctx.ui.notify(
      `Music Study Board\n` +
      `${active.length} researchers · Tools enabled (wsp-v3, summarize, bash)\n\n` +
      `/study-preset    Select preset\n` +
      `/study-status    Show researchers\n` +
      `/study-history   Recent reports`,
      "info",
    );

    updateWidget();

    ctx.ui.setFooter((_tui: any, theme: any, _footerData: any) => ({
      dispose: () => { },
      invalidate() { },
      render(width: number): string[] {
        const presetLabel = activePreset || "default";
        const memberCount = getActiveMembers().length;
        const left =
          theme.fg("dim", ` glm/glm-5-turbo`) +
          theme.fg("muted", " · ") +
          theme.fg("accent", "music-study") +
          theme.fg("muted", " · ") +
          theme.fg("dim", presetLabel) +
          theme.fg("muted", " · ") +
          theme.fg("dim", `${memberCount} researchers`);
        const right = theme.fg("dim", ` `);
        const pad = " ".repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));
        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });
}
