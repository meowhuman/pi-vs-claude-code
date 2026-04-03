/**
 * Intel Board — 三位共享專家戰略情報系統
 *
 * 三位跨域情報專家（地緣政治 + 全球市場 + 軍事戰略）並行分析，
 * 輸出合併情報備忘錄。支援一對一模式（/select）直接與單一專家深入對話。
 *
 * Config: .pi/intel-board/config.yaml
 * Agents: .pi/meta-orchestrator/agents/<name>/
 * Memos:  .pi/intel-board/memos/
 *
 * Commands:
 *   /select [name]      — 選擇專家進行 1-on-1（無參數 = 選單；再次呼叫回群組模式）
 *   /intel-preset [name]— 切換專家組合（full / geo-markets / geo-military / markets-military）
 *   /intel-status       — 顯示當前模式與活躍專家
 *
 * Tools:
 *   intel_brief  — 提交問題 → 三位專家並行分析 → 合併情報備忘錄（.md 輸出）
 *
 * Usage: pi -e extensions/boards/intel-board.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { truncateToWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { readFileSync, existsSync, writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ExpertConfig {
  name: string;
  path: string;
  active: boolean;
}

interface BoardConfig {
  meeting: { discussion_time_minutes: number };
  board: ExpertConfig[];
  presets: Record<string, string[]>;
}

interface ExpertDef {
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  knowledgePath: string;
}

interface RunResult {
  output: string;
  exitCode: number;
  elapsed: number;
}

// ── YAML Parser ───────────────────────────────────────────────────────────────

function parseConfigYaml(raw: string): BoardConfig {
  const config: BoardConfig = { meeting: { discussion_time_minutes: 10 }, board: [], presets: {} };
  const lines = raw.split("\n");
  let section = "";
  let inItem = false;
  let cur: Partial<ExpertConfig> = {};

  const flush = () => {
    if (inItem && cur.name) {
      config.board.push({ name: cur.name!, path: cur.path || "", active: cur.active !== false });
    }
    cur = {}; inItem = false;
  };

  for (const line of lines) {
    if (line.match(/^meeting:/)) { flush(); section = "meeting"; continue; }
    if (line.match(/^damage_control:/)) { flush(); section = "damage_control"; continue; }
    if (line.match(/^board:/)) { flush(); section = "board"; continue; }
    if (line.match(/^presets:/)) { flush(); section = "presets"; continue; }

    if (section === "meeting") {
      const m = line.match(/^\s+discussion_time_minutes:\s*(\d+)/);
      if (m) config.meeting.discussion_time_minutes = parseInt(m[1], 10);
      continue;
    }
    if (section === "board") {
      if (line.match(/^\s+-\s+name:/)) {
        flush(); inItem = true;
        const m = line.match(/^\s+-\s+name:\s*(.+)$/);
        if (m) cur.name = m[1].trim();
        continue;
      }
      if (inItem) {
        const pm = line.match(/^\s+path:\s*(.+)$/);
        if (pm) { cur.path = pm[1].trim(); continue; }
        const am = line.match(/^\s+active:\s*(true|false)/);
        if (am) { cur.active = am[1] === "true"; continue; }
      }
    }
    if (section === "presets") {
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) config.presets[m[1].trim()] = m[2].split(",").map(s => s.trim()).filter(Boolean);
    }
  }
  flush();
  return config;
}

// ── Agent File Parser ─────────────────────────────────────────────────────────

function parseExpertFile(filePath: string): ExpertDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    const fm: Record<string, string> = {};
    let body = raw;
    if (match) {
      for (const line of match[1].split("\n")) {
        const idx = line.indexOf(":");
        if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
      body = match[2].trim();
    }
    const name = fm["name"] || filePath;
    return {
      name,
      description: fm["description"] || "",
      systemPrompt: body,
      model: fm["model"] || "kimi-coding/k2p5",
      knowledgePath: join(dirname(filePath), `${name}-knowledge.md`),
    };
  } catch { return null; }
}

function loadKnowledge(expert: ExpertDef): string {
  if (!existsSync(expert.knowledgePath)) return "";
  const content = readFileSync(expert.knowledgePath, "utf-8").trim();
  return content ? `\n\n## ${expert.name} 個人知識庫\n\n${content}` : "";
}

function displayName(name: string): string {
  return name.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^\w\u4e00-\u9fff\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 50);
}

// ── Subprocess Runner ─────────────────────────────────────────────────────────

function runExpert(
  systemPrompt: string,
  prompt: string,
  model: string,
  onChunk?: (text: string) => void,
): Promise<RunResult> {
  const args = [
    "--mode", "json",
    "-p",
    "--no-extensions",
    "--model", model,
    "--tools", "none",
    "--thinking", "off",
    "--append-system-prompt", systemPrompt,
    "--no-session",
    prompt,
  ];

  const chunks: string[] = [];
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
              chunks.push(t);
              if (onChunk) onChunk(t);
            }
          }
        } catch { }
      }
    });

    const stderrChunks: string[] = [];
    proc.stderr!.setEncoding("utf-8");
    proc.stderr!.on("data", (c: string) => stderrChunks.push(c));

    proc.on("close", (code) => {
      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer);
          if (event.type === "message_update") {
            const d = event.assistantMessageEvent;
            if (d?.type === "text_delta") chunks.push(d.delta || "");
          }
        } catch { }
      }
      resolve({
        output: chunks.join("") || stderrChunks.join("").trim(),
        exitCode: code ?? 1,
        elapsed: Date.now() - startTime,
      });
    });

    proc.on("error", (err) => {
      resolve({ output: `Error: ${err.message}`, exitCode: 1, elapsed: Date.now() - startTime });
    });
  });
}

// ── Module State ──────────────────────────────────────────────────────────────

let boardConfig: BoardConfig | null = null;
let activePreset: string = "full";
let activeExpert: ExpertDef | null = null; // null = group mode
let cwdRef = "";

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Footer ─────────────────────────────────────────────────────────────────

  function renderFooter(tui: any, theme: any, footerData: any) {
    return {
      dispose: footerData.onBranchChange(() => tui.requestRender()),
      invalidate() { },
      render(width: number): string[] {
        const prefix = theme.fg("dim", "[ Intel Board ]  ");
        if (activeExpert) {
          const name = theme.fg("accent", theme.bold(displayName(activeExpert.name)));
          const desc = theme.fg("dim", `  ${activeExpert.description.split("—")[0]?.trim()}`);
          const kb = existsSync(activeExpert.knowledgePath) ? theme.fg("success", " ●") : theme.fg("muted", " ○");
          return [truncateToWidth(prefix + theme.fg("muted", "1-on-1 ▸ ") + name + desc + theme.fg("muted", ` kb${kb}`), width)];
        }
        if (!boardConfig) {
          return [truncateToWidth(prefix + theme.fg("error", "config 未載入"), width)];
        }
        const activeMembers = getActiveMembers();
        const names = activeMembers.map(e => theme.fg("accent", e.name.split("-")[0])).join(theme.fg("dim", " · "));
        const preset = theme.fg("muted", `[${activePreset}] `);
        return [truncateToWidth(prefix + theme.fg("muted", "GROUP ▸ ") + preset + names + theme.fg("dim", "  /select 切換 1-on-1"), width)];
      },
    };
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getActiveMembers(): ExpertDef[] {
    if (!boardConfig) return [];
    const presetNames = boardConfig.presets[activePreset] ?? boardConfig.board.filter(b => b.active).map(b => b.name);
    return presetNames.flatMap(name => {
      const cfg = boardConfig!.board.find(b => b.name === name);
      if (!cfg) return [];
      const def = parseExpertFile(join(cwdRef, cfg.path));
      return def ? [def] : [];
    });
  }

  function saveMemo(slug: string, content: string): string {
    const memosDir = join(cwdRef, ".pi/intel-board/memos");
    mkdirSync(memosDir, { recursive: true });
    const ts = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
    const filename = `${slug}-${ts}.md`;
    const path = join(memosDir, filename);
    writeFileSync(path, content, "utf-8");
    return path;
  }

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    cwdRef = ctx.cwd;

    const configPath = join(ctx.cwd, ".pi/intel-board/config.yaml");
    if (existsSync(configPath)) {
      boardConfig = parseConfigYaml(readFileSync(configPath, "utf-8"));
    } else {
      ctx.ui.notify("找不到 .pi/intel-board/config.yaml", "error");
    }

    ctx.ui.setStatus("intel-board", "GROUP MODE");
    ctx.ui.setFooter(renderFooter);
    ctx.ui.notify("Intel Board 已載入\n使用 intel_brief 開始群組分析，/select 切換 1-on-1", "info");
  });

  // ── 1-on-1: Inject Expert System Prompt ───────────────────────────────────

  pi.on("before_agent_start", async (event, _ctx) => {
    if (!activeExpert) return;
    const knowledge = loadKnowledge(activeExpert);
    const knowledgeSection = knowledge ? `\n\n---\n\n## 你的個人知識庫\n\n路徑：\`${activeExpert.knowledgePath}\`\n\n${knowledge}\n\n**這是你在會話之間的持久記憶。** 用 \`edit\` 工具更新此文件，記錄重要洞見和追蹤事件。` : "";
    return {
      systemPrompt: activeExpert.systemPrompt + knowledgeSection + "\n\n" + event.systemPrompt,
    };
  });

  // ── Tool: intel_brief ──────────────────────────────────────────────────────

  pi.registerTool("intel_brief", {
    description: "提交情報問題 → 所有活躍專家並行分析 → 輸出合併情報備忘錄（.md 檔案）",
    inputSchema: Type.Object({
      brief: Type.String({ description: "問題、局勢描述或分析請求（支援多行）。切換專家組合請先用 /intel-preset 指令。" }),
    }),
    handler: async ({ brief }, ctx) => {
      if (!boardConfig) return "config 未載入，請重啟";

      const members = getActiveMembers();
      if (members.length === 0) return "沒有活躍的專家，請檢查 config 或更換 preset";

      const slug = slugify(brief);
      const startTime = Date.now();

      ctx.ui.notify(`Intel Brief 開始\n專家：${members.map(m => displayName(m.name)).join(" · ")}\n問題：${brief.slice(0, 80)}`, "info");

      // ── Parallel expert runs ───────────────────────────────────────────────
      const prompt = `以下是情報簡報任務：\n\n${brief}\n\n請按照你的分析格式輸出完整分析。`;

      const results = await Promise.all(
        members.map(async (expert) => {
          ctx.ui.setStatus("intel-board", `分析中：${displayName(expert.name)}…`);
          const systemPrompt = expert.systemPrompt + loadKnowledge(expert);
          const result = await runExpert(systemPrompt, prompt, expert.model);
          return { expert, result };
        })
      );

      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      // ── Compile memo ───────────────────────────────────────────────────────
      const ts = new Date().toISOString().slice(0, 10);
      const sections = results.map(({ expert, result }) => {
        const header = `## ${displayName(expert.name)}`;
        const body = result.exitCode !== 0
          ? `⚠️ 分析失敗 (exit ${result.exitCode})\n\n${result.output.slice(0, 300)}`
          : result.output;
        return `${header}\n\n${body}`;
      }).join("\n\n---\n\n");

      const memo = `# Intel Brief — ${ts}

**Brief：** ${brief}

**Preset：** ${activePreset} (${members.map(m => displayName(m.name)).join(", ")})

**耗時：** ${elapsed}s

---

${sections}
`;

      const memoPath = saveMemo(slug, memo);
      ctx.ui.setStatus("intel-board", "GROUP MODE");
      ctx.ui.notify(`Intel Brief 完成 (${elapsed}s)\n備忘錄：${memoPath}`, "success");

      return `Intel Brief 已完成。備忘錄儲存至：${memoPath}\n\n---\n\n${memo}`;
    },
  });

  // ── /select ────────────────────────────────────────────────────────────────

  pi.registerCommand("select", {
    description: "選擇專家進行 1-on-1 對話（/select <name> 或選單）；無參數或 /select off 返回群組模式",
    handler: async (args, ctx) => {
      if (!boardConfig) { ctx.ui.notify("config 未載入", "error"); return; }

      const arg = args?.trim().toLowerCase();

      // Return to group mode
      if (!arg || arg === "off" || arg === "group") {
        activeExpert = null;
        ctx.ui.setStatus("intel-board", "GROUP MODE");
        ctx.ui.notify("已切換回群組模式", "info");
        return;
      }

      // Try direct name match
      const allExperts = boardConfig.board.flatMap(cfg => {
        const def = parseExpertFile(join(cwdRef, cfg.path));
        return def ? [def] : [];
      });

      const matched = allExperts.find(e => e.name === arg || e.name.startsWith(arg) || e.name.includes(arg));
      if (matched) {
        activeExpert = matched;
        ctx.ui.setStatus("intel-board", `1-on-1: ${displayName(matched.name)}`);
        ctx.ui.notify(`已切換至 1-on-1：${displayName(matched.name)}\n知識庫：${matched.knowledgePath}\n\n/select off 返回群組模式`, "success");
        return;
      }

      // Interactive select menu
      const options = [
        "↩ 群組模式（GROUP）",
        ...allExperts.map(e => {
          const kb = existsSync(e.knowledgePath) ? "📚" : "○";
          return `${kb}  ${e.name}  —  ${e.description.split("—")[0]?.trim()}`;
        }),
      ];

      const choice = await ctx.ui.select("選擇 Intel Board 專家", options);
      if (choice === undefined) return;

      if (choice === options[0]) {
        activeExpert = null;
        ctx.ui.setStatus("intel-board", "GROUP MODE");
        ctx.ui.notify("已切換回群組模式", "info");
        return;
      }

      const idx = options.indexOf(choice) - 1;
      activeExpert = allExperts[idx];
      ctx.ui.setStatus("intel-board", `1-on-1: ${displayName(activeExpert.name)}`);
      ctx.ui.notify(`已切換至 1-on-1：${displayName(activeExpert.name)}\n\n/select off 返回群組模式`, "success");
    },
  });

  // ── /intel-preset ──────────────────────────────────────────────────────────

  pi.registerCommand("intel-preset", {
    description: "切換專家組合：full | geo-markets | geo-military | markets-military",
    handler: async (args, ctx) => {
      if (!boardConfig) { ctx.ui.notify("config 未載入", "error"); return; }

      const arg = args?.trim();
      if (arg && boardConfig.presets[arg]) {
        activePreset = arg;
        const names = boardConfig.presets[arg].map(displayName).join(", ");
        ctx.ui.notify(`Preset 已切換：${arg}\n成員：${names}`, "success");
        return;
      }

      // Interactive preset selection
      const presetNames = Object.keys(boardConfig.presets);
      const options = presetNames.map(p => {
        const names = boardConfig!.presets[p].map(displayName).join(", ");
        const marker = p === activePreset ? "▶ " : "  ";
        return `${marker}${p}  —  ${names}`;
      });

      const choice = await ctx.ui.select("選擇 Intel Board Preset", options);
      if (choice === undefined) return;

      const idx = options.indexOf(choice);
      activePreset = presetNames[idx];
      const names = boardConfig.presets[activePreset].map(displayName).join(", ");
      ctx.ui.notify(`Preset 已切換：${activePreset}\n成員：${names}`, "success");
    },
  });

  // ── /intel-status ──────────────────────────────────────────────────────────

  pi.registerCommand("intel-status", {
    description: "顯示 Intel Board 當前狀態",
    handler: async (_args, ctx) => {
      if (!boardConfig) { ctx.ui.notify("config 未載入", "error"); return; }

      const mode = activeExpert ? `1-on-1 ▸ ${displayName(activeExpert.name)}` : `GROUP MODE (preset: ${activePreset})`;
      const members = getActiveMembers();
      const memberList = members.map(e => {
        const kb = existsSync(e.knowledgePath) ? "📚" : "○";
        return `  ${kb} ${displayName(e.name)}`;
      }).join("\n");

      ctx.ui.notify(
        `Intel Board 狀態\n模式：${mode}\n\n活躍專家：\n${memberList}\n\n指令：intel_brief · /select · /intel-preset`,
        "info"
      );
    },
  });
}
