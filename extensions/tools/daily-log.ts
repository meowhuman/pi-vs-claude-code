/**
 * Daily Log — Lightweight work journaling extension for Pi Coding Agent
 *
 * Tools:
 *   log_entry    — Append an entry to today's log
 *   log_show     — Display a day's log in overlay
 *   log_summary  — Generate and append an AI summary
 *   log_search   — Search across all log files
 *
 * Commands:
 *   /daily-log   — Open today's log overlay
 *
 * Usage: pi -e extensions/daily-log.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import { readFile, writeFile, readdir, mkdir } from "fs/promises";
import { existsSync } from "fs";
import { join } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";

// ── Constants ──────────────────────────────────────────────────────────────────

const SECTION_LABELS: Record<string, string> = {
  done: "Done",
  blocked: "Blocked",
  note: "Notes",
  decision: "Decisions",
};

const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Validate YYYY-MM-DD format strictly — no path traversal characters allowed. */
function isValidDate(date: string): boolean {
  if (!DATE_REGEX.test(date)) return false;
  const parsed = new Date(date);
  return !isNaN(parsed.getTime());
}

/** Get today's date string in YYYY-MM-DD format. */
function todayString(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Return the absolute path to a log file given a validated date string and cwd. */
function logFilePath(cwd: string, date: string): string {
  return join(cwd, "logs", `${date}.md`);
}

/** Generate the initial Markdown template for a new daily log. */
function buildTemplate(date: string): string {
  return (
    `# Daily Log — ${date}\n\n` +
    `## Done\n\n` +
    `## Blocked\n\n` +
    `## Decisions\n\n` +
    `## Notes\n\n` +
    `## Summary\n\n` +
    `_(no summary yet — run \`log_summary\` to generate one)_\n`
  );
}

/** Ensure the logs/ directory exists, creating it if needed. */
async function ensureLogsDir(cwd: string): Promise<void> {
  const logsDir = join(cwd, "logs");
  if (!existsSync(logsDir)) {
    await mkdir(logsDir, { recursive: true });
  }
}

/** Read a log file, returning null if it does not exist. */
async function readLogFile(filePath: string): Promise<string | null> {
  try {
    return await readFile(filePath, "utf-8");
  } catch {
    return null;
  }
}

/**
 * Append an entry line to the correct section within a Markdown log string.
 * Returns the updated content.
 */
function appendToSection(
  content: string,
  section: string,
  entryLine: string
): string {
  const heading = `## ${SECTION_LABELS[section]}`;
  const headingIdx = content.indexOf(heading);

  if (headingIdx === -1) {
    // Fallback: append at end
    return content.trimEnd() + `\n\n${heading}\n${entryLine}\n`;
  }

  // Find the end of this section (next ## heading or end of file)
  const afterHeading = headingIdx + heading.length;
  const nextHeadingIdx = content.indexOf("\n## ", afterHeading);
  const sectionEnd = nextHeadingIdx === -1 ? content.length : nextHeadingIdx;

  // Insert the new entry just before the section boundary
  const before = content.slice(0, sectionEnd).trimEnd();
  const after = content.slice(sectionEnd);
  return `${before}\n${entryLine}\n${after}`;
}

/** Count the total number of bullet-point entries across all sections. */
function countEntries(content: string): number {
  return (content.match(/^- /gm) || []).length;
}

/** Replace the Summary section content (idempotent). */
function replaceSummarySection(content: string, summary: string): string {
  const heading = "## Summary";
  const headingIdx = content.indexOf(heading);
  if (headingIdx === -1) {
    return content.trimEnd() + `\n\n${heading}\n\n${summary}\n`;
  }

  const afterHeading = headingIdx + heading.length;
  const nextHeadingIdx = content.indexOf("\n## ", afterHeading);
  const sectionEnd = nextHeadingIdx === -1 ? content.length : nextHeadingIdx;

  const before = content.slice(0, headingIdx + heading.length);
  const after = content.slice(sectionEnd);
  return `${before}\n\n${summary}\n${after}`;
}

/** Extract a specific section's content from a log file string. */
function extractSection(content: string, section: string): string {
  if (section === "all") return content;

  const heading = `## ${SECTION_LABELS[section]}`;
  const headingIdx = content.indexOf(heading);
  if (headingIdx === -1) return `_(no ${SECTION_LABELS[section]} entries)_`;

  const afterHeading = headingIdx + heading.length;
  const nextHeadingIdx = content.indexOf("\n## ", afterHeading);
  const sectionEnd = nextHeadingIdx === -1 ? content.length : nextHeadingIdx;

  return content.slice(headingIdx, sectionEnd).trim();
}

// ── Extension Export ───────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let cwd = "";
  let entryCount = 0;

  // ── Tool: log_entry ──────────────────────────────────────────────────────────

  pi.registerTool({
    name: "log_entry",
    label: "Log Entry",
    description:
      "Append a new entry to today's daily log. " +
      "Use section='done' for completed work, 'blocked' for blockers, " +
      "'note' for general notes, 'decision' for decisions made.",
    parameters: Type.Object({
      section: Type.Union(
        [
          Type.Literal("done"),
          Type.Literal("blocked"),
          Type.Literal("note"),
          Type.Literal("decision"),
        ],
        { description: "Section to append the entry to" }
      ),
      text: Type.String({
        description: "Entry content (plain text, supports inline code)",
        minLength: 1,
        maxLength: 5000,
      }),
      tags: Type.Optional(
        Type.Array(Type.String(), {
          description: "Optional labels for filtering (e.g. [\"backend\", \"auth\"])",
        })
      ),
    }),

    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { section, text, tags } = params as {
        section: "done" | "blocked" | "note" | "decision";
        text: string;
        tags?: string[];
      };

      if (text.trim().length === 0) {
        return {
          content: [{ type: "text", text: "Entry text cannot be blank." }],
          details: { status: "error" },
        };
      }

      const date = todayString();
      const filePath = logFilePath(cwd, date);

      await ensureLogsDir(cwd);

      let content = await readLogFile(filePath);
      if (content === null) {
        content = buildTemplate(date);
      }

      const tagString = tags && tags.length > 0
        ? " " + tags.map((t) => `#${t.replace(/^#/, "")}`).join(" ")
        : "";
      const entryLine = `- ${text}${tagString}`;

      const updated = appendToSection(content, section, entryLine);
      try {
        await writeFile(filePath, updated, "utf-8");
      } catch (err) {
        return {
          content: [{ type: "text", text: `Failed to write log file: ${(err as Error).message}` }],
          details: { status: "error" },
        };
      }

      entryCount = countEntries(updated);
      ctx.ui.setStatus("daily-log", `Daily Log — ${date} | ${entryCount} entries`);

      return {
        content: [
          {
            type: "text",
            text: `Entry added to [${SECTION_LABELS[section]}]:\n${entryLine}\n\nTotal entries today: ${entryCount}`,
          },
        ],
        details: { status: "done", date, section, entryLine },
      };
    },
  });

  // ── Tool: log_show ───────────────────────────────────────────────────────────

  pi.registerTool({
    name: "log_show",
    label: "Log Show",
    description:
      "Display a daily log in the Pi overlay. Defaults to today's log. " +
      "Optionally filter by section.",
    parameters: Type.Object({
      date: Type.Optional(
        Type.String({ description: "ISO date YYYY-MM-DD. Defaults to today." })
      ),
      section: Type.Optional(
        Type.Union(
          [
            Type.Literal("done"),
            Type.Literal("blocked"),
            Type.Literal("note"),
            Type.Literal("decision"),
            Type.Literal("all"),
          ],
          { description: "Filter by section. Defaults to 'all'." }
        )
      ),
    }),

    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { date: rawDate, section = "all" } = params as {
        date?: string;
        section?: "done" | "blocked" | "note" | "decision" | "all";
      };

      const date = rawDate ?? todayString();

      // Security: strict date validation to prevent path traversal
      if (!isValidDate(date)) {
        return {
          content: [{ type: "text", text: `Invalid date format: "${date}". Use YYYY-MM-DD.` }],
          details: { status: "error" },
        };
      }

      const filePath = logFilePath(cwd, date);
      const content = await readLogFile(filePath);

      if (content === null) {
        ctx.ui.notify(`No log for ${date}.`, "info");
        return {
          content: [{ type: "text", text: `No log for ${date}.` }],
          details: { status: "done", date },
        };
      }

      const display = extractSection(content, section);
      const title = section === "all"
        ? `Daily Log — ${date}`
        : `Daily Log — ${date} / ${SECTION_LABELS[section]}`;

      ctx.ui.notify(`${title}\n\n${display}`, "info");

      return {
        content: [{ type: "text", text: display }],
        details: { status: "done", date, section },
      };
    },
  });

  // ── Tool: log_summary ────────────────────────────────────────────────────────

  pi.registerTool({
    name: "log_summary",
    label: "Log Summary",
    description:
      "Generate a one-paragraph AI summary of the day's activity and append it to the Summary section. " +
      "Idempotent — replaces any existing summary. Defaults to today.",
    parameters: Type.Object({
      date: Type.Optional(
        Type.String({ description: "ISO date YYYY-MM-DD. Defaults to today." })
      ),
    }),

    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const { date: rawDate } = params as { date?: string };
      const date = rawDate ?? todayString();

      // Security: strict date validation
      if (!isValidDate(date)) {
        return {
          content: [{ type: "text", text: `Invalid date format: "${date}". Use YYYY-MM-DD.` }],
          details: { status: "error" },
        };
      }

      const filePath = logFilePath(cwd, date);
      const content = await readLogFile(filePath);

      if (content === null) {
        return {
          content: [{ type: "text", text: `No log found for ${date}. Nothing to summarize.` }],
          details: { status: "done", date },
        };
      }

      // Return the log content so the agent can generate a summary inline,
      // then call this tool again with the result embedded via append.
      const prompt =
        `Please write a concise one-paragraph summary of the following daily log for ${date}. ` +
        `Cover completed work, blockers, and key decisions. Be factual and brief.\n\n` +
        `---\n${content}\n---\n\n` +
        `After writing the summary, call \`log_summary_write\` with the date and summary text to persist it.`;

      return {
        content: [{ type: "text", text: prompt }],
        details: { status: "pending_summary", date },
      };
    },
  });

  // ── Tool: log_summary_write (internal — called by agent after generating summary) ──

  pi.registerTool({
    name: "log_summary_write",
    label: "Log Summary Write",
    description:
      "Write a generated summary into the Summary section of a daily log. " +
      "Called after log_summary provides the log content for summarization.",
    parameters: Type.Object({
      date: Type.String({ description: "ISO date YYYY-MM-DD of the log to update." }),
      summary: Type.String({
        description: "The generated summary paragraph to store.",
        minLength: 1,
        maxLength: 5000,
      }),
    }),

    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const { date, summary } = params as { date: string; summary: string };

      if (summary.trim().length === 0) {
        return {
          content: [{ type: "text", text: "Summary text cannot be blank." }],
          details: { status: "error" },
        };
      }

      // Security: strict date validation
      if (!isValidDate(date)) {
        return {
          content: [{ type: "text", text: `Invalid date format: "${date}". Use YYYY-MM-DD.` }],
          details: { status: "error" },
        };
      }

      const filePath = logFilePath(cwd, date);
      const content = await readLogFile(filePath);

      if (content === null) {
        return {
          content: [{ type: "text", text: `No log found for ${date}.` }],
          details: { status: "error" },
        };
      }

      const updated = replaceSummarySection(content, summary);
      try {
        await writeFile(filePath, updated, "utf-8");
      } catch (err) {
        return {
          content: [{ type: "text", text: `Failed to write summary: ${(err as Error).message}` }],
          details: { status: "error" },
        };
      }

      return {
        content: [{ type: "text", text: `Summary written to logs/${date}.md.` }],
        details: { status: "done", date },
      };
    },
  });

  // ── Tool: log_search ─────────────────────────────────────────────────────────

  pi.registerTool({
    name: "log_search",
    label: "Log Search",
    description:
      "Search across all daily log files for entries matching a keyword or #tag. " +
      "Results are returned newest-first.",
    parameters: Type.Object({
      query: Type.String({ description: "Keyword or #tag to search for" }),
      limit: Type.Optional(
        Type.Number({ description: "Max results to return. Defaults to 20." })
      ),
    }),

    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const { query, limit = 20 } = params as { query: string; limit?: number };

      const logsDir = join(cwd, "logs");

      if (!existsSync(logsDir)) {
        return {
          content: [{ type: "text", text: "No logs directory found. Start logging first." }],
          details: { status: "done", results: [] },
        };
      }

      let files: string[];
      try {
        const allFiles = await readdir(logsDir);
        files = allFiles
          .filter((f) => f.endsWith(".md") && DATE_REGEX.test(f.replace(".md", "")))
          .sort()
          .reverse();
      } catch {
        return {
          content: [{ type: "text", text: "Failed to read logs directory." }],
          details: { status: "error" },
        };
      }

      const isTagSearch = query.startsWith("#");
      const searchTerm = isTagSearch ? query.toLowerCase() : query.toLowerCase();
      const results: Array<{ date: string; line: string }> = [];

      for (const file of files) {
        if (results.length >= limit) break;

        const filePath = join(logsDir, file);
        const content = await readLogFile(filePath);
        if (!content) continue;

        const date = file.replace(".md", "");
        const lines = content.split("\n");

        for (const line of lines) {
          if (results.length >= limit) break;
          if (line.toLowerCase().includes(searchTerm)) {
            results.push({ date, line: line.trim() });
          }
        }
      }

      if (results.length === 0) {
        ctx.ui.notify(`No results for "${query}".`, "info");
        return {
          content: [{ type: "text", text: `No results found for "${query}".` }],
          details: { status: "done", results: [] },
        };
      }

      const formatted = results
        .map((r) => `[${r.date}] ${r.line}`)
        .join("\n");

      const summary = `Found ${results.length} result(s) for "${query}":\n\n${formatted}`;
      ctx.ui.notify(summary, "info");

      return {
        content: [{ type: "text", text: summary }],
        details: { status: "done", results },
      };
    },
  });

  // ── Command: /daily-log ──────────────────────────────────────────────────────

  pi.registerCommand("daily-log", {
    description: "Open today's daily log overlay",
    handler: async (_args, ctx) => {
      const date = todayString();
      const filePath = logFilePath(cwd, date);
      const content = await readLogFile(filePath);

      if (content === null) {
        ctx.ui.notify(`No log for today (${date}) yet. Use log_entry to start.`, "info");
        return;
      }

      ctx.ui.notify(content, "info");
    },
  });

  // ── Session Start ─────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    cwd = ctx.cwd;

    const date = todayString();
    await ensureLogsDir(cwd);

    const filePath = logFilePath(cwd, date);
    let content = await readLogFile(filePath);

    if (content === null) {
      content = buildTemplate(date);
      try {
        await writeFile(filePath, content, "utf-8");
      } catch (err) {
        ctx.ui.notify(`Daily Log: failed to create today's log file — ${(err as Error).message}`, "warning");
      }
    }

    entryCount = countEntries(content);
    ctx.ui.setStatus("daily-log", `Daily Log — ${date} | ${entryCount} entries`);
  });

  // ── Session End ───────────────────────────────────────────────────────────────

  pi.on("session_end", async (_event, ctx) => {
    const date = todayString();
    const filePath = logFilePath(cwd, date);
    const content = await readLogFile(filePath);
    const count = content ? countEntries(content) : 0;

    if (count > 0) {
      ctx.ui.notify(
        `Daily log has ${count} entries.\nRun \`log_summary\` to generate a summary.`,
        "info"
      );
    }
  });

  // ── Before Agent Start ────────────────────────────────────────────────────────

  pi.on("before_agent_start", async (_event, _ctx) => {
    const date = todayString();
    return {
      systemPrompt:
        `You have access to a daily log system for recording work progress.\n\n` +
        `## Daily Log Tools\n` +
        `- \`log_entry\` — Add an entry (done/blocked/note/decision) with optional #tags\n` +
        `- \`log_show\` — Display a day's log (defaults to today)\n` +
        `- \`log_summary\` — Generate a summary of the day (then use \`log_summary_write\` to save it)\n` +
        `- \`log_search\` — Search all log files for a keyword or #tag\n\n` +
        `## Today's Date\n` +
        `${date}\n\n` +
        `## Commands\n` +
        `/daily-log    Open today's log overlay\n\n` +
        `Log important completions, blockers, decisions, and notes as you work.`,
    };
  });
}
