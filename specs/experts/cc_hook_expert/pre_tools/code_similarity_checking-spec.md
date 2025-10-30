# Code Similarity Checking Hook - Specification

## 1. Overview

### Purpose
Prevent Claude Code from creating duplicate files with versioned or backup naming patterns by detecting similar functionality before allowing file modifications. This hook encourages Claude to update existing files directly rather than creating new versions.

### Problem Statement
Claude Code AI frequently creates new files with versioning or backup patterns instead of updating existing files:
- Version suffixes: `file_v1.py`, `file_v2.py`, `file_v3.py`
- Copy/backup suffixes: `file_copy.py`, `file_backup.py`
- Number suffixes: `file (1).py`, `file (2).py`
- Date suffixes: `file_20240101.py`, `file_20240102.py`
- Backup extensions: `file.py.bak`, `file.py~`

This creates project clutter, confusion about which version is current, and undermines version control practices.

### Objectives
1. **Detect Versioned Naming Patterns**: Identify when Claude attempts to create files with versioning/backup patterns
2. **Check for Similar Existing Files**: Search for existing files with similar base names in the target directory
3. **Compare Content Similarity**: Analyze if the new content is similar to existing files
4. **Provide Educational Feedback**: Guide Claude to edit existing files instead of creating duplicates
5. **Allow Legitimate Cases**: Permit creation when content is genuinely different or when user explicitly requests backups

## 2. Hook Configuration

### Event Type
**PreToolUse** - Intercepts Write tool calls before file creation

### Matcher Pattern
```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/code_similarity_checking.py",
      "timeout": 30
    }
  ]
}
```

### Why PreToolUse?
- Needs to **prevent** file creation before it occurs
- Can analyze intended content before writing
- Can suggest alternatives (edit existing file) proactively
- Blocking at PreToolUse stage prevents downstream issues

## 3. Input Schema

### Hook Input (via stdin)
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file_v2.py",
    "content": "#!/usr/bin/env python3\n..."
  }
}
```

### Required Fields
- `tool_name`: Must be "Write"
- `tool_input.file_path`: Path where file will be created
- `tool_input.content`: Content to be written

## 4. Output Schema

### Success (Allow Creation)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "No similar files found or content is sufficiently different"
  },
  "suppressOutput": true
}
```

### Blocked (Deny Creation)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🔍 Duplicate File Detected\n\nFile: /path/to/file_v2.py\nSimilar file exists: /path/to/file.py (85% similar)\n\nWhy this is blocked:\n  - Creates project clutter with multiple versions\n  - Unclear which file is the current version\n  - Should use version control (git) for tracking changes\n  - Content is very similar to existing file\n\nRecommended action:\n  Use the Edit tool to update the existing file:\n  Edit(\n    file_path='/path/to/file.py',\n    old_string='<existing code>',\n    new_string='<updated code>'\n  )\n\nOr use git for version tracking:\n  git commit -m \"feat: update implementation\"\n  git branch feature/v2"
  },
  "suppressOutput": false
}
```

## 5. Validation Rules

### Pattern Detection

#### 5.1 Version Suffix Patterns
Regex patterns to detect versioned file names:
```python
VERSION_PATTERNS = [
    r'[_-]?v(ersion)?[_-]?\d+$',           # file_v2, file_version2
    r'[_-]\d+$',                            # file_2, file-3
    r'\s*\(\d+\)$',                         # file (2), file (3)
    r'[_-]\d{8}$',                          # file_20240101
    r'[_-](copy|backup|old|new|final)$',   # file_copy, file_backup
]
```

#### 5.2 Backup Extension Patterns
```python
BACKUP_EXTENSIONS = ['.bak', '.old', '.orig', '.backup', '~']
```

#### 5.3 Monitored Directories
Default directories to check for duplicates:
```python
MONITORED_DIRS = [
    './queries',
    './utils',
    './components',
    './src',
    './lib',
    './services',
    './models',
    './handlers',
]
```

Configuration via environment variable:
```bash
export CODE_SIMILARITY_DIRS="./queries:./utils:./components"
```

### Similarity Detection

#### 5.4 Content Similarity Algorithm
Use Python's `difflib.SequenceMatcher` for content comparison:

1. **Preprocessing**:
   - Remove comments and docstrings
   - Normalize whitespace
   - Extract function/class signatures

2. **Similarity Metrics**:
   - **Line-based similarity**: Compare line-by-line using `difflib.unified_diff`
   - **Structural similarity**: Compare function/class names and signatures
   - **Token similarity**: Compare significant tokens (imports, function names)

3. **Threshold Levels**:
   - `similarity >= 0.85`: Very similar (DENY - suggest editing existing file)
   - `0.60 <= similarity < 0.85`: Moderately similar (ALLOW with warning in context)
   - `similarity < 0.60`: Different enough (ALLOW without warning)

```python
from difflib import SequenceMatcher

def calculate_similarity(content1: str, content2: str) -> float:
    """Calculate similarity ratio between two file contents."""
    matcher = SequenceMatcher(None, content1, content2)
    return matcher.ratio()
```

#### 5.5 Search Strategy
For a file like `file_v2.py`:
1. Extract base name: `file.py`
2. Search for files matching `file*.py` in same directory
3. For each match, calculate similarity
4. If any match has similarity >= 0.85, deny creation

### Exception Rules

#### 5.6 Allowlist - Always Allow
- Files explicitly ending with `.backup` (user-requested backups)
- Files in test directories (`tests/`, `test_*`)
- Configuration files (`.env`, `config.yaml`)
- Generated files (indicated by special markers in content)

#### 5.7 Blocklist - Always Block
- Files ending with `.bak`, `.old`, `.orig`, `~`
- Files with patterns like `file_v2`, `file_v3`, etc. with high similarity (>= 0.85)

## 6. Error Handling

### Fail-Safe Philosophy
**Always fail-safe to "allow"** - Never block valid operations due to hook errors.

### Error Scenarios

1. **Parse Error**: JSON parsing fails
   - Decision: `allow`
   - Reason: "Hook error: failed to parse input (fail-safe)"

2. **File System Error**: Cannot read existing files for comparison
   - Decision: `allow`
   - Reason: "Hook error: file system access failed (fail-safe)"

3. **Similarity Calculation Error**: Algorithm throws exception
   - Decision: `allow`
   - Reason: "Hook error: similarity calculation failed (fail-safe)"

4. **Timeout**: Computation takes too long
   - Decision: `allow` (before timeout)
   - Hook timeout: 30 seconds (configured in settings.json)

### Logging
- Log all errors to stderr for debugging
- Include session_id, file_path, and error details
- Format: `[code_similarity_checking] ERROR: <message>`

## 7. Implementation Details

### Dependencies (UV Script Metadata)
```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

No external dependencies - uses only Python standard library:
- `json`: Input/output parsing
- `sys`: stdin/stdout/stderr handling
- `os`: Environment variables and file paths
- `pathlib`: Path manipulation
- `re`: Pattern matching
- `difflib`: Content similarity
- `typing`: Type hints

### File Structure
```
.claude/hooks/pre_tools/
├── code_similarity_checking.py      # Main hook implementation
└── utils/                            # Shared utilities
    ├── __init__.py
    ├── data_types.py                 # TypedDict definitions
    └── utils.py                      # parse_hook_input, output_decision
```

### Module Organization

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Code Similarity Checking Hook
==============================

Prevents duplicate file creation by checking for similar functionality
before allowing Write operations.
"""

# Standard library imports
import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, List, Tuple

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_hook_input, output_decision

# Module-level constants
SIMILARITY_THRESHOLD_DENY = 0.85
SIMILARITY_THRESHOLD_WARN = 0.60
DEFAULT_MONITORED_DIRS = [
    './queries', './utils', './components',
    './src', './lib', './services'
]

# Main implementation...
```

### Key Functions

#### 7.1 Pattern Detection
```python
def detect_versioned_pattern(file_path: str) -> Optional[str]:
    """
    Detect if file name matches versioning/backup pattern.

    Returns:
        Base file name without version suffix, or None if no pattern detected
    """
    pass
```

#### 7.2 Find Similar Files
```python
def find_similar_files(base_name: str, directory: str) -> List[str]:
    """
    Find existing files with similar base names.

    Returns:
        List of file paths that might be duplicates
    """
    pass
```

#### 7.3 Calculate Similarity
```python
def calculate_similarity(content1: str, content2: str) -> float:
    """
    Calculate content similarity ratio (0.0 to 1.0).

    Returns:
        Similarity ratio using SequenceMatcher
    """
    pass
```

#### 7.4 Main Validation
```python
def validate_write_operation(file_path: str, content: str) -> Optional[str]:
    """
    Validate Write operation against similarity rules.

    Returns:
        None if allowed, error message string if denied
    """
    pass
```

## 8. Testing Strategy

### Unit Test Structure
```
tests/claude_hook/pre_tools/
├── test_code_similarity_checking.py
└── fixtures/
    ├── sample_file.py
    ├── sample_file_v2.py (85% similar)
    └── sample_file_different.py (40% similar)
```

### Test Scenarios

#### 8.1 Pattern Detection Tests
```python
def test_detect_version_suffix():
    """Test version suffix pattern detection"""
    assert detect_versioned_pattern("file_v2.py") == "file.py"
    assert detect_versioned_pattern("file (2).py") == "file.py"
    assert detect_versioned_pattern("file_20240101.py") == "file.py"
    assert detect_versioned_pattern("file.py") is None

def test_detect_backup_extension():
    """Test backup extension detection"""
    assert is_backup_extension("file.py.bak") is True
    assert is_backup_extension("file.py~") is True
    assert is_backup_extension("file.py.backup") is False  # Allowed
```

#### 8.2 Similarity Calculation Tests
```python
def test_identical_content():
    """Test similarity detection for identical content"""
    content1 = "print('hello')\n"
    content2 = "print('hello')\n"
    assert calculate_similarity(content1, content2) >= 0.99

def test_very_similar_content():
    """Test similarity detection for very similar content"""
    content1 = read_fixture("sample_file.py")
    content2 = read_fixture("sample_file_v2.py")
    similarity = calculate_similarity(content1, content2)
    assert 0.80 <= similarity <= 0.90

def test_different_content():
    """Test similarity detection for different content"""
    content1 = read_fixture("sample_file.py")
    content2 = read_fixture("sample_file_different.py")
    assert calculate_similarity(content1, content2) < 0.60
```

#### 8.3 Integration Tests
```python
def test_deny_duplicate_file_creation():
    """Test denying creation of duplicate file"""
    hook_input = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "./utils/helper_v2.py",
            "content": "<85% similar content>"
        }
    }
    result = run_hook(hook_input)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_allow_new_file_creation():
    """Test allowing creation of genuinely new file"""
    hook_input = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "./utils/new_helper.py",
            "content": "<unique content>"
        }
    }
    result = run_hook(hook_input)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

def test_allow_backup_extension():
    """Test allowing .backup extension (user-requested)"""
    hook_input = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "./utils/helper.py.backup",
            "content": "<any content>"
        }
    }
    result = run_hook(hook_input)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
```

#### 8.4 Edge Cases
```python
def test_first_versioned_file():
    """Test allowing first file with version pattern when no base exists"""
    # If file_v2.py is created but file.py doesn't exist, allow it
    pass

def test_non_monitored_directory():
    """Test allowing files outside monitored directories"""
    pass

def test_empty_content():
    """Test handling empty file content"""
    pass

def test_binary_content():
    """Test handling non-text content gracefully"""
    pass
```

### Test Execution
```bash
# Run all tests with distributed execution
uv run pytest tests/claude_hook/pre_tools/test_code_similarity_checking.py -n auto -v

# Run with coverage
uv run pytest tests/claude_hook/pre_tools/test_code_similarity_checking.py --cov --cov-report=html
```

## 9. Configuration

### Environment Variables

```bash
# Monitored directories (colon-separated)
export CODE_SIMILARITY_DIRS="./queries:./utils:./components"

# Similarity thresholds
export CODE_SIMILARITY_DENY_THRESHOLD="0.85"
export CODE_SIMILARITY_WARN_THRESHOLD="0.60"

# Enable/disable hook
export CODE_SIMILARITY_ENABLED="true"

# Debug mode (verbose logging)
export CODE_SIMILARITY_DEBUG="false"
```

### Project Configuration
Settings can also be configured in `.claude/settings.json`:

```json
{
  "env": {
    "CODE_SIMILARITY_DIRS": "./queries:./utils:./components",
    "CODE_SIMILARITY_DENY_THRESHOLD": "0.85",
    "CODE_SIMILARITY_WARN_THRESHOLD": "0.60"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/code_similarity_checking.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## 10. Security Considerations

### Path Traversal Prevention
```python
def validate_file_path(file_path: str) -> bool:
    """Ensure file path is within project directory"""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    file_abs = Path(file_path).resolve()

    try:
        file_abs.relative_to(project_dir)
        return True
    except ValueError:
        return False
```

### Input Sanitization
- Validate all paths before file system operations
- Limit file size for similarity comparisons (max 1MB)
- Timeout protection (30 second hook timeout)
- Never execute file content, only read and compare

### Sensitive File Protection
Skip similarity checking for:
- `.env` files
- `.git/` directory
- Files in `.gitignore`
- SSH keys, certificates
- Database files

## 11. Performance Optimization

### Caching Strategy
```python
# Cache similarity results for session
_similarity_cache: dict[tuple[str, str], float] = {}

def get_cached_similarity(file1: str, file2: str) -> Optional[float]:
    """Get cached similarity result"""
    cache_key = tuple(sorted([file1, file2]))
    return _similarity_cache.get(cache_key)
```

### File Size Limits
```python
MAX_FILE_SIZE = 1_048_576  # 1MB
MAX_LINES = 10_000

def is_file_too_large(file_path: str) -> bool:
    """Check if file is too large for similarity checking"""
    return Path(file_path).stat().st_size > MAX_FILE_SIZE
```

### Early Exit Optimization
```python
def quick_similarity_check(content1: str, content2: str) -> Optional[float]:
    """Quick pre-check before full similarity calculation"""
    # Check line count difference
    lines1 = content1.count('\n')
    lines2 = content2.count('\n')
    if abs(lines1 - lines2) > max(lines1, lines2) * 0.3:
        return 0.0  # Too different in size

    # Check first/last lines
    if content1[:100] == content2[:100] and content1[-100:] == content2[-100:]:
        return 1.0  # Likely identical

    return None  # Needs full check
```

## 12. User Experience

### Educational Error Messages
Format error messages to guide Claude toward better practices:

```
🔍 Duplicate File Detected

Attempted to create: utils/parser_v2.py
Similar file exists: utils/parser.py (87% similar)

Why this is blocked:
  • Creates confusion about which file is current
  • Duplicates code instead of improving existing implementation
  • Bypasses version control best practices
  • Makes codebase harder to maintain

✅ Recommended action:
  Update the existing file instead:

  Edit(
    file_path='utils/parser.py',
    old_string='<existing implementation>',
    new_string='<improved implementation>'
  )

📚 Alternative approaches:
  • Use git branches: git checkout -b feature/parser-improvements
  • Use git commits: git commit -m "refactor: improve parser logic"
  • If truly different functionality, use descriptive name: utils/json_parser.py
```

### Logging Output (suppress_output=false for denials)
Show blocking messages in transcript mode so user can see the guidance.

## 13. Integration with Other Hooks

### Coordination with file_naming_enforcer.py
The `code_similarity_checking.py` hook works alongside `file_naming_enforcer.py`:

- **file_naming_enforcer**: Blocks based on naming pattern alone
- **code_similarity_checking**: Additionally checks content similarity

Both hooks run in parallel for Write operations:
```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/file_naming_enforcer.py"
    },
    {
      "type": "command",
      "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/code_similarity_checking.py"
    }
  ]
}
```

### Deduplication
Claude Code automatically deduplicates identical hook commands, ensuring no duplicate execution.

## 14. Rollback Strategy

If the hook causes issues:

1. **Disable temporarily**:
   ```bash
   export CODE_SIMILARITY_ENABLED="false"
   ```

2. **Remove from settings.json**:
   ```bash
   # Edit .claude/settings.json, remove hook entry
   ```

3. **Emergency bypass**:
   ```bash
   # Rename hook file to disable
   mv .claude/hooks/pre_tools/code_similarity_checking.py{,.disabled}
   ```

4. **Git revert**:
   ```bash
   git revert <commit-hash>
   ```

## 15. Documentation

### README for Hook
Create `.claude/hooks/pre_tools/README.md` with:
- Hook purpose and behavior
- Configuration options
- Example scenarios
- Troubleshooting guide

### Inline Documentation
- Docstrings for all functions
- Type hints for all parameters
- Comments explaining complex logic
- Examples in docstrings

## 16. Future Enhancements

### Potential Improvements
1. **AST-based similarity**: Use Python AST for more accurate code comparison
2. **Machine learning**: Train model to detect semantic similarity
3. **Multi-language support**: Extend beyond Python files
4. **User preferences**: Per-directory or per-file-type thresholds
5. **Git integration**: Check git history for similar commits
6. **Incremental checking**: Only check modified portions

### Metrics Collection
Track hook effectiveness:
- Number of blocks (duplicates prevented)
- False positives (legitimate files blocked)
- Performance metrics (execution time)

## 17. Implementation Checklist

- [ ] Create hook script with UV metadata
- [ ] Implement pattern detection functions
- [ ] Implement similarity calculation
- [ ] Implement main validation logic
- [ ] Add error handling and fail-safe mechanisms
- [ ] Write comprehensive unit tests
- [ ] Test with real-world scenarios
- [ ] Update .claude/settings.json
- [ ] Create README documentation
- [ ] Add to project documentation
- [ ] Monitor for issues in first week

## 18. Success Criteria

### Functional Requirements Met
✅ Detects versioned/backup file naming patterns
✅ Calculates content similarity accurately
✅ Blocks creation of duplicate files (>= 85% similar)
✅ Allows creation of genuinely new files
✅ Provides educational feedback to Claude
✅ Fails safe on errors (always allows)

### Performance Requirements
✅ Executes within 30 second timeout
✅ Handles files up to 1MB efficiently
✅ No noticeable impact on Claude Code responsiveness

### Quality Requirements
✅ 100% test coverage for core functions
✅ All tests pass with pytest
✅ Type checking passes with basedpyright
✅ Linting passes with ruff
✅ Clear documentation and examples

---

**Specification Version**: 1.0
**Last Updated**: 2025-10-31
**Author**: Claude Code Hook Expert
**Status**: Ready for Implementation
