---
model: sonnet
description: Create and configure new agents and teams with proper role definitions, memory setup, and tool permissions
argument-hint: [agent-name] [team-name] (optional)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Purpose

Guide users through creating well-structured agents and teams for multi-agent orchestration. Handles agent definition files, team configuration, memory initialization, and role documentation. Supports both individual agents and team groupings.

## Variables

```
AGENT_NAME: lowercase-with-dashes (e.g., "data-analyst", "security-reviewer")
TEAM_NAME: optional, group name for related agents (e.g., "data-ops-team")
AGENTS_DIR: .claude/agents/
TEAMS_JSON: .claude/teams/teams.json
MEMORY_DIR: .claude/agent-memory/
MODEL: sonnet | opus (default: sonnet for workers, opus for leads)
TOOLS: comma-separated list (Read, Write, Edit, Bash, Grep, Glob, Agent)
PERMISSION_MODE: acceptEdits | bypassPermissions | default
```

## Instructions

1. **Validate Naming**: Agent names must be lowercase-with-dashes, descriptive, not already existing
2. **Gather Role Info**: Description, responsibilities, which workers/agents it supervises
3. **Define Tools**: Select appropriate tools based on agent responsibilities
4. **Memory Scope**: project | user | global (where to save learnings)
5. **Team Association**: Optionally add to existing team or create new one

## Workflow

### 1. Validate Agent Name

Check that name:
- Uses only lowercase letters, numbers, dashes
- Does not already exist in `.claude/agents/`
- Is descriptive (3-5 words suggested)

Example: ✓ `data-quality-lead` ✓ `security-reviewer` ✗ `dr` ✗ `Data-Reviewer`

### 2. Gather Agent Configuration

Ask for:
- **Description**: One-line role summary (e.g., "Data Quality Lead — validates pipelines and schemas")
- **Responsibilities**: 2-3 bullet points (what this agent does)
- **Model**: Choose sonnet (workers) or opus (leads)
- **Tools**: Select from: Read, Write, Edit, Bash, Grep, Glob, Agent
- **Permission Mode**: acceptEdits (default) | bypassPermissions | default
- **Memory Type**: project (task-specific) | user (about the human) | global (cross-project)
- **Supervised Agents**: If a lead, which agents/workers report to it

### 3. Create Agent Definition File

Generate `.claude/agents/[AGENT_NAME].md`:

```markdown
---
name: [AGENT_NAME]
description: [ONE-LINE DESCRIPTION]
tools: [TOOLS_LIST]
model: [sonnet|opus]
permissionMode: [acceptEdits|bypassPermissions|default]
memory: [project|user|global]
---

# [AGENT_ROLE_TITLE]

[Introductory role statement]

## Responsibilities

1. [Responsibility 1]
2. [Responsibility 2]
3. [Responsibility 3]

## Team Members (if Lead)

- **[worker-name]** — [role description]
- **[worker-name]** — [role description]

## Domain Expertise

- [Expertise area 1]
- [Expertise area 2]

## Delegation Examples

[Show how to delegate to workers via Agent tool]

## Communication Guidelines

[How to communicate with other agents and orchestrator]

---

**Language: Always respond in [LANGUAGE]. Technical terms may remain in English.**
```

### 4. Update Team Configuration

If `TEAM_NAME` provided:

1. Read `.claude/teams/teams.json`
2. Add agent to existing team OR create new team entry
3. Format: `{ "team-name": { "members": [{ "name": "...", "agent": "...", "model": "..." }] } }`

Example:
```json
{
  "data-ops-team": {
    "members": [
      { "name": "data-quality-lead", "agent": "data-quality-lead", "model": "sonnet" },
      { "name": "data-analyst", "agent": "data-analyst", "model": "sonnet" }
    ]
  }
}
```

### 5. Initialize Memory Structure

Create `.claude/agent-memory/[AGENT_NAME]/`:
- `MEMORY.md` — Index of agent's learnings
- Subdirectories for organized memory (optional)

### 6. Report

Display:
- Agent file location
- Team assignment (if applicable)
- Next steps (test via `claude --teammate-mode tmux`)

## Report

```
=== Agent Created Successfully ===

✓ Agent: [AGENT_NAME]
✓ Location: .claude/agents/[AGENT_NAME].md
✓ Description: [DESCRIPTION]
✓ Model: [MODEL]
✓ Tools: [TOOLS]
✓ Memory Scope: [SCOPE]

✓ Team: [TEAM_NAME] (if applicable)
✓ Memory Dir: .claude/agent-memory/[AGENT_NAME]/

Next Steps:
1. Edit .claude/agents/[AGENT_NAME].md to customize role details
2. If adding supervised agents, update their agent files with delegation examples
3. Test with: claude --teammate-mode tmux
4. Or spawn single agent: /use [AGENT_NAME]

Configuration validated ✓
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Agent exists | File already in `.claude/agents/` | Choose different name or use `/update` |
| Invalid name | Contains spaces, uppercase, special chars | Use lowercase-with-dashes: "my-agent-name" |
| Team not found | Referenced team doesn't exist in teams.json | Create new team or use existing team name |
| Memory init failed | Permission error on `.claude/agent-memory/` | Verify directory exists and is writable |
| Invalid tools | Tool name not in allowed list | Choose from: Read, Write, Edit, Bash, Grep, Glob, Agent |

## Examples

### Example 1: Create Worker Agent

```bash
/cc-agent-team-setup data-analyst
```

→ Prompts for: description, tools (Read, Grep recommended), team (optional)
→ Creates: `.claude/agents/data-analyst.md` + memory dir
→ No team assignment unless specified

### Example 2: Create Team Lead with Supervised Workers

```bash
/cc-agent-team-setup frontend-qa-lead
```

→ Prompts for: description, model (opus), tools, memory scope
→ Asks: "Which agents will this lead supervise?" → Select from: test-case-writer, performance-tester
→ Creates lead agent + updates team roster
→ Initializes memory for delegation patterns

### Example 3: Create and Add to Existing Team

```bash
/cc-agent-team-setup backend-security-reviewer data-ops-team
```

→ Reads `teams.json`
→ Checks if team exists; if not, creates it
→ Adds agent to team roster
→ Creates agent file with team context

## Summary

The `/cc-agent-team-setup` command:

✓ Guides agent creation from role definition to team integration
✓ Validates naming and configuration before file creation
✓ Manages `.claude/agents/`, `teams.json`, and memory directories
✓ Supports hierarchical teams (leads + workers)
✓ Generates proper YAML frontmatter and role documentation
✓ Sets up agent memory structure automatically
✓ Enables rapid multi-agent orchestration setup

Use this to:
- Create new specialized agents (e.g., data analysts, security reviewers)
- Organize agents into teams with clear hierarchies
- Build lead-worker relationships for delegation
- Maintain consistent agent configuration across projects
