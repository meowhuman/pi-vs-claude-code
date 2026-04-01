/**
 * Investment Adviser Board — 多代理投資顧問委員會系統
 *
 * 7位專業委員並行分析投資標的，CEO 整合後輸出具體交易建議（含 HTML 報告）。
 * 支援兩種交易風格：長期宏觀部位 和 搖擺交易操作。
 *
 * Config: .pi/investment-adviser-board/config.yaml
 * Agents: .pi/investment-adviser-board/agents/<name>.md
 * Memos:  .pi/investment-adviser-board/memos/<slug>-<timestamp>.md
 *
 * Commands:
 *   /board-preset  — 選擇委員會 preset（full/macro-focus/swing-trade/quick）
 *   /board-status  — 顯示活躍委員
 *
 * Tools (Mode A — 全自動):
 *   board_begin    — 提交 brief → AI 全自動運行 → 輸出 HTML 報告
 *
 * Tools (Mode B — 互動討論):
 *   board_discuss  — 開始互動討論模式，用戶作為「人類委員」坐入委員會
 *   board_next     — 讓下一位或指定委員發言（可帶入用戶的背景/回應）
 *   board_report   — 結束討論，生成最終報告（輸出 -discussion 後綴的 .md 和 .html）
 *
 * Usage: pi -e extensions/investment-adviser-board.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync } from "fs";
import { join, resolve, dirname } from "path";
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

// ── YAML Parser ───────────────────────────────────────────────────────────────

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
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) {
        const presetName = m[1].trim();
        const members = m[2].split(",").map(s => s.trim()).filter(Boolean);
        config.presets[presetName] = members;
      }
      continue;
    }
  }

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

// ── Personal Knowledge Loader ─────────────────────────────────────────────────

function loadMemberKnowledge(member: MemberDef): string {
  if (!existsSync(member.knowledgePath)) return "";
  const content = readFileSync(member.knowledgePath, "utf-8").trim();
  if (!content) return "";
  return `\n\n## ${member.name} 個人知識庫\n\n${content}`;
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

// ── Format Discussion History ─────────────────────────────────────────────────

function formatHistory(history: Array<{ speaker: string; content: string; timestamp: number }>): string {
  if (history.length === 0) return "（尚無討論記錄）";
  return history.map((entry, i) => {
    const speakerLabel = entry.speaker === "user"
      ? "👤 人類委員（Human Board Member）"
      : entry.speaker === "ceo"
        ? "🏛 CEO（Board Chair）"
        : `📊 ${displayName(entry.speaker)}`;
    return `[${i + 1}] ${speakerLabel}\n${entry.content}`;
  }).join("\n\n---\n\n");
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
      resolve({
        output: output || (stderr ? `[stderr] ${stderr}` : ""),
        exitCode: code ?? 1,
        elapsed: Date.now() - startTime,
      });
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

  const finalDecision = escapeHtml(extractMemoSection(memo, "Final Decision|最終建議|最终建议"));
  const dissent = escapeHtml(extractMemoSection(memo, "Dissent.*Tensions|Dissent|分歧|張力|张力"));
  const tradeoffs = extractMemoSection(memo, "Trade.offs|Trade-offs|權衡|取捨|风险機會权衡");
  const nextActionsRaw = extractMemoSection(memo, "Next Actions|具體操作步驟|下一步行動|下一步|後續行動");
  const actions = parseActionsList(nextActionsRaw);

  // 宏觀建議 & 搖擺交易建議
  const macroSection = escapeHtml(extractMemoSection(memo, "長期宏觀部位|Macro.*Long.term|宏觀建議"));
  const swingSection = escapeHtml(extractMemoSection(memo, "搖擺交易|Swing.*Trade|搖擺交易操作"));
  const riskSection = escapeHtml(extractMemoSection(memo, "風險提示|Risk.*Warning|整體風險|風險評估"));

  const briefHtml = briefText.split("\n").map(line => {
    if (line.startsWith("## ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^##\s*/, ""))}</div>`;
    if (line.startsWith("# ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^#\s*/, ""))}</div>`;
    if (line.trim() === "") return `<div class="brief-spacer"></div>`;
    return `<div class="brief-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  const stanceCards = boardResults.filter(r => !r.error).map(r => {
    const parsed = parseStanceCard(r.stance);
    const name = displayName(r.name);
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

  const gainMatch = tradeoffs.match(/(?:得到|機會|Gain|得)[：:\n]?([\s\S]*?)(?=(?:放棄|Lose|失去|風險|損失)[：:\n]|$)/i);
  const loseMatch = tradeoffs.match(/(?:放棄|Lose|失去|風險|損失)[：:\n]?([\s\S]*?)$/i);
  const gainItems = gainMatch ? parseActionsList(gainMatch[1]) : [];
  const loseItems = loseMatch ? parseActionsList(loseMatch[1]) : [];
  const tradeoffHtml = (gainItems.length > 0 || loseItems.length > 0)
    ? `<div class="tradeoff-grid">
        <div class="gain">
          <div class="tradeoff-label">機會 / 上行空間</div>
          <ul>${gainItems.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
        </div>
        <div class="lose">
          <div class="tradeoff-label">風險 / 下行風險</div>
          <ul>${loseItems.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
        </div>
      </div>`
    : `<div class="dissent-block">${escapeHtml(tradeoffs)}</div>`;

  const actionItems = actions.map(a => `<li>${escapeHtml(a)}</li>`).join("\n");
  const memberTags = memberNames.map(n =>
    `<span class="dissent-tag">${escapeHtml(displayName(n))}</span>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>投資顧問委員會報告</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0d1117; --card-bg: #161b22; --accent: #d4a017; --secondary: #58a6ff;
      --text: #e6edf3; --muted: #8b949e; --border: rgba(212,160,23,0.2);
      --border-accent: #d4a017; --success: #3fb950; --danger: #f85149;
      --divider: rgba(255,255,255,0.06); --navy: #1c2333;
    }
    body { background: var(--bg); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; font-size: 15px; line-height: 1.7; min-height: 100vh; }
    .container { max-width: 960px; margin: 0 auto; padding: 0 2rem; }
    header { text-align: center; padding: 4rem 2rem 2.5rem; border-bottom: 1px solid var(--divider); background: linear-gradient(180deg, rgba(212,160,23,0.05) 0%, transparent 100%); }
    .logo { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.35em; color: var(--accent); text-transform: uppercase; margin-bottom: 0.6rem; }
    .title { font-size: 1.9rem; font-weight: 800; color: var(--text); margin-bottom: 0.4rem; }
    .subtitle { font-size: 0.82rem; font-weight: 500; letter-spacing: 0.15em; text-transform: uppercase; color: var(--muted); margin-bottom: 1.2rem; }
    .meta { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; justify-content: center; gap: 0.5rem; flex-wrap: wrap; }
    .dot { opacity: 0.4; }
    .meta-badge { background: rgba(212,160,23,0.12); color: var(--accent); padding: 0.15rem 0.7rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em; }
    section { padding: 2.5rem 0; border-bottom: 1px solid var(--divider); }
    section:last-of-type { border-bottom: none; }
    .section-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--accent); margin-bottom: 1.2rem; }
    .brief-section { background: rgba(88,166,255,0.03); padding: 2.5rem 2rem; }
    .brief-heading { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin: 1rem 0 0.4rem; }
    .brief-heading:first-child { margin-top: 0; }
    .brief-line { color: var(--muted); font-size: 0.9rem; line-height: 1.8; max-width: 700px; }
    .brief-spacer { height: 0.5rem; }
    .ceo-framing { margin-top: 1rem; padding: 1rem 1.2rem; border-left: 3px solid rgba(212,160,23,0.4); background: rgba(212,160,23,0.04); border-radius: 0 6px 6px 0; font-size: 0.88rem; color: var(--muted); line-height: 1.8; }
    .ceo-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin-bottom: 0.5rem; }
    .decision-section { background: rgba(212,160,23,0.04); padding: 2.5rem 2rem; }
    .decision-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-bottom: 1.2rem; }
    @media (max-width: 600px) { .decision-grid { grid-template-columns: 1fr; } }
    .decision-card { border-radius: 10px; padding: 1.3rem 1.5rem; border: 1px solid var(--border); }
    .decision-card.macro { background: rgba(212,160,23,0.06); border-top: 3px solid var(--accent); }
    .decision-card.swing { background: rgba(63,185,80,0.05); border-top: 3px solid var(--success); }
    .decision-card-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 0.8rem; }
    .decision-card.macro .decision-card-label { color: var(--accent); }
    .decision-card.swing .decision-card-label { color: var(--success); }
    .decision-text { font-size: 0.92rem; font-weight: 500; color: var(--text); line-height: 1.75; white-space: pre-wrap; }
    .decision-block { border-left: 4px solid var(--accent); padding: 1.2rem 1.5rem; background: rgba(212,160,23,0.05); border-radius: 0 8px 8px 0; }
    .decision-main { font-size: 1.0rem; font-weight: 600; color: var(--text); line-height: 1.75; }
    .risk-block { margin-top: 1rem; padding: 1rem 1.2rem; border-left: 3px solid var(--danger); background: rgba(248,81,73,0.05); border-radius: 0 6px 6px 0; font-size: 0.88rem; color: var(--muted); line-height: 1.8; }
    .risk-label { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--danger); font-weight: 600; margin-bottom: 0.5rem; }
    .stances-section { padding: 2.5rem 2rem; }
    .stances-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 1rem; }
    @media (max-width: 700px) { .stances-grid { grid-template-columns: repeat(2,1fr); } }
    @media (max-width: 420px) { .stances-grid { grid-template-columns: 1fr; } }
    .stance-card { background: var(--card-bg); border: 1px solid var(--border); border-top: 3px solid var(--border-accent); border-radius: 8px; padding: 1.2rem; }
    .card-header { font-size: 0.88rem; font-weight: 700; color: var(--accent); margin-bottom: 1rem; letter-spacing: 0.05em; }
    .micro-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--secondary); margin-top: 0.8rem; margin-bottom: 0.3rem; }
    .micro-content { font-size: 0.82rem; color: var(--text); line-height: 1.65; }
    .dissent-section, .tradeoffs-section, .actions-section { padding: 2.5rem 2rem; }
    .dissent-block { background: rgba(212,160,23,0.04); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem 1.4rem; font-size: 0.9rem; line-height: 1.75; color: var(--text); }
    .dissent-members { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
    .dissent-tag { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; background: rgba(212,160,23,0.12); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 4px; }
    .tradeoff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    @media (max-width: 500px) { .tradeoff-grid { grid-template-columns: 1fr; } }
    .gain, .lose { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem 1.4rem; }
    .gain { border-top: 3px solid var(--success); }
    .lose { border-top: 3px solid var(--danger); }
    .tradeoff-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.8rem; }
    .gain .tradeoff-label { color: var(--success); }
    .lose .tradeoff-label { color: var(--danger); }
    .gain ul, .lose ul { list-style: none; padding: 0; }
    .gain ul li, .lose ul li { font-size: 0.88rem; color: var(--text); line-height: 1.6; padding: 0.3rem 0; display: flex; align-items: flex-start; gap: 0.6rem; }
    .gain ul li::before { content: '+'; color: var(--success); font-weight: 700; flex-shrink: 0; }
    .lose ul li::before { content: '−'; color: var(--danger); font-weight: 700; flex-shrink: 0; }
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
    <div class="logo">Investment Adviser Board</div>
    <div class="title">投資顧問委員會報告</div>
    <div class="subtitle">Multi-Agent Investment Analysis</div>
    <div class="meta">
      <span>${escapeHtml(date)}</span><span class="dot">·</span>
      <span class="meta-badge">${escapeHtml(preset)}</span><span class="dot">·</span>
      <span>${memberNames.length} 位委員</span><span class="dot">·</span>
      <span>CEO: openai-codex/gpt-5.2-codex</span>
    </div>
  </header>

  <section class="brief-section">
    <div class="section-label">分析簡報</div>
    <div class="brief-body">${briefHtml}</div>
    <div class="ceo-framing">
      <div class="ceo-label">CEO 框架</div>
      ${escapeHtml(ceoFrame)}
    </div>
  </section>

  <section class="decision-section">
    <div class="section-label">最終建議</div>
    ${(macroSection || swingSection) ? `
    <div class="decision-grid">
      ${macroSection ? `<div class="decision-card macro">
        <div class="decision-card-label">長期宏觀部位</div>
        <div class="decision-text">${macroSection}</div>
      </div>` : ""}
      ${swingSection ? `<div class="decision-card swing">
        <div class="decision-card-label">搖擺交易操作</div>
        <div class="decision-text">${swingSection}</div>
      </div>` : ""}
    </div>` : ""}
    <div class="decision-block">
      <p class="decision-main">${finalDecision || escapeHtml(memo.split("\n").find(l => l.trim() && !l.startsWith("#")) || "")}</p>
    </div>
    ${riskSection ? `<div class="risk-block">
      <div class="risk-label">風險提示</div>
      ${riskSection}
    </div>` : ""}
  </section>

  <section class="stances-section">
    <div class="section-label">各委員立場</div>
    <div class="stances-grid">${stanceCards}</div>
  </section>

  ${dissent ? `<section class="dissent-section">
    <div class="section-label">分歧與張力</div>
    <div class="dissent-block">
      <div class="dissent-members">${memberTags}</div>
      ${dissent}
    </div>
  </section>` : ""}

  <section class="tradeoffs-section">
    <div class="section-label">風險 / 機會權衡</div>
    ${tradeoffHtml}
  </section>

  ${actionItems ? `<section class="actions-section">
    <div class="section-label">具體操作步驟</div>
    <ol class="actions-list">${actionItems}</ol>
  </section>` : ""}

  <footer>
    <span>本報告由投資顧問委員會多代理系統自動生成，僅供參考，不構成投資建議。</span>
    <span>Investment Adviser Board — Generated by Pi Multi-Agent System</span>
  </footer>
</body>
</html>`;
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: any;
  let boardConfig: BoardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
  let activePreset: string | null = null;
  let memberStates: MemberState[] = [];
  let boardPhase: "idle" | "framing" | "deliberating" | "synthesizing" | "done" = "idle";
  let ceoFramingText = "";
  let cwd = "";

  // ── Discussion Mode State ──────────────────────────────────────────────────

  interface DiscussionEntry {
    speaker: string; // "ceo" | "user" | member name
    content: string;
    timestamp: number;
  }

  interface DiscussionSession {
    active: boolean;
    brief: string;
    ceoFrame: string;
    history: DiscussionEntry[];
    activeMembers: BoardMemberConfig[];
    memberDefs: Map<string, MemberDef>;
    speakOrder: string[]; // 所有非 CEO 委員名稱列表（依序）
    nextSpeakerIdx: number;
    ceoModel: string;
    knowledgeBase: string;
    preset: string;
  }

  let discussionSession: DiscussionSession | null = null;

  // ── Config Loader ──────────────────────────────────────────────────────────

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "investment-adviser-board", "config.yaml");
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

    widgetCtx.ui.setWidget("investment-adviser-board", (_tui: any, theme: any) => {
      const text = new Text("", 0, 1);

      return {
        render(width: number): string[] {
          // 互動討論模式 widget
          if (discussionSession?.active) {
            const sess = discussionSession;
            const spokenNames = sess.history
              .filter(e => e.speaker !== "user" && e.speaker !== "ceo")
              .map(e => displayName(e.speaker));
            const uniqueSpoken = [...new Set(spokenNames)];
            const rounds = sess.history.length;
            const nextIdx = sess.nextSpeakerIdx;
            const remaining = sess.speakOrder.length - nextIdx;

            const lines: string[] = [
              theme.fg("accent", "● 互動討論模式"),
              "",
              theme.fg("muted", `對話輪次：${rounds}  |  已發言：${uniqueSpoken.length} 位  |  待發言：${remaining} 位`),
            ];
            if (uniqueSpoken.length > 0) {
              lines.push(theme.fg("dim", `已發言：${uniqueSpoken.join(", ")}`));
            }
            if (nextIdx < sess.speakOrder.length) {
              lines.push(theme.fg("accent", `下一位：${displayName(sess.speakOrder[nextIdx])}`));
            } else {
              lines.push(theme.fg("success", "所有委員已發言，可 board_report 生成報告"));
            }

            text.setText(lines.join("\n"));
            return text.render(width);
          }

          if (boardPhase === "idle" || members.length === 0) {
            text.setText(theme.fg("dim", "Investment Adviser Board idle. Use board_begin to start analysis."));
            return text.render(width);
          }

          const phaseLabel = boardPhase === "framing" ? "● CEO 框架分析中..."
            : boardPhase === "deliberating" ? "● 委員並行分析中..."
              : boardPhase === "synthesizing" ? "● CEO 整合報告中..."
                : boardPhase === "done" ? "✓ 分析完成" : "";
          const headerLine = theme.fg("accent", phaseLabel);

          if (boardPhase === "framing" && ceoFramingText) {
            const preview = ceoFramingText.split("\n").filter((l: string) => l.trim()).slice(-3).join(" · ");
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

    const memberSystemPrompt = memberDef.systemPrompt + loadMemberKnowledge(memberDef) + knowledgeBase;

    const prompt =
      `CEO 已框架此次投資分析：\n\n${ceoFrame}\n\n` +
      `原始分析 Brief：\n${briefText}\n\n` +
      `請以 ${displayName(memberConfig.name)} 的角色給出你的立場分析，包含：\n` +
      `- 你的立場（明確的方向性判斷）\n` +
      `- 關鍵論點（支撐立場的核心依據）\n` +
      `- 主要顧慮（最大的反向風險）\n` +
      `- 你想問其他委員的一個問題\n\n` +
      `請使用你分配的工具進行實際分析。分析長度 200-300 字。\n\n` +
      `重要：全程使用繁體中文回應。技術指標名稱、股票代碼可保留英文。`;

    return runSubagent(memberSystemPrompt, prompt, memberDef.model, memberDef.tools, (chunk) => {
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
      "召集投資顧問委員會進行分析。提供分析 brief（內聯 markdown 或 .md 檔案路徑）。" +
      "CEO 框架問題後，所有委員並行分析，最後 CEO 整合輸出交易建議報告（含 HTML）。",
    parameters: Type.Object({
      brief: Type.String({
        description: "分析 brief 文字（markdown）或 .md 檔案路徑，應包含分析標的和背景資訊",
      }),
      preset: Type.Optional(Type.String({
        description: "覆蓋委員會 preset（full/macro-focus/swing-trade/quick）",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };

      // 0. Load shared knowledge base
      const kbPath = join(cwd, ".pi", "investment-adviser-board", "knowledge-base.md");
      const knowledgeBase = existsSync(kbPath)
        ? `\n\n## 投資顧問委員會知識庫（共享背景資料）\n\n${readFileSync(kbPath, "utf-8")}`
        : "";

      // 1. Resolve brief text
      let briefText = brief;
      if (brief.endsWith(".md")) {
        const briefPath = resolve(cwd, brief);
        if (existsSync(briefPath)) {
          briefText = readFileSync(briefPath, "utf-8");
        } else {
          return {
            content: [{ type: "text", text: `Brief 檔案未找到：${briefPath}` }],
            details: { status: "error" },
          };
        }
      }

      // 2. Resolve active members
      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: "text", text: "沒有活躍的委員。請檢查 config.yaml 或選擇一個 preset。" }],
          details: { status: "error" },
        };
      }

      // Validate all member paths exist before starting
      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return {
          content: [{ type: "text", text: `缺少 agent 檔案：\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }],
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
          content: [{ type: "text", text: `召集 ${activeMembers.length} 位委員開始分析...` }],
          details: { status: "running", phase: "framing" },
        });
      }

      // 4. CEO Framing (sequential, with streaming to widget)
      ceoFramingText = "";

      // Find CEO def to get its model
      const ceoDef = memberDefs.get("ceo");
      const ceoModel = ceoDef?.model || "openai-codex/gpt-5.2-codex";

      const ceoSystemPrompt =
        `你是投資顧問委員會（Investment Adviser Board）的主席（CEO）。` +
        `你是一位中立的 AI 協調者，負責框架投資問題並整合委員分析。` +
        knowledgeBase;

      const framingPrompt =
        `閱讀以下投資分析 brief，為委員會框架此次分析。識別：\n` +
        `1. 分析標的（股票/資產代碼）\n` +
        `2. 核心問題和分析框架\n` +
        `3. 各委員應聚焦的面向\n` +
        `4. 關鍵問題：長期宏觀部位 vs. 搖擺交易，哪個更適合當前情況？\n\n` +
        `Brief：\n${briefText}\n\n` +
        `輸出框架分析 200-300 字，語氣直接清晰。\n\n` +
        `重要：全程使用繁體中文。技術術語、股票代碼可保留英文。`;

      const framingResult = await runSubagent(ceoSystemPrompt, framingPrompt, ceoModel, "none", (chunk) => {
        ceoFramingText += chunk;
        updateWidget();
      });
      const ceoFrame = framingResult.output;

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `CEO 框架完成。委員並行分析中...` }],
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
            memberStates[i].lastWork = "Agent 檔案未找到";
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
          content: [{ type: "text", text: `所有委員分析完畢。CEO 整合最終建議報告中...` }],
          details: { status: "running", phase: "synthesizing" },
        });
      }

      const validResults = boardResults.filter(r => !r.error);
      const allStances = validResults
        .map(r => `### ${displayName(r.name)}\n${r.stance}`)
        .join("\n\n");
      const errorNote = boardResults.length > validResults.length
        ? `\n\n（注意：${boardResults.length - validResults.length} 位委員回應失敗，未納入此次綜合。）`
        : "";

      const synthesisPrompt =
        `你是投資顧問委員會的主席（CEO）。\n\n` +
        `根據原始 brief 和所有委員的分析，撰寫最終投資建議報告。\n\n` +
        `Brief：\n${briefText}\n\n` +
        `CEO 框架：\n${ceoFrame}\n\n` +
        `委員分析：\n${allStances}\n\n` +
        `撰寫結構化報告，包含以下章節：\n` +
        `## Final Decision\n` +
        `[整體市場觀點和核心建議 — 要果斷]\n\n` +
        `## 長期宏觀部位\n` +
        `[方向、進場區間、目標價、止損位、倉位比例]\n\n` +
        `## 搖擺交易操作\n` +
        `[進場點、出場目標、止損位、持倉時間預估]\n\n` +
        `## 風險提示\n` +
        `[整體風險等級和主要風險事件]\n\n` +
        `## Board Member Stances\n` +
        `[每位委員一段：立場 + 關鍵論點 + 主要顧慮]\n\n` +
        `## Dissent & Tensions\n` +
        `[委員之間的重大分歧和未解決的張力]\n\n` +
        `## Trade-offs\n` +
        `[機會（得到） vs. 風險（失去）]\n\n` +
        `## Next Actions\n` +
        `[3-5 個具體可執行的操作步驟]\n\n` +
        `## Deliberation Summary\n` +
        `[討論如何展開，什麼因素影響了最終判斷]\n\n` +
        `重要：全程使用繁體中文。章節標題保持英文以便解析。技術術語可保留英文。${errorNote}`;

      const synthResult = await runSubagent(ceoSystemPrompt, synthesisPrompt, ceoModel, "none");
      const memo = synthResult.output;

      // 7. Save memo
      const memosDir = join(cwd, ".pi", "investment-adviser-board", "memos");
      mkdirSync(memosDir, { recursive: true });

      const briefFirstLine = briefText.split("\n").find(l => l.trim()) || "investment-analysis";
      const slug = slugify(briefFirstLine.replace(/^#+\s*/, ""));
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const memoFilename = `${slug}-${timestamp}.md`;
      const memoPath = join(memosDir, memoFilename);

      const memoContent =
        `# 投資顧問委員會報告\n\n` +
        `**日期：** ${new Date().toISOString().slice(0, 10)}\n` +
        `**Preset：** ${preset || activePreset || "custom"}\n` +
        `**委員：** ${activeMembers.map(m => displayName(m.name)).join(", ")}\n` +
        `**分析時間：** ${boardConfig.meeting.discussion_time_minutes} 分鐘\n\n` +
        `---\n\n` +
        `## 分析 Brief\n\n${briefText}\n\n` +
        `---\n\n` +
        `## CEO 框架\n\n${ceoFrame}\n\n` +
        `---\n\n` +
        `## 各委員立場\n\n${allStances}\n\n` +
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

      const truncated = memo.length > 8000 ? memo.slice(0, 8000) + "\n\n... [截斷 — 請查看報告檔案]" : memo;

      return {
        content: [{ type: "text", text: `報告已儲存：\n  📄 ${memoPath}\n  🌐 ${htmlPath}\n\n${truncated}` }],
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
        const phaseZh = phase === "framing" ? "CEO 框架中"
          : phase === "deliberating" ? "委員分析中"
            : phase === "synthesizing" ? "整合報告中" : phase;
        return new Text(
          theme.fg("accent", `● investment-adviser-board`) +
          theme.fg("dim", ` ${phaseZh}...`),
          0, 0,
        );
      }

      if (details.status === "error") {
        return new Text(theme.fg("error", `✗ board_begin 失敗`), 0, 0);
      }

      const header =
        theme.fg("success", `✓ investment-adviser-board`) +
        theme.fg("dim", ` · ${details.memberCount} 位委員 · `) +
        theme.fg("muted", details.memoPath || "");

      if (options.expanded && details.memo) {
        const output = details.memo.length > 4000
          ? details.memo.slice(0, 4000) + "\n... [截斷]"
          : details.memo;
        return new Text(header + "\n" + theme.fg("muted", output), 0, 0);
      }

      return new Text(header, 0, 0);
    },
  });

  // ── board_discuss Tool ─────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_discuss",
    label: "Board Discuss",
    description:
      "開始互動討論模式（Mode B）。用戶作為「人類委員」坐入委員會。" +
      "CEO 框架問題後，第一位委員發言，之後用 board_next 輪流發言，最後用 board_report 生成報告。",
    parameters: Type.Object({
      brief: Type.String({
        description: "分析 brief 文字（markdown）或 .md 檔案路徑",
      }),
      preset: Type.Optional(Type.String({
        description: "覆蓋委員會 preset（full/macro-focus/swing-trade/quick）",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };

      // 0. Load knowledge base
      const kbPath = join(cwd, ".pi", "investment-adviser-board", "knowledge-base.md");
      const knowledgeBase = existsSync(kbPath)
        ? `\n\n## 投資顧問委員會知識庫（共享背景資料）\n\n${readFileSync(kbPath, "utf-8")}`
        : "";

      // 1. Resolve brief text
      let briefText = brief;
      if (brief.endsWith(".md")) {
        const briefPath = resolve(cwd, brief);
        if (existsSync(briefPath)) {
          briefText = readFileSync(briefPath, "utf-8");
        } else {
          return {
            content: [{ type: "text", text: `Brief 檔案未找到：${briefPath}` }],
            details: { status: "error" },
          };
        }
      }

      // 2. Resolve active members
      const activeMembers = getActiveMembers(preset);
      if (activeMembers.length === 0) {
        return {
          content: [{ type: "text", text: "沒有活躍的委員。請檢查 config.yaml 或選擇一個 preset。" }],
          details: { status: "error" },
        };
      }

      // Validate paths
      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return {
          content: [{ type: "text", text: `缺少 agent 檔案：\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }],
          details: { status: "error" },
        };
      }

      // Load member definitions
      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const def = parseMemberFile(resolve(cwd, member.path));
        if (def) memberDefs.set(member.name, def);
      }

      // Find CEO model
      const ceoDef = memberDefs.get("ceo");
      const ceoModel = ceoDef?.model || "openai-codex/gpt-5.2-codex";

      // 3. CEO Framing
      boardPhase = "framing";
      ceoFramingText = "";
      memberStates = [];
      updateWidget();

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `🏛 CEO 框架問題中...` }],
          details: { status: "running", phase: "framing" },
        });
      }

      const ceoSystemPrompt =
        `你是投資顧問委員會（Investment Adviser Board）的主席（CEO）。` +
        `你是一位中立的 AI 協調者，負責框架投資問題並整合委員分析。` +
        knowledgeBase;

      const framingPrompt =
        `閱讀以下投資分析 brief，為委員會框架此次分析。識別：\n` +
        `1. 分析標的（股票/資產代碼）\n` +
        `2. 核心問題和分析框架\n` +
        `3. 各委員應聚焦的面向\n` +
        `4. 關鍵問題：長期宏觀部位 vs. 搖擺交易，哪個更適合當前情況？\n\n` +
        `注意：此次為互動討論模式，人類委員也將參與討論。請框架時留下開放問題供討論。\n\n` +
        `Brief：\n${briefText}\n\n` +
        `輸出框架分析 200-300 字，語氣直接清晰。\n\n` +
        `重要：全程使用繁體中文。技術術語、股票代碼可保留英文。`;

      const framingResult = await runSubagent(ceoSystemPrompt, framingPrompt, ceoModel, "none", (chunk) => {
        ceoFramingText += chunk;
        updateWidget();
      });
      const ceoFrame = framingResult.output;

      // 4. 選出第一位發言委員（非 CEO）
      const nonCeoMembers = activeMembers.filter(m => m.name !== "ceo");
      const speakOrder = nonCeoMembers.map(m => m.name);

      // 5. 第一位委員發言（通常從第一個非 CEO 開始）
      const firstMemberName = speakOrder[0];
      const firstMember = nonCeoMembers[0];
      const firstDef = memberDefs.get(firstMemberName);

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `📊 ${displayName(firstMemberName)} 發言中...` }],
          details: { status: "running", phase: "discussing" },
        });
      }

      let firstMemberOutput = `（${displayName(firstMemberName)} agent 未找到）`;
      if (firstDef && firstMember) {
        const firstPrompt =
          `CEO 框架：\n${ceoFrame}\n\n` +
          `原始 Brief：\n${briefText}\n\n` +
          `現在是互動討論模式的第一輪發言。輪到你（${displayName(firstMemberName)}）率先發言。\n` +
          `請基於 CEO 框架和 Brief，給出你的初步分析。\n` +
          `格式：立場 → 關鍵論點 → 主要顧慮 → 你想問其他委員或人類委員的一個問題\n\n` +
          `重要：全程繁體中文。200-300 字。`;

        const result = await runSubagent(
          firstDef.systemPrompt + loadMemberKnowledge(firstDef) + knowledgeBase,
          firstPrompt,
          firstDef.model,
          firstDef.tools,
        );
        firstMemberOutput = result.output || `（${displayName(firstMemberName)} 無輸出，exit ${result.exitCode}）`;
      }

      // 6. 初始化 discussionSession
      const history: DiscussionEntry[] = [
        { speaker: "ceo", content: ceoFrame, timestamp: Date.now() },
        { speaker: firstMemberName, content: firstMemberOutput, timestamp: Date.now() },
      ];

      discussionSession = {
        active: true,
        brief: briefText,
        ceoFrame,
        history,
        activeMembers,
        memberDefs,
        speakOrder,
        nextSpeakerIdx: 1, // 第一位已說，從 index 1 開始
        ceoModel,
        knowledgeBase,
        preset: preset || activePreset || "custom",
      };

      boardPhase = "idle";
      updateWidget();

      const remainingNames = speakOrder.slice(1).map(displayName).join(", ");
      const output =
        `## 🏛 投資顧問委員會 — 互動討論模式已開始\n\n` +
        `### CEO 框架\n\n${ceoFrame}\n\n` +
        `---\n\n` +
        `### 📊 ${displayName(firstMemberName)}（第一位發言）\n\n${firstMemberOutput}\n\n` +
        `---\n\n` +
        `**你可以：**\n` +
        `- 直接回應上述觀點，然後用 \`board_next\` 繼續（在 \`context\` 參數填入你的回應）\n` +
        `- 用 \`board_next member="委員名稱"\` 指定下一位發言\n` +
        `- 用 \`board_report\` 結束討論並生成最終報告\n\n` +
        `待發言委員：${remainingNames || "（全部已發言）"}`;

      return {
        content: [{ type: "text", text: output }],
        details: {
          status: "discussing",
          ceoFrame,
          firstSpeaker: firstMemberName,
          firstOutput: firstMemberOutput,
          speakOrder,
          remainingCount: speakOrder.length - 1,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const presetLabel = a.preset ? ` [${a.preset}]` : "";
      const briefPreview = (a.brief || "").slice(0, 50).replace(/\n/g, " ");
      const preview = briefPreview.length > 47 ? briefPreview.slice(0, 47) + "..." : briefPreview;
      return new Text(
        theme.fg("toolTitle", theme.bold("board_discuss")) +
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
        const phaseZh = phase === "framing" ? "CEO 框架中" : phase === "discussing" ? "委員發言中" : phase;
        return new Text(
          theme.fg("accent", `● board_discuss`) + theme.fg("dim", ` ${phaseZh}...`),
          0, 0,
        );
      }
      if (details.status === "error") {
        return new Text(theme.fg("error", `✗ board_discuss 失敗`), 0, 0);
      }
      return new Text(
        theme.fg("success", `✓ board_discuss 互動討論已開始`) +
        theme.fg("dim", ` · 首位：${displayName(details.firstSpeaker || "")} · 待發言：${details.remainingCount || 0} 位`),
        0, 0,
      );
    },
  });

  // ── board_next Tool ────────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_next",
    label: "Board Next",
    description:
      "在互動討論模式中，讓下一位或指定委員發言。" +
      "需先呼叫 board_discuss 開始討論。",
    parameters: Type.Object({
      member: Type.Optional(Type.String({
        description: "指定委員名稱（如 macro-strategist、risk-officer 等）。不填則自動選下一位未發言的委員。",
      })),
      context: Type.Optional(Type.String({
        description:
          "你對上一位委員發言的回應或補充觀點。這會被自動記錄到討論歷史（標記為人類委員）並轉達給接下來的委員。",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { member, context } = params as { member?: string; context?: string };

      if (!discussionSession?.active) {
        return {
          content: [{ type: "text", text: "目前沒有進行中的互動討論。請先呼叫 board_discuss 開始討論。" }],
          details: { status: "error" },
        };
      }

      const sess = discussionSession;

      // 1. 如果用戶提供了 context，先記錄為人類委員發言
      if (context?.trim()) {
        sess.history.push({
          speaker: "user",
          content: context.trim(),
          timestamp: Date.now(),
        });
        updateWidget();
      }

      // 2. 決定由哪位委員發言
      let targetName: string | undefined;
      if (member) {
        // 支援部分匹配（如輸入 "macro" 能匹配 "macro-strategist"）
        targetName = sess.speakOrder.find(n =>
          n === member || n.includes(member) || displayName(n).toLowerCase().includes(member.toLowerCase())
        );
        if (!targetName) {
          return {
            content: [{ type: "text", text: `找不到委員「${member}」。可用委員：${sess.speakOrder.map(displayName).join(", ")}` }],
            details: { status: "error" },
          };
        }
      } else {
        // 自動選下一位未發言的委員
        if (sess.nextSpeakerIdx >= sess.speakOrder.length) {
          return {
            content: [{
              type: "text",
              text: "所有委員都已發言。你可以繼續指定特定委員補充發言，或用 board_report 生成最終報告。"
            }],
            details: { status: "all_spoken" },
          };
        }
        targetName = sess.speakOrder[sess.nextSpeakerIdx];
        sess.nextSpeakerIdx++;
      }

      const targetMember = sess.activeMembers.find(m => m.name === targetName);
      const targetDef = sess.memberDefs.get(targetName);

      if (!targetDef || !targetMember) {
        return {
          content: [{ type: "text", text: `無法載入委員 ${targetName} 的定義。` }],
          details: { status: "error" },
        };
      }

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `📊 ${displayName(targetName)} 發言中...` }],
          details: { status: "running" },
        });
      }

      // 3. 構建 prompt（包含完整對話歷史）
      const historyText = formatHistory(sess.history);
      const memberPrompt =
        `CEO 框架：\n${sess.ceoFrame}\n\n` +
        `原始 Brief：\n${sess.brief}\n\n` +
        `委員會討論歷史：\n${historyText}\n\n` +
        `現在輪到你（${displayName(targetName)}）發言。\n` +
        `請基於以上討論，給出你的分析並回應已提出的觀點（包括人類委員的觀點，若有）。\n` +
        `格式：立場 → 關鍵論點 → 主要顧慮 → 對之前觀點的回應\n\n` +
        `重要：全程繁體中文。200-350 字。`;

      let result;
      try {
        result = await runSubagent(
          targetDef.systemPrompt + loadMemberKnowledge(targetDef) + sess.knowledgeBase,
          memberPrompt,
          targetDef.model,
          targetDef.tools,
        );
      } catch (err) {
        return {
          content: [{ type: "text", text: `${displayName(targetName)} 子進程錯誤：${String(err)}` }],
          details: { status: "error" },
        };
      }

      if (result.exitCode !== 0 && !result.output) {
        return {
          content: [{ type: "text", text: `${displayName(targetName)} 執行失敗（exit ${result.exitCode}）：${result.output || "無輸出"}` }],
          details: { status: "error" },
        };
      }

      // 4. 記錄發言
      sess.history.push({
        speaker: targetName,
        content: result.output,
        timestamp: Date.now(),
      });

      updateWidget();

      // 5. 統計發言情況
      const spokenSet = new Set(
        sess.history.filter(e => e.speaker !== "user" && e.speaker !== "ceo").map(e => e.speaker)
      );
      const remainingMembers = sess.speakOrder.filter(n => !spokenSet.has(n));
      const allSpoken = remainingMembers.length === 0;

      const nextHint = allSpoken
        ? "\n\n所有委員都已發言。輸入 `board_report` 生成最終報告，或繼續用 `board_next member=\"委員名稱\"` 補充發言。"
        : `\n\n待發言委員：${remainingMembers.map(displayName).join(", ")}\n繼續用 \`board_next\` 讓下一位發言，或用 \`board_next member=\"委員名稱\"\` 指定委員。`;

      const userNoteShown = context?.trim()
        ? `\n**（已記錄你的回應）**\n\n`
        : "\n\n";

      const output =
        `${userNoteShown}### 📊 ${displayName(targetName)}\n\n${result.output}${nextHint}`;

      return {
        content: [{ type: "text", text: output }],
        details: {
          status: allSpoken ? "all_spoken" : "discussing",
          speaker: targetName,
          output: result.output,
          remainingMembers,
          allSpoken,
        },
      };
    },

    renderCall(args, theme) {
      const a = args as any;
      const memberLabel = a.member ? ` → ${a.member}` : " → 自動選擇";
      return new Text(
        theme.fg("toolTitle", theme.bold("board_next")) +
        theme.fg("accent", memberLabel),
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
        return new Text(theme.fg("accent", `● board_next`) + theme.fg("dim", " 委員發言中..."), 0, 0);
      }
      if (details.status === "error") {
        return new Text(theme.fg("error", `✗ board_next 失敗`), 0, 0);
      }
      if (details.status === "all_spoken") {
        return new Text(theme.fg("success", `✓ 所有委員已發言`) + theme.fg("dim", " — 可 board_report 生成報告"), 0, 0);
      }
      const remaining = (details.remainingMembers || []).length;
      return new Text(
        theme.fg("success", `✓ ${displayName(details.speaker || "")} 發言完畢`) +
        theme.fg("dim", ` · 待發言：${remaining} 位`),
        0, 0,
      );
    },
  });

  // ── board_report Tool ──────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_report",
    label: "Board Report",
    description:
      "結束互動討論模式，由 CEO 整合所有發言（含人類委員觀點）生成最終報告。" +
      "輸出 -discussion 後綴的 .md 和 .html 報告。",
    parameters: Type.Object({
      user_final_take: Type.Optional(Type.String({
        description: "你作為人類委員的最後總結或最終立場（可選）。會被納入報告。",
      })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { user_final_take } = params as { user_final_take?: string };

      if (!discussionSession?.active) {
        return {
          content: [{ type: "text", text: "目前沒有進行中的互動討論。請先呼叫 board_discuss 開始討論。" }],
          details: { status: "error" },
        };
      }

      const sess = discussionSession;

      // 1. 如果用戶有最後總結，先記錄
      if (user_final_take?.trim()) {
        sess.history.push({
          speaker: "user",
          content: `【人類委員最終總結】\n${user_final_take.trim()}`,
          timestamp: Date.now(),
        });
      }

      if (onUpdate) {
        onUpdate({
          content: [{ type: "text", text: `🏛 CEO 整合所有討論生成最終報告中...` }],
          details: { status: "running", phase: "synthesizing" },
        });
      }

      boardPhase = "synthesizing";
      updateWidget();

      // 2. 準備 CEO 整合 prompt
      const historyText = formatHistory(sess.history);

      // 整理各委員的原始發言（供 HTML 報告的 stance cards 使用）
      const boardResults: { name: string; stance: string; error: boolean }[] = sess.speakOrder
        .map(name => {
          const entries = sess.history.filter(e => e.speaker === name);
          if (entries.length === 0) return { name, stance: "（未發言）", error: true };
          return { name, stance: entries.map(e => e.content).join("\n\n"), error: false };
        });

      const userEntries = sess.history.filter(e => e.speaker === "user");
      const userContributions = userEntries.length > 0
        ? `\n\n## 人類委員（Human Board Member）貢獻\n\n${userEntries.map(e => e.content).join("\n\n---\n\n")}`
        : "";

      const ceoSystemPrompt =
        `你是投資顧問委員會（Investment Adviser Board）的主席（CEO）。` +
        `你是一位中立的 AI 協調者，負責框架投資問題並整合委員分析。` +
        sess.knowledgeBase;

      const synthesisPrompt =
        `你是投資顧問委員會的主席（CEO）。\n\n` +
        `根據原始 brief 和完整互動討論，撰寫最終投資建議報告。\n\n` +
        `Brief：\n${sess.brief}\n\n` +
        `CEO 框架：\n${sess.ceoFrame}\n\n` +
        `完整討論歷史：\n${historyText}\n\n` +
        `注意：此次為互動討論模式，人類委員（Human Board Member）也參與了討論，` +
        `請特別注意人類委員提出的觀點並在最終建議中納入考量。\n\n` +
        `撰寫結構化報告，包含以下章節：\n` +
        `## Final Decision\n` +
        `[整體市場觀點和核心建議 — 要果斷]\n\n` +
        `## 長期宏觀部位\n` +
        `[方向、進場區間、目標價、止損位、倉位比例]\n\n` +
        `## 搖擺交易操作\n` +
        `[進場點、出場目標、止損位、持倉時間預估]\n\n` +
        `## 風險提示\n` +
        `[整體風險等級和主要風險事件]\n\n` +
        `## Board Member Stances\n` +
        `[每位委員一段：立場 + 關鍵論點 + 主要顧慮；並包含人類委員的觀點摘要]\n\n` +
        `## Dissent & Tensions\n` +
        `[委員之間的重大分歧和未解決的張力，包含人類委員引發的討論]\n\n` +
        `## Trade-offs\n` +
        `[機會（得到） vs. 風險（失去）]\n\n` +
        `## Next Actions\n` +
        `[3-5 個具體可執行的操作步驟]\n\n` +
        `## Deliberation Summary\n` +
        `[互動討論如何展開，人類委員的參與如何影響了最終判斷]\n\n` +
        `重要：全程使用繁體中文。章節標題保持英文以便解析。技術術語可保留英文。`;

      const synthResult = await runSubagent(ceoSystemPrompt, synthesisPrompt, sess.ceoModel, "none");
      const memo = synthResult.output;

      // 3. 儲存報告（加 -discussion 後綴）
      const memosDir = join(cwd, ".pi", "investment-adviser-board", "memos");
      mkdirSync(memosDir, { recursive: true });

      const briefFirstLine = sess.brief.split("\n").find(l => l.trim()) || "investment-analysis";
      const slug = slugify(briefFirstLine.replace(/^#+\s*/, ""));
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const memoFilename = `${slug}-${timestamp}-discussion.md`;
      const memoPath = join(memosDir, memoFilename);

      const validResults = boardResults.filter(r => !r.error);
      const allStances = validResults
        .map(r => `### ${displayName(r.name)}\n${r.stance}`)
        .join("\n\n");

      const memoContent =
        `# 投資顧問委員會報告（互動討論模式）\n\n` +
        `**日期：** ${new Date().toISOString().slice(0, 10)}\n` +
        `**模式：** 互動討論（Mode B）\n` +
        `**Preset：** ${sess.preset}\n` +
        `**委員：** ${sess.activeMembers.map(m => displayName(m.name)).join(", ")}\n` +
        `**對話輪次：** ${sess.history.length}\n` +
        `**人類委員發言次數：** ${userEntries.length}\n\n` +
        `---\n\n` +
        `## 分析 Brief\n\n${sess.brief}\n\n` +
        `---\n\n` +
        `## CEO 框架\n\n${sess.ceoFrame}\n\n` +
        `---\n\n` +
        `## 完整討論歷史\n\n${historyText}\n\n` +
        `---\n\n` +
        `## 各委員立場（彙整）\n\n${allStances}${userContributions}\n\n` +
        `---\n\n` +
        `${memo}`;

      writeFileSync(memoPath, memoContent, "utf-8");

      // 4. 生成 HTML（使用相同的 generateHtmlReport，加入人類委員的 stance card）
      const htmlBoardResults = [
        ...boardResults,
        ...(userEntries.length > 0 ? [{
          name: "human-board-member",
          stance: userEntries.map(e => e.content).join("\n\n---\n\n"),
          error: false,
        }] : []),
      ];

      const htmlPath = memoPath.replace(/\.md$/, ".html");
      const htmlContent = generateHtmlReport({
        date: new Date().toISOString().slice(0, 10),
        preset: `${sess.preset} · 互動討論模式`,
        memberNames: [
          ...sess.activeMembers.map(m => m.name),
          ...(userEntries.length > 0 ? ["human-board-member"] : []),
        ],
        briefText: sess.brief,
        ceoFrame: sess.ceoFrame,
        boardResults: htmlBoardResults,
        memo,
      });
      writeFileSync(htmlPath, htmlContent, "utf-8");

      // 5. 清除 discussionSession
      discussionSession = null;
      boardPhase = "done";
      updateWidget();

      const truncated = memo.length > 8000 ? memo.slice(0, 8000) + "\n\n... [截斷 — 請查看報告檔案]" : memo;

      return {
        content: [{ type: "text", text: `報告已儲存：\n  📄 ${memoPath}\n  🌐 ${htmlPath}\n\n${truncated}` }],
        details: {
          status: "done",
          memoPath,
          htmlPath,
          preset: sess.preset,
          memberCount: sess.activeMembers.length,
          discussionRounds: sess.history.length,
          memo,
        },
      };
    },

    renderCall(_args, theme) {
      return new Text(
        theme.fg("toolTitle", theme.bold("board_report")) +
        theme.fg("dim", " — 生成最終討論報告"),
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
        return new Text(theme.fg("accent", `● board_report`) + theme.fg("dim", " CEO 整合報告中..."), 0, 0);
      }
      if (details.status === "error") {
        return new Text(theme.fg("error", `✗ board_report 失敗`), 0, 0);
      }
      const header =
        theme.fg("success", `✓ 互動討論報告已生成`) +
        theme.fg("dim", ` · ${details.memberCount} 位委員 · ${details.discussionRounds} 輪對話 · `) +
        theme.fg("muted", details.memoPath || "");
      if (options.expanded && details.memo) {
        const output = details.memo.length > 4000
          ? details.memo.slice(0, 4000) + "\n... [截斷]"
          : details.memo;
        return new Text(header + "\n" + theme.fg("muted", output), 0, 0);
      }
      return new Text(header, 0, 0);
    },
  });

  // ── Commands ───────────────────────────────────────────────────────────────

  pi.registerCommand("board-preset", {
    description: "選擇投資顧問委員會 preset",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const presetNames = Object.keys(boardConfig.presets);
      if (presetNames.length === 0) {
        ctx.ui.notify("config.yaml 中未定義 preset", "warning");
        return;
      }

      const options = presetNames.map(name => {
        const members = boardConfig.presets[name];
        return `${name} (${members.join(", ")})`;
      });

      const choice = await ctx.ui.select("選擇委員會 Preset", options);
      if (choice === undefined) return;

      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];

      const members = boardConfig.presets[activePreset];
      ctx.ui.setStatus("investment-adviser-board", `Preset: ${activePreset} · ${members.length} 位委員`);
      ctx.ui.notify(
        `Preset：${activePreset}\n委員：${members.map(displayName).join(", ")}`,
        "info",
      );
      updateWidget();
    },
  });

  pi.registerCommand("board-status", {
    description: "顯示活躍的投資顧問委員",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const active = getActiveMembers();
      const all = boardConfig.board;

      const lines = all.map(m => {
        const isActive = active.some(a => a.name === m.name);
        const icon = isActive ? "✓" : "○";
        return `${icon} ${displayName(m.name)}  (${m.path})`;
      });

      const presetInfo = activePreset ? `Preset：${activePreset}` : "使用 config 預設";
      const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 10), 10);

      ctx.ui.notify(
        `${presetInfo}\n分析時間：${time} 分鐘（參考值）\n\n` +
        lines.join("\n"),
        "info",
      );
    },
  });

  pi.registerCommand("board-history", {
    description: "列出最近的投資分析報告",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const memosDir = join(cwd, ".pi", "investment-adviser-board", "memos");
      if (!existsSync(memosDir)) {
        ctx.ui.notify("尚無報告。執行 board_begin 開始第一次分析。", "info");
        return;
      }

      const files = readdirSync(memosDir)
        .filter(f => f.endsWith(".md"))
        .sort()
        .reverse()
        .slice(0, 10);

      if (files.length === 0) {
        ctx.ui.notify("在 .pi/investment-adviser-board/memos/ 中未找到報告", "info");
        return;
      }

      const lines = files.map((f, i) => {
        const hasHtml = existsSync(join(memosDir, f.replace(/\.md$/, ".html")));
        return `${i + 1}. ${f}${hasHtml ? " 🌐" : ""}`;
      });

      ctx.ui.notify(
        `最近的投資分析報告（${files.length} 份）：\n\n${lines.join("\n")}\n\n📁 ${memosDir}`,
        "info",
      );
    },
  });

  // ── before_agent_start ─────────────────────────────────────────────────────

  pi.on("before_agent_start", async (_event, _ctx) => {
    widgetCtx = _ctx;

    const active = getActiveMembers();
    const presetLabel = activePreset || "config 預設";
    const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 10), 10);

    const presetList = Object.keys(boardConfig.presets).join(", ");
    const memberList = active.map(m => `- **${displayName(m.name)}**`).join("\n");

    return {
      systemPrompt:
        `你是投資顧問委員會（Investment Adviser Board）的主持人。\n\n` +
        `這是一個多代理投資分析系統，支援兩種交易風格：\n` +
        `- **長期宏觀部位**：基於全球經濟週期和貨幣政策\n` +
        `- **搖擺交易**：基於動量/反轉策略，持倉數天至數週\n\n` +
        `## 兩種分析模式\n\n` +
        `### Mode A — 全自動（board_begin）\n` +
        `用戶提交 brief → AI 全自動運行 → 輸出 HTML 報告。用戶在迴圈外等待。\n\n` +
        `### Mode B — 互動討論（board_discuss → board_next → board_report）\n` +
        `用戶作為「人類委員」坐入委員會，與 AI 委員輪流討論。\n` +
        `- \`board_discuss\`：開始互動模式，CEO 框架 + 第一位委員發言\n` +
        `- \`board_next\`：讓下一位委員發言（可在 context 填入你的回應）\n` +
        `- \`board_report\`：結束討論，生成報告（-discussion 後綴）\n\n` +
        `## 你的職責\n` +
        `當用戶想分析投資標的時，先詢問他們想用哪種模式：\n` +
        `1. **全自動模式**：呼叫 \`board_begin\` 即可\n` +
        `2. **互動討論模式**：先呼叫 \`board_discuss\`，然後引導用戶用 \`board_next\` 輪流討論\n\n` +
        `如果用戶沒有明確表示偏好，可根據其需求建議：想快速得到報告選 Mode A；想深度參與討論選 Mode B。\n\n` +
        `## 當前委員會配置\n` +
        `Preset：${presetLabel}\n` +
        `分析時間：${time} 分鐘（參考值）\n` +
        `活躍委員（${active.length}）：\n${memberList}\n\n` +
        `## 可用 Presets\n` +
        `${presetList || "未定義"}\n` +
        `使用 /board-preset 切換，/board-status 查看委員。\n\n` +
        `## Brief 格式建議\n` +
        `請用戶以下列結構提供 brief：\n` +
        `- ## 分析標的（股票代碼 + 公司名）\n` +
        `- ## 背景與問題\n` +
        `- ## 當前市場狀況\n` +
        `- ## 分析重點\n\n` +
        `也接受任何自由格式文字。若有 .md 檔案，直接傳路徑。\n\n` +
        `## 指令\n` +
        `/board-preset    選擇 preset\n` +
        `/board-status    顯示活躍委員\n` +
        `/board-history   查看過往報告\n\n` +
        `請先歡迎用戶，詢問他們想分析哪個投資標的，以及偏好全自動模式還是互動討論模式。\n\n` +
        `**語言規則：永遠使用繁體中文（Traditional Chinese）與用戶溝通。技術術語（RSI、MACD、ATR）、股票代碼、工具名稱可保留英文。絕對不可用英文回覆用戶。**`,
    };
  });

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, _ctx) => {
    applyExtensionDefaults(import.meta.url, _ctx);

    if (widgetCtx) widgetCtx.ui.setWidget("investment-adviser-board", undefined);
    _ctx.ui.setWidget("investment-adviser-board", undefined);
    widgetCtx = _ctx;

    boardPhase = "idle";
    memberStates = [];
    activePreset = null;

    loadConfig(_ctx.cwd);

    const active = getActiveMembers();
    const time = parseInt(String(process.env.DISCUSSION_TIME || boardConfig.meeting.discussion_time_minutes || 10), 10);

    _ctx.ui.setStatus("investment-adviser-board", `Investment Board · ${active.length} 位委員活躍`);
    _ctx.ui.notify(
      `投資顧問委員會\n` +
      `${active.length} 位活躍委員 · ${time} 分鐘分析\n\n` +
      `Mode A（全自動）：board_begin\n` +
      `Mode B（互動討論）：board_discuss → board_next → board_report\n\n` +
      `/board-preset    選擇 preset\n` +
      `/board-status    顯示委員`,
      "info",
    );

    updateWidget();

    _ctx.ui.setFooter((_tui, theme, _footerData) => ({
      dispose: () => { },
      invalidate() { },
      render(width: number): string[] {
        const presetLabel = activePreset || "default";
        const memberCount = getActiveMembers().length;

        const left =
          theme.fg("dim", ` CEO: gpt-5.2-codex`) +
          theme.fg("muted", " · ") +
          theme.fg("accent", "investment-board") +
          theme.fg("muted", " · ") +
          theme.fg("dim", presetLabel) +
          theme.fg("muted", " · ") +
          theme.fg("dim", `${memberCount} 位委員活躍`);

        const right = theme.fg("dim", ` `);

        const pad = " ".repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));

        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });
}
