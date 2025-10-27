# Temporary Directory Creation Blocker Hook - Specification

## Overview

**Hook Name**: `tmp_creation_blocker.py`

**Category**: `pre_tools`

**Purpose**: Prevent file creation in system temporary directories (`/tmp`, `/var/tmp`, etc.) during Claude Code operations. Instead of creating in system temporary directories, it recommends creating files inside the current project structure. This improves development workflow observability by ensuring all generated files remain within the project directory where they can be easily tracked, version controlled, and managed.

**Event**: PreToolUse

**Matchers**: Write, Edit, MultiEdit, NotebookEdit, Bash

**Version**: 2.0.0

## Objectives

1. **Project Containment**: Keep all development artifacts within the project directory
2. **Observability**: Ensure generated files are visible and trackable
3. **Version Control**: Enable git tracking of all created files
4. **Workflow Clarity**: Prevent scattered files across system temporary directories
5. **Educational**: Teach best practices for file organization in development
6. **Performance**: Minimal overhead with efficient path checking

## Problem Statement

### Current Issues

When Claude Code creates files in system temporary directories:

1. **Lost Visibility**: Files created in `/tmp` are not visible in the project workspace
2. **Version Control Gap**: Cannot track, commit, or version temporary work files
3. **Cleanup Confusion**: System temp files may be auto-deleted, causing confusion
4. **Workflow Disruption**: Developers must manually search `/tmp` to find generated files
5. **Multi-Session Issues**: Temporary files from different sessions can collide
6. **Security Concerns**: Sensitive data may inadvertently persist in world-readable temp directories

### Target Scenarios

This hook prevents:

1. **Write Tool**: `file_path: "/tmp/output.txt"`
2. **Edit Tool**: `file_path: "/var/tmp/config.json"`
3. **NotebookEdit Tool**: `file_path: "/tmp/analysis.ipynb"`
4. **Bash Tool**:
   - `echo "data" > /tmp/file.txt`
   - `touch /tmp/test.py`
   - `cat data > /var/tmp/output.csv`
   - `python script.py > /tmp/results.json`

## System Temporary Directory Patterns

### Primary Patterns (Cross-Platform)

1. **Unix/Linux/macOS**:
   - `/tmp/` - Standard temporary directory
   - `/var/tmp/` - Persistent temporary directory
   - `/private/tmp/` - macOS specific (symlink to /tmp)
   - `/private/var/tmp/` - macOS specific

2. **Environment Variables**:
   - `$TMPDIR` - User-specific temporary directory
   - `$TEMP` - Windows/cross-platform temp
   - `$TMP` - Alternative temp variable

3. **Windows**:
   - `C:\Temp\`
   - `C:\Windows\Temp\`
   - `%TEMP%\`
   - `%TMP%\`

### Detection Strategy

**Path Normalization**:
- Resolve symlinks (e.g., `/tmp` → `/private/tmp` on macOS)
- Expand environment variables (`$TMPDIR`, `$TEMP`)
- Normalize separators (handle both `/` and `\`)
- Convert to absolute paths for comparison

**Core Check**: Does the normalized path start with a known temp directory?

## Technical Architecture

### Input/Output Format

**Input** (via stdin):
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/project",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/tmp/output.txt",
    "content": "data"
  }
}
```

**Output** (to stdout) when blocking:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "📂 Blocked: File creation in system temporary directory\n\nPath: /tmp/output.txt\n\nWhy this is blocked:\n  - Files in /tmp are not visible in your project workspace\n  - Cannot be tracked by git\n  - May be automatically deleted by the system\n  - Scattered outside your project directory\n\nRecommended alternatives:\n  - Create in project: ./tmp/output.txt\n  - Use project subdirectory: ./output/output.txt\n  - Use workspace directory: ./workspace/output.txt\n\nTo create the directory: mkdir -p ./tmp"
  },
  "suppressOutput": true
}
```

**Output** when allowing:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Path is not in system temporary directory"
  }
}
```

### Dependencies

**Python Version**: >= 3.12

**UV Script Metadata**:
```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**External Packages**: None (standard library only)

**Shared Utilities**:
- `.claude/hooks/pre_tools/utils/utils.py` - `parse_hook_input()`, `output_decision()`
- `.claude/hooks/pre_tools/utils/data_types.py` - `ToolInput`, `HookOutput`

### Code Structure

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Temporary Directory Creation Blocker - PreToolUse Hook
=======================================================
Prevents file creation in system temporary directories during Claude Code operations.

This hook ensures all generated files remain within the project directory for better
observability, version control, and workflow management.

Blocked Directories:
- /tmp/
- /var/tmp/
- $TMPDIR/
- /private/tmp/ (macOS)
- /private/var/tmp/ (macOS)
- C:\Temp\ (Windows)
- %TEMP%\ (Windows)

Usage:
    This hook is automatically invoked by Claude Code before file operations.
    It receives JSON input via stdin and outputs JSON permission decisions.

Dependencies:
    - Python >= 3.12
    - No external packages (standard library only)
    - Shared utilities from .claude/hooks/pre_tools/utils/

Exit Codes:
    0: Success (decision output via stdout)

Author: Claude Code Hook Expert
Version: 2.0.0
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Temporary Directory Definitions ============

# Known system temporary directory paths (normalized, absolute)
SYSTEM_TEMP_DIRS = [
    "/tmp",
    "/var/tmp",
    "/private/tmp",
    "/private/var/tmp",
]

# Windows temporary directories
WINDOWS_TEMP_DIRS = [
    r"C:\Temp",
    r"C:\Windows\Temp",
]

# Environment variable names that point to temp directories
TEMP_ENV_VARS = ["TMPDIR", "TEMP", "TMP"]


# ============ Path Detection Functions ============

def get_all_temp_directories() -> list[str]:
    """
    Get all system temporary directories for the current platform.

    Returns:
        List of normalized absolute paths to temporary directories
    """
    temp_dirs = []

    # Add Unix/Linux/macOS standard paths
    if os.name != 'nt':  # Not Windows
        temp_dirs.extend(SYSTEM_TEMP_DIRS)

    # Add Windows paths
    if os.name == 'nt':
        temp_dirs.extend(WINDOWS_TEMP_DIRS)

    # Add directories from environment variables
    for env_var in TEMP_ENV_VARS:
        env_value = os.environ.get(env_var)
        if env_value and os.path.isdir(env_value):
            # Normalize and resolve symlinks
            try:
                resolved = str(Path(env_value).resolve())
                if resolved not in temp_dirs:
                    temp_dirs.append(resolved)
            except (OSError, ValueError):
                # Skip if path resolution fails
                pass

    return temp_dirs


def check_path_is_temp_directory(file_path: str) -> bool:
    """
    Check if a file path is within a system temporary directory.

    Args:
        file_path: Path to check (can be relative or absolute)

    Returns:
        True if path is in a temporary directory, False otherwise
    """
    if not file_path:
        return False

    try:
        # Convert to absolute path
        abs_path = os.path.abspath(file_path)

        # Normalize path separators
        normalized_path = os.path.normpath(abs_path)

        # Get all temp directories for current platform
        temp_dirs = get_all_temp_directories()

        # Check if path starts with any temp directory
        for temp_dir in temp_dirs:
            temp_dir_norm = os.path.normpath(temp_dir)

            # Check if file is within temp directory
            # Use os.path.commonpath to ensure proper directory boundary checking
            try:
                common = os.path.commonpath([normalized_path, temp_dir_norm])
                if common == temp_dir_norm:
                    return True
            except ValueError:
                # Paths on different drives (Windows)
                continue

    except (OSError, ValueError):
        # If path resolution fails, allow operation (fail-safe)
        return False

    return False


def extract_bash_output_paths(command: str) -> list[str]:
    """
    Extract file paths from bash commands that create/write files.

    Handles:
    - Redirects: > file, >> file, 2> file
    - Touch: touch file
    - Echo: echo text > file
    - Cat: cat input > output
    - Tee: command | tee file

    Args:
        command: Bash command string

    Returns:
        List of file paths found in the command
    """
    paths = []

    # Pattern 1: Redirect operators (>, >>, 2>, &>)
    # Matches: echo "text" > /tmp/file.txt
    redirect_pattern = re.compile(r'(?:>>?|2>>?|&>>?)\s+([^\s;|&<>]+)')
    paths.extend(redirect_pattern.findall(command))

    # Pattern 2: Touch command
    # Matches: touch /tmp/file.txt
    touch_pattern = re.compile(r'\btouch\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)')
    paths.extend(touch_pattern.findall(command))

    # Pattern 3: Tee command
    # Matches: command | tee /tmp/file.txt
    tee_pattern = re.compile(r'\btee\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)')
    paths.extend(tee_pattern.findall(command))

    return paths


def generate_project_alternative(temp_path: str, project_dir: str) -> str:
    """
    Generate a project-relative alternative path suggestion.

    Args:
        temp_path: Original temporary directory path
        project_dir: Current project directory

    Returns:
        Suggested project-relative path
    """
    # Extract filename from temp path
    filename = os.path.basename(temp_path)

    # Suggest creating in ./tmp/ subdirectory
    return f"./tmp/{filename}"


# ============ Main Validation ============

def validate_file_path(file_path: str, project_dir: str) -> Optional[str]:
    """
    Validate that a file path is not in a system temporary directory.

    Args:
        file_path: Path to validate
        project_dir: Current project directory

    Returns:
        Error message if invalid, None if valid
    """
    if check_path_is_temp_directory(file_path):
        alternative = generate_project_alternative(file_path, project_dir)

        return f"""📂 Blocked: File creation in system temporary directory

Path: {file_path}

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: {alternative}
  - Use project subdirectory: ./output/{os.path.basename(file_path)}
  - Use workspace directory: ./workspace/{os.path.basename(file_path)}

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable."""

    return None


def main() -> None:
    """
    Main entry point for temporary directory creation blocker hook.

    Reads JSON input from stdin, validates file paths, and outputs
    permission decisions. Implements fail-safe behavior on errors.

    Exit Codes:
        0: Always (decision output via stdout)
    """
    try:
        # Parse input using shared utility
        parsed = parse_hook_input()
        if not parsed:
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = parsed

        # Get current project directory
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Handle file-based tools (Write, Edit, MultiEdit, NotebookEdit)
        if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            file_path = tool_input.get("file_path", "")
            if not file_path:
                output_decision("allow", "No file path to validate")
                return

            error = validate_file_path(file_path, project_dir)
            if error:
                output_decision("deny", error, suppress_output=True)
            else:
                output_decision("allow", "Path is not in system temporary directory")

        # Handle Bash commands
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if not command:
                output_decision("allow", "No command to validate")
                return

            # Extract file paths from bash command
            paths = extract_bash_output_paths(command)

            # Validate each extracted path
            for path in paths:
                error = validate_file_path(path, project_dir)
                if error:
                    # Add command context to error message
                    full_message = f"{error}\n\nCommand: {command}"
                    output_decision("deny", full_message, suppress_output=True)
                    return

            output_decision("allow", "Command does not write to temporary directories")

        else:
            # Other tools - allow
            output_decision("allow", f"Tool '{tool_name}' not monitored by this hook")

    except Exception as e:
        # Fail-safe: allow operation on error
        print(f"Temporary directory blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
```

## Testing Strategy

### Test Infrastructure

**Framework**: pytest >= 7.0.0

**Test File**: `.claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py`

**Test Categories**:

1. **Path Detection Tests** - Test `check_path_is_temp_directory()`
2. **Bash Parsing Tests** - Test `extract_bash_output_paths()`
3. **Integration Tests** - Test full hook execution via `main()`
4. **Cross-Platform Tests** - Test Windows vs Unix path handling
5. **Edge Cases** - Test symlinks, environment variables, relative paths

### Test Cases

#### 1. Basic Temporary Directory Detection

```python
def test_detect_tmp_directory():
    """Test detection of /tmp paths."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/tmp/file.txt") is True

def test_detect_var_tmp_directory():
    """Test detection of /var/tmp paths."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/var/tmp/data.json") is True

def test_detect_private_tmp_directory():
    """Test detection of /private/tmp paths (macOS)."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/private/tmp/output.txt") is True

def test_allow_project_directory():
    """Test that project directories are allowed."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/project/tmp/file.txt") is False
    assert check_path_is_temp_directory("/home/user/code/output.txt") is False
    assert check_path_is_temp_directory("./local/temp.txt") is False
```

#### 2. Relative Path Handling

```python
def test_allow_relative_tmp_in_project():
    """Test that ./tmp/ in project is allowed (not system /tmp)."""
    from tmp_creation_blocker import check_path_is_temp_directory

    # Relative path to project's tmp directory
    assert check_path_is_temp_directory("./tmp/file.txt") is False
    assert check_path_is_temp_directory("tmp/file.txt") is False
```

#### 3. Bash Command Parsing

```python
def test_extract_redirect_path():
    """Test extracting path from redirect operator."""
    from tmp_creation_blocker import extract_bash_output_paths

    paths = extract_bash_output_paths("echo test > /tmp/output.txt")
    assert "/tmp/output.txt" in paths

def test_extract_append_redirect():
    """Test extracting path from append redirect."""
    from tmp_creation_blocker import extract_bash_output_paths

    paths = extract_bash_output_paths("echo test >> /var/tmp/log.txt")
    assert "/var/tmp/log.txt" in paths

def test_extract_touch_path():
    """Test extracting path from touch command."""
    from tmp_creation_blocker import extract_bash_output_paths

    paths = extract_bash_output_paths("touch /tmp/newfile.txt")
    assert "/tmp/newfile.txt" in paths

def test_extract_tee_path():
    """Test extracting path from tee command."""
    from tmp_creation_blocker import extract_bash_output_paths

    paths = extract_bash_output_paths("echo data | tee /tmp/output.txt")
    assert "/tmp/output.txt" in paths

def test_extract_multiple_paths():
    """Test extracting multiple paths from one command."""
    from tmp_creation_blocker import extract_bash_output_paths

    paths = extract_bash_output_paths("echo a > /tmp/a.txt && echo b > /tmp/b.txt")
    assert "/tmp/a.txt" in paths
    assert "/tmp/b.txt" in paths
```

#### 4. Integration Tests - Write Tool

```python
def test_hook_blocks_write_to_tmp():
    """Test full hook execution blocking Write to /tmp."""
    from tmp_creation_blocker import main
    import json
    from io import StringIO
    from unittest.mock import patch
    import pytest

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt", "content": "hello"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
            assert "/tmp/test.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]

def test_hook_allows_write_to_project():
    """Test hook allows Write to project directory."""
    from tmp_creation_blocker import main
    import json
    from io import StringIO
    from unittest.mock import patch
    import pytest

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/project/output.txt", "content": "hello"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
```

#### 5. Integration Tests - Bash Tool

```python
def test_hook_blocks_bash_redirect_to_tmp():
    """Test hook blocks Bash redirect to /tmp."""
    from tmp_creation_blocker import main
    import json
    from io import StringIO
    from unittest.mock import patch
    import pytest

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test > /tmp/output.txt"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
            assert "/tmp/output.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]

def test_hook_allows_bash_redirect_to_project():
    """Test hook allows Bash redirect to project directory."""
    from tmp_creation_blocker import main
    import json
    from io import StringIO
    from unittest.mock import patch
    import pytest

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test > ./output.txt"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
```

#### 6. Integration Tests - NotebookEdit Tool

```python
def test_hook_blocks_notebook_edit_to_tmp():
    """Test hook blocks NotebookEdit to /tmp."""
    from tmp_creation_blocker import main
    import json
    from io import StringIO
    from unittest.mock import patch
    import pytest

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "NotebookEdit",
        "tool_input": {"file_path": "/tmp/notebook.ipynb", "new_source": "code"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
```

#### 7. Edge Cases

```python
def test_handle_empty_file_path():
    """Test handling of empty file path."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("") is False

def test_handle_none_file_path():
    """Test handling of None file path."""
    from tmp_creation_blocker import validate_file_path

    # Should not crash
    result = validate_file_path("", "/project")
    assert result is None  # Allow empty paths

def test_handle_invalid_path():
    """Test handling of invalid path that cannot be resolved."""
    from tmp_creation_blocker import check_path_is_temp_directory

    # Should not crash, should fail-safe to False
    assert check_path_is_temp_directory("\x00invalid\x00") is False
```

### Running Tests

```bash
# Run all tests
uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py -v

# Run with coverage
uv run pytest --cov=.claude/hooks/pre_tools/tmp_creation_blocker.py \
    .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py

# Run distributed (parallel)
uv run pytest -n auto .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py
```

## Configuration

### settings.json Entry

The hook will NOT require explicit configuration in settings.json. This is because:

1. The existing `pre_tool_use.py` dispatcher already exists
2. Individual pre_tools hooks are imported and executed by the dispatcher
3. No direct hook configuration needed in settings.json for pre_tools category hooks

The hook integrates into the existing pre_tools infrastructure automatically when placed in `.claude/hooks/pre_tools/tmp_creation_blocker.py`.

### Integration with Existing Hooks

The tmp_creation_blocker will run alongside:
- `universal_hook_logger.py` (universal matcher via main hook system)
- `destructive_command_blocker.py` (Bash matcher via pre_tools)
- `file_naming_enforcer.py` (Write/Edit matcher via pre_tools)
- `sensitive_file_access_validator.py` (Read/Write/Edit matcher via pre_tools)
- Other pre_tools hooks

**Execution Order**: All pre_tools hooks run in sequence. If any hook denies, the operation is blocked.

## Security Considerations

### Fail-Safe Behavior

- **Error Handling**: All exceptions caught and logged
- **Default Action**: Allow on error (fail-safe, not fail-secure)
- **Rationale**: Prevent blocking legitimate work if path resolution fails

### Path Resolution Safety

- **Symlink Resolution**: Uses `Path.resolve()` to handle symlinks
- **Normalization**: Properly handles path separators and case sensitivity
- **Cross-Platform**: Works on Unix, macOS, and Windows
- **Environment Variables**: Safely expands `$TMPDIR`, `$TEMP`, `$TMP`

### False Positive Mitigation

**Risk**: Blocking legitimate uses of "./tmp" in project

**Mitigations**:
1. Distinguish absolute vs relative paths
2. Only block system temporary directories
3. Allow project-local "tmp" directories
4. Clear error messages explaining why blocked

### False Negative Risks

**Risk**: Missing temporary directory variants

**Mitigations**:
1. Comprehensive list of temp directory patterns
2. Environment variable expansion
3. Symlink resolution
4. Regular updates based on user feedback

## Performance Considerations

### Path Resolution Overhead

- **Typical Case**: < 1ms per file path check
- **Worst Case**: < 5ms for complex symlink chains
- **Caching**: Temp directory list built once per invocation

### Regex Performance

- **Bash Parsing**: Compiled regex patterns
- **Pattern Matching**: Simple findall operations
- **Minimal Backtracking**: Efficient patterns

### Expected Overhead

- **File Tools**: 1-2ms per invocation
- **Bash Tools**: 2-5ms per invocation (due to path extraction)
- **Overall Impact**: Negligible in typical development workflow

## Error Handling

### Error Categories

1. **Path Resolution Errors**: Invalid paths, permission denied
2. **Environment Errors**: Missing or invalid environment variables
3. **Parsing Errors**: Invalid JSON input
4. **Unexpected Exceptions**: Catch-all for unknown errors

### Error Responses

All errors result in:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Hook error (fail-safe): {error_message}"
  }
}
```

Error details also written to stderr for debugging.

## Maintenance and Updates

### Adding New Temporary Directory Patterns

1. **Identify Pattern**: Discover new temp directory location
2. **Add to Constants**: Update `SYSTEM_TEMP_DIRS` or `WINDOWS_TEMP_DIRS`
3. **Test**: Add test cases for new pattern
4. **Document**: Update this specification

### Pattern Update Process

1. Monitor hook logs via `universal_hook_logger`
2. Collect false positives/negatives
3. Refine path detection logic
4. Test thoroughly
5. Deploy updated hook

## User Experience

### Educational Messages

When blocking, provide:
1. **Clear Explanation**: Why the path is problematic
2. **Specific Alternatives**: Suggest project-relative paths
3. **Setup Commands**: Show how to create project directories
4. **Context**: Include original file path and command

### Example Message

```
📂 Blocked: File creation in system temporary directory

Path: /tmp/output.txt

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: ./tmp/output.txt
  - Use project subdirectory: ./output/output.txt
  - Use workspace directory: ./workspace/output.txt

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable.
```

## Rollback Strategy

If hook causes issues:

1. **Disable Hook**: Remove from pre_tools directory
2. **Restart Session**: Use `/clear` to reset
3. **Report Issue**: Document problem for investigation
4. **Re-enable**: After fix is deployed

## Success Metrics

1. **Effectiveness**: Files stay in project directory (observable via git status)
2. **Accuracy**: False positive rate < 1%
3. **Performance**: Overhead < 5ms per operation
4. **User Satisfaction**: Positive feedback on workflow clarity

## Future Enhancements

### Phase 2 Features

1. **Smart Suggestions**: Analyze file type and suggest appropriate project directory
2. **Auto-Create Directories**: Offer to create `./tmp` directory automatically
3. **Whitelist**: Allow specific temp paths with user confirmation
4. **Configuration**: Per-project settings for allowed temp directories
5. **Integration with .gitignore**: Auto-add project tmp/ to .gitignore

### Integration Opportunities

1. **Context Injection**: Remind Claude to use project directories in responses
2. **Workflow Templates**: Suggest standard directory structures (./tmp, ./output, ./workspace)
3. **Git Integration**: Auto-stage files in project tmp/ for easy tracking

## Appendix A: Temporary Directory Reference

### Unix/Linux Temporary Directories

```
/tmp/                   - Standard temporary directory
/var/tmp/               - Persistent temporary directory
$TMPDIR/                - User-specific temporary directory
```

### macOS Temporary Directories

```
/tmp/                   - Symlink to /private/tmp
/var/tmp/               - Symlink to /private/var/tmp
/private/tmp/           - Actual temporary directory
/private/var/tmp/       - Persistent temporary directory
$TMPDIR/                - User-specific (usually /var/folders/...)
```

### Windows Temporary Directories

```
C:\Temp\                - Common temporary directory
C:\Windows\Temp\        - System temporary directory
%TEMP%\                 - User temporary directory
%TMP%\                  - Alternative temp variable
```

## Appendix B: Example Blocked Operations

### Will Block

```bash
# Write tool
file_path: "/tmp/output.txt"
file_path: "/var/tmp/data.json"

# Bash tool
echo "data" > /tmp/file.txt
touch /tmp/test.py
cat data > /var/tmp/output.csv
python script.py > /tmp/results.json
command | tee /tmp/log.txt

# NotebookEdit tool
file_path: "/tmp/analysis.ipynb"
```

### Will Allow

```bash
# Write tool
file_path: "./tmp/output.txt"
file_path: "/project/tmp/data.json"
file_path: "./workspace/results.txt"

# Bash tool
echo "data" > ./tmp/file.txt
touch ./output/test.py
cat data > ./workspace/output.csv
python script.py > ./results.json
command | tee ./log.txt

# Relative project paths
file_path: "tmp/file.txt"  # Relative to project, not /tmp
file_path: "./temporary/data.txt"  # Project subdirectory
```

## Appendix C: Testing Checklist

- [ ] Path detection works for /tmp
- [ ] Path detection works for /var/tmp
- [ ] Path detection works for /private/tmp (macOS)
- [ ] Path detection works for environment variables ($TMPDIR)
- [ ] Relative paths like "./tmp" are allowed
- [ ] Bash redirect parsing extracts paths correctly
- [ ] Bash touch command parsing works
- [ ] Bash tee command parsing works
- [ ] Write tool integration test passes
- [ ] Edit tool integration test passes
- [ ] NotebookEdit tool integration test passes
- [ ] Bash tool integration test passes
- [ ] Error handling prevents crashes
- [ ] Empty/None paths handled gracefully
- [ ] Invalid paths fail-safe to allow
- [ ] Cross-platform path normalization works
- [ ] Test coverage >= 95%

## Version History

- **2.0.0** (2025-10-28): Complete specification with enhanced detection, bash parsing, and comprehensive testing
- **1.0.0** (Previous): Initial implementation (refactored)
