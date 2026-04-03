/**
 * Football Betting Board Member Session — 與 AI 工具委員會個別成員一對一深度對話
 *
 * 從 ai-tools-board config.yaml 讀取成員列表，讓用戶選擇單一成員進行
 * 一對一會話。成員有完整的 read/write/edit/bash 工具，可透過聊天更新自己的
 * 個人知識庫（.pi/football-betting-board/agents/<name>/<name>-knowledge.md）。
 *
 * Commands:
 *   /member-select [name]    — 選擇或切換對話成員（互動選單）
 *   /member-status           — 顯示當前成員資訊和知識庫狀態
 *   /member-equip <skill>    — 將 skill 用法寫入成員知識庫
 *   /member-learn <url>      — 從 URL 學習並更新個人知識庫
 *   /member-meeting [preset] — 召開董事會，與其他成員一起分析（可選 preset：full, pre-match, live, value-scan, quick）
 *
 * Usage: pi -e extensions/boards/fb-board-member-session.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { truncateToWidth } from "@mariozechner/pi-tui";
import { readFileSync, existsSync, writeFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { homedir } from "os";
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
  description: string;
  systemPrompt: string;
  model: string;
  tools: string[];
  knowledgePath: string;
  sourcesPath: string;
}

interface SkillInfo {
  name: string;
  description: string;
  dir: string;
  mdPath: string;
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
    }
    if (section === "presets" && inPresets) {
      const m = line.match(/^\s+(\w[\w-]*):\s*\[(.+)\]/);
      if (m) config.presets[m[1].trim()] = m[2].split(",").map(s => s.trim()).filter(Boolean);
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
    const knowledgePath = join(dirname(filePath), `${name}-knowledge.md`);
    const sourcesPath = join(dirname(filePath), `${name}-sources.md`);
    return {
      name,
      description: fm["description"] || "",
      systemPrompt: body,
      model: fm["model"] || "",
      tools: fm["tools"] ? fm["tools"].split(",").map(t => t.trim()).filter(Boolean) : [],
      knowledgePath,
      sourcesPath,
    };
  } catch { return null; }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function displayName(name: string): string {
  return name.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function ensureKnowledgeFile(member: MemberDef): void {
  if (!existsSync(member.knowledgePath)) {
    writeFileSync(member.knowledgePath, `# ${displayName(member.name)} — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 ${member.name}-sources.md。
> 使用 edit 工具更新此文件。

## 追蹤的賽事與博彩數據

（尚未記錄）

## 核心分析框架

（尚未記錄）

## 重要發現與洞見

（尚未記錄）

## 分析過的賽事記錄

| 日期 | 賽事 | 聯賽 | 建議 | 結果 |
|------|------|------|------|------|

## 裝備的技能

（尚未記錄）
`, "utf-8");
  }

  if (!existsSync(member.sourcesPath)) {
    writeFileSync(member.sourcesPath, `# ${displayName(member.name)} — 來源登記表

> 學習來源索引。knowledge.md 中的 [src:NNN] 對應此表的 ID 欄。
> 此檔不會自動注入 context，需要溯源時自行 read。

| ID | 日期 | 類型 | 來源 URL | 說明 |
|----|------|------|----------|------|
`, "utf-8");
  }
}

function scanSkills(cwdRef: string): SkillInfo[] {
  const skillDirs = [join(cwdRef, ".claude/skills"), join(homedir(), ".claude/skills")];
  const seen = new Set<string>();
  const skills: SkillInfo[] = [];
  for (const base of skillDirs) {
    if (!existsSync(base)) continue;
    try {
      for (const name of readdirSync(base)) {
        if (seen.has(name)) continue;
        const dir = join(base, name);
        const mdFiles = readdirSync(dir).filter(f => f.endsWith(".md"));
        if (mdFiles.length === 0) continue;
        const mdPath = join(dir, mdFiles[0]);
        const raw = readFileSync(mdPath, "utf-8");
        const descMatch = raw.match(/^description:\s*(.+)$/m);
        const description = descMatch ? descMatch[1].trim().split(".")[0] : "";
        seen.add(name);
        skills.push({ name, description, dir, mdPath });
      }
    } catch { }
  }
  return skills;
}

async function equipSkill(member: MemberDef, skill: SkillInfo, ctx: ExtensionContext): Promise<void> {
  const skillContent = readFileSync(skill.mdPath, "utf-8");
  const bashBlocks: string[] = [];
  const bashRe = /```bash\n([\s\S]*?)```/g;
  let m: RegExpExecArray | null;
  while ((m = bashRe.exec(skillContent)) !== null) bashBlocks.push(m[1].trim());

  const usageSection = bashBlocks.length > 0
    ? `\`\`\`bash\n${bashBlocks.slice(0, 3).join("\n\n")}\n\`\`\``
    : skillContent.slice(0, 800);

  const entry = `\n## 技能裝備：${skill.name}\n\n> 裝備於 ${new Date().toISOString().slice(0, 10)}\n\n**描述：** ${skill.description}\n\n**使用方式：**\n${usageSection}\n`;

  const current = existsSync(member.knowledgePath) ? readFileSync(member.knowledgePath, "utf-8") : "";
  if (current.includes(`技能裝備：${skill.name}`)) {
    ctx.ui.notify(`${skill.name} 已在知識庫中，跳過`, "info");
    return;
  }

  writeFileSync(member.knowledgePath, current + entry, "utf-8");
  ctx.ui.notify(`已將 ${skill.name} 裝備到 ${displayName(member.name)} 的知識庫`, "success");
}

// ── Module State ──────────────────────────────────────────────────────────────

let activeMember: MemberDef | null = null;
let boardConfig: BoardConfig | null = null;
let defaultTools: string[] = [];
let cwdRef = "";

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Roster Widget ──────────────────────────────────────────────────────────

  function showRosterWidget(ctx: ExtensionContext): void {
    if (!boardConfig) return;
    ctx.ui.setWidget(
      "member-roster",
      (_tui, theme) => {
        const lines: string[] = [];
        lines.push(theme.fg("accent", theme.bold("  Football Betting Board  ")) + theme.fg("dim", `(${boardConfig!.board.length} 位成員)`));
        lines.push(theme.fg("dim", "  " + "─".repeat(50)));
        for (const m of boardConfig!.board) {
          const def = parseMemberFile(join(cwdRef, m.path));
          const isActive = activeMember?.name === m.name;
          const kbMark = def && existsSync(def.knowledgePath) ? theme.fg("success", "📚") : theme.fg("muted", " ○");
          const nameStr = isActive
            ? theme.fg("accent", theme.bold(`  ${m.name}`))
            : theme.fg("dim", `  ${m.name}`);
          const desc = def?.description ? theme.fg("muted", `  —  ${def.description.split("—")[1]?.trim() ?? def.description.split("—")[0]?.trim()}`) : "";
          lines.push(`  ${kbMark} ${nameStr}${desc}`);
        }
        lines.push(theme.fg("dim", "  " + "─".repeat(50)));
        lines.push(theme.fg("muted", "  /member-select  ·  /member-equip <skill>  ·  /member-learn <url>"));
        return {
          render(width: number) { return lines.map(l => truncateToWidth(l, width)); },
          invalidate() { },
        };
      },
      { placement: "belowEditor", dismissAfter: 8000 }
    );
  }

  // ── Footer ─────────────────────────────────────────────────────────────────

  function renderFooter(tui: any, theme: any, footerData: any) {
    return {
      dispose: footerData.onBranchChange(() => tui.requestRender()),
      invalidate() { },
      render(width: number): string[] {
        const prefix = theme.fg("dim", "[ Football Betting Board · Member ]  ");
        if (!activeMember) {
          return [truncateToWidth(prefix + theme.fg("muted", "未選擇成員 — 使用 /member-select"), width)];
        }
        const namePart = theme.fg("accent", theme.bold(displayName(activeMember.name)));
        const descPart = theme.fg("dim", `  ${activeMember.description.split("—")[0]?.trim() || ""}`);
        const kbMark = existsSync(activeMember.knowledgePath) ? theme.fg("success", " ●") : theme.fg("muted", " ○");
        return [truncateToWidth(prefix + namePart + descPart + theme.fg("muted", ` kb${kbMark}`), width)];
      },
    };
  }

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    cwdRef = ctx.cwd;
    defaultTools = pi.getActiveTools();

    const configPath = join(ctx.cwd, ".pi/football-betting-board/config.yaml");
    if (existsSync(configPath)) {
      boardConfig = parseBoardConfigYaml(readFileSync(configPath, "utf-8"));
    } else {
      ctx.ui.notify("找不到 .pi/football-betting-board/config.yaml", "warning");
    }

    ctx.ui.setStatus("member-session", "成員：未選擇");
    ctx.ui.setFooter(renderFooter);

    // Auto-select from env var (e.g. BOARD_MEMBER=coding-ai-scout)
    const envMember = process.env.BOARD_MEMBER;
    if (envMember && boardConfig) {
      const matched = boardConfig.board.find(m => m.name === envMember || m.name.startsWith(envMember));
      if (matched) {
        const member = parseMemberFile(join(cwdRef, matched.path));
        if (member) {
          activeMember = member;
          ensureKnowledgeFile(member);
          pi.setActiveTools(["read", "write", "edit", "bash", "grep", "find"]);
          ctx.ui.setStatus("member-session", `成員：${displayName(member.name)}`);
          showRosterWidget(ctx);
          ctx.ui.notify(`已自動載入成員：${displayName(member.name)}`, "success");
          return;
        }
      }
      ctx.ui.notify(`BOARD_MEMBER="${envMember}" 找不到對應成員`, "warning");
    }

    showRosterWidget(ctx);
  });

  // ── Inject Member System Prompt ────────────────────────────────────────────

  pi.on("before_agent_start", async (event, _ctx) => {
    if (!activeMember) return;

    const knowledgeContent = existsSync(activeMember.knowledgePath)
      ? readFileSync(activeMember.knowledgePath, "utf-8")
      : "（尚未建立）";

    const knowledgeSection = `

---

## 你的個人知識庫

路徑：\`${activeMember.knowledgePath}\`

目前內容：
\`\`\`markdown
${knowledgeContent}
\`\`\`

**這是你在會話之間的持久記憶。** 你可以隨時用 \`edit\` 工具更新此文件，記錄：
- 你追蹤的賽事、聯賽、博彩市場的最新洞見
- 你識別的 value bet 機會與賠率異動（附日期）
- Poisson 模型參數、Kelly 倉位校正記錄
- 值得持續監察的博彩平台賠率差異

每次對話結束時，主動問用戶是否有新的博彩洞見值得寫入知識庫。
`;

    return {
      systemPrompt: activeMember.systemPrompt + knowledgeSection + "\n\n" + event.systemPrompt,
    };
  });

  // ── /member-select ─────────────────────────────────────────────────────────

  pi.registerCommand("member-select", {
    description: "選擇或切換對話的委員會成員（可帶名稱：/member-select coding-ai-scout）",
    handler: async (args, ctx) => {
      if (!boardConfig) { ctx.ui.notify("博彩板設定未載入", "error"); return; }

      const argName = args?.trim();
      if (argName) {
        const matched = boardConfig.board.find(m => m.name === argName || m.name.startsWith(argName));
        if (matched) {
          const member = parseMemberFile(join(cwdRef, matched.path));
          if (member) {
            activeMember = member;
            ensureKnowledgeFile(member);
            pi.setActiveTools(["read", "write", "edit", "bash", "grep", "find"]);
            ctx.ui.setStatus("member-session", `成員：${displayName(member.name)}`);
            ctx.ui.notify(`已切換至：${displayName(member.name)}\n知識庫：${member.knowledgePath}`, "success");
            return;
          }
        }
        ctx.ui.notify(`找不到成員：${argName}`, "warning");
      }

      const options = [
        "（清除 — 回到預設模式）",
        ...boardConfig.board.map(m => {
          const def = parseMemberFile(join(cwdRef, m.path));
          const desc = def?.description ?? "";
          const kbMark = def && existsSync(def.knowledgePath) ? "📚" : "○";
          return `${kbMark}  ${m.name}  —  ${desc}`;
        }),
      ];

      const choice = await ctx.ui.select("選擇足球博彩情報中心成員", options);
      if (choice === undefined) return;

      if (choice === options[0]) {
        activeMember = null;
        pi.setActiveTools(defaultTools);
        ctx.ui.setStatus("member-session", "成員：未選擇");
        ctx.ui.notify("已清除成員，回到預設模式", "info");
        return;
      }

      const idx = options.indexOf(choice) - 1;
      const memberConfig = boardConfig.board[idx];
      const member = parseMemberFile(join(cwdRef, memberConfig.path));
      if (!member) { ctx.ui.notify(`無法載入成員文件：${memberConfig.path}`, "error"); return; }

      activeMember = member;
      ensureKnowledgeFile(member);
      pi.setActiveTools(["read", "write", "edit", "bash", "grep", "find"]);
      ctx.ui.setStatus("member-session", `成員：${displayName(member.name)}`);
      ctx.ui.notify(`已切換至：${displayName(member.name)}\n知識庫：${member.knowledgePath}`, "success");
    },
  });

  // ── /member-status ─────────────────────────────────────────────────────────

  pi.registerCommand("member-status", {
    description: "顯示當前選中的成員和知識庫狀態",
    handler: async (_args, ctx) => {
      if (!activeMember) {
        ctx.ui.notify("目前沒有選擇成員。使用 /member-select 選擇。", "warning");
        return;
      }
      const kbExists = existsSync(activeMember.knowledgePath) ? "存在 ✓" : "尚未建立";
      ctx.ui.notify([
        `成員：${displayName(activeMember.name)}`,
        `描述：${activeMember.description}`,
        `模型：${activeMember.model || "預設"}`,
        `工具：${activeMember.tools.join(", ")}`,
        `知識庫：${activeMember.knowledgePath}（${kbExists}）`,
      ].join("\n"), "info");
    },
  });

  // ── /member-equip ──────────────────────────────────────────────────────────

  pi.registerCommand("member-equip", {
    description: "將 skill 的使用方法寫入成員知識庫（/member-equip wsp-v3）",
    handler: async (args, ctx) => {
      if (!activeMember) { ctx.ui.notify("請先用 /member-select 選擇成員", "warning"); return; }

      const skills = scanSkills(cwdRef);
      const argSkill = args?.trim();

      if (!argSkill) {
        if (skills.length === 0) { ctx.ui.notify("找不到任何 skill", "warning"); return; }
        const options = skills.map(s => `${s.name}  —  ${s.description}`);
        const choice = await ctx.ui.select("選擇要裝備的 Skill", options);
        if (!choice) return;
        await equipSkill(activeMember, skills[options.indexOf(choice)], ctx);
        return;
      }

      const matched = skills.find(s => s.name === argSkill || s.name.startsWith(argSkill));
      if (!matched) {
        ctx.ui.notify(`找不到 skill：${argSkill}\n可用：${skills.map(s => s.name).join(", ")}`, "warning");
        return;
      }
      await equipSkill(activeMember, matched, ctx);
    },
  });

  // ── /member-learn ──────────────────────────────────────────────────────────

  pi.registerCommand("member-learn", {
    description: "從 URL（YouTube / 文章 / GitHub）學習並更新個人知識庫（/member-learn <url>）",
    handler: async (args, ctx) => {
      if (!activeMember) { ctx.ui.notify("請先用 /member-select 選擇成員", "warning"); return; }
      const url = args?.trim();
      if (!url) { ctx.ui.notify("用法：/member-learn <url>", "warning"); return; }

      const today = new Date().toISOString().slice(0, 10);
      const learnPrompt = [
        `請從以下來源學習，並按格式更新兩個檔案：`,
        ``,
        `URL：${url}`,
        ``,
        `## 步驟一：取得內容`,
        `用 bash 執行：`,
        `  summarize "${url}" --youtube auto`,
        `（若非 YouTube，去掉 --youtube auto）`,
        ``,
        `## 步驟二：先查 sources.md 取得下一個 ID`,
        `用 bash 執行：`,
        `  grep -c "^|" ${activeMember.sourcesPath}`,
        `（減去 header 行得到當前筆數，新 ID = 筆數 + 1，格式 src:001）`,
        ``,
        `## 步驟三：追加到 knowledge.md（${activeMember.knowledgePath}）`,
        `用 edit 工具，在最相關的 section 下追加：`,
        ``,
        `  ### <標題> [src:NNN]`,
        `  - 核心洞見 1（與你職責直接相關）`,
        `  - 核心洞見 2`,
        `  - 對我分析框架的啟發：<一句話>`,
        ``,
        `只保留與你職責（${displayName(activeMember.name)}）直接相關的內容，3-5 點即可。`,
        ``,
        `## 步驟四：追加到 sources.md（${activeMember.sourcesPath}）`,
        `用 edit 工具，在表格末尾加一行：`,
        ``,
        `  | src:NNN | ${today} | <YouTube/GitHub/Article> | ${url} | <一句描述> |`,
        ``,
        `完成後告訴我學到了什麼（一段話）。`,
      ].join("\n");

      ctx.ui.notify(
        `已為 ${displayName(activeMember.name)} 準備學習任務\n請將以下訊息發送給成員：\n\n${learnPrompt}`,
        "info"
      );
    },
  });

  // ── /member-meeting ─────────────────────────────────────────────────────────

  pi.registerCommand("member-meeting", {
    description: "召開足球博彩情報中心董事會（/member-meeting [preset]）",
    handler: async (args, ctx) => {
      if (!activeMember) { ctx.ui.notify("請先用 /member-select 選擇成員", "warning"); return; }
      if (!boardConfig) { ctx.ui.notify("博彩板設定未載入", "error"); return; }

      const presetName = args?.trim() || "full";
      const memberNames = boardConfig.presets[presetName] || boardConfig.presets["full"];

      if (!memberNames || memberNames.length === 0) {
        ctx.ui.notify(`找不到 preset：${presetName}，可用：${Object.keys(boardConfig.presets).join(", ")}`, "error");
        return;
      }

      // Get member definitions for the meeting
      const meetingMembers = memberNames
        .map(name => {
          const config = boardConfig!.board.find(m => m.name === name);
          if (!config) return null;
          return parseMemberFile(join(cwdRef, config.path));
        })
        .filter((m): m is MemberDef => m !== null);

      if (meetingMembers.length === 0) {
        ctx.ui.notify("無法載入任何成員定義", "error");
        return;
      }

      // Build meeting prompt
      const meetingPrompt = [
        `## 足球博彩情報中心董事會 — ${presetName.toUpperCase()} 模式`,
        ``,
        `### 召集人`,
        `${displayName(activeMember.name)} — ${activeMember.description}`,
        ``,
        `### 與會成員（${meetingMembers.length} 人）`,
        ...meetingMembers.map(m => `- ${displayName(m.name)}：${m.description}`),
        ``,
        `### 會議流程`,
        `1. **召集人開場** — 說明分析目標（指定賽事/市場問題）`,
        `2. **各成員輪流發言** — 按專業領域提供分析：`,
        `   - Data Scout：球員數據、FC26 屬性`,
        `   - Form Analyst：近期狀態、傷兵、主客場`,
        `   - Stats Modeler：Poisson 模型、xG、勝率`,
        `   - Odds Tracker：賠率走勢、平台差異`,
        `   - Market Intel：市場情報、資金流向`,
        `   - Value Hunter：價值機會、正 EV`,
        `   - Risk Manager：風險評估、倉位建議`,
        `3. **召集人總結** — 綜合各方分析，給出最終投注建議`,
        ``,
        `### 輸出格式`,
        `請生成一份完整的博彩分析報告，包含：`,
        `- 賽事概述`,
        `- 數據分析（各成員專業見解）`,
        `- 投注建議（標注信心指數 1-5⭐）`,
        `- 風險提示`,
        `- 參考來源`,
        ``,
        `請召集人（${displayName(activeMember.name)}）開始會議，指定要分析的賽事或市場問題。`,
      ].join("\n");

      ctx.ui.setWidget(
        "member-meeting",
        (_tui, theme) => {
          const lines: string[] = [];
          lines.push(theme.fg("accent", theme.bold("  Football Betting Board Meeting  ")));
          lines.push(theme.fg("dim", `  Mode: ${presetName} | Members: ${meetingMembers.length}`));
          lines.push(theme.fg("dim", "  " + "─".repeat(50)));
          meetingMembers.forEach((m, i) => {
            const marker = m.name === activeMember!.name ? theme.fg("accent", "▶") : theme.fg("dim", "○");
            lines.push(`  ${marker} ${displayName(m.name)}`);
          });
          lines.push(theme.fg("dim", "  " + "─".repeat(50)));
          lines.push(theme.fg("muted", "  會議已開始 — 請召集人指定分析目標"));
          return {
            render(width: number) { return lines.map(l => truncateToWidth(l, width)); },
            invalidate() { },
          };
        },
        { placement: "belowEditor", dismissAfter: 10000 }
      );

      ctx.ui.notify(meetingPrompt, "info");
    },
  });
}
