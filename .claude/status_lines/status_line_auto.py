#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""
Auto-detect status line: team mode if team-dashboard.json has recent entries,
otherwise fall back to status_line_main.py output.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_project_dir() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if env:
        return Path(env)
    cwd = Path.cwd()
    if (cwd / ".claude").exists():
        return cwd
    return cwd


def is_team_active(project_dir: Path) -> bool:
    """Return True if team-dashboard.json has entries updated within the last 5 minutes."""
    dashboard_file = project_dir / ".claude" / "data" / "team-dashboard.json"
    if not dashboard_file.exists():
        return False
    try:
        data = json.loads(dashboard_file.read_text())
        if not data:
            return False
        cutoff = datetime.now() - timedelta(minutes=5)
        for entry in data.values():
            last_seen = entry.get("last_seen", "")
            if last_seen:
                try:
                    if datetime.fromisoformat(last_seen) > cutoff:
                        return True
                except Exception:
                    pass
    except Exception:
        pass
    return False


def run_script(script_path: Path, input_data: dict) -> None:
    import subprocess
    result = subprocess.run(
        ["uv", "run", str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5,
    )
    print(result.stdout, end="")
    sys.exit(result.returncode)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
        status_lines_dir = Path(__file__).parent

        mode = os.environ.get("CLAUDE_STATUS_MODE", "")
        if mode == "team":
            run_script(status_lines_dir / "status_line_team.py", input_data)
        elif mode == "main":
            run_script(status_lines_dir / "status_line_main.py", input_data)
        else:
            # Auto-detect fallback
            project_dir = get_project_dir()
            if is_team_active(project_dir):
                run_script(status_lines_dir / "status_line_team.py", input_data)
            else:
                run_script(status_lines_dir / "status_line_main.py", input_data)
    except Exception as e:
        print(f"\033[31m[status] error: {str(e)[:60]}\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
