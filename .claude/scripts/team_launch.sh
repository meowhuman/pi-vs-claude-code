#!/usr/bin/env bash
# team_launch.sh — launch claude in teammate mode
# Status line auto-detects team mode via status_line_auto.py (no settings modification needed)

echo "→ Launching team mode..."
CLAUDE_STATUS_MODE=team claude --teammate-mode tmux
echo "→ Team session ended."
