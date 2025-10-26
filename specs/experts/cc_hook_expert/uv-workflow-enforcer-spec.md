# UV Workflow Enforcer Hook Specification

## Overview

**Hook Name**: `uv_workflow_enforcer.py`
**Category**: PreToolUse Hook
**Event**: PreToolUse
**Matcher**: `Bash`
**Purpose**: Enforce the use of UV for all Python-related commands during development, providing educational guidance and command alternatives.

## Purpose and Objectives

This hook addresses a common workflow issue where developers continue using traditional `python` and `pip` commands despite the project standardizing on UV. The hook serves three primary objectives:

1. **Enforcement**: Intercept and redirect `python`/`pip` commands to UV equivalents
2. **Education**: Provide clear, helpful guidance on UV command syntax and benefits
3. **Flexibility**: Allow fallback cases where UV cannot or should not be used

### Problem Statement

Despite repeated reminders to use UV, developers often default to familiar patterns:
- Running scripts with `python script.py` instead of `uv run script.py`
- Installing packages with `pip install` instead of `uv add`
- Using `pip` for operations that UV handles more elegantly

This creates inconsistencies in dependency management and bypasses UV's benefits:
- Fast dependency resolution
- Automatic virtual environment management
- Locked, reproducible environments
- Modern Python tooling integration

## Event Selection Rationale

**Event**: PreToolUse
**Tool Matcher**: `Bash`

**Why PreToolUse?**
- Intercepts commands before execution, preventing problematic operations
- Allows for educational feedback and command correction
- Provides opportunity to suggest better alternatives

**Why Bash tool specifically?**
- All shell commands go through the Bash tool in Claude Code
- Captures both direct `python`/`pip` invocations and complex command chains
- Enables pattern matching on command strings before execution

## Input Schema

### Hook Input Structure

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "python script.py",
    "description": "Run Python script"
  }
}
```

### Key Fields

- **tool_name**: Must be "Bash" for this hook to activate
- **tool_input.command**: The shell command to validate
- **tool_input.description**: Optional description of command intent

## Output Schema

### Success Output (Allow)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Command uses UV correctly"
  }
}
```

### Denial Output (Block)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Use UV instead of pip...\n\nCommand detected: pip install requests\nUV equivalent: uv add requests\n\nWhy UV?\n• Faster dependency resolution\n• Automatic environment management\n• Locked, reproducible builds\n\nCommon UV commands:\n  uv add <package>     - Add dependency\n  uv remove <package>  - Remove dependency\n  uv sync              - Install all dependencies\n  uv lock              - Update lock file\n  uv run <script>      - Run Python script\n\nDocs: https://docs.astral.sh/uv/"
  },
  "suppressOutput": true
}
```

### Ask Permission Output (Educational)

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "⚠️ Consider using UV instead...\n\n[Educational message]"
  }
}
```

## Detection Logic

### Commands to Intercept

#### Python Interpreter Commands

Pattern: `python`, `python3`, `python3.X` at command start or after `&&`, `||`, `;`, `|`

**Examples to intercept**:
```bash
python script.py
python3 -m module
python -c "print('hello')"
python3.12 script.py
```

**UV Equivalents**:
```bash
uv run script.py
uv run python -m module
uv run python -c "print('hello')"
uv run --python 3.12 script.py
```

#### Pip Package Management Commands

Pattern: `pip`, `pip3` followed by subcommands

**Examples to intercept**:
```bash
pip install requests
pip install -r requirements.txt
pip uninstall package
pip install --upgrade package
pip install -e .
```

**UV Equivalents**:
```bash
uv add requests
uv sync  # for requirements.txt
uv remove package
uv add --upgrade package
uv pip install -e .  # fallback for editable installs
```

#### Common Pip Operations

| Pip Command | UV Equivalent | Notes |
|------------|---------------|-------|
| `pip install <pkg>` | `uv add <pkg>` | Adds to pyproject.toml |
| `pip install <pkg>==<ver>` | `uv add <pkg>==<ver>` | Pin specific version |
| `pip install -r requirements.txt` | `uv sync` | Sync all dependencies |
| `pip uninstall <pkg>` | `uv remove <pkg>` | Remove from project |
| `pip list` | `uv pip list` | Fallback: list packages |
| `pip freeze` | `uv pip freeze` | Fallback: export deps |
| `pip show <pkg>` | `uv pip show <pkg>` | Fallback: show package info |
| `pip install -e .` | `uv pip install -e .` | Fallback: editable install |
| `pip install --upgrade <pkg>` | `uv add --upgrade <pkg>` | Update package |

### Fallback Cases (Allow Without Warning)

The following patterns should be **allowed** as UV alternatives don't exist or aren't appropriate:

#### 1. UV Commands (Already Correct)
```bash
uv run script.py
uv add package
uv sync
uv lock
uv pip install -e .  # Legitimate fallback
```

#### 2. System Python Operations
```bash
which python
python --version
python -V
/usr/bin/python3 --version  # Absolute path to system Python
```

#### 3. Shebang Inspection
```bash
head -n 1 script.py | grep python
cat script.py | grep "#!/usr/bin/env python"
```

#### 4. Documentation/Help Commands
```bash
python --help
pip --help
python -m pip --version
```

#### 5. Non-Executable Context
```bash
echo "python script.py"  # Just printing
git commit -m "Update python version"  # In strings
export PYTHON_PATH=/usr/bin/python  # Environment variables
```

#### 6. Build/Setup Operations (Conditional)
```bash
python setup.py sdist  # Package building
python setup.py develop  # Development mode setup
```

*Note: These should show warnings but may be allowed with user confirmation*

#### 7. Testing/CI Specific Operations
```bash
python -m pytest
python -m unittest discover
python -m coverage run
```

*Note: These can be run through UV, so provide suggestions but allow with confirmation*

### Detection Patterns (Regular Expressions)

```python
# Python interpreter detection
PYTHON_INTERPRETER = r'\b(python3?(\.\d+)?)\s'

# Pip command detection
PIP_COMMAND = r'\bpip3?\s+(install|uninstall|list|freeze|show|search)'

# UV command detection (to skip)
UV_COMMAND = r'\buv\s+(run|add|remove|sync|lock|pip)'

# System/info commands (to allow)
SYSTEM_INFO = r'\b(python3?|pip3?)\s+(--version|-V|--help|-h|help)\b'

# Shebang inspection (to allow)
SHEBANG_CHECK = r'(head|cat|grep).*python'

# String context (to allow)
STRING_CONTEXT = r'(echo|printf|git commit).*["\'].*python.*["\']'
```

## Educational Message Templates

### Template 1: Direct Pip Install

```
🚫 Use UV instead of pip for package management

Command detected: pip install {package}
UV equivalent:    uv add {package}

Why UV?
• ⚡ 10-100x faster dependency resolution
• 🔒 Automatic lock file management
• 📦 Virtual environment handling built-in
• 🎯 Works with pyproject.toml (modern Python standard)

Common UV Commands:
  uv add <package>        Add a dependency
  uv add --dev <package>  Add a dev dependency
  uv remove <package>     Remove a dependency
  uv sync                 Install all dependencies
  uv lock                 Update lock file only
  uv run <script>         Run a Python script

Learn more: https://docs.astral.sh/uv/
```

### Template 2: Python Script Execution

```
🚫 Use UV to run Python scripts

Command detected: python {script}
UV equivalent:    uv run {script}

Benefits:
• ✅ Runs in project's virtual environment automatically
• ✅ Ensures dependencies are installed
• ✅ Supports inline script metadata
• ✅ Works with any Python version

Examples:
  uv run script.py              # Run script
  uv run --python 3.12 script.py  # Specific Python version
  uv run python -m module       # Run module
  uv run --with requests script.py  # Add temporary dependency

Learn more: https://docs.astral.sh/uv/guides/scripts/
```

### Template 3: Requirements.txt Installation

```
🚫 Use UV sync instead of pip install -r

Command detected: pip install -r requirements.txt
UV equivalent:    uv sync

Why uv sync?
• 📋 Installs dependencies from pyproject.toml + uv.lock
• 🔐 Ensures exact versions from lock file
• 🎯 Creates/updates venv automatically
• ⚡ Much faster than pip

Migration path:
1. Convert requirements.txt to pyproject.toml:
   uv add $(cat requirements.txt | grep -v "^#" | grep -v "^$")

2. Or keep requirements.txt temporarily:
   uv pip install -r requirements.txt  # Fallback option

3. Long-term: Move to pyproject.toml for modern Python packaging

Learn more: https://docs.astral.sh/uv/guides/projects/
```

### Template 4: Fallback Cases Explanation

```
ℹ️ This command might work better with UV

Command detected: {command}
Consider:         {suggestion}

This operation may work, but UV provides better alternatives.
If you need to proceed with the original command, you can:
• Use the fallback: uv pip {original_pip_args}
• Continue anyway if UV doesn't support this operation

Common UV workflows:
  uv add <package>     # Instead of pip install
  uv remove <package>  # Instead of pip uninstall
  uv sync              # Instead of pip install -r requirements.txt
  uv lock              # Update dependency locks
  uv run <script>      # Instead of python script.py

Learn more: https://docs.astral.sh/uv/
```

## Security Validation Requirements

### Input Validation

1. **Command String Validation**
   - Ensure command is a valid string (non-empty)
   - Handle multiline commands properly
   - Parse command chains (`&&`, `||`, `;`)

2. **Pattern Safety**
   - Use compiled regex patterns for performance
   - Prevent regex denial-of-service (ReDoS) attacks
   - Limit command length for parsing (reasonable limit: 10,000 chars)

3. **Path Safety**
   - No path traversal concerns (we're not accessing files)
   - Validate that we're in a UV-compatible project (check for pyproject.toml)

### Error Handling

1. **Invalid JSON Input**: Exit gracefully with code 0 (non-blocking)
2. **Missing Command Field**: Allow execution (no command to validate)
3. **Regex Failures**: Log error, allow execution (fail-safe)
4. **Long Commands**: Truncate for display, still analyze

## Dependency Management

### UV Script Metadata

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**Dependencies**: None required (uses standard library only)

**Python Version**: 3.12+ (for modern type hints and match/case support)

### Standard Library Imports

```python
import json
import re
import sys
from pathlib import Path
from typing import Literal, Optional, Tuple, Pattern
```

## Implementation Plan

### File Structure

```
.claude/hooks/pre_tools/
├── uv_workflow_enforcer.py       # Main hook implementation
├── utils/
│   ├── data_types.py              # Shared TypedDict definitions (extend if needed)
│   └── utils.py                    # Shared utilities (reuse existing)
└── tests/
    ├── test_uv_workflow_enforcer.py  # Unit + integration tests
    └── test_data_types.py            # Update if extending types
```

### Implementation Steps

#### Step 1: Core Command Detection

```python
def detect_python_command(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect Python interpreter invocations.

    Returns:
        (detected_command, suggested_uv_command) or None
    """
    # Implementation details...
    pass

def detect_pip_command(command: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect pip package management commands.

    Returns:
        (detected_command, pip_subcommand, suggested_uv_command) or None
    """
    # Implementation details...
    pass
```

#### Step 2: Fallback Detection

```python
def is_fallback_case(command: str) -> bool:
    """
    Check if command is a legitimate fallback case.

    Returns:
        True if command should be allowed without warning
    """
    # Check for UV commands
    # Check for system info commands
    # Check for string contexts
    # Check for shebang inspection
    pass
```

#### Step 3: Educational Message Generation

```python
def generate_educational_message(
    detected_cmd: str,
    suggested_cmd: str,
    message_type: Literal["python", "pip_install", "pip_requirements", "fallback"]
) -> str:
    """
    Generate educational denial message with UV alternatives.

    Args:
        detected_cmd: The command that was detected
        suggested_cmd: The suggested UV equivalent
        message_type: Type of message template to use

    Returns:
        Formatted educational message
    """
    pass
```

#### Step 4: Main Hook Logic

```python
def main() -> None:
    """Main entry point for UV workflow enforcer hook."""
    # 1. Parse input using shared utility
    parsed = parse_hook_input()
    if not parsed:
        return

    tool_name, tool_input = parsed

    # 2. Only validate Bash commands
    if tool_name != "Bash":
        output_decision("allow", "Not a Bash command")
        return

    # 3. Extract command from tool_input
    command = tool_input.get("command", "")
    if not command:
        output_decision("allow", "No command to validate")
        return

    # 4. Check for fallback cases first
    if is_fallback_case(command):
        output_decision("allow", "Legitimate UV fallback or system command")
        return

    # 5. Detect Python/pip usage
    violation = detect_uv_violation(command)

    if violation:
        detected_cmd, suggested_cmd, msg_type = violation
        message = generate_educational_message(detected_cmd, suggested_cmd, msg_type)
        output_decision("deny", message, suppress_output=True)
    else:
        output_decision("allow", "Command follows UV workflow")
```

### Testing Scenarios

#### Unit Tests

1. **Command Detection Tests**
   ```python
   def test_detect_python_script():
       assert detect_python_command("python script.py") is not None
       assert detect_python_command("python3 script.py") is not None
       assert detect_python_command("uv run script.py") is None

   def test_detect_pip_install():
       assert detect_pip_command("pip install requests") is not None
       assert detect_pip_command("pip3 install -r requirements.txt") is not None
       assert detect_pip_command("uv add requests") is None
   ```

2. **Fallback Detection Tests**
   ```python
   def test_fallback_uv_commands():
       assert is_fallback_case("uv run script.py") is True
       assert is_fallback_case("uv add requests") is True

   def test_fallback_system_commands():
       assert is_fallback_case("python --version") is True
       assert is_fallback_case("which python") is True

   def test_fallback_string_context():
       assert is_fallback_case('echo "python script.py"') is True
       assert is_fallback_case("git commit -m 'Update python'") is True
   ```

3. **Message Generation Tests**
   ```python
   def test_educational_message_format():
       msg = generate_educational_message(
           "pip install requests",
           "uv add requests",
           "pip_install"
       )
       assert "🚫" in msg
       assert "uv add requests" in msg
       assert "Why UV?" in msg or "Benefits:" in msg
   ```

#### Integration Tests

1. **Full Hook Workflow**
   ```python
   def test_hook_denies_pip_install():
       input_data = {
           "tool_name": "Bash",
           "tool_input": {"command": "pip install requests"}
       }
       result = run_hook(input_data)
       assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

   def test_hook_allows_uv_commands():
       input_data = {
           "tool_name": "Bash",
           "tool_input": {"command": "uv add requests"}
       }
       result = run_hook(input_data)
       assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
   ```

2. **Edge Cases**
   ```python
   def test_command_chains():
       # Should detect python in command chain
       cmd = "uv sync && python script.py"
       # Should suggest: uv sync && uv run script.py

   def test_complex_pip_commands():
       cmd = "pip install -e . --no-deps --no-build-isolation"
       # Should suggest fallback: uv pip install -e . --no-deps --no-build-isolation
   ```

### Configuration Changes

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
          }
        ]
      }
    ]
  }
}
```

**Important**: This hook should be added to the PreToolUse Bash matcher array. If there are existing Bash hooks, add this to the same matcher group to avoid duplication.

## Error Handling Strategy

### Error Categories

1. **Input Errors** (Non-blocking)
   - Invalid JSON → Exit 0, allow operation
   - Missing fields → Exit 0, allow operation
   - Malformed command → Exit 0, allow operation

2. **Parsing Errors** (Non-blocking)
   - Regex failures → Log error, exit 0, allow operation
   - Unknown command patterns → Exit 0, allow operation

3. **Logic Errors** (Fail-safe)
   - Unexpected exceptions → Catch, log, exit 0, allow operation

### Error Output Format

```python
def handle_error(error: Exception) -> None:
    """Handle errors gracefully without blocking Claude."""
    # Log to stderr for debugging
    print(f"UV workflow enforcer error: {error}", file=sys.stderr)
    # Allow operation to continue
    output_decision("allow", f"Hook error (fail-safe): {error}")
```

## Performance Considerations

### Optimization Strategies

1. **Compile Regex Patterns Once**
   ```python
   # At module level
   PYTHON_PATTERN = re.compile(r'\b(python3?(\.\d+)?)\s')
   PIP_PATTERN = re.compile(r'\bpip3?\s+(install|uninstall)')
   ```

2. **Early Exits**
   - Check for UV commands first (most common after adoption)
   - Exit early on non-Bash tools
   - Skip validation for empty commands

3. **Command Length Limits**
   - Cap analysis at 10,000 characters
   - Truncate display messages for very long commands

4. **Minimal Dependencies**
   - Use only Python standard library
   - No external API calls
   - No file I/O (except stdin/stdout)

### Expected Performance

- **Typical execution time**: < 50ms
- **Timeout**: Use default 60s (should never be reached)
- **Memory usage**: Minimal (< 10MB)

## Integration Considerations

### Integration with Existing Hooks

1. **universal_hook_logger.py**
   - Runs in parallel, no conflicts
   - Will log this hook's decisions

2. **sensitive_file_access_validator.py**
   - May both validate Bash commands
   - No conflicts (different validation targets)

3. **uv_dependency_blocker.py**
   - Complementary: blocks file edits, this blocks commands
   - Together provide comprehensive UV enforcement

### Project Context Awareness

**Check for UV project**:
```python
def is_uv_project() -> bool:
    """Check if current directory is a UV project."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    return (project_dir / "pyproject.toml").exists()
```

**Behavior**:
- In UV projects: Enforce UV usage strictly
- In non-UV projects: Provide suggestions but allow with warning
- Mixed projects: Detect pyproject.toml presence, suggest migration

## Rollback Strategy

### Disabling the Hook

**Temporary disable** (in `.claude/settings.local.json`):
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Permanent disable**: Remove from `.claude/settings.json`

### Gradual Rollout

**Phase 1**: Ask permission mode (provide suggestions, don't block)
```python
# In generate_educational_message, change decision to "ask"
output_decision("ask", message)
```

**Phase 2**: Deny mode for critical commands (pip install, python scripts)

**Phase 3**: Deny mode for all violations

### Monitoring and Feedback

1. **Universal hook logger** will capture all decisions
2. **Check logs** at `agents/hook_logs/<session_id>/PreToolUse.jsonl`
3. **Analyze patterns** to refine fallback cases
4. **User feedback** through deny message quality

## Success Metrics

### Enforcement Metrics

- **Interception rate**: % of python/pip commands intercepted
- **Compliance rate**: % of Bash commands using UV after intervention
- **False positive rate**: % of legitimate commands incorrectly blocked

### Educational Metrics

- **Message clarity**: User feedback on helpfulness
- **Command adoption**: Increase in UV command usage over time
- **Developer satisfaction**: Fewer violations after education period

## UV Command Reference (For Quick Access)

### Core Commands

```bash
# Package Management
uv add <package>              # Add dependency (like pip install)
uv add --dev <package>        # Add dev dependency
uv add <package>==<version>   # Pin specific version
uv remove <package>           # Remove dependency (like pip uninstall)

# Environment Management
uv sync                       # Install all dependencies (like pip install -r requirements.txt)
uv lock                       # Update lock file without installing

# Running Code
uv run <script>               # Run Python script (like python script.py)
uv run python -m <module>     # Run Python module
uv run --python 3.12 <script> # Run with specific Python version
uv run --with <pkg> <script>  # Run with temporary dependency

# Project Management
uv init                       # Initialize new project
uv init --script <file>       # Initialize standalone script with metadata

# Fallback Commands (when UV equivalent doesn't exist)
uv pip install <args>         # Direct pip wrapper
uv pip freeze                 # Export dependencies
uv pip list                   # List installed packages
uv pip show <package>         # Show package info
```

### Migration Commands

```bash
# Convert from requirements.txt
uv add $(cat requirements.txt | grep -v "^#" | tr '\n' ' ')

# Convert from Pipfile
uv add $(cat Pipfile | grep -A 1000 '[packages]' | grep '=' | cut -d'=' -f1 | tr '\n' ' ')

# Create lock file from existing environment
uv lock
```

## Appendix: Implementation Pseudo-code

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""UV Workflow Enforcer - PreToolUse Hook"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Literal, Optional, Tuple, Pattern

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision
except ImportError:
    from utils.utils import parse_hook_input, output_decision

# === REGEX PATTERNS ===
PYTHON_INTERPRETER = re.compile(r'\b(python3?(\.\d+)?)\s+')
PIP_COMMAND = re.compile(r'\bpip3?\s+(install|uninstall|list|freeze|show)')
UV_COMMAND = re.compile(r'\buv\s+(run|add|remove|sync|lock|pip)')
SYSTEM_INFO = re.compile(r'\b(python3?|pip3?)\s+(--version|-V|--help|-h)\b')
SHEBANG_CHECK = re.compile(r'(head|cat|grep).*python')
STRING_CONTEXT = re.compile(r'(echo|printf|git\s+commit).*["\'].*python.*["\']')

# === DETECTION FUNCTIONS ===

def is_fallback_case(command: str) -> bool:
    """Check if command is a legitimate fallback case."""
    # Allow UV commands
    if UV_COMMAND.search(command):
        return True

    # Allow system info commands
    if SYSTEM_INFO.search(command):
        return True

    # Allow shebang inspection
    if SHEBANG_CHECK.search(command):
        return True

    # Allow string contexts
    if STRING_CONTEXT.search(command):
        return True

    # Allow 'which python' and version checks
    if re.search(r'\bwhich\s+python', command):
        return True

    return False

def detect_python_command(command: str) -> Optional[Tuple[str, str]]:
    """Detect Python interpreter invocations and suggest UV."""
    match = PYTHON_INTERPRETER.search(command)
    if not match:
        return None

    # Extract the python command
    python_cmd = match.group(1)

    # Build suggestion
    suggestion = command.replace(python_cmd, "uv run", 1)

    return (command, suggestion)

def detect_pip_command(command: str) -> Optional[Tuple[str, str, str]]:
    """Detect pip commands and suggest UV equivalents."""
    match = PIP_COMMAND.search(command)
    if not match:
        return None

    subcommand = match.group(1)

    # Map pip subcommands to UV equivalents
    if subcommand == "install":
        if "-r requirements.txt" in command or "-r " in command:
            suggestion = "uv sync"
            msg_type = "pip_requirements"
        elif "-e ." in command:
            suggestion = command.replace("pip", "uv pip", 1)
            msg_type = "fallback"
        else:
            # Extract package name
            pkg_match = re.search(r'install\s+([a-zA-Z0-9_-]+)', command)
            if pkg_match:
                package = pkg_match.group(1)
                suggestion = f"uv add {package}"
            else:
                suggestion = "uv add <package>"
            msg_type = "pip_install"

    elif subcommand == "uninstall":
        pkg_match = re.search(r'uninstall\s+([a-zA-Z0-9_-]+)', command)
        if pkg_match:
            package = pkg_match.group(1)
            suggestion = f"uv remove {package}"
        else:
            suggestion = "uv remove <package>"
        msg_type = "pip_install"

    else:
        # For list, freeze, show - suggest uv pip fallback
        suggestion = command.replace("pip", "uv pip", 1)
        msg_type = "fallback"

    return (command, suggestion, msg_type)

def detect_uv_violation(command: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect UV workflow violations.

    Returns:
        (detected_command, suggested_command, message_type) or None
    """
    # Check for pip commands first (higher priority)
    pip_result = detect_pip_command(command)
    if pip_result:
        detected, suggested, msg_type = pip_result
        return (detected, suggested, msg_type)

    # Check for python commands
    python_result = detect_python_command(command)
    if python_result:
        detected, suggested = python_result
        return (detected, suggested, "python")

    return None

# === MESSAGE GENERATION ===

def generate_educational_message(
    detected_cmd: str,
    suggested_cmd: str,
    message_type: str
) -> str:
    """Generate educational message with UV alternatives."""

    # Truncate long commands for display
    display_cmd = detected_cmd if len(detected_cmd) <= 60 else detected_cmd[:57] + "..."

    if message_type == "python":
        return f"""🚫 Use UV to run Python scripts

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Benefits:
• ✅ Runs in project's virtual environment automatically
• ✅ Ensures dependencies are installed
• ✅ Supports inline script metadata
• ✅ Works with any Python version

Common UV commands:
  uv run <script>              # Run script
  uv run --python 3.12 <script>  # Specific Python version
  uv run python -m <module>    # Run module

Learn more: https://docs.astral.sh/uv/guides/scripts/"""

    elif message_type == "pip_install":
        return f"""🚫 Use UV instead of pip for package management

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Why UV?
• ⚡ 10-100x faster dependency resolution
• 🔒 Automatic lock file management
• 📦 Virtual environment handling built-in
• 🎯 Works with pyproject.toml (modern Python standard)

Common UV commands:
  uv add <package>        # Add dependency
  uv add --dev <package>  # Add dev dependency
  uv remove <package>     # Remove dependency
  uv sync                 # Install all dependencies
  uv lock                 # Update lock file

Learn more: https://docs.astral.sh/uv/"""

    elif message_type == "pip_requirements":
        return f"""🚫 Use UV sync instead of pip install -r

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Why uv sync?
• 📋 Installs dependencies from pyproject.toml + uv.lock
• 🔐 Ensures exact versions from lock file
• 🎯 Creates/updates venv automatically
• ⚡ Much faster than pip

Migration path:
1. Convert requirements.txt to pyproject.toml
2. Or use: uv pip install -r requirements.txt (fallback)
3. Long-term: Move to pyproject.toml for modern Python packaging

Learn more: https://docs.astral.sh/uv/guides/projects/"""

    elif message_type == "fallback":
        return f"""ℹ️ Consider using UV for this operation

Command detected: {display_cmd}
UV suggestion:    {suggested_cmd}

This operation may work, but UV provides better alternatives.
The suggested command uses 'uv pip' as a fallback.

Prefer native UV commands when possible:
  uv add <package>     # Instead of pip install
  uv remove <package>  # Instead of pip uninstall
  uv sync              # Instead of pip install -r requirements.txt

Learn more: https://docs.astral.sh/uv/"""

    return f"""🚫 Use UV for Python workflow

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Learn more: https://docs.astral.sh/uv/"""

# === MAIN HOOK ===

def main() -> None:
    """Main entry point for UV workflow enforcer hook."""
    try:
        # Parse input using shared utility
        parsed = parse_hook_input()
        if not parsed:
            return

        tool_name, tool_input = parsed

        # Only validate Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Not a Bash command")
            return

        # Extract command from tool_input (handle dict access)
        command_obj = tool_input.get("command")
        if not command_obj or not isinstance(command_obj, str):
            output_decision("allow", "No command to validate")
            return

        command = command_obj

        # Check for fallback cases first
        if is_fallback_case(command):
            output_decision("allow", "Legitimate UV fallback or system command")
            return

        # Detect UV violations
        violation = detect_uv_violation(command)

        if violation:
            detected_cmd, suggested_cmd, msg_type = violation
            message = generate_educational_message(detected_cmd, suggested_cmd, msg_type)
            output_decision("deny", message, suppress_output=True)
        else:
            output_decision("allow", "Command follows UV workflow")

    except Exception as e:
        # Fail-safe: allow operation on any error
        print(f"UV workflow enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")

if __name__ == "__main__":
    main()
```

## Summary

This specification provides a comprehensive blueprint for implementing the UV Workflow Enforcer hook. The hook will:

1. ✅ **Intercept** all `python` and `pip` commands via Bash tool
2. ✅ **Educate** developers with clear, helpful UV alternatives
3. ✅ **Enforce** UV workflow while allowing legitimate fallback cases
4. ✅ **Integrate** seamlessly with existing hook infrastructure
5. ✅ **Perform** efficiently with minimal overhead
6. ✅ **Fail safely** to avoid disrupting development workflow

The implementation follows established patterns from existing hooks, reuses shared utilities, and provides comprehensive testing coverage. The specification is ready for the build phase.
