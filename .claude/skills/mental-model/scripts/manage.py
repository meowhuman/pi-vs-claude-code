#!/usr/bin/env python3
"""Mental Model Manager - CLI tool for managing expertise files."""

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

DEFAULT_DIR = ".claude/mental-models"
MAX_LINES = 200


def get_models_dir(project_dir: str = ".") -> Path:
    """Get the mental models directory path."""
    return Path(project_dir) / DEFAULT_DIR


def cmd_init(args):
    """Initialize mental models directory with template files."""
    models_dir = get_models_dir(args.dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    templates = {
        "architecture.yaml": (
            "# Architecture\n"
            "# System structure, patterns, and key files\n"
            "\n"
            "architecture:\n"
            "  # Add architectural components here\n"
            "  # Example:\n"
            "  # api_layer:\n"
            "  #   pattern: \"REST with WebSocket\"\n"
            "  #   key_files:\n"
            "  #     - path: src/api/routes.ts\n"
            "  #       note: \"Main API endpoints\"\n"
        ),
        "decisions.yaml": (
            "# Decisions\n"
            "# Architectural decisions and their rationale\n"
            "\n"
            "decisions:\n"
            "  # - date: \"YYYY-MM-DD\"\n"
            "  #   decision: \"Description of decision\"\n"
            "  #   rationale: \"Why this was chosen\"\n"
            "  #   context: \"What trade-offs were considered\"\n"
        ),
        "patterns.yaml": (
            "# Patterns\n"
            "# Recurring patterns, conventions, and gotchas\n"
            "\n"
            "patterns:\n"
            "  # - name: \"Pattern name\"\n"
            "  #   description: \"What this pattern looks like\"\n"
            "  #   key_files:\n"
            "  #     - path: \"relative/path\"\n"
            "  #       note: \"Description\"\n"
            "\n"
            "gotchas:\n"
            "  # - \"Watch out for X when doing Y\"\n"
        ),
        "team-dynamics.yaml": (
            "# Team Dynamics\n"
            "# Team strengths, preferences, and observations\n"
            "\n"
            "observations:\n"
            "  # - date: \"YYYY-MM-DD\"\n"
            "  #   note: \"Observation about team workflow\"\n"
            "\n"
            "preferences:\n"
            "  # - area: \"Code style\"\n"
            "  #   preference: \"Description of team preference\"\n"
        ),
        "open-questions.yaml": (
            "# Open Questions\n"
            "# Unresolved questions and hypotheses\n"
            "\n"
            "open_questions:\n"
            "  # - \"Question about the system?\"\n"
            "  # - date_added: \"YYYY-MM-DD\"\n"
            "  #   question: \"Another question\"\n"
            "  #   status: \"open\"  # open | resolved\n"
        ),
    }

    created = 0
    for filename, content in templates.items():
        filepath = models_dir / filename
        if not filepath.exists():
            filepath.write_text(content.strip() + "\n")
            created += 1
        else:
            print(f"  skip: {filename} (already exists)")

    print(f"Initialized {created} template files in {models_dir}")


def cmd_list(args):
    """List all expertise files with line counts."""
    models_dir = get_models_dir(args.dir)
    if not models_dir.exists():
        print(f"No mental models directory at {models_dir}")
        print("Run 'init' first to create it.")
        return

    yaml_files = sorted(models_dir.glob("*.yaml"))
    if not yaml_files:
        print("No expertise files found.")
        return

    total_lines = 0
    for f in yaml_files:
        lines = len(f.read_text().splitlines())
        total_lines += lines
        status = "OK" if lines <= MAX_LINES else "OVER"
        print(f"  {lines:>4}/{MAX_LINES} [{status}] {f.name}")

    print(f"  {'─' * 30}")
    print(f"  Total: {total_lines} lines across {len(yaml_files)} files")


def cmd_validate(args):
    """Validate all YAML files."""
    models_dir = get_models_dir(args.dir)
    if not models_dir.exists():
        print(f"No mental models directory at {models_dir}")
        return

    yaml_files = sorted(models_dir.glob("*.yaml"))
    if not yaml_files:
        print("No expertise files found.")
        return

    all_ok = True
    for f in yaml_files:
        try:
            content = f.read_text()
            yaml.safe_load(content)
            lines = len(content.splitlines())
            warn = " [OVER LIMIT]" if lines > MAX_LINES else ""
            print(f"  OK{warn}: {f.name} ({lines} lines)")
        except yaml.YAMLError as e:
            print(f"  FAIL: {f.name} — {e}")
            all_ok = False

    if all_ok:
        print("All files valid.")
    else:
        print("Some files have errors. Fix them before continuing.")
        sys.exit(1)


def cmd_trim(args):
    """Trim a file to fit within line limits."""
    models_dir = get_models_dir(args.dir)
    filepath = models_dir / args.file

    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    content = filepath.read_text()
    lines = content.splitlines()

    if len(lines) <= MAX_LINES:
        print(f"{args.file}: {len(lines)} lines — within limit, no trim needed.")
        return

    print(f"{args.file}: {len(lines)} lines — trimming to {MAX_LINES}...")

    # Try to parse as YAML and trim intelligently
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            # Strategy: remove oldest observations, resolved questions first
            data = _trim_data(data, len(lines) - MAX_LINES)
            new_content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
            filepath.write_text(new_content + "\n")
            new_lines = len(new_content.splitlines())
            print(f"  Trimmed to {new_lines} lines.")
            if new_lines > MAX_LINES:
                # Hard trim: just take the last MAX_LINES
                filepath.write_text("\n".join(lines[-MAX_LINES:]) + "\n")
                print(f"  Hard-trimmed to {MAX_LINES} lines.")
        else:
            # Not a dict, hard trim
            filepath.write_text("\n".join(lines[-MAX_LINES:]) + "\n")
            print(f"  Hard-trimmed to {MAX_LINES} lines.")
    except yaml.YAMLError:
        # Can't parse, hard trim
        filepath.write_text("\n".join(lines[-MAX_LINES:]) + "\n")
        print(f"  (YAML parse error, hard-trimmed to {MAX_LINES} lines)")


def _trim_data(data: dict, excess: int) -> dict:
    """Intelligently trim YAML data to remove excess lines."""
    # Priority 1: Remove resolved open_questions
    if "open_questions" in data:
        oq = data["open_questions"]
        if isinstance(oq, list):
            resolved = [q for q in oq if isinstance(q, dict) and q.get("status") == "resolved"]
            if resolved and excess > 0:
                for r in resolved:
                    oq.remove(r)
                    excess -= 1
                    if excess <= 0:
                        break

    # Priority 2: Remove old observations
    if "observations" in data:
        obs = data["observations"]
        if isinstance(obs, list):
            # Sort by date, remove oldest
            dated = []
            undated = []
            for o in obs:
                if isinstance(o, dict) and "date" in o:
                    dated.append(o)
                else:
                    undated.append(o)
            dated.sort(key=lambda x: x.get("date", ""))
            while dated and excess > 0:
                dated.pop(0)
                excess -= 1
            data["observations"] = dated + undated

    return data


def cmd_read(args):
    """Read and display all expertise files."""
    models_dir = get_models_dir(args.dir)
    if not models_dir.exists():
        print(f"No mental models directory at {models_dir}")
        print("Run 'init' first to create it.")
        return

    yaml_files = sorted(models_dir.glob("*.yaml"))
    if not yaml_files:
        print("No expertise files found.")
        return

    for f in yaml_files:
        print(f"\n{'=' * 60}")
        print(f"  {f.name}")
        print(f"{'=' * 60}")
        print(f.read_text())


def main():
    parser = argparse.ArgumentParser(description="Mental Model Manager")
    parser.add_argument("--dir", default=".", help="Project root directory")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("init", help="Initialize mental models directory")
    subparsers.add_parser("read", help="Read all expertise files")
    subparsers.add_parser("list", help="List files with line counts")
    subparsers.add_parser("validate", help="Validate all YAML files")

    trim_parser = subparsers.add_parser("trim", help="Trim a file to fit line limits")
    trim_parser.add_argument("file", help="File name to trim")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "read": cmd_read,
        "list": cmd_list,
        "validate": cmd_validate,
        "trim": cmd_trim,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
