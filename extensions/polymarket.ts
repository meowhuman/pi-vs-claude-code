whats/**
 * Polymarket Agent — Specialized prediction market trading terminal
 *
 * Full-stack Polymarket CLI integration as a Pi extension. Wraps pm.py,
 * trade.py, search.py, analyze.py, and monitoring scripts into typed Pi tools.
 * Injects a trading-expert system prompt and renders a live market footer.
 *
 * Configure the polymarket scripts directory:
 *   export POLYMARKET_DIR=/path/to/polymarket-trader
 *   pi -e extensions/polymarket.ts
 *
 * Or use /pm-config at runtime.
 *
 * Tools:
 *   Portfolio  — portfolio_dashboard, portfolio_close, portfolio_report,
 *                portfolio_rebalance, portfolio_liquidity
 *   Trading    — trade_market, trade_limit, trade_orders, trade_cancel,
 *                trade_set_alert
 *   Search     — search_markets, market_detail
 *   Analysis   — analyze_market, analyze_whales, analyze_wallet, analyze_odds,
 *                analyze_kelly, analyze_signal, analyze_distribution,
 *                analyze_insider, analyze_holders
 *   Monitoring — scan_insider_bulk, insider_detail
 *
 * Commands:
 *   /pm-config  — set the polymarket scripts directory
 *   /pm-help    — show quick reference of all tools
 *
 * Usage: pi -e extensions/polymarket.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawn } from "child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, resolve, dirname } from "path";
import { applyExtensionDefaults } from "./themeMap.ts";
import { fileURLToPath } from "url";

// ── Config persistence ────────────────────────────────────────────────────────

const EXTENSION_DIR = dirname(fileURLToPath(import.meta.url));
const CONFIG_FILE = join(EXTENSION_DIR, "..", ".pi", "polymarket-config.json");

function loadPersistedDir(): string {
  try {
    const raw = readFileSync(CONFIG_FILE, "utf8");
    const cfg = JSON.parse(raw);
    if (cfg.scriptsDir && existsSync(cfg.scriptsDir)) return cfg.scriptsDir;
  } catch { }
  return "";
}

function persistDir(dir: string): void {
  try {
    mkdirSync(dirname(CONFIG_FILE), { recursive: true });
    writeFileSync(CONFIG_FILE, JSON.stringify({ scriptsDir: dir }, null, 2));
  } catch { }
}

// ── Auto-discovery ────────────────────────────────────────────────────────────

const CANDIDATE_ROOTS = [
  process.env.POLYMARKET_DIR ?? "",
  join(process.env.HOME ?? "", "Documents", "Obsidian", ".claude", "skills", "polymarket-trader"),
  join(process.env.HOME ?? "", ".claude", "skills", "polymarket-trader"),
  join(process.env.HOME ?? "", "polymarket-trader"),
  join(process.env.HOME ?? "", "Documents", "polymarket-trader"),
  join(process.env.HOME ?? "", "Desktop", "polymarket-trader"),
].filter(Boolean);

function autoDiscover(): string {
  for (const root of CANDIDATE_ROOTS) {
    const candidate = join(root, "scripts");
    if (existsSync(join(candidate, "pm.py"))) return candidate;
  }
  return "";
}

// ── State ────────────────────────────────────────────────────────────────────

let scriptsDir: string = loadPersistedDir() || autoDiscover();
if (scriptsDir) persistDir(scriptsDir); // ensure config is written on first auto-discover

let lastToolCall: string = "idle";
let lastToolTime: number = Date.now();
let toolCallCount: number = 0;

// ── Script Runner ─────────────────────────────────────────────────────────────

interface RunResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

function runScript(
  scriptRelPath: string,
  args: string[],
  signal?: AbortSignal
): Promise<RunResult> {
  return new Promise((resolve_) => {
    if (!scriptsDir) {
      resolve_({
        stdout: "",
        stderr: [
          "Polymarket scripts directory not found.",
          "Set it one of these ways:",
          "  1. Run /pm-config inside Pi",
          "  2. export POLYMARKET_DIR=/path/to/polymarket-trader",
          "",
          "Searched paths:",
          ...CANDIDATE_ROOTS.map(r => `  ${r}`),
        ].join("\n"),
        exitCode: 1,
      });
      return;
    }

    const scriptPath = join(scriptsDir, scriptRelPath);
    if (!existsSync(scriptPath)) {
      resolve_({
        stdout: "",
        stderr: `Script not found: ${scriptPath}\nCheck that POLYMARKET_DIR points to the polymarket-trader root.`,
        exitCode: 1,
      });
      return;
    }

    // Use venv python if present (check both venv/ and .venv/), else fall back to python3
    const projectRoot = join(scriptsDir, "..");
    const venvPython = join(projectRoot, "venv", "bin", "python");
    const dotVenvPython = join(projectRoot, ".venv", "bin", "python");
    const python = existsSync(venvPython)
      ? venvPython
      : existsSync(dotVenvPython)
        ? dotVenvPython
        : "python3";

    const proc = spawn(python, [scriptPath, ...args], {
      cwd: join(scriptsDir, ".."),
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

    if (signal) {
      signal.addEventListener("abort", () => proc.kill("SIGTERM"), { once: true });
    }

    proc.on("close", (code: number) => {
      resolve_({ stdout, stderr, exitCode: code ?? 0 });
    });

    proc.on("error", (err: Error) => {
      resolve_({ stdout: "", stderr: err.message, exitCode: 1 });
    });
  });
}

function formatOutput(result: RunResult): string {
  const parts: string[] = [];
  if (result.stdout.trim()) parts.push(result.stdout.trim());
  if (result.stderr.trim()) parts.push(`[stderr]\n${result.stderr.trim()}`);
  if (parts.length === 0) parts.push(result.exitCode === 0 ? "(no output)" : "(empty output)");
  return parts.join("\n");
}

// ── Tool Render Helpers ────────────────────────────────────────────────────────

function renderCall(label: string, args: object, theme: any): Text {
  const preview = Object.entries(args)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}=${v}`)
    .join(" ");
  return new Text(
    theme.fg("toolTitle", theme.bold(label + " ")) +
    theme.fg("dim", preview.length > 80 ? preview.slice(0, 77) + "..." : preview),
    0, 0
  );
}

function renderResult(result: any, options: any, theme: any): Text {
  const text = result.content?.[0]?.text ?? "";
  const lines = text.split("\n");
  if (options.expanded || lines.length <= 4) {
    return new Text(theme.fg("muted", text.length > 5000 ? text.slice(0, 5000) + "\n…[truncated]" : text), 0, 0);
  }
  const preview = lines.slice(0, 3).join("\n") + `\n… (${lines.length} lines)`;
  return new Text(theme.fg("muted", preview), 0, 0);
}

// ── Extension ─────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Session boot ────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);

    if (ctx.hasUI) {
      ctx.ui.setStatus("polymarket", scriptsDir ? "Polymarket Ready" : "Polymarket: run /pm-config");

      ctx.ui.setFooter((tui, theme, footerData) => {
        const unsub = footerData.onBranchChange(() => tui.requestRender());
        return {
          dispose: unsub,
          invalidate() { },
          render(width: number): string[] {
            const dir = scriptsDir
              ? scriptsDir.replace(/\/scripts$/, "").replace(process.env.HOME ?? "", "~")
              : theme.fg("error", "not configured");

            const elapsed = Math.round((Date.now() - lastToolTime) / 1000);
            const sinceStr = elapsed < 60 ? `${elapsed}s ago` : `${Math.round(elapsed / 60)}m ago`;

            // Line 1: brand + dir (left) | tool stats (right)
            const l1Left =
              theme.fg("accent", " ◆ Polymarket") +
              theme.fg("dim", " | ") +
              theme.fg("muted", dir);

            const l1Right =
              theme.fg("dim", "tools: ") +
              theme.fg("success", `${toolCallCount}`) +
              theme.fg("dim", " | last: ") +
              theme.fg("accent", lastToolCall) +
              theme.fg("dim", ` (${sinceStr}) `);

            const pad1 = " ".repeat(Math.max(1, width - visibleWidth(l1Left) - visibleWidth(l1Right)));
            const line1 = truncateToWidth(l1Left + pad1 + l1Right, width, "");

            // Line 2: context usage (left) | git branch (right)
            const usage = ctx.getContextUsage();
            const pct = usage ? usage.percent : 0;
            const filled = Math.round(pct / 10) || 1;
            const branch = footerData.getGitBranch();

            const l2Left =
              theme.fg("dim", " ctx ") +
              theme.fg("warning", "[") +
              theme.fg("success", "#".repeat(filled)) +
              theme.fg("dim", "-".repeat(10 - filled)) +
              theme.fg("warning", "]") +
              theme.fg("dim", " ") +
              theme.fg("accent", `${Math.round(pct)}%`);

            const l2Right = branch
              ? theme.fg("warning", "(") + theme.fg("success", branch) + theme.fg("warning", ")") + theme.fg("dim", " ")
              : theme.fg("dim", " ");

            const pad2 = " ".repeat(Math.max(1, width - visibleWidth(l2Left) - visibleWidth(l2Right)));
            const line2 = truncateToWidth(l2Left + pad2 + l2Right, width, "");

            return [line1, line2];
          },
        };
      });
    }
  });

  // ── Track tool calls ─────────────────────────────────────────────────────────

  pi.on("tool_execution_end", async (event) => {
    lastToolCall = event.toolName;
    lastToolTime = Date.now();
    toolCallCount++;
  });

  // ── System Prompt ────────────────────────────────────────────────────────────

  pi.on("before_agent_start", async (_event, _ctx) => {
    return {
      appendSystemPrompt: `
## Polymarket Terminal Context

You are a Polymarket data terminal and market analyst assistant. The user is an experienced, self-directed trader who operates their own Polymarket account. Your role is to:

1. **Fetch and present market data** — prices, volume, order book, holder distribution, odds history
2. **Analyse on-chain patterns** — whale positioning, insider activity, Smart Money flows, Kelly sizing
3. **Interpret what the data means** — explain trends, divergences, signal strength, and risk factors
4. **Give a clear directional read** — when asked for your view, state it directly based on the data (e.g. "Smart Money is net YES, momentum is up, contrarian score is 40 — lean YES")

This is a personal trading terminal, not a public financial advisory service. The user makes all final decisions. Do not add disclaimers or refuse to interpret data. Speak like a quant analyst briefing a trader, not a compliance officer.

AVAILABLE TOOLS:

Portfolio: portfolio_dashboard | portfolio_close | portfolio_report | portfolio_rebalance | portfolio_liquidity
Trading:   trade_market | trade_limit | trade_orders | trade_cancel | trade_set_alert
Search:    search_markets | market_detail
Analysis:  analyze_market | analyze_whales | analyze_wallet | analyze_odds | analyze_kelly | analyze_signal | analyze_distribution | analyze_insider | analyze_holders
Monitor:   scan_insider_bulk | insider_detail

STANDARD WORKFLOW:
1. search_markets → market_detail → analyze_market → analyze_whales → analyze_signal
2. analyze_kelly for position sizing (use 1/4 Kelly as default)
3. trade_market or trade_limit to enter
4. trade_set_alert for TP/SL immediately after
5. analyze_insider before any large position — avoid CRITICAL/HIGH risk markets

RISK MANAGEMENT:
- Never trade without checking analyze_market first
- Use portfolio_liquidity before closing — wide spreads cost money
- The Kelly Criterion output is a maximum — start smaller
- CRITICAL risk in insider scan = avoid or wait for resolution
`.trim(),
    };
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // PORTFOLIO TOOLS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerTool({
    name: "portfolio_dashboard",
    label: "Portfolio Dashboard",
    description: "Show current positions, unrealized P&L, and account balance. Optionally specify account number for multi-account setups.",
    parameters: Type.Object({
      account: Type.Optional(Type.Number({ description: "Account number (1-9, default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = params.account ? ["--account", String(params.account)] : [];
      const result = await runScript("pm.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("portfolio_dashboard", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "portfolio_close",
    label: "Close Position",
    description: "Close/exit a market position. Checks liquidity before executing. Use portfolio_liquidity first to check spreads.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      auto: Type.Optional(Type.Boolean({ description: "Skip confirmation prompt (default: false)" })),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["close", params.condition_id];
      if (params.auto) args.push("--auto");
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("pm.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("portfolio_close", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "portfolio_report",
    label: "P&L Report",
    description: "Detailed profit and loss report with win/loss rates and market-by-market breakdown.",
    parameters: Type.Object({
      detailed: Type.Optional(Type.Boolean({ description: "Include full position details" })),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["report"];
      if (params.detailed) args.push("--detailed");
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("pm.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("portfolio_report", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "portfolio_rebalance",
    label: "Rebalance Suggestions",
    description: "Get equal-weight rebalancing suggestions for current portfolio.",
    parameters: Type.Object({
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["rebalance"];
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("pm.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("portfolio_rebalance", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "portfolio_liquidity",
    label: "Check Liquidity",
    description: "Check bid-ask spread and available liquidity for a market outcome before trading.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      outcome: Type.Optional(StringEnum(["Yes", "No"])),
    }),
    async execute(_id, params: any, signal) {
      const args = ["liquidity", params.condition_id];
      if (params.outcome) args.push("--outcome", params.outcome);
      const result = await runScript("pm.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("portfolio_liquidity", args, theme),
    renderResult,
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // TRADING TOOLS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerTool({
    name: "trade_market",
    label: "Market Order",
    description: "Execute a market buy or sell order immediately. Use analyze_market first to check current prices.",
    parameters: Type.Object({
      action: StringEnum(["buy", "sell"]),
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      outcome: StringEnum(["Yes", "No"]),
      amount: Type.Optional(Type.Number({ description: "USDC amount to spend (for buy)" })),
      shares: Type.Optional(Type.Number({ description: "Number of shares to sell (for sell)" })),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = [params.action, params.condition_id, "--outcome", params.outcome];
      if (params.amount) args.push("--amount", String(params.amount));
      if (params.shares) args.push("--shares", String(params.shares));
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("trade.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("trade_market", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "trade_limit",
    label: "Limit Order",
    description: "Place a limit order at a specific price. Useful for entering at better prices than market.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      outcome: StringEnum(["Yes", "No"]),
      side: StringEnum(["BUY", "SELL"]),
      price: Type.Number({ description: "Price per share (0.01 to 0.99)" }),
      amount: Type.Optional(Type.Number({ description: "USDC amount (for BUY)" })),
      shares: Type.Optional(Type.Number({ description: "Number of shares (for SELL)" })),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = [
        "limit", params.condition_id,
        "--outcome", params.outcome,
        "--side", params.side,
        "--price", String(params.price),
      ];
      if (params.amount) args.push("--amount", String(params.amount));
      if (params.shares) args.push("--shares", String(params.shares));
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("trade.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("trade_limit", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "trade_orders",
    label: "View Open Orders",
    description: "List all open/pending limit orders.",
    parameters: Type.Object({
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["orders"];
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("trade.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("trade_orders", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "trade_cancel",
    label: "Cancel Order(s)",
    description: "Cancel a specific order by ID or cancel all open orders.",
    parameters: Type.Object({
      order_id: Type.Optional(Type.String({ description: "Order ID to cancel (omit to cancel all)" })),
      all: Type.Optional(Type.Boolean({ description: "Cancel all open orders" })),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["cancel"];
      if (params.all) {
        args.push("--all");
      } else if (params.order_id) {
        args.push(params.order_id);
      }
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("trade.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("trade_cancel", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "trade_set_alert",
    label: "Set TP/SL Alert",
    description: "Set Take Profit or Stop Loss price alert. Run trade.py monitor to auto-execute when triggered.",
    parameters: Type.Object({
      type: StringEnum(["tp", "sl"]),
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      outcome: StringEnum(["Yes", "No"]),
      price: Type.Number({ description: "Trigger price (0.01 to 0.99). TP: above current. SL: below current." }),
      account: Type.Optional(Type.Number({ description: "Account number (default: 1)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = [params.type, params.condition_id, "--outcome", params.outcome, "--price", String(params.price)];
      if (params.account) args.push("--account", String(params.account));
      const result = await runScript("trade.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("trade_set_alert", args, theme),
    renderResult,
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // SEARCH TOOLS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerTool({
    name: "search_markets",
    label: "Search Markets",
    description: "Search Polymarket markets by keyword, category, probability range, volume, or deadline urgency.",
    parameters: Type.Object({
      query: Type.Optional(Type.String({ description: "Search keyword (e.g. 'Trump', 'Bitcoin')" })),
      category: Type.Optional(StringEnum([
        "crypto", "sports", "politics", "economy", "tech", "world", "entertainment"
      ])),
      prob: Type.Optional(Type.String({ description: "Probability range e.g. '80:20' = 20%-80%" })),
      min_vol: Type.Optional(Type.Number({ description: "Minimum volume in USD" })),
      urgent: Type.Optional(Type.Number({ description: "Closes within N days" })),
      sort: Type.Optional(StringEnum(["volume", "prob", "date"])),
      limit: Type.Optional(Type.Number({ description: "Max results (default: 10)" })),
      date_from: Type.Optional(Type.String({ description: "Start date YYYY-MM-DD" })),
      date_to: Type.Optional(Type.String({ description: "End date YYYY-MM-DD" })),
      fast: Type.Optional(Type.Boolean({ description: "Fast mode: only scan latest 1000 markets" })),
    }),
    async execute(_id, params: any, signal) {
      const args: string[] = [];
      if (params.query) args.push("-q", params.query);
      if (params.category) args.push("-c", params.category);
      if (params.prob) args.push("--prob", params.prob);
      if (params.min_vol) args.push("--min-vol", String(params.min_vol));
      if (params.urgent) args.push("--urgent", String(params.urgent));
      if (params.sort) args.push("--sort", params.sort);
      if (params.limit) args.push("--limit", String(params.limit));
      if (params.date_from) args.push("--date-from", params.date_from);
      if (params.date_to) args.push("--date-to", params.date_to);
      if (params.fast) args.push("--fast");
      const result = await runScript("search.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("search_markets", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "market_detail",
    label: "Market Detail",
    description: "Get full market information from a condition ID or URL slug.",
    parameters: Type.Object({
      id_or_slug: Type.String({ description: "Condition ID (0x...) or URL slug (e.g. 'trump-2024')" }),
    }),
    async execute(_id, params: any, signal) {
      const isConditionId = params.id_or_slug.startsWith("0x");
      const subcmd = isConditionId ? "detail" : "url";
      const result = await runScript("search.py", [subcmd, params.id_or_slug], signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("market_detail", args, theme),
    renderResult,
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // ANALYSIS TOOLS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerTool({
    name: "analyze_market",
    label: "Deep Market Analysis",
    description: "Full market analysis: order book depth, recent trade history, price charts, volume metrics.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
    }),
    async execute(_id, params: any, signal) {
      const result = await runScript("analyze.py", ["market", params.condition_id], signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_market", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_whales",
    label: "Whale Analysis",
    description: "Identify large position holders (whales) and their direction. Shows Smart Money vs retail positioning.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      min_value: Type.Optional(Type.Number({ description: "Minimum position value USD (default: 1000)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["whales", params.condition_id];
      if (params.min_value) args.push("--min-value", String(params.min_value));
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_whales", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_wallet",
    label: "Wallet Profile",
    description: "Deep wallet analysis: trader role classification (Smart Money/Market Maker/Whale/Loser/Retail), win/loss history, P&L.",
    parameters: Type.Object({
      address: Type.String({ description: "Wallet address (0x...)" }),
      max_trades: Type.Optional(Type.Number({ description: "Max trades to analyze (default: 500)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["wallet", params.address];
      if (params.max_trades) args.push("--max-trades", String(params.max_trades));
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_wallet", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_odds",
    label: "Historical Odds",
    description: "Historical odds analysis over 7/14/30 day lookback. Detects probability drift and significant changes. Supports event slugs or single market IDs.",
    parameters: Type.Object({
      event_slug: Type.Optional(Type.String({ description: "Event slug from URL (e.g. 'which-ai-model-best-q1')" })),
      market_id: Type.Optional(Type.String({ description: "Single market condition ID (0x...)" })),
      lookback: Type.Optional(Type.String({ description: "Lookback periods comma-separated (default: '7,14,30')" })),
      alert: Type.Optional(Type.Boolean({ description: "Output alert JSON for markets with big changes" })),
      alert_threshold: Type.Optional(Type.Number({ description: "Alert threshold % (default: 10)" })),
    }),
    async execute(_id, params: any, signal) {
      const args: string[] = ["odds"];
      if (params.event_slug) args.push(params.event_slug);
      if (params.market_id) args.push("--market", params.market_id);
      if (params.lookback) args.push("--lookback", params.lookback);
      if (params.alert) args.push("--alert");
      if (params.alert_threshold) args.push("--alert-threshold", String(params.alert_threshold));
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_odds", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_kelly",
    label: "Kelly Criterion",
    description: "Calculate optimal position size using Kelly Criterion. Returns full/half/quarter Kelly in USD. Always use conservative fraction.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      estimate: Type.Number({ description: "Your estimated true probability (0.0 to 1.0)" }),
      bankroll: Type.Number({ description: "Available capital in USD" }),
      outcome: Type.Optional(StringEnum(["Yes", "No"])),
      fraction: Type.Optional(Type.Number({ description: "Kelly fraction (default: 1.0, use 0.25 for quarter-Kelly)" })),
    }),
    async execute(_id, params: any, signal) {
      const args = [
        "kelly", params.condition_id,
        "--estimate", String(params.estimate),
        "--bankroll", String(params.bankroll),
      ];
      if (params.outcome) args.push("--outcome", params.outcome);
      if (params.fraction) args.push("--fraction", String(params.fraction));
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_kelly", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_signal",
    label: "Trading Signal",
    description: "Composite trading signal from 3 indicators: whale direction, 7-day momentum, recent buy ratio. Returns BUY YES / BUY NO / NEUTRAL.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
    }),
    async execute(_id, params: any, signal) {
      const result = await runScript("analyze.py", ["signal", params.condition_id], signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_signal", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_distribution",
    label: "Market Distribution",
    description: "Analyze position distribution by trader type. Generates contrarian signal score 0-100: >70 = strong contrarian opportunity. Smart Money vs Losers divergence.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
    }),
    async execute(_id, params: any, signal) {
      const result = await runScript("analyze.py", ["distribution", params.condition_id], signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_distribution", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_insider",
    label: "Insider Detection",
    description: "Detect suspicious pre-spike trading patterns. Identifies wallets that traded large amounts 1-24h before major price moves. Risk: LOW/MEDIUM/HIGH/CRITICAL.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Condition ID, event slug, or Polymarket URL" }),
      price_threshold: Type.Optional(Type.Number({ description: "Min price change % to flag (default: 10)" })),
      trade_threshold: Type.Optional(Type.Number({ description: "Min trade size USD (default: 5000)" })),
      detail: Type.Optional(Type.Boolean({ description: "Show detailed trade breakdown" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["insider", params.condition_id];
      if (params.price_threshold) args.push("--price-threshold", String(params.price_threshold));
      if (params.trade_threshold) args.push("--trade-threshold", String(params.trade_threshold));
      if (params.detail) args.push("--detail");
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_insider", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "analyze_holders",
    label: "Full Holder Distribution",
    description: "Complete holder distribution via Goldsky subgraph — no 20-person limit. Shows Yes/No ratios, top holders, concentration analysis.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      top: Type.Optional(Type.Number({ description: "Show top N holders (default: 20)" })),
      min_balance: Type.Optional(Type.Number({ description: "Filter by minimum balance" })),
      ratio_only: Type.Optional(Type.Boolean({ description: "Only show Yes/No ratio summary" })),
    }),
    async execute(_id, params: any, signal) {
      const args = ["holders", params.condition_id];
      if (params.top) args.push("--top", String(params.top));
      if (params.min_balance) args.push("--min-balance", String(params.min_balance));
      if (params.ratio_only) args.push("--ratio");
      const result = await runScript("analyze.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("analyze_holders", args, theme),
    renderResult,
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // MONITORING TOOLS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerTool({
    name: "scan_insider_bulk",
    label: "Bulk Insider Scan",
    description: "Async scan of hundreds of markets for insider activity. 5-10x faster than sequential scan. Use to find CRITICAL/HIGH risk markets to avoid.",
    parameters: Type.Object({
      max_markets: Type.Optional(Type.Number({ description: "Max markets to scan (default: 500)" })),
      min_vol: Type.Optional(Type.Number({ description: "Min volume USD (default: 50000)" })),
      min_risk: Type.Optional(StringEnum(["LOW", "MEDIUM", "HIGH", "CRITICAL"])),
      threshold: Type.Optional(Type.Number({ description: "Price change threshold % (default: 15)" })),
      concurrency: Type.Optional(Type.Number({ description: "Concurrent requests (default: 20)" })),
      start_index: Type.Optional(Type.Number({ description: "Resume scan from market index" })),
    }),
    async execute(_id, params: any, signal) {
      const args: string[] = [];
      if (params.max_markets) args.push("--max", String(params.max_markets));
      if (params.min_vol) args.push("--min-vol", String(params.min_vol));
      if (params.min_risk) args.push("--min-risk", params.min_risk);
      if (params.threshold) args.push("--threshold", String(params.threshold));
      if (params.concurrency) args.push("--concurrency", String(params.concurrency));
      if (params.start_index) args.push("--start-index", String(params.start_index));
      const result = await runScript("monitoring/auto_insider_scan_async.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("scan_insider_bulk", args, theme),
    renderResult,
  });

  pi.registerTool({
    name: "insider_detail",
    label: "Insider Detail Chart",
    description: "Generate ASCII price chart + insider timeline for a specific market. Use after scan_insider_bulk identifies a suspicious market.",
    parameters: Type.Object({
      condition_id: Type.String({ description: "Market condition ID (0x...)" }),
      days: Type.Optional(Type.Number({ description: "Days of history to show (default: 17)" })),
      start: Type.Optional(Type.String({ description: "Start date MM-DD" })),
      end: Type.Optional(Type.String({ description: "End date MM-DD" })),
    }),
    async execute(_id, params: any, signal) {
      const args = [params.condition_id];
      if (params.days) args.push("--days", String(params.days));
      if (params.start) args.push("--start", params.start);
      if (params.end) args.push("--end", params.end);
      const result = await runScript("monitoring/insider_detail.py", args, signal);
      return { content: [{ type: "text" as const, text: formatOutput(result) }] };
    },
    renderCall: (args, theme) => renderCall("insider_detail", args, theme),
    renderResult,
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // COMMANDS
  // ══════════════════════════════════════════════════════════════════════════════

  pi.registerCommand("pm-config", {
    description: "Set the polymarket-trader project directory",
    handler: async (_args, ctx) => {
      const current = scriptsDir
        ? scriptsDir.replace(/\/scripts$/, "")
        : "(not set)";

      const input = await ctx.ui.input(
        "Polymarket project directory",
        current,
      );
      if (!input) return;

      const resolved = resolve(input.replace(/^~/, process.env.HOME ?? ""));
      const candidateScripts = join(resolved, "scripts");

      if (!existsSync(candidateScripts)) {
        ctx.ui.notify(`Directory not found: ${candidateScripts}`, "error");
        return;
      }

      scriptsDir = candidateScripts;
      persistDir(candidateScripts);
      ctx.ui.setStatus("polymarket", "Polymarket Ready");
      ctx.ui.notify(`Polymarket directory set and saved:\n${resolved}`, "info");
    },
  });

  pi.registerCommand("pm-help", {
    description: "Show Polymarket tool quick reference",
    handler: async (_args, ctx) => {
      ctx.ui.notify(
        `PORTFOLIO: portfolio_dashboard | portfolio_close | portfolio_report | portfolio_rebalance | portfolio_liquidity

TRADING: trade_market | trade_limit | trade_orders | trade_cancel | trade_set_alert

SEARCH: search_markets | market_detail

ANALYSIS: analyze_market | analyze_whales | analyze_wallet | analyze_odds | analyze_kelly | analyze_signal | analyze_distribution | analyze_insider | analyze_holders

MONITORING: scan_insider_bulk | insider_detail

WORKFLOW: search → market_detail → analyze_market → analyze_whales → analyze_signal → analyze_kelly → trade_market → trade_set_alert`,
        "info",
      );
    },
  });
}
