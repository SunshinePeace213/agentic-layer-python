# Output Styles - Claude Code

## Overview

Output styles adapt Claude Code for various use cases beyond software engineering while maintaining core capabilities like running scripts, file management, and TODO tracking.

## Built-in Output Styles

Claude Code includes three output style options:

1. **Default** - The standard system prompt optimized for efficient software engineering tasks
2. **Explanatory** - Provides "Insights" between coding tasks to help users understand implementation choices and codebase patterns
3. **Learning** - A collaborative, learn-by-doing mode where Claude shares insights and requests user contributions, marking code sections with `TODO(human)` labels

## How Output Styles Work

Output styles directly modify Claude Code's system prompt by:
- Removing instructions specific to code generation and efficiency
- Adding custom instructions tailored to the selected style

## Changing Your Output Style

Users can switch styles via:
- `/output-style` - Opens a menu to select from available styles
- `/output-style [style]` - Direct selection (e.g., `/output-style explanatory`)
- `/config` menu - Alternative access point

Changes apply at the local project level and are saved in `.claude/settings.local.json`.

## Creating Custom Output Styles

Run `/output-style:new I want an output style that ...` to create custom styles with Claude's assistance.

Custom styles are markdown files with the structure:
```
---
name: My Custom Style
description: Brief description
---

# Custom Style Instructions
[Your instructions here...]
```

Location options:
- User level: `~/.claude/output-styles` (available across all projects)
- Project level: `.claude/output-styles` (project-specific)

## Related Features Comparison

| Feature | Purpose |
|---------|---------|
| **Output Styles** | Replace default system prompt entirely |
| **CLAUDE.md** | Adds content as user message after system prompt |
| **--append-system-prompt** | Appends content to system prompt |
| **Agents** | Handle specific tasks with custom settings |
| **Custom Slash Commands** | Store reusable prompts |
