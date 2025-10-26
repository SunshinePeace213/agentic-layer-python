# PreToolUse Hooks Documentation

Comprehensive documentation for the Claude Code PreToolUse hook system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Available Hooks](#available-hooks)
- [Shared Utilities](#shared-utilities)
- [Adding New Hooks](#adding-new-hooks)
- [Testing](#testing)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

The `pre_tools` directory contains PreToolUse hooks that intercept and validate Claude Code tool operations before execution. These hooks enforce:

- **Security**: Prevent access to sensitive files and dangerous commands
- **Standards**: Enforce naming conventions and dependency management workflows
- **Quality**: Block creation of temporary files and enforce linting standards

### Key Features

- **Modular Design**: Each hook focuses on a single responsibility
- **Shared Utilities**: Common functionality in `utils/` reduces code duplication
- **Type Safety**: Full TypedDict definitions with strict type checking
- **Educational**: Hooks provide helpful guidance, not just blocking
- **Fail-Safe**: Errors allow operations to continue (non-blocking)

---

## Architecture

### Directory Structure

```
.claude/hooks/pre_tools/
├── README.md                              # This file
├── __init__.py                            # Package marker
├── utils/                                 # Shared utilities
│   ├── __init__.py                        # Public API exports
│   ├── data_types.py                      # TypedDict definitions
│   └── utils.py                           # Shared functions
├── tests/                                 # Test suite
│   ├── __init__.py
│   ├── test_data_types.py
│   ├── test_utils.py
│   ├── test_uv_workflow_enforcer.py
│   ├── test_uv_dependency_blocker.py
│   └── test_sensitive_file_access_validator.py
├── coding_naming_enforcer.py              # Python code naming standards
├── destructive_command_blocker.py         # Dangerous Bash command blocker
├── file_naming_enforcer.py                # File naming conventions
├── lint_argument_enforcer.py              # Linting command validator
├── pre_tools_logging.py                   # Hook execution logger
├── sensitive_file_access_validator.py     # Sensitive file protection
├── tmp_creation_blocker.py                # Temporary file blocker
├── uv_dependency_blocker.py               # UV dependency file protector
└── uv_workflow_enforcer.py                # UV workflow enforcer
```

### Hook Execution Flow

```
User Request → Claude Code Tool → PreToolUse Hook → Validation Logic
                                                    ↓
                                          [allow|deny|ask] Decision
                                                    ↓
                                          Tool Execution or Block
```

---

## Available Hooks

### 1. UV Workflow Enforcer

**File**: `uv_workflow_enforcer.py`

**Purpose**: Enforces the use of UV for all Python package management and script execution.

**Blocks**:
- `python script.py` → Suggests `uv run script.py`
- `pip install <package>` → Suggests `uv add <package>`
- `pip install -r requirements.txt` → Suggests `uv sync`
- `pip uninstall <package>` → Suggests `uv remove <package>`

**Allows**:
- UV commands (`uv run`, `uv add`, `uv sync`)
- System info commands (`python --version`, `pip --help`)
- Shebang inspection (`grep python`, `head script.py`)
- String contexts (`echo "python"`, `git commit -m "..."`)
- Which commands (`which python`)

**Configuration**:
```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
  }]
}
```

**Example Output**:
```
🚫 Use UV to run Python scripts

Command detected: python script.py
UV equivalent:    uv run script.py

Benefits:
• ✅ Runs in project's virtual environment automatically
• ✅ Ensures dependencies are installed
• ✅ Supports inline script metadata
• ✅ Works with any Python version

Learn more: https://docs.astral.sh/uv/guides/scripts/
```

---

### 2. UV Dependency Blocker

**File**: `uv_dependency_blocker.py`

**Purpose**: Prevents direct editing of dependency files, enforcing UV command usage.

**Blocks**:
- Editing `pyproject.toml` (dependencies section)
- Editing `requirements.txt`, `requirements-*.txt`
- Editing `uv.lock` (auto-generated)
- Editing `Pipfile`, `Pipfile.lock`

**Allows**:
- Template files (`*.sample`, `*.example`, `*.template`)
- Non-dependency sections of `pyproject.toml`

**Configuration**:
```json
{
  "matcher": "Write|Edit|MultiEdit",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_dependency_blocker.py"
  }]
}
```

**Example Output**:
```
🚫 Cannot edit pyproject.toml directly.

Use UV commands instead:
  • Add dependency: uv add <package>
  • Add dev dependency: uv add --dev <package>
  • Remove dependency: uv remove <package>

UV manages dependencies in pyproject.toml automatically.
```

---

### 3. Sensitive File Access Validator

**File**: `sensitive_file_access_validator.py`

**Purpose**: Prevents reading/writing sensitive files and system directories.

**Blocks**:
- Environment files (`.env`, `.env.local`)
- SSH keys (`~/.ssh/*`, `id_rsa`, `id_ed25519`)
- Cloud credentials (`~/.aws/credentials`, `~/.gcp/`)
- System directories (`/etc/*`, `/var/*`, `/sys/*`)
- Database files (`*.db`, `*.sqlite`)
- API keys and secrets

**Allows**:
- Example files (`.env.example`, `.env.sample`)
- Project files outside sensitive locations
- Documented exceptions

**Configuration**:
```json
{
  "matcher": "Read|Write|Edit|Bash",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/sensitive_file_access_validator.py"
  }]
}
```

---

### 4. Destructive Command Blocker

**File**: `destructive_command_blocker.py`

**Purpose**: Prevents execution of dangerous Bash commands.

**Blocks**:
- `rm -rf /` and similar destructive rm commands
- `dd` disk operations
- `mkfs` formatting operations
- Fork bombs (`:(){:|:&};:`)
- `chmod 777` on system directories
- `kill -9` on critical processes

**Allows**:
- Safe file operations (`rm file.txt`)
- Documented destructive operations (with warnings)

**Configuration**:
```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/destructive_command_blocker.py"
  }]
}
```

---

### 5. File Naming Enforcer

**File**: `file_naming_enforcer.py`

**Purpose**: Enforces file naming conventions and prevents poor naming practices.

**Blocks**:
- Version suffixes (`file_v2.py`, `script_final.py`)
- Backup files (`file.backup`, `file.bak`)
- Temporary suffixes (`file_fixed.py`, `file_update.py`)
- Poor Python naming (mixing snake_case and camelCase)

**Allows**:
- Proper snake_case (`my_module.py`)
- Proper CamelCase (`MyClass.py`)
- Version directories (`v1/`, `v2/`)
- Test files (`test_*.py`)

**Configuration**:
```json
{
  "matcher": "Write|Edit",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/file_naming_enforcer.py"
  }]
}
```

**Example Output**:
```
🚫 Poor file naming detected: script_v2.py

Use git for versioning instead:
  • Create a git commit for changes
  • Use branches for variations
  • Tag releases with semantic versions

Suggested alternatives:
  • Rename to: script.py (use git for history)
  • Use branches: feature/new-script
  • Tag versions: git tag v2.0.0
```

---

### 6. Coding Naming Enforcer

**File**: `coding_naming_enforcer.py`

**Purpose**: Enforces Python naming conventions in code content.

**Validates**:
- Function names (snake_case)
- Class names (PascalCase)
- Constants (UPPER_SNAKE_CASE)
- Module names (snake_case)
- Variable names (snake_case)

**Configuration**:
```json
{
  "matcher": "Write|Edit",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/coding_naming_enforcer.py"
  }]
}
```

---

### 7. Lint Argument Enforcer

**File**: `lint_argument_enforcer.py`

**Purpose**: Ensures linting commands include proper arguments (e.g., file paths, fix flags).

**Validates**:
- Ruff commands have targets
- Pylint commands have paths
- Black commands have targets
- MyPy commands have modules

**Configuration**:
```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/lint_argument_enforcer.py"
  }]
}
```

---

### 8. Temporary File Blocker

**File**: `tmp_creation_blocker.py`

**Purpose**: Prevents file creation in system temporary directories for better observability.

**Why**: System temp directories clutter your system and make debugging harder. All project files should live in the project directory for better tracking, version control, and observability.

**Blocks**:
- `/tmp/*` - Standard Unix/Linux temp
- `/var/tmp/*` - Variable temp directory
- `/private/tmp/*` - macOS-specific temp
- `/dev/shm/*` - Shared memory temp
- `/run/shm/*` - Alternative shared memory temp

**Allows**:
- Project-local directories (e.g., `./temp/`, `./cache/`)
- Any path outside system temp directories

**Tools Monitored**:
- `Write` - Direct file creation
- `NotebookEdit` - Jupyter notebook files
- `Bash` - Shell commands (future enhancement)

**Example Blocked Operation**:
```
🚫 Blocked file creation in system temp directory.
Path: /tmp/debug.log
Policy: Never create files in system temp paths for better observability.
Alternative: Use project directory instead:
  - Create: /Users/ringo/Desktop/claude-setup-python/temp/debug.log
  - Then add 'temp/' to .gitignore if needed
```

**Configuration**:
```json
{
  "matcher": "Write|NotebookEdit|Bash",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py"
  }]
}
```

**Testing**:
```bash
uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py -v
```

**Specification**: `specs/experts/cc_hook_expert/tmp-creation-blocker-spec.md`

---

### 9. PreTools Logging

**File**: `pre_tools_logging.py`

**Purpose**: Logs all PreToolUse hook executions for debugging and auditing.

**Logs**:
- Timestamp
- Hook event name
- Tool name
- Input parameters
- Decision made

**Configuration**:
```json
{
  "matcher": "*",
  "hooks": [{
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/pre_tools_logging.py"
  }]
}
```

---

## Shared Utilities

### `utils/data_types.py`

Centralized TypedDict definitions for consistent type safety.

**Key Types**:

```python
class ToolInput(TypedDict, total=False):
    """Input parameters from Claude Code tools."""
    file_path: str
    content: str

class HookSpecificOutput(TypedDict):
    """PreToolUse hook output structure."""
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str

class HookOutput(TypedDict, total=False):
    """Complete hook output."""
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
```

### `utils/utils.py`

Shared utility functions for common operations.

**Key Functions**:

```python
def parse_hook_input() -> Optional[Tuple[str, ToolInput]]:
    """Parse and validate hook input from stdin."""

def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False
) -> None:
    """Output formatted JSON decision and exit."""

def get_file_path(tool_input: ToolInput) -> str:
    """Extract file path from tool input."""
```

**Benefits**:
- **DRY Principle**: 30-35% code reduction per hook
- **Consistency**: All hooks use identical patterns
- **Type Safety**: Centralized type definitions
- **Maintainability**: Bug fixes in one place benefit all hooks

---

## Adding New Hooks

### Step-by-Step Guide

#### 1. Write Test First (TDD)

Create `tests/test_my_new_hook.py`:

```python
#!/usr/bin/env python3
"""Tests for My New Hook"""

import json
import subprocess
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent.parent / "my_new_hook.py"

def run_hook(tool_name: str, **kwargs) -> dict:
    """Run the hook with test input."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": kwargs
    }

    result = subprocess.run(
        ["uv", "run", str(HOOK_SCRIPT)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)

def test_blocks_invalid_operation():
    """Test that invalid operations are blocked."""
    output = run_hook("Bash", command="dangerous operation")
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

if __name__ == "__main__":
    test_blocks_invalid_operation()
    print("✓ test_blocks_invalid_operation")
```

#### 2. Create Minimal Hook Implementation

Create `my_new_hook.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
My New Hook - PreToolUse Hook
===============================

Description of what this hook does.
"""

try:
    from .utils.utils import parse_hook_input, output_decision
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision
    from utils.data_types import ToolInput


def validate_operation(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Validate the operation.

    Returns:
        Error message if invalid, None if valid
    """
    # Your validation logic here
    return None  # or error message


def main() -> None:
    """Main entry point."""
    parsed = parse_hook_input()
    if not parsed:
        return

    tool_name, tool_input = parsed

    # Validate
    violation = validate_operation(tool_name, tool_input)

    if violation:
        output_decision("deny", violation, suppress_output=True)
    else:
        output_decision("allow", "Operation is valid")


if __name__ == "__main__":
    main()
```

#### 3. Run Test (See it Fail)

```bash
uv run python .claude/hooks/pre_tools/tests/test_my_new_hook.py
```

#### 4. Implement Logic

Add your validation logic to make the test pass.

#### 5. Run Code Quality Checks

```bash
# Ruff
uv run ruff check my_new_hook.py

# Basedpyright
uv run basedpyright my_new_hook.py

# Vulture (dead code detection)
uv run vulture my_new_hook.py --min-confidence 80
```

#### 6. Make Executable

```bash
chmod +x .claude/hooks/pre_tools/my_new_hook.py
```

#### 7. Add to Configuration

Edit `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/my_new_hook.py"
          }
        ]
      }
    ]
  }
}
```

#### 8. Test Integration

```bash
# Test hook directly
echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | \
  uv run .claude/hooks/pre_tools/my_new_hook.py | jq .
```

---

## Testing

### Running Tests

**Run All Tests**:
```bash
uv run python .claude/hooks/pre_tools/tests/test_*.py
```

**Run Specific Test**:
```bash
uv run python .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py
```

**Run with Pytest** (if available):
```bash
uv run pytest .claude/hooks/pre_tools/tests/
```

### Test Structure

```python
def test_descriptive_name():
    """Clear description of what this test validates."""
    # Arrange
    input_data = {...}

    # Act
    output = run_hook("ToolName", **input_data)

    # Assert
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "expected text" in output["hookSpecificOutput"]["permissionDecisionReason"]
```

### Code Coverage

```bash
# Install coverage
uv add --dev coverage

# Run with coverage
uv run coverage run -m pytest .claude/hooks/pre_tools/tests/
uv run coverage report
uv run coverage html  # Generate HTML report
```

---

## Configuration

### Settings File Structure

Edit `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/universal_hook_logger.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/destructive_command_blocker.py"
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
          }
        ]
      },
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_dependency_blocker.py"
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/file_naming_enforcer.py"
          }
        ]
      },
      {
        "matcher": "Read|Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/sensitive_file_access_validator.py"
          }
        ]
      }
    ]
  }
}
```

### Matcher Patterns

- `*` - Match all tools
- `Bash` - Match only Bash tool
- `Write|Edit` - Match Write OR Edit tools
- `Read|Write|Edit|Bash` - Match multiple tools

### Local Overrides

Create `.claude/settings.local.json` (gitignored) for personal overrides:

```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

This disables all PreToolUse hooks locally without affecting the team.

---

## Troubleshooting

### Hook Not Executing

**Check Registration**:
```bash
# In Claude Code
/hooks
```

Look for your hook in the output.

**Verify Executable Permission**:
```bash
chmod +x .claude/hooks/pre_tools/my_hook.py
```

**Test Manually**:
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"test"}}' | \
  uv run .claude/hooks/pre_tools/my_hook.py
```

### Hook Errors

**Enable Debug Mode**:
```bash
claude --debug
```

**Check Logs**:
```bash
# Hook logs are in
agents/hook_logs/<session_id>/PreToolUse.jsonl
```

**Common Issues**:

1. **JSON Parse Error**: Ensure your hook outputs valid JSON
2. **Import Error**: Check that `utils/` directory is accessible
3. **Permission Error**: Run `chmod +x` on the hook script
4. **Timeout**: Default is 60s, increase if needed in settings

### Hook Blocks Valid Operation

**Temporary Disable**:

Edit `.claude/settings.local.json`:
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Check Hook Logic**:
```bash
# Test with specific input
echo '{"tool_name":"Bash","tool_input":{"command":"your command"}}' | \
  uv run .claude/hooks/pre_tools/hook_name.py | jq .
```

**Report Issue**:
- File bug report with hook name
- Include command that was blocked
- Include expected behavior

---

## Best Practices

### Hook Development

1. **Single Responsibility**: Each hook should do one thing well
2. **Fail-Safe**: Always allow operations on errors
3. **Educational**: Provide helpful guidance, not just "no"
4. **Type-Safe**: Use TypedDict and strict type checking
5. **Test-Driven**: Write tests before implementation
6. **Fast**: Hooks should execute in < 100ms

### Security

1. **Validate Input**: Never trust JSON input directly
2. **Sanitize Paths**: Check for `..` traversal
3. **Regex Safety**: Avoid ReDoS with complex patterns
4. **No Secrets**: Never log sensitive data
5. **Fail Open**: Errors should allow (not block) operations

### Performance

1. **Compile Regex**: Use module-level compiled patterns
2. **Early Exit**: Check cheapest conditions first
3. **Cache**: Use `@lru_cache` for expensive operations
4. **Limit Input**: Cap command/content length for parsing

---

## Appendix

### Environment Variables

- `CLAUDE_PROJECT_DIR`: Absolute path to project root
- `CLAUDE_CODE_REMOTE`: "true" for web environments

### Exit Codes

- `0`: Success (JSON output controls permission)
- `1`: Non-blocking error (operation continues)
- `2`: Blocking error (deprecated, use JSON output)

### Hook Output Format

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Human-readable explanation"
  },
  "suppressOutput": true  // Optional: hide from transcript
}
```

### Related Documentation

- [Claude Code Hooks Reference](https://docs.claude.com/en/docs/claude-code/hooks)
- [UV Documentation](https://docs.astral.sh/uv/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [JSON Schema](https://json-schema.org/)

---

## Contributing

### Code Standards

- Python 3.12+
- PEP 8 compliant (via Ruff)
- Type-safe (via Basedpyright in strict mode)
- No dead code (via Vulture)
- 100% test coverage target

### Pull Request Process

1. Write tests first (TDD)
2. Implement minimal solution
3. Pass all code quality checks
4. Update documentation
5. Submit PR with clear description

### Questions?

- File issues in the project tracker
- Check existing hooks for examples
- Review specification files in `specs/`

---

**Last Updated**: 2025-10-26
**Version**: 1.0.0
**Maintainer**: Claude Code Team
