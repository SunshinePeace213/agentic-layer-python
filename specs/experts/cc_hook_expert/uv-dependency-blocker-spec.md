# UV Dependency Blocker Hook - Specification

## Overview

The UV Dependency Blocker is a PreToolUse hook that prevents direct editing of Python dependency files, enforcing the use of UV commands for dependency management during development. This ensures consistency, prevents manual errors, and maintains the integrity of the dependency resolution system.

## Purpose and Objectives

### Primary Goals
1. **Prevent Manual Dependency Edits**: Block direct editing of dependency files that should only be modified through UV commands
2. **Enforce UV Workflow**: Guide developers to use proper UV commands (`uv add`, `uv remove`, `uv sync`)
3. **Protect Auto-Generated Files**: Prevent modification of lock files and other auto-generated dependency artifacts
4. **Provide Clear Guidance**: Offer helpful error messages with correct UV command alternatives

### Protected Files
The hook protects the following dependency files:

1. **requirements.txt** - Traditional pip requirements file
   - Should use: `uv add <package>` or `uv remove <package>`

2. **pyproject.toml** - Modern Python project configuration
   - Should use: `uv add <package>` or `uv remove <package>`
   - Note: Only dependency-related sections should be blocked, not the entire file

3. **uv.lock** - UV's lock file (auto-generated)
   - Should use: Automatically updated by `uv add/remove/sync`
   - Never manually edit

4. **Pipfile** - Pipenv configuration (legacy)
   - Should use: `uv add <package>` or migrate to pyproject.toml
   - Auto-generated if using Pipenv

5. **Pipfile.lock** - Pipenv lock file (legacy)
   - Should use: Automatically updated by Pipenv or UV
   - Never manually edit

## Event Selection and Rationale

### Hook Event: PreToolUse

**Rationale**:
- Intercepts tool execution BEFORE the edit happens
- Allows blocking the operation with clear feedback
- Prevents corrupted dependency files from being created

**Alternative Considered**: PostToolUse
- ❌ Rejected: Would detect violations after the damage is done
- ❌ Cannot prevent the edit, only notify

### Tool Matchers

**Target Tools**: `Write|Edit|MultiEdit`

**Rationale**:
- `Write` - Catches file creation or complete rewrites
- `Edit` - Catches targeted edits to existing files
- `MultiEdit` - Catches batch edit operations (if used)

**Tools NOT Matched**:
- `Bash` - Complex to parse reliably for all edit scenarios (echo >, cat <<EOF, etc.)
- However, we should consider adding Bash support in future iterations for completeness
- `Read` - No need to block reading dependency files

## Input/Output Schema

### Input Schema

The hook receives JSON via stdin following the PreToolUse event structure:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write|Edit|MultiEdit",
  "tool_input": {
    "file_path": "/path/to/requirements.txt"
  }
}
```

**Key Fields**:
- `tool_name`: String - Name of the tool being invoked
- `tool_input.file_path`: String - Absolute or relative path to the file

### Output Schema

The hook outputs JSON to stdout with a permission decision:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny|allow",
    "permissionDecisionReason": "Detailed explanation with UV command alternative"
  },
  "suppressOutput": true
}
```

**Decision Types**:

1. **Allow** - File is not a protected dependency file
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Not a dependency file"
  }
}
```

2. **Deny** - File is protected, block the edit
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Cannot edit requirements.txt directly.\nUse: uv add <package> or uv remove <package>\nDirect edits bypass dependency resolution and may cause conflicts."
  },
  "suppressOutput": true
}
```

## Security Validation Requirements

### Path Validation

1. **Absolute Path Resolution**
   - Convert all file paths to absolute paths for comparison
   - Use `os.path.abspath()` or `Path.resolve()` to normalize paths
   - Prevents bypassing via relative paths like `./requirements.txt` vs `requirements.txt`

2. **Path Traversal Prevention**
   - Already handled by Claude Code's security layer
   - No additional validation needed in this hook

3. **Case Sensitivity**
   - Use case-insensitive comparison for filenames on case-insensitive filesystems
   - Check both `requirements.txt` and `Requirements.txt`
   - Convert filenames to lowercase for comparison

### File Detection Logic

**Strategy**: Filename-based detection (not content analysis)

**Implementation**:
```python
def is_protected_dependency_file(file_path: str) -> tuple[bool, str | None]:
    """
    Check if a file path represents a protected dependency file.

    Returns:
        (is_protected, file_type) - tuple indicating protection status and file type
    """
    path = Path(file_path).resolve()
    filename = path.name.lower()

    # Check against protected filenames
    protected_files = {
        'requirements.txt': 'requirements file',
        'pyproject.toml': 'project configuration',
        'uv.lock': 'UV lock file',
        'pipfile': 'Pipfile configuration',
        'pipfile.lock': 'Pipfile lock file'
    }

    if filename in protected_files:
        return (True, protected_files[filename])

    return (False, None)
```

### Special Cases

1. **requirements.txt variants**
   - `requirements.txt` - BLOCK
   - `requirements-dev.txt` - BLOCK (common pattern)
   - `requirements-test.txt` - BLOCK (common pattern)
   - `requirements-prod.txt` - BLOCK (common pattern)
   - Pattern: `requirements*.txt` should be blocked

2. **pyproject.toml**
   - **Challenge**: This file contains both dependency and non-dependency sections
   - **Decision**: Block ALL edits to pyproject.toml
   - **Rationale**:
     - UV commands can modify non-dependency sections when needed
     - Simpler implementation, clearer user guidance
     - Users can use `uv add` for dependencies and UV commands for project settings
   - **Future Enhancement**: Parse content to only block dependency sections

3. **Template/Example Files**
   - `requirements.txt.sample` - ALLOW (template file)
   - `requirements.txt.example` - ALLOW (template file)
   - `pyproject.toml.dist` - ALLOW (distribution template)
   - Pattern: `*.(sample|example|template|dist)` should be allowed

## Dependency Management

### UV Script Metadata

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**Dependencies**: NONE
- Uses only Python standard library
- `pathlib` - Path manipulation
- `json` - Input/output serialization
- `sys` - stdin/stdout/exit codes
- Shared utilities from `.claude/hooks/pre_tools/utils/`

### Shared Utilities

The hook will utilize the existing shared utilities:

```python
from .utils.utils import parse_hook_input, output_decision
from .utils.data_types import ToolInput
```

**Benefits**:
- 30-35% code reduction
- Consistent error handling
- Centralized bug fixes
- Type safety

## Error Handling Strategies

### Error Categories

1. **Invalid Input Errors** (Non-blocking)
   - Missing stdin data
   - Invalid JSON format
   - Missing required fields
   - **Action**: Allow operation, log to stderr, exit 1

2. **Validation Errors** (Blocking)
   - Protected file detected
   - **Action**: Deny operation, provide UV command alternative, exit 0 with JSON

3. **Unexpected Errors** (Non-blocking)
   - Unexpected exceptions
   - **Action**: Allow operation (fail-safe), log to stderr, exit 1

### Error Handling Implementation

```python
def main() -> None:
    try:
        # Parse input using shared utility
        parsed = parse_hook_input()
        if not parsed:
            return  # Error already handled by utility

        tool_name, tool_input = parsed

        # Only validate file edit tools
        if tool_name not in {"Write", "Edit", "MultiEdit"}:
            output_decision("allow", "Not a file edit tool")
            return

        # Validate the file path
        violation = validate_dependency_file_edit(tool_input)

        if violation:
            # Deny operation with helpful message
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Not a protected dependency file")

    except Exception as e:
        # Unexpected error - non-blocking (fail-safe)
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)
```

## Testing Scenarios

### Test Infrastructure

**Framework**: pytest with UV
```bash
uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py
```

### Test Categories

#### 1. Protected File Detection Tests

```python
def test_blocks_requirements_txt_edit():
    """Test that editing requirements.txt is blocked."""
    tool_input = ToolInput(file_path="requirements.txt")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None
    assert "requirements.txt" in result.lower()
    assert "uv add" in result.lower()

def test_blocks_pyproject_toml_edit():
    """Test that editing pyproject.toml is blocked."""
    tool_input = ToolInput(file_path="pyproject.toml")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None
    assert "pyproject.toml" in result.lower()

def test_blocks_uv_lock_edit():
    """Test that editing uv.lock is blocked."""
    tool_input = ToolInput(file_path="uv.lock")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None
    assert "auto-generated" in result.lower()

def test_blocks_pipfile_edit():
    """Test that editing Pipfile is blocked."""
    tool_input = ToolInput(file_path="Pipfile")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None

def test_blocks_pipfile_lock_edit():
    """Test that editing Pipfile.lock is blocked."""
    tool_input = ToolInput(file_path="Pipfile.lock")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None
```

#### 2. Variant and Special Case Tests

```python
def test_blocks_requirements_dev_txt():
    """Test that requirements-dev.txt is also blocked."""
    tool_input = ToolInput(file_path="requirements-dev.txt")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None

def test_allows_requirements_sample():
    """Test that requirements.txt.sample is allowed."""
    tool_input = ToolInput(file_path="requirements.txt.sample")
    result = validate_dependency_file_edit(tool_input)
    assert result is None

def test_allows_requirements_example():
    """Test that requirements.txt.example is allowed."""
    tool_input = ToolInput(file_path="requirements.txt.example")
    result = validate_dependency_file_edit(tool_input)
    assert result is None
```

#### 3. Path Resolution Tests

```python
def test_blocks_absolute_path():
    """Test blocking with absolute paths."""
    tool_input = ToolInput(file_path="/home/user/project/requirements.txt")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None

def test_blocks_relative_path():
    """Test blocking with relative paths."""
    tool_input = ToolInput(file_path="./requirements.txt")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None

def test_blocks_nested_path():
    """Test blocking with nested paths."""
    tool_input = ToolInput(file_path="src/requirements.txt")
    result = validate_dependency_file_edit(tool_input)
    assert result is not None
```

#### 4. Case Sensitivity Tests

```python
def test_case_insensitive_detection():
    """Test case-insensitive file detection."""
    test_cases = [
        "requirements.txt",
        "REQUIREMENTS.TXT",
        "Requirements.txt",
        "PyProject.toml",
        "PYPROJECT.TOML",
        "UV.LOCK",
        "Pipfile",
        "PIPFILE"
    ]

    for file_path in test_cases:
        tool_input = ToolInput(file_path=file_path)
        result = validate_dependency_file_edit(tool_input)
        assert result is not None, f"Failed to block {file_path}"
```

#### 5. Non-Dependency File Tests

```python
def test_allows_regular_python_file():
    """Test that regular Python files are allowed."""
    tool_input = ToolInput(file_path="main.py")
    result = validate_dependency_file_edit(tool_input)
    assert result is None

def test_allows_readme_md():
    """Test that README.md is allowed."""
    tool_input = ToolInput(file_path="README.md")
    result = validate_dependency_file_edit(tool_input)
    assert result is None

def test_allows_config_file():
    """Test that other config files are allowed."""
    tool_input = ToolInput(file_path="setup.cfg")
    result = validate_dependency_file_edit(tool_input)
    assert result is None
```

#### 6. Integration Tests

```python
def test_hook_integration_blocks_write():
    """Integration test: Write tool should be blocked."""
    import subprocess
    import json

    hook_input = {
        "session_id": "test123",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "requirements.txt"}
    }

    result = subprocess.run(
        ["uv", "run", ".claude/hooks/pre_tools/uv_dependency_blocker.py"],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_hook_integration_allows_regular_file():
    """Integration test: Regular file should be allowed."""
    import subprocess
    import json

    hook_input = {
        "session_id": "test123",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "main.py"}
    }

    result = subprocess.run(
        ["uv", "run", ".claude/hooks/pre_tools/uv_dependency_blocker.py"],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
```

## Integration with Existing Hooks

### Configuration in settings.json

Add the hook to the PreToolUse event:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_dependency_blocker.py"
          }
        ]
      }
    ]
  }
}
```

### Hook Execution Order

The UV Dependency Blocker will run in parallel with other PreToolUse hooks:

1. `universal_hook_logger.py` (matcher: `*`) - Logs all tool uses
2. `sensitive_file_access_validator.py` (matcher: `Read|Write|Edit|TodoWrite|Bash`) - Blocks sensitive files
3. **`uv_dependency_blocker.py`** (matcher: `Write|Edit|MultiEdit`) - Blocks dependency file edits

**Potential Conflicts**: None
- Different file patterns being protected
- Both use deny decisions, so either can block independently
- No interaction between hooks required

### Deduplication Considerations

Claude Code automatically deduplicates identical hook commands. Since this hook has a unique command path, no deduplication issues.

## Implementation Plan

### Step-by-Step Implementation Guide

#### Phase 1: Test-Driven Development Setup
1. **Create test file structure**
   ```bash
   touch .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py
   ```

2. **Write failing tests** (TDD approach)
   - Write all test scenarios from "Testing Scenarios" section
   - Run tests: `uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py`
   - Verify all tests fail (no implementation yet)

#### Phase 2: Core Implementation
1. **Create hook file**
   ```bash
   touch .claude/hooks/pre_tools/uv_dependency_blocker.py
   chmod +x .claude/hooks/pre_tools/uv_dependency_blocker.py
   ```

2. **Implement UV script metadata**
   - Add shebang and UV script header
   - Import shared utilities

3. **Implement main() function**
   - Parse input using `parse_hook_input()`
   - Validate tool name
   - Call validation function
   - Output decision

4. **Implement validation logic**
   ```python
   def validate_dependency_file_edit(tool_input: ToolInput) -> str | None:
       """Validate that dependency files are not being edited."""
       # Get file path
       # Resolve to absolute path
       # Check against protected patterns
       # Return violation message or None
   ```

5. **Implement file detection**
   ```python
   def is_protected_dependency_file(file_path: str) -> tuple[bool, str | None]:
       """Check if file is a protected dependency file."""
       # Normalize path and filename
       # Check against patterns
       # Return (is_protected, file_type)
   ```

6. **Implement message generation**
   ```python
   def generate_violation_message(file_type: str, file_path: str) -> str:
       """Generate helpful violation message with UV command alternatives."""
       # Different messages for different file types
       # Include UV command suggestions
   ```

#### Phase 3: Testing and Validation
1. **Run unit tests**
   ```bash
   uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py -v
   ```

2. **Fix failing tests**
   - Iterate until all tests pass
   - Ensure 100% coverage of protected file patterns

3. **Manual integration testing**
   - Add hook to settings.json
   - Test with actual Claude Code session
   - Verify error messages are helpful
   - Test with various file paths (absolute, relative, nested)

#### Phase 4: Configuration and Documentation
1. **Update settings.json**
   - Add hook configuration under PreToolUse
   - Verify matcher pattern is correct

2. **Create inline documentation**
   - Comprehensive docstrings
   - Usage examples in comments
   - Security considerations notes

3. **Update test coverage**
   - Run coverage report: `uv run pytest --cov=.claude/hooks/pre_tools/uv_dependency_blocker.py`
   - Aim for 90%+ coverage

#### Phase 5: Rollback Strategy
If issues arise after deployment:

1. **Quick Rollback**
   - Comment out or remove hook from settings.json
   - Restart Claude Code session

2. **Debugging**
   - Run Claude Code with `--debug` flag
   - Check hook execution logs
   - Verify JSON input/output format

3. **Gradual Rollout**
   - Deploy to local settings first (.claude/settings.local.json)
   - Test thoroughly before committing to project settings

## File Structure

```
.claude/
├── settings.json                                    # Updated with new hook
├── hooks/
│   └── pre_tools/
│       ├── uv_dependency_blocker.py                # NEW: Main hook implementation
│       ├── utils/
│       │   ├── data_types.py                       # Existing: Shared types
│       │   └── utils.py                            # Existing: Shared utilities
│       └── tests/
│           └── test_uv_dependency_blocker.py       # NEW: Test suite

specs/
└── experts/
    └── cc_hook_expert/
        └── uv-dependency-blocker-spec.md           # This specification
```

## Implementation Details

### Complete Hook Implementation Outline

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Dependency Blocker - PreToolUse Hook
========================================
Prevents direct editing of dependency files, enforcing use of UV commands.

Protected Files:
- requirements.txt (and variants like requirements-dev.txt)
- pyproject.toml
- uv.lock
- Pipfile
- Pipfile.lock

Usage:
    python uv_dependency_blocker.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

from pathlib import Path

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision, get_file_path
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision, get_file_path
    from utils.data_types import ToolInput


def main() -> None:
    """Main entry point for the UV dependency blocker hook."""
    # Implementation here
    pass


def validate_dependency_file_edit(tool_input: ToolInput) -> str | None:
    """
    Validate that dependency files are not being directly edited.

    Args:
        tool_input: Tool input parameters containing file_path

    Returns:
        Violation message if found, None otherwise
    """
    # Implementation here
    pass


def is_protected_dependency_file(file_path: str) -> tuple[bool, str | None]:
    """
    Check if a file path represents a protected dependency file.

    Args:
        file_path: Path to check

    Returns:
        (is_protected, file_type) - tuple indicating protection status and file type
    """
    # Implementation here
    pass


def generate_violation_message(file_type: str, file_name: str) -> str:
    """
    Generate helpful violation message with UV command alternatives.

    Args:
        file_type: Type of protected file
        file_name: Name of the file being edited

    Returns:
        Formatted violation message
    """
    # Implementation here
    pass


if __name__ == "__main__":
    main()
```

### Message Templates

#### requirements.txt
```
🚫 Cannot edit requirements.txt directly.

Use UV commands instead:
  • Add dependency: uv add <package>
  • Remove dependency: uv remove <package>
  • Install all: uv sync

Direct edits bypass dependency resolution and may cause version conflicts.
```

#### pyproject.toml
```
🚫 Cannot edit pyproject.toml directly.

Use UV commands instead:
  • Add dependency: uv add <package>
  • Add dev dependency: uv add --dev <package>
  • Remove dependency: uv remove <package>

UV manages dependencies in pyproject.toml automatically.
```

#### uv.lock
```
🚫 Cannot edit uv.lock - this file is auto-generated.

The lock file is automatically updated by UV commands:
  • uv add <package>
  • uv remove <package>
  • uv sync

Manual edits will be overwritten and may corrupt the lock state.
```

#### Pipfile / Pipfile.lock
```
🚫 Cannot edit Pipfile directly.

Consider migrating to modern UV workflow:
  • UV uses pyproject.toml (industry standard)
  • Faster dependency resolution
  • Better compatibility

Or use: pipenv install/uninstall for Pipfile management
```

## Performance Considerations

### Execution Time
- **Target**: < 50ms for typical operations
- **Lightweight**: No external dependencies, simple string matching
- **Early Exit**: Returns immediately for non-file-edit tools

### Resource Usage
- **Memory**: < 10MB (minimal Python runtime + shared utilities)
- **CPU**: Negligible (simple path operations)
- **I/O**: Read stdin, write stdout (no file system operations)

### Parallelization
- Runs in parallel with other PreToolUse hooks
- No blocking I/O operations
- Thread-safe (no shared state)

## Future Enhancements

### Phase 2 Features (Future Iterations)

1. **Smart pyproject.toml Parsing**
   - Only block edits to `[project.dependencies]` and `[tool.uv.dependencies]` sections
   - Allow edits to other sections (name, version, etc.)
   - Requires content parsing and AST analysis

2. **Bash Command Detection**
   - Detect `echo >> requirements.txt`, `cat > requirements.txt`, etc.
   - Regex-based command parsing
   - May have false positives, requires careful testing

3. **Context-Aware Messages**
   - Detect what package was being added/removed from content
   - Suggest exact UV command: `uv add requests` instead of `uv add <package>`
   - Requires content analysis

4. **Whitelist Support**
   - Allow certain automated tools to edit dependency files
   - Environment variable: `UV_DEPENDENCY_BLOCKER_WHITELIST`
   - Use case: CI/CD automated dependency updates

5. **Poetry Support**
   - Block `poetry.lock` edits
   - Suggest Poetry commands as alternative to UV

## Security Considerations

### Threat Model

**Threats Mitigated**:
1. ✅ Accidental manual edits to dependency files
2. ✅ Bypassing UV's dependency resolution
3. ✅ Corrupting lock files through direct edits
4. ✅ Version conflict introduction

**Threats NOT Mitigated**:
1. ❌ Malicious actors with direct file system access
2. ❌ External processes modifying files outside Claude Code
3. ❌ Path traversal attacks (handled by Claude Code security layer)

### Security Best Practices

1. **Path Handling**
   - Always use `Path.resolve()` to normalize paths
   - Handle symbolic links consistently
   - Prevent bypass through path manipulation

2. **Error Messages**
   - Don't expose sensitive file system information
   - Provide helpful but not overly detailed error messages
   - Log suspicious patterns to stderr for debugging

3. **Fail-Safe Behavior**
   - On unexpected errors, ALLOW the operation (non-blocking)
   - Prevents hook from breaking Claude Code functionality
   - Logs errors to stderr for investigation

## Success Criteria

### Functional Requirements
- ✅ Blocks all direct edits to protected dependency files
- ✅ Provides clear, actionable error messages
- ✅ Works with absolute and relative paths
- ✅ Case-insensitive file detection
- ✅ Allows template/example files
- ✅ Zero false positives for non-dependency files

### Performance Requirements
- ✅ Execution time < 50ms per hook invocation
- ✅ No noticeable impact on Claude Code responsiveness
- ✅ Minimal memory footprint

### User Experience Requirements
- ✅ Error messages clearly explain the problem
- ✅ Error messages provide exact UV commands to use
- ✅ No disruption to normal development workflow
- ✅ Consistent behavior across all protected file types

### Testing Requirements
- ✅ 90%+ test coverage
- ✅ All test scenarios pass
- ✅ Integration tests with actual Claude Code session
- ✅ Performance benchmarks met

## Summary

The UV Dependency Blocker hook will:

1. **Event**: PreToolUse
2. **Matchers**: Write|Edit|MultiEdit
3. **Protected Files**: requirements.txt, pyproject.toml, uv.lock, Pipfile, Pipfile.lock (and variants)
4. **Output**: JSON permission decisions with helpful UV command suggestions
5. **Dependencies**: None (uses shared utilities)
6. **Testing**: Comprehensive pytest suite with 90%+ coverage
7. **Integration**: Minimal configuration in settings.json

This hook enforces UV workflow best practices, prevents common errors, and maintains dependency file integrity throughout the development process.
