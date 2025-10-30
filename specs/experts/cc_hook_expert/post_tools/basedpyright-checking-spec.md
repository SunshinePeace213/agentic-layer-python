# Basedpyright Type Checking Hook Specification

## Overview

**Feature Name:** Basedpyright Type Checking Hook
**Location:** `.claude/hooks/post_tools/basedpyright_checking.py`
**Hook Event:** PostToolUse
**Version:** 1.0.0
**Author:** Claude Code Hook Expert
**Created:** 2025-10-31

## Purpose

Automatically enforce complete type safety for all Python files after Write, Edit, or NotebookEdit operations using basedpyright. This hook ensures that NO type errors exist in Python code before Claude continues, maintaining strict type safety standards across the codebase.

## Problem Statement

### Current Challenges

1. **Delayed Type Error Detection**: Type errors discovered late in development cycle
2. **Incomplete Type Coverage**: Code may have implicit `Any` types that hide bugs
3. **Runtime Type Issues**: Type-related bugs only discovered at runtime
4. **Manual Type Checking**: Developers must remember to run basedpyright manually
5. **Inconsistent Type Safety**: Some files pass strict checking, others don't

### Impact

- Type errors slip into codebase undetected
- Runtime failures due to type mismatches
- Reduced code quality and maintainability
- Additional debugging time spent on type-related issues
- Claude may continue writing code with type errors

## Objectives

### Primary Goals

1. **Zero Type Errors**: Block operations that result in any type errors
2. **Complete Type Safety**: Enforce strict type checking with no `Any` types allowed
3. **Immediate Feedback**: Provide Claude with detailed type error information
4. **Blocking Enforcement**: Prevent Claude from continuing until type errors are fixed
5. **Security**: Validate file paths and prevent processing files outside project directory

### Success Criteria

- 100% of Python files pass strict basedpyright type checking
- Zero tolerance for type errors (all errors must be fixed)
- Clear, actionable error messages for type violations
- Hook executes quickly (< 10 seconds for typical files)
- Full integration with existing post_tools utils infrastructure
- Respects pyrightconfig.json settings in project

## Architecture Design

### Hook Event Selection

**Event:** PostToolUse
**Rationale:**
- Type checking should happen AFTER file is written/edited to disk
- Need access to the actual file on disk to run basedpyright
- PostToolUse provides tool_response with success status
- Can validate that Write/Edit succeeded before type checking

**Tool Matchers:**
- `Write`: Triggers when new Python files are created
- `Edit`: Triggers when existing Python files are modified
- `NotebookEdit`: Triggers when notebook cells with Python code are edited

### File Structure

```
.claude/hooks/post_tools/
├── basedpyright_checking.py   # Basedpyright type checking hook
└── utils/
    ├── __init__.py            # Shared utilities (already exists)
    ├── data_types.py          # Type definitions (already exists)
    └── utils.py               # Utility functions (already exists)
```

### Dependencies

**Python Packages (via UV inline metadata):**
```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "basedpyright>=1.31.0",
# ]
# ///
```

**Rationale:**
- `basedpyright>=1.31.0`: Latest stable version with strict type checking features
- Requires Python 3.12+ for modern type hints support
- Uses stdlib subprocess for execution

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
    "content": "def foo(x):\n    return x + 1\n"
  },
  "tool_response": {
    "filePath": "/project/root/src/example.py",
    "success": true
  }
}
```

**Relevant Fields:**
- `tool_name`: Filter for Write/Edit/NotebookEdit
- `tool_input.file_path`: File to type check
- `tool_response.success`: Only process if tool succeeded

### Output Schema

**Successful Type Check (non-blocking):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Type check passed for example.py"
  },
  "suppressOutput": true
}
```

**Type Errors Found (BLOCKING):**
```json
{
  "decision": "block",
  "reason": "❌ Type checking failed: 3 errors found in example.py\n\nError 1 (line 5): Expression of type \"str\" is not assignable to declared type \"int\"\nError 2 (line 8): Argument type \"Any\" is not assignable to parameter \"value\" of type \"int\"\nError 3 (line 12): \"foo\" is not a known attribute of \"None\"\n\nPlease fix all type errors before continuing.\nRun: basedpyright example.py",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Type errors must be resolved"
  },
  "suppressOutput": false
}
```

**Skipped (non-Python file or outside project):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ""
  },
  "suppressOutput": true
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
   ├─ False → Exit silently (tool failed, skip type checking)
   └─ Continue

5. Verify file exists on disk
   ├─ File not found → Exit silently
   └─ Continue

6. Run basedpyright on file
   ├─ Success (exit code 0) → Output success feedback (non-blocking)
   ├─ Type errors found (exit code 1) → BLOCK with detailed errors
   └─ Other error → Log warning, exit silently (fail-safe)

7. Exit 0 (always exit 0, blocking handled via JSON decision field)
```

## Implementation Details

### Core Functions

#### `main()` - Entry Point
```python
def main() -> None:
    """Main entry point for basedpyright type checking hook.

    Process:
        1. Parse input from stdin
        2. Validate tool, file, and operation
        3. Run basedpyright type checker
        4. Block if type errors found, or allow if clean
    """
    try:
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

        # 3. Run basedpyright type checking
        check_result = run_basedpyright_check(file_path)

        # 4. Output decision based on type checking result
        if check_result["has_errors"]:
            # Type errors found - BLOCK
            output_block(
                reason=format_error_message(file_path, check_result),
                additional_context="Type errors must be resolved",
                suppress_output=False
            )
        else:
            # Type check passed - Allow
            file_name = Path(file_path).name
            output_feedback(
                f"✅ Type check passed for {file_name}",
                suppress_output=True
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Basedpyright hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
```

#### `should_process()` - Validation
```python
def should_process(
    tool_name: str,
    tool_input: ToolInput,
    tool_response: dict[str, object]
) -> bool:
    """Determine if file should be type checked.

    Args:
        tool_name: Name of the Claude Code tool that was executed
        tool_input: Tool input parameters
        tool_response: Tool execution response

    Returns:
        True if file should be type checked, False otherwise

    Validation Steps:
        1. Check tool name is Write/Edit/NotebookEdit
        2. Verify tool operation succeeded
        3. Validate file path exists and is valid
        4. Check file is Python (.py, .pyi)
        5. Verify file is within project directory
        6. Ensure file exists on disk
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

#### `run_basedpyright_check()` - Type Check File
```python
def run_basedpyright_check(file_path: str) -> dict[str, object]:
    """Run basedpyright type checker on file.

    Args:
        file_path: Absolute path to Python file to type check

    Returns:
        Result dict with:
        - has_errors: bool (True if type errors found)
        - error_count: int (number of errors found)
        - errors: list[dict] (structured error information)
        - output: str (raw basedpyright output)
        - error: Optional[str] (error message if execution failed)

    Implementation:
        - Runs: basedpyright --outputjson <file_path>
        - Parses JSON output for structured error information
        - Timeout: 10 seconds for typical files
        - Uses project's pyrightconfig.json settings
    """
    try:
        # Run basedpyright with JSON output for structured parsing
        result = subprocess.run(
            ["basedpyright", "--outputjson", file_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=get_project_dir()
        )

        # Parse JSON output
        if result.stdout:
            try:
                output_data = json.loads(result.stdout)

                # Extract diagnostics
                diagnostics = output_data.get("generalDiagnostics", [])

                # Filter only errors (not warnings or information)
                errors = [
                    d for d in diagnostics
                    if d.get("severity") == "error"
                ]

                return {
                    "has_errors": len(errors) > 0,
                    "error_count": len(errors),
                    "errors": errors,
                    "output": result.stdout,
                    "error": None
                }
            except json.JSONDecodeError:
                # Fallback to text parsing if JSON fails
                has_errors = result.returncode != 0
                return {
                    "has_errors": has_errors,
                    "error_count": -1,  # Unknown
                    "errors": [],
                    "output": result.stderr or result.stdout,
                    "error": "Failed to parse JSON output"
                }

        # No output - assume success
        return {
            "has_errors": False,
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": None
        }

    except subprocess.TimeoutExpired:
        return {
            "has_errors": False,  # Fail-safe: don't block on timeout
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": "Type check timeout (file may be too large)"
        }
    except FileNotFoundError:
        return {
            "has_errors": False,  # Fail-safe: don't block if basedpyright missing
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": "basedpyright not found in PATH"
        }
    except Exception as e:
        return {
            "has_errors": False,  # Fail-safe: don't block on unexpected error
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": str(e)
        }
```

#### `format_error_message()` - Create Blocking Message
```python
def format_error_message(file_path: str, check_result: dict[str, object]) -> str:
    """Format detailed error message for blocking decision.

    Args:
        file_path: Path to file with type errors
        check_result: Result from run_basedpyright_check()

    Returns:
        Formatted error message with all type errors

    Message Structure:
        - Summary line with error count
        - Individual error details (line, message)
        - Actionable fix instructions
        - Command to rerun type check manually
    """
    file_name = Path(file_path).name
    error_count = check_result.get("error_count", 0)
    errors = check_result.get("errors", [])

    # Header
    lines = [
        f"❌ Type checking failed: {error_count} error{'s' if error_count != 1 else ''} found in {file_name}",
        ""
    ]

    # Format each error
    for i, error in enumerate(errors[:10], 1):  # Limit to first 10 errors
        line_num = error.get("range", {}).get("start", {}).get("line", 0) + 1
        message = error.get("message", "Unknown error")

        lines.append(f"Error {i} (line {line_num}): {message}")

    # Show truncation if more than 10 errors
    if error_count > 10:
        lines.append(f"\n... and {error_count - 10} more error{'s' if error_count - 10 != 1 else ''}")

    # Footer with instructions
    lines.extend([
        "",
        "Please fix all type errors before continuing.",
        f"Run: basedpyright {file_path}"
    ])

    return "\n".join(lines)
```

#### `get_project_dir()` - Project Directory Helper
```python
def get_project_dir() -> Path:
    """Get absolute path to project directory.

    Uses CLAUDE_PROJECT_DIR environment variable with fallback to cwd.

    Returns:
        Path object for project directory

    Usage:
        Used as cwd when running basedpyright to ensure it finds
        pyrightconfig.json in the project root.
    """
    project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir_str).resolve()
```

### Security Validation

#### Path Traversal Prevention
```python
# Use is_within_project() from shared utils
if not is_within_project(file_path):
    output_feedback("", suppress_output=True)
    return
```

**Security Measures:**
- Resolve absolute paths before checking
- Use Path.is_relative_to() for validation
- Reject files outside CLAUDE_PROJECT_DIR
- Prevent accessing sensitive system files

#### File Type Validation
```python
# Use is_python_file() from shared utils
if not is_python_file(file_path):
    output_feedback("", suppress_output=True)
    return
```

**Validation Rules:**
- Only process .py and .pyi files
- Skip non-Python files immediately
- Prevent processing arbitrary file types

#### Subprocess Safety
```python
# Always use list form for subprocess (never shell=True)
subprocess.run(
    ["basedpyright", "--outputjson", file_path],
    capture_output=True,
    text=True,
    timeout=10,
    cwd=get_project_dir(),
    shell=False  # Explicit (default, but be clear)
)
```

**Safety Measures:**
- Use list form (prevents shell injection)
- Never use shell=True
- Set explicit timeout to prevent hanging
- Capture output safely

### Error Handling Strategy

#### Critical vs Non-Critical Errors

**Critical Errors (BLOCK):**
- Type errors found by basedpyright
- These MUST be fixed before continuing

**Non-Critical Errors (ALLOW with warning):**
- Timeout during type check (file too large)
- basedpyright not found in PATH
- JSON parsing failures
- Unexpected exceptions

#### Error Logging
```python
try:
    # ... type checking operation ...
except Exception as e:
    # Log to stderr for debugging, but don't block on infrastructure errors
    print(f"Basedpyright hook error: {e}", file=sys.stderr)
    output_feedback("", suppress_output=True)
```

**Philosophy:**
- Only block on actual type errors
- Infrastructure failures should not halt development
- Log all errors to stderr for debugging
- Fail-safe approach for unexpected issues

### Performance Considerations

**Timeouts:**
- `basedpyright`: 10 second timeout per file
- Total max execution: ~10 seconds

**Optimization Strategies:**
- Skip non-Python files immediately
- Skip files outside project directory
- Use JSON output for faster parsing
- Type check single file (not entire project)
- Leverage basedpyright's caching internally

**Expected Performance:**
- Small files (< 100 lines): < 1 second
- Medium files (100-500 lines): 1-3 seconds
- Large files (> 500 lines): 3-10 seconds

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
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/basedpyright_checking.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Configuration Notes:**
- `matcher`: Targets Write, Edit, and NotebookEdit tools
- `timeout`: 15 seconds (includes overhead + type checking)
- `command`: Uses $CLAUDE_PROJECT_DIR for portability
- Runs in parallel with other PostToolUse hooks

### Pyrightconfig.json Integration

The hook respects project's `pyrightconfig.json` settings:

**Current Project Settings:**
```json
{
  "include": ["src", ".claude", "tests"],
  "exclude": ["**/node_modules", "**/__pycache__"],
  "extraPaths": [".claude/hooks/pre_tools", ".claude/hooks/post_tools"],
  "pythonVersion": "3.12",
  "typeCheckingMode": "strict",

  // Strict typing - no Any types allowed
  "reportAny": "error",
  "reportExplicitAny": "error",
  "reportUnknownMemberType": "error",
  "reportUnknownArgumentType": "error",
  "reportUnknownVariableType": "error",
  "reportUnknownLambdaType": "error",
  "reportUnknownParameterType": "error",
  "reportMissingImports": "error",

  "failOnWarnings": true,
  "enableTypeIgnoreComments": true
}
```

**Hook Behavior:**
- Automatically uses project's pyrightconfig.json
- No need to pass config explicitly
- Respects all project-specific rules and settings
- Enforces strict type checking as configured

### Local Override Support

Users can temporarily disable in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": []
  }
}
```

Or disable just basedpyright hook by removing its entry from the PostToolUse hooks array.

## Testing Strategy

### Unit Tests Location
`tests/claude_hook/post_tools/test_basedpyright_checking.py`

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

#### 2. Type Checking Tests
```python
def test_run_basedpyright_check_on_valid_file():
    """Test type checking of valid, well-typed Python file."""

def test_run_basedpyright_check_with_type_errors():
    """Test detection of type errors."""

def test_run_basedpyright_check_with_missing_annotations():
    """Test detection of missing type annotations."""

def test_run_basedpyright_check_with_any_types():
    """Test rejection of Any types in strict mode."""

def test_run_basedpyright_check_handles_syntax_errors():
    """Test handling of files with syntax errors."""
```

#### 3. Blocking Behavior Tests
```python
def test_blocks_on_type_errors():
    """Test that hook blocks when type errors are found."""

def test_allows_on_clean_type_check():
    """Test that hook allows when no type errors found."""

def test_allows_on_infrastructure_errors():
    """Test that infrastructure errors don't block (fail-safe)."""
```

#### 4. Error Message Tests
```python
def test_format_error_message_single_error():
    """Test formatting of single type error."""

def test_format_error_message_multiple_errors():
    """Test formatting of multiple type errors."""

def test_format_error_message_truncation():
    """Test truncation of > 10 errors."""

def test_error_message_includes_line_numbers():
    """Test that error messages include line numbers."""
```

#### 5. Integration Tests
```python
def test_full_workflow_write_tool():
    """Test complete workflow for Write tool."""

def test_full_workflow_edit_tool():
    """Test complete workflow for Edit tool."""

def test_full_workflow_notebookedit_tool():
    """Test complete workflow for NotebookEdit tool."""

def test_integration_with_pyrightconfig():
    """Test that hook respects pyrightconfig.json settings."""
```

#### 6. Error Handling Tests
```python
def test_handles_basedpyright_timeout():
    """Test timeout handling."""

def test_handles_missing_basedpyright_binary():
    """Test error handling when basedpyright is not installed."""

def test_handles_invalid_json_output():
    """Test handling of malformed JSON from basedpyright."""

def test_handles_file_disappearing_during_check():
    """Test handling when file is deleted during type check."""
```

#### 7. Performance Tests
```python
def test_performance_small_file():
    """Test performance on small files (< 100 lines)."""

def test_performance_medium_file():
    """Test performance on medium files (100-500 lines)."""

def test_performance_large_file():
    """Test performance on large files (> 500 lines)."""
```

### Test Execution

Run tests with:
```bash
uv run pytest -n auto tests/claude_hook/post_tools/test_basedpyright_checking.py
```

**Test Coverage Target:** ≥90% code coverage

### Test Data

**Test Files:**
```python
# tests/claude_hook/post_tools/fixtures/valid_typed.py
def add(x: int, y: int) -> int:
    return x + y

# tests/claude_hook/post_tools/fixtures/type_errors.py
def add(x: int, y: int) -> int:
    return str(x + y)  # Type error: returning str instead of int

# tests/claude_hook/post_tools/fixtures/missing_types.py
def add(x, y):  # Missing type annotations
    return x + y
```

## Basedpyright Best Practices Integration

### Configuration Recommendations

**Strict Mode (Recommended):**
```json
{
  "typeCheckingMode": "strict",
  "reportAny": "error",
  "reportUnknownMemberType": "error",
  "failOnWarnings": true
}
```

**Benefits:**
- Catches maximum number of type errors
- Prevents implicit Any types
- Enforces complete type annotations
- Best for high-quality codebases

### Type Ignore Comments

When type errors are unavoidable:
```python
result = subprocess.run(...)
args: object = result.args  # type: ignore[reportUnknownVariableType]
```

**Guidelines:**
- Use sparingly and only when necessary
- Include specific error code to ignore
- Add comment explaining why it's needed
- Document in pyrightconfig.json: `"enableTypeIgnoreComments": true`

### Common Type Checking Scenarios

#### Scenario 1: JSON Parsing
```python
# Bad: Returns Any
data = json.loads(text)

# Good: Use TypedDict or cast
from typing import TypedDict, cast

class Config(TypedDict):
    name: str
    value: int

data = cast(Config, json.loads(text))
```

#### Scenario 2: Dictionary Access
```python
# Bad: Unknown type
value = my_dict.get("key")

# Good: Provide default with correct type
value = my_dict.get("key", "default_string")
```

#### Scenario 3: subprocess.args
```python
# Known basedpyright limitation with subprocess.args
result = subprocess.run(["echo", "hello"], capture_output=True)
args: object = result.args  # type: ignore[reportUnknownVariableType]
```

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
Remove the basedpyright_checking hook entry from PostToolUse hooks array.

### Emergency Fixes

If hook is blocking legitimate work:

1. **Quick Disable:**
   ```bash
   # Add to .claude/settings.local.json
   echo '{"hooks": {"PostToolUse": []}}' > .claude/settings.local.json
   ```

2. **Fix Type Errors:**
   ```bash
   # Run basedpyright to see all errors
   basedpyright src/problematic_file.py
   ```

3. **Use Type Ignore (last resort):**
   ```python
   # Add type: ignore to problematic lines
   result = problematic_function()  # type: ignore
   ```

## Migration Path

### Phase 1: Audit Current Code
- Run basedpyright on entire codebase
- Identify files with type errors
- Create backlog of type fixes
- Document patterns of common errors

### Phase 2: Soft Launch (Warning Mode)
- Deploy hook with blocking disabled (feedback only)
- Monitor type errors in existing code
- Fix critical type errors
- Train team on type annotation best practices

### Phase 3: Strict Enforcement
- Enable blocking mode (this specification)
- Enforce zero type errors on new/edited files
- Continue fixing type errors in old files
- Monitor for false positives

### Phase 4: Full Coverage
- Ensure all Python files pass strict type checking
- Remove any type: ignore comments where possible
- Document remaining unavoidable type ignores
- Maintain 100% type safety going forward

## Success Metrics

### Quantitative Metrics
- **Execution Time**: Average < 3 seconds per file
- **Error Rate**: < 1% of executions result in infrastructure errors
- **Coverage**: 100% of Python Write/Edit operations trigger hook
- **Test Coverage**: ≥90% code coverage
- **Type Error Rate**: 0 type errors in new/edited code

### Qualitative Metrics
- **Code Quality**: All Python code has complete type annotations
- **Bug Prevention**: Fewer runtime type errors in production
- **Developer Experience**: Clear, actionable type error messages
- **Maintenance**: Minimal ongoing maintenance required

## Future Enhancements

### Potential Additions
1. **Performance Mode**: Skip type check for very large files
2. **Incremental Checking**: Only check changed regions
3. **Warning Mode**: Allow with warnings, block only on errors
4. **Custom Severity**: Configurable error thresholds
5. **Type Coverage Report**: Generate type coverage statistics
6. **Auto-Fix Suggestions**: Suggest type annotations for missing types

### Experimental Features
1. **AI-Powered Type Hints**: Use Claude to suggest type annotations
2. **Smart Type Inference**: Infer types from usage patterns
3. **Cross-File Analysis**: Type check related files together

## References

### Documentation
- [Basedpyright Documentation](https://docs.basedpyright.com/)
- [Pyright Type Checking](https://github.com/microsoft/pyright)
- [Python Type Hints PEP 484](https://peps.python.org/pep-0484/)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Claude Code Hooks Reference](../../../ai_docs/claude-code-hooks.md)

### Related Specifications
- [PostToolUse Shared Utils Spec](./shared-utils-spec.md)
- [Ruff Checking Spec](./ruff-checking-spec.md)
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
    "content": "def add(x: int, y: int) -> int:\n    return str(x + y)\n"
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
5. Run `basedpyright --outputjson example.py`
6. Parse JSON output → 1 error found
   - Line 2: Expression of type "str" is not assignable to return type "int"

**Output (BLOCKING):**
```json
{
  "decision": "block",
  "reason": "❌ Type checking failed: 1 error found in example.py\n\nError 1 (line 2): Expression of type \"str\" is not assignable to return type \"int\"\n\nPlease fix all type errors before continuing.\nRun: basedpyright /project/root/src/example.py",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Type errors must be resolved"
  },
  "suppressOutput": false
}
```

### Verbose Logging Mode

For debugging, add verbose logging:

```python
import os

DEBUG = os.environ.get("BASEDPYRIGHT_HOOK_DEBUG", "").lower() == "true"

def log_debug(message: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)
```

Enable with:
```bash
export BASEDPYRIGHT_HOOK_DEBUG=true
```

### Integration with pyrightconfig.json

**Project Configuration:**
The hook automatically uses the project's pyrightconfig.json file located at the project root. This ensures consistency between the hook's type checking and manual type checking runs.

**Key Settings:**
- `typeCheckingMode: "strict"` - Enforces strictest type checking
- `reportAny: "error"` - Blocks implicit Any types
- `failOnWarnings: true` - Treats warnings as errors

**Testing Configuration:**
The hook changes working directory to CLAUDE_PROJECT_DIR before running basedpyright, ensuring it finds and uses the correct configuration file.

---

**End of Specification**
