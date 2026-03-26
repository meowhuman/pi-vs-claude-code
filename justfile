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

# cldsp: launch claude with skip-permissions (no MCP)
cldsp:
    claude --dangerously-skip-permissions

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