---
model: haiku
description: Create custom slash commands following standard template structure
argument-hint: [command-name] [description]
allowed-tools: Write, Read, AskUserQuestion
---

# Purpose

Guide users through creating well-structured custom slash commands with proper YAML frontmatter, required sections, and optional validation hooks. All commands must be written in English.

## Variables

```
COMMAND_NAME: $1 (e.g., "process-data")
DESCRIPTION: $2 (one-line description)
OUTPUT_DIR: /Volumes/Ketomuffin_mac/ET_VP/Art-direction /style-book/.claude/commands/km-selection
```

## Instructions

- All custom commands MUST be in English
- Follow standard template: Purpose, Variables, Instructions, Workflow, Report, Error Handling
- Suggest hooks based on file type (CSV, Python, HTML, etc.)
- Validate command name format before creation
- Write file to OUTPUT_DIR

## Workflow

### 1. Gather Requirements

If arguments missing, ask user for:
- Command name (lowercase with dashes only)
- Description (one-line)
- Arguments needed
- Tools required

### 2. Validate Command Name

Check that:
- Uses lowercase with dashes only
- Descriptive and not already exists
- Report errors and halt if invalid

### 3. Suggest Hooks (Optional)

| File Type | Validator | When |
|-----------|-----------|------|
| CSV | csv-single-validator.py | Read/Write CSV |
| Python | ruff-validator.py | Edit/Write .py |
| HTML | html-validator.py | Write .html |
| Graphs | graph-validator.py | Create visualizations |

Ask if user wants to add hooks.

### 4. Generate Command File

Create command with template structure:

```yaml
---
model: haiku
description: [DESCRIPTION]
argument-hint: [ARGS]
allowed-tools: [TOOLS]
---
```

Add sections: Purpose, Variables, Instructions, Workflow, Report, Error Handling, Examples, Summary

### 5. Write and Verify

- Write to OUTPUT_DIR
- Confirm file creation
- Display command path and usage

## Report

```
=== Command Created ===

✓ Command: /km-selection:[COMMAND_NAME]
✓ Location: [FILE_PATH]
✓ Description: [DESCRIPTION]

✓ Sections: Purpose, Variables, Instructions, Workflow, Report, Error Handling, Examples, Summary
✓ Hooks: [INSTALLED/NONE]
✓ Usage: /km-selection:[COMMAND_NAME] [ARGS]

Next: Test the command with sample inputs
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Command exists | File already present | Choose different name or confirm overwrite |
| Invalid format | Spaces or special chars | Use lowercase with dashes: "my-command" |
| Write failed | Permission or path error | Verify OUTPUT_DIR exists and is writable |

## Examples

### Example 1: CSV processor

```bash
/km:custom-command:custom-command-helper process-csv "Process and validate CSV files"
```

Creates `process-csv.md` with csv-single-validator.py hook suggestion.

### Example 2: Data fetcher

```bash
/km:custom-command:custom-command-helper fetch-api "Fetch data from external API"
```

Creates `fetch-api.md` with no hooks (no file validation needed).

## Command Template

Every generated command includes:

```markdown
---
model: haiku
description: [One-line description]
argument-hint: [ARG1] [ARG2]
allowed-tools: [Bash, Read, Write, etc.]
---

# Purpose
[What and why - 2-3 sentences]

## Variables
[Positional args and config paths]

## Instructions
[Key guidelines and validation approach]

## Workflow
### 1. [Step name]
[Action and display message]

### 2. [Step name]
[Action and display message]

### N. Report
[Display success in standard format]

## Report
[Output format after completion]

## Error Handling
[Common errors, causes, and solutions table]

## Examples
[2-3 usage scenarios]

## Summary
[Features and use cases]
```

## Language Requirements

✅ Command structure MUST be in English:
- Descriptions, variables, instructions
- Workflow steps, error messages, examples
- Comments and documentation

❌ Avoid mixed languages in command internals.

## Summary

The `/km:custom-command:custom-command-helper` command:

✓ Guides creation of standard custom commands
✓ Enforces proper YAML structure
✓ Suggests validation hooks
✓ Ensures English-only documentation
✓ Validates inputs before creation

Use to build new slash commands following best practices.
