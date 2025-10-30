# Temporary Directory Creation Blocker Hook - Specification

## Metadata

- **Hook Name**: tmp_creation_blocker.py
- **Hook Category**: PreToolUse
- **Version**: 2.1.0
- **Author**: Claude Code Hook Expert
- **Last Updated**: 2025-10-30

## 1. Purpose

Prevent file creation in system temporary directories during Claude Code development operations, encouraging the use of project-local directories instead. This ensures better observability, version control integration, and workflow management by keeping all generated files within the project workspace.

## 2. Problem Statement

Claude Code frequently creates temporary files in system directories (e.g., `/tmp/`, `C:\Temp\`, `$TMPDIR`) which presents several challenges:

1. **Lack of Observability**: Files scattered in system temp directories are not visible in the project workspace
2. **Version Control Issues**: Cannot track or commit temporary artifacts that may be needed for debugging or reproducibility
3. **Auto-deletion Risk**: System cleanup processes may delete important development artifacts
4. **Poor Organization**: Files spread across system locations are harder to manage and locate
5. **Cross-platform Issues**: Different platforms have different temp directory conventions
6. **Workflow Disruption**: Difficult to review, archive, or share temporary development artifacts

## 3. Objectives

1. **Block System Temp Usage**: Prevent file creation in all known system temporary directories
2. **Provide Clear Guidance**: Offer helpful error messages with specific alternatives
3. **Cross-platform Support**: Handle Unix, Linux, macOS, and Windows temporary directories
4. **Bash Command Parsing**: Detect file creation in shell commands (redirects, touch, tee, etc.)
5. **Fail-safe Behavior**: Allow operations on errors to avoid disrupting development
6. **Zero Dependencies**: Use only Python standard library for maximum portability
7. **Integration**: Leverage shared utilities for consistency across pre_tools hooks

## 4. Hook Event Selection

### Selected Event: PreToolUse

**Rationale**:
- Executes **before** tool processing, allowing prevention of unwanted operations
- Receives complete tool parameters for validation
- Can deny operations via `permissionDecision: "deny"`
- Supports structured error messages to guide user behavior
- Ideal for validation and policy enforcement

**Alternative Events Considered**:
- **PostToolUse**: Too late - files would already be created
- **UserPromptSubmit**: Too early - tool parameters not yet available
- **SessionStart**: Not appropriate for per-operation validation

## 5. Tool Matchers

The hook monitors the following Claude Code tools:

### File Operation Tools

1. **Write**: Direct file creation/overwriting
   - Validates `tool_input.file_path`
   - Most common file creation tool

2. **Edit**: File modification (may create new files)
   - Validates `tool_input.file_path`
   - Can create files if they don't exist

### Shell Command Tools

3. **Bash**: Shell command execution
   - Parses `tool_input.command` to extract output paths
   - Detects redirects: `>`, `>>`, `2>`, `&>`
   - Detects commands: `touch`, `tee`
   - Example patterns:
     - `echo "text" > /tmp/file.txt`
     - `touch /tmp/data.json`
     - `command | tee /tmp/output.log`

### Tools Explicitly Excluded

- **NotebookEdit**: While available in Claude Code, excluded to simplify scope. Jupyter notebook operations rarely target system temp directories.
- **MultiEdit**: Not available in current Claude Code built-in tools.

### Matcher Configuration

```json
{
  "matcher": "Write|Edit|Bash"
}
```

## 6. Input Schema

### Standard PreToolUse Input Structure

```typescript
{
  session_id: string,           // Unique session identifier
  transcript_path: string,      // Path to transcript JSONL
  cwd: string,                  // Current working directory
  hook_event_name: "PreToolUse",
  tool_name: string,            // "Write" | "Edit" | "Bash" | etc.
  tool_input: {                 // Tool-specific parameters
    file_path?: string,         // For Write/Edit
    command?: string,           // For Bash
    content?: string,           // For Write
    // ... other tool-specific fields
  }
}
```

### Tool-Specific Input Handling

#### File Operation Tools (Write, Edit)

```python
file_path = tool_input.get("file_path", "")
```

#### Bash Command Tool

```python
command = tool_input.get("command", "")
# Parse to extract file paths from:
# - Redirects: > file, >> file, 2> file, &> file
# - touch: touch file1 file2
# - tee: command | tee file
```

## 7. Output Schema

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

#### 7.1 Allow Decision

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Path is not in system temporary directory"
  }
}
```

**Used when**:
- Path is within project directory
- Tool is not monitored by this hook
- Bash command doesn't write to temp directories
- Error occurs (fail-safe behavior)

#### 7.2 Deny Decision

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "📂 Blocked: File creation in system temporary directory\n\nPath: /tmp/data.json\n\nWhy this is blocked:\n  - Files in system temp directories are not visible in your project workspace\n  - Cannot be tracked by git for version control\n  - May be automatically deleted by the system\n  - Scattered outside your project directory structure\n  - Harder to manage and locate during development\n\nRecommended alternatives:\n  - Create in project: ./tmp/data.json\n  - Use project subdirectory: ./output/data.json\n  - Use workspace directory: ./workspace/data.json\n\nTo create the directory: mkdir -p ./tmp\n\nThis keeps all development artifacts organized and trackable."
  },
  "suppressOutput": true
}
```

**Used when**:
- Path is detected in system temporary directory
- Provides clear explanation and alternatives
- `suppressOutput: true` to prevent cluttering transcript

## 8. Validation Logic

### 8.1 Temporary Directory Detection

**System Temporary Directories** (platform-specific):

```python
# Unix/Linux/macOS
SYSTEM_TEMP_DIRS = [
    "/tmp",
    "/var/tmp",
    "/private/tmp",        # macOS
    "/private/var/tmp",    # macOS
]

# Windows
WINDOWS_TEMP_DIRS = [
    r"C:\Temp",
    r"C:\Windows\Temp",
]

# Environment Variables
TEMP_ENV_VARS = ["TMPDIR", "TEMP", "TMP"]
```

**Detection Algorithm**:

```python
def get_all_temp_directories() -> list[str]:
    """Get all system temporary directories for current platform."""
    temp_dirs = []

    # Add platform-specific standard paths
    if os.name != 'nt':  # Unix-like
        temp_dirs.extend(SYSTEM_TEMP_DIRS)
    else:  # Windows
        temp_dirs.extend(WINDOWS_TEMP_DIRS)

    # Add directories from environment variables
    for env_var in TEMP_ENV_VARS:
        env_value = os.environ.get(env_var)
        if env_value and os.path.isdir(env_value):
            resolved = str(Path(env_value).resolve())
            if resolved not in temp_dirs:
                temp_dirs.append(resolved)

    return temp_dirs


def check_path_is_temp_directory(file_path: str) -> bool:
    """Check if file path is within a system temporary directory."""
    if not file_path:
        return False

    try:
        # Convert to absolute, normalized path
        abs_path = os.path.abspath(file_path)
        normalized_path = os.path.normpath(abs_path)

        # Check against all temp directories
        for temp_dir in get_all_temp_directories():
            temp_dir_norm = os.path.normpath(temp_dir)

            # Use os.path.commonpath for proper boundary checking
            try:
                common = os.path.commonpath([normalized_path, temp_dir_norm])
                if common == temp_dir_norm:
                    return True
            except ValueError:
                # Paths on different drives (Windows)
                continue

    except (OSError, ValueError):
        # Fail-safe: allow on error
        return False

    return False
```

### 8.2 Bash Command Parsing

**File Creation Patterns Detected**:

```python
def extract_bash_output_paths(command: str) -> list[str]:
    """Extract file paths from bash commands that create/write files."""
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
```

**Example Commands Caught**:

```bash
# Redirects
echo "data" > /tmp/output.txt          # ❌ Blocked
cat input.txt >> /tmp/log.txt          # ❌ Blocked
command 2> /tmp/errors.log             # ❌ Blocked

# Touch
touch /tmp/marker.txt                  # ❌ Blocked
touch -a /tmp/file1.txt /tmp/file2.txt # ❌ Blocked (first file)

# Tee
ls -la | tee /tmp/listing.txt          # ❌ Blocked
command | tee -a /tmp/output.log       # ❌ Blocked

# Allowed (project-relative)
echo "data" > ./tmp/output.txt         # ✅ Allowed
touch ./workspace/marker.txt           # ✅ Allowed
ls -la | tee ./output/listing.txt      # ✅ Allowed
```

### 8.3 Alternative Path Generation

```python
def generate_project_alternative(temp_path: str, _project_dir: str) -> str:
    """Generate project-relative alternative path suggestion."""
    filename = os.path.basename(temp_path)
    return f"./tmp/{filename}"
```

**Suggested Alternatives**:

1. **Primary**: `./tmp/{filename}` - Dedicated temp directory in project
2. **Secondary**: `./output/{filename}` - For output artifacts
3. **Tertiary**: `./workspace/{filename}` - For workspace files

## 9. Error Handling Strategy

### Fail-Safe Principle

**All errors result in "allow" decision** to prevent disrupting development:

```python
try:
    # Validation logic
    pass
except Exception as e:
    # Log error to stderr
    print(f"Temporary directory blocker error: {e}", file=sys.stderr)
    # Allow operation (fail-safe)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Error Scenarios

1. **Input Parsing Failure**:
   - Decision: Allow
   - Reason: "Failed to parse input (fail-safe)"

2. **Path Resolution Error**:
   - Decision: Allow (exception caught in validation)
   - Behavior: Assume path is not in temp directory

3. **Environment Variable Access Error**:
   - Decision: Skip that temp directory
   - Continue with remaining checks

4. **Regex Parsing Error**:
   - Decision: Return empty path list
   - Allow command to execute

## 10. Configuration

### 10.1 Hook Registration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### 10.2 Hook Script Location

**Path**: `.claude/hooks/pre_tools/tmp_creation_blocker.py`

**Execution**: `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py`

### 10.3 Environment Variables

- **CLAUDE_PROJECT_DIR**: Absolute path to project root
  - Used for generating alternative paths
  - Accessed via: `os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())`

- **TMPDIR, TEMP, TMP**: System temporary directory paths
  - Dynamically detected and validated
  - Used to identify temp directories across platforms

## 11. Dependencies

### UV Script Metadata

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

### Python Version Requirement

- **Minimum**: Python 3.12
- **Rationale**: Use of modern type hints and pattern matching

### Standard Library Modules

```python
import os          # Path operations, environment variables
import re          # Regex for bash command parsing
import sys         # stdin/stdout/stderr, exit codes
from pathlib import Path  # Path normalization
from typing import Optional  # Type hints
```

### Shared Utilities

```python
from .utils import parse_hook_input, output_decision
```

**Imported Functions**:
- `parse_hook_input()` - Parse and validate JSON from stdin
- `output_decision()` - Output formatted JSON decision

## 12. Testing Strategy

### 12.1 Unit Tests Structure

**Location**: `tests/claude-hook/pre_tools/test_tmp_creation_blocker.py`

**Test Framework**: pytest with distributed testing

**Execution**: `uv run pytest -n auto tests/claude-hook/pre_tools/test_tmp_creation_blocker.py`

### 12.2 Test Categories

#### Path Detection Tests

```python
def test_unix_temp_directory_detection():
    """Test detection of Unix/Linux temporary directories."""
    assert check_path_is_temp_directory("/tmp/file.txt") is True
    assert check_path_is_temp_directory("/var/tmp/data.json") is True
    assert check_path_is_temp_directory("/private/tmp/output.log") is True

def test_project_path_allowed():
    """Test project-relative paths are allowed."""
    assert check_path_is_temp_directory("./tmp/file.txt") is False
    assert check_path_is_temp_directory("./output/data.json") is False
    assert check_path_is_temp_directory("/home/user/project/tmp/file.txt") is False

def test_environment_variable_temp_detection():
    """Test temp directory detection via environment variables."""
    # Mock TMPDIR environment variable
    # Verify detection
    pass

def test_relative_path_normalization():
    """Test relative paths are properly normalized."""
    # Test ../../../tmp/file.txt
    # Test symlink resolution
    pass
```

#### Bash Command Parsing Tests

```python
def test_redirect_operator_parsing():
    """Test detection of redirect operators in bash commands."""
    paths = extract_bash_output_paths('echo "text" > /tmp/output.txt')
    assert "/tmp/output.txt" in paths

    paths = extract_bash_output_paths('cat input.txt >> /tmp/log.txt')
    assert "/tmp/log.txt" in paths

def test_touch_command_parsing():
    """Test detection of touch commands."""
    paths = extract_bash_output_paths('touch /tmp/marker.txt')
    assert "/tmp/marker.txt" in paths

def test_tee_command_parsing():
    """Test detection of tee commands."""
    paths = extract_bash_output_paths('ls -la | tee /tmp/listing.txt')
    assert "/tmp/listing.txt" in paths

def test_complex_bash_command():
    """Test complex commands with multiple file outputs."""
    cmd = 'echo "data" > /tmp/out.txt && cat /tmp/out.txt >> /var/tmp/log.txt'
    paths = extract_bash_output_paths(cmd)
    assert "/tmp/out.txt" in paths
    assert "/var/tmp/log.txt" in paths
```

#### Integration Tests

```python
def test_write_tool_blocked_in_tmp():
    """Test Write tool blocked when writing to /tmp/."""
    # Mock stdin with Write tool input
    # Verify "deny" decision output
    pass

def test_write_tool_allowed_in_project():
    """Test Write tool allowed when writing to project directory."""
    # Mock stdin with Write tool input
    # Verify "allow" decision output
    pass

def test_bash_tool_blocked_redirect():
    """Test Bash tool blocked when redirecting to /tmp/."""
    # Mock stdin with Bash tool input
    # Verify "deny" decision output
    pass

def test_bash_tool_allowed_redirect():
    """Test Bash tool allowed when redirecting to project directory."""
    # Mock stdin with Bash tool input
    # Verify "allow" decision output
    pass
```

#### Error Handling Tests

```python
def test_fail_safe_on_invalid_input():
    """Test hook allows operation on invalid JSON input."""
    # Mock malformed JSON
    # Verify "allow" decision output
    pass

def test_fail_safe_on_path_resolution_error():
    """Test hook allows operation when path resolution fails."""
    # Mock path that causes OSError
    # Verify "allow" decision output
    pass
```

#### Cross-Platform Tests

```python
@pytest.mark.skipif(os.name == 'nt', reason="Unix-only test")
def test_unix_temp_directories():
    """Test Unix temporary directory detection."""
    pass

@pytest.mark.skipif(os.name != 'nt', reason="Windows-only test")
def test_windows_temp_directories():
    """Test Windows temporary directory detection."""
    pass
```

### 12.3 Test Coverage Goals

- **Line Coverage**: ≥ 90%
- **Branch Coverage**: ≥ 85%
- **Edge Cases**: All documented edge cases tested
- **Platform Coverage**: Tests for Unix/Linux, macOS, Windows

### 12.4 Test Data

**Example Tool Inputs**:

```python
# Write tool - blocked
WRITE_BLOCKED = {
    "session_id": "test123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/project",
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {
        "file_path": "/tmp/data.json",
        "content": '{"test": true}'
    }
}

# Write tool - allowed
WRITE_ALLOWED = {
    "session_id": "test123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/project",
    "hook_event_name": "PreToolUse",
    "tool_name": "Write",
    "tool_input": {
        "file_path": "./tmp/data.json",
        "content": '{"test": true}'
    }
}

# Bash tool - blocked
BASH_BLOCKED = {
    "session_id": "test123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/project",
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {
        "command": 'echo "output" > /tmp/result.txt'
    }
}
```

## 13. Security Considerations

### 13.1 Path Traversal Prevention

**Risk**: Malicious paths like `../../tmp/file.txt` could bypass validation

**Mitigation**:
```python
# Always normalize and resolve to absolute path
abs_path = os.path.abspath(file_path)
normalized_path = os.path.normpath(abs_path)
```

### 13.2 Symlink Handling

**Risk**: Symlinks could point to temp directories

**Mitigation**:
```python
# Resolve symlinks when detecting temp directories from env vars
resolved = str(Path(env_value).resolve())
```

### 13.3 Input Validation

**Risk**: Malformed or malicious JSON input

**Mitigation**:
- Use shared `parse_hook_input()` utility
- Validate types before processing
- Fail-safe on errors (allow operation)

### 13.4 Regex Safety

**Risk**: ReDoS (Regular Expression Denial of Service)

**Mitigation**:
- Use simple, non-backtracking regex patterns
- Avoid nested quantifiers
- Set timeout via hook configuration (60 seconds default)

### 13.5 Error Message Safety

**Risk**: Exposing sensitive information in error messages

**Mitigation**:
- Only show file paths (which user already provided)
- No system information or configuration details
- No environment variable values

## 14. Performance Considerations

### 14.1 Execution Time

**Target**: < 100ms per invocation

**Optimizations**:
- Minimal path operations
- Cache environment variable lookups
- Simple regex patterns
- Early return on non-monitored tools

### 14.2 Memory Usage

**Target**: < 10 MB per invocation

**Considerations**:
- Small list of temp directories
- Minimal regex compilation
- No large data structures

### 14.3 Scalability

**Expected Load**: 10-100 hook invocations per minute

**Design**:
- Stateless execution (no shared state)
- No file I/O (except stdin/stdout)
- No network operations

## 15. Integration Considerations

### 15.1 Coexistence with Other Hooks

**Scenario**: Multiple PreToolUse hooks registered

**Behavior**:
- Hooks run in parallel
- Any "deny" decision blocks operation
- This hook uses `suppressOutput: true` to avoid spam

**Compatibility**:
- Works alongside universal_hook_logger.py
- Compatible with other validation hooks
- No shared state or conflicts

### 15.2 User Experience

**Error Message Design**:
- Clear explanation of what was blocked
- Specific reasons why it's problematic
- Concrete alternatives with commands
- Helpful tone, not punitive

**Example**:
```
📂 Blocked: File creation in system temporary directory

Path: /tmp/data.json

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: ./tmp/data.json
  - Use project subdirectory: ./output/data.json
  - Use workspace directory: ./workspace/data.json

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable.
```

### 15.3 Debugging Support

**Hook Execution Visibility**:
- Use `claude --debug` to see hook invocations
- Check logs in transcript mode (Ctrl-R)
- Error messages sent to stderr (visible in debug mode)

**Testing Hook Manually**:
```bash
# Test with sample input
echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.txt"}}' | \
  uv run .claude/hooks/pre_tools/tmp_creation_blocker.py
```

## 16. Rollback Strategy

### 16.1 Disabling the Hook

**Option 1**: Comment out in settings.json
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Write|Edit|Bash",
      //   "hooks": [...]
      // }
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
rm .claude/hooks/pre_tools/tmp_creation_blocker.py
```

### 16.2 Partial Rollback

**Disable for specific tools**:
```json
{
  "matcher": "Write|Edit"  // Removed Bash
}
```

**Disable for local development**:
- Create `.claude/settings.local.json` with empty hooks
- Gitignored by default

## 17. Future Enhancements

### 17.1 Configuration Options

**Potential Settings**:
```python
# Allow-list for specific temp paths
ALLOWED_TEMP_PATHS = ["/tmp/claude-cache"]

# Custom project temp directory
PROJECT_TEMP_DIR = "./workspace/tmp"

# Disable for specific commands
IGNORE_COMMANDS = ["pytest"]
```

### 17.2 Advanced Features

1. **Automatic Directory Creation**:
   - Create `./tmp/` directory automatically
   - Add to `.gitignore` if not present

2. **Path Rewriting**:
   - Automatically rewrite `/tmp/file.txt` to `./tmp/file.txt`
   - Use `permissionDecision: "ask"` with suggested rewrite

3. **Pattern Customization**:
   - User-defined regex patterns for bash parsing
   - Configuration file for temp directory patterns

4. **Analytics**:
   - Track frequency of blocked operations
   - Report most common temp directory usage patterns

## 18. Documentation Requirements

### 18.1 Inline Documentation

- Comprehensive module docstring
- Function docstrings with Args/Returns
- Type hints on all functions
- Comments for complex logic

### 18.2 User Documentation

**Topics to Cover**:
1. What the hook does and why
2. How to disable if needed
3. How to configure project temp directories
4. Troubleshooting common issues
5. Examples of blocked vs allowed operations

### 18.3 Developer Documentation

**Topics to Cover**:
1. Architecture and design decisions
2. How to extend for new tools
3. How to add new temp directory patterns
4. Testing procedures
5. Debugging techniques

## 19. Success Criteria

### 19.1 Functional Requirements

- ✅ Blocks file creation in all system temp directories
- ✅ Provides helpful error messages with alternatives
- ✅ Works on Unix/Linux/macOS/Windows
- ✅ Parses bash commands correctly
- ✅ Uses shared utilities from pre_tools/utils
- ✅ Fail-safe behavior on errors

### 19.2 Non-Functional Requirements

- ✅ Execution time < 100ms
- ✅ Test coverage ≥ 90%
- ✅ Zero external dependencies
- ✅ Clear, helpful error messages
- ✅ No disruption to development workflow

### 19.3 Integration Requirements

- ✅ Registered in .claude/settings.json
- ✅ Works alongside other PreToolUse hooks
- ✅ Compatible with universal_hook_logger.py
- ✅ No conflicts with existing infrastructure

## 20. Implementation Plan

### Phase 1: Core Implementation (Pending)

1. ⏳ Create UV script with metadata
2. ⏳ Implement temp directory detection
3. ⏳ Implement bash command parsing
4. ⏳ Implement validation logic
5. ⏳ Add comprehensive error messages
6. ⏳ Integrate with shared utilities

### Phase 2: Configuration (Pending)

1. ⏳ Add to .claude/settings.json
2. ⏳ Configure tool matchers (Write, Edit, Bash only)
3. ⏳ Set appropriate timeout
4. ⏳ Test hook registration

### Phase 3: Testing (Pending)

1. ⏳ Write unit tests for path detection
2. ⏳ Write unit tests for bash parsing
3. ⏳ Write integration tests
4. ⏳ Write cross-platform tests
5. ⏳ Achieve ≥90% code coverage

### Phase 4: Documentation (Pending)

1. ⏳ Complete inline documentation
2. ⏳ Write user guide
3. ⏳ Write developer guide
4. ⏳ Add examples and troubleshooting

### Phase 5: Validation (Pending)

1. ⏳ Manual testing with real Claude Code sessions
2. ⏳ Test on all supported platforms
3. ⏳ Validate error messages are helpful
4. ⏳ Performance testing

## 21. Specification Change Log

| Version | Date       | Changes                                      | Author                   |
|---------|------------|----------------------------------------------|--------------------------|
| 1.0.0   | 2025-10-30 | Initial specification                        | Claude Code Hook Expert  |
| 2.0.0   | 2025-10-30 | Updated to use shared utilities pattern      | Claude Code Hook Expert  |
| 2.1.0   | 2025-10-30 | Removed MultiEdit (not available) and NotebookEdit (simplified scope) | Claude Code Hook Expert  |

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
