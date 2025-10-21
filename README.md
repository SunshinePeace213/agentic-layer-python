# Agentic Layer Primitives

A codebase which design the fundamental building blocks of agentic coding with Claude Code CLI -- a new paradigm where we template our engineering and teach agents to operate our entire codebases instead of directly modifying them ourselves. The codebase is building with Python.

## Visions
Moving towards from in-loop coding to out-loop coding, and aims to Zero Touch Engineering which leads by AI Agents for the software development live cycle (SDLC)

## Prerequisites

- Python 3.11+
- uv (Python package manager)
- Claude Code Plan Subscription (provided by users)

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Post-Installation
Enjoy the joy of in-loop coding with templated commands and tools.


## Project Structure
A fully-featured implementation for production-grade agentic development with Claude Code Configuration:

```
specs/                          # Plans and specifications
├── issue-*.md                  # Issue-based specs
└── deep_specs/                 # Complex architectural specs

.claude/                        # Agent configuration
├── agents/                     # Sub-agent system prompts configuration
│   ├── meta-agent.md
│   ├── docs-scraper.md
├── commands/                   # Agentic prompts
│   ├── bug.md
│   ├── chore.md
│   ├── feature.md
│   ├── test.md
│   ├── e2e/                    # End-to-end test templates
│   │   └── test_*.md
│   └── *.md                    # Domain-specific templates
├── hooks/                      # Event-driven automation
│   ├── pre_tool_use.py
│   ├── post_tool_use.py
│   └── utils/                  # Hook utilities
├── output-styles/              # Output Format Configurations
│   ├── pre_tool_use.py
│   ├── post_tool_use.py
│   └── utils/                  # Hook utilities
├── tdd-guard/                  # TDD Guard Config
│   ├── data/    
│   │   ├── config.json
│   │   ├── instructions.md     # TDD rules for agents
└── settings.json               # Agent configuration

adws/                           # AI Developer Workflows
├── adw_modules/                # Core logic modules
│   ├── agent.py                # Agent execution
│   ├── data_types.py           # Type definitions
│   ├── git_ops.py              # Git operations
│   ├── github.py               # GitHub integration
│   ├── state.py                # State management
│   └── workflow_ops.py         # Workflow orchestration
├── adw_triggers/               # Workflow triggers
│   ├── trigger_webhook.py      # Webhook-based triggers
│   ├── trigger_cron.py         # Scheduled triggers
│   └── adw_trigger_*.py        # Custom triggers
├── adw_tests/                  # Testing suite
│   ├── test_agents.py
│   └── test_*.py
├── adw_data/                   # Agent database
│   ├── agents.db
│   └── backups/
├── adw_*_iso.py                # Isolated workflows
├── adw_sdlc_*.py               # Full SDLC workflows
└── README.md                   # ADW documentation

agents/                         # Agent output & observability
├── {adw_id}/                   # Per-workflow outputs
│   ├── {agent_name}/           # Per-agent artifacts
│   └── adw_state.json          # Workflow state

ai_docs/                        # AI-generated documentation
├── *.md                        # Generated docs

app_docs/                       # Application documentation
├── feature-*.md                # Feature documentation
└── assets/                     # Supporting materials

trees/                          # Agent worktrees (isolation)
└── {branch_name}/              # Isolated work environments

.mcp.json                       # MCP configuration
```

**Advanced Components:**
- **Types** (`adw_modules/data_types.py`): Strong typing for agent interactions
- **Triggers** (`adw_triggers/`): Multiple invocation patterns (manual, cron, webhooks)
- **Testing** (`adw_tests/`): Validate agent behavior
- **Observability** (`agents/`): Comprehensive logging and debugging
- **Isolation** (`trees/`): Dedicated worktrees for safe agent operations
- **Hooks** (`.claude/hooks/`): Event-driven automation and guardrails

## Flexibility Note

This is just *one way* to organize the agentic layer. The key principle is creating a structured environment where:
- Engineering patterns are templated and reusable
- Agents have clear instructions on how to operate the codebase
- Workflows are composable and scalable
- Output is observable and debuggable

## Codebase Structure

### Agentic Layer

The agent layer contains the functionality responsible for agentic coding.
This is where you template your engineering and teach agents how to operate your codebase.

### Application Layer

The application layer contains your actual application code.
This is what your agents will operate on.

`apps/` - Your application code

## 12 Leverage Points of Agentic Coding

### In Agent (Core Four)

1. Context
2. Model
3. Prompt
4. Tools

### Through Agent

5. Standard Output
6. Types
7. Docs
8. Tests
9. Architecture
10. Plans
11. Templates
12. AI Developer Workflows

