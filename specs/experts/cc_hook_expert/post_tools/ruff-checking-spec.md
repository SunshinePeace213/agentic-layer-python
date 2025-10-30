# Ruff Checking Hook Specification

## Overview

**Feature Name:** Ruff Checking Hook
**Location:** `.claude/hooks/post_tools/ruff_checking.py`
**Hook Event:** PostToolUse
**Version:** 1.0.0
**Author:** Claude Code Hook Expert
**Created:** 2025-10-31

## Purpose

Automatically format and check Python files after Write, Edit, or NotebookEdit operations using Ruff, providing immediate feedback to Claude about code style issues and lint violations. This hook ensures consistent code formatting and adherence to Python best practices across the codebase.

## Problem Statement

### Current Challenges

1. **Manual Formatting**: Developers must manually run `ruff format` after writing code
2. **Lint Violations**: Code may contain fixable lint violations that go unnoticed
3. **Inconsistent Style**: Without automatic formatting, code style varies across files
4. **Delayed Feedback**: Claude doesn't receive immediate feedback about formatting/linting issues
5. **Context Switching**: Developers must remember to run formatting tools separately

### Impact

- Inconsistent code style across the codebase
- Accumulation of fixable lint violations
- Additional manual steps required in development workflow
- Claude may continue with poorly formatted code
- PR reviews spend time on formatting instead of logic

## Objectives

### Primary Goals

1. **Automatic Formatting**: Run `ruff format` on all Python files after Write/Edit operations
2. **Automatic Linting**: Run `ruff check --fix` to auto-fix lint violations
3. **Immediate Feedback**: Provide Claude with clear feedback about formatting/linting results
4. **Non-Blocking**: Inform Claude without blocking workflow (formatting is enhancement, not requirement)
5. **Security**: Validate file paths and prevent processing files outside project directory

### Success Criteria

- All Python files are automatically formatted after Write/Edit operations
- Auto-fixable lint violations are resolved automatically
- Claude receives concise feedback about formatting/linting changes
- Hook executes quickly (< 5 seconds for typical files)
- Zero false positives or unnecessary noise in feedback
- Full integration with existing post_tools utils infrastructure

## Architecture Design

### Hook Event Selection

**Event:** PostToolUse
**Rationale:**
- Formatting should happen AFTER file is written/edited
- Need access to the actual file on disk to run ruff
- PostToolUse provides tool_response with success status
- Can validate that Write/Edit succeeded before formatting

**Tool Matchers:**
- `Write`: Triggers when new files are created
- `Edit`: Triggers when existing files are modified
- `NotebookEdit`: Triggers when notebook cells are edited (Python code cells)

### File Structure

```
.claude/hooks/post_tools/
│   └── ruff_checking.py       # Ruff formatting and linting hook
└── utils/
    ├── __init__.py            # Shared utilities (already exists)
    ├── data_types.py          # Type definitions (already exists)
    └── utils.py               # Utility functions (already exists)
```

### Dependencies

**Python Packages (via UV inline metadata):**
```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruff>=0.8.0",
# ]
# ///
```

**Rationale:**
- `ruff>=0.8.0`: Modern version with stable JSON output and formatting features
- No additional dependencies needed (uses stdlib + ruff)

### Input Schema

**Hook Input Structure (PostToolUse):**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/root/src/example.py",
    "content": "def foo():\n  return 42\n"
  },
  "tool_response": {
    "filePath": "/project/root/src/example.py",
    "success": true
  }
}
```

**Relevant Fields:**
- `tool_name`: Filter for Write/Edit/NotebookEdit
- `tool_input.file_path`: File to format/check
- `tool_response.success`: Only process if tool succeeded

### Output Schema

**Non-Blocking Feedback (default):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Ruff: Formatted + fixed 3 lint issues in example.py"
  },
  "suppressOutput": true
}
```

**No Changes Made:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ""
  },
  "suppressOutput": true
}
```

**Error Handling (non-blocking):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "⚠️ Ruff check found 2 issues in example.py (run: ruff check example.py)"
  },
  "suppressOutput": false
}
```

### Decision Logic Flow

```
1. Parse hook input
   ├─ Success → Continue
   └─ Failure → Exit silently (exit 0)

2. Extract tool_name and file_path
   ├─ tool_name not in [Write, Edit, NotebookEdit] → Exit silently
   └─ Continue

3. Validate file_path
   ├─ Not a Python file (.py, .pyi) → Exit silently
   ├─ Outside project directory → Exit silently
   └─ Continue

4. Check tool_response.success
   ├─ False → Exit silently (tool failed, skip formatting)
   └─ Continue

5. Verify file exists on disk
   ├─ File not found → Exit silently
   └─ Continue

6. Run ruff format
   ├─ Success → Track formatting result
   └─ Error → Log warning, continue to check

7. Run ruff check --fix --output-format=json
   ├─ Success → Track linting result
   └─ Error → Log warning

8. Generate feedback message
   ├─ Changes made → Output feedback with summary
   └─ No changes → Exit silently

9. Exit 0 (non-blocking)
```

## Implementation Details

### Core Functions

#### `main()` - Entry Point
```python
def main() -> None:
    """Main entry point for ruff checking hook."""
    # 1. Parse input
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # 2. Validate tool and file
    if not should_process(tool_name, tool_input, tool_response):
        output_feedback("", suppress_output=True)
        return

    file_path = get_file_path(tool_input)

    # 3. Run ruff format and check
    format_result = run_ruff_format(file_path)
    check_result = run_ruff_check(file_path)

    # 4. Generate feedback
    feedback = generate_feedback(file_path, format_result, check_result)
    output_feedback(feedback, suppress_output=True)
```

#### `should_process()` - Validation
```python
def should_process(
    tool_name: str,
    tool_input: ToolInput,
    tool_response: dict[str, object]
) -> bool:
    """Determine if file should be processed.

    Returns:
        True if file should be formatted/checked, False otherwise
    """
    # Check tool name
    if tool_name not in ["Write", "Edit", "NotebookEdit"]:
        return False

    # Check tool success
    if not was_tool_successful(tool_response):
        return False

    # Get and validate file path
    file_path = get_file_path(tool_input)
    if not file_path:
        return False

    # Check if Python file
    if not is_python_file(file_path):
        return False

    # Check if within project
    if not is_within_project(file_path):
        return False

    # Check if file exists
    if not Path(file_path).exists():
        return False

    return True
```

#### `run_ruff_format()` - Format File
```python
def run_ruff_format(file_path: str) -> dict[str, object]:
    """Run ruff format on file.

    Args:
        file_path: Absolute path to Python file

    Returns:
        Result dict with:
        - success: bool
        - formatted: bool (True if file was reformatted)
        - error: Optional[str]
    """
    try:
        # Run ruff format --check first to see if formatting needed
        check_result = subprocess.run(
            ["ruff", "format", "--check", file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        needs_formatting = check_result.returncode != 0

        if needs_formatting:
            # Actually format the file
            format_result = subprocess.run(
                ["ruff", "format", file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "success": format_result.returncode == 0,
                "formatted": True,
                "error": format_result.stderr if format_result.returncode != 0 else None
            }

        return {
            "success": True,
            "formatted": False,
            "error": None
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "formatted": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "formatted": False, "error": str(e)}
```

#### `run_ruff_check()` - Check and Fix Linting
```python
def run_ruff_check(file_path: str) -> dict[str, object]:
    """Run ruff check --fix on file.

    Args:
        file_path: Absolute path to Python file

    Returns:
        Result dict with:
        - success: bool
        - fixed_count: int (number of auto-fixed violations)
        - remaining_count: int (number of unfixed violations)
        - error: Optional[str]
    """
    try:
        # Run ruff check --fix --output-format=json
        result = subprocess.run(
            ["ruff", "check", "--fix", "--output-format=json", file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Parse JSON output
        if result.stdout:
            violations = json.loads(result.stdout)

            # Count fixed vs remaining violations
            fixed = sum(1 for v in violations if v.get("fix"))
            remaining = len(violations) - fixed

            return {
                "success": True,
                "fixed_count": fixed,
                "remaining_count": remaining,
                "error": None
            }

        # No violations found
        return {
            "success": True,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": None
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "fixed_count": 0, "remaining_count": 0, "error": "Timeout"}
    except json.JSONDecodeError:
        return {"success": False, "fixed_count": 0, "remaining_count": 0, "error": "Invalid JSON"}
    except Exception as e:
        return {"success": False, "fixed_count": 0, "remaining_count": 0, "error": str(e)}
```

#### `generate_feedback()` - Create Feedback Message
```python
def generate_feedback(
    file_path: str,
    format_result: dict[str, object],
    check_result: dict[str, object]
) -> str:
    """Generate human-readable feedback message.

    Args:
        file_path: File that was processed
        format_result: Result from run_ruff_format()
        check_result: Result from run_ruff_check()

    Returns:
        Feedback message for Claude (empty if no changes)
    """
    file_name = Path(file_path).name
    messages = []

    # Check for errors
    if not format_result.get("success"):
        error = format_result.get("error", "Unknown error")
        messages.append(f"⚠️ Ruff format error in {file_name}: {error}")

    if not check_result.get("success"):
        error = check_result.get("error", "Unknown error")
        messages.append(f"⚠️ Ruff check error in {file_name}: {error}")

    # Report changes
    formatted = format_result.get("formatted", False)
    fixed_count = check_result.get("fixed_count", 0)
    remaining_count = check_result.get("remaining_count", 0)

    if formatted or fixed_count > 0:
        parts = []
        if formatted:
            parts.append("formatted")
        if fixed_count > 0:
            parts.append(f"fixed {fixed_count} lint issue{'s' if fixed_count != 1 else ''}")

        messages.append(f"✅ Ruff: {' + '.join(parts)} in {file_name}")

    # Warn about remaining issues
    if remaining_count > 0:
        messages.append(
            f"⚠️ Ruff: {remaining_count} remaining issue{'s' if remaining_count != 1 else ''} "
            f"in {file_name} (run: ruff check {file_path})"
        )

    return " | ".join(messages) if messages else ""
```

### Security Validation

#### Path Traversal Prevention
```python
# Use is_within_project() from shared utils
if not is_within_project(file_path):
    output_feedback("", suppress_output=True)
    return
```

#### File Type Validation
```python
# Use is_python_file() from shared utils
if not is_python_file(file_path):
    output_feedback("", suppress_output=True)
    return
```

#### Subprocess Safety
```python
# Always use list form for subprocess (never shell=True)
subprocess.run(
    ["ruff", "format", file_path],  # List form (safe)
    capture_output=True,
    text=True,
    timeout=10,  # Prevent hanging
    shell=False  # Explicit (default, but be clear)
)
```

### Error Handling Strategy

#### Non-Blocking Errors
- All errors are non-blocking (exit 0)
- Format errors don't prevent linting checks
- Lint errors don't block Claude's workflow
- Timeout errors are logged but don't halt execution

#### Error Logging
```python
try:
    # ... operation ...
except Exception as e:
    # Log to stderr for debugging, but don't block
    print(f"Ruff hook error: {e}", file=sys.stderr)
    output_feedback("", suppress_output=True)
```

### Performance Considerations

**Timeouts:**
- `ruff format`: 10 second timeout
- `ruff check`: 10 second timeout
- Total max execution: ~20 seconds

**Optimization Strategies:**
- Skip non-Python files immediately
- Skip files outside project directory
- Use `--check` before actual formatting to avoid unnecessary writes
- Use JSON output for structured parsing (faster than text parsing)

## Configuration Integration

### Settings.json Entry

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/ruff_checking.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Configuration Notes:**
- `matcher`: Targets Write, Edit, and NotebookEdit tools
- `timeout`: 30 seconds (generous for large files)
- `command`: Uses $CLAUDE_PROJECT_DIR for portability

### Local Override Support

Users can disable in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": []
  }
}
```

## Testing Strategy

### Unit Tests Location
`tests/claude_hook/post_tools/test_ruff_checking.py`

### Test Categories

#### 1. Input Validation Tests
```python
def test_should_process_valid_python_file():
    """Test that valid Python files are processed."""

def test_should_skip_non_python_files():
    """Test that non-Python files are skipped."""

def test_should_skip_files_outside_project():
    """Test that files outside project are skipped."""

def test_should_skip_when_tool_failed():
    """Test that files are skipped when tool_response.success=False."""
```

#### 2. Formatting Tests
```python
def test_run_ruff_format_on_unformatted_file():
    """Test formatting of unformatted Python file."""

def test_run_ruff_format_on_already_formatted_file():
    """Test that already-formatted files are not changed."""

def test_run_ruff_format_handles_syntax_errors():
    """Test error handling for files with syntax errors."""
```

#### 3. Linting Tests
```python
def test_run_ruff_check_fixes_violations():
    """Test auto-fixing of lint violations."""

def test_run_ruff_check_reports_remaining_violations():
    """Test reporting of unfixable violations."""

def test_run_ruff_check_handles_no_violations():
    """Test files with no violations."""
```

#### 4. Feedback Generation Tests
```python
def test_generate_feedback_format_only():
    """Test feedback when only formatting is applied."""

def test_generate_feedback_fix_only():
    """Test feedback when only lint fixes are applied."""

def test_generate_feedback_format_and_fix():
    """Test feedback when both formatting and fixes are applied."""

def test_generate_feedback_no_changes():
    """Test that empty feedback is returned when no changes made."""

def test_generate_feedback_with_remaining_violations():
    """Test feedback includes warning about remaining violations."""
```

#### 5. Integration Tests
```python
def test_full_workflow_write_tool():
    """Test complete workflow for Write tool."""

def test_full_workflow_edit_tool():
    """Test complete workflow for Edit tool."""

def test_full_workflow_notebookedit_tool():
    """Test complete workflow for NotebookEdit tool."""
```

#### 6. Error Handling Tests
```python
def test_handles_ruff_format_timeout():
    """Test timeout handling for ruff format."""

def test_handles_ruff_check_timeout():
    """Test timeout handling for ruff check."""

def test_handles_invalid_json_output():
    """Test handling of malformed JSON from ruff."""

def test_handles_missing_ruff_binary():
    """Test error handling when ruff is not installed."""
```

### Test Execution

Run tests with:
```bash
uv run pytest -n auto tests/claude_hook/post_tools/test_ruff_checking.py
```

**Test Coverage Target:** ≥90% code coverage

## Ruff Best Practices Integration

### Configuration File Detection

Ruff automatically detects configuration from:
- `ruff.toml` (recommended)
- `pyproject.toml` (recommended)
- `.ruff.toml`

**Hook Behavior:**
- Hook uses project's existing Ruff configuration
- No need to pass config explicitly
- Respects project-specific rules and exclusions

### Recommended Ruff Configuration

**Example `ruff.toml` section:**
```toml
line-length = 88
target-version = "py311"

[lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]

[format]
quote-style = "double"
indent-style = "space"
```

### Additional Features to Consider (Future Enhancements)

1. **Unsafe Fixes**: Currently not enabled; could add flag for `--unsafe-fixes`
2. **Show Fixes**: Could capture and display specific fixes made
3. **Custom Output**: Could format output differently for different severity levels
4. **Diff Display**: Could show diffs of changes made
5. **Selective Rules**: Could allow per-file rule selection

## Rollback Strategy

### Disabling the Hook

**Temporary Disable (local override):**
```json
// .claude/settings.local.json
{
  "hooks": {
    "PostToolUse": []
  }
}
```

**Permanent Disable (remove from settings.json):**
Remove the ruff_checking hook entry from PostToolUse hooks array.

### Reverting Formatting Changes

If ruff introduces unwanted formatting:

1. **Git Revert:**
   ```bash
   git checkout HEAD -- <file_path>
   ```

2. **Adjust Ruff Config:**
   Update `ruff.toml` with desired formatting rules

3. **Disable Formatting Only:**
   Modify hook to skip `run_ruff_format()` and only run linting

## Migration Path

### Phase 1: Soft Launch (Feedback Only)
- Deploy hook with `suppressOutput: true`
- Monitor stderr logs for errors
- Verify formatting/linting works correctly

### Phase 2: Full Deployment
- Change to `suppressOutput: false` for important feedback
- Add to project documentation
- Train team on interpreting feedback

### Phase 3: Optimization
- Tune timeout values based on real usage
- Adjust feedback verbosity
- Add additional ruff features as needed

## Success Metrics

### Quantitative Metrics
- **Execution Time**: Average < 2 seconds per file
- **Error Rate**: < 1% of executions result in errors
- **Coverage**: 100% of Python Write/Edit operations trigger hook
- **Test Coverage**: ≥90% code coverage

### Qualitative Metrics
- **Code Consistency**: All new/edited Python files follow consistent style
- **Developer Satisfaction**: Developers appreciate automatic formatting
- **Feedback Quality**: Claude receives actionable, concise feedback
- **Maintenance Burden**: Minimal ongoing maintenance required

## Future Enhancements

### Potential Additions
1. **Configurable Strictness**: Allow per-project strictness levels
2. **Diff Display**: Show actual changes made by ruff
3. **Statistics Tracking**: Track formatting/linting stats over time
4. **Integration with Other Tools**: Coordinate with basedpyright, vulture hooks
5. **Selective Formatting**: Format only changed regions (not entire file)
6. **Pre-commit Integration**: Coordinate with git pre-commit hooks

### Experimental Features
1. **AI-Powered Suggestions**: Use Claude to suggest rule adjustments
2. **Auto-Configuration**: Automatically generate ruff config from codebase analysis
3. **Performance Profiling**: Detailed timing metrics for optimization

## References

### Documentation
- [Ruff Official Docs](https://docs.astral.sh/ruff/)
- [Ruff Format Guide](https://docs.astral.sh/ruff/formatter/)
- [Ruff Linter Rules](https://docs.astral.sh/ruff/rules/)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Claude Code Hooks Reference](../../../ai_docs/claude-code-hooks.md)

### Related Specifications
- [PostToolUse Shared Utils Spec](./shared-utils-spec.md)
- [PreToolUse Hooks Specs](../pre_tools/)

### Code Examples
- [Universal Hook Logger](../../../.claude/hooks/universal_hook_logger.py)
- [PreToolUse Hooks](../../../.claude/hooks/pre_tools/)

## Appendix

### Example Hook Execution

**Input:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/root/src/example.py",
    "content": "def foo( ):\n  return  42\n"
  },
  "tool_response": {
    "filePath": "/project/root/src/example.py",
    "success": true
  }
}
```

**Processing:**
1. Parse input → Success
2. Validate tool_name → "Write" (valid)
3. Validate file_path → `.py` extension (valid)
4. Check tool_response.success → true (valid)
5. Run `ruff format example.py` → Formatted (fixed spacing)
6. Run `ruff check --fix example.py` → Fixed 1 violation (extra spaces)

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Ruff: formatted + fixed 1 lint issue in example.py"
  },
  "suppressOutput": true
}
```

### Verbose Logging Mode

For debugging, add verbose logging:

```python
import os

DEBUG = os.environ.get("RUFF_HOOK_DEBUG", "").lower() == "true"

def log_debug(message: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)
```

Enable with:
```bash
export RUFF_HOOK_DEBUG=true
```

---

**End of Specification**
