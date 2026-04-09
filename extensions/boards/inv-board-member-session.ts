/**
 * Inv Board Member Session — 與投資委員會個別成員一對一深度對話
 *
 * 從 investment-adviser-board config.yaml 讀取成員列表，讓用戶選擇單一成員進行
 * 一對一會話。成員有完整的 read/write/edit/bash 工具，可透過聊天更新自己的
 * 個人知識庫（.pi/investment-adviser-board/agents/<name>-knowledge.md）。
 *
 * Commands:
 *   /member-select [name]    — 選擇或切換對話成員
 *   /member-status           — 顯示當前成員資訊和知識庫狀態
 *   /member-equip <skill>    — 將 skill 用法寫入成員知識庫
 *
 * Usage: pi -e extensions/boards/inv-board-member-session.ts
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

// ── YAML Config Parser ────────────────────────────────────────────────────────

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
      if (m) {
        config.presets[m[1].trim()] = m[2].split(",").map((s) => s.trim()).filter(Boolean);
      }
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
      tools: fm["tools"] ? fm["tools"].split(",").map((t) => t.trim()).filter(Boolean) : [],
      knowledgePath,
      sourcesPath,
    };
  } catch {
    return null;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function displayName(name: string): string {
  return name.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function ensureKnowledgeFile(member: MemberDef): void {
  if (!existsSync(member.knowledgePath)) {
    const template = `# ${displayName(member.name)} — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID，完整 URL 在 ${member.name}-sources.md。
> 使用 edit 工具更新此文件。

## 核心投資哲學

（尚未記錄）

## 分析框架

（尚未記錄）

## 市場觀點與看法

（尚未記錄）

## 分析過的標的記錄

| 日期 | 標的 | 立場 | 結果/複盤 |
|------|------|------|----------|

## 經驗教訓 / 避免的偏誤

（尚未記錄）
`;
    writeFileSync(member.knowledgePath, template, "utf-8");
  }

  if (!existsSync(member.sourcesPath)) {
    const sourcesTemplate = `# ${displayName(member.name)} — 來源登記表

> 學習來源索引。knowledge.md 中的 [src:NNN] 對應此表的 ID 欄。
> 此檔不會自動注入 context，需要溯源時自行 read。

| ID | 日期 | 類型 | 來源 URL | 說明 |
|----|------|------|----------|------|
`;
    writeFileSync(member.sourcesPath, sourcesTemplate, "utf-8");
  }
}

// ── Skill Scanner ─────────────────────────────────────────────────────────────

interface SkillInfo {
  name: string;
  description: string;
  dir: string;
  mdPath: string;
}

function scanSkills(cwd: string): SkillInfo[] {
  const skillDirs = [
    join(cwd, ".claude/skills"),
    join(homedir(), ".claude/skills"),
  ];
  const seen = new Set<string>();
  const skills: SkillInfo[] = [];
  for (const base of skillDirs) {
    if (!existsSync(base)) continue;
    try {
      for (const name of readdirSync(base)) {
        if (seen.has(name)) continue;
        const dir = join(base, name);
        const mdFiles = readdirSync(dir).filter((f) => f.endsWith(".md"));
        if (mdFiles.length === 0) continue;
        const mdPath = join(dir, mdFiles[0]);
        const raw = readFileSync(mdPath, "utf-8");
        const descMatch = raw.match(/^description:\s*(.+)$/m);
        const description = descMatch ? descMatch[1].trim().split(".")[0] : "";
        seen.add(name);
        skills.push({ name, description, dir, mdPath });
      }
    } catch {}
  }
  return skills;
}

// ── Module State ──────────────────────────────────────────────────────────────

let activeMember: MemberDef | null = null;
let boardConfig: BoardConfig | null = null;
let defaultTools: string[] = [];
let cwdRef = "";
let baseSystemPrompt: string | null = null; // Store original system prompt to avoid accumulation

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Roster widget (shown on load) ──────────────────────────────────────────
  function showRosterWidget(ctx: ExtensionContext): void {
    if (!boardConfig) return;
    ctx.ui.setWidget(
      "member-roster",
      (_tui, theme, _footerData) => {
        const lines: string[] = [];
        lines.push(theme.fg("accent", theme.bold("  投資顧問委員會  ")) + theme.fg("dim", `(${boardConfig!.board.length} 位成員)`));
        lines.push(theme.fg("dim", "  " + "─".repeat(50)));
        for (const m of boardConfig!.board) {
          const def = parseMemberFile(join(cwdRef, m.path));
          const isActive = activeMember?.name === m.name;
          const kbMark = def && existsSync(def.knowledgePath)
            ? theme.fg("success", "📚")
            : theme.fg("muted", " ○");
          const nameStr = isActive
            ? theme.fg("accent", theme.bold(`  ${m.name}`))
            : theme.fg("dim", `  ${m.name}`);
          const desc = def?.description ? theme.fg("muted", `  —  ${def.description.split("—")[1]?.trim() ?? def.description.split("—")[0]?.trim()}`) : "";
          lines.push(`  ${kbMark} ${nameStr}${desc}`);
        }
        lines.push(theme.fg("dim", "  " + "─".repeat(50)));
        lines.push(theme.fg("muted", "  /member-select  ·  /member-equip <skill>  ·  /member-status"));
        return {
          render(width: number) {
            return lines.map((l) => truncateToWidth(l, width));
          },
          invalidate() {},
        };
      },
      { placement: "belowEditor", dismissAfter: 8000 }
    );
  }

  // ── Footer renderer ────────────────────────────────────────────────────────
  function renderFooter(tui: any, theme: any, footerData: any) {
    return {
      dispose: footerData.onBranchChange(() => tui.requestRender()),
      invalidate() {},
      render(width: number): string[] {
        const prefix = theme.fg("dim", "[ Member Session ]  ");
        if (!activeMember) {
          return [truncateToWidth(prefix + theme.fg("muted", "未選擇成員 — 使用 /member-select"), width)];
        }
        const namePart = theme.fg("accent", theme.bold(displayName(activeMember.name)));
        const descPart = theme.fg("dim", `  ${activeMember.description}`);
        const kbExists = existsSync(activeMember.knowledgePath);
        const kbMark = kbExists ? theme.fg("success", " ●") : theme.fg("muted", " ○");
        const kbLabel = theme.fg("muted", ` kb${kbMark}`);
        return [truncateToWidth(prefix + namePart + descPart + kbLabel, width)];
      },
    };
  }

  // ── Session start ──────────────────────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    cwdRef = ctx.cwd;
    defaultTools = pi.getActiveTools();

    const configPath = join(ctx.cwd, ".pi/investment-adviser-board/config.yaml");
    if (existsSync(configPath)) {
      boardConfig = parseBoardConfigYaml(readFileSync(configPath, "utf-8"));
    } else {
      ctx.ui.notify("找不到 .pi/investment-adviser-board/config.yaml", "warning");
    }

    ctx.ui.setStatus("member-session", "成員：未選擇");
    ctx.ui.setFooter(renderFooter);

    // Auto-select member from BOARD_MEMBER env var (e.g. just ext-inv-member-macro)
    const envMember = process.env.BOARD_MEMBER;
    if (envMember && boardConfig) {
      const matched = boardConfig.board.find(
        (m) => m.name === envMember || m.name.startsWith(envMember)
      );
      if (matched) {
        const member = parseMemberFile(join(cwdRef, matched.path));
        if (member) {
          activeMember = member;
          ensureKnowledgeFile(member);
          pi.setActiveTools(["read", "write", "edit", "bash"]);
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

  // ── Inject member system prompt ────────────────────────────────────────────
  pi.on("before_agent_start", async (event, _ctx) => {
    if (!activeMember) return;

    // Store base system prompt on first call to avoid accumulation when switching members
    if (baseSystemPrompt === null) {
      baseSystemPrompt = event.systemPrompt;
    }

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

**這是你在會話之間持久記憶的地方。** 你可以隨時用 \`edit\` 工具更新此文件，記錄：
- 你對市場或資產的最新看法與哲學演變
- 你分析過的標的和結論（附日期）
- 你容易犯的偏誤（為了下次避免）
- 你更新的分析框架或方法論

每次對話結束時，主動問用戶是否有新見解值得寫入知識庫。
`;

    // Use baseSystemPrompt instead of event.systemPrompt to avoid accumulation
    return {
      systemPrompt: activeMember.systemPrompt + knowledgeSection + "\n\n" + (baseSystemPrompt || event.systemPrompt),
    };
  });

  // ── /member-select ─────────────────────────────────────────────────────────
  pi.registerCommand("member-select", {
    description: "選擇或切換對話的委員會成員（可帶名稱：/member-select macro-strategist）",
    handler: async (args, ctx) => {
      if (!boardConfig) {
        ctx.ui.notify("委員會設定未載入", "error");
        return;
      }

      // Direct arg match
      const argName = args?.trim();
      if (argName) {
        const matched = boardConfig.board.find(
          (m) => m.name === argName || m.name.startsWith(argName)
        );
        if (matched) {
          const member = parseMemberFile(join(cwdRef, matched.path));
          if (member) {
            activeMember = member;
            ensureKnowledgeFile(member);
            pi.setActiveTools(["read", "write", "edit", "bash"]);
            ctx.ui.setStatus("member-session", `成員：${displayName(member.name)}`);
            ctx.ui.notify(
              `已切換至：${displayName(member.name)}\n知識庫：${member.knowledgePath}`,
              "success"
            );
            return;
          }
        }
        ctx.ui.notify(`找不到成員：${argName}`, "warning");
      }

      // Select dialog
      const options = [
        "（清除 — 回到預設模式）",
        ...boardConfig.board.map((m) => {
          const def = parseMemberFile(join(cwdRef, m.path));
          const desc = def?.description ?? "";
          const kbMark = def && existsSync(def.knowledgePath) ? "📚" : "○";
          return `${kbMark}  ${m.name}  —  ${desc}`;
        }),
      ];

      const choice = await ctx.ui.select("選擇委員會成員", options);
      if (choice === undefined) return;

      if (choice === options[0]) {
        activeMember = null;
        baseSystemPrompt = null; // Reset to allow fresh start next time
        pi.setActiveTools(defaultTools);
        ctx.ui.setStatus("member-session", "成員：未選擇");
        ctx.ui.notify("已清除成員，回到預設模式", "info");
        return;
      }

      const idx = options.indexOf(choice) - 1;
      const memberConfig = boardConfig.board[idx];
      const member = parseMemberFile(join(cwdRef, memberConfig.path));

      if (!member) {
        ctx.ui.notify(`無法載入成員文件：${memberConfig.path}`, "error");
        return;
      }

      activeMember = member;
      ensureKnowledgeFile(member);
      pi.setActiveTools(["read", "write", "edit", "bash"]);
      ctx.ui.setStatus("member-session", `成員：${displayName(member.name)}`);
      ctx.ui.notify(
        `已切換至：${displayName(member.name)}\n知識庫：${member.knowledgePath}`,
        "success"
      );
    },
  });

  // ── /member-status ─────────────────────────────────────────────────────────
  pi.registerCommand("member-status", {
    description: "顯示當前選中的委員會成員和知識庫狀態",
    handler: async (_args, ctx) => {
      if (!activeMember) {
        ctx.ui.notify("目前沒有選擇成員。使用 /member-select 選擇。", "warning");
        return;
      }
      const kbExists = existsSync(activeMember.knowledgePath) ? "存在 ✓" : "尚未建立";
      ctx.ui.notify(
        [
          `成員：${displayName(activeMember.name)}`,
          `描述：${activeMember.description}`,
          `模型：${activeMember.model || "預設"}`,
          `知識庫：${activeMember.knowledgePath}（${kbExists}）`,
        ].join("\n"),
        "info"
      );
    },
  });

  // ── /member-equip ──────────────────────────────────────────────────────────
  pi.registerCommand("member-equip", {
    description: "將 skill 的使用方法寫入成員知識庫（/member-equip wsp-v3）",
    handler: async (args, ctx) => {
      if (!activeMember) {
        ctx.ui.notify("請先用 /member-select 選擇成員", "warning");
        return;
      }

      const skills = scanSkills(cwdRef);
      const argSkill = args?.trim();

      // No arg → show select dialog
      if (!argSkill) {
        if (skills.length === 0) {
          ctx.ui.notify("找不到任何 skill（搜尋 .claude/skills/ 和 ~/.claude/skills/）", "warning");
          return;
        }
        const options = skills.map((s) => `${s.name}  —  ${s.description}`);
        const choice = await ctx.ui.select("選擇要裝備的 Skill", options);
        if (!choice) return;
        const idx = options.indexOf(choice);
        await equipSkill(activeMember, skills[idx], ctx);
        return;
      }

      // Arg provided → match skill
      const matched = skills.find(
        (s) => s.name === argSkill || s.name.startsWith(argSkill)
      );
      if (!matched) {
        const available = skills.map((s) => s.name).join(", ");
        ctx.ui.notify(`找不到 skill：${argSkill}\n可用：${available}`, "warning");
        return;
      }
      await equipSkill(activeMember, matched, ctx);
    },
  });

  // ── /member-learn ──────────────────────────────────────────────────────────
  pi.registerCommand("member-learn", {
    description: "從 URL（YouTube / X / 文章）學習並更新個人知識庫（/member-learn <url>）",
    handler: async (args, ctx) => {
      if (!activeMember) {
        ctx.ui.notify("請先用 /member-select 選擇成員", "warning");
        return;
      }
      const url = args?.trim();
      if (!url) {
        ctx.ui.notify("用法：/member-learn <url>", "warning");
        return;
      }

      const today = new Date().toISOString().slice(0, 10);
      const learnPrompt = [
        `請從以下來源學習，並按格式更新兩個檔案：`,
        ``,
        `URL：${url}`,
        ``,
        `## 步驟一：取得內容`,
        `用 bash 執行：`,
        `  summarize "${url}" --youtube auto`,
        `（若非 YouTube，去掉 --youtube auto；X/Twitter 貼文直接用 URL 不需要 --youtube）`,
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
        `  | src:NNN | ${today} | <YouTube/X/Article> | ${url} | <一句描述> |`,
        ``,
        `完成後告訴我學到了什麼（一段話）。`,
      ].join("\n");

      ctx.ui.notify(
        `已為 ${displayName(activeMember.name)} 準備學習任務\n請將以下訊息發送給成員：\n\n${learnPrompt}`,
        "info"
      );
    },
  });
}

// ── Equip helper (outside export fn to keep it clean) ────────────────────────

async function equipSkill(
  member: MemberDef,
  skill: SkillInfo,
  ctx: any
): Promise<void> {
  // Read skill's main .md for usage instructions
  const skillContent = readFileSync(skill.mdPath, "utf-8");

  // Extract the bash usage block(s) — look for ```bash fences
  const bashBlocks: string[] = [];
  const bashRe = /```bash\n([\s\S]*?)```/g;
  let m: RegExpExecArray | null;
  while ((m = bashRe.exec(skillContent)) !== null) {
    bashBlocks.push(m[1].trim());
  }

  const usageSection = bashBlocks.length > 0
    ? `\`\`\`bash\n${bashBlocks.slice(0, 3).join("\n\n")}\n\`\`\``
    : skillContent.slice(0, 800);

  const entry = `
## 技能裝備：${skill.name}

> 裝備於 ${new Date().toISOString().slice(0, 10)}

**描述：** ${skill.description}

**使用方式：**
${usageSection}
`;

  // Append to knowledge file
  const current = existsSync(member.knowledgePath)
    ? readFileSync(member.knowledgePath, "utf-8")
    : "";

  // Check if already equipped
  if (current.includes(`技能裝備：${skill.name}`)) {
    ctx.ui.notify(`${skill.name} 已在知識庫中，跳過`, "info");
    return;
  }

  writeFileSync(member.knowledgePath, current + "\n" + entry, "utf-8");
  ctx.ui.notify(
    `已將 ${skill.name} 寫入 ${displayName(member.name)} 的知識庫\n下次會話起生效`,
    "success"
  );
}
