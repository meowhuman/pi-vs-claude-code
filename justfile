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

# music-study: Full music research board (deep-researcher + youtube-curator + genre-historian + listening-guide)
ext-music-study:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# music-study-jazz: Jazz deep dive (deep-researcher + genre-historian)
ext-music-study-jazz:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# music-study-discovery: Find new music (youtube-curator + listening-guide)
ext-music-study-discovery:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# intel-board: Strategic Intel Board — 3 experts (group + /select for 1-on-1)
ext-intel:
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

# meta-orchestrator: Full cross-domain analysis (investment + drip + ai-tools + geopolitics)
ext-meta:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-strategic: Investment + Drip boards (business strategy questions)
ext-meta-strategic:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-tech: AI Tools + Investment boards (tech policy questions)
ext-meta-tech:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# meta-creative: Drip + AI Tools boards (creative tech questions)
ext-meta-creative:
    pi -e extensions/boards/meta-orchestrator.ts -e extensions/theme-cycler.ts

# drip-board: Drip Music strategic decision board (full board)
ext-drip-board:
    pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-board-quick: Quick 2-member sanity check (revenue + contrarian)
ext-drip-board-quick:
    pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-board-marketing: Marketing campaign decisions
ext-drip-board-marketing:
    BOARD_PRESET=marketing-campaign pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-board-grants: Funding & government relations decisions
ext-drip-board-grants:
    BOARD_PRESET=grants-funding pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# drip-board-programming: Programming & artist decisions
ext-drip-board-programming:
    BOARD_PRESET=programming pi -e extensions/drip-board.ts -e extensions/theme-cycler.ts

# inv-board: Investment Adviser Board — Mode A auto (all members, use board_begin)
ext-inv-board:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-board-discuss: Investment Adviser Board — Mode B interactive (you sit in, use board_discuss)
ext-inv-board-discuss:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-board-swing: Swing-trade preset: CEO + technical-analyst + risk-officer + backtest
ext-inv-board-swing:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-board-macro: Macro preset: CEO + macro-strategist + fundamental-analyst + risk-officer + prediction-market-analyst + backtest
ext-inv-board-macro:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-board-quick: Quick preset: CEO + technical-analyst + risk-officer (fastest)
ext-inv-board-quick:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-board-pm: Prediction market preset: CEO + macro-strategist + prediction-market-analyst + backtest
ext-inv-board-pm:
    pi -e extensions/boards/investment-adviser-board.ts -e extensions/theme-cycler.ts

# inv-member: One-on-one member session (select member + update knowledge)
ext-inv-member:
    pi -e extensions/boards/inv-board-member-session.ts -e extensions/theme-cycler.ts

# ai-tools-board: AI Tools Board — Mode A auto (全自動研究，用 board_begin 啟動)
ext-ai-tools-board:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-discuss: AI Tools Board — Mode B interactive (你坐進委員會)
ext-ai-tools-board-discuss:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-discovery: discovery preset — director + music + video + coding scouts
ext-ai-tools-board-discovery:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-coding: coding preset — director + coding-ai-scout
ext-ai-tools-board-coding:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-music: music preset — director + music-ai-scout
ext-ai-tools-board-music:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-video: video preset — director + video-ai-scout
ext-ai-tools-board-video:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-github: github preset — director + github-researcher
ext-ai-tools-board-github:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-board-systems: systems preset — director + system-analyst
ext-ai-tools-board-systems:
    pi -e extensions/boards/ai-tools-board.ts -e extensions/theme-cycler.ts

# ai-tools-member: 1-on-1 session with a specific AI Tools Board member
ext-ai-tools-member:
    pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-tools-member-coding: 直接載入 coding-ai-scout 一對一會話
ext-ai-tools-member-coding:
    BOARD_MEMBER=coding-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-tools-member-music: 直接載入 music-ai-scout 一對一會話
ext-ai-tools-member-music:
    BOARD_MEMBER=music-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-tools-member-video: 直接載入 video-ai-scout 一對一會話
ext-ai-tools-member-video:
    BOARD_MEMBER=video-ai-scout pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# ai-tools-member-github: 直接載入 github-researcher 一對一會話
ext-ai-tools-member-github:
    BOARD_MEMBER=github-researcher pi -e extensions/boards/ai-tools-board-member-session.ts -e extensions/theme-cycler.ts

# music-study-quick: Quick 2-member check (researcher + curator)
ext-music-study-quick:
    pi -e extensions/boards/music-study.ts -e extensions/theme-cycler.ts

# ── Football Betting Board ────────────────────────────────────────────────────

# fb-board: Full board meeting mode — 全自動委員會分析
ext-fb-board:
    pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-board-quick: Quick preset — director + stats-modeler + risk-manager
ext-fb-board-quick:
    BOARD_PRESET=quick pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-board-pre-match: Pre-match analysis preset
ext-fb-board-pre-match:
    BOARD_PRESET=pre-match pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-board-live: Live odds monitoring preset
ext-fb-board-live:
    BOARD_PRESET=live pi -e extensions/boards/football-betting-board.ts -e extensions/theme-cycler.ts

# fb-member: 1-on-1 session — 互動選單選擇成員
ext-fb-member:
    pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-director: 1-on-1 with Director (總監)
ext-fb-member-director:
    BOARD_MEMBER=director pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-data-scout: 1-on-1 with Data Scout (球員數據偵察員)
ext-fb-member-data-scout:
    BOARD_MEMBER=data-scout pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-form-analyst: 1-on-1 with Form Analyst (近期狀態分析師)
ext-fb-member-form-analyst:
    BOARD_MEMBER=form-analyst pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-stats-modeler: 1-on-1 with Stats Modeler (統計模型師)
ext-fb-member-stats-modeler:
    BOARD_MEMBER=stats-modeler pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-odds-tracker: 1-on-1 with Odds Tracker (賠率追蹤員)
ext-fb-member-odds-tracker:
    BOARD_MEMBER=odds-tracker pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-market-intel: 1-on-1 with Market Intel (市場情報員)
ext-fb-member-market-intel:
    BOARD_MEMBER=market-intel pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-value-hunter: 1-on-1 with Value Hunter (價值獵手)
ext-fb-member-value-hunter:
    BOARD_MEMBER=value-hunter pi -e extensions/boards/fb-board-member-session.ts -e extensions/theme-cycler.ts

# fb-member-risk-manager: 1-on-1 with Risk Manager (風險管理官)
ext-fb-member-risk-manager:
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