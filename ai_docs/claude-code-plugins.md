# Claude Code Plugins Documentation

## Overview

Plugins extend Claude Code with custom functionality including commands, agents, hooks, and MCP servers. They can be shared across projects and teams, installed from marketplaces, or created custom.

## Quickstart

### Prerequisites
- Claude Code installed locally
- Basic command-line familiarity

### Create Your First Plugin

**Step 1: Set up marketplace structure**
```bash
mkdir test-marketplace
cd test-marketplace
```

**Step 2: Create plugin directory**
```bash
mkdir my-first-plugin
cd my-first-plugin
```

**Step 3: Create plugin manifest** (`.claude-plugin/plugin.json`)
```json
{
  "name": "my-first-plugin",
  "description": "A simple greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

**Step 4: Add custom command** (`commands/hello.md`)
```markdown
---
description: Greet the user with a personalized message
---

# Hello Command

Greet the user warmly and ask how you can help them today. Make the greeting personal and encouraging.
```

**Step 5: Create marketplace manifest** (`.claude-plugin/marketplace.json`)
```json
{
  "name": "test-marketplace",
  "owner": {
    "name": "Test User"
  },
  "plugins": [
    {
      "name": "my-first-plugin",
      "source": "./my-first-plugin",
      "description": "My first test plugin"
    }
  ]
}
```

**Step 6: Install and test**
```bash
cd ..
claude
/plugin marketplace add ./test-marketplace
/plugin install my-first-plugin@test-marketplace
# Restart Claude Code
/hello
```

### Plugin Structure Overview

Standard directory layout:
```
my-first-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
├── agents/
├── skills/
│   └── my-skill/
│       └── SKILL.md
└── hooks/
    └── hooks.json
```

## Install and Manage Plugins

### Add Marketplaces

```bash
/plugin marketplace add your-org/claude-plugins
/plugin
```

### Install Plugins

**Interactive menu** (recommended for discovery):
```bash
/plugin
# Select "Browse Plugins"
```

**Direct commands**:
```bash
/plugin install formatter@your-org
/plugin enable plugin-name@marketplace-name
/plugin disable plugin-name@marketplace-name
/plugin uninstall plugin-name@marketplace-name
```

### Verify Installation

1. Run `/help` to see new commands
2. Test plugin features
3. Use `/plugin` → "Manage Plugins" for details

## Team Plugin Workflows

Configure plugins at repository level in `.claude/settings.json`:
- Add marketplace and plugin configuration
- Team members trust the repository folder
- Plugins install automatically for all team members

See Plugin marketplaces guide for complete instructions.

## Develop More Complex Plugins

### Add Skills to Your Plugin

Create `skills/` directory at plugin root with `SKILL.md` files. Skills are model-invoked and automatically available when installed.

### Organize Complex Plugins

Organize by functionality for plugins with many components. See Plugins reference for directory layout patterns.

### Test Locally

**Development structure**:
```bash
mkdir dev-marketplace
cd dev-marketplace
mkdir my-plugin
```

**Create marketplace manifest**:
```json
{
  "name": "dev-marketplace",
  "owner": {
    "name": "Developer"
  },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./my-plugin",
      "description": "Plugin under development"
    }
  ]
}
```

**Install and iterate**:
```bash
cd ..
claude
/plugin marketplace add ./dev-marketplace
/plugin install my-plugin@dev-marketplace
# Make changes, then uninstall and reinstall to test
/plugin uninstall my-plugin@dev-marketplace
/plugin install my-plugin@dev-marketplace
```

### Debug Plugin Issues

1. Check directory structure (ensure directories at plugin root, not inside `.claude-plugin/`)
2. Test components individually
3. Use validation and debugging tools from Plugins reference

### Share Your Plugins

1. Add README.md with installation and usage instructions
2. Use semantic versioning in `plugin.json`
3. Distribute through plugin marketplaces
4. Have team members test before wider distribution

## Next Steps

**For plugin users:**
- Discover plugins from community marketplaces
- Set up repository-level plugins
- Manage multiple plugin sources
- Explore plugin combinations

**For plugin developers:**
- Create first marketplace
- Explore slash commands, subagents, skills, hooks, MCP
- Plan distribution strategies
- Consider community contribution

**For team leads:**
- Configure automatic plugin installation
- Establish approval guidelines
- Maintain organization-specific catalogs
- Train team members

## Related Documentation

- [Plugin marketplaces](/en/docs/claude-code/plugin-marketplaces)
- [Slash commands](/en/docs/claude-code/slash-commands)
- [Subagents](/en/docs/claude-code/sub-agents)
- [Agent Skills](/en/docs/claude-code/skills)
- [Hooks](/en/docs/claude-code/hooks)
- [MCP](/en/docs/claude-code/mcp)
