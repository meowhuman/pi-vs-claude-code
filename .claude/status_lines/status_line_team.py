#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Team Mode Status Line
Renders a live agent-team tree with cost, tokens, and model info.
Reads from .claude/data/team-dashboard.json (shared state written by each agent).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ── ANSI colours ──────────────────────────────────────────────────────────────
R = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
DARK = "\033[90m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
ORANGE = "\033[38;5;214m"
PINK = "\033[38;5;205m"
TEAL = "\033[38;5;43m"

AGENT_COLORS: dict[str, str] = {
    "orchestrator": ORANGE,
    "orch": ORANGE,
    "planning-lead": PINK,
    "engineering-lead": CYAN,
    "validation-lead": YELLOW,
    "product-manager": BLUE,
    "ux-researcher": MAGENTA,
    "frontend-dev": BLUE,
    "backend-dev": PINK,
    "qa-engineer": GREEN,
    "security-reviewer": RED,
}

# Claude model pricing ($ per 1M tokens)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (15.0, 75.0),
    "claude-opus-4-5": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
    "claude-haiku-3": (0.25, 1.25),
}


def agent_color(name: str) -> str:
    return AGENT_COLORS.get(name.lower().replace(" ", "-"), WHITE)


def model_short(model: str) -> str:
    """Shorten model display name."""
    replacements = [
        ("claude-opus-4-6", "opus-4-6"),
        ("claude-sonnet-4-6", "sonnet-4-6"),
        ("claude-haiku-4-5", "haiku-4-5"),
        ("claude-opus-4-5-20251001", "opus-4-5"),
        ("claude-sonnet-4-5-20251001", "sonnet-4-5"),
    ]
    for full, short in replacements:
        if full in model.lower():
            return short
    return model.split("-20")[0] if "-20" in model else model


def calc_cost(model: str, input_tok: int, output_tok: int) -> float:
    for key, (inp_price, out_price) in MODEL_PRICING.items():
        if key in model.lower():
            return (input_tok * inp_price + output_tok * out_price) / 1_000_000
    # Default to sonnet pricing
    return (input_tok * 3.0 + output_tok * 15.0) / 1_000_000


def fmt_cost(cost: float) -> str:
    return f"💰${cost:.3f}"


def fmt_tokens(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"🧠{tokens / 1_000_000:.1f}M"
    if tokens >= 1000:
        return f"🧠{tokens // 1000}K"
    return f"🧠{tokens}"


def get_project_dir() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if env:
        return Path(env)
    # Try to find from cwd
    cwd = Path.cwd()
    if (cwd / ".claude").exists():
        return cwd
    return cwd


def load_teams(project_dir: Path) -> dict:
    f = project_dir / ".claude" / "teams" / "teams.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def load_dashboard(project_dir: Path) -> dict:
    f = project_dir / ".claude" / "data" / "team-dashboard.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def save_dashboard(project_dir: Path, data: dict) -> None:
    f = project_dir / ".claude" / "data" / "team-dashboard.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        f.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def get_agent_name_from_session(project_dir: Path, session_id: str) -> str | None:
    f = project_dir / ".claude" / "data" / "sessions" / f"{session_id}.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            return d.get("agent_name")
        except Exception:
            pass
    return None


def get_agent_name() -> str:
    """Try various sources to detect current agent name."""
    # Env vars Claude Code might set in teammate mode
    for var in ("CLAUDE_AGENT_NAME", "CLAUDE_TEAMMATE_NAME", "AGENT_NAME", "AGENT_ROLE"):
        val = os.environ.get(var, "")
        if val:
            return val
    return ""


def extract_usage_from_transcript(transcript_path: str) -> tuple[int, int, str]:
    """Parse transcript .jsonl and sum token usage. Returns (input_tok, output_tok, model)."""
    input_tok = 0
    output_tok = 0
    model = ""
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message", {})
                if not msg:
                    continue
                usage = msg.get("usage", {})
                if usage:
                    input_tok += usage.get("input_tokens", 0)
                    output_tok += usage.get("output_tokens", 0)
                    if not model and msg.get("model"):
                        model = msg["model"]
    except Exception:
        pass
    return input_tok, output_tok, model


def session_duration(dashboard: dict) -> str:
    starts = [v["session_start"] for v in dashboard.values() if v.get("session_start")]
    if not starts:
        return ""
    try:
        earliest = min(datetime.fromisoformat(s) for s in starts)
        elapsed = datetime.now() - earliest
        m = int(elapsed.total_seconds() // 60)
        s = int(elapsed.total_seconds() % 60)
        return f"{m}m {s:02d}s"
    except Exception:
        return ""


def render_tree(
    teams: dict,
    dashboard: dict,
    current_agent: str,
    current_model: str,
) -> list[str]:
    lines: list[str] = []

    for _team_name, team_cfg in teams.items():
        members: list[dict] = team_cfg.get("members", [])
        total = len(members)

        for idx, member in enumerate(members):
            name: str = member.get("name", "unknown")
            fallback_model: str = member.get("model", "sonnet")
            stats = dashboard.get(name, {})

            # Model
            if name == current_agent:
                model = current_model or stats.get("model", fallback_model)
            else:
                model = stats.get("model", fallback_model)

            # Tokens + cost
            in_tok: int = stats.get("input_tokens", 0)
            out_tok: int = stats.get("output_tokens", 0)
            total_tok = in_tok + out_tok
            cost: float = stats.get("cost", 0.0)

            # Activity
            is_active = name == current_agent or stats.get("status") == "active"
            dot = f"{GREEN}◆{R}" if is_active else f"{DARK}◇{R}"

            # Tree prefix
            is_last = idx == total - 1
            prefix = f"{DARK}└── {R}" if is_last else f"{DARK}├── {R}"

            color = agent_color(name)
            name_part = f"{color}{BOLD}{name}{R}"
            cost_part = f" {fmt_cost(cost)}" if cost > 0 else ""
            tok_part = f" {fmt_tokens(total_tok)}" if total_tok > 0 else ""
            model_part = f" {DARK}{model_short(model)}{R}"

            lines.append(f"{prefix}{dot} {name_part}{cost_part}{tok_part}{model_part}")

    return lines


def update_self_in_dashboard(
    dashboard: dict,
    agent_name: str,
    model: str,
    input_tok: int,
    output_tok: int,
) -> None:
    if not agent_name:
        return
    entry = dashboard.get(agent_name, {})
    entry["model"] = model
    entry["input_tokens"] = input_tok
    entry["output_tokens"] = output_tok
    entry["cost"] = calc_cost(model, input_tok, output_tok)
    entry["status"] = "active"
    entry.setdefault("session_start", datetime.now().isoformat())
    entry["last_seen"] = datetime.now().isoformat()
    dashboard[agent_name] = entry


def get_cc_switch_model() -> str:
    """Get current model from cc-switch config if available."""
    try:
        config_path = Path.home() / ".cc-switch" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            claude_config = config.get("claude", {})
            current_id = claude_config.get("current", "")
            providers = claude_config.get("providers", {})
            if current_id and current_id in providers:
                provider = providers[current_id]
                env = provider.get("settingsConfig", {}).get("env", {})
                model = env.get("ANTHROPIC_MODEL", "")
                if model:
                    return model
                return provider.get("name", "")
    except Exception:
        pass
    return ""


def generate_status(input_data: dict) -> str:
    project_dir = get_project_dir()
    session_id: str = input_data.get("session_id", "")

    # Prefer cc-switch model over Claude Code's reported model
    cc_switch_model = get_cc_switch_model()
    if cc_switch_model:
        model_name = cc_switch_model
    else:
        model_info: dict = input_data.get("model", {})
        model_name: str = model_info.get("id", model_info.get("display_name", ""))

    transcript_path: str = input_data.get("transcript_path", "")

    # Detect current agent name
    agent_name = (
        get_agent_name()
        or get_agent_name_from_session(project_dir, session_id)
        or ""
    )

    # Extract usage from transcript
    in_tok, out_tok, tx_model = extract_usage_from_transcript(transcript_path) if transcript_path else (0, 0, "")
    if tx_model and not model_name:
        model_name = tx_model

    # Load and update shared dashboard
    teams = load_teams(project_dir)
    dashboard = load_dashboard(project_dir)

    if agent_name:
        update_self_in_dashboard(dashboard, agent_name, model_name, in_tok, out_tok)
        save_dashboard(project_dir, dashboard)

    # Header
    sid_short = session_id[:8] if session_id else "--------"
    dur = session_duration(dashboard)
    header_parts = [f"{TEAL}{sid_short}{R}"]
    if dur:
        header_parts.append(f"{DARK}{dur}{R}")
    header = f" {DARK}|{R} ".join(header_parts)

    # Tree
    if teams:
        tree = render_tree(teams, dashboard, agent_name, model_name)
        return header + "\n" + "\n".join(tree)
    else:
        # Fallback: no team config
        col = agent_color(agent_name)
        cost = calc_cost(model_name, in_tok, out_tok)
        tok_total = in_tok + out_tok
        parts = [f"{col}{BOLD}{agent_name or 'agent'}{R}"]
        if cost > 0:
            parts.append(fmt_cost(cost))
        if tok_total > 0:
            parts.append(fmt_tokens(tok_total))
        parts.append(f"{DARK}{model_short(model_name)}{R}")
        return f"{header}  " + " ".join(parts)


def main() -> None:
    try:
        input_data = json.loads(sys.stdin.read())
        print(generate_status(input_data))
        sys.exit(0)
    except Exception as e:
        print(f"{YELLOW}[team-status] {str(e)[:60]}{R}")
        sys.exit(0)


if __name__ == "__main__":
    main()
