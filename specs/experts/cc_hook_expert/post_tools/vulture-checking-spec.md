# Vulture Checking Hook Specification

## Overview

**Feature Name:** Vulture Checking Hook
**Location:** `.claude/hooks/post_tools/vulture_checking.py`
**Hook Event:** PostToolUse
**Version:** 1.0.0
**Author:** Claude Code Hook Expert
**Created:** 2025-10-31

## Purpose

Automatically detect dead code (unused functions, classes, variables, imports, and attributes) in Python files after Write or Edit operations using Vulture, providing immediate feedback to Claude about potential dead code. This hook helps maintain clean, efficient codebases by identifying code that can be safely removed.

## Problem Statement

### Current Challenges

1. **Undetected Dead Code**: Unused functions, variables, and imports accumulate over time
2. **Manual Detection**: Developers must manually run `vulture` to find dead code
3. **Code Bloat**: Unused code increases maintenance burden and cognitive load
4. **Delayed Feedback**: Claude doesn't receive immediate feedback about dead code
5. **Import Pollution**: Unused imports clutter files and slow down IDEs
6. **Refactoring Artifacts**: Dead code often remains after refactoring operations

### Impact

- Increased codebase size with unused code
- Higher maintenance burden from unnecessary code
- Potential confusion from unused functions/variables
- Import clutter affecting code readability
- Missed opportunities for code cleanup during development
- Claude may continue generating code that includes dead code patterns

## Objectives

### Primary Goals

1. **Automatic Detection**: Run `vulture` on all Python files after Write/Edit operations
2. **Immediate Feedback**: Provide Claude with clear feedback about dead code findings
3. **Confidence-Based Reporting**: Only report high-confidence dead code (min_confidence: 80)
4. **Non-Blocking**: Inform Claude without blocking workflow (dead code is informational)
5. **Security**: Validate file paths and prevent processing files outside project directory
6. **Selective Reporting**: Filter out false positives and test files

### Success Criteria

- All Python files are automatically scanned for dead code after Write/Edit operations
- Claude receives concise feedback about high-confidence dead code findings
- Hook executes quickly (< 5 seconds for typical files)
- Zero false positives reported to Claude (filtered by confidence threshold)
- Full integration with existing post_tools utils infrastructure
- Respects project's vulture configuration (pyproject.toml)

## Architecture Design

### Hook Event Selection

**Event:** PostToolUse
**Rationale:**
- Dead code detection requires the file to exist on disk
- Need to analyze actual file content, not just tool parameters
- PostToolUse provides tool_response with success status
- Can validate that Write/Edit succeeded before scanning

**Tool Matchers:**
- `Write`: Triggers when new files are created
- `Edit`: Triggers when existing files are modified
- `NotebookEdit`: Triggers when notebook cells are edited (Python code cells)

### File Structure

```
.claude/hooks/post_tools/
├── vulture_checking.py        # Vulture dead code detection hook
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
#   "vulture>=2.14",
# ]
# ///
```

**Rationale:**
- `vulture>=2.14`: Modern version with JSON output and confidence scoring
- No additional dependencies needed (uses stdlib + vulture)

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
    "content": "def unused_func():\n    pass\n\ndef main():\n    print('hello')\n"
  },
  "tool_response": {
    "filePath": "/project/root/src/example.py",
    "success": true
  }
}
```

**Relevant Fields:**
- `tool_name`: Filter for Write/Edit/NotebookEdit
- `tool_input.file_path`: File to scan for dead code
- `tool_response.success`: Only process if tool succeeded

### Output Schema

**Dead Code Found (Non-Blocking Feedback):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "⚠️ Vulture: Found 2 unused items in example.py (unused_func at line 1, unused_import at line 5)"
  },
  "suppressOutput": false
}
```

**No Dead Code:**
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
    "additionalContext": "⚠️ Vulture scan error in example.py: syntax error"
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
   ├─ False → Exit silently (tool failed, skip scanning)
   └─ Continue

5. Verify file exists on disk
   ├─ File not found → Exit silently
   └─ Continue

6. Check if test file
   ├─ Is test file (test_*.py, *_test.py) → Exit silently (tests often have intentional unused code)
   └─ Continue

7. Run vulture scan with JSON output
   ├─ Success → Parse results
   └─ Error → Log warning, exit silently

8. Filter findings by confidence threshold (min_confidence: 80)
   ├─ No high-confidence findings → Exit silently
   └─ Continue

9. Generate concise feedback message
   ├─ Findings exist → Output feedback with summary
   └─ No findings → Exit silently

10. Exit 0 (non-blocking)
```

## Implementation Details

### Core Functions

#### `main()` - Entry Point
```python
def main() -> None:
    """Main entry point for vulture checking hook."""
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

    # 3. Run vulture scan
    findings = run_vulture_scan(file_path)

    # 4. Generate feedback
    feedback = generate_feedback(file_path, findings)

    # Show output if findings exist, suppress if clean
    suppress = len(findings) == 0
    output_feedback(feedback, suppress_output=suppress)
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
        True if file should be scanned for dead code, False otherwise
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

    # Skip test files (tests often have intentional unused code)
    if is_test_file(file_path):
        return False

    return True
```

#### `is_test_file()` - Test File Detection
```python
def is_test_file(file_path: str) -> bool:
    """Check if file is a test file.

    Test files often have intentional unused code (fixtures, helpers)
    and should be skipped from dead code detection.

    Args:
        file_path: File path to check

    Returns:
        True if file appears to be a test file

    Patterns:
        - test_*.py
        - *_test.py
        - conftest.py
        - tests/ directory
        - test/ directory
    """
    path = Path(file_path)
    file_name = path.name

    # Check file name patterns
    if file_name.startswith("test_") or file_name.endswith("_test.py"):
        return True
    if file_name == "conftest.py":
        return True

    # Check if in tests directory
    parts = path.parts
    if "tests" in parts or "test" in parts:
        return True

    return False
```

#### `run_vulture_scan()` - Scan for Dead Code
```python
def run_vulture_scan(file_path: str) -> list[dict[str, object]]:
    """Run vulture scan on file with JSON output.

    Args:
        file_path: Absolute path to Python file

    Returns:
        List of findings (each finding is a dict with: file, line, message, confidence)
        Empty list if no findings or on error

    Implementation:
        - Runs: vulture <file_path> --min-confidence 80 --json
        - Uses project's min_confidence setting from pyproject.toml
        - Parses JSON output for structured findings
        - Filters by confidence threshold
        - Returns only high-confidence findings
    """
    try:
        # Get project directory to find pyproject.toml
        project_dir = get_project_dir()

        # Run vulture with JSON output
        # Note: vulture reads min_confidence from pyproject.toml
        result = subprocess.run(
            ["vulture", file_path, "--min-confidence", "80", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_dir)  # Run from project root to use pyproject.toml
        )

        # Exit code 0 = no dead code found
        # Exit code 1 = dead code found
        # Exit code 2 = error
        if result.returncode == 0:
            return []  # No dead code found

        if result.returncode == 2:
            # Error occurred
            print(f"Vulture error: {result.stderr}", file=sys.stderr)
            return []

        # Parse JSON output
        if result.stdout:
            findings_data = json.loads(result.stdout)

            # Vulture JSON format: list of dicts with keys:
            # - file: str (file path)
            # - line: int (line number)
            # - message: str (description)
            # - confidence: int (0-100)

            # Filter by confidence threshold
            MIN_CONFIDENCE = 80
            high_confidence = [
                f for f in findings_data
                if isinstance(f, dict) and f.get("confidence", 0) >= MIN_CONFIDENCE
            ]

            return high_confidence

        return []

    except subprocess.TimeoutExpired:
        print("Vulture scan timeout", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Vulture JSON parse error: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Vulture scan error: {e}", file=sys.stderr)
        return []
```

#### `generate_feedback()` - Create Feedback Message
```python
def generate_feedback(
    file_path: str,
    findings: list[dict[str, object]]
) -> str:
    """Generate human-readable feedback message.

    Args:
        file_path: File that was scanned
        findings: List of dead code findings from vulture

    Returns:
        Feedback message for Claude (empty if no findings)

    Format:
        "⚠️ Vulture: Found N unused items in file.py (item1 at line X, item2 at line Y)"

    Examples:
        - Single finding: "⚠️ Vulture: Found 1 unused function in example.py (unused_func at line 5)"
        - Multiple findings: "⚠️ Vulture: Found 3 unused items in example.py (unused_func at line 5, unused_var at line 10, unused_import at line 1)"
        - Many findings: "⚠️ Vulture: Found 10 unused items in example.py (show first 3: unused_func at line 5, ...)"
    """
    if not findings:
        return ""

    file_name = Path(file_path).name
    count = len(findings)

    # Extract item descriptions
    items = []
    MAX_ITEMS_TO_SHOW = 3

    for finding in findings[:MAX_ITEMS_TO_SHOW]:
        message = finding.get("message", "unknown")
        line = finding.get("line", 0)

        # Extract item name from message
        # Vulture messages format: "unused function 'foo'" or "unused variable 'bar'"
        item_name = extract_item_name(message)

        items.append(f"{item_name} at line {line}")

    # Format item list
    if count <= MAX_ITEMS_TO_SHOW:
        item_list = ", ".join(items)
    else:
        item_list = ", ".join(items) + f", ...{count - MAX_ITEMS_TO_SHOW} more"

    # Pluralize "item" if needed
    item_word = "item" if count == 1 else "items"

    return f"⚠️ Vulture: Found {count} unused {item_word} in {file_name} ({item_list})"
```

#### `extract_item_name()` - Parse Vulture Message
```python
def extract_item_name(message: str) -> str:
    """Extract item name from vulture message.

    Args:
        message: Vulture message like "unused function 'foo'" or "unused variable 'bar'"

    Returns:
        Extracted item name or cleaned message

    Examples:
        "unused function 'foo'" → "unused_func foo"
        "unused variable 'bar'" → "unused_var bar"
        "unused import 'os'" → "unused_import os"
        "unused attribute 'baz'" → "unused_attr baz"
    """
    # Try to extract quoted name
    import re
    match = re.search(r"'([^']+)'", message)

    if match:
        item_name = match.group(1)

        # Extract item type (function, variable, import, etc.)
        if "function" in message.lower():
            return f"function '{item_name}'"
        elif "variable" in message.lower():
            return f"variable '{item_name}'"
        elif "import" in message.lower():
            return f"import '{item_name}'"
        elif "attribute" in message.lower():
            return f"attribute '{item_name}'"
        elif "class" in message.lower():
            return f"class '{item_name}'"
        else:
            return item_name

    # Fallback: return cleaned message
    return message.replace("unused ", "").strip()
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
    ["vulture", file_path, "--min-confidence", "80", "--json"],
    capture_output=True,
    text=True,
    timeout=10,
    shell=False  # Explicit (default, but be clear)
)
```

### Error Handling Strategy

#### Non-Blocking Errors
- All errors are non-blocking (exit 0)
- Scan errors don't block Claude's workflow
- Timeout errors are logged but don't halt execution
- Parse errors return empty findings list

#### Error Logging
```python
try:
    # ... operation ...
except Exception as e:
    # Log to stderr for debugging, but don't block
    print(f"Vulture hook error: {e}", file=sys.stderr)
    output_feedback("", suppress_output=True)
```

### Performance Considerations

**Timeouts:**
- `vulture scan`: 10 second timeout
- Total max execution: ~10 seconds

**Optimization Strategies:**
- Skip non-Python files immediately
- Skip files outside project directory
- Skip test files (reduce false positives and improve performance)
- Use JSON output for structured parsing (faster than text parsing)
- Filter by confidence threshold to reduce noise

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
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/vulture_checking.py",
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
- `timeout`: 15 seconds (generous for large files)
- `command`: Uses $CLAUDE_PROJECT_DIR for portability

### Vulture Configuration (pyproject.toml)

Hook respects existing vulture configuration:

```toml
[tool.vulture]
min_confidence = 80
ignore_decorators = ["@app.route", "@pytest.fixture", "@click.command"]
ignore_names = ["test_*", "Test*", "setUp", "tearDown"]
exclude = ["*/migrations/*", "*/tests/*"]
sort_by_size = true
verbose = false
```

**Configuration Notes:**
- `min_confidence = 80`: Only report findings with 80%+ confidence
- `ignore_decorators`: Skip common framework patterns
- `ignore_names`: Skip test patterns
- `exclude`: Skip migrations and tests directories

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
`tests/claude_hook/post_tools/test_vulture_checking.py`

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

def test_should_skip_test_files():
    """Test that test files are skipped to avoid false positives."""
```

#### 2. Test File Detection Tests
```python
def test_is_test_file_with_test_prefix():
    """Test detection of test_*.py files."""

def test_is_test_file_with_test_suffix():
    """Test detection of *_test.py files."""

def test_is_test_file_conftest():
    """Test detection of conftest.py."""

def test_is_test_file_in_tests_directory():
    """Test detection of files in tests/ directory."""

def test_is_not_test_file_regular():
    """Test that regular files are not detected as test files."""
```

#### 3. Vulture Scan Tests
```python
def test_run_vulture_scan_with_unused_function():
    """Test detection of unused functions."""

def test_run_vulture_scan_with_unused_variable():
    """Test detection of unused variables."""

def test_run_vulture_scan_with_unused_import():
    """Test detection of unused imports."""

def test_run_vulture_scan_no_dead_code():
    """Test clean file with no dead code."""

def test_run_vulture_scan_low_confidence_filtered():
    """Test that low-confidence findings are filtered out."""
```

#### 4. Feedback Generation Tests
```python
def test_generate_feedback_single_finding():
    """Test feedback with single dead code finding."""

def test_generate_feedback_multiple_findings():
    """Test feedback with multiple findings."""

def test_generate_feedback_many_findings():
    """Test feedback truncation for many findings."""

def test_generate_feedback_no_findings():
    """Test that empty feedback is returned for clean files."""
```

#### 5. Message Parsing Tests
```python
def test_extract_item_name_function():
    """Test extraction of function names from vulture messages."""

def test_extract_item_name_variable():
    """Test extraction of variable names."""

def test_extract_item_name_import():
    """Test extraction of import names."""

def test_extract_item_name_fallback():
    """Test fallback for unparseable messages."""
```

#### 6. Integration Tests
```python
def test_full_workflow_write_tool():
    """Test complete workflow for Write tool."""

def test_full_workflow_edit_tool():
    """Test complete workflow for Edit tool."""

def test_full_workflow_notebookedit_tool():
    """Test complete workflow for NotebookEdit tool."""
```

#### 7. Error Handling Tests
```python
def test_handles_vulture_timeout():
    """Test timeout handling for vulture scan."""

def test_handles_invalid_json_output():
    """Test handling of malformed JSON from vulture."""

def test_handles_missing_vulture_binary():
    """Test error handling when vulture is not installed."""

def test_handles_syntax_error_in_file():
    """Test handling of Python files with syntax errors."""
```

### Test Execution

Run tests with:
```bash
uv run pytest -n auto tests/claude_hook/post_tools/test_vulture_checking.py
```

**Test Coverage Target:** ≥90% code coverage

## Vulture Best Practices Integration

### Confidence Threshold

**Default:** 80% confidence
**Rationale:** Reduces false positives while catching real dead code

**Confidence Levels:**
- 100%: Definitely dead code (unused imports, clearly unused functions)
- 80-99%: Very likely dead code (unused variables, private methods)
- 60-79%: Possibly dead code (may have false positives)
- <60%: Likely false positives

### False Positive Reduction

**Strategies:**
1. **Test File Exclusion**: Skip test_*.py, *_test.py, conftest.py
2. **Confidence Filtering**: Only report findings ≥80% confidence
3. **Decorator Awareness**: Respect ignore_decorators in pyproject.toml
4. **Name Patterns**: Respect ignore_names in pyproject.toml
5. **Directory Exclusions**: Respect exclude patterns in pyproject.toml

### Whitelist Support

For intentional "dead code" (e.g., public API not used internally):

**Create whitelist.py in project root:**
```python
# Whitelist for vulture
# List intentionally unused items here

from mymodule import public_api_function  # noqa: F401
unused_public_class = None  # Used by external packages
```

**Configure in pyproject.toml:**
```toml
[tool.vulture]
paths = ["src", "whitelist.py"]
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
Remove the vulture_checking hook entry from PostToolUse hooks array.

### Adjusting Sensitivity

If too noisy, adjust confidence threshold in pyproject.toml:

```toml
[tool.vulture]
min_confidence = 90  # More conservative (fewer findings)
```

Or in the hook directly:
```python
MIN_CONFIDENCE = 90  # Adjust in run_vulture_scan()
```

## Migration Path

### Phase 1: Soft Launch (Silent Mode)
- Deploy hook with `suppressOutput: true` for all findings
- Monitor stderr logs for errors
- Verify vulture scanning works correctly
- Duration: 1 week

### Phase 2: Feedback Mode
- Change to `suppressOutput: false` for findings
- Claude receives feedback about dead code
- Gather feedback from team
- Duration: 2 weeks

### Phase 3: Optimization
- Tune confidence threshold based on feedback
- Adjust feedback verbosity
- Add additional filtering if needed
- Duration: Ongoing

## Success Metrics

### Quantitative Metrics
- **Execution Time**: Average < 3 seconds per file
- **Error Rate**: < 1% of executions result in errors
- **Coverage**: 100% of Python Write/Edit operations trigger hook
- **Test Coverage**: ≥90% code coverage
- **False Positive Rate**: < 5% of reported findings are false positives

### Qualitative Metrics
- **Code Quality**: Reduced dead code in new/edited files
- **Developer Satisfaction**: Developers appreciate dead code detection
- **Feedback Quality**: Claude receives actionable, concise feedback
- **Maintenance Burden**: Minimal ongoing maintenance required

## Future Enhancements

### Potential Additions
1. **Interactive Removal**: Suggest code removal with confirmation
2. **Statistics Tracking**: Track dead code metrics over time
3. **Integration with Other Tools**: Coordinate with ruff, basedpyright hooks
4. **Diff-Based Analysis**: Only check new/modified code regions
5. **Whitelist Management**: Automated whitelist generation
6. **Severity Levels**: Categorize findings by severity (critical, medium, low)

### Experimental Features
1. **AI-Powered Analysis**: Use Claude to suggest safe removals
2. **Auto-Comment**: Add TODO comments for potential dead code
3. **Dead Code Dashboard**: Aggregate findings across project

## References

### Documentation
- [Vulture Official Docs](https://github.com/jendrikseipp/vulture)
- [Vulture Configuration Guide](https://github.com/jendrikseipp/vulture#configuration)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Claude Code Hooks Reference](../../../ai_docs/claude-code-hooks.md)

### Related Specifications
- [PostToolUse Shared Utils Spec](./shared-utils-spec.md)
- [Ruff Checking Spec](./ruff-checking-spec.md)
- [PreToolUse Hooks Specs](../pre_tools/)

### Code Examples
- [Universal Hook Logger](../../../.claude/hooks/universal_hook_logger.py)
- [Ruff Checking Hook](../../../.claude/hooks/post_tools/ruff_checking.py)

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
    "content": "import os\nimport sys\n\ndef unused_func():\n    pass\n\ndef main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()\n"
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
5. Check is_test_file → false (not a test file)
6. Run `vulture src/example.py --min-confidence 80 --json`
7. Parse findings:
   - unused import 'os' at line 1 (confidence: 90)
   - unused import 'sys' at line 2 (confidence: 90)
   - unused function 'unused_func' at line 4 (confidence: 100)

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "⚠️ Vulture: Found 3 unused items in example.py (import 'os' at line 1, import 'sys' at line 2, function 'unused_func' at line 4)"
  },
  "suppressOutput": false
}
```

### Verbose Logging Mode

For debugging, add verbose logging:

```python
import os

DEBUG = os.environ.get("VULTURE_HOOK_DEBUG", "").lower() == "true"

def log_debug(message: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)
```

Enable with:
```bash
export VULTURE_HOOK_DEBUG=true
```

### Common Dead Code Patterns

**1. Unused Imports:**
```python
import os  # Imported but never used
import sys  # Imported but never used

def main():
    print("hello")
```

**2. Unused Functions:**
```python
def helper_func():  # Defined but never called
    return 42

def main():
    print("hello")
```

**3. Unused Variables:**
```python
def main():
    result = expensive_computation()  # Computed but never used
    print("done")
```

**4. Unused Class Attributes:**
```python
class MyClass:
    unused_attr = 42  # Defined but never accessed

    def method(self):
        print("hello")
```

**5. Unused Method Parameters:**
```python
def process_data(data, unused_param):  # Parameter never used
    return data * 2
```

### Integration with Code Review

**Workflow:**
1. Developer writes code via Claude
2. vulture_checking.py detects dead code
3. Claude receives feedback
4. Claude can suggest removal or ask for clarification
5. Developer confirms or explains why code should remain

**Example Interaction:**
```
Claude: I've written the function. Let me check for any issues...

[vulture_checking hook runs]

Claude: Note: Vulture detected an unused function 'helper_func' at line 5.
Would you like me to remove it, or is it intended for future use?

User: Yes, please remove it.

Claude: [Removes the function]
```

---

**End of Specification**
