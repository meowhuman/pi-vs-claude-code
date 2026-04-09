/**
 * AI Tools Board — 多代理 AI 工具研究委員會系統
 *
 * 追蹤音樂 AI、影片 AI、程式 AI 的最新動態，整合洞見並給出行動建議。
 * 支援全自動研究模式（Mode A）和互動討論模式（Mode B）。
 *
 * Config: .pi/ai-tools-board/config.yaml
 * Agents: .pi/ai-tools-board/agents/<name>/
 * Memos:  .pi/ai-tools-board/memos/<slug>-<timestamp>.md
 *
 * Commands:
 *   /board-preset  — 選擇委員會 preset（互動 select UI）
 *   /board-status  — 顯示活躍委員
 *
 * Tools (Mode A — 全自動):
 *   board_begin    — 提交研究主題 → AI 全自動運行 → 輸出 HTML 報告
 *
 * Tools (Mode B — 互動討論):
 *   board_discuss  — 開始互動討論模式，用戶作為「人類委員」坐入委員會
 *   board_next     — 讓下一位或指定委員發言（可帶入用戶的背景/回應）
 *   board_report   — 結束討論，生成最終報告
 *
 * Usage: pi -e extensions/boards/ai-tools-board.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { Text } from "@mariozechner/pi-tui";
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

interface DiscussionEntry {
  speaker: string;
  content: string;
  timestamp: number;
}

interface DiscussionSession {
  active: boolean;
  brief: string;
  directorFrame: string;
  history: DiscussionEntry[];
  activeMembers: BoardMemberConfig[];
  memberDefs: Map<string, MemberDef>;
  speakOrder: string[];
  nextSpeakerIdx: number;
  directorModel: string;
  preset: string;
}

// ── YAML Parser ───────────────────────────────────────────────────────────────

function parseBoardConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
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
      if (m) config.presets[m[1].trim()] = m[2].split(",").map(s => s.trim()).filter(Boolean);
      continue;
    }
  }
  if (section === "board" && inBoardItem && currentItem.name) {
    config.board.push({ name: currentItem.name!, path: currentItem.path || "", active: currentItem.active !== false });
  }
  return config;
}

// ── Agent File Parser ─────────────────────────────────────────────────────────

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
      const knowledgePath = join(dirname(filePath), `${name}-knowledge.md`);
      return { name, systemPrompt: match[2].trim(), model: fm["model"] || "glm/glm-5-turbo", tools: fm["tools"] || "bash,read", knowledgePath };
    }
    return null;
  } catch { return null; }
}

function loadMemberKnowledge(member: MemberDef): string {
  if (!existsSync(member.knowledgePath)) return "";
  const content = readFileSync(member.knowledgePath, "utf-8").trim();
  return content ? `\n\n## ${member.name} 個人知識庫\n\n${content}` : "";
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^\w\u4e00-\u9fff\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 60);
}

function displayName(name: string): string {
  return name.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function formatHistory(history: DiscussionEntry[]): string {
  if (history.length === 0) return "（尚無討論記錄）";
  return history.map((entry, i) => {
    const label = entry.speaker === "user" ? "👤 人類委員"
      : entry.speaker === "director" ? "🎯 主席（Director）"
        : `🔍 ${displayName(entry.speaker)}`;
    return `[${i + 1}] ${label}\n${entry.content}`;
  }).join("\n\n---\n\n");
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── Subprocess Runner ─────────────────────────────────────────────────────────

interface RunResult { output: string; exitCode: number; elapsed: number; }

function runSubagent(
  systemPrompt: string,
  prompt: string,
  model: string = "glm/glm-5-turbo",
  tools: string = "bash,read",
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = ["--mode", "json", "-p", "--no-extensions", "--model", model, "--tools", tools, "--thinking", "off", "--append-system-prompt", systemPrompt, "--no-session", prompt];
  const textChunks: string[] = [];
  const startTime = Date.now();

  return new Promise((resolve) => {
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
    proc.stderr!.on("data", (chunk: string) => { stderrChunks.push(chunk); });

    proc.on("close", (code) => {
      const output = textChunks.join("") || (stderrChunks.join("").trim() ? `[stderr] ${stderrChunks.join("").trim()}` : "");
      resolve({ output, exitCode: code ?? 1, elapsed: Date.now() - startTime });
    });
    proc.on("error", (err) => resolve({ output: `Error: ${err.message}`, exitCode: 1, elapsed: Date.now() - startTime }));
  });
}

// ── HTML Report ───────────────────────────────────────────────────────────────

function extractSection(memo: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}[^\n]*\n([\\s\\S]*?)(?=\n##\\s|$)`, "i");
  const m = memo.match(re);
  return m ? m[1].trim() : "";
}

function parseList(text: string): string[] {
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  const items: string[] = [];
  for (const line of lines) {
    const m = line.match(/^(?:\d+[.)]\s*|-\s*)(.+)/);
    if (m) items.push(m[1].replace(/\*+/g, "").trim());
    else if (items.length > 0 && !line.startsWith("#")) items[items.length - 1] += " " + line.replace(/\*+/g, "");
  }
  return items.slice(0, 8);
}

function generateHtmlReport(opts: {
  date: string; preset: string; memberNames: string[]; briefText: string;
  directorFrame: string; boardResults: { name: string; analysis: string; error: boolean }[]; memo: string;
}): string {
  const { date, preset, memberNames, briefText, directorFrame, boardResults, memo } = opts;
  const keySignals = escapeHtml(extractSection(memo, "本週關鍵信號|Key Signals|今週最值得關注|核心發現"));
  const currentSystemReview = escapeHtml(extractSection(memo, "Current System Review|現有系統檢視|系統檢視"));
  const recommendedArchitecture = escapeHtml(extractSection(memo, "Recommended Architecture|建議架構|推薦架構"));
  const costTradeoff = escapeHtml(extractSection(memo, "Cost / Performance Tradeoff|Cost Performance Tradeoff|成本效能權衡"));
  const adoptNow = escapeHtml(extractSection(memo, "Adopt Now / Watch / Ignore|Adopt Now|採用建議"));
  const nextActions = parseList(extractSection(memo, "下一步行動|Next Actions|建議行動|行動建議"));
  const dissent = escapeHtml(extractSection(memo, "分歧|爭議|Dissent|張力"));
  const overview = escapeHtml(extractSection(memo, "整體觀察|Overview|全局觀點|綜合分析"));

  const briefHtml = briefText.split("\n").map(line => {
    if (line.startsWith("## ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^##\s*/, ""))}</div>`;
    if (line.startsWith("# ")) return `<div class="brief-heading">${escapeHtml(line.replace(/^#\s*/, ""))}</div>`;
    if (line.trim() === "") return `<div class="brief-spacer"></div>`;
    return `<div class="brief-line">${escapeHtml(line)}</div>`;
  }).join("\n");

  const analysisCards = boardResults.filter(r => !r.error).map(r => {
    const firstPara = r.analysis.split("\n").filter(l => l.trim())[0] || "";
    return `<div class="member-card"><div class="card-header">${escapeHtml(displayName(r.name))}</div><div class="card-content">${escapeHtml(firstPara.replace(/\*+/g, "").slice(0, 200))}${firstPara.length > 200 ? "…" : ""}</div></div>`;
  }).join("\n");

  const actionItems = nextActions.map(a => `<li>${escapeHtml(a)}</li>`).join("\n");
  const memberTags = memberNames.map(n => `<span class="member-tag">${escapeHtml(displayName(n))}</span>`).join("");

  return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Tools Board 研究報告</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#1a1b26;--card-bg:#24283b;--accent:#7aa2f7;--secondary:#9ece6a;--text:#c0caf5;--muted:#a9b1d6;--border:rgba(122,162,247,0.2);--success:#9ece6a;--danger:#f7768e;--divider:rgba(255,255,255,0.06)}
body{background:var(--bg);color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;font-size:15px;line-height:1.7;min-height:100vh}
.container{max-width:960px;margin:0 auto;padding:0 2rem}
header{text-align:center;padding:4rem 2rem 2.5rem;border-bottom:1px solid var(--divider);background:linear-gradient(180deg,rgba(122,162,247,0.05) 0%,transparent 100%)}
.logo{font-size:.75rem;font-weight:700;letter-spacing:.35em;color:var(--accent);text-transform:uppercase;margin-bottom:.6rem}
.title{font-size:1.9rem;font-weight:800;color:var(--text);margin-bottom:.4rem}
.subtitle{font-size:.82rem;font-weight:500;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);margin-bottom:1.2rem}
.meta{font-size:.8rem;color:var(--muted);display:flex;align-items:center;justify-content:center;gap:.5rem;flex-wrap:wrap}
.meta-badge{background:rgba(122,162,247,0.12);color:var(--accent);padding:.15rem .7rem;border-radius:20px;font-size:.72rem;font-weight:600;letter-spacing:.08em}
section{padding:2.5rem 0;border-bottom:1px solid var(--divider)}
section:last-of-type{border-bottom:none}
.section-label{font-size:.68rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);margin-bottom:1.2rem}
.brief-heading{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--secondary);margin:1rem 0 .4rem}
.brief-line{color:var(--muted);font-size:.9rem;line-height:1.8;max-width:700px}
.brief-spacer{height:.5rem}
.director-framing{margin-top:1rem;padding:1rem 1.2rem;border-left:3px solid rgba(122,162,247,0.4);background:rgba(122,162,247,0.04);border-radius:0 6px 6px 0;font-size:.88rem;color:var(--muted);line-height:1.8}
.director-label{font-size:.65rem;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:.5rem}
.signals-block{background:rgba(158,206,106,0.04);border:1px solid rgba(158,206,106,0.2);border-radius:10px;padding:1.5rem;font-size:.92rem;color:var(--text);line-height:1.8;white-space:pre-wrap}
.members-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}
.member-card{background:var(--card-bg);border-radius:10px;padding:1.2rem 1.5rem;border:1px solid var(--border)}
.card-header{font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:.6rem}
.card-content{font-size:.88rem;color:var(--muted);line-height:1.7}
.member-tag{background:rgba(122,162,247,0.1);color:var(--accent);padding:.2rem .6rem;border-radius:12px;font-size:.7rem;font-weight:600;margin-right:.4rem;display:inline-block;margin-bottom:.3rem}
.overview-block{font-size:.92rem;color:var(--muted);line-height:1.85;white-space:pre-wrap}.architecture-block,.tradeoff-block,.adopt-block{font-size:.9rem;color:var(--muted);line-height:1.8;white-space:pre-wrap;background:rgba(122,162,247,0.04);border:1px solid var(--border);border-radius:10px;padding:1.2rem 1.4rem}.tradeoff-block{background:rgba(158,206,106,0.04);border-color:rgba(158,206,106,0.2)}.adopt-block{background:rgba(247,118,142,0.04);border-color:rgba(247,118,142,0.15)}
.actions-list{list-style:none;counter-reset:actions}
.actions-list li{counter-increment:actions;display:flex;align-items:flex-start;gap:.8rem;padding:.8rem 0;border-bottom:1px solid var(--divider);font-size:.9rem;color:var(--text)}
.actions-list li::before{content:counter(actions);background:rgba(122,162,247,0.15);color:var(--accent);min-width:1.8rem;height:1.8rem;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;flex-shrink:0}
.dissent-block{background:rgba(247,118,142,0.04);border:1px solid rgba(247,118,142,0.15);border-radius:10px;padding:1.2rem 1.5rem;font-size:.88rem;color:var(--muted);line-height:1.8}
footer{text-align:center;padding:2rem;font-size:.75rem;color:var(--muted);opacity:.5;border-top:1px solid var(--divider);display:flex;flex-direction:column;gap:.3rem}
</style>
</head>
<body>
<div class="container">
<header>
  <div class="logo">AI Tools Board</div>
  <div class="title">AI 工具研究報告</div>
  <div class="subtitle">Multi-Agent Research Intelligence</div>
  <div class="meta"><span>${escapeHtml(date)}</span><span>·</span><span class="meta-badge">${escapeHtml(preset)}</span><span>·</span><div>${memberTags}</div></div>
</header>
<section>
  <div class="section-label">研究主題</div>
  ${briefHtml}
  <div class="director-framing"><div class="director-label">主席框架</div>${escapeHtml(directorFrame)}</div>
</section>
${keySignals ? `<section><div class="section-label">本週關鍵信號</div><div class="signals-block">${keySignals}</div></section>` : ""}
<section><div class="section-label">各委員分析</div><div class="members-grid">${analysisCards}</div></section>
${overview ? `<section><div class="section-label">整體觀察</div><div class="overview-block">${overview}</div></section>` : ""}
${currentSystemReview ? `<section><div class="section-label">Current System Review</div><div class="architecture-block">${currentSystemReview}</div></section>` : ""}
${recommendedArchitecture ? `<section><div class="section-label">Recommended Architecture</div><div class="architecture-block">${recommendedArchitecture}</div></section>` : ""}
${costTradeoff ? `<section><div class="section-label">Cost / Performance Tradeoff</div><div class="tradeoff-block">${costTradeoff}</div></section>` : ""}
${adoptNow ? `<section><div class="section-label">Adopt Now / Watch / Ignore</div><div class="adopt-block">${adoptNow}</div></section>` : ""}
${dissent ? `<section><div class="section-label">分歧與爭議</div><div class="dissent-block">${dissent}</div></section>` : ""}
${actionItems ? `<section><div class="section-label">行動建議</div><ol class="actions-list">${actionItems}</ol></section>` : ""}
<footer><span>本報告由 AI Tools Board 多代理系統自動生成，供研究參考。</span><span>Generated by Pi Multi-Agent System</span></footer>
</div>
</body>
</html>`;
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let widgetCtx: ExtensionContext | null = null;
  let boardConfig: BoardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
  let activePreset: string | null = null;
  let memberStates: MemberState[] = [];
  let boardPhase: "idle" | "framing" | "researching" | "synthesizing" | "done" = "idle";
  let cwd = "";
  let discussionSession: DiscussionSession | null = null;

  // ── Config Loader ──────────────────────────────────────────────────────────

  function loadConfig(rootCwd: string) {
    cwd = rootCwd;
    const configPath = join(rootCwd, ".pi", "ai-tools-board", "config.yaml");
    if (!existsSync(configPath)) return;
    try {
      boardConfig = parseBoardConfigYaml(readFileSync(configPath, "utf-8"));
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

  // ── Widget ─────────────────────────────────────────────────────────────────

  function updateWidget() {
    if (!widgetCtx) return;
    widgetCtx.ui.setWidget("ai-tools-board", (_tui: any, theme: any) => {
      const text = new Text("", 0, 1);
      return {
        render(width: number): string[] {
          if (discussionSession?.active) {
            const sess = discussionSession;
            const spoken = [...new Set(sess.history.filter(e => e.speaker !== "user" && e.speaker !== "director").map(e => displayName(e.speaker)))];
            const remaining = sess.speakOrder.length - sess.nextSpeakerIdx;
            const lines = [
              theme.fg("accent", "● AI Tools Board — 互動討論模式"),
              "",
              theme.fg("muted", `對話輪次：${sess.history.length}  |  已發言：${spoken.length} 位  |  待發言：${remaining} 位`),
              spoken.length > 0 ? theme.fg("dim", `已發言：${spoken.join(", ")}`) : "",
              sess.nextSpeakerIdx < sess.speakOrder.length
                ? theme.fg("accent", `下一位：${displayName(sess.speakOrder[sess.nextSpeakerIdx])}`)
                : theme.fg("success", "所有委員已發言，可 board_report 生成報告"),
            ].filter(Boolean);
            text.setText(lines.join("\n"));
            return text.render(width);
          }

          if (memberStates.length === 0) {
            const lines = [
              theme.fg("accent", "● AI Tools Board"),
              "",
              theme.fg("muted", `Preset: ${activePreset || "full"} · ${getActiveMembers().length} 位委員`),
              theme.fg("dim", "board_begin <topic> — 全自動研究"),
              theme.fg("dim", "board_discuss <topic> — 互動討論"),
            ];
            text.setText(lines.join("\n"));
            return text.render(width);
          }

          const doneCnt = memberStates.filter(s => s.status === "done").length;
          const total = memberStates.length;
          const phaseLabel = { framing: "框架分析中...", researching: "委員研究中...", synthesizing: "主席整合中...", done: "研究完成", idle: "待機" }[boardPhase];

          const cols = Math.max(1, Math.floor(width / 32));
          const allLines: string[] = [
            theme.fg("accent", `● AI Tools Board — ${phaseLabel}`),
            theme.fg("muted", `委員進度：${doneCnt}/${total}`),
            "",
          ];

          for (let i = 0; i < memberStates.length; i += cols) {
            const row = memberStates.slice(i, i + cols);
            const colWidth = Math.floor(width / cols);
            const cards = row.map(s => {
              const w = colWidth - 2;
              const truncate = (str: string, max: number) => str.length > max ? str.slice(0, max - 3) + "..." : str;
              const statusColor = s.status === "pending" ? "dim" : s.status === "running" ? "accent" : s.status === "done" ? "success" : "error";
              const statusIcon = s.status === "pending" ? "○" : s.status === "running" ? "◉" : s.status === "done" ? "✓" : "✗";
              const name = displayName(s.name);
              const nameStr = theme.fg("accent", theme.bold(truncate(name, w)));
              const statusLine = theme.fg(statusColor, `${statusIcon} ${s.status}${s.status !== "pending" ? ` ${Math.round(s.elapsed / 1000)}s` : ""}`);
              const workText = s.lastWork ? truncate(s.lastWork.replace(/\*+([^*]+)\*+/g, "$1"), Math.min(55, w - 1)) : "";
              const workLine = workText ? theme.fg("muted", workText) : theme.fg("dim", "—");
              const border = (content: string, vis: number) => theme.fg("borderMuted", "│") + content + " ".repeat(Math.max(0, w - vis)) + theme.fg("borderMuted", "│");
              return [
                theme.fg("accent", "┌" + "─".repeat(w) + "┐"),
                border(" " + nameStr, 1 + Math.min(name.length, w)),
                border(" " + statusLine, 1 + `${statusIcon} ${s.status}`.length + (s.status !== "pending" ? ` ${Math.round(s.elapsed / 1000)}s`.length : 0)),
                border(" " + workLine, 1 + (workText ? workText.length : 1)),
                border(" ", 1),
                theme.fg("borderMuted", "└" + "─".repeat(w) + "┘"),
              ];
            });
            const maxH = Math.max(...cards.map(c => c.length));
            for (let r = 0; r < maxH; r++) {
              allLines.push(cards.map(c => c[r] || " ".repeat(colWidth)).join(""));
            }
          }

          text.setText(allLines.join("\n"));
          return text.render(width);
        },
      };
    });
  }

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    widgetCtx = ctx;
    applyExtensionDefaults(import.meta.url, ctx);
    loadConfig(ctx.cwd);
    updateWidget();
  });

  // ── Commands ───────────────────────────────────────────────────────────────

  pi.registerCommand("board-preset", {
    description: "選擇 AI Tools Board preset（互動選單）",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      loadConfig(ctx.cwd);
      const presetNames = Object.keys(boardConfig.presets);
      if (presetNames.length === 0) {
        ctx.ui.notify("config.yaml 中未定義 preset", "warning");
        return;
      }
      const options = presetNames.map(name => {
        const members = boardConfig.presets[name];
        return `${name}  (${members.join(", ")})`;
      });
      const choice = await ctx.ui.select("選擇委員會 Preset", options);
      if (choice === undefined) return;
      activePreset = presetNames[options.indexOf(choice)];
      const members = boardConfig.presets[activePreset];
      ctx.ui.setStatus("ai-tools-board", `Preset: ${activePreset} · ${members.length} 位委員`);
      ctx.ui.notify(`Preset：${activePreset}\n委員：${members.map(displayName).join(", ")}`, "info");
      updateWidget();
    },
  });

  pi.registerCommand("board-status", {
    description: "顯示 AI Tools Board 活躍委員",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      loadConfig(ctx.cwd);
      const active = getActiveMembers();
      const presetInfo = activePreset ? `Preset：${activePreset}` : "使用 config 預設";
      const lines = boardConfig.board.map(m => {
        const isActive = active.some(a => a.name === m.name);
        return `${isActive ? "✓" : "○"} ${displayName(m.name)}`;
      });
      ctx.ui.notify(`${presetInfo}\n\n${lines.join("\n")}`, "info");
    },
  });

  pi.registerCommand("board-history", {
    description: "列出最近的 AI Tools Board 研究報告",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      const memosDir = join(ctx.cwd, ".pi", "ai-tools-board", "memos");
      if (!existsSync(memosDir)) {
        ctx.ui.notify("尚無報告。執行 board_begin 開始第一次研究。", "info");
        return;
      }
      const files = readdirSync(memosDir).filter(f => f.endsWith(".md")).sort().reverse().slice(0, 10);
      if (files.length === 0) {
        ctx.ui.notify("尚無報告", "info");
        return;
      }
      ctx.ui.notify(`最近報告：\n${files.map((f, i) => `${i + 1}. ${f}`).join("\n")}`, "info");
    },
  });

  // ── Tool: board_begin (Mode A) ────────────────────────────────────────────

  pi.registerTool({
    name: "board_begin",
    label: "Board Begin",
    description: "召集 AI Tools Board 進行全自動研究。主席框架後所有委員並行研究，最後整合輸出 HTML 報告（Mode A）。",
    parameters: Type.Object({
      brief: Type.String({ description: "研究主題或問題，例如：本週 AI coding 工具有哪些重大更新？" }),
      preset: Type.Optional(Type.String({ description: "指定 preset（full/discovery/music/video/coding/github/systems/quick）" })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };
      if (ctx && !widgetCtx) widgetCtx = ctx;
      loadConfig(ctx?.cwd || cwd);

      const presetName = preset || activePreset || "full";
      activePreset = presetName;
      const activeMembers = getActiveMembers(presetName);

      if (activeMembers.length === 0) {
        return { content: [{ type: "text", text: "找不到任何委員。請確認 config.yaml 正確配置。" }], details: { status: "error" } };
      }

      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return { content: [{ type: "text", text: `缺少 agent 檔案：\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }], details: { status: "error" } };
      }

      // Init widget
      memberStates = activeMembers.map(m => ({ name: m.name, status: "pending" as const, elapsed: 0, lastWork: "" }));
      boardPhase = "framing";
      updateWidget();

      // 步驟 1：主席框架
      const directorConfig = activeMembers.find(m => m.name === "director");
      const directorDef = directorConfig ? parseMemberFile(resolve(cwd, directorConfig.path)) : null;
      const directorModel = directorDef?.model || "glm/glm-5-turbo";
      const directorSystem = (directorDef?.systemPrompt || "你是 AI Tools Board 的主席。") + (directorDef ? loadMemberKnowledge(directorDef) : "");

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🎯 主席框架研究議題中...` }], details: { status: "running", phase: "framing" } });

      const frameResult = await runSubagent(
        directorSystem,
        `你是 AI Tools Board 主席。請框架以下研究主題：\n\n${brief}\n\n委員陣容：${activeMembers.filter(m => m.name !== "director").map(m => m.name).join(", ")}\n\n請明確點出：核心問題、各委員應聚焦的方向、預期洞見。若主題與系統改進有關，優先聚焦 agentic architecture、成本、評測、整合可行性，避免過度複雜。繁體中文，200字以內。`,
        directorModel, "bash,read"
      );
      const directorFrame = frameResult.output;

      // 步驟 2：各委員並行研究
      boardPhase = "researching";
      updateWidget();

      const nonDirectorMembers = activeMembers.filter(m => m.name !== "director");
      const memberResults: { name: string; analysis: string; error: boolean }[] = [];

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🔍 ${nonDirectorMembers.length} 位委員並行研究中...` }], details: { status: "running", phase: "researching" } });

      await Promise.all(nonDirectorMembers.map(async (member) => {
        const stateIdx = memberStates.findIndex(s => s.name === member.name);
        if (stateIdx >= 0) memberStates[stateIdx].status = "running";
        updateWidget();

        const def = parseMemberFile(resolve(cwd, member.path));
        if (!def) {
          if (stateIdx >= 0) { memberStates[stateIdx].status = "error"; memberStates[stateIdx].lastWork = "無法解析角色定義"; }
          memberResults.push({ name: member.name, analysis: "角色定義解析失敗", error: true });
          updateWidget();
          return;
        }

        const systemPrompt = def.systemPrompt + loadMemberKnowledge(def);
        const prompt = `作為 ${displayName(def.name)}，請研究以下主題並提供專業洞見：\n\n研究主題：${brief}\n\n主席框架：${directorFrame}\n\n請提供：\n1. 最重要的 1-3 個最新信號（需搜尋最新資料）\n2. 你的專業評估\n3. 對現有系統或 workflow 的具體影響\n4. 建議立即採用 / 觀察 / 忽略的項目\n\n若主題涉及系統設計，請優先追求簡單、低成本、可落地。繁體中文，300-500字。`;

        const result = await runSubagent(systemPrompt, prompt, def.model, def.tools, (chunk) => {
          if (stateIdx >= 0) { memberStates[stateIdx].lastWork = chunk.slice(-60); updateWidget(); }
        });

        if (stateIdx >= 0) {
          memberStates[stateIdx].status = result.exitCode === 0 ? "done" : "error";
          memberStates[stateIdx].elapsed = result.elapsed;
          memberStates[stateIdx].lastWork = result.output.split("\n").find(l => l.trim()) || "";
        }
        memberResults.push({ name: member.name, analysis: result.output, error: result.exitCode !== 0 });
        updateWidget();
      }));

      // 步驟 3：主席整合
      boardPhase = "synthesizing";
      updateWidget();
      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🎯 主席整合報告中...` }], details: { status: "running", phase: "synthesizing" } });

      const synthPrompt = `你是 AI Tools Board 主席，請整合所有委員的研究結果：\n\n研究主題：${brief}\n\n主席框架：${directorFrame}\n\n各委員分析：\n${memberResults.map(r => `=== ${displayName(r.name)} ===\n${r.analysis}`).join("\n\n")}\n\n請生成整合報告（用 ## 標記章節）：\n## 本週關鍵信號\n（3 個最重要的發現）\n\n## 整體觀察\n（全局分析）\n\n## Current System Review\n（現有系統做對了什麼、哪裡過度複雜、哪裡缺失）\n\n## Recommended Architecture\n（最簡單可行架構、平衡版架構、明確不建議做的複雜方案）\n\n## Cost / Performance Tradeoff\n（最省錢方案 / 最平衡方案 / 最強性能方案）\n\n## Adopt Now / Watch / Ignore\n（哪些應立即採用、哪些只觀察、哪些暫時忽略）\n\n## 分歧\n（委員間的主要分歧，如有）\n\n## 下一步行動\n（具體建議 3-5 條）\n\n重要：若沒有明顯證據，不要推薦過度複雜的框架。繁體中文，900字以內。`;

      const synthResult = await runSubagent(directorSystem, synthPrompt, directorModel, "bash,read");
      const memo = synthResult.output;
      boardPhase = "done";
      updateWidget();

      // 儲存報告
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const slug = slugify(brief);
      const memosDir = join(cwd, ".pi", "ai-tools-board", "memos");
      mkdirSync(memosDir, { recursive: true });
      const memoPath = join(memosDir, `${slug}-${timestamp}.md`);
      writeFileSync(memoPath, `# AI Tools Board — ${brief}\n\n**日期：** ${new Date().toLocaleString("zh-TW")}\n**Preset：** ${presetName}\n\n---\n\n## 主席框架\n\n${directorFrame}\n\n---\n\n## 各委員分析\n\n${memberResults.map(r => `### ${displayName(r.name)}\n\n${r.analysis}`).join("\n\n")}\n\n---\n\n## 整合報告\n\n${memo}`);

      const htmlPath = memoPath.replace(/\.md$/, ".html");
      writeFileSync(htmlPath, generateHtmlReport({ date: new Date().toLocaleString("zh-TW"), preset: presetName, memberNames: activeMembers.map(m => m.name), briefText: brief, directorFrame, boardResults: memberResults, memo }));

      return {
        content: [{ type: "text", text: `研究完成！\n\n${memo}\n\n---\n- Memo：${memoPath}\n- HTML：${htmlPath}` }],
        details: { status: "done", preset: presetName, members: activeMembers.length },
      };
    },
  });

  // ── Tool: board_discuss (Mode B) ──────────────────────────────────────────

  pi.registerTool({
    name: "board_discuss",
    label: "Board Discuss",
    description: "開始互動討論模式，用戶作為「人類委員」坐入 AI Tools Board（Mode B）。主席框架後第一位委員發言，之後用 board_next 輪流，board_report 結束。",
    parameters: Type.Object({
      brief: Type.String({ description: "研究主題或問題" }),
      preset: Type.Optional(Type.String({ description: "指定 preset（full/discovery/music/video/coding/github/systems/quick）" })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, ctx) {
      const { brief, preset } = params as { brief: string; preset?: string };
      if (ctx && !widgetCtx) widgetCtx = ctx;
      loadConfig(ctx?.cwd || cwd);

      const presetName = preset || activePreset || "full";
      activePreset = presetName;
      const activeMembers = getActiveMembers(presetName);

      if (activeMembers.length === 0) {
        return { content: [{ type: "text", text: "找不到任何委員。" }], details: { status: "error" } };
      }

      const missingMembers = activeMembers.filter(m => !existsSync(resolve(cwd, m.path)));
      if (missingMembers.length > 0) {
        return { content: [{ type: "text", text: `缺少 agent 檔案：\n${missingMembers.map(m => `  • ${m.name}: ${m.path}`).join("\n")}` }], details: { status: "error" } };
      }

      // Load all member defs
      const memberDefs = new Map<string, MemberDef>();
      for (const member of activeMembers) {
        const def = parseMemberFile(resolve(cwd, member.path));
        if (def) memberDefs.set(member.name, def);
      }

      const directorDef = memberDefs.get("director");
      const directorModel = directorDef?.model || "glm/glm-5-turbo";
      const directorSystem = (directorDef?.systemPrompt || "你是 AI Tools Board 的主席。") + (directorDef ? loadMemberKnowledge(directorDef) : "");

      boardPhase = "framing";
      memberStates = [];
      updateWidget();

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🎯 主席開場框架中...` }], details: { status: "running", phase: "framing" } });

      const nonDirectorMembers = activeMembers.filter(m => m.name !== "director");
      const frameResult = await runSubagent(
        directorSystem,
        `你是 AI Tools Board 主席，開始今天的互動討論。\n\n研究主題：${brief}\n\n請：\n1. 歡迎人類委員加入\n2. 框架今天的核心議題\n3. 說明討論流程\n4. 邀請第一位委員（${displayName(nonDirectorMembers[0]?.name || "...")}）發言\n\n委員陣容：${nonDirectorMembers.map(m => m.name).join(", ")}\n\n繁體中文，親切主持風格，200字以內。`,
        directorModel, "bash,read"
      );

      // 第一位委員發言
      const firstMember = nonDirectorMembers[0];
      const firstDef = firstMember ? memberDefs.get(firstMember.name) : null;
      let firstOutput = "";

      if (firstDef && firstMember) {
        if (onUpdate) onUpdate({ content: [{ type: "text", text: `🔍 ${displayName(firstMember.name)} 發言中...` }], details: { status: "running" } });
        const firstSystem = firstDef.systemPrompt + loadMemberKnowledge(firstDef);
        const firstResult = await runSubagent(
          firstSystem,
          `你正在參加 AI Tools Board 互動討論。\n\n研究主題：${brief}\n\n主席框架：${frameResult.output}\n\n請以 ${displayName(firstDef.name)} 身份發言：提供你領域的最新洞見（需搜尋實際資料）。繁體中文，200-350字。`,
          firstDef.model, firstDef.tools
        );
        firstOutput = firstResult.output;
      }

      const history: DiscussionEntry[] = [
        { speaker: "director", content: frameResult.output, timestamp: Date.now() },
      ];
      if (firstOutput && firstMember) {
        history.push({ speaker: firstMember.name, content: firstOutput, timestamp: Date.now() });
      }

      discussionSession = {
        active: true, brief, directorFrame: frameResult.output, history,
        activeMembers, memberDefs,
        speakOrder: nonDirectorMembers.map(m => m.name),
        nextSpeakerIdx: firstMember ? 1 : 0,
        directorModel, preset: presetName,
      };

      updateWidget();

      const firstMemberSection = firstOutput && firstMember
        ? `\n\n---\n\n**${displayName(firstMember.name)}：**\n\n${firstOutput}`
        : "";

      return {
        content: [{ type: "text", text: `**AI Tools Board 互動討論開始**\n\nPreset：${presetName} | 委員：${activeMembers.map(m => m.name).join(", ")}\n\n---\n\n**主席：**\n\n${frameResult.output}${firstMemberSection}\n\n---\n\n使用 **board_next** 讓下一位委員發言。\n使用 **board_report** 結束討論並生成報告。` }],
        details: { status: "running", phase: "discussing" },
      };
    },
  });

  // ── Tool: board_next ──────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_next",
    label: "Board Next",
    description: "讓下一位（或指定）委員發言。可附上用戶的補充說明。",
    parameters: Type.Object({
      user_input: Type.Optional(Type.String({ description: "用戶的補充說明、問題或觀點（會傳遞給下一位委員）" })),
      member: Type.Optional(Type.String({ description: "指定委員名稱（可選，預設按順序）" })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { user_input, member } = params as { user_input?: string; member?: string };

      if (!discussionSession?.active) {
        return { content: [{ type: "text", text: "目前沒有進行中的互動討論。請先使用 board_discuss 開始。" }], details: { status: "error" } };
      }

      const sess = discussionSession;
      if (user_input) sess.history.push({ speaker: "user", content: user_input, timestamp: Date.now() });

      let nextMemberName: string;
      if (member) {
        nextMemberName = member.toLowerCase().replace(/\s+/g, "-");
      } else {
        if (sess.nextSpeakerIdx >= sess.speakOrder.length) {
          return { content: [{ type: "text", text: "所有委員已發言一輪。請使用 board_report 生成報告，或指定 member 讓特定委員補充。" }], details: { status: "done" } };
        }
        nextMemberName = sess.speakOrder[sess.nextSpeakerIdx];
        sess.nextSpeakerIdx++;
      }

      const def = sess.memberDefs.get(nextMemberName);
      if (!def) {
        return { content: [{ type: "text", text: `找不到委員 "${nextMemberName}"。可用：${[...sess.memberDefs.keys()].join(", ")}` }], details: { status: "error" } };
      }

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🔍 ${displayName(nextMemberName)} 發言中...` }], details: { status: "running" } });

      const systemPrompt = def.systemPrompt + loadMemberKnowledge(def);
      const historyText = formatHistory(sess.history.slice(-8));
      const prompt = `你正在參加 AI Tools Board 互動討論。\n\n研究主題：${sess.brief}\n\n最近討論：\n${historyText}\n\n${user_input ? `人類委員說：${user_input}\n\n` : ""}請以 ${displayName(def.name)} 身份發言，提供洞見或對討論的回應。繁體中文，200-350字，自然對話風格。`;

      const result = await runSubagent(systemPrompt, prompt, def.model, def.tools);
      sess.history.push({ speaker: nextMemberName, content: result.output, timestamp: Date.now() });
      updateWidget();

      return {
        content: [{ type: "text", text: `**${displayName(nextMemberName)}：**\n\n${result.output}` }],
        details: { status: "running", speaker: nextMemberName },
      };
    },
  });

  // ── Tool: board_report ────────────────────────────────────────────────────

  pi.registerTool({
    name: "board_report",
    label: "Board Report",
    description: "結束互動討論，主席整合討論內容生成最終研究報告（.md + .html）。",
    parameters: Type.Object({
      user_final_take: Type.Optional(Type.String({ description: "你作為人類委員的最後總結或觀點（可選，會納入報告）" })),
    }),

    async execute(_toolCallId, params, _signal, onUpdate, _ctx) {
      const { user_final_take } = params as { user_final_take?: string };

      if (!discussionSession?.active) {
        return { content: [{ type: "text", text: "目前沒有進行中的互動討論。請先使用 board_discuss 開始。" }], details: { status: "error" } };
      }

      const sess = discussionSession;
      if (user_final_take?.trim()) {
        sess.history.push({ speaker: "user", content: `【人類委員最終總結】\n${user_final_take.trim()}`, timestamp: Date.now() });
      }

      if (onUpdate) onUpdate({ content: [{ type: "text", text: `🎯 主席整合討論生成報告中...` }], details: { status: "running", phase: "synthesizing" } });

      boardPhase = "synthesizing";
      updateWidget();

      const directorDef = sess.memberDefs.get("director");
      const directorSystem = (directorDef?.systemPrompt || "你是 AI Tools Board 的主席。") + (directorDef ? loadMemberKnowledge(directorDef) : "");
      const historyText = formatHistory(sess.history);

      const synthPrompt = `你是 AI Tools Board 主席，整合以下互動討論生成最終研究報告。\n\n研究主題：${sess.brief}\n\n討論記錄：\n${historyText}\n\n請生成整合報告（用 ## 標記章節）：\n## 本週關鍵信號\n## 整體觀察\n## Current System Review\n## Recommended Architecture\n## Cost / Performance Tradeoff\n## Adopt Now / Watch / Ignore\n## 分歧\n## 下一步行動\n\n重要：若沒有明顯證據，不要推薦過度複雜的框架。繁體中文，900字以內。`;

      const synthResult = await runSubagent(directorSystem, synthPrompt, sess.directorModel, "bash,read");
      const memo = synthResult.output;

      sess.active = false;
      discussionSession = null;
      boardPhase = "done";
      updateWidget();

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const slug = slugify(sess.brief);
      const memosDir = join(cwd, ".pi", "ai-tools-board", "memos");
      mkdirSync(memosDir, { recursive: true });
      const memoPath = join(memosDir, `${slug}-${timestamp}-discussion.md`);
      writeFileSync(memoPath, `# AI Tools Board 討論 — ${sess.brief}\n\n**日期：** ${new Date().toLocaleString("zh-TW")}\n**Preset：** ${sess.preset}\n\n---\n\n## 討論記錄\n\n${historyText}\n\n---\n\n## 整合報告\n\n${memo}`);

      const htmlPath = memoPath.replace(/\.md$/, ".html");
      writeFileSync(htmlPath, generateHtmlReport({
        date: new Date().toLocaleString("zh-TW"), preset: sess.preset,
        memberNames: sess.activeMembers.map(m => m.name), briefText: sess.brief,
        directorFrame: sess.directorFrame,
        boardResults: sess.speakOrder.map(name => ({
          name, error: false,
          analysis: sess.history.filter(e => e.speaker === name).map(e => e.content).join("\n\n"),
        })),
        memo,
      }));

      return {
        content: [{ type: "text", text: `**討論報告已生成！**\n\n${memo}\n\n---\n- Memo：${memoPath}\n- HTML：${htmlPath}` }],
        details: { status: "done" },
      };
    },
  });
}
