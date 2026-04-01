/**
 * Crypto Onchain Monitor — Cross-chain capital flow & DeFi activity tracker
 *
 * Monitors onchain activity across multiple chains using 100% free APIs:
 *   DeFiLlama  — TVL, protocols, bridges, stablecoins, RWA
 *   DexScreener — DEX trading pairs and volumes
 *   CoinGecko   — Global market data
 *
 * Spawns a 5-pane tmux agent team for parallel monitoring.
 *
 * Tools:
 *   get_chain_tvl        — Chain TVL rankings + 24h/7d changes
 *   get_bridge_flows     — Cross-chain bridge volumes + net flows
 *   get_stablecoin_data  — Stablecoin supply, chain distribution, peg health
 *   get_rwa_protocols    — Real World Asset protocol metrics
 *   get_dex_activity     — Hot DEX pairs + volume from DexScreener
 *   get_protocol_flows   — Protocol inflow/outflow ranking
 *   spawn_monitor_team   — Launch 5-pane tmux agent team
 *
 * Commands:
 *   /onchain-status   — Quick live snapshot
 *   /onchain-refresh  — Force cache refresh
 *
 * Usage: pi -e extensions/crypto-onchain-monitor.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";
import { Type } from "@sinclair/typebox";
import { Text, truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { spawnSync } from "child_process";
import { applyExtensionDefaults } from "../themeMap.ts";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ChainTVL {
  name: string;
  tvl: number;
  change_1d?: number;
  change_7d?: number;
}

interface Cache {
  chains?: ChainTVL[];
  stablecoinMcap?: number;
  totalTvl?: number;
  lastFetch?: number;
}

// ── State ──────────────────────────────────────────────────────────────────────

let cache: Cache = {};
const CACHE_TTL = 5 * 60 * 1000; // 5 min
let widgetCtx: any;

// ── API Helpers ────────────────────────────────────────────────────────────────

async function apiGet(url: string): Promise<any> {
  const res = await fetch(url, {
    headers: { Accept: "application/json", "User-Agent": "pi-onchain-monitor/1.0" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.json();
}

function fmtUsd(n: number): string {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${(n / 1e3).toFixed(0)}K`;
}

function fmtPct(p?: number): string {
  if (p === undefined || p === null) return "";
  const sign = p >= 0 ? "+" : "";
  return `${sign}${p.toFixed(1)}%`;
}

// ── Cache Refresh ──────────────────────────────────────────────────────────────

async function refreshCache(force = false): Promise<void> {
  if (!force && cache.lastFetch && Date.now() - cache.lastFetch < CACHE_TTL) return;
  try {
    const [chainsRaw, stablesRaw] = await Promise.all([
      apiGet("https://api.llama.fi/v2/chains"),
      apiGet("https://stablecoins.llama.fi/stablecoins?includePrices=true"),
    ]);

    const chains: ChainTVL[] = chainsRaw
      .filter((c: any) => c.tvl > 0)
      .sort((a: any, b: any) => b.tvl - a.tvl)
      .slice(0, 20)
      .map((c: any) => ({ name: c.name, tvl: c.tvl, change_1d: c.change_1d, change_7d: c.change_7d }));

    const stablecoinMcap = (stablesRaw?.peggedAssets ?? [])
      .reduce((s: number, st: any) => s + (st.circulating?.peggedUSD || 0), 0);

    cache = {
      chains,
      stablecoinMcap,
      totalTvl: chains.reduce((s, c) => s + c.tvl, 0),
      lastFetch: Date.now(),
    };
  } catch { /* keep stale */ }
}

// ── Extension ──────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── Boot ────────────────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    applyExtensionDefaults(import.meta.url, ctx);
    widgetCtx = ctx;
    ctx.ui.setStatus("onchain", "⟳ loading...");

    refreshCache(true).then(() => {
      const tvl = cache.totalTvl ? fmtUsd(cache.totalTvl) : "?";
      const sc = cache.stablecoinMcap ? fmtUsd(cache.stablecoinMcap) : "?";
      ctx.ui.setStatus("onchain", `TVL ${tvl} · SC ${sc}`);
    });

    ctx.ui.notify(
      "⛓  Crypto Onchain Monitor\n" +
      "APIs: DeFiLlama · DexScreener · CoinGecko\n\n" +
      "Tools: get_chain_tvl  get_bridge_flows  get_stablecoin_data\n" +
      "       get_rwa_protocols  get_dex_activity  get_protocol_flows\n" +
      "       spawn_monitor_team\n\n" +
      "/onchain-status  — live snapshot\n" +
      "/onchain-refresh — force refresh",
      "info",
    );

    ctx.ui.setFooter((_tui, theme, footerData) => ({
      dispose: footerData.onBranchChange(() => {}),
      invalidate() {},
      render(width: number): string[] {
        const tvl = cache.totalTvl ? fmtUsd(cache.totalTvl) : "loading";
        const sc = cache.stablecoinMcap ? fmtUsd(cache.stablecoinMcap) : "—";
        const top3 = (cache.chains ?? []).slice(0, 3).map(c => c.name).join(" · ");
        const age = cache.lastFetch
          ? `${Math.round((Date.now() - cache.lastFetch) / 60000)}m ago`
          : "—";
        const left =
          theme.fg("accent", " ⛓ ONCHAIN") +
          theme.fg("dim", "  TVL: ") +
          theme.fg("muted", tvl) +
          theme.fg("dim", "  SC: ") +
          theme.fg("muted", sc) +
          theme.fg("dim", "  " + top3);
        const right = theme.fg("dim", `${age} `);
        const pad = " ".repeat(Math.max(1, width - visibleWidth(left) - visibleWidth(right)));
        return [truncateToWidth(left + pad + right, width)];
      },
    }));
  });

  // ── Tool 1: Chain TVL ────────────────────────────────────────────────────────

  pi.registerTool({
    name: "get_chain_tvl",
    label: "Chain TVL",
    description: "Get TVL rankings for all major chains from DeFiLlama. Returns TVL, 24h and 7d changes.",
    parameters: Type.Object({
      top_n: Type.Optional(Type.Number({ description: "Number of top chains (default: 20)" })),
      chain: Type.Optional(Type.String({ description: "Filter to specific chain name (e.g. Ethereum, Arbitrum)" })),
    }),
    async execute(_id, params: any) {
      const raw = await apiGet("https://api.llama.fi/v2/chains");
      let chains: any[] = raw.filter((c: any) => c.tvl > 0).sort((a: any, b: any) => b.tvl - a.tvl);
      if (params.chain) {
        chains = chains.filter(c => c.name.toLowerCase().includes(params.chain.toLowerCase()));
      } else {
        chains = chains.slice(0, params.top_n ?? 20);
      }
      const rows = chains.map((c: any, i: number) =>
        `${String(i + 1).padStart(2)}. ${c.name.padEnd(18)} ${fmtUsd(c.tvl).padStart(10)}` +
        (c.change_1d != null ? `  24h: ${fmtPct(c.change_1d).padStart(7)}` : "") +
        (c.change_7d != null ? `  7d: ${fmtPct(c.change_7d).padStart(7)}` : "")
      ).join("\n");
      const total = chains.reduce((s: number, c: any) => s + c.tvl, 0);
      const text = `Chain TVL Rankings — ${new Date().toUTCString()}\n\n${rows}\n\nShown total: ${fmtUsd(total)}`;
      return {
        content: [{ type: "text" as const, text }],
        details: { chains, timestamp: Date.now() },
      };
    },
    renderCall(_args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("get_chain_tvl")), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const preview = (result.content?.[0]?.text ?? "").split("\n")[2] ?? "";
      return new Text(theme.fg("muted", preview.trim()), 0, 0);
    },
  });

  // ── Tool 2: Bridge Flows ─────────────────────────────────────────────────────

  pi.registerTool({
    name: "get_bridge_flows",
    label: "Bridge Flows",
    description: "Get cross-chain bridge volumes from DeFiLlama Bridges API. Shows top bridges, 24h volume, and chain pairs.",
    parameters: Type.Object({
      top_n: Type.Optional(Type.Number({ description: "Number of bridges to show (default: 15)" })),
    }),
    async execute(_id, params: any) {
      const raw = await apiGet("https://bridges.llama.fi/bridges?includeChains=true");
      const bridges: any[] = (raw?.bridges ?? [])
        .filter((b: any) => (b.volumePrevDay ?? 0) > 0)
        .sort((a: any, b: any) => b.volumePrevDay - a.volumePrevDay)
        .slice(0, params.top_n ?? 15);

      const rows = bridges.map((b: any, i: number) => {
        const chains = (b.chains ?? []).slice(0, 4).join(" ↔ ");
        return `${String(i + 1).padStart(2)}. ${(b.displayName ?? b.name ?? "?").padEnd(22)} ${fmtUsd(b.volumePrevDay).padStart(10)}/day  ${chains}`;
      }).join("\n");

      const totalVol = bridges.reduce((s: number, b: any) => s + (b.volumePrevDay ?? 0), 0);
      const text = `Bridge Activity — ${new Date().toUTCString()}\n\n${rows}\n\nTotal bridge vol (24h): ${fmtUsd(totalVol)}`;
      return {
        content: [{ type: "text" as const, text }],
        details: { bridges, totalVol, timestamp: Date.now() },
      };
    },
    renderCall(_args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("get_bridge_flows")), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const v = (result.details as any)?.totalVol;
      return new Text(theme.fg("muted", `Bridge vol 24h: ${v ? fmtUsd(v) : "?"}`), 0, 0);
    },
  });

  // ── Tool 3: Stablecoin Data ──────────────────────────────────────────────────

  pi.registerTool({
    name: "get_stablecoin_data",
    label: "Stablecoin Data",
    description: "Get stablecoin supply, chain distribution, and peg health from DeFiLlama. Covers USDT, USDC, DAI, FRAX, PYUSD, etc.",
    parameters: Type.Object({
      focus: Type.Optional(StringEnum(["by-stablecoin", "by-chain", "peg-deviations"])),
    }),
    async execute(_id, params: any) {
      const [stablesRaw, chainsRaw] = await Promise.all([
        apiGet("https://stablecoins.llama.fi/stablecoins?includePrices=true"),
        apiGet("https://stablecoins.llama.fi/stablecoinchains"),
      ]);
      const stables: any[] = stablesRaw?.peggedAssets ?? [];
      const focus = params.focus ?? "by-stablecoin";
      let text = `Stablecoin Monitor — ${new Date().toUTCString()}\n\n`;

      if (focus === "by-stablecoin") {
        const top = stables
          .sort((a: any, b: any) => (b.circulating?.peggedUSD ?? 0) - (a.circulating?.peggedUSD ?? 0))
          .slice(0, 15);
        text += "Top Stablecoins by Supply:\n";
        top.forEach((s: any, i: number) => {
          const mcap = fmtUsd(s.circulating?.peggedUSD ?? 0);
          const price = s.price ? ` @ $${Number(s.price).toFixed(4)}` : "";
          const warn = s.price && Math.abs(s.price - 1) > 0.005 ? "  ⚠️ PEG DEVIATION" : "";
          text += `${String(i + 1).padStart(2)}. ${(s.symbol ?? "?").padEnd(8)} ${mcap.padStart(10)}${price}${warn}\n`;
        });
        const total = stables.reduce((s: number, st: any) => s + (st.circulating?.peggedUSD ?? 0), 0);
        text += `\nTotal stablecoin supply: ${fmtUsd(total)}`;

      } else if (focus === "by-chain") {
        const top = (chainsRaw ?? [])
          .sort((a: any, b: any) => (b.totalCirculatingUSD?.peggedUSD ?? 0) - (a.totalCirculatingUSD?.peggedUSD ?? 0))
          .slice(0, 15);
        text += "Stablecoin Supply by Chain:\n";
        top.forEach((c: any, i: number) => {
          text += `${String(i + 1).padStart(2)}. ${(c.name ?? "?").padEnd(18)} ${fmtUsd(c.totalCirculatingUSD?.peggedUSD ?? 0).padStart(10)}\n`;
        });

      } else if (focus === "peg-deviations") {
        const devs = stables
          .filter((s: any) => s.price && Math.abs(s.price - 1) > 0.002)
          .sort((a: any, b: any) => Math.abs(b.price - 1) - Math.abs(a.price - 1))
          .slice(0, 20);
        text += "Peg Deviations (>0.2%):\n";
        if (devs.length === 0) {
          text += "No significant deviations detected ✓\n";
        } else {
          devs.forEach((s: any) => {
            const dev = ((s.price - 1) * 100).toFixed(3);
            const sign = s.price > 1 ? "+" : "";
            text += `⚠️  ${s.symbol}: $${Number(s.price).toFixed(4)} (${sign}${dev}%)\n`;
          });
        }
      }

      return {
        content: [{ type: "text" as const, text }],
        details: { timestamp: Date.now() },
      };
    },
    renderCall(args, theme) {
      const focus = (args as any).focus ?? "by-stablecoin";
      return new Text(theme.fg("toolTitle", theme.bold("get_stablecoin_data ")) + theme.fg("dim", focus), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const lines = (result.content?.[0]?.text ?? "").split("\n");
      const total = lines.find(l => l.includes("Total")) ?? lines[3] ?? "";
      return new Text(theme.fg("muted", total.trim()), 0, 0);
    },
  });

  // ── Tool 4: RWA Protocols ────────────────────────────────────────────────────

  pi.registerTool({
    name: "get_rwa_protocols",
    label: "RWA Protocols",
    description: "Get Real World Asset (RWA) protocol metrics from DeFiLlama. Covers Ondo, Centrifuge, Maple, Superstate, Backed, Goldfinch.",
    parameters: Type.Object({
      min_tvl_usd: Type.Optional(Type.Number({ description: "Minimum TVL in USD (default: 1000000)" })),
    }),
    async execute(_id, params: any) {
      const protocols: any[] = await apiGet("https://api.llama.fi/protocols");
      const RWA_NAMES = ["ondo", "centrifuge", "maple", "superstate", "backed", "goldfinch",
        "securitize", "openeden", "matrixdock", "hashnote", "steadefi"];
      const RWA_CATS = ["rwa", "real world", "tokenized"];
      const minTvl = params.min_tvl_usd ?? 1_000_000;

      const rwa = protocols
        .filter((p: any) => {
          const name = (p.name ?? "").toLowerCase();
          const cat = (p.category ?? "").toLowerCase();
          return (
            RWA_NAMES.some(n => name.includes(n)) ||
            RWA_CATS.some(c => cat.includes(c))
          ) && (p.tvl ?? 0) >= minTvl;
        })
        .sort((a: any, b: any) => b.tvl - a.tvl)
        .slice(0, 25);

      let text = `RWA Protocol Monitor — ${new Date().toUTCString()}\n\n`;

      if (rwa.length === 0) {
        text += "No RWA protocols found above minimum TVL threshold.\nTry lowering min_tvl_usd.\n";
      } else {
        rwa.forEach((p: any, i: number) => {
          const chg = p.change_1d != null ? `  24h: ${fmtPct(p.change_1d)}` : "";
          const chg7 = p.change_7d != null ? `  7d: ${fmtPct(p.change_7d)}` : "";
          text += `${String(i + 1).padStart(2)}. ${(p.name ?? "?").padEnd(20)} ${fmtUsd(p.tvl ?? 0).padStart(10)}${chg}${chg7}\n`;
          if (p.chains?.length) {
            text += `    Chains: ${p.chains.slice(0, 5).join(", ")}\n`;
          }
        });
        const total = rwa.reduce((s: number, p: any) => s + (p.tvl ?? 0), 0);
        text += `\nTotal RWA TVL: ${fmtUsd(total)} (${rwa.length} protocols)`;
      }

      return {
        content: [{ type: "text" as const, text }],
        details: { count: rwa.length, totalTvl: rwa.reduce((s: number, p: any) => s + (p.tvl ?? 0), 0), timestamp: Date.now() },
      };
    },
    renderCall(_args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("get_rwa_protocols")), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const d = result.details as any;
      return new Text(theme.fg("muted", `RWA TVL: ${d?.totalTvl ? fmtUsd(d.totalTvl) : "?"} · ${d?.count ?? 0} protocols`), 0, 0);
    },
  });

  // ── Tool 5: DEX Activity ─────────────────────────────────────────────────────

  pi.registerTool({
    name: "get_dex_activity",
    label: "DEX Activity",
    description: "Get DEX trading activity from DexScreener. Search hot pairs, tokens, or trending pairs by chain.",
    parameters: Type.Object({
      query: Type.String({ description: "Token/pair to search (e.g. ETH, USDC, WBTC)" }),
      chain: Type.Optional(StringEnum(["ethereum", "bsc", "arbitrum", "base", "polygon", "solana", "all"])),
    }),
    async execute(_id, params: any) {
      const q = params.query || "USDC";
      const raw = await apiGet(`https://api.dexscreener.com/latest/dex/search?q=${encodeURIComponent(q)}`);
      let pairs: any[] = raw?.pairs ?? [];

      if (params.chain && params.chain !== "all") {
        pairs = pairs.filter((p: any) => p.chainId === params.chain);
      }
      pairs = pairs
        .filter((p: any) => (p.volume?.h24 ?? 0) > 1000)
        .sort((a: any, b: any) => (b.volume?.h24 ?? 0) - (a.volume?.h24 ?? 0))
        .slice(0, 15);

      let text = `DEX Activity — "${q}" — ${new Date().toUTCString()}\n\n`;
      if (pairs.length === 0) {
        text += "No pairs found with significant volume. Try a different query.\n";
      } else {
        pairs.forEach((p: any, i: number) => {
          const base = p.baseToken?.symbol ?? "?";
          const quote = p.quoteToken?.symbol ?? "?";
          const price = p.priceUsd ? `$${Number(p.priceUsd).toPrecision(5)}` : "?";
          const vol = fmtUsd(p.volume?.h24 ?? 0);
          const liq = fmtUsd(p.liquidity?.usd ?? 0);
          const chg = p.priceChange?.h24 != null
            ? `  ${fmtPct(p.priceChange.h24)}`
            : "";
          text += `${String(i + 1).padStart(2)}. ${base}/${quote} [${p.chainId}] @ ${price}${chg}\n`;
          text += `    Vol 24h: ${vol}  Liq: ${liq}  DEX: ${p.dexId ?? "?"}\n`;
        });
      }
      return {
        content: [{ type: "text" as const, text }],
        details: { pairCount: pairs.length, timestamp: Date.now() },
      };
    },
    renderCall(args, theme) {
      const q = (args as any).query ?? "?";
      return new Text(theme.fg("toolTitle", theme.bold("get_dex_activity ")) + theme.fg("dim", q), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const d = result.details as any;
      return new Text(theme.fg("muted", `${d?.pairCount ?? 0} pairs found`), 0, 0);
    },
  });

  // ── Tool 6: Protocol Flows ───────────────────────────────────────────────────

  pi.registerTool({
    name: "get_protocol_flows",
    label: "Protocol Flows",
    description: "Get protocol TVL inflow/outflow rankings from DeFiLlama. Identifies capital gaining or losing protocols.",
    parameters: Type.Object({
      category: Type.Optional(Type.String({ description: "Filter by category: Lending, DEX, Liquid Staking, Bridge, Yield" })),
      sort_by: Type.Optional(StringEnum(["change_1d", "change_7d", "tvl"])),
      top_n: Type.Optional(Type.Number({ description: "Protocols to show (default: 20)" })),
    }),
    async execute(_id, params: any) {
      const protocols: any[] = await apiGet("https://api.llama.fi/protocols");
      let filtered = protocols.filter((p: any) => (p.tvl ?? 0) > 1_000_000);

      if (params.category) {
        filtered = filtered.filter((p: any) =>
          (p.category ?? "").toLowerCase().includes(params.category.toLowerCase())
        );
      }

      const sortBy = params.sort_by ?? "change_1d";
      filtered.sort((a: any, b: any) => {
        if (sortBy === "tvl") return b.tvl - a.tvl;
        const key = sortBy as "change_1d" | "change_7d";
        return Math.abs(b[key] ?? 0) - Math.abs(a[key] ?? 0);
      });

      const top = filtered.slice(0, params.top_n ?? 20);
      const gainers = filtered.filter((p: any) => (p.change_1d ?? 0) > 5).slice(0, 8);
      const losers = filtered.filter((p: any) => (p.change_1d ?? 0) < -5).slice(0, 8);

      let text = `Protocol Capital Flows — ${new Date().toUTCString()}\n`;
      if (params.category) text += `Category: ${params.category}\n`;
      text += "\n";

      if (!params.category) {
        if (gainers.length > 0) {
          text += "📈 Top Inflows (24h):\n";
          gainers.forEach(p => {
            text += `  ${p.name.padEnd(22)} ${fmtUsd(p.tvl).padStart(10)}  +${(p.change_1d ?? 0).toFixed(1)}%\n`;
          });
          text += "\n";
        }
        if (losers.length > 0) {
          text += "📉 Top Outflows (24h):\n";
          losers.forEach(p => {
            text += `  ${p.name.padEnd(22)} ${fmtUsd(p.tvl).padStart(10)}   ${(p.change_1d ?? 0).toFixed(1)}%\n`;
          });
          text += "\n";
        }
      } else {
        top.forEach((p: any, i: number) => {
          text += `${String(i + 1).padStart(2)}. ${p.name.padEnd(22)} ${fmtUsd(p.tvl).padStart(10)}`;
          if (p.change_1d != null) text += `  24h: ${fmtPct(p.change_1d).padStart(7)}`;
          text += "\n";
        });
      }

      return {
        content: [{ type: "text" as const, text }],
        details: { count: top.length, timestamp: Date.now() },
      };
    },
    renderCall(args, theme) {
      const cat = (args as any).category ?? "all";
      return new Text(theme.fg("toolTitle", theme.bold("get_protocol_flows ")) + theme.fg("dim", cat), 0, 0);
    },
    renderResult(result, _opts, theme) {
      const lines = (result.content?.[0]?.text ?? "").split("\n").filter(l => l.trim());
      return new Text(theme.fg("muted", lines[2]?.trim() ?? ""), 0, 0);
    },
  });

  // ── Tool 7: Spawn Monitor Team (tmux) ────────────────────────────────────────

  pi.registerTool({
    name: "spawn_monitor_team",
    label: "Spawn Monitor Team",
    description: "Launch a 5-window tmux session with parallel Pi agents monitoring different onchain aspects: chain TVL, bridge flows, stablecoins/RWA, DEX activity, and orchestrator.",
    parameters: Type.Object({
      session: Type.Optional(Type.String({ description: "tmux session name (default: onchain-monitor)" })),
      model: Type.Optional(Type.String({ description: "Model for agents (default: anthropic/claude-haiku-4-5-20251001)" })),
    }),
    async execute(_id, params: any) {
      const session = params.session ?? "onchain-monitor";
      const model = params.model ?? "anthropic/claude-haiku-4-5-20251001";

      const agents = [
        {
          name: "chain-tvl",
          task: "You are a chain TVL monitor. Fetch https://api.llama.fi/v2/chains using bash curl, parse the JSON, show top 20 chains by TVL with 24h changes in a formatted table. Highlight chains with >5% daily moves. Then analyze what the data means for capital flow trends.",
        },
        {
          name: "bridge-flows",
          task: "You are a cross-chain bridge monitor. Fetch https://bridges.llama.fi/bridges?includeChains=true using bash curl. Show top 15 bridges by 24h volume with chain pairs. Calculate net flow direction for major chains (Ethereum, Arbitrum, Base, Optimism). Identify unusual bridge activity patterns.",
        },
        {
          name: "stablecoin-rwa",
          task: "You are a stablecoin and RWA monitor. Fetch (1) https://stablecoins.llama.fi/stablecoins?includePrices=true and (2) https://api.llama.fi/protocols using bash curl. Report: stablecoin supply by top issuers, any peg deviations >0.2%, and RWA protocol TVL (search for ondo, centrifuge, maple, superstate). Flag any anomalies.",
        },
        {
          name: "dex-activity",
          task: "You are a DEX activity monitor. Fetch (1) https://api.dexscreener.com/latest/dex/search?q=WETH and (2) https://api.coingecko.com/api/v3/global using bash curl. Show top WETH pairs by volume, global DeFi TVL, and market dominance stats. Also check https://api.dexscreener.com/latest/dex/search?q=USDC for stablecoin pair activity.",
        },
        {
          name: "orchestrator",
          task: "You are the onchain monitoring orchestrator. Fetch comprehensive data from https://api.llama.fi/protocols using bash curl (parse JSON with python3 or jq). Identify: (1) top 5 protocols by TVL, (2) top 5 gainers by 1d change, (3) top 5 losers by 1d change. Then synthesize a 5-bullet executive summary of current DeFi market conditions. Format clearly for investors.",
        },
      ];

      function tmux(...args: string[]): boolean {
        return spawnSync("tmux", args, { stdio: "pipe" }).status === 0;
      }

      const results: string[] = [];

      // Kill existing session
      tmux("kill-session", "-t", session);

      // Create new session with first window
      if (!tmux("new-session", "-d", "-s", session, "-n", agents[0].name)) {
        return {
          content: [{ type: "text" as const, text: "Failed to create tmux session. Is tmux installed?\n\nbrew install tmux" }],
          details: { error: "tmux unavailable", timestamp: Date.now() },
        };
      }
      results.push(`✓ Window 1: ${agents[0].name}`);

      const cmd0 = `pi -p --no-extensions --model '${model}' '${agents[0].task.replace(/'/g, "\\'")}' ; echo ''; echo '--- Done. Press Enter ---' ; read`;
      tmux("send-keys", "-t", `${session}:0`, cmd0, "Enter");

      // Create windows for remaining agents
      for (let i = 1; i < agents.length; i++) {
        tmux("new-window", "-t", session, "-n", agents[i].name);
        const cmd = `pi -p --no-extensions --model '${model}' '${agents[i].task.replace(/'/g, "\\'")}' ; echo ''; echo '--- Done. Press Enter ---' ; read`;
        tmux("send-keys", "-t", `${session}:${i}`, cmd, "Enter");
        results.push(`✓ Window ${i + 1}: ${agents[i].name}`);
      }

      // Select orchestrator window
      tmux("select-window", "-t", `${session}:${agents.length - 1}`);

      const text =
        `Onchain Monitor Team launched!\n\n` +
        `Session: tmux attach -t ${session}\n\n` +
        `Windows:\n${results.join("\n")}\n\n` +
        `Switch windows: Ctrl+B then 0-4\n` +
        `Each agent fetches live data from free APIs and reports findings.`;

      return {
        content: [{ type: "text" as const, text }],
        details: { session, agentCount: agents.length, timestamp: Date.now() },
      };
    },
    renderCall(args, theme) {
      const s = (args as any).session ?? "onchain-monitor";
      return new Text(
        theme.fg("toolTitle", theme.bold("spawn_monitor_team ")) +
        theme.fg("accent", s),
        0, 0,
      );
    },
    renderResult(result, _opts, theme) {
      const d = result.details as any;
      if (d?.error) return new Text(theme.fg("error", `Error: ${d.error}`), 0, 0);
      return new Text(
        theme.fg("success", `✓ ${d?.agentCount ?? 0} agents launched`) +
        theme.fg("dim", ` — tmux attach -t ${d?.session ?? "?"}`),
        0, 0,
      );
    },
  });

  // ── System Prompt ────────────────────────────────────────────────────────────

  pi.on("before_agent_start", async () => {
    return {
      appendSystemPrompt: `
## Crypto Onchain Monitor

You are equipped with live onchain monitoring tools powered by free APIs:
- **DeFiLlama** (api.llama.fi, bridges.llama.fi, stablecoins.llama.fi): TVL, protocols, bridges, stablecoins, RWA
- **DexScreener** (api.dexscreener.com): DEX trading pairs and volume
- **CoinGecko** (api.coingecko.com): Global market data and prices

### Available Tools
| Tool | Purpose |
|------|---------|
| \`get_chain_tvl\` | Chain TVL rankings with 24h/7d changes |
| \`get_bridge_flows\` | Cross-chain bridge volumes and net flows |
| \`get_stablecoin_data\` | Stablecoin supply, chain distribution, peg health |
| \`get_rwa_protocols\` | Real World Asset protocol metrics |
| \`get_dex_activity\` | Hot DEX pairs and trading volumes |
| \`get_protocol_flows\` | Protocol inflow/outflow by category |
| \`spawn_monitor_team\` | Launch 5-window tmux parallel monitoring team |

### Analysis Framework
1. **Capital rotation** — Which chains/protocols are gaining/losing TVL?
2. **Stablecoin signals** — Supply growing = risk-on; moving to savings = risk-off
3. **Bridge flows** — Net bridge flows reveal ecosystem confidence
4. **RWA growth** — Tokenized real-world assets = institutional adoption signal
5. **DEX volume** — High vol + rising price = organic; high vol + falling = selling pressure

### Key Alert Thresholds
- Peg deviation > 0.5% → stablecoin risk
- Chain TVL drop > 10% in 7d → ecosystem concern
- Bridge volume spike > 3x normal → capital movement event
- RWA TVL growth > 20% in 30d → institutional signal
`,
    };
  });

  // ── Commands ─────────────────────────────────────────────────────────────────

  pi.registerCommand("onchain-status", {
    description: "Show live onchain status snapshot",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      ctx.ui.notify("Fetching live onchain data...", "info");
      try {
        await refreshCache(true);
        const tvl = cache.totalTvl ? fmtUsd(cache.totalTvl) : "?";
        const sc = cache.stablecoinMcap ? fmtUsd(cache.stablecoinMcap) : "?";
        const top5 = (cache.chains ?? []).slice(0, 5).map((c, i) =>
          `  ${i + 1}. ${c.name.padEnd(18)} ${fmtUsd(c.tvl).padStart(10)}${c.change_1d != null ? `  ${fmtPct(c.change_1d)}` : ""}`
        ).join("\n");
        ctx.ui.setStatus("onchain", `TVL ${tvl} · SC ${sc}`);
        ctx.ui.notify(
          `Onchain Snapshot — ${new Date().toUTCString()}\n\n` +
          `Total DeFi TVL:    ${tvl}\n` +
          `Stablecoin Mcap:   ${sc}\n\n` +
          `Top Chains:\n${top5}`,
          "info",
        );
      } catch (err: any) {
        ctx.ui.notify(`Error: ${err.message}`, "error");
      }
    },
  });

  pi.registerCommand("onchain-refresh", {
    description: "Force refresh all onchain data caches",
    handler: async (_args, ctx) => {
      widgetCtx = ctx;
      cache = {};
      ctx.ui.notify("Refreshing...", "info");
      await refreshCache(true);
      const tvl = cache.totalTvl ? fmtUsd(cache.totalTvl) : "?";
      const sc = cache.stablecoinMcap ? fmtUsd(cache.stablecoinMcap) : "?";
      ctx.ui.setStatus("onchain", `TVL ${tvl} · SC ${sc}`);
      ctx.ui.notify(`Refreshed. TVL: ${tvl}  Stablecoins: ${sc}`, "success");
    },
  });
}
