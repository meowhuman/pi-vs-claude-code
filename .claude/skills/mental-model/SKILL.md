---
name: Mental Model
description: Manage structured YAML expertise files as persistent mental models. Use when starting tasks (read for context), completing work (capture learnings), discovering new system knowledge, or when understanding of the system needs updating. Also use when user says "mental model", "expertise file", "capture learning", or "update mental model".
---

# Mental Model

You have personal expertise files — structured YAML documents that represent your mental model of the systems you work on. These are YOUR files. You own them. They persist across conversations.

## Storage

All expertise files live in `.claude/mental-models/`. Each domain gets its own YAML file:

- `architecture.yaml` — System structure, patterns, key files
- `decisions.yaml` — Architectural decisions and their rationale
- `patterns.yaml` — Recurring patterns, conventions, gotchas
- `team-dynamics.yaml` — Team strengths, preferences, observations
- `open-questions.yaml` — Unresolved questions and hypotheses

Max **200 lines** per file. This is a hard limit.

## When to Read

- **At the start of every task** — read relevant expertise files for context before doing anything
- **When you need to recall** prior observations, decisions, or patterns
- **When a teammate references** something you've tracked before

## When to Update

- **After completing meaningful work** — capture what you learned
- **When you discover something new** about the system (architecture, patterns, gotchas)
- **When your understanding changes** — update stale entries, don't just append
- **When you observe team dynamics** — note what works, what doesn't, who's strong at what

## How to Structure

Write structured YAML. Don't be rigid about categories — let structure emerge from work. Keep it organized enough to scan quickly.

```yaml
# Good: structured, scannable, evolving
architecture:
  api_layer:
    pattern: "REST with WebSocket for real-time"
    key_files:
      - path: apps/server/routes.ts
        note: "All endpoints, ~400 lines"
    decisions:
      - "Chose Express over Fastify for ecosystem maturity"

observations:
  - date: "2026-03-24"
    note: "Engineering team handles scope-heavy requests better with explicit constraints"

open_questions:
  - "Should we split the auth module? It's growing fast."
```

## What NOT to Store

- Don't copy-paste entire files — reference them by path
- Don't store conversation logs — that's what the session is for
- Don't store transient data (build output, test results) — just conclusions
- Don't be prescriptive about categories — evolve them naturally

## Commands

### `init` — Initialize mental models directory

Create `.claude/mental-models/` with template files:
```bash
mkdir -p .claude/mental-models
```

Then create template YAML files (see [templates/](templates/) for starters).

### `read` — Load all expertise files for context

Read all `.yaml` files in `.claude/mental-models/`:
```bash
cat .claude/mental-models/*.yaml
```

### `list` — Show files and line counts

```bash
wc -l .claude/mental-models/*.yaml
```

### `update <file>` — Update a specific expertise file

1. Read the current file
2. Merge new knowledge (update stale entries, don't just append)
3. Write the updated YAML
4. Run [Line Limit Enforcement](#line-limit-enforcement)
5. Run [YAML Validation](#yaml-validation)

### `trim <file>` — Trim to fit within line limits

1. Check: `wc -l <file>`
2. If over 200 lines, trim in this priority order:
   - Remove oldest observations (keep last 30 days)
   - Remove resolved open_questions
   - Condense verbose sections into summaries
   - Merge redundant entries
3. Re-check until within limit

### `validate` — Validate all YAML files

```bash
for f in .claude/mental-models/*.yaml; do
  python3 -c "import yaml; yaml.safe_load(open('$f'))" && echo "OK: $f" || echo "FAIL: $f"
done
```

## Line Limit Enforcement

After every write to an expertise file:

1. Check the line count: `wc -l <file>`
2. If over 200 lines, trim immediately:
   - Remove least critical entries (old observations, resolved questions)
   - Condense verbose sections
   - Merge redundant entries
3. Re-check until within limit

This is not optional. If a file exceeds the limit after a write, resolve it before continuing.

## YAML Validation

After every write, validate YAML is parseable. Malformed YAML is useless:

```bash
python3 -c "import yaml; yaml.safe_load(open('<file>'))"
```

Fix any syntax errors immediately.

## Examples

### Example 1: Starting a new task

User: "Help me refactor the authentication module"

You would:
1. Run `read` command — load all expertise files
2. Check `architecture.yaml` for auth module structure
3. Check `decisions.yaml` for prior auth-related decisions
4. Check `open-questions.yaml` for anything related to auth
5. Use that context to inform your approach

### Example 2: After completing work

You just finished refactoring the auth module and learned that:
- JWT validation was duplicated in 3 places
- The team prefers separating middleware into its own directory
- There's a circular dependency between auth and user service

You would:
1. Update `architecture.yaml` — new auth module structure
2. Add to `patterns.yaml` — "Extract middleware to dedicated directory"
3. Add to `observations.yaml` — "JWT validation should be centralized"
4. Move the circular dependency question from open_questions to decisions with the resolution

### Example 3: Discovering something new

While reading code, you notice the team uses a custom error handling pattern:

You would:
1. Add to `patterns.yaml`:
```yaml
error_handling:
  pattern: "Custom Result<T, E> type instead of exceptions"
  key_files:
    - path: src/core/result.ts
      note: "Result type definition"
  note: "Consistent across all service layer code"
```

### Example 4: First time setup

User: "Set up mental models for this project"

You would:
1. Run `init` command to create directory
2. Explore the codebase to understand structure
3. Create initial `architecture.yaml` with system overview
4. Create initial `patterns.yaml` with conventions observed
5. Create initial `open-questions.yaml` with unknowns
6. Validate all files
