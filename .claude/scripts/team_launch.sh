#!/usr/bin/env bash
# team_launch.sh — swap statusLine to team mode, launch claude, restore on exit

SETTINGS=".claude/settings.local.json"
TEAM_CMD="uv run \$CLAUDE_PROJECT_DIR/.claude/status_lines/status_line_team.py"

# Inject team statusLine into settings.local.json
python3 - <<PYEOF
import json
from pathlib import Path
p = Path("$SETTINGS")
d = json.loads(p.read_text()) if p.exists() else {}
d["statusLine"] = {"type": "command", "command": "$TEAM_CMD"}
p.write_text(json.dumps(d, indent=2))
PYEOF

echo "→ Team status line active. Launching..."
claude --teammate-mode tmux

# Remove statusLine override on exit (restore regular mode)
python3 - <<PYEOF
import json
from pathlib import Path
p = Path("$SETTINGS")
if p.exists():
    d = json.loads(p.read_text())
    d.pop("statusLine", None)
    p.write_text(json.dumps(d, indent=2))
PYEOF
echo "→ Team status line removed. Regular mode restored."
