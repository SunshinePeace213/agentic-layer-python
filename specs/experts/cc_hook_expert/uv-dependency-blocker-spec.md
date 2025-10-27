# UV Dependency Blocker Hook Specification

**Version:** 1.0.0
**Hook Type:** PreToolUse
**Target Tools:** Write, Edit, MultiEdit, Bash
**Created:** 2025-10-28
**Status:** Ready for Implementation

---

## 1. Purpose and Objectives

### Primary Purpose
Prevent direct editing of Python dependency files to enforce the use of UV commands for dependency management during development. This ensures consistency, reproducibility, and proper dependency tracking across the project lifecycle.

### Objectives
1. **Block Direct File Edits**: Prevent Write/Edit/MultiEdit operations on dependency files
2. **Block Bash Operations**: Prevent shell commands that modify dependency files
3. **Provide Clear Guidance**: Offer actionable UV command alternatives for common operations
4. **Maintain Workflow**: Allow reading dependency files while blocking modifications
5. **Support Standard Files**: Cover all common Python dependency file formats

### Benefits
- **Consistency**: All dependency changes tracked through UV workflow
- **Reproducibility**: uv.lock ensures consistent environments across developers
- **Version Control**: Changes to pyproject.toml/uv.lock are atomic and reviewable
- **Performance**: UV's faster dependency resolution compared to manual edits
- **Safety**: Prevents manual errors in dependency specifications
- **Best Practices**: Enforces modern Python packaging standards (PEP 621)

### Target Dependency Files
- `requirements.txt` - Legacy pip requirements format
- `pyproject.toml` - Modern Python project metadata (PEP 621)
- `uv.lock` - UV lock file for reproducible installs
- `Pipfile` - Pipenv dependency specification
- `Pipfile.lock` - Pipenv lock file

---

## 2. Event Selection and Hook Architecture

### Event Type
**PreToolUse** - Intercepts tool execution before file modification

### Tool Matchers
```json
{
  "matcher": "Write|Edit|MultiEdit|Bash"
}
```

### Rationale
- **Write**: Catches new file creation and overwrites
- **Edit**: Catches inline edits to existing files
- **MultiEdit**: Catches multi-file edit operations
- **Bash**: Catches shell commands that modify files (echo >, sed -i, etc.)
- PreToolUse allows blocking before modification (prevents data loss)

### Hook Configuration Entry
```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit|MultiEdit|Bash",
      "hooks": [
        {
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_dependency_blocker.py"
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
  "tool_name": "Write|Edit|MultiEdit|Bash",
  "tool_input": {
    "file_path": "/project/requirements.txt",
    "content": "requests>=2.28.0"
  }
}
```

### Relevant Fields by Tool

#### Write/Edit/MultiEdit
- **tool_name**: One of "Write", "Edit", "MultiEdit"
- **tool_input.file_path**: Path to file being modified

#### Bash
- **tool_name**: "Bash"
- **tool_input.command**: Shell command string to validate

---

## 4. Output Schema

### JSON Output Format
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Detailed explanation with UV command alternatives"
  },
  "suppressOutput": true
}
```

### Permission Decisions
- **"allow"**: File is not a dependency file, or tool is not monitored
- **"deny"**: File is a dependency file being modified
- **"ask"**: Not used in this hook (binary allow/deny decision)

### Decision Logic
1. File path matches dependency file → **deny** (with alternatives)
2. Bash command modifies dependency file → **deny** (with alternatives)
3. File is not a dependency file → **allow**
4. Tool not monitored → **allow**

---

## 5. Detection Patterns

### 5.1 Dependency File Detection

#### File Name Patterns
```python
DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock"
}
```

#### Detection Logic
```python
def is_dependency_file(file_path: str) -> bool:
    """
    Check if a file path represents a dependency file.

    Args:
        file_path: Absolute or relative file path

    Returns:
        True if file is a dependency file, False otherwise

    Examples:
        >>> is_dependency_file("/project/requirements.txt")
        True
        >>> is_dependency_file("./pyproject.toml")
        True
        >>> is_dependency_file("/project/src/main.py")
        False
        >>> is_dependency_file("/project/requirements.txt.bak")
        False
    """
    if not file_path:
        return False

    filename = os.path.basename(file_path)
    return filename in DEPENDENCY_FILES
```

### 5.2 Bash Command Pattern Detection

#### Shell Redirect Patterns
Detect shell commands that redirect output to dependency files:

```bash
# Block these patterns:
echo "requests" > requirements.txt
cat file >> requirements.txt
sed -i 's/old/new/' pyproject.toml
vi requirements.txt
nano Pipfile
```

#### Detection Regex
```python
BASH_FILE_MODIFY_PATTERNS = [
    # Redirect operators: >, >>, &>
    re.compile(r'(?:>>?|2>>?|&>>?)\s+([^\s;|&<>]+)'),

    # Inline edit commands: sed -i, perl -i
    re.compile(r'\b(?:sed|perl)\s+(?:-[a-z]*i[a-z]*)\s+.*?\s+([^\s;|&<>]+)'),

    # Text editors: vi, vim, nano, emacs
    re.compile(r'\b(?:vi|vim|nano|emacs)\s+([^\s;|&<>]+)'),
]
```

---

## 6. Validation Rules

### Rule 1: Block Write Tool on Dependency Files

```python
def validate_write_operation(file_path: str) -> Optional[str]:
    """
    Validate Write tool operations on dependency files.

    Args:
        file_path: Target file path

    Returns:
        Error message if invalid, None if valid

    Examples:
        >>> validate_write_operation("requirements.txt")
        "📦 Blocked: Direct editing of requirements.txt..."

        >>> validate_write_operation("src/main.py")
        None
    """
    if not is_dependency_file(file_path):
        return None

    filename = os.path.basename(file_path)
    alternatives = get_uv_alternatives(filename)

    return f"""📦 Blocked: Direct editing of {filename}

Why this is blocked:
  - Manual edits bypass UV's dependency resolution
  - Changes won't be reflected in uv.lock
  - Risk of dependency conflicts
  - No validation of version constraints
  - Breaks project reproducibility

{alternatives}

For migration from requirements.txt:
  1. Review existing requirements.txt
  2. Use: uv add <package1> <package2> ...
  3. Or manually add to pyproject.toml [project.dependencies]
  4. Run: uv lock to generate lock file
  5. Safely delete old requirements.txt after migration"""
```

### Rule 2: Block Edit Tool on Dependency Files

```python
def validate_edit_operation(file_path: str) -> Optional[str]:
    """
    Validate Edit tool operations on dependency files.

    Args:
        file_path: Target file path

    Returns:
        Error message if invalid, None if valid
    """
    # Same logic as validate_write_operation
    return validate_write_operation(file_path)
```

### Rule 3: Block Bash Commands Modifying Dependency Files

```python
def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash commands that might modify dependency files.

    Args:
        command: Shell command to validate

    Returns:
        Error message if invalid, None if valid

    Examples:
        >>> validate_bash_command("echo 'requests' > requirements.txt")
        "📦 Blocked: Shell modification of requirements.txt..."

        >>> validate_bash_command("cat requirements.txt")
        None
    """
    # Extract file paths from command
    file_paths = extract_file_paths_from_bash(command)

    # Check if any are dependency files
    for file_path in file_paths:
        if is_dependency_file(file_path):
            filename = os.path.basename(file_path)
            alternatives = get_uv_alternatives(filename)

            return f"""📦 Blocked: Shell modification of {filename}

Command: {command}

Why this is blocked:
  - Bypasses UV dependency management
  - Won't update uv.lock
  - Risk of syntax errors
  - No validation or conflict resolution

{alternatives}"""

    return None
```

---

## 7. UV Command Alternatives

### Alternative Command Mapping

```python
def get_uv_alternatives(filename: str) -> str:
    """
    Get UV command alternatives based on the dependency file.

    Args:
        filename: Name of the dependency file

    Returns:
        Formatted string with UV alternatives
    """
    if filename == "requirements.txt":
        return """Recommended UV commands:
  - Add package:        uv add <package>
  - Add with version:   uv add "package>=1.0,<2.0"
  - Add dev package:    uv add --dev <package>
  - Remove package:     uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync all:           uv sync
  - Install from lock:  uv sync --frozen

Note: UV uses pyproject.toml for dependency tracking (modern standard)"""

    elif filename == "pyproject.toml":
        return """Recommended UV commands:
  - Add dependency:     uv add <package>
  - Add dev dependency: uv add --dev <package>
  - Add with group:     uv add --group <group> <package>
  - Remove dependency:  uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync dependencies:  uv sync
  - Lock dependencies:  uv lock

Manual edits to pyproject.toml should be followed by: uv lock"""

    elif filename == "uv.lock":
        return """Recommended UV commands:
  - Regenerate lock:    uv lock
  - Update all:         uv lock --upgrade
  - Update package:     uv lock --upgrade-package <package>
  - Sync from lock:     uv sync --frozen

IMPORTANT: Never edit uv.lock manually!
This file is auto-generated by UV and ensures reproducibility."""

    elif filename in ("Pipfile", "Pipfile.lock"):
        return """Recommended UV commands:
  - Add dependency:     uv add <package>
  - Add dev dependency: uv add --dev <package>
  - Remove dependency:  uv remove <package>
  - Sync dependencies:  uv sync

Note: Consider migrating from Pipenv to UV for better performance:
  1. Review Pipfile dependencies
  2. Use: uv add <package1> <package2> ...
  3. UV will create pyproject.toml and uv.lock
  4. Safely remove Pipfile after migration"""

    else:
        return """Recommended UV commands:
  - Add package:        uv add <package>
  - Remove package:     uv remove <package>
  - Sync dependencies:  uv sync
  - Lock dependencies:  uv lock"""
```

---

## 8. Security Considerations

### Path Traversal Prevention
```python
def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        file_path: Path to validate

    Returns:
        True if path is safe, False otherwise
    """
    # Check for path traversal patterns
    if ".." in file_path:
        return False

    # Ensure path doesn't escape project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    abs_path = os.path.abspath(file_path)
    abs_project = os.path.abspath(project_dir)

    try:
        common = os.path.commonpath([abs_path, abs_project])
        return common == abs_project
    except ValueError:
        return False
```

### Input Sanitization
- All file paths normalized with `os.path.basename()`
- Command strings are analyzed but not executed
- No shell evaluation or dynamic code execution
- JSON output properly escaped

### Fail-Safe Behavior
```python
try:
    # Hook logic
    pass
except Exception as e:
    # Fail-safe: allow operation on error
    print(f"UV dependency blocker error: {e}", file=sys.stderr)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

---

## 9. Error Handling Strategies

### Error Categories

#### 1. Invalid Input
```python
if not parsed:
    output_decision("allow", "Failed to parse input (fail-safe)")
    return
```

#### 2. Missing File Path
```python
if not file_path:
    output_decision("allow", "No file path to validate")
    return
```

#### 3. Path Resolution Failures
```python
try:
    abs_path = os.path.abspath(file_path)
except (OSError, ValueError) as e:
    # Allow operation if path cannot be resolved
    output_decision("allow", f"Path resolution failed (fail-safe): {e}")
    return
```

#### 4. Unexpected Exceptions
```python
except Exception as e:
    # Log error but don't block Claude operations
    print(f"Unexpected error: {e}", file=sys.stderr)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Non-Blocking Errors
All errors result in `allow` decisions to prevent disrupting Claude Code operations. The hook is defensive-only and should never break legitimate workflows.

---

## 10. Testing Scenarios

### 10.1 Unit Tests

#### Test File Detection
```python
def test_is_dependency_file():
    """Test dependency file detection."""
    assert is_dependency_file("requirements.txt") == True
    assert is_dependency_file("./requirements.txt") == True
    assert is_dependency_file("/path/to/requirements.txt") == True
    assert is_dependency_file("pyproject.toml") == True
    assert is_dependency_file("uv.lock") == True
    assert is_dependency_file("Pipfile") == True
    assert is_dependency_file("Pipfile.lock") == True

    # Negative cases
    assert is_dependency_file("main.py") == False
    assert is_dependency_file("requirements.txt.bak") == False
    assert is_dependency_file("requirements_old.txt") == False
    assert is_dependency_file("") == False
```

#### Test Write Tool Validation
```python
def test_validate_write_operation():
    """Test Write tool validation."""
    # Should block
    result = validate_write_operation("requirements.txt")
    assert result is not None
    assert "Blocked" in result
    assert "uv add" in result

    # Should allow
    result = validate_write_operation("src/main.py")
    assert result is None
```

#### Test Edit Tool Validation
```python
def test_validate_edit_operation():
    """Test Edit tool validation."""
    # Should block
    result = validate_edit_operation("pyproject.toml")
    assert result is not None
    assert "Blocked" in result

    # Should allow
    result = validate_edit_operation("README.md")
    assert result is None
```

#### Test Bash Command Validation
```python
def test_validate_bash_command():
    """Test bash command validation."""
    # Should block redirects
    result = validate_bash_command("echo 'requests' > requirements.txt")
    assert result is not None
    assert "Blocked" in result

    # Should block sed -i
    result = validate_bash_command("sed -i 's/old/new/' pyproject.toml")
    assert result is not None

    # Should allow read operations
    result = validate_bash_command("cat requirements.txt")
    assert result is None

    # Should allow unrelated commands
    result = validate_bash_command("echo 'hello world'")
    assert result is None
```

### 10.2 Integration Tests

#### Test Hook with Mock Input
```python
def test_hook_with_write_tool():
    """Test hook with Write tool input."""
    mock_input = json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "requirements.txt",
            "content": "requests>=2.28.0"
        }
    })

    # Run hook with mock stdin
    result = run_hook_with_input(mock_input)

    # Parse output
    output = json.loads(result)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "requirements.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]
```

#### Test Hook with Bash Tool
```python
def test_hook_with_bash_tool():
    """Test hook with Bash tool input."""
    mock_input = json.dumps({
        "session_id": "test123",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo 'django' >> requirements.txt"
        }
    })

    result = run_hook_with_input(mock_input)
    output = json.loads(result)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
```

### 10.3 Edge Cases

#### Empty File Path
```python
def test_empty_file_path():
    """Test handling of empty file path."""
    result = validate_write_operation("")
    assert result is None  # Should allow (fail-safe)
```

#### Path Traversal Attempt
```python
def test_path_traversal():
    """Test path traversal prevention."""
    result = validate_write_operation("../../requirements.txt")
    # Should validate against project directory
```

#### Non-Dependency File
```python
def test_non_dependency_file():
    """Test that non-dependency files are allowed."""
    result = validate_write_operation("README.md")
    assert result is None

    result = validate_write_operation("src/utils/helper.py")
    assert result is None
```

#### MultiEdit Tool
```python
def test_multiedit_tool():
    """Test MultiEdit tool handling."""
    # MultiEdit uses same file_path validation
    mock_input = json.dumps({
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": "pyproject.toml"
        }
    })
    # Should block
```

---

## 11. Implementation Plan

### Phase 1: Core Hook Implementation
1. **Create hook file**: `.claude/hooks/pre_tools/uv_dependency_blocker.py`
2. **Import shared utilities**: Use `parse_hook_input()` and `output_decision()` from utils
3. **Implement detection logic**:
   - `is_dependency_file(file_path: str) -> bool`
   - `extract_file_paths_from_bash(command: str) -> list[str]`
4. **Implement validation logic**:
   - `validate_write_operation(file_path: str) -> Optional[str]`
   - `validate_bash_command(command: str) -> Optional[str]`
5. **Implement alternative suggestions**:
   - `get_uv_alternatives(filename: str) -> str`
6. **Implement main() entry point** with fail-safe error handling

### Phase 2: UV Script Metadata
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

### Phase 3: Testing Infrastructure
1. **Create test file**: `.claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py`
2. **Write unit tests**: File detection, validation logic, edge cases
3. **Write integration tests**: Full hook execution with mock inputs
4. **Run tests**: `uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py`
5. **Achieve coverage**: Aim for >90% code coverage

### Phase 4: Configuration
1. **Update settings.json**: Add hook configuration to PreToolUse
2. **Test hook registration**: Use `/hooks` command to verify
3. **Validate execution**: Run `claude --debug` and trigger hook

### Phase 5: Documentation
1. **Add docstrings**: Document all functions with type hints
2. **Create usage examples**: Add to hook file header
3. **Update project docs**: Document the hook in project README or CLAUDE.md

---

## 12. Dependencies

### Python Version
- Minimum: Python 3.12+
- Rationale: Matches project standard, modern type hints

### External Packages
- None (standard library only)
- Uses: `os`, `sys`, `json`, `re`, `typing`

### Internal Dependencies
```python
from .utils import parse_hook_input, output_decision
from .utils.data_types import ToolInput, HookOutput
```

### Environment Variables
- `CLAUDE_PROJECT_DIR`: Project root directory (fallback to `os.getcwd()`)

---

## 13. Performance Considerations

### Complexity Analysis
- File detection: O(1) - hash set lookup
- Bash parsing: O(n) - linear scan of command string
- Path validation: O(1) - basename extraction

### Optimization Strategies
1. **Pre-compile regex patterns**: Define at module level
2. **Early returns**: Short-circuit on non-matching tools
3. **Minimal I/O**: No file system operations needed
4. **Fail-fast**: Return immediately on first match

### Expected Performance
- Processing time: < 10ms per invocation
- Memory usage: < 5MB
- No network I/O
- No disk I/O (except reading stdin)

---

## 14. Rollback Strategy

### If Hook Causes Issues

#### Immediate Rollback
1. **Remove from settings.json**:
   ```json
   // Comment out or remove this section:
   // {
   //   "matcher": "Write|Edit|MultiEdit|Bash",
   //   "hooks": [{"type": "command", "command": "...uv_dependency_blocker.py"}]
   // }
   ```

2. **Restart Claude Code**: Changes take effect immediately

#### Temporary Bypass
Use `.claude/settings.local.json` to override:
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

### Debugging Issues
1. **Enable debug mode**: `claude --debug`
2. **Check hook logs**: Look for errors in stderr
3. **Test hook manually**:
   ```bash
   echo '{"tool_name":"Write","tool_input":{"file_path":"requirements.txt"}}' | \
     uv run .claude/hooks/pre_tools/uv_dependency_blocker.py
   ```

---

## 15. Future Enhancements

### Potential Improvements

#### 1. Configurable File List
Allow users to customize which files are protected:
```json
{
  "hooks": {
    "uv_dependency_blocker": {
      "protected_files": [
        "requirements.txt",
        "pyproject.toml",
        "uv.lock"
      ]
    }
  }
}
```

#### 2. Allow-List Patterns
Support exceptions for specific cases:
```json
{
  "hooks": {
    "uv_dependency_blocker": {
      "allow_patterns": [
        "# This is safe to edit"
      ]
    }
  }
}
```

#### 3. Warning Mode
Provide warnings instead of blocking:
```json
{
  "hooks": {
    "uv_dependency_blocker": {
      "mode": "warn"  // vs "block"
    }
  }
}
```

#### 4. Integration with Git Hooks
Coordinate with pre-commit hooks for double protection

#### 5. Metrics Collection
Track how often the hook blocks operations (for process improvement)

---

## 16. Success Criteria

### Implementation Success
- Hook successfully blocks Write/Edit/MultiEdit on dependency files
- Hook successfully blocks Bash commands modifying dependency files
- Hook provides clear, actionable UV command alternatives
- All unit tests pass (>90% coverage)
- Integration tests pass with mock inputs
- No false positives on legitimate files

### Workflow Success
- Developers naturally use UV commands for dependency management
- No manual edits to dependency files slip through
- Error messages are clear and helpful
- Hook doesn't disrupt legitimate workflows
- Fail-safe behavior prevents blocking Claude Code

### Project Success
- Consistent dependency management across team
- Improved reproducibility with uv.lock
- Reduced dependency conflicts
- Faster dependency operations
- Better version control of dependencies

---

## Appendix A: Complete File List

### Files to Create
1. `.claude/hooks/pre_tools/uv_dependency_blocker.py` - Main hook implementation
2. `.claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py` - Test suite

### Files to Modify
1. `.claude/settings.json` - Add hook configuration

### Files to Reference
1. `.claude/hooks/pre_tools/utils/data_types.py` - Shared type definitions
2. `.claude/hooks/pre_tools/utils/utils.py` - Shared utilities

---

## Appendix B: Example Error Messages

### requirements.txt Edit Blocked
```
📦 Blocked: Direct editing of requirements.txt

Why this is blocked:
  - Manual edits bypass UV's dependency resolution
  - Changes won't be reflected in uv.lock
  - Risk of dependency conflicts
  - No validation of version constraints
  - Breaks project reproducibility

Recommended UV commands:
  - Add package:        uv add <package>
  - Add with version:   uv add "package>=1.0,<2.0"
  - Add dev package:    uv add --dev <package>
  - Remove package:     uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync all:           uv sync
  - Install from lock:  uv sync --frozen

Note: UV uses pyproject.toml for dependency tracking (modern standard)

For migration from requirements.txt:
  1. Review existing requirements.txt
  2. Use: uv add <package1> <package2> ...
  3. Or manually add to pyproject.toml [project.dependencies]
  4. Run: uv lock to generate lock file
  5. Safely delete old requirements.txt after migration
```

### uv.lock Edit Blocked
```
📦 Blocked: Direct editing of uv.lock

Why this is blocked:
  - Manual edits bypass UV's dependency resolution
  - Changes won't be reflected in uv.lock
  - Risk of dependency conflicts
  - No validation of version constraints
  - Breaks project reproducibility

Recommended UV commands:
  - Regenerate lock:    uv lock
  - Update all:         uv lock --upgrade
  - Update package:     uv lock --upgrade-package <package>
  - Sync from lock:     uv sync --frozen

IMPORTANT: Never edit uv.lock manually!
This file is auto-generated by UV and ensures reproducibility.
```

### Bash Command Blocked
```
📦 Blocked: Shell modification of requirements.txt

Command: echo 'django>=4.0' >> requirements.txt

Why this is blocked:
  - Bypasses UV dependency management
  - Won't update uv.lock
  - Risk of syntax errors
  - No validation or conflict resolution

Recommended UV commands:
  - Add package:        uv add <package>
  - Add with version:   uv add "package>=1.0,<2.0"
  - Add dev package:    uv add --dev <package>
  - Remove package:     uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync all:           uv sync
  - Install from lock:  uv sync --frozen

Note: UV uses pyproject.toml for dependency tracking (modern standard)
```

---

## Appendix C: Testing Command Reference

### Run All Tests
```bash
uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py -v
```

### Run with Coverage
```bash
uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py --cov=.claude/hooks/pre_tools --cov-report=html
```

### Run Distributed Tests
```bash
uv run pytest -n auto .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py
```

### Run Specific Test
```bash
uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py::test_is_dependency_file -v
```

### Manual Hook Testing
```bash
# Test Write tool blocking
echo '{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "requirements.txt",
    "content": "requests>=2.28.0"
  }
}' | uv run .claude/hooks/pre_tools/uv_dependency_blocker.py

# Test Bash command blocking
echo '{
  "tool_name": "Bash",
  "tool_input": {
    "command": "echo django >> requirements.txt"
  }
}' | uv run .claude/hooks/pre_tools/uv_dependency_blocker.py

# Test allowed operation
echo '{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "src/main.py",
    "content": "print(hello)"
  }
}' | uv run .claude/hooks/pre_tools/uv_dependency_blocker.py
```

---

**End of Specification**
