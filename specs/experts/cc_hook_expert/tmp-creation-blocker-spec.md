# Temporary Directory Creation Blocker - Hook Specification

## 1. Overview

### Purpose
The `tmp_creation_blocker.py` hook prevents file creation in system temporary directories (`/tmp`, `/var/tmp`, etc.) during Claude Code operations. This improves development workflow observability by ensuring all generated files remain within the project directory where they can be easily tracked, version controlled, and managed.

### Problem Statement
Claude Code frequently creates temporary files in system temp directories (`/tmp`, `/var/tmp`, etc.) during development operations. These files:
- Are difficult to locate and inspect during debugging
- Clutter system temp directories requiring manual cleanup
- Cannot be easily version controlled or shared with team members
- May accumulate over time causing disk space issues
- Are hidden from standard project file monitoring tools

### Solution
Intercept file creation operations **before** execution and block any attempts to create files in system temporary directories. Provide clear guidance to redirect file creation to project-local temporary directories instead.

## 2. Hook Configuration

### Event Type
**PreToolUse** - Intercepts tool execution before file operations occur

### Tool Matchers
```json
"matcher": "Write|NotebookEdit|Bash"
```

**Rationale:**
- `Write` - Primary file creation tool
- `NotebookEdit` - Can create/modify Jupyter notebook files
- `Bash` - Can execute shell commands that create files (e.g., `touch`, `echo >`, `cat >`)

### Hook Registration
Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py"
          }
        ]
      }
    ]
  }
}
```

**Note:** This hook will coexist with other PreToolUse hooks targeting the same tools.

## 3. Technical Architecture

### Input Schema

Receives JSON via stdin conforming to PreToolUse event structure:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/tmp/example.txt",
    "content": "..."
  }
}
```

**Tool-Specific Input Fields:**
- **Write/NotebookEdit**: `file_path` (string)
- **Bash**: `command` (string)

### Output Schema

Returns JSON with permission decision:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked file creation in system temp directory.\nPath: /tmp/example.txt\nPolicy: Never create files in system temp paths for better observability.\nAlternative: Use project directory instead:\n  - Create: /Users/ringo/Desktop/claude-setup-python/temp/example.txt\n  - Then add 'temp/' to .gitignore if needed\n"
  },
  "suppressOutput": true
}
```

**Permission Decision Values:**
- `"allow"` - File creation is not in temp directory, proceed
- `"deny"` - File creation is in temp directory, block with helpful message
- `"ask"` - Not used in this hook (could be added for edge cases)

### Exit Codes
Always exits with `0` (success) since JSON output controls the decision.

## 4. Validation Rules

### Blocked Path Patterns

#### Unix/Linux/macOS Paths
```python
TEMP_DIRECTORIES = [
    "/tmp/",
    "/var/tmp/",
    "/private/tmp/",      # macOS specific
    "/dev/shm/",          # Shared memory temp
    "/run/shm/",          # Alternative shared memory location
]
```

#### Windows Paths (if applicable)
```python
WINDOWS_TEMP_PATTERNS = [
    r"C:\Windows\Temp",
    r"C:\Temp",
    r"C:\TMP",
    r"%TEMP%",
    r"%TMP%",
]
```

### Detection Logic

#### For Write/NotebookEdit Tools
1. Extract `file_path` from `tool_input`
2. Normalize path (resolve symlinks, handle relative paths)
3. Check if normalized path starts with any blocked temp directory
4. If match found → Deny with alternative suggestion
5. Otherwise → Allow

#### For Bash Tool
1. Extract `command` from `tool_input`
2. Parse command for file creation operations:
   - Redirections: `>`, `>>`
   - Commands: `touch`, `cat >`, `echo >`, `tee`, `cp`, `mv`
3. Extract file paths from command using regex patterns
4. Check each path against blocked temp directories
5. If any match found → Deny with command modification suggestion
6. Otherwise → Allow

### Path Normalization
```python
import os
from pathlib import Path

def normalize_path(file_path: str) -> str:
    """Normalize path for reliable comparison."""
    # Resolve relative paths using CLAUDE_PROJECT_DIR
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # Convert to absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.join(project_dir, file_path)

    # Resolve symlinks and normalize
    return str(Path(file_path).resolve())
```

## 5. Error Messages and Suggestions

### Denial Message Format
```
🚫 Blocked file creation in system temp directory.
Path: {original_path}
Policy: Never create files in system temp paths for better observability.
Alternative: Use project directory instead:
  - Create: {suggested_project_path}
  - Then add 'temp/' to .gitignore if needed
```

### Alternative Path Suggestion
```python
def suggest_alternative_path(blocked_path: str) -> str:
    """Generate project-local alternative path."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    filename = os.path.basename(blocked_path)

    # Suggest project-local temp directory
    alternative = os.path.join(project_dir, "temp", filename)
    return alternative
```

## 6. Code Structure

### File Location
```
.claude/hooks/pre_tools/tmp_creation_blocker.py
```

### Code Organization
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""
Temporary Directory Creation Blocker - PreToolUse Hook
======================================================
Prevents file creation in system temp directories for better observability.
"""

import os
import re
from pathlib import Path

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision
    from utils.data_types import ToolInput


def main() -> None:
    """Main entry point."""
    # [Implementation]
    pass


def validate_file_creation(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Validate file creation operation.

    Returns:
        Violation message if temp directory detected, None otherwise
    """
    # [Implementation]
    pass


def check_path_is_temp_directory(file_path: str) -> bool:
    """Check if path is in a temp directory."""
    # [Implementation]
    pass


def suggest_alternative_path(blocked_path: str) -> str:
    """Generate project-local alternative path."""
    # [Implementation]
    pass


def check_bash_temp_file_creation(command: str) -> str | None:
    """Check bash command for temp file creation."""
    # [Implementation]
    pass


if __name__ == "__main__":
    main()
```

## 7. Dependencies

### Python Version
- **Requires:** Python 3.12+
- **Rationale:** Uses modern type hints (`str | None` union syntax)

### External Packages
- **None** - Only uses Python standard library
  - `os` - Environment variable access, path operations
  - `re` - Command parsing with regex
  - `pathlib` - Path normalization and manipulation
  - `json` - Input/output serialization (via shared utils)
  - `sys` - stdin/stdout/exit (via shared utils)

### Shared Utilities
```python
from .utils.utils import parse_hook_input, output_decision
from .utils.data_types import ToolInput
```

**Benefits of Code Reuse:**
- Consistent input parsing across all PreToolUse hooks
- Standardized JSON output format
- Reduced code duplication (~30-35% reduction)
- Centralized bug fixes and improvements

## 8. Testing Strategy

### Test File Location
```
.claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py
```

### Test Categories

#### 1. Unit Tests - Path Detection
```python
def test_detect_tmp_directory():
    """Test detection of /tmp paths."""
    assert check_path_is_temp_directory("/tmp/file.txt") is True
    assert check_path_is_temp_directory("/var/tmp/data.json") is True
    assert check_path_is_temp_directory("/private/tmp/test.py") is True
    assert check_path_is_temp_directory("/project/temp/file.txt") is False

def test_path_normalization():
    """Test path normalization handles relative paths."""
    # Setup CLAUDE_PROJECT_DIR
    os.environ["CLAUDE_PROJECT_DIR"] = "/project"

    # Relative path to temp should be blocked
    assert check_path_is_temp_directory("../../../tmp/file.txt") is True

    # Project-local relative path should be allowed
    assert check_path_is_temp_directory("./temp/file.txt") is False
```

#### 2. Unit Tests - Bash Command Parsing
```python
def test_detect_bash_redirection_to_tmp():
    """Test detection of bash redirections to temp."""
    violations = check_bash_temp_file_creation("echo 'test' > /tmp/output.txt")
    assert violations is not None
    assert "/tmp/output.txt" in violations

def test_detect_bash_touch_in_tmp():
    """Test detection of touch command in temp."""
    violations = check_bash_temp_file_creation("touch /var/tmp/tempfile")
    assert violations is not None

def test_allow_bash_normal_operations():
    """Test bash commands with no temp file creation are allowed."""
    violations = check_bash_temp_file_creation("ls -la /tmp")
    assert violations is None
```

#### 3. Integration Tests - Full Hook Execution
```python
def test_hook_blocks_write_to_tmp():
    """Test full hook execution blocking Write to /tmp."""
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

def test_hook_allows_project_directory_write():
    """Test hook allows writing to project directory."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/project/temp/test.txt", "content": "hello"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
```

### Running Tests
```bash
# Run all tests for this hook
uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py -v

# Run with coverage
uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py --cov=.claude/hooks/pre_tools --cov-report=html
```

## 9. Security Considerations

### Input Validation
- **Path Traversal**: Normalize all paths to prevent `../../` bypasses
- **Symlink Resolution**: Resolve symlinks to detect hidden temp directory references
- **Command Injection**: Use safe parsing for bash commands, no shell execution
- **Environment Variables**: Safely handle `$TMPDIR`, `$TEMP`, `$TMP` in paths

### Safe Failure Modes
- **Invalid Input**: Allow operation (fail open) with debug logging
- **Parsing Errors**: Allow operation to avoid blocking valid workflows
- **Missing Environment**: Use `os.getcwd()` fallback if `CLAUDE_PROJECT_DIR` unavailable

### Defense in Depth
```python
def safe_normalize_path(file_path: str) -> str:
    """Safely normalize path with multiple security checks."""
    try:
        # Get project directory with fallback
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Resolve relative paths
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_dir, file_path)

        # Resolve symlinks (prevents symlink bypass)
        normalized = str(Path(file_path).resolve())

        return normalized
    except Exception as e:
        # Log error but allow operation (fail open)
        print(f"Path normalization error: {e}", file=sys.stderr)
        return file_path  # Return original path
```

## 10. Error Handling

### Graceful Degradation
```python
def main() -> None:
    """Main entry point with comprehensive error handling."""
    try:
        # Parse input
        parsed = parse_hook_input()
        if not parsed:
            # Invalid input - allow operation
            output_decision("allow", "Invalid input format, allowing operation")
            return

        tool_name, tool_input = parsed

        # Validate file creation
        violation = validate_file_creation(tool_name, tool_input)

        if violation:
            output_decision("deny", violation, suppress_output=True)
        else:
            output_decision("allow", "File operation is safe")

    except Exception as e:
        # Unexpected error - fail open (allow) to avoid blocking workflows
        output_decision("allow", f"Hook error (allowing operation): {str(e)}")
```

### Edge Cases
1. **Empty file_path**: Allow (not a file creation operation)
2. **Missing tool_input**: Allow (invalid invocation)
3. **Non-existent parent directory**: Still block if in temp directory
4. **Relative paths**: Normalize relative to `CLAUDE_PROJECT_DIR`
5. **Symlinks pointing to /tmp**: Block (detected via normalization)
6. **Environment variable expansion**: Expand `$TMPDIR` → Check if it's temp

## 11. Performance Considerations

### Optimization Strategies
- **Early Exit**: Return immediately for non-file tools
- **Compiled Regex**: Pre-compile bash command patterns
- **Path Caching**: Cache normalized paths for repeated checks (if needed)
- **Minimal I/O**: No disk operations, only path string analysis

### Expected Performance
- **Execution Time**: < 50ms for typical operations
- **Memory Usage**: < 5MB (minimal allocations)
- **CPU Impact**: Negligible (string operations only)

### Performance Measurement
```python
import time

def main() -> None:
    start_time = time.time()

    # ... hook logic ...

    elapsed = (time.time() - start_time) * 1000
    # Log to stderr for debugging (not shown to user)
    print(f"Hook execution time: {elapsed:.2f}ms", file=sys.stderr)
```

## 12. Integration Considerations

### Coexistence with Other Hooks
This hook will run alongside existing PreToolUse hooks:
- `universal_hook_logger.py` - Logging (no conflicts)
- `sensitive_file_access_validator.py` - Security validation (complementary)
- `uv_workflow_enforcer.py` - UV workflow enforcement (no overlap)

**Execution Order**: Hooks run in **parallel** (independent execution), so order doesn't matter.

### Configuration Merge Strategy
Add new hook entry to existing PreToolUse matcher:

**Option 1: Separate Matcher Entry (Recommended)**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Write|Edit|TodoWrite|Bash",
        "hooks": [
          {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/sensitive_file_access_validator.py"}
        ]
      },
      {
        "matcher": "Write|NotebookEdit|Bash",
        "hooks": [
          {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py"}
        ]
      }
    ]
  }
}
```

**Option 2: Combined Matcher Entry**
```json
{
  "matcher": "Read|Write|Edit|TodoWrite|NotebookEdit|Bash",
  "hooks": [
    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/sensitive_file_access_validator.py"},
    {"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py"}
  ]
}
```

### Session Environment Variables
The hook respects Claude Code environment:
- `CLAUDE_PROJECT_DIR` - Project root directory (required for path normalization)
- `CLAUDE_CODE_REMOTE` - Indicates web environment (may affect path detection)

## 13. Rollback Strategy

### Disabling the Hook
**Temporary Disable (Testing):**
1. Comment out hook entry in `.claude/settings.json`
2. Or use `.claude/settings.local.json` override:
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Permanent Removal:**
1. Remove hook entry from `.claude/settings.json`
2. Delete hook file: `.claude/hooks/pre_tools/tmp_creation_blocker.py`
3. Delete test file: `.claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py`

### Monitoring During Rollout
1. Check hook logs via universal logger
2. Monitor for false positives (legitimate temp usage)
3. Review blocked operations in session transcript
4. Gather user feedback on suggested alternatives

## 14. Future Enhancements

### Potential Improvements
1. **Configurable Temp Directories**
   - Allow users to specify additional blocked paths
   - Support per-project temp directory allowlist

2. **Smart Alternative Suggestions**
   - Analyze file purpose from content/name
   - Suggest appropriate project subdirectory (e.g., `cache/`, `build/`, `temp/`)

3. **Automatic Directory Creation**
   - Auto-create project-local temp directory
   - Add to `.gitignore` automatically

4. **Metrics and Analytics**
   - Track blocked operations frequency
   - Identify most common temp usage patterns
   - Report via hook logs

5. **Ask Mode for Edge Cases**
   - Allow user to override for specific operations
   - Remember user decisions per session

### Configuration Schema (Future)
```json
{
  "hooks": {
    "tmp_creation_blocker": {
      "blocked_paths": ["/tmp", "/var/tmp"],
      "allowed_exceptions": ["*.log"],
      "auto_create_project_temp": true,
      "auto_gitignore": true
    }
  }
}
```

## 15. Documentation and Communication

### User-Facing Documentation
Create `.claude/hooks/pre_tools/README.md` section:

```markdown
### tmp_creation_blocker.py

**Purpose:** Prevents file creation in system temp directories.

**Why:** System temp directories clutter your system and make debugging harder.
All project files should live in the project directory for better observability.

**Blocked Paths:**
- `/tmp/`
- `/var/tmp/`
- `/private/tmp/` (macOS)

**Alternative:** Use project-local temp directory:
```bash
mkdir -p temp/
echo "temp/" >> .gitignore  # If needed
```

**How to Disable:** Comment out the hook in `.claude/settings.json`
```

### Developer Documentation
- Add JSDoc-style comments to all functions
- Include examples in docstrings
- Reference this spec in file header

## 16. Success Criteria

### Functional Requirements
- ✅ Block all file creation operations in `/tmp/*`
- ✅ Block all file creation operations in `/var/tmp/*`
- ✅ Suggest project-local alternative paths
- ✅ Allow normal project directory file operations
- ✅ Handle Write, NotebookEdit, and Bash tools
- ✅ Parse bash commands for file creation operations

### Non-Functional Requirements
- ✅ Execution time < 50ms
- ✅ Zero false negatives (all temp operations blocked)
- ✅ Minimal false positives (< 1% legitimate operations blocked)
- ✅ Clear, actionable error messages
- ✅ 100% test coverage on core logic
- ✅ No external dependencies

### User Experience
- ✅ Clear explanation why operation was blocked
- ✅ Actionable alternative path suggested
- ✅ No disruption to normal workflows
- ✅ Suppressible output to avoid transcript clutter

## 17. Implementation Checklist

### Phase 1: Core Development
- [ ] Create `tmp_creation_blocker.py` with UV script metadata
- [ ] Implement `main()` function with error handling
- [ ] Implement `check_path_is_temp_directory()` for path validation
- [ ] Implement `suggest_alternative_path()` for alternatives
- [ ] Implement `check_bash_temp_file_creation()` for bash parsing
- [ ] Add comprehensive docstrings and type hints

### Phase 2: Testing
- [ ] Create `test_tmp_creation_blocker.py` in tests directory
- [ ] Write unit tests for path detection (10+ test cases)
- [ ] Write unit tests for bash command parsing (10+ test cases)
- [ ] Write integration tests for full hook execution (5+ test cases)
- [ ] Run tests and verify 100% pass rate
- [ ] Verify test coverage > 90%

### Phase 3: Integration
- [ ] Update `.claude/settings.json` with hook configuration
- [ ] Test hook with real Claude Code session
- [ ] Verify coexistence with other PreToolUse hooks
- [ ] Test on macOS, Linux (if available)
- [ ] Document any platform-specific behavior

### Phase 4: Documentation
- [ ] Add section to `.claude/hooks/pre_tools/README.md`
- [ ] Create usage examples
- [ ] Document configuration options
- [ ] Update this spec with lessons learned

### Phase 5: Validation
- [ ] Manual testing with various file operations
- [ ] Performance benchmarking (< 50ms target)
- [ ] Security review (path traversal, injection)
- [ ] User acceptance testing
- [ ] Final adjustments based on feedback

## 18. Appendix

### Example Scenarios

#### Scenario 1: Write Tool to /tmp
**Input:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/tmp/debug_output.log",
    "content": "Debug information..."
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked file creation in system temp directory.\nPath: /tmp/debug_output.log\nPolicy: Never create files in system temp paths for better observability.\nAlternative: Use project directory instead:\n  - Create: /Users/ringo/Desktop/claude-setup-python/temp/debug_output.log\n  - Then add 'temp/' to .gitignore if needed\n"
  },
  "suppressOutput": true
}
```

#### Scenario 2: Bash Redirection to /var/tmp
**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "echo 'test data' > /var/tmp/test.txt"
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Bash command attempts to create file in temp directory.\nCommand: echo 'test data' > /var/tmp/test.txt\nPolicy: Never create files in system temp paths.\nAlternative: Use project directory:\n  echo 'test data' > ./temp/test.txt\n"
  },
  "suppressOutput": true
}
```

#### Scenario 3: Allowed Project Directory Write
**Input:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "./temp/output.txt",
    "content": "Output data..."
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "File operation is safe"
  }
}
```

### References
- **Claude Code Hooks Documentation**: `ai_docs/claude-code-hooks.md`
- **UV Scripts Guide**: `ai_docs/uv-scripts-guide.md`
- **Existing Hook Implementation**: `.claude/hooks/pre_tools/sensitive_file_access_validator.py`
- **Shared Utilities**: `.claude/hooks/pre_tools/utils/`
- **Test Examples**: `.claude/hooks/pre_tools/tests/test_sensitive_file_access_validator.py`

---

**Specification Version**: 1.0
**Created**: 2025-10-26
**Author**: Claude Code Hook Expert
**Status**: Ready for Implementation
