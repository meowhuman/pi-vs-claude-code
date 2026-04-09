set dotenv-load := true

default:
    @just --list

# g1

# 1. default pi
pi:
    pi

# pi-dc
pi-dc:
    pi -e extensions/damage-control.ts -e extensions/minimal.ts

# pi-multi-agent: Launches the Agent Chain orchestrator to build websites
pi-multi-agent:
    pi -e extensions/agent-chain.ts -e extensions/tool-counter-widget.ts -e extensions/damage-control.ts -e extensions/session-replay.ts

# 2. Pure focus pi: strip footer and status line entirely
ext-pure-focus:
    pi -e extensions/pure-focus.ts

# 3. Minimal pi: model name + 10-block context meter
ext-minimal:
    pi -e extensions/minimal.ts -e extensions/theme-cycler.ts

# 4. Cross-agent pi: load commands from .claude/, .gemini/, .codex/ dirs
ext-cross-agent:
    pi -e extensions/cross-agent.ts -e extensions/minimal.ts

# 5. Purpose gate pi: declare intent before working, persistent widget, focus the system prompt on the ONE PURPOSE for this agent
ext-purpose-gate:
    pi -e extensions/purpose-gate.ts -e extensions/minimal.ts

# 6. Customized footer pi: Tool counter, model, branch, cwd, cost, etc.
ext-tool-counter:
    pi -e extensions/tool-counter.ts

# 7. Tool counter widget: tool call counts in a below-editor widget
ext-tool-counter-widget:
    pi -e extensions/tool-counter-widget.ts -e extensions/minimal.ts

# 8. Subagent widget: /sub <task> with live streaming progress
ext-subagent-widget:
    pi -e extensions/subagent-widget.ts -e extensions/pure-focus.ts -e extensions/theme-cycler.ts

# 9. TillDone: task-driven discipline — define tasks before working
ext-tilldone:
    pi -e extensions/tilldone.ts -e extensions/theme-cycler.ts

#g2

# 10. Agent team: dispatcher orchestrator with team select and grid dashboard
ext-agent-team:
    pi -e extensions/agent-team.ts -e extensions/theme-cycler.ts

# 11. System select: /system to pick an agent persona as system prompt
ext-system-select:
    pi -e extensions/system-select.ts -e extensions/minimal.ts -e extensions/theme-cycler.ts

# 12. Launch with Damage-Control safety auditing
ext-damage-control:
    pi -e extensions/damage-control.ts -e extensions/minimal.ts -e extensions/theme-cycler.ts

# 13. Agent chain: sequential pipeline orchestrator
ext-agent-chain:
    pi -e extensions/agent-chain.ts -e extensions/theme-cycler.ts

#g3

# 14. Pi Pi: meta-agent that builds Pi agents with parallel expert research
ext-pi-pi:
    pi -e extensions/pi-pi.ts -e extensions/theme-cycler.ts

#ext

# 15. Session Replay: scrollable timeline overlay of session history (legit)
ext-session-replay:
    pi -e extensions/session-replay.ts -e extensions/minimal.ts

# 16. Theme cycler: Ctrl+X forward, Ctrl+Q backward, /theme picker
ext-theme-cycler:
    pi -e extensions/theme-cycler.ts -e extensions/minimal.ts

# polymarket: specialized prediction market trading agent
ext-polymarket:
    pi -e extensions/polymarket.ts -e extensions/theme-cycler.ts

# crypto-onchain-monitor: cross-chain capital flow & DeFi activity tracker (DeFiLlama + DexScreener)
ext-onchain:
    pi -e extensions/crypto-onchain-monitor.ts -e extensions/theme-cycler.ts

# crypto-onchain-chain: run onchain-monitor chain pipeline (scout → analysis → RWA → report)
ext-onchain-chain:
    pi -e extensions/agent-chain.ts -e extensions/crypto-onchain-monitor.ts -e extensions/theme-cycler.ts

# music: Full music research board (deep-researcher + youtube-curator + genre-historian + listening-guide)
music:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# music-jazz: Jazz deep dive (deep-researcher + genre-historian)
music-jazz:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# music-discovery: Find new music (youtube-curator + listening-guide)
music-discovery:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# intel: Strategic Intel Board — 3 experts (group + /select for 1-on-1)
intel:
    pi -e extensions/boards/intel-board.ts -e extensions/theme-cycler.ts

# geo: 1-on-1 with Geopolitics Analyst (shared expert)
ext-geo:
    EXPERT=geopolitics-analyst pi -e extensions/boards/meta-expert-session.ts -e extensions/theme-cycler.ts

# markets: 1-on-1 with Global Markets Expert (shared expert)
ext-markets:
    EXPERT=global-markets-expert pi -e extensions/boards/meta-expert-session.ts -e extensions/theme-cycler.ts

# military: 1-on-1 with Military Expert (shared expert)
ext-military:
    EXPERT=military-expert pi -e extensions/boards/meta-expert-session.ts -e extensions/theme-cycler.ts

# meta: Full cross-domain analysis (investment + drip + ai-tools + geopolitics)
meta:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-strategic: Investment + Drip boards (business strategy questions)
meta-strategic:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-tech: AI Tools + Investment boards (tech policy questions)
meta-tech:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-creative: Drip + AI Tools boards (creative tech questions)
meta-creative:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-sports: Football betting + Investment boards (sports betting analysis)
meta-sports:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# drip: Drip Music strategic decision board (full board)
drip:
    pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-quick: Quick 2-member sanity check (revenue + contrarian)
drip-quick:
    pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-marketing: Marketing campaign decisions
drip-marketing:
    BOARD_PRESET=marketing-campaign pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-grants: Funding & government relations decisions
drip-grants:
    BOARD_PRESET=grants-funding pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-programming: Programming & artist decisions
drip-programming:
    BOARD_PRESET=programming pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# inv: Investment Adviser Board — Mode A auto (all members, use board_begin)
inv:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-discuss: Investment Adviser Board — Mode B interactive (you sit in, use board_discuss)
inv-discuss:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-swing: Swing-trade preset: CEO + technical-analyst + risk-officer + backtest
inv-swing:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-macro: Macro preset: CEO + macro-strategist + fundamental-analyst + risk-officer + prediction-market-analyst + backtest
inv-macro:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-quick: Quick preset: CEO + technical-analyst + risk-officer (fastest)
inv-quick:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-pm: Prediction market preset: CEO + macro-strategist + prediction-market-analyst + backtest
inv-pm:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-1: One-on-one member session (select member + update knowledge)
inv-1:
    pi -e extensions/boards/inv-board-member-session.ts -e extensions/theme-cycler.ts

# ai: AI Tools Board — Mode A auto (全自動研究，用 board_begin 啟動)
ai:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-discuss: AI Tools Board — Mode B interactive (你坐進委員會)
ai-discuss:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-discovery: discovery preset — director + music + video + coding scouts
ai-discovery:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-coding: coding preset — director + coding-ai-scout
ai-coding:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-music: music preset — director + music-ai-scout
ai-music:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-video: video preset — director + video-ai-scout
ai-video:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-github: github preset — director + github-researcher
ai-github:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-systems: systems preset — director + system-analyst
ai-systems:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-1: 1-on-1 session with a specific AI Tools Board member
ai-1:
    pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-1-coding: 直接載入 coding-ai-scout 一對一會話
ai-1-coding:
    BOARD_MEMBER=coding-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-1-music: 直接載入 music-ai-scout 一對一會話
ai-1-music:
    BOARD_MEMBER=music-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-1-video: 直接載入 video-ai-scout 一對一會話
ai-1-video:
    BOARD_MEMBER=video-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-1-github: 直接載入 github-researcher 一對一會話
ai-1-github:
    BOARD_MEMBER=github-researcher pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# music-quick: Quick 2-member check (researcher + curator)
music-quick:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# ── Football Betting Board ────────────────────────────────────────────────────

# fb: Full board meeting mode — 全自動委員會分析
fb:
    pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-quick: Quick preset — director + stats-modeler + risk-manager
fb-quick:
    BOARD_PRESET=quick pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-pre: Pre-match analysis preset
fb-pre:
    BOARD_PRESET=pre-match pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-live: Live odds monitoring preset
fb-live:
    BOARD_PRESET=live pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-1: 1-on-1 session — 互動選單選擇成員
fb-1:
    pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-director: 1-on-1 with Director (總監)
fb-1-director:
    BOARD_MEMBER=director pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-data-scout: 1-on-1 with Data Scout (球員數據偵察員)
fb-1-data-scout:
    BOARD_MEMBER=data-scout pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-form-analyst: 1-on-1 with Form Analyst (近期狀態分析師)
fb-1-form:
    BOARD_MEMBER=form-analyst pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-stats-modeler: 1-on-1 with Stats Modeler (統計模型師)
fb-1-stats:
    BOARD_MEMBER=stats-modeler pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-odds-tracker: 1-on-1 with Odds Tracker (賠率追蹤員)
fb-1-odds:
    BOARD_MEMBER=odds-tracker pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-market-intel: 1-on-1 with Market Intel (市場情報員)
fb-1-market:
    BOARD_MEMBER=market-intel pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-value-hunter: 1-on-1 with Value Hunter (價值獵手)
fb-1-value:
    BOARD_MEMBER=value-hunter pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-1-risk-manager: 1-on-1 with Risk Manager (風險管理官)
fb-1-risk:
    BOARD_MEMBER=risk-manager pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# ─────────────────────────────────────────────────────────────────────────────

# cldsp: launch claude with skip-permissions (no MCP)
cldsp:
    claude --dangerously-skip-permissions

# team: start multi-agent team orchestration in tmux (with team status line)
team:
    bash .claude/scripts/team_launch.sh

# cldsp-figma: add Figma MCP → launch cldsp → remove MCP on exit (ephemeral)
cldsp-figma:
    #!/usr/bin/env bash
    echo "→ Adding Figma MCP..."
    claude mcp add --scope project --transport http figma https://mcp.figma.com/mcp 2>/dev/null || true
    echo "→ Launching cldsp with Figma MCP loaded. Exit to auto-remove."
    claude --dangerously-skip-permissions
    echo "→ Removing Figma MCP..."
    claude mcp remove figma
    echo "✓ Figma MCP removed."

# utils

# Open pi with one or more stacked extensions in a new terminal: just open minimal tool-counter
open +exts:
    #!/usr/bin/env bash
    args=""
    for ext in {{exts}}; do
        args="$args -e extensions/$ext.ts"
    done
    cmd="cd '{{justfile_directory()}}' && pi$args"
    escaped="${cmd//\\/\\\\}"
    escaped="${escaped//\"/\\\"}"
    osascript -e "tell application \"Terminal\" to do script \"$escaped\""

# Open every extension in its own terminal window
all:
    just open pi
    just open pure-focus 
    just open minimal theme-cycler
    just open cross-agent minimal
    just open purpose-gate minimal
    just open tool-counter
    just open tool-counter-widget minimal
    just open subagent-widget pure-focus theme-cycler
    just open tilldone theme-cycler
    just open agent-team theme-cycler
    just open system-select minimal theme-cycler
    just open damage-control minimal theme-cycler
    just open agent-chain theme-cycler
    just open pi-pi theme-cycler