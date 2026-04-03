/**
 * Meta Expert Session — 與 Meta-Orchestrator 共享專家一對一深度對話
 *
 * 直接載入 shared_experts（目前：geopolitics-analyst）進行 1-on-1 會話。
 * 支援知識庫更新，讓專家在對話間保留洞見。
 *
 * 透過 EXPERT 環境變數指定專家（未設定則預設 geopolitics-analyst）：
 *   EXPERT=geopolitics-analyst pi -e extensions/boards/meta-expert-session.ts
 *
 * Commands:
 *   /expert-status   — 顯示當前專家資訊和知識庫狀態
 *   /expert-learn    — 更新知識庫
 *
 * Usage: pi -e extensions/boards/meta-expert-session.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { truncateToWidth } from "@mariozechner/pi-tui";
import { readFileSync, existsSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ExpertDef {
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  knowledgePath: string;
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
      model: fm["model"] || "",
      knowledgePath: join(dirname(filePath), `${name}-knowledge.md`),
    };
  } catch { return null; }
}

function displayName(name: string): string {
  return name.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function ensureKnowledgeFile(expert: ExpertDef): void {
  if (existsSync(expert.knowledgePath)) return;
  writeFileSync(expert.knowledgePath, `# ${displayName(expert.name)} — 個人知識庫

> 洞見摘要檔。每條學習以 [src:NNN] 標記來源 ID。
> 使用 edit 工具更新此文件。

## 核心分析框架

（尚未記錄）

## 持續追蹤的風險事件

（尚未記錄）

## 重要發現與洞見

（尚未記錄）
`, "utf-8");
}

// ── Module State ──────────────────────────────────────────────────────────────

let activeExpert: ExpertDef | null = null;
let cwdRef = "";

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Footer ─────────────────────────────────────────────────────────────────

  function renderFooter(tui: any, theme: any, footerData: any) {
    return {
      dispose: footerData.onBranchChange(() => tui.requestRender()),
      invalidate() { },
      render(width: number): string[] {
        const prefix = theme.fg("dim", "[ Meta Expert · 1-on-1 ]  ");
        if (!activeExpert) {
          return [truncateToWidth(prefix + theme.fg("error", "專家未載入"), width)];
        }
        const namePart = theme.fg("accent", theme.bold(displayName(activeExpert.name)));
        const descShort = activeExpert.description.split("—")[0]?.trim() || "";
        const descPart = theme.fg("dim", `  ${descShort}`);
        const kbMark = existsSync(activeExpert.knowledgePath)
          ? theme.fg("success", " ●")
          : theme.fg("muted", " ○");
        return [truncateToWidth(prefix + namePart + descPart + theme.fg("muted", ` kb${kbMark}`), width)];
      },
    };
  }

  // ── Session Start ──────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    cwdRef = ctx.cwd;

    const expertName = process.env.EXPERT || "geopolitics-analyst";
    const expertPath = join(cwdRef, `.pi/meta-orchestrator/agents/${expertName}/${expertName}.md`);

    if (!existsSync(expertPath)) {
      ctx.ui.notify(`找不到專家檔案：${expertPath}`, "error");
      ctx.ui.setFooter(renderFooter);
      return;
    }

    const expert = parseExpertFile(expertPath);
    if (!expert) {
      ctx.ui.notify(`無法解析專家檔案：${expertPath}`, "error");
      ctx.ui.setFooter(renderFooter);
      return;
    }

    activeExpert = expert;
    ensureKnowledgeFile(expert);
    pi.setActiveTools(["read", "write", "edit", "bash", "grep", "glob", "web_search", "web_fetch"]);

    ctx.ui.setStatus("meta-expert", `專家：${displayName(expert.name)}`);
    ctx.ui.setFooter(renderFooter);
    ctx.ui.notify(`已載入 ${displayName(expert.name)}\n知識庫：${expert.knowledgePath}`, "success");
  });

  // ── Inject Expert System Prompt ────────────────────────────────────────────

  pi.on("before_agent_start", async (event, _ctx) => {
    if (!activeExpert) return;

    const knowledgeContent = existsSync(activeExpert.knowledgePath)
      ? readFileSync(activeExpert.knowledgePath, "utf-8")
      : "（尚未建立）";

    const knowledgeSection = `

---

## 你的個人知識庫

路徑：\`${activeExpert.knowledgePath}\`

目前內容：
\`\`\`markdown
${knowledgeContent}
\`\`\`

**這是你在會話之間的持久記憶。** 你可以隨時用 \`edit\` 工具更新此文件，記錄：
- 追蹤中的地緣政治風險事件（附日期）
- 已確認的結構性趨勢與分析框架
- 跨域交叉影響的洞見

每次對話結束時，主動問用戶是否有新洞見值得寫入知識庫。
`;

    return {
      systemPrompt: activeExpert.systemPrompt + knowledgeSection + "\n\n" + event.systemPrompt,
    };
  });

  // ── /expert-status ─────────────────────────────────────────────────────────

  pi.registerCommand("expert-status", {
    description: "顯示當前專家資訊和知識庫狀態",
    handler: async (_args, ctx) => {
      if (!activeExpert) {
        ctx.ui.notify("未載入任何專家", "warning");
        return;
      }
      const kbExists = existsSync(activeExpert.knowledgePath);
      ctx.ui.notify(
        `${displayName(activeExpert.name)}\n` +
        `描述：${activeExpert.description}\n` +
        `模型：${activeExpert.model || "預設"}\n` +
        `知識庫：${kbExists ? "✓ 存在" : "✗ 未建立"}\n` +
        `路徑：${activeExpert.knowledgePath}`,
        "info"
      );
    },
  });

  // ── /expert-learn ──────────────────────────────────────────────────────────

  pi.registerCommand("expert-learn", {
    description: "提示專家將當前對話洞見寫入知識庫",
    handler: async (_args, ctx) => {
      if (!activeExpert) { ctx.ui.notify("未載入任何專家", "warning"); return; }
      ctx.ui.notify(
        `請整理本次對話的洞見，用 edit 工具更新：\n${activeExpert.knowledgePath}`,
        "info"
      );
    },
  });
}
