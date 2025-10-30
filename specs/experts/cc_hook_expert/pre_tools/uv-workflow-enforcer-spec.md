# UV Workflow Enforcer Hook - Specification

## Metadata

- **Hook Name**: uv_workflow_enforcer.py (replaces uv_dependency_blocker.py)
- **Hook Category**: PreToolUse
- **Version**: 2.0.0
- **Author**: Claude Code Hook Expert
- **Last Updated**: 2025-10-30

## 1. Purpose

Enforce UV-based Python workflow by preventing direct execution of `pip`, `python`, and `python3` commands. Ensure consistent, high-performance package management and script execution across all Claude Code operations by requiring the use of UV commands (`uv run`, `uv add`, `uv pip`, etc.).

## 2. Problem Statement

Direct usage of `pip`, `python`, and `python3` commands bypasses UV's modern Python project management workflow and creates several critical issues:

1. **Environment Fragmentation**: Direct `python` usage doesn't leverage UV's automatic environment management
2. **Dependency Drift**: Using `pip install` without UV breaks lock file consistency and reproducibility
3. **Performance Loss**: Missing UV's parallel installation and caching optimizations
4. **Version Inconsistency**: Direct `python` may use wrong Python version vs. project requirements
5. **Workflow Confusion**: Mixing UV and traditional tools creates unclear dependency management practices
6. **Missing Isolation**: Direct installations pollute global or system environments
7. **Broken Reproducibility**: Changes not tracked in UV's lock file can't be reproduced by team members

### Real-World Impact Examples

```bash
# ❌ Problematic patterns
pip install requests                    # Bypasses UV lock file
python script.py                        # Uses wrong environment/version
python3 -m pip install numpy            # Double bypass (python3 + pip)
python -m venv .venv                    # Manual venv when UV manages this

# ✅ UV-based equivalents
uv add requests                         # Updates lock file automatically
uv run script.py                        # Uses correct environment/version
uv add numpy                            # UV manages dependencies
# UV creates/manages .venv automatically
```

## 3. Objectives

1. **Command-Level Enforcement**: Block direct `pip`, `python`, `python3` command execution
2. **Comprehensive Detection**: Catch commands in various contexts (simple, chained, piped)
3. **Clear UV Alternatives**: Provide specific UV command equivalents for each blocked operation
4. **Smart Context Awareness**: Allow UV-managed Python execution (e.g., `uv run python`)
5. **Educational Messaging**: Help developers learn modern UV workflows
6. **Fail-Safe Behavior**: Allow operations on parsing errors to avoid blocking legitimate work
7. **Zero Dependencies**: Use only Python standard library for maximum portability
8. **Shared Infrastructure**: Leverage pre_tools/utils for consistency

## 4. Hook Event Selection

### Selected Event: PreToolUse

**Rationale**:
- Executes **before** command execution, preventing unwanted operations
- Receives complete command strings for parsing and validation
- Can deny operations via `permissionDecision: "deny"`
- Supports structured error messages with UV command alternatives
- Ideal for workflow enforcement at the command level

**Alternative Events Considered**:
- **PostToolUse**: Too late - commands would already be executed
- **UserPromptSubmit**: Too early - command parameters not yet available
- **SessionStart**: Not appropriate for per-command validation

## 5. Tool Matchers

The hook monitors command execution tools that can run Python/pip commands:

### Primary Tool: Bash

1. **Bash**: Shell command execution
   - Validates `tool_input.command` string
   - Parses for `pip`, `python`, `python3` usage
   - Most common command execution tool
   - Supports complex command structures

### Tools Explicitly Excluded

- **Write**: File creation doesn't execute commands
- **Edit**: File modification doesn't execute commands
- **Read**: Read-only operations
- **Glob/Grep**: Search operations only
- **NotebookEdit**: Jupyter cells have different execution context

### Matcher Configuration

```json
{
  "matcher": "Bash"
}
```

**Note**: This is DIFFERENT from the old uv_dependency_blocker which used `"matcher": "Write|Edit"` for file-based blocking.

## 6. Command Detection Patterns

### 6.1 Commands to Block

#### pip Commands (All Variants)

```python
PIP_PATTERNS = [
    # Direct pip usage
    r'\bpip\s+',              # pip install, pip uninstall, etc.
    r'\bpip3\s+',             # pip3 install

    # Python module invocation of pip
    r'\bpython\s+-m\s+pip\b', # python -m pip install
    r'\bpython3\s+-m\s+pip\b', # python3 -m pip install
]
```

**Examples**:
- `pip install requests`
- `pip3 install numpy`
- `pip uninstall flask`
- `python -m pip install pandas`
- `python3 -m pip install --upgrade pip`

#### python/python3 Commands (Direct Execution)

```python
PYTHON_PATTERNS = [
    # Script execution
    r'\bpython\s+[^\s].*\.py\b',   # python script.py
    r'\bpython3\s+[^\s].*\.py\b',  # python3 script.py

    # Module execution
    r'\bpython\s+-m\s+\w+',        # python -m module
    r'\bpython3\s+-m\s+\w+',       # python3 -m module

    # Interactive/REPL
    r'\bpython\s*$',               # python (REPL)
    r'\bpython3\s*$',              # python3 (REPL)

    # Version checks (questionable - might allow)
    r'\bpython\s+--version\b',     # python --version
    r'\bpython3\s+--version\b',    # python3 --version
]
```

**Examples**:
- `python main.py --arg value`
- `python3 -m pytest tests/`
- `python -c "print('hello')"`
- `python` (interactive REPL)

### 6.2 Commands to ALLOW (Exceptions)

```python
ALLOWED_PATTERNS = [
    # UV-managed Python execution (already using UV!)
    r'\buv\s+run\s+python\b',     # uv run python script.py
    r'\buv\s+run\s+python3\b',    # uv run python3 script.py

    # UV pip interface (using UV!)
    r'\buv\s+pip\s+',              # uv pip install

    # UV tool runs (using UV!)
    r'\buv\s+tool\s+run\s+',       # uv tool run

    # Shebang checks (read-only, informational)
    r'head.*\.py.*#!.*python',     # Checking shebangs
    r'grep.*"#!.*python"',         # Searching for shebangs

    # Documentation/help (informational only)
    r'\bpython\s+-h\b',            # python -h
    r'\bpython\s+--help\b',        # python --help
]
```

### 6.3 Pattern Matching Strategy

**Command Parsing Approach**:
1. Extract command string from tool_input
2. Normalize whitespace and handle multi-line commands
3. Split on command separators (`;`, `&&`, `||`, `|`)
4. Check each command segment independently
5. Apply allow-list patterns first (early return)
6. Apply block patterns second (deny if matched)
7. Handle edge cases (quoted strings, escaped characters)

**Rationale**:
- **Allow-list first**: Prevent false positives for UV-managed commands
- **Segment splitting**: Catch commands in complex chains like `cd dir && python script.py`
- **Regex-based**: Flexible enough for variations but simple to maintain
- **Fail-safe**: On parsing errors, allow (don't block legitimate work)

### 6.4 Command Parsing Challenges

#### Shell Complexity Issues

```bash
# Challenge 1: Command chaining
cd backend && python manage.py runserver

# Challenge 2: Piping
cat script.py | python

# Challenge 3: Subshells
(python -m venv .venv && source .venv/bin/activate)

# Challenge 4: Quoted strings
python -c "import sys; print('test')"

# Challenge 5: Environment variables
PYTHONPATH=/custom python script.py

# Challenge 6: Aliases (can't detect)
alias py=python  # Then: py script.py
```

**Handling Strategy**:
- **Split on separators**: Handle `&&`, `||`, `;`, `|`
- **Regex word boundaries**: Use `\b` to avoid matching `mypython` or `python3.12`
- **Fail-safe**: Complex/ambiguous cases → allow (don't over-block)
- **Aliases**: Can't detect - acceptable limitation
- **Document limitations**: Be transparent about what can/can't be detected

## 7. Input Schema

### Standard PreToolUse Input Structure

```typescript
{
  session_id: string,           // Unique session identifier
  transcript_path: string,      // Path to transcript JSONL
  cwd: string,                  // Current working directory
  hook_event_name: "PreToolUse",
  tool_name: string,            // "Bash"
  tool_input: {                 // Tool-specific parameters
    command: string,            // Shell command to execute
    description?: string,       // Optional command description
    timeout?: number,           // Optional timeout in milliseconds
  }
}
```

### Tool-Specific Input Handling

#### Bash Tool

```python
command = tool_input.get("command", "")
# Parse command for pip/python/python3 usage
```

## 8. Output Schema

### JSON Output Format

```typescript
{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow" | "deny" | "ask",
    permissionDecisionReason: string
  },
  suppressOutput?: boolean  // Optional: hide from transcript
}
```

### Decision Types

#### 8.1 Allow Decision

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Command uses UV workflow"
  }
}
```

**Used when**:
- Command uses UV (e.g., `uv run python script.py`)
- No pip/python/python3 detected
- Tool is not Bash
- Parsing error occurs (fail-safe)

#### 8.2 Deny Decision - pip install

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked: Direct pip usage bypasses UV dependency management\n\nCommand: pip install requests\n\nWhy this is blocked:\n  - Bypasses UV's lock file (uv.lock)\n  - Breaks reproducibility for your team\n  - Misses UV's parallel installation optimizations\n  - Installs into wrong environment\n  - Creates dependency drift over time\n\nUse UV instead:\n\n  For project dependencies:\n    uv add requests              # Add to project + update lock file\n    uv add --dev pytest          # Add dev dependency\n    uv add 'requests>=2.28'      # Add with version constraint\n\n  For one-off installations:\n    uv pip install requests      # Use UV's pip interface\n    uv tool install ruff         # Install CLI tools\n\n  To sync environment:\n    uv sync                      # Install from lock file\n    uv sync --all-extras         # Include all optional dependencies\n\nLearn more: https://docs.astral.sh/uv/concepts/dependencies/"
  },
  "suppressOutput": true
}
```

#### 8.3 Deny Decision - python script.py

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked: Direct python execution bypasses UV environment management\n\nCommand: python main.py --arg value\n\nWhy this is blocked:\n  - Uses system Python instead of project-specified version\n  - Misses dependencies from UV's managed environment\n  - Doesn't respect requires-python constraints\n  - Breaks isolation between projects\n  - Inconsistent behavior across team members\n\nUse UV instead:\n\n  For script execution:\n    uv run main.py --arg value   # Run with UV-managed environment\n    uv run --python 3.12 main.py # Use specific Python version\n    uv run --no-project main.py  # Run without project dependencies\n\n  For module execution:\n    uv run -m pytest tests/      # Run Python modules\n    uv run -m http.server 8000   # Run standard library modules\n\n  For inline code:\n    uv run - <<EOF\n    print('hello from UV')\n    EOF\n\nLearn more: https://docs.astral.sh/uv/guides/scripts/"
  },
  "suppressOutput": true
}
```

#### 8.4 Deny Decision - python -m pip install

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked: python -m pip bypasses UV (double bypass!)\n\nCommand: python -m pip install numpy\n\nWhy this is blocked:\n  - Bypasses UV's environment management (using direct python)\n  - Bypasses UV's dependency resolution (using pip)\n  - Installs into wrong environment\n  - Breaks lock file consistency\n  - Creates unreproducible state\n\nUse UV instead:\n\n  For project dependencies:\n    uv add numpy                 # Add to project + update lock file\n    uv add 'numpy>=1.24'         # Add with version constraint\n\n  For pip-compatible operations:\n    uv pip install numpy         # Use UV's pip interface\n    uv pip install -e .          # Editable install\n    uv pip install -r requirements.txt  # Install from requirements\n\nLearn more: https://docs.astral.sh/uv/pip/"
  },
  "suppressOutput": true
}
```

## 9. Validation Logic

### 9.1 Command Parsing Function

```python
def parse_command_segments(command: str) -> list[str]:
    """
    Split command into segments for independent validation.

    Handles command separators: ;, &&, ||, |

    Args:
        command: Full bash command string

    Returns:
        List of command segments to validate independently

    Examples:
        >>> parse_command_segments("cd dir && python script.py")
        ["cd dir", "python script.py"]
        >>> parse_command_segments("pip install pkg1 pkg2")
        ["pip install pkg1 pkg2"]
        >>> parse_command_segments("echo test | python -")
        ["echo test", "python -"]
    """
    # Split on common command separators
    # Handle edge cases: quoted strings, escaped characters
    import re

    # Simple approach: split on unquoted separators
    # More robust: use shlex for proper shell parsing
    segments = re.split(r'\s*(?:&&|\|\||;|\|)\s*', command)

    return [seg.strip() for seg in segments if seg.strip()]
```

### 9.2 Pattern Detection Function

```python
def is_allowed_command(command_segment: str) -> bool:
    """
    Check if command segment matches allow-list patterns.

    Args:
        command_segment: Single command to check

    Returns:
        True if command is allowed (uses UV or is informational)

    Examples:
        >>> is_allowed_command("uv run python script.py")
        True
        >>> is_allowed_command("uv pip install requests")
        True
        >>> is_allowed_command("python --help")
        True
        >>> is_allowed_command("python script.py")
        False
    """
    import re

    # Check against allow patterns
    allowed_patterns = [
        r'\buv\s+run\s+python',
        r'\buv\s+pip\s+',
        r'\bpython\s+(?:--help|-h)\b',
    ]

    for pattern in allowed_patterns:
        if re.search(pattern, command_segment):
            return True

    return False


def detect_blocked_command(command_segment: str) -> tuple[bool, str, str]:
    """
    Detect if command uses blocked pip/python/python3 patterns.

    Args:
        command_segment: Single command to check

    Returns:
        Tuple of (is_blocked, command_type, detected_command)
        - is_blocked: True if command should be denied
        - command_type: "pip", "python", "python3", or ""
        - detected_command: The specific command that was detected

    Examples:
        >>> detect_blocked_command("pip install requests")
        (True, "pip", "pip install")
        >>> detect_blocked_command("python script.py")
        (True, "python", "python script.py")
        >>> detect_blocked_command("uv run python script.py")
        (False, "", "")
    """
    import re

    # First check allow-list
    if is_allowed_command(command_segment):
        return (False, "", "")

    # Check pip patterns
    pip_patterns = [
        (r'\bpip\s+\w+', "pip"),
        (r'\bpip3\s+\w+', "pip"),
        (r'\bpython3?\s+-m\s+pip\b', "pip"),
    ]

    for pattern, cmd_type in pip_patterns:
        match = re.search(pattern, command_segment)
        if match:
            return (True, cmd_type, match.group())

    # Check python patterns
    python_patterns = [
        (r'\bpython\s+[^\s].*\.py\b', "python"),
        (r'\bpython3\s+[^\s].*\.py\b', "python3"),
        (r'\bpython\s+-m\s+\w+', "python"),
        (r'\bpython3\s+-m\s+\w+', "python3"),
    ]

    for pattern, cmd_type in python_patterns:
        match = re.search(pattern, command_segment)
        if match:
            return (True, cmd_type, match.group())

    return (False, "", "")
```

### 9.3 Message Generation Function

```python
def get_deny_message(
    command: str,
    command_type: str,
    detected_command: str
) -> str:
    """
    Generate appropriate denial message based on command type.

    Args:
        command: Full original command
        command_type: Type of blocked command ("pip", "python", "python3")
        detected_command: Specific command pattern that was detected

    Returns:
        Formatted error message with UV command alternatives
    """
    # Map command types to detailed error messages
    # Include specific UV equivalents
    # Provide educational context

    messages = {
        "pip": generate_pip_denial_message(command),
        "python": generate_python_denial_message(command),
        "python3": generate_python3_denial_message(command),
    }

    return messages.get(command_type, "")
```

### 9.4 Main Validation Function

```python
def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for pip/python/python3 usage.

    Args:
        command: Bash command to validate

    Returns:
        None if validation passes, error message string if validation fails
    """
    if not command:
        return None

    # Parse command into segments
    segments = parse_command_segments(command)

    # Check each segment
    for segment in segments:
        is_blocked, cmd_type, detected = detect_blocked_command(segment)

        if is_blocked:
            return get_deny_message(command, cmd_type, detected)

    return None
```

## 10. Error Handling Strategy

### Fail-Safe Principle

**All errors result in "allow" decision** to prevent disrupting development:

```python
try:
    # Validation logic
    pass
except Exception as e:
    # Log error to stderr
    print(f"UV workflow enforcer error: {e}", file=sys.stderr)
    # Allow operation (fail-safe)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Error Scenarios

1. **Input Parsing Failure**:
   - Decision: Allow
   - Reason: "Failed to parse input (fail-safe)"

2. **Command Extraction Error**:
   - Decision: Allow
   - Behavior: Assume command doesn't use blocked patterns

3. **Regex Compilation Error**:
   - Decision: Allow
   - Continue with remaining patterns

4. **Complex Shell Syntax**:
   - Decision: Allow if uncertain
   - Better to allow edge cases than block legitimate work

## 11. Configuration

### 11.1 Hook Registration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

**Note**: This replaces the old `"matcher": "Write|Edit"` configuration.

### 11.2 Hook Script Location

**Path**: `.claude/hooks/pre_tools/uv_workflow_enforcer.py`

**Execution**: `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py`

### 11.3 Environment Variables

- **CLAUDE_PROJECT_DIR**: Absolute path to project root
  - Used for robust path handling
  - Accessed via: `os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())`

## 12. Dependencies

### UV Script Metadata

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

### Python Version Requirement

- **Minimum**: Python 3.12
- **Rationale**: Modern type hints, match statements, improved regex

### Standard Library Modules

```python
import os          # Environment variables
import re          # Command pattern matching
import sys         # stdin/stdout/stderr
from typing import Optional, Tuple  # Type hints
from pathlib import Path  # Path operations
```

### Shared Utilities

```python
from utils import parse_hook_input, output_decision
```

**Imported Functions**:
- `parse_hook_input()` - Parse and validate JSON from stdin
- `output_decision()` - Output formatted JSON decision

## 13. Testing Strategy

### 13.1 Unit Tests Structure

**Location**: `tests/claude-hook/pre_tools/test_uv_workflow_enforcer.py`

**Test Framework**: pytest with distributed testing

**Execution**: `uv run pytest -n auto tests/claude-hook/pre_tools/test_uv_workflow_enforcer.py`

### 13.2 Test Categories

#### Command Detection Tests

```python
def test_detect_pip_install():
    """Test detection of pip install commands."""
    assert detect_blocked_command("pip install requests")[0] is True
    assert detect_blocked_command("pip3 install numpy")[0] is True
    assert detect_blocked_command("pip uninstall flask")[0] is True

def test_detect_python_script():
    """Test detection of python script.py commands."""
    assert detect_blocked_command("python main.py")[0] is True
    assert detect_blocked_command("python3 script.py --arg")[0] is True

def test_detect_python_module():
    """Test detection of python -m commands."""
    assert detect_blocked_command("python -m pytest")[0] is True
    assert detect_blocked_command("python3 -m pip install pkg")[0] is True

def test_allow_uv_commands():
    """Test that UV commands are allowed."""
    assert detect_blocked_command("uv run python script.py")[0] is False
    assert detect_blocked_command("uv pip install requests")[0] is False
    assert detect_blocked_command("uv add numpy")[0] is False
```

#### Command Parsing Tests

```python
def test_parse_command_chaining():
    """Test parsing of chained commands."""
    segments = parse_command_segments("cd dir && python script.py")
    assert len(segments) == 2
    assert "python script.py" in segments

def test_parse_piped_commands():
    """Test parsing of piped commands."""
    segments = parse_command_segments("cat file | python")
    assert len(segments) == 2

def test_parse_complex_commands():
    """Test parsing of complex command structures."""
    segments = parse_command_segments("cmd1 ; cmd2 || cmd3 && cmd4")
    assert len(segments) == 4
```

#### Message Generation Tests

```python
def test_pip_message_content():
    """Test pip denial message contains UV alternatives."""
    msg = get_deny_message("pip install requests", "pip", "pip install")
    assert "uv add" in msg
    assert "uv pip install" in msg
    assert "lock file" in msg.lower()

def test_python_message_content():
    """Test python denial message contains UV alternatives."""
    msg = get_deny_message("python script.py", "python", "python script.py")
    assert "uv run" in msg
    assert "environment" in msg.lower()
```

#### Integration Tests

```python
def test_bash_tool_blocked_pip():
    """Test Bash tool blocked for pip commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "pip install requests"}
    }
    # Test hook outputs "deny" decision

def test_bash_tool_blocked_python():
    """Test Bash tool blocked for python commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "python main.py"}
    }
    # Test hook outputs "deny" decision

def test_bash_tool_allowed_uv():
    """Test Bash tool allowed for UV commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "uv run python script.py"}
    }
    # Test hook outputs "allow" decision
```

### 13.3 Test Coverage Goals

- **Line Coverage**: ≥ 95%
- **Branch Coverage**: ≥ 90%
- **Pattern Coverage**: All documented patterns tested
- **Edge Cases**: Complex shell syntax, quoted strings, multi-line commands

## 14. Security Considerations

### 14.1 Input Validation

**Risk**: Malformed or malicious command strings

**Mitigation**:
- Use shared `parse_hook_input()` utility
- Validate types before processing
- Fail-safe on errors (allow operation)
- No command execution in hook (read-only)

### 14.2 Command Injection

**Risk**: Hook itself shouldn't execute commands

**Mitigation**:
- Hook is **read-only** - analyzes but never executes
- Uses regex matching, not eval() or exec()
- No subprocess calls
- No shell interpretation

### 14.3 Regex Safety

**Risk**: ReDoS (Regular Expression Denial of Service)

**Mitigation**:
- Use simple, bounded patterns
- Avoid nested quantifiers
- Set timeout on hook execution (60 seconds)
- Test patterns with long inputs

### 14.4 Bypass Considerations

**Known Bypasses**:
1. **Shell aliases**: `alias py=python` then `py script.py`
2. **Environment manipulation**: Setting PATH to custom python
3. **Complex syntax**: Obscure shell constructs
4. **Write then Bash**: Write script with python, then bash it

**Rationale**:
- This is **workflow enforcement**, not security
- Focus on catching **accidental** usage
- Advanced users who intentionally bypass understand implications
- Can't catch 100% of cases - acceptable trade-off

## 15. Performance Considerations

### 15.1 Execution Time

**Target**: < 50ms per invocation

**Optimizations**:
- Simple string operations and regex
- No file system I/O
- No network calls
- Early return on allow-list matches
- Compiled regex patterns (cache)

### 15.2 Memory Usage

**Target**: < 5 MB per invocation

**Considerations**:
- Small string operations
- No large data structures
- Minimal allocations

## 16. Integration Considerations

### 16.1 Coexistence with Other Hooks

**Scenario**: Multiple PreToolUse hooks registered

**Behavior**:
- Hooks run in parallel
- Any "deny" decision blocks operation
- Uses `suppressOutput: true` to avoid spam

**Compatibility**:
- Works alongside universal_hook_logger.py
- Works alongside tmp_creation_blocker.py
- Works alongside other validation hooks
- No shared state or conflicts

### 16.2 Relationship to File-Based Blocking

**Old Hook** (uv_dependency_blocker.py - file blocking):
- Matcher: `Write|Edit`
- Purpose: Block editing dependency files
- Example: Block `Write(file_path="uv.lock")`

**New Hook** (uv_workflow_enforcer.py - command blocking):
- Matcher: `Bash`
- Purpose: Block pip/python/python3 commands
- Example: Block `Bash(command="pip install requests")`

**Both Can Coexist**: Different tools, different purposes, complementary enforcement.

## 17. User Experience

### 17.1 Error Message Design

**Principles**:
- **Clear**: Explain what was blocked and why
- **Specific**: Show exact command that triggered block
- **Educational**: Explain benefits of UV workflow
- **Actionable**: Provide specific UV command alternatives
- **Links**: Point to official UV documentation

**Structure**:
1. Visual indicator (emoji)
2. What was blocked
3. Why it's blocked (5-7 bullet points)
4. UV alternatives (categorized, with examples)
5. Documentation link

### 17.2 Educational Value

**Learning Objectives**:
- Understand UV's environment management
- Learn UV command patterns
- Appreciate benefits of lock files
- Develop muscle memory for UV workflows

## 18. Rollback Strategy

### 18.1 Disabling the Hook

**Option 1**: Comment out in settings.json
```json
{
  "hooks": {
    "PreToolUse": [
      // Commented out UV workflow enforcer
    ]
  }
}
```

**Option 2**: Use settings.local.json override
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete hook script
```bash
rm .claude/hooks/pre_tools/uv_workflow_enforcer.py
```

## 19. Future Enhancements

### 19.1 Smart Command Translation

**Feature**: Auto-suggest exact UV equivalent

```python
# Detect: pip install requests numpy
# Suggest: uv add requests numpy

# Detect: python -m pytest tests/
# Suggest: uv run -m pytest tests/
```

### 19.2 Interactive Mode

**Feature**: Use `permissionDecision: "ask"` for learning phase

```python
# Allow user to:
# - See blocked command
# - See UV alternative
# - Choose to allow anyway (with explanation)
# - Choose to always allow similar (add exception)
```

### 19.3 Analytics & Reporting

**Feature**: Track blocked commands for insights

```python
# Generate reports:
# - Most commonly blocked commands
# - Conversion progress (fewer blocks over time)
# - Team adoption metrics
```

## 20. Success Criteria

### 20.1 Functional Requirements

- ✅ Blocks pip/python/python3 commands in Bash
- ✅ Allows UV-managed commands (uv run python, uv pip, etc.)
- ✅ Provides specific UV alternatives for each command type
- ✅ Handles complex command structures (chains, pipes)
- ✅ Uses shared utilities from pre_tools/utils
- ✅ Fail-safe behavior on errors

### 20.2 Non-Functional Requirements

- ✅ Execution time < 50ms
- ✅ Test coverage ≥ 95%
- ✅ Zero external dependencies
- ✅ Clear, educational error messages
- ✅ No disruption to UV-based workflows

### 20.3 Integration Requirements

- ✅ Registered in .claude/settings.json
- ✅ Works alongside other PreToolUse hooks
- ✅ Compatible with universal_hook_logger.py
- ✅ No conflicts with existing infrastructure

## 21. Implementation Plan

### Phase 1: Core Implementation

1. Create UV script with metadata
2. Implement command parsing logic
3. Implement pattern detection (allow-list and block-list)
4. Create command-type-specific error messages
5. Integrate with shared utilities
6. Add comprehensive docstrings

### Phase 2: Configuration

1. Update .claude/settings.json with Bash matcher
2. Remove old Write|Edit file-blocking configuration (if replacing)
3. Set appropriate timeout (60 seconds)
4. Test hook registration

### Phase 3: Testing

1. Write unit tests for command detection
2. Write unit tests for command parsing
3. Write unit tests for message generation
4. Write integration tests
5. Achieve ≥95% code coverage

### Phase 4: Documentation

1. Complete inline documentation
2. Write user guide
3. Add examples and troubleshooting
4. Update pre_tools/README.md
5. Document migration from old hook (if applicable)

### Phase 5: Validation

1. Manual testing with real Claude Code sessions
2. Test edge cases (complex commands, escaping, etc.)
3. Validate error messages are helpful
4. Performance testing

## 22. Specification Change Log

| Version | Date       | Changes                                      | Author                   |
|---------|------------|----------------------------------------------|--------------------------|
| 2.0.0   | 2025-10-30 | Complete redesign for command-level enforcement | Claude Code Hook Expert  |

---

**Specification Status**: ✅ Ready for Implementation

**Next Steps**:
1. Review specification with stakeholders
2. Proceed to build phase using `/experts:cc_hook_expert:cc_hook_expert_build`
3. Implement comprehensive test suite
4. Deploy and validate in real-world usage

**Related Documents**:
- `.claude/hooks/pre_tools/utils/data_types.py` - Shared type definitions
- `.claude/hooks/pre_tools/utils/utils.py` - Shared utility functions
- `ai_docs/claude-code-hooks.md` - Claude Code hooks reference
- `ai_docs/uv-scripts-guide.md` - UV script execution guide
- [UV CLI Documentation](https://docs.astral.sh/uv/)
- [UV Scripts Guide](https://docs.astral.sh/uv/guides/scripts/)
- [UV Dependencies Guide](https://docs.astral.sh/uv/concepts/dependencies/)
