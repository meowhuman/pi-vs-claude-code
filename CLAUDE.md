# Pi vs CC — Extension Playground

Pi Coding Agent extension examples and experiments.

## Language

- **所有回覆必須使用繁體中文**，除非用戶明確以其他語言書寫
- 程式碼、變數名稱、檔案路徑、指令保持英文
- 技術術語可保留英文，但解釋必須用繁體中文

## Tooling
- **Package manager**: `bun` (not npm/yarn/pnpm)
- **Task runner**: `just` (see justfile)
- **Extensions run via**: `pi -e extensions/<name>.ts`

## Project Structure
- `extensions/` — Pi extension source files (.ts)
- `specs/` — Feature specifications
- `.pi/agents/` — Agent definitions for agent-team extension
- `.pi/agent-sessions/` — Ephemeral session files (gitignored)

## Conventions
- Extensions are standalone .ts files loaded by Pi's jiti runtime
- Available imports: `@mariozechner/pi-coding-agent`, `@mariozechner/pi-tui`, `@mariozechner/pi-ai`, `@sinclair/typebox`, plus any deps in package.json
- Register tools at the top level of the extension function (not inside event handlers)
- Use `isToolCallEventType()` for type-safe tool_call event narrowing

## Agent Team Orchestration

This project uses a 3-tier multi-agent team architecture:

```
Orchestrator (you/lead) → Team Leads (opus) → Workers (sonnet)
```

### Teams
- **Planning Lead** → Product Manager, UX Researcher
- **Engineering Lead** → Frontend Dev, Backend Dev
- **Validation Lead** → QA Engineer, Security Reviewer

### Usage
```
# Start a team
Create an agent team with planning-lead, engineering-lead, and validation-lead.

# Delegate to workers (from within a lead)
Use the frontend-dev agent to implement the login page.
```

See `.claude/agents/` for all agent definitions and `.claude/teams/teams.json` for team config.
