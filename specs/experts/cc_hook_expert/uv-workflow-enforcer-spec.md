# UV Workflow Enforcer Hook Specification

**Version:** 1.0.0
**Hook Type:** PreToolUse
**Target Tools:** Bash
**Created:** 2025-10-28
**Status:** Ready for Implementation

---

## 1. Purpose and Objectives

### Primary Purpose
Enforce uv-based Python workflow to ensure consistent, high-performance package management and script execution across Claude Code operations.

### Objectives
1. **Block Direct Python Execution**: Prevent `python` or `python3` commands from running scripts directly
2. **Block pip Package Installation**: Prevent `pip install` commands in favor of `uv add`
3. **Provide Clear Guidance**: Offer actionable alternatives using uv commands
4. **Maintain Developer Experience**: Use non-intrusive messaging and fail-safe behavior

### Benefits
- **Performance**: uv provides significantly faster dependency resolution and installation
- **Consistency**: All project dependencies managed through unified pyproject.toml
- **Environment Management**: Automatic virtual environment handling by uv
- **Lock Files**: Built-in dependency locking for reproducibility

---

## 2. Event Selection and Hook Architecture

### Event Type
**PreToolUse** - Intercepts tool execution before processing

### Tool Matcher
```json
{
  "matcher": "Bash"
}
```

### Rationale
- Only Bash commands can execute `python`, `python3`, or `pip` commands
- PreToolUse allows blocking before execution (prevents wasted computation)
- Other tools (Write, Edit, Read) don't need monitoring for this use case

### Hook Configuration Entry
```json
{
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
```

---

## 3. Input Schema

### Hook Input Structure
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "python script.py --arg value"
  }
}
```

### Relevant Fields
- **tool_name**: Must be "Bash" for processing
- **tool_input.command**: The bash command string to validate

---

## 4. Output Schema

### JSON Output Format
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Detailed explanation with alternatives"
  },
  "suppressOutput": true
}
```

### Permission Decisions
- **"allow"**: Command follows uv workflow or doesn't match patterns
- **"deny"**: Command violates uv workflow (python/python3/pip detected)
- **"ask"**: Not used in this hook (binary allow/deny decision)

### Decision Logic
1. Command uses `python` or `python3` to run scripts → **deny**
2. Command uses `pip install` → **deny**
3. Command uses acceptable patterns (uv run, python -c, etc.) → **allow**
4. Command doesn't match any patterns → **allow**

---

## 5. Detection Patterns

### Pattern Categories

#### 5.1 Direct Python Script Execution
**Pattern**: `python <script>.py` or `python3 <script>.py`

**Examples to Block**:
```bash
python script.py
python3 main.py --arg value
python ./path/to/script.py
python3 -u script.py
/usr/bin/python script.py
/usr/bin/python3 script.py
```

**Examples to Allow**:
```bash
uv run script.py
uv run python script.py  # uv-managed execution
python -c "print('hello')"  # One-liner (acceptable)
python -m module  # Module execution (acceptable for some cases)
which python  # Shell query (not execution)
echo "python"  # String literal (not execution)
```

**Detection Regex**:
```python
PYTHON_SCRIPT_PATTERN = re.compile(
    r'\b(?:python3?|/usr/bin/python3?)\s+(?!-[cm]\s)(?!-$)[\w\./\-]+\.py\b',
    re.IGNORECASE
)
```

**Alternative Suggestion**:
```
Use: uv run <script>.py [args]
Instead of: python <script>.py [args]
```

#### 5.2 pip Package Installation
**Pattern**: `pip install <package>`

**Examples to Block**:
```bash
pip install requests
pip install -r requirements.txt
pip3 install numpy
pip install --upgrade package
python -m pip install package
```

**Examples to Allow**:
```bash
uv add requests
uv add "requests>=2.28.0"
uv add --dev pytest
echo "pip install"  # String literal
which pip  # Shell query
```

**Detection Regex**:
```python
PIP_INSTALL_PATTERN = re.compile(
    r'\b(?:pip3?|python3?\s+-m\s+pip)\s+install\b',
    re.IGNORECASE
)
```

**Alternative Suggestions**:
- For single package: `uv add <package>`
- For requirements file: `uv add -r requirements.txt` (if supported) or manual conversion
- For dev dependencies: `uv add --dev <package>`

---

## 6. Validation Rules

### Rule 1: Block Direct Python Script Execution
```python
def detect_python_script_execution(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect direct python/python3 script execution.

    Returns:
        Tuple of (violation_type, message) if detected, None otherwise
    """
    if PYTHON_SCRIPT_PATTERN.search(command):
        return (
            "direct_python_execution",
            """🐍 UV Workflow Required: Direct python execution blocked

Use uv for better performance and dependency management.

Your command: {command}

Recommended alternative:
  uv run <script>.py [args]

Why use uv run:
  - Automatically manages virtual environments
  - Respects inline script dependencies (PEP 723)
  - Faster execution with optimized caching
  - Consistent environment across all executions

Examples:
  uv run script.py --arg value
  uv run --no-project script.py  # Skip project deps
  uv run --with requests script.py  # Add runtime dep

Note: python -c and python -m are still allowed for quick commands."""
        )
    return None
```

### Rule 2: Block pip install Commands
```python
def detect_pip_install(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect pip install commands.

    Returns:
        Tuple of (violation_type, message) if detected, None otherwise
    """
    if PIP_INSTALL_PATTERN.search(command):
        return (
            "pip_install_blocked",
            """📦 UV Package Management Required: pip install blocked

Use uv for better performance and consistent dependency tracking.

Your command: {command}

Recommended alternatives:
  uv add <package>              # Add production dependency
  uv add --dev <package>        # Add development dependency
  uv add "package>=1.0,<2.0"    # With version constraints

Why use uv add:
  - 10-100x faster than pip install
  - Automatically updates pyproject.toml
  - Creates/updates uv.lock for reproducibility
  - Better dependency resolution
  - Unified project management

For requirements.txt migration:
  1. Review requirements.txt
  2. Use: uv add <package1> <package2> <package3>
  3. Or manually add to pyproject.toml dependencies"""
        )
    return None
```

### Rule 3: Edge Case Handling
```python
def should_allow_command(command: str) -> bool:
    """
    Check if command should be allowed despite containing 'python' keyword.

    Allowed patterns:
    - python -c "code"  # One-liner
    - python -m module  # Module execution (context-dependent)
    - which python      # Shell queries
    - echo "python"     # String literals
    - type python       # Shell introspection
    """
    # Check for one-liners
    if re.search(r'\bpython3?\s+-c\s+', command):
        return True

    # Check for shell queries
    if re.search(r'\b(which|type|command\s+-v)\s+python3?\b', command):
        return True

    # Check for echo/printf (not execution)
    if re.search(r'\b(echo|printf)\s+.*python', command):
        return True

    return False
```

---

## 7. Security Considerations

### Input Sanitization
- **No shell injection risk**: Hook only analyzes commands, doesn't execute them
- **Safe regex patterns**: All patterns escape special characters appropriately
- **No arbitrary code execution**: Pure pattern matching and string analysis

### Path Handling
- **No file system access**: Hook doesn't read/write files
- **No path traversal**: Only analyzes command strings

### Error Handling
- **Fail-safe behavior**: On error, allow command to proceed (exit 0)
- **Clear error messages**: Stderr output for debugging
- **Non-blocking errors**: Hook errors don't break Claude operations

### Privacy
- **No data collection**: Hook doesn't log or transmit commands
- **Local execution**: All validation happens locally
- **No external dependencies**: Standard library only

---

## 8. Dependencies and Requirements

### Python Version
- **Minimum**: Python 3.12 (for modern typing features)

### UV Script Metadata
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

### External Dependencies
- **None**: Uses Python standard library only
- **Internal**: Shared utilities from `.claude/hooks/pre_tools/utils/`

### Shared Utilities
```python
from utils import parse_hook_input, output_decision
```

---

## 9. Error Handling Strategy

### Error Categories

#### 9.1 Input Parsing Errors
```python
try:
    parsed = parse_hook_input()
    if not parsed:
        output_decision("allow", "Failed to parse input (fail-safe)")
        return
except json.JSONDecodeError as e:
    output_decision("allow", f"JSON decode error (fail-safe): {e}")
    return
```

#### 9.2 Pattern Matching Errors
```python
try:
    violation = validate_command(command)
except re.error as e:
    output_decision("allow", f"Regex error (fail-safe): {e}")
    return
```

#### 9.3 General Exceptions
```python
except Exception as e:
    print(f"UV workflow enforcer error: {e}", file=sys.stderr)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Fail-Safe Principle
**Always allow on error** - Never block operations due to hook failures. Better to miss enforcement than break user workflow.

---

## 10. Testing Strategy (TDD Approach)

### Test Categories

#### 10.1 Pattern Detection Tests
```python
class TestPythonScriptDetection:
    """Test detection of direct python script execution."""

    def test_detects_python_script_execution()
    def test_detects_python3_script_execution()
    def test_allows_python_oneliner()
    def test_allows_python_module_execution()
    def test_allows_which_python()
    def test_allows_echo_python()
    def test_allows_uv_run_python()
    def test_detects_absolute_path_python()
```

#### 10.2 pip Install Detection Tests
```python
class TestPipInstallDetection:
    """Test detection of pip install commands."""

    def test_detects_pip_install()
    def test_detects_pip3_install()
    def test_detects_python_m_pip_install()
    def test_detects_pip_install_with_flags()
    def test_allows_which_pip()
    def test_allows_echo_pip()
    def test_allows_uv_add()
```

#### 10.3 Integration Tests
```python
class TestHookIntegration:
    """Test full hook execution with various commands."""

    def test_hook_blocks_python_script()
    def test_hook_blocks_pip_install()
    def test_hook_allows_uv_run()
    def test_hook_allows_uv_add()
    def test_hook_allows_safe_python_commands()
    def test_hook_provides_alternatives_in_message()
```

#### 10.4 Edge Case Tests
```python
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_command()
    def test_handles_invalid_json()
    def test_handles_missing_tool_input()
    def test_handles_non_bash_tools()
    def test_handles_complex_multiline_commands()
    def test_handles_escaped_quotes()
```

#### 10.5 Performance Tests
```python
class TestPerformance:
    """Test performance characteristics."""

    def test_validation_is_fast()  # <10ms per validation
    def test_regex_compilation_cached()
```

### Test Commands
```bash
# Run all tests
uv run pytest .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py -v

# Run with coverage
uv run pytest --cov=.claude/hooks/pre_tools/uv_workflow_enforcer.py \
    .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py

# Run distributed (parallel)
uv run pytest -n auto .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py

# Run specific test class
uv run pytest .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py::TestPythonScriptDetection -v
```

### Test Coverage Goals
- **Line Coverage**: >95%
- **Branch Coverage**: >90%
- **Edge Cases**: All identified edge cases covered

---

## 11. Implementation Plan

### Phase 1: Core Structure Setup
1. Create hook file: `.claude/hooks/pre_tools/uv_workflow_enforcer.py`
2. Add UV script metadata header
3. Import shared utilities
4. Implement skeleton `main()` function

### Phase 2: TDD - Write Tests First
1. Create test file: `.claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py`
2. Write test cases for all detection patterns
3. Write integration tests
4. Write edge case tests
5. **Run tests** - They should fail (no implementation yet)

### Phase 3: Implementation
1. Implement `PYTHON_SCRIPT_PATTERN` regex
2. Implement `PIP_INSTALL_PATTERN` regex
3. Implement `detect_python_script_execution()` function
4. Implement `detect_pip_install()` function
5. Implement `should_allow_command()` helper
6. Implement `validate_command()` main validator
7. Complete `main()` function with error handling

### Phase 4: Testing and Refinement
1. **Run tests** - All should pass
2. Run coverage analysis
3. Fix any gaps in test coverage
4. Test manually with sample commands
5. Refine error messages for clarity

### Phase 5: Integration
1. Add hook to `.claude/settings.json`
2. Test in live Claude Code session
3. Verify blocking behavior
4. Verify allow behavior
5. Verify error messages display correctly

### Phase 6: Documentation
1. Add docstrings to all functions
2. Add inline comments for complex regex
3. Update hook module header documentation
4. Create usage examples

---

## 12. Configuration Changes

### settings.json Addition
Add to `.claude/settings.json` in the `"PreToolUse"` array:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
    }
  ]
}
```

### Complete PreToolUse Configuration
```json
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
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
      }
    ]
  },
  {
    "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
    "hooks": [
      {
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py"
      }
    ]
  }
]
```

---

## 13. File Structure

```
.claude/
├── settings.json                           # Updated with new hook config
├── hooks/
│   └── pre_tools/
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── data_types.py
│       │   └── utils.py
│       ├── tests/
│       │   ├── __init__.py
│       │   └── test_uv_workflow_enforcer.py   # NEW: Comprehensive tests
│       ├── uv_workflow_enforcer.py            # NEW: Main hook implementation
│       ├── tmp_creation_blocker.py
│       ├── destructive_command_blocker.py
│       └── ...other hooks

specs/
└── experts/
    └── cc_hook_expert/
        └── uv-workflow-enforcer-spec.md       # This specification
```

---

## 14. Example Scenarios

### Scenario 1: Python Script Execution Blocked
**Input Command:**
```bash
python train_model.py --epochs 10
```

**Hook Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🐍 UV Workflow Required: Direct python execution blocked\n\nUse uv for better performance and dependency management.\n\nYour command: python train_model.py --epochs 10\n\nRecommended alternative:\n  uv run train_model.py --epochs 10\n\n..."
  },
  "suppressOutput": true
}
```

**User Experience:**
Claude receives denial and suggests: "Use `uv run train_model.py --epochs 10` instead"

### Scenario 2: pip install Blocked
**Input Command:**
```bash
pip install requests beautifulsoup4
```

**Hook Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "📦 UV Package Management Required: pip install blocked\n\nUse uv for better performance and consistent dependency tracking.\n\nYour command: pip install requests beautifulsoup4\n\nRecommended alternatives:\n  uv add requests beautifulsoup4\n\n..."
  },
  "suppressOutput": true
}
```

**User Experience:**
Claude receives denial and suggests: "Use `uv add requests beautifulsoup4` instead"

### Scenario 3: uv run Allowed
**Input Command:**
```bash
uv run script.py --arg value
```

**Hook Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Command follows UV workflow"
  }
}
```

**User Experience:**
Command executes normally

### Scenario 4: python -c Allowed (One-liner)
**Input Command:**
```bash
python -c "import sys; print(sys.version)"
```

**Hook Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "One-liner execution allowed"
  }
}
```

**User Experience:**
Command executes normally (edge case handling)

---

## 15. Rollback Strategy

### If Issues Arise

#### Immediate Rollback
1. Remove hook configuration from `.claude/settings.json`
2. Reload Claude Code or start new session
3. Verify normal operation

#### Configuration Removal
```json
// Remove this entry from PreToolUse array:
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py"
    }
  ]
}
```

#### Debugging Steps
1. Check debug logs: `claude --debug`
2. Test hook manually: `echo '{"tool_name":"Bash","tool_input":{"command":"python test.py"}}' | uv run .claude/hooks/pre_tools/uv_workflow_enforcer.py`
3. Verify JSON output format
4. Check for Python errors in stderr

#### File Removal (if needed)
```bash
# Remove hook file
rm .claude/hooks/pre_tools/uv_workflow_enforcer.py

# Remove test file
rm .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py
```

---

## 16. Success Criteria

### Functional Requirements
- ✅ Blocks `python <script>.py` commands
- ✅ Blocks `python3 <script>.py` commands
- ✅ Blocks `pip install` commands
- ✅ Allows `uv run` commands
- ✅ Allows `uv add` commands
- ✅ Allows `python -c` one-liners
- ✅ Provides clear alternative suggestions

### Quality Requirements
- ✅ All tests pass (100% pass rate)
- ✅ Test coverage >95%
- ✅ No false positives (safe commands blocked)
- ✅ No false negatives (violations missed)
- ✅ Error handling prevents Claude disruption

### Performance Requirements
- ✅ Hook execution <10ms per command
- ✅ No noticeable impact on Claude response time
- ✅ Regex patterns compiled and cached

### User Experience Requirements
- ✅ Clear, actionable error messages
- ✅ Helpful alternatives provided
- ✅ Non-intrusive (suppressOutput=true)
- ✅ Fail-safe behavior (allows on error)

---

## 17. Future Enhancements

### Potential Improvements
1. **Configurable Strictness**: Allow opt-in for `python -m` blocking
2. **Auto-suggestion API**: Integration with Claude's tool retry mechanism
3. **Statistical Tracking**: Log enforcement stats for analysis
4. **Project Detection**: Different rules for uv projects vs non-uv projects
5. **Allowlist Support**: User-configurable command exceptions

### Integration Ideas
1. **IDE Integration**: VSCode extension with same rules
2. **Pre-commit Hook**: Git hook version for team consistency
3. **CI/CD Checks**: Validate scripts don't use banned patterns

---

## 18. References

### Related Documentation
- [UV Scripts Guide](ai_docs/uv-scripts-guide.md)
- [Claude Code Hooks Reference](ai_docs/claude-code-hooks.md)
- [PEP 723: Inline Script Metadata](https://peps.python.org/pep-0723/)

### Related Hooks
- `tmp_creation_blocker.py` - Similar pattern detection approach
- `destructive_command_blocker.py` - Bash command validation reference

### Key Technologies
- **UV**: https://docs.astral.sh/uv/
- **Python Regex**: https://docs.python.org/3/library/re.html
- **pytest**: https://docs.pytest.org/

---

## Appendix A: Complete Implementation Skeleton

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Workflow Enforcer - PreToolUse Hook
=======================================
Enforces uv-based Python workflow by blocking direct python/pip usage.

This hook ensures all Python script execution uses 'uv run' and all
package installations use 'uv add' for better performance and consistency.

Blocked Patterns:
- python script.py / python3 script.py
- pip install package / pip3 install package
- python -m pip install package

Allowed Patterns:
- uv run script.py
- uv add package
- python -c "code" (one-liners)
- shell queries (which python, etc.)

Usage:
    This hook is automatically invoked by Claude Code before Bash execution.
    It receives JSON input via stdin and outputs JSON permission decisions.

Dependencies:
    - Python >= 3.12
    - No external packages (standard library only)
    - Shared utilities from .claude/hooks/pre_tools/utils/

Exit Codes:
    0: Success (decision output via stdout)

Author: Claude Code Hook Expert
Version: 1.0.0
"""

import re
import sys
from typing import Optional, Tuple

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Pattern Definitions ============

PYTHON_SCRIPT_PATTERN: re.Pattern[str] = re.compile(
    r'\b(?:python3?|/usr/bin/python3?)\s+(?!-[cm]\s)(?!-$)[\w\./\-]+\.py\b',
    re.IGNORECASE
)

PIP_INSTALL_PATTERN: re.Pattern[str] = re.compile(
    r'\b(?:pip3?|python3?\s+-m\s+pip)\s+install\b',
    re.IGNORECASE
)


# ============ Detection Functions ============

def detect_python_script_execution(command: str) -> Optional[Tuple[str, str]]:
    """Detect direct python/python3 script execution."""
    # Implementation here
    pass


def detect_pip_install(command: str) -> Optional[Tuple[str, str]]:
    """Detect pip install commands."""
    # Implementation here
    pass


def should_allow_command(command: str) -> bool:
    """Check if command should be allowed (edge cases)."""
    # Implementation here
    pass


def validate_command(command: str) -> Optional[Tuple[str, str]]:
    """Validate command against all patterns."""
    # Implementation here
    pass


def main() -> None:
    """Main entry point for UV workflow enforcer hook."""
    # Implementation here
    pass


if __name__ == "__main__":
    main()
```

---

## Appendix B: Complete Test Skeleton

```python
#!/usr/bin/env python3
"""
Comprehensive pytest-based tests for the uv_workflow_enforcer PreToolUse hook.

Test Categories:
1. Python Script Detection Tests
2. pip Install Detection Tests
3. Edge Case Detection Tests
4. Integration Tests
5. Error Handling Tests
6. Performance Tests

Usage:
    uv run pytest .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py -v
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from uv_workflow_enforcer import (
        detect_python_script_execution,
        detect_pip_install,
        should_allow_command,
        validate_command,
        main,
    )
except ImportError:
    pytest.skip("Could not import uv_workflow_enforcer", allow_module_level=True)


class TestPythonScriptDetection:
    """Test detection of direct python script execution."""
    # Tests here
    pass


class TestPipInstallDetection:
    """Test detection of pip install commands."""
    # Tests here
    pass


class TestEdgeCases:
    """Test edge cases and allowed patterns."""
    # Tests here
    pass


class TestHookIntegration:
    """Test full hook execution."""
    # Tests here
    pass


class TestPerformance:
    """Test performance characteristics."""
    # Tests here
    pass
```

---

## Document History

| Version | Date       | Changes                        | Author            |
|---------|------------|--------------------------------|-------------------|
| 1.0.0   | 2025-10-28 | Initial specification created  | Claude Code Expert|

---

**Specification Status: ✅ READY FOR IMPLEMENTATION**
