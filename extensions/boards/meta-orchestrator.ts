/**
 * Meta-Orchestrator — 跨域多委員會戰略分析系統
 *
 * 頂層 Orchestrator 接收問題後，先調用地緣政治分析師，
 * 再並行委派各委員會 CEO，最後整合跨域洞見輸出報告。
 *
 * Structure:
 *   Meta-Orchestrator
 *   ├── Geopolitics Expert  ── 共享跨板專家（優先運行）
 *   ├── Investment Adviser Board (CEO)
 *   ├── Drip Music Board (Brand Lead)
 *   └── AI Tools Board (Director)
 *
 * Config: .pi/meta-orchestrator/config.yaml
 * Agents: .pi/meta-orchestrator/agents/
 * Memos:  .pi/meta-orchestrator/memos/
 *
 * Commands:
 *   /orchestrate-preset  — 選擇委員會組合（full/strategic/tech-policy/etc.）
 *   /orchestrate-status  — 顯示目前活躍委員會
 *
 * Tools:
 *   orchestrate  — 全自動分析 → HTML 報告（Orchestrator 路由 → 地緣政治 → 各委員會 CEO 並行 → 綜合）
 *
 * Usage: pi -e extensions/boards/meta-orchestrator.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve, dirname } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Types ──────────────────────────────────────────────────────────────────────

interface OrchestratorConfig {
  name: string;
  path: string;
  model: string;
}

interface SharedExpertConfig {
  name: string;
  path: string;
  active: boolean;
}

interface BoardDelegateConfig {
  name: string;
  label: string;
  description: string;
  ceo_path: string;
  knowledge_base_path?: string;
  active: boolean;
}

interface MetaConfig {
  meeting: { discussion_time_minutes: number };
  orchestrator: OrchestratorConfig;
  shared_experts: SharedExpertConfig[];
  boards: BoardDelegateConfig[];
  presets: Record<string, string[]>;
}

interface AgentDef {
  name: string;
  systemPrompt: string;
  model: string;
  tools: string;
  knowledgePath: string;
}

interface BoardState {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
  elapsed: number;
  lastWork: string;
}

// ── YAML Parser ────────────────────────────────────────────────────────────────

function parseMetaConfigYaml(raw: string): MetaConfig {
  const config: MetaConfig = {
    meeting: { discussion_time_minutes: 15 },
    orchestrator: { name: "orchestrator", path: "", model: "openai-codex/gpt-5.2-codex" },
    shared_experts: [],
    boards: [],
    presets: {},
  };

  const lines = raw.split("\n");
  let section = "";
  let inItem = false;
  let currentItem: Record<string, any> = {};

  const flushExpert = () => {
    if (inItem && currentItem["name"]) {
      config.shared_experts.push({
        name: currentItem["name"],
        path: currentItem["path"] || "",
        active: currentItem["active"] !== false,
      });
    }
    currentItem = {};
    inItem = false;
  };

  const flushBoard = () => {
    if (inItem && currentItem["name"]) {
      config.boards.push({
        name: currentItem["name"],
        label: currentItem["label"] || currentItem["name"],
        description: currentItem["description"] || "",
        ceo_path: currentItem["ceo_path"] || "",
        knowledge_base_path: currentItem["knowledge_base_path"],
        active: currentItem["active"] !== false,
      });
    }
    currentItem = {};
    inItem = false;
  };

  for (const line of lines) {
    if (line.match(/^meeting:\s*$/)) {
      if (section === "shared_experts") flushExpert();
      if (section === "boards") flushBoard();
      section = "meeting"; inItem = false; continue;
    }
    if (line.match(/^orchestrator:\s*$/)) {
      if (section === "shared_experts") flushExpert();
      if (section === "boards") flushBoard();
      section = "orchestrator"; inItem = false; continue;
    }
    if (line.match(/^shared_experts:\s*$/)) {
      if (section === "boards") flushBoard();
      section = "shared_experts"; inItem = false; continue;
    }
    if (line.match(/^boards:\s*$/)) {
      if (section === "shared_experts") flushExpert();
      section = "boards"; inItem = false; continue;
    }
    if (line.match(/^presets:\s*$/)) {
      if (section === "shared_experts") flushExpert();
      if (section === "boards") flushBoard();
      section = "presets"; inItem = false; continue;
    }

    if (section === "meeting") {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) config.meeting.discussion_time_minutes = parseInt(m[1], 10);
      continue;
    }

    if (section === "orchestrator") {
      const nm = line.match(/^\s+name:\s*(.+)$/);
      if (nm) { config.orchestrator.name = nm[1].trim(); continue; }
      const pm = line.match(/^\s+path:\s*(.+)$/);
      if (pm) { config.orchestrator.path = pm[1].trim(); continue; }
      const mm = line.match(/^\s+model:\s*(.+)$/);
      if (mm) { config.orchestrator.model = mm[1].trim(); continue; }
      continue;
    }

    if (section === "shared_experts") {
      if (line.match(/^\s+-\s+name:/)) {
        flushExpert();
        inItem = true;
        const m = line.match(/^\s+-\s+name:\s*(.+)$/);
        if (m) currentItem["name"] = m[1].trim();
        continue;
      }
      if (inItem) {
        const pm = line.match(/^\s+path:\s*(.+)$/);
        if (pm) { currentItem["path"] = pm[1].trim(); continue; }
        const am = line.match(/^\s+active:\s*(true|false)/);
        if (am) { currentItem["active"] = am[1] === "true"; continue; }
      }
      continue;
    }

    if (section === "boards") {
      if (line.match(/^\s+-\s+name:/)) {
        flushBoard();
        inItem = true;
        const m = line.match(/^\s+-\s+name:\s*(.+)$/);
        if (m) currentItem["name"] = m[1].trim();
        continue;
      }
      if (inItem) {
        const lm = line.match(/^\s+label:\s*(.+)$/);
        if (lm) { currentItem["label"] = lm[1].trim(); continue; }
        const dm = line.match(/^\s+description:\s*(.+)$/);
        if (dm) { currentItem["description"] = dm[1].trim(); continue; }
        const cm = line.match(/^\s+ceo_path:\s*(.+)$/);
        if (cm) { currentItem["ceo_path"] = cm[1].trim(); continue; }
        const km = line.match(/^\s+knowledge_base_path:\s*(.+)$/);
        if (km) { currentItem["knowledge_base_path"] = km[1].trim(); continue; }
        const am = line.match(/^\s+active:\s*(true|false)/);
        if (am) { currentItem["active"] = am[1] === "true"; continue; }
      }
      continue;
    }

    if (section === "presets") {
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        config.presets[m[1].trim()] = m[2].split(",").map(s => s.trim()).filter(Boolean);
      }
      continue;
    }
  }

  // Flush remaining
  if (section === "shared_experts") flushExpert();
  if (section === "boards") flushBoard();

  return config;
}

// ── Agent File Parser ──────────────────────────────────────────────────────────

function parseAgentFile(filePath: string): AgentDef | null {
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
      const model = fm["model"] || "kimi-coding/k2p5";
      const tools = fm["tools"] || "none";
      const knowledgePath = join(dirname(filePath), `${name}-knowledge.md`);
      return { name, systemPrompt: match[2].trim(), model, tools, knowledgePath };
    }
    return { name: filePath, systemPrompt: raw.trim(), model: "kimi-coding/k2p5", tools: "none", knowledgePath: filePath + "-knowledge.md" };
  } catch {
    return null;
  }
}

function loadAgentKnowledge(agent: AgentDef): string {
  if (!existsSync(agent.knowledgePath)) return "";
  const content = readFileSync(agent.knowledgePath, "utf-8").trim();
  if (!content) return "";
  return `\n\n## ${agent.name} 個人知識庫\n\n${content}`;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
}

function displayName(name: string): string {
  return name.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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

function extractSection(memo: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}[^\n]*\n([\\s\\S]*?)(?=\n##\\s|$)`, "i");
  const m = memo.match(re);
  return m ? m[1].trim() : "";
}

// ── Subprocess ─────────────────────────────────────────────────────────────────

interface RunResult {
  output: string;
  exitCode: number;
  elapsed: number;
}

function runSubagent(
  systemPrompt: string,
  prompt: string,
  model: string = "kimi-coding/k2p5",
  tools: string = "none",
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = [
    "--mode", "json",
    "-p",
    "--no-extensions",
    "--model", model,
    "--tools", tools,
    "--thinking", "off",
    "--append-system-prompt", systemPrompt,
    "--no-session",
    prompt,
  ];

  const textChunks: string[] = [];
  const startTime = Date.now();

  return new Promise((res) => {
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

    const stderrChunks: string[] = [];
    proc.stderr!.setEncoding("utf-8");
    proc.stderr!.on("data", (chunk: string) => { stderrChunks.push(chunk); });

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
      res({
        output: output || (stderr ? `[stderr] ${stderr}` : ""),
        exitCode: code ?? 1,
        elapsed: Date.now() - startTime,
      });
    });

    proc.on("error", (err) => {
      res({ output: `Error spawning subprocess: ${err.message}`, exitCode: 1, elapsed: Date.now() - startTime });
    });
  });
}

// ── HTML Report ────────────────────────────────────────────────────────────────

function generateHtmlReport(opts: {
  date: string;
  preset: string;
  briefText: string;
  routingMemo: string;
  geoBrief: string;
  boardResults: { name: string; label: string; output: string; error: boolean }[];
  synthesis: string;
}): string {
  const { date, preset, briefText, routingMemo, geoBrief, boardResults, synthesis } = opts;

  const finalDecision = escapeHtml(extractSection(synthesis, "Final Decision|最終建議|跨域建議"));
  const tensions = escapeHtml(extractSection(synthesis, "跨域張力|Tensions|分歧"));
  const nextActionsRaw = extractSection(synthesis, "Next Actions|行動清單|具體步驟|下一步");
  const actions = parseActionsList(nextActionsRaw);

  const boardCards = boardResults.filter(r => !r.error).map(r => {
    const firstPara = r.output.split("\n\n")[0] || r.output.slice(0, 300);
    return `
      <div class="board-card">
        <div class="board-card-header">${escapeHtml(r.label)}</div>
        <div class="board-card-body">${escapeHtml(firstPara.replace(/\*+/g, "").trim())}</div>
      </div>`;
  }).join("\n");

  const briefHtml = briefText.split("\n").map(line => {
    if (line.startsWith("## ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^##\s*/, ""))}</div>`;
    if (line.startsWith("# ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^#\s*/, ""))}</div>`;
    if (line.trim() === "") return `<div class="brief-spacer"></div>`;
    return `<div class="brief-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  const geoHtml = geoBrief.split("\n").map(line => {
    if (line.startsWith("## ") || line.startsWith("**## ")) {
      const clean = line.replace(/^\*+##\s*|\*+$/g, "").replace(/^##\s*/, "");
      return `<div class="geo-heading">${escapeHtml(clean)}</div>`;
    }
    if (line.startsWith("- ") || line.startsWith("• ")) {
      return `<div class="geo-bullet">${escapeHtml(line.replace(/^[-•]\s*/, ""))}</div>`;
    }
    if (line.trim() === "") return `<div class="brief-spacer"></div>`;
    return `<div class="brief-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  const actionItems = actions.map(a => `<li>${escapeHtml(a)}</li>`).join("\n");
  const activeBoardNames = boardResults.filter(r => !r.error).map(r =>
    `<span class="board-tag">${escapeHtml(r.label)}</span>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Meta-Orchestrator 跨域戰略報告</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #282a36; --card-bg: #21222c; --surface: #2e3047;
      --accent: #bd93f9; --secondary: #8be9fd; --green: #50fa7b;
      --orange: #ffb86c; --pink: #ff79c6; --red: #ff5555; --yellow: #f1fa8c;
      --text: #f8f8f2; --muted: #6272a4; --border: rgba(189,147,249,0.2);
      --divider: rgba(255,255,255,0.06);
    }
    body { background: var(--bg); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px; line-height: 1.7; min-height: 100vh; }
    .container { max-width: 980px; margin: 0 auto; padding: 0 2rem; }
    header { text-align: center; padding: 4rem 2rem 2.5rem; border-bottom: 1px solid var(--divider); background: linear-gradient(180deg, rgba(189,147,249,0.07) 0%, transparent 100%); }
    .logo { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.35em; color: var(--accent); text-transform: uppercase; margin-bottom: 0.5rem; }
    .title { font-size: 1.9rem; font-weight: 800; color: var(--text); margin-bottom: 0.4rem; }
    .subtitle { font-size: 0.8rem; font-weight: 500; letter-spacing: 0.15em; text-transform: uppercase; color: var(--muted); margin-bottom: 1.2rem; }
    .meta { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; justify-content: center; gap: 0.5rem; flex-wrap: wrap; }
    .dot { opacity: 0.4; }
    .meta-badge { background: rgba(189,147,249,0.14); color: var(--accent); padding: 0.15rem 0.7rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; }
    section { padding: 2.5rem 0; border-bottom: 1px solid var(--divider); }
    section:last-of-type { border-bottom: none; }
    .section-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--accent); margin-bottom: 1.2rem; }
    .brief-section { background: rgba(139,233,253,0.03); padding: 2.5rem 2rem; }
    .brief-heading { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin: 1rem 0 0.4rem; }
    .brief-line { color: var(--muted); font-size: 0.9rem; line-height: 1.8; }
    .brief-spacer { height: 0.5rem; }
    .routing-block { margin-top: 1rem; padding: 1rem 1.2rem; border-left: 3px solid rgba(189,147,249,0.5); background: rgba(189,147,249,0.05); border-radius: 0 6px 6px 0; font-size: 0.88rem; color: var(--muted); line-height: 1.8; white-space: pre-wrap; }
    .routing-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 0.5rem; }
    .geo-section { background: rgba(80,250,123,0.03); padding: 2.5rem 2rem; }
    .geo-heading { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.1em; color: var(--green); margin: 1.2rem 0 0.4rem; text-transform: uppercase; }
    .geo-heading:first-child { margin-top: 0; }
    .geo-bullet { padding-left: 1rem; position: relative; color: var(--text); font-size: 0.9rem; line-height: 1.75; margin: 0.3rem 0; }
    .geo-bullet::before { content: "▸"; position: absolute; left: 0; color: var(--green); }
    .decision-section { background: rgba(189,147,249,0.04); padding: 2.5rem 2rem; }
    .decision-block { border-left: 4px solid var(--accent); padding: 1.2rem 1.5rem; background: rgba(189,147,249,0.06); border-radius: 0 8px 8px 0; }
    .decision-main { font-size: 1.0rem; font-weight: 600; color: var(--text); line-height: 1.75; white-space: pre-wrap; }
    .tensions-block { margin-top: 1.2rem; padding: 1rem 1.2rem; border-left: 3px solid var(--orange); background: rgba(255,184,108,0.05); border-radius: 0 6px 6px 0; font-size: 0.88rem; color: var(--muted); line-height: 1.8; white-space: pre-wrap; }
    .tensions-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--orange); font-weight: 600; margin-bottom: 0.5rem; }
    .boards-section { padding: 2.5rem 2rem; }
    .boards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.2rem; }
    .board-card { background: var(--card-bg); border: 1px solid var(--border); border-top: 3px solid var(--accent); border-radius: 8px; padding: 1.3rem 1.5rem; }
    .board-card-header { font-size: 0.85rem; font-weight: 700; color: var(--accent); margin-bottom: 0.8rem; letter-spacing: 0.05em; }
    .board-card-body { font-size: 0.85rem; color: var(--muted); line-height: 1.7; }
    .board-tags { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.8rem; }
    .board-tag { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; background: rgba(189,147,249,0.12); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 4px; }
    .actions-section { padding: 2.5rem 2rem; }
    .actions-list { list-style: none; padding: 0; counter-reset: actions; }
    .actions-list li { counter-increment: actions; display: flex; align-items: flex-start; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--divider); font-size: 0.9rem; line-height: 1.65; }
    .actions-list li:last-child { border-bottom: none; }
    .actions-list li::before { content: counter(actions, decimal-leading-zero); color: var(--accent); font-weight: 700; font-size: 0.82rem; letter-spacing: 0.05em; flex-shrink: 0; margin-top: 0.1rem; min-width: 2rem; }
    footer { text-align: center; padding: 2.5rem 2rem; display: flex; flex-direction: column; gap: 0.3rem; border-top: 1px solid var(--divider); }
    footer span { font-size: 0.82rem; font-style: italic; color: var(--muted); opacity: 0.6; }
  </style>
</head>
<body>
  <header>
    <div class="logo">Meta-Orchestrator</div>
    <div class="title">跨域戰略分析報告</div>
    <div class="subtitle">Cross-Domain Strategic Intelligence</div>
    <div class="meta">
      <span>${escapeHtml(date)}</span><span class="dot">·</span>
      <span class="meta-badge">${escapeHtml(preset)}</span><span class="dot">·</span>
      <span>${boardResults.filter(r => !r.error).length} 個委員會</span>
    </div>
  </header>

  <section class="brief-section">
    <div class="section-label">分析簡報</div>
    <div class="brief-body">${briefHtml}</div>
    <div class="routing-block">
      <div class="routing-label">Orchestrator 路由決策</div>
      ${escapeHtml(routingMemo.replace(/## ROUTING[\s\S]*$/, "").trim())}
    </div>
  </section>

  <section class="geo-section">
    <div class="section-label">地緣政治快報 — 共享背景分析</div>
    <div class="geo-body">${geoHtml}</div>
  </section>

  <section class="boards-section">
    <div class="section-label">各委員會視角</div>
    <div class="board-tags">${activeBoardNames}</div>
    <div class="boards-grid" style="margin-top: 1.2rem">${boardCards}</div>
  </section>

  <section class="decision-section">
    <div class="section-label">跨域綜合建議</div>
    <div class="decision-block">
      <p class="decision-main">${finalDecision || escapeHtml(synthesis.split("\n").find(l => l.trim() && !l.startsWith("#")) || "")}</p>
    </div>
    ${tensions ? `<div class="tensions-block">
      <div class="tensions-label">跨域張力與分歧</div>
      ${tensions}
    </div>` : ""}
  </section>

  ${actionItems ? `<section class="actions-section">
    <div class="section-label">行動清單</div>
    <ol class="actions-list">${actionItems}</ol>
  </section>` : ""}

  <footer>
    <span>本報告由 Meta-Orchestrator 多委員會系統自動生成，僅供參考。</span>
    <span>Meta-Orchestrator — Generated by Pi Multi-Agent System</span>
  </footer>
</body>
</html>`;
}

// ── Extension ──────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: any;
  let metaConfig: MetaConfig = {
    meeting: { discussion_time_minutes: 15 },
    orchestrator: { name: "orchestrator", path: "", model: "openai-codex/gpt-5.2-codex" },
    shared_experts: [],
    boards: [],
    presets: {},
  };
  let activePreset: string | null = null;
  let boardStates: BoardState[] = [];
  let geoStatus: "idle" | "running" | "done" | "error" = "idle";
  let orchestratorStatus: "idle" | "running" | "done" | "error" = "idle";
  let phase: "idle" | "routing" | "geopolitics" | "delegating" | "synthesizing" | "done" = "idle";
  let routingPreview = "";
  let cwd = "";

  // ── Config Loader ────────────────────────────────────────────────────────────

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "meta-orchestrator", "config.yaml");
    if (!existsSync(configPath)) return;
    try {
      const raw = readFileSync(configPath, "utf-8");
      metaConfig = parseMetaConfigYaml(raw);
    } catch { }
  }

  function getActiveBoards(presetOverride?: string): BoardDelegateConfig[] {
    const preset = presetOverride || activePreset;
    if (preset && metaConfig.presets[preset]) {
      const names = new Set(metaConfig.presets[preset]);
      return metaConfig.boards.filter(b => names.has(b.name));
    }
    return metaConfig.boards.filter(b => b.active);
  }

  // ── Widget ───────────────────────────────────────────────────────────────────

  function renderBoardCard(state: BoardState, colWidth: number, theme: any): string[] {
    const w = colWidth - 2;
    const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max - 3) + "..." : s;
    const stripMd = (s: string) => s.replace(/\*+([^*]+)\*+/g, "$1").replace(/_{1,2}([^_]+)_{1,2}/g, "$1");

    const statusColor = state.status === "pending" ? "dim"
      : state.status === "running" ? "accent"
        : state.status === "done" ? "success" : "error";
    const statusIcon = state.status === "pending" ? "○"
      : state.status === "running" ? "◉"
        : state.status === "done" ? "✓" : "✗";

    const label = state.label || displayName(state.name);
    const nameStr = theme.fg("accent", theme.bold(truncate(label, w)));
    const nameVisible = Math.min(label.length, w);
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

    widgetCtx.ui.setWidget("meta-orchestrator", (_tui: any, theme: any) => {
      const text = new Text("", 0, 1);

      return {
        render(width: number): string[] {
          if (phase === "idle") {
            text.setText(theme.fg("dim", "Meta-Orchestrator idle. Use orchestrate to begin."));
            return text.render(width);
          }

          const phaseLabel =
            phase === "routing" ? "● Orchestrator 路由分析中..."
              : phase === "geopolitics" ? "● 地緣政治分析師運行中..."
                : phase === "delegating" ? "● 各委員會 CEO 並行分析中..."
                  : phase === "synthesizing" ? "● Orchestrator 跨域整合中..."
                    : phase === "done" ? "✓ 分析完成" : "";

          const headerLine = theme.fg("accent", phaseLabel);
          const lines: string[] = [headerLine, ""];

          // Orchestrator + Geo status row
          const orchIcon = orchestratorStatus === "done" ? theme.fg("success", "✓ Orchestrator")
            : orchestratorStatus === "running" ? theme.fg("accent", "◉ Orchestrator")
              : orchestratorStatus === "error" ? theme.fg("error", "✗ Orchestrator")
                : theme.fg("dim", "○ Orchestrator");
          const geoIcon = geoStatus === "done" ? theme.fg("success", "✓ Geopolitics")
            : geoStatus === "running" ? theme.fg("accent", "◉ Geopolitics")
              : geoStatus === "error" ? theme.fg("error", "✗ Geopolitics")
                : theme.fg("dim", "○ Geopolitics");

          lines.push(`  ${orchIcon}   ${geoIcon}`);

          if (phase === "routing" && routingPreview) {
            const preview = routingPreview.split("\n").filter((l: string) => l.trim()).slice(-2).join(" · ");
            const truncated = preview.length > width - 4 ? preview.slice(0, width - 7) + "..." : preview;
            lines.push("");
            lines.push(theme.fg("muted", truncated));
          }

          if (boardStates.length > 0 && (phase === "delegating" || phase === "synthesizing" || phase === "done")) {
            lines.push("");
            const COLS = Math.min(3, boardStates.length);
            const GAP = 2;
            const colWidth = Math.max(14, Math.floor((width - GAP * (COLS - 1)) / COLS));

            for (let start = 0; start < boardStates.length; start += COLS) {
              const rowStates = boardStates.slice(start, start + COLS);
              const cards = rowStates.map(s => renderBoardCard(s, colWidth, theme));
              const cardHeight = cards[0].length;
              for (let line = 0; line < cardHeight; line++) {
                let rowStr = cards[0][line];
                for (let c = 1; c < rowStates.length; c++) {
                  rowStr += " ".repeat(GAP) + cards[c][line];
                }
                lines.push(rowStr);
              }
              lines.push("");
            }
          }

          text.setText(lines.join("\n"));
          return text.render(width);
        },
        invalidate() { text.invalidate(); },
      };
    });
  }

  // ── orchestrate Tool ─────────────────────────────────────────────────────────

  pi.registerTool({
    name: "orchestrate",
    label: "Orchestrate",
    description:
      "啟動 Meta-Orchestrator 跨域分析。提供 brief（inline 或 .md 路徑）。" +
      "Orchestrator 路由 → 地緣政治專家 → 各委員會 CEO 並行 → 跨域綜合報告（HTML + MD）。",
    parameters: Type.Object({
      brief: Type.String({
        description: "分析問題或 brief 文字（markdown），或 .md 檔案路徑",
      }),
      preset: Type.Optional(Type.String({
        description: "指定委員會組合（full/strategic/tech-policy/investment-geo/creative）",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const raw = params as { brief?: unknown; preset?: unknown };
      const brief = typeof raw.brief === "string" ? raw.brief : String(raw.brief ?? "");
      const preset = typeof raw.preset === "string" ? raw.preset : undefined;

      // 1. Resolve brief text
      let briefText = brief;
      if (brief.trim().endsWith(".md")) {
        const briefPath = resolve(cwd, brief.trim());
        if (existsSync(briefPath)) {
          briefText = readFileSync(briefPath, "utf-8");
        } else {
          return {
            content: [{ type: "text", text: `Brief 檔案未找到：${briefPath}` }],
            details: { status: "error" },
          };
        }
      }

      // 2. Resolve active boards
      const activeBoards = getActiveBoards(preset);
      if (activeBoards.length === 0) {
        return {
          content: [{ type: "text", text: "沒有活躍的委員會。請檢查 config.yaml 或選擇一個 preset。" }],
          details: { status: "error" },
        };
      }

      // Check board CEO paths exist
      const missingBoards = activeBoards.filter(b => !existsSync(resolve(cwd, b.ceo_path)));
      if (missingBoards.length > 0) {
        return {
          content: [{
            type: "text",
            text: `缺少 CEO agent 檔案：\n${missingBoards.map(b => `  • ${b.name}: ${b.ceo_path}`).join("\n")}`,
          }],
          details: { status: "error" },
        };
      }

      // 3. Load orchestrator def
      const orchPath = resolve(cwd, metaConfig.orchestrator.path);
      const orchDef = existsSync(orchPath) ? parseAgentFile(orchPath) : null;
      const orchModel = orchDef?.model || metaConfig.orchestrator.model;
      const orchSystemPrompt = orchDef
        ? orchDef.systemPrompt + loadAgentKnowledge(orchDef)
        : "You are the Meta-Orchestrator. Analyze briefs and route them to appropriate boards.";

      // 4. Load geopolitics expert def
      const geoExperts = metaConfig.shared_experts.filter(e => e.active);
      let geoDef: AgentDef | null = null;
      if (geoExperts.length > 0) {
        const geoPath = resolve(cwd, geoExperts[0].path);
        if (existsSync(geoPath)) {
          geoDef = parseAgentFile(geoPath);
          if (geoDef) {
            geoDef.systemPrompt += loadAgentKnowledge(geoDef);
          }
        }
      }

      // 5. Initialize state
      boardStates = activeBoards.map(b => ({
        name: b.name,
        label: b.label,
        status: "pending" as const,
        elapsed: 0,
        lastWork: "",
      }));
      phase = "routing";
      orchestratorStatus = "running";
      geoStatus = "idle";
      routingPreview = "";
      updateWidget();

      if (onUpdate) onUpdate({
        content: [{ type: "text", text: "Orchestrator 路由分析中..." }],
        details: { status: "running", phase: "routing" },
      });

      // ── Phase A: Orchestrator Routing ──────────────────────────────────────

      const boardDescriptions = activeBoards
        .map(b => `- **${b.label}** (${b.name}): ${b.description}`)
        .join("\n");

      const routingPrompt =
        `分析以下 brief，為各委員會框架問題。\n\n` +
        `可用委員會：\n${boardDescriptions}\n\n` +
        `Brief：\n${briefText}\n\n` +
        `輸出：\n` +
        `1. 跨域視角框架（100-150字）：這個問題如何跨越投資、創意、科技三個域？\n` +
        `2. 給各委員會的具體問題（每個委員會 1-2 句聚焦問題）\n` +
        `3. 機器可讀路由塊（必須包含）：\n\n` +
        `## ROUTING\n` +
        `boards: <從以下選擇並用逗號分隔: ${activeBoards.map(b => b.name).join(", ")}>\n` +
        `geopolitics: required\n\n` +
        `全程使用繁體中文。`;

      const routingResult = await runSubagent(orchSystemPrompt, routingPrompt, orchModel, "none", (chunk) => {
        routingPreview += chunk;
        updateWidget();
      });

      orchestratorStatus = routingResult.exitCode === 0 ? "done" : "error";
      const routingMemo = routingResult.output;

      // Parse routing to determine which boards to call
      const routingMatch = routingMemo.match(/## ROUTING\s*\nboards:\s*([^\n]+)/i);
      let boardsToCall = activeBoards;
      if (routingMatch) {
        const requested = new Set(routingMatch[1].split(",").map(s => s.trim()).filter(Boolean));
        const filtered = activeBoards.filter(b => requested.has(b.name));
        if (filtered.length > 0) boardsToCall = filtered;
      }

      // Update board states to only include routed boards
      boardStates = boardsToCall.map(b => ({
        name: b.name,
        label: b.label,
        status: "pending" as const,
        elapsed: 0,
        lastWork: "",
      }));

      if (onUpdate) onUpdate({
        content: [{ type: "text", text: `路由完成。地緣政治分析師運行中...` }],
        details: { status: "running", phase: "geopolitics" },
      });

      // ── Phase B: Geopolitics Expert ────────────────────────────────────────

      phase = "geopolitics";
      geoStatus = "running";
      updateWidget();

      let geoBrief = "";
      if (geoDef) {
        const geoPrompt =
          `分析以下 brief 的地緣政治背景，為三個委員會（投資、創意音樂、AI科技）提供共享地緣政治快報。\n\n` +
          `Brief：\n${briefText}\n\n` +
          `Orchestrator 框架：\n${routingMemo.replace(/## ROUTING[\s\S]*$/, "").trim()}\n\n` +
          `依照你的輸出格式輸出完整地緣政治快報。250-350 字。`;

        const geoResult = await runSubagent(geoDef.systemPrompt, geoPrompt, geoDef.model, geoDef.tools);
        geoStatus = geoResult.exitCode === 0 ? "done" : "error";
        geoBrief = geoResult.output;
      } else {
        geoStatus = "done";
        geoBrief = "（地緣政治分析師未配置）";
      }

      if (onUpdate) onUpdate({
        content: [{ type: "text", text: `地緣政治分析完成。${boardsToCall.length} 個委員會 CEO 並行分析中...` }],
        details: { status: "running", phase: "delegating" },
      });

      // ── Phase C: Board CEOs in Parallel ────────────────────────────────────

      phase = "delegating";
      boardStates.forEach(s => { s.status = "pending"; });
      updateWidget();

      const boardResults = await Promise.all(
        boardsToCall.map((board, i) => {
          const state = boardStates[i];
          state.status = "running";
          updateWidget();

          const startTime = Date.now();
          const timer = setInterval(() => {
            state.elapsed = Date.now() - startTime;
            updateWidget();
          }, 1000);

          const ceoDef = parseAgentFile(resolve(cwd, board.ceo_path));
          if (!ceoDef) {
            clearInterval(timer);
            state.status = "error";
            state.lastWork = "CEO agent 檔案解析失敗";
            updateWidget();
            return Promise.resolve({ name: board.name, label: board.label, output: "Error: agent file parse failed", error: true });
          }

          // Load board knowledge base
          let boardKb = "";
          if (board.knowledge_base_path) {
            const kbPath = resolve(cwd, board.knowledge_base_path);
            if (existsSync(kbPath)) {
              boardKb = `\n\n## 委員會知識庫\n\n${readFileSync(kbPath, "utf-8")}`;
            }
          }

          const ceoSystemPrompt = ceoDef.systemPrompt + loadAgentKnowledge(ceoDef) + boardKb;

          const prompt =
            `你是 ${board.label} 的代表，正在 Meta-Orchestrator 跨域討論中發言。\n\n` +
            `Orchestrator 框架（跨域視角）：\n${routingMemo.replace(/## ROUTING[\s\S]*$/, "").trim()}\n\n` +
            `地緣政治背景（共享）：\n${geoBrief}\n\n` +
            `原始 Brief：\n${briefText}\n\n` +
            `請從 **${board.label}** 的專業視角回應，包含：\n` +
            `- 你的委員會對此問題的核心立場\n` +
            `- 地緣政治如何影響你的分析（引用具體內容）\n` +
            `- 給其他委員會的一個重要提醒（你的專業發現他們可能沒看到的）\n` +
            `- 具體建議行動（1-2 條）\n\n` +
            `200-280 字。全程繁體中文。`;

          return runSubagent(ceoSystemPrompt, prompt, ceoDef.model, "none", (chunk) => {
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
            return { name: board.name, label: board.label, output: result.output, error: result.exitCode !== 0 };
          }).catch(err => {
            clearInterval(timer);
            state.status = "error";
            state.lastWork = String(err);
            updateWidget();
            return { name: board.name, label: board.label, output: `Error: ${err}`, error: true };
          });
        })
      );

      // ── Phase D: Orchestrator Synthesis ────────────────────────────────────

      phase = "synthesizing";
      updateWidget();

      if (onUpdate) onUpdate({
        content: [{ type: "text", text: "各委員會回應完畢。Orchestrator 跨域整合中..." }],
        details: { status: "running", phase: "synthesizing" },
      });

      const validResults = boardResults.filter(r => !r.error);
      const allBoardOutputs = validResults
        .map(r => `### ${r.label}\n${r.output}`)
        .join("\n\n");

      const synthesisPrompt =
        `你是 Meta-Orchestrator。整合各委員會回應，輸出跨域戰略報告。\n\n` +
        `Brief：\n${briefText}\n\n` +
        `地緣政治背景：\n${geoBrief}\n\n` +
        `各委員會回應：\n${allBoardOutputs}\n\n` +
        `輸出以下章節：\n\n` +
        `## Final Decision\n` +
        `[跨域核心建議 — 整合三個委員會視角，3-4句，果斷]\n\n` +
        `## 跨域張力\n` +
        `[各委員會之間的主要分歧，以及如何取捨]\n\n` +
        `## 地緣政治對各域的差異化影響\n` +
        `[同一地緣政治因素如何在投資/創意/科技三域產生不同影響]\n\n` +
        `## Next Actions\n` +
        `[4-6 條具體可執行行動，標明負責域（投資/Drip/AI工具）]\n\n` +
        `## 分析說明\n` +
        `[跨域協同點：哪些因素讓三個委員會達成共識]\n\n` +
        `全程繁體中文。章節標題保持英文以便解析。`;

      const synthResult = await runSubagent(orchSystemPrompt, synthesisPrompt, orchModel, "none");
      const synthesis = synthResult.output;

      // ── Save Reports ────────────────────────────────────────────────────────

      const memosDir = join(cwd, ".pi", "meta-orchestrator", "memos");
      mkdirSync(memosDir, { recursive: true });

      const briefFirstLine = briefText.split("\n").find(l => l.trim()) || "orchestration";
      const slug = slugify(briefFirstLine.replace(/^#+\s*/, ""));
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const memoFilename = `${slug}-${timestamp}.md`;
      const memoPath = join(memosDir, memoFilename);

      const memoContent =
        `# Meta-Orchestrator 跨域戰略報告\n\n` +
        `**日期：** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Preset：** ${preset || activePreset || "custom"}\n` +
        `**委員會：** ${boardsToCall.map(b => b.label).join(", ")}\n\n` +
        `---\n\n## 分析 Brief\n\n${briefText}\n\n` +
        `---\n\n## Orchestrator 路由決策\n\n${routingMemo}\n\n` +
        `---\n\n## 地緣政治快報\n\n${geoBrief}\n\n` +
        `---\n\n## 各委員會回應\n\n${allBoardOutputs}\n\n` +
        `---\n\n${synthesis}`;

      writeFileSync(memoPath, memoContent, "utf-8");

      const htmlPath = memoPath.replace(/\.md$/, ".html");
      const htmlContent = generateHtmlReport({
        date: new Date().toISOString().slice(0, 10),
        preset: preset || activePreset || "custom",
        briefText,
        routingMemo,
        geoBrief,
        boardResults,
        synthesis,
      });
      writeFileSync(htmlPath, htmlContent, "utf-8");

      phase = "done";
      updateWidget();

      const truncated = synthesis.length > 6000
        ? synthesis.slice(0, 6000) + "\n\n... [截斷 — 請查看報告檔案]"
        : synthesis;

      return {
        content: [{
          type: "text",
          text: `報告已儲存：\n  📄 ${memoPath}\n  🌐 ${htmlPath}\n\n${truncated}`,
        }],
        details: {
          status: "done",
          memoPath,
          htmlPath,
          preset: preset || activePreset,
          boardCount: boardsToCall.length,
          synthesis,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : "";
      const briefPreview = (a.brief || "").slice(0, 50).replace(/\n/g, " ");
      const preview = briefPreview.length > 47 ? briefPreview.slice(0, 47) + "..." : briefPreview;
      return new Text(
        theme.fg("toolTitle", theme.bold("orchestrate")) +
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
        const phaseZh = phase === "routing" ? "路由分析中"
          : phase === "geopolitics" ? "地緣政治分析中"
            : phase === "delegating" ? "委員會並行中"
              : phase === "synthesizing" ? "跨域整合中" : phase;
        return new Text(
          theme.fg("accent", "● meta-orchestrator") + theme.fg("dim", ` ${phaseZh}...`),
          0, 0,
        );
      }
      if (details.status === "error") {
        return new Text(theme.fg("error", "✗ orchestrate 失敗"), 0, 0);
      }
      return new Text(
        theme.fg("success", "✓ meta-orchestrator") +
        theme.fg("dim", ` · ${details.boardCount} 個委員會 · `) +
        theme.fg("muted", details.memoPath || ""),
        0, 0,
      );
    },
  });

  // ── Commands ─────────────────────────────────────────────────────────────────

  pi.registerCommand("orchestrate-preset", {
    description: "Select board preset (full/strategic/tech-policy/investment-geo/creative/tech-creative)",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const presetNames = Object.keys(metaConfig.presets);
      if (presetNames.length === 0) {
        ctx.ui.notify("No presets defined in config.yaml", "warning");
        return;
      }
      const options = presetNames.map(name => {
        const boards = metaConfig.presets[name];
        return `${name} (${boards.join(", ")})`;
      });
      const choice = await ctx.ui.select("Select Orchestrator Preset", options);
      if (choice === undefined) return;
      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];
      const boards = metaConfig.presets[activePreset];
      ctx.ui.setStatus("meta-orchestrator", `Preset: ${activePreset} · ${boards.length} boards`);
      ctx.ui.notify(
        `Preset: ${activePreset}\nBoards: ${boards.map(displayName).join(", ")}`,
        "info",
      );
      updateWidget();
    },
  });

  pi.registerCommand("orchestrate-status", {
    description: "Show active boards and Meta-Orchestrator config",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const activeBoards = getActiveBoards();
      const presetLabel = activePreset || "config defaults";
      const experts = metaConfig.shared_experts.filter(e => e.active);
      const boardLines = activeBoards.map(b => `✓ ${b.label}  —  ${b.description}`);
      const expertLines = experts.map(e => `★ ${displayName(e.name)}`);
      ctx.ui.notify(
        `Meta-Orchestrator\nPreset: ${presetLabel}\n\n` +
        `Boards (${activeBoards.length}):\n${boardLines.join("\n")}\n\n` +
        `Shared Experts:\n${expertLines.join("\n") || "none"}\n\n` +
        `/orchestrate-preset    Switch preset\n` +
        `/orchestrate-status    Show this panel`,
        "info",
      );
    },
  });

  // ── Session Start ─────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);

    if (widgetCtx) widgetCtx.ui.setWidget("meta-orchestrator", undefined);
    ctx.ui.setWidget("meta-orchestrator", undefined);
    widgetCtx = ctx;

    phase = "idle";
    boardStates = [];
    activePreset = null;

    loadConfig(ctx.cwd);

    const active = getActiveBoards();
    ctx.ui.setStatus("meta-orchestrator", `Meta-Orchestrator · ${active.length} boards`);
    ctx.ui.notify(
      `Meta-Orchestrator\n` +
      `${active.length} boards · Geopolitics Expert shared\n\n` +
      `/orchestrate-preset    Select preset\n` +
      `/orchestrate-status    Show boards`,
      "info",
    );

    updateWidget();

    ctx.ui.setFooter((_tui: any, theme: any, _footerData: any) => ({
      dispose: () => { },
      invalidate() { },
      render(width: number): string[] {
        const presetLabel = activePreset || "default";
        const boardCount = getActiveBoards().length;
        const left =
          theme.fg("dim", ` meta-orchestrator`) +
          theme.fg("muted", " · ") +
          theme.fg("accent", presetLabel) +
          theme.fg("muted", " · ") +
          theme.fg("dim", `${boardCount} boards`);
        const right = theme.fg("dim", ` `);
        const pad = " ".repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));
        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });
}
