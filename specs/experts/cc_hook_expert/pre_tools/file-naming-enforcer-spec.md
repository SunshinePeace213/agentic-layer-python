# File Naming Convention Enforcer Hook - Technical Specification

**Hook Name**: `file_naming_enforcer.py`
**Hook Event**: PreToolUse
**Monitored Tools**: Write, Edit, Bash
**Version**: 1.0.0
**Author**: Claude Code Hook Expert
**Date**: 2025-10-30

---

## Executive Summary

This hook prevents creation of files with poor naming conventions during Claude Code development operations. It enforces professional file naming standards by blocking temporary-style naming patterns, version suffixes, and non-standard conventions that indicate developers should be using version control features instead.

### Quick Reference

**Blocked Patterns**:
- Backup extensions: `.backup`, `.bak`, `.old`, `.orig`
- Version suffixes: `_v2`, `_v3`, `file_v2.py`
- Iteration suffixes: `_final`, `_fixed`, `_update`, `_new`, `_copy`, `_old`
- Test/temp markers: `_test`, `_tmp`, `_temp` (except in test directories)
- Number suffixes: `file2.py`, `script_2.py`, `code3.js`
- Python-specific: Non-standard naming for `.py` files

**Allowed**:
- Standard project files: `main.py`, `utils.py`, `UserModel.py`
- Test files in proper locations: `tests/test_user.py`
- Documentation: `README.md`, `CHANGELOG.md`
- Configuration: `.env.example`, `config.yaml`

---

## 1. Purpose and Objectives

### 1.1 Problem Statement

During development, especially in AI-assisted workflows, files are often created with poor naming conventions that indicate anti-patterns:

1. **Backup File Proliferation**: `script.py.backup`, `utils.py.old`, `config.json.bak`
   - Problem: Clutters project directories
   - Solution: Use `git stash` or create feature branches

2. **Version Suffix Hell**: `api_v2.py`, `parser_v3.js`, `handler_final.ts`
   - Problem: Multiple versions coexist, causing confusion
   - Solution: Use git branches, tags, and semantic versioning

3. **Iteration Artifacts**: `code_fixed.py`, `test_update.js`, `script_new.py`
   - Problem: Unclear what "final" or "fixed" actually means
   - Solution: Use git commits with descriptive messages

4. **Number Suffixes**: `utils2.py`, `helper_2.js`, `script3.py`
   - Problem: No semantic meaning, hard to maintain
   - Solution: Use descriptive names or git branches

5. **Python-Specific Issues**: `MyScript.py`, `user-handler.py`, `APIEndpoint.py`
   - Problem: Violates Python community conventions
   - Solution: Use `snake_case` for modules or `PascalCase` for classes

### 1.2 Objectives

1. **Enforce Professional Naming**: Prevent creation of files with temporary-style names
2. **Promote Git Usage**: Educate developers to use version control features
3. **Maintain Clean Projects**: Keep project directories free of clutter
4. **Follow Language Conventions**: Ensure Python files follow community standards
5. **Educational Feedback**: Provide clear explanations and better alternatives

### 1.3 Success Criteria

- ✅ Zero false positives on standard project files
- ✅ 100% detection of common poor naming patterns
- ✅ Clear, actionable error messages with alternatives
- ✅ < 100ms execution time per invocation
- ✅ Zero external dependencies
- ✅ Cross-platform compatibility (Unix, macOS, Windows)

---

## 2. Hook Architecture

### 2.1 Event Selection Rationale

**PreToolUse** is the optimal event because:
- Intercepts file operations BEFORE creation
- Prevents clutter from ever being created
- Enables educational "just-in-time" feedback
- Supports blocking with detailed error messages
- Allows suggesting better alternatives immediately

### 2.2 Tool Matchers

**Monitored Tools**: `Write|Edit|Bash`

**Rationale**:
1. **Write**: Catches direct file creation attempts
2. **Edit**: Catches attempts to rename/modify file names via edit operations
3. **Bash**: Catches file creation via shell commands:
   - Redirects: `echo "data" > file_v2.txt`
   - Touch: `touch script.py.backup`
   - cp/mv: `cp main.py main_backup.py`

### 2.3 Input Schema

**PreToolUse Hook Input** (via stdin as JSON):
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write|Edit|Bash",
  "tool_input": {
    "file_path": "string (for Write/Edit)",
    "content": "string (for Write)",
    "command": "string (for Bash)",
    "old_string": "string (for Edit)",
    "new_string": "string (for Edit)"
  }
}
```

### 2.4 Output Schema

**JSON Output Format**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny",
    "permissionDecisionReason": "Detailed explanation with alternatives"
  },
  "suppressOutput": false
}
```

**Exit Code**: Always `0` (fail-safe behavior)

---

## 3. Validation Rules

### 3.1 File Extension Blocklist

**Category**: Backup/Temporary Extensions

**Blocked Extensions**:
- `.backup` - Use `git stash` instead
- `.bak` - Use `git stash` instead
- `.old` - Use `git stash` or git branches
- `.orig` - Git merge artifact, should be cleaned up
- `.swp`, `.swo` - Vim swap files (should be in .gitignore)
- `~` suffix - Editor backup files (should be in .gitignore)

**Examples**:
```
❌ script.py.backup
❌ config.json.bak
❌ utils.py.old
❌ README.md.orig
❌ main.py~
✅ script.py
✅ config.json
✅ utils.py
```

**Detection**: Case-insensitive extension matching

### 3.2 Version Suffix Patterns

**Category**: Version Control Anti-Patterns

**Blocked Patterns**:
- `_v<number>` - e.g., `file_v2.py`, `script_v10.js`
- `_version<number>` - e.g., `api_version2.py`
- `-v<number>` - e.g., `parser-v3.js`
- `v<number>` at end - e.g., `handlerv2.py`

**Examples**:
```
❌ api_v2.py
❌ parser_v3.js
❌ handler-v2.ts
❌ utilsv2.py
✅ api.py
✅ parser.js
✅ handler.ts
```

**Regex Pattern**: `(?i)[_-]?v(ersion)?[_-]?\d+(?:[_.-]\d+)*$`

**Git Alternative**: Use branches/tags
```bash
# Instead of api_v2.py, use:
git checkout -b feature/api-v2
# ... make changes to api.py
git tag v2.0.0
```

### 3.3 Iteration Suffix Patterns

**Category**: Temporary Development Artifacts

**Blocked Suffixes** (case-insensitive):
- `_final`, `_FINAL`, `-final`
- `_fixed`, `_fix`
- `_update`, `_updated`
- `_new`, `_latest`
- `_copy`, `_backup`
- `_old`, `_obsolete`
- `_modified`, `_mod`
- `_revised`, `_rev`
- `_corrected`

**Examples**:
```
❌ script_final.py
❌ code_fixed.js
❌ test_update.py
❌ handler_new.ts
❌ utils_copy.py
✅ script.py
✅ code.js
✅ test.py
✅ handler.ts
```

**Regex Pattern**: `(?i)[_-](final|fixed?|update[d]?|new|latest|copy|backup|old|obsolete|modified|mod|revised|rev|corrected)$`

**Git Alternative**: Use descriptive commits
```bash
# Instead of script_fixed.py, use:
git add script.py
git commit -m "fix: correct validation logic in script.py"
```

### 3.4 Number Suffix Patterns

**Category**: Meaningless Numeric Suffixes

**Blocked Patterns**:
- Trailing numbers: `file2.py`, `script3.js`
- Underscore + number: `utils_2.py`, `helper_3.js`
- Hyphen + number: `parser-2.ts`, `handler-3.py`

**Exceptions** (Allowed):
- Semantic versioning in names: `python3`, `http2`, `base64`
- Date formats: `report_2025_10_30.txt`
- Index files when part of convention: `blog_post_1.md` (numbered series)

**Examples**:
```
❌ script2.py
❌ utils_2.js
❌ handler-3.ts
✅ python3_wrapper.py (semantic)
✅ http2_client.js (semantic)
✅ report_2025_10_30.txt (date)
```

**Regex Pattern**: `(?i)[_-]?\d+$` (with semantic exceptions)

### 3.5 Test/Temp Markers in Wrong Locations

**Category**: Misplaced Development Files

**Blocked**: `_test`, `_tmp`, `_temp` suffixes OUTSIDE proper test/temp directories

**Allowed Locations**:
- `tests/`, `test/`, `__tests__/` - Standard test directories
- `tmp/`, `temp/`, `.tmp/` - Temporary directories (project-local)
- `_test.py`, `_spec.js` - When in test directories

**Examples**:
```
❌ src/api_test.py (in source directory)
❌ lib/utils_tmp.js (in library directory)
✅ tests/api_test.py (in test directory)
✅ tests/test_api.py (standard naming)
✅ tmp/scratch.py (in temp directory)
```

**Logic**: Check if file path contains test/temp directory in path

### 3.6 Python-Specific Naming Conventions

**Category**: Python Module Naming Standards

**Applies To**: Files ending with `.py` extension

**Rules**:
1. **Preferred**: `snake_case` - e.g., `user_handler.py`, `api_client.py`
2. **Acceptable**: `PascalCase` - e.g., `UserHandler.py` (for class-only modules)
3. **Blocked**:
   - `kebab-case`: `user-handler.py` (incompatible with Python imports)
   - `camelCase`: `userHandler.py` (violates PEP 8)
   - Mixed case: `User_Handler.py`, `API_Endpoint.py`

**Examples**:
```
❌ user-handler.py (kebab-case)
❌ userHandler.py (camelCase)
❌ User_Handler.py (mixed)
❌ API_Endpoint.py (mixed)
✅ user_handler.py (snake_case)
✅ api_endpoint.py (snake_case)
✅ UserHandler.py (PascalCase, single class)
```

**Regex Patterns**:
- Valid snake_case: `^[a-z][a-z0-9_]*\.py$`
- Valid PascalCase: `^[A-Z][a-zA-Z0-9]*\.py$`
- Invalid patterns: Contains hyphens, starts with uppercase + has underscores

**Exception**: Common Python files like `__init__.py`, `__main__.py`, `setup.py`

### 3.7 Allowlist (Always Permitted)

**Standard Files**:
- `README.md`, `LICENSE`, `CHANGELOG.md`
- `setup.py`, `pyproject.toml`, `requirements.txt`
- `Makefile`, `Dockerfile`, `.gitignore`
- `__init__.py`, `__main__.py`, `conftest.py`

**Configuration Files**:
- `.env.example`, `.env.local`, `.env.test`
- `config.yaml`, `settings.json`
- `.prettierrc`, `.eslintrc`, `tsconfig.json`

**Pattern**: Exact filename match (case-insensitive)

---

## 4. Implementation Details

### 4.1 File Structure

```
.claude/hooks/pre_tools/file_naming_enforcer.py
```

**Dependencies**:
```python
# UV Script Metadata
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# Standard Library Only
import json
import os
import re
import sys
from pathlib import Path
```

### 4.2 Core Algorithm

**High-Level Flow**:
```
1. Parse hook input from stdin
2. Extract file path based on tool type:
   - Write/Edit: tool_input["file_path"]
   - Bash: Parse command for file creation operations
3. Normalize path (resolve symlinks, handle relative paths)
4. Run validation pipeline:
   a. Check allowlist → allow if matches
   b. Check blocked extensions → deny if matches
   c. Check version suffixes → deny if matches
   d. Check iteration suffixes → deny if matches
   e. Check number suffixes → deny if matches
   f. Check test/temp location → deny if misplaced
   g. If .py file, check Python naming → deny if invalid
5. Output decision (allow/deny) with reason
```

### 4.3 Bash Command Parsing

**File Creation Detection** in Bash commands:

**Patterns to detect**:
1. **Redirects**: `>`, `>>`, `2>`, `&>`
   - `echo "data" > output.txt`
   - `cat input.txt > output.txt`

2. **Touch command**: `touch filename`
   - `touch file.txt`
   - `touch file1.txt file2.txt`

3. **Copy/Move**: `cp source dest`, `mv source dest`
   - `cp main.py main_backup.py`
   - `mv old.py new_v2.py`

**Extraction Logic**:
```python
def extract_file_paths_from_command(command: str) -> list[str]:
    """Extract file paths from bash command."""
    paths = []

    # Redirect operators
    redirect_pattern = r'[12&]?>>?\s+([^\s;|&]+)'
    paths.extend(re.findall(redirect_pattern, command))

    # Touch command
    touch_pattern = r'\btouch\s+(.*?)(?:;|&&|\||$)'
    touch_matches = re.findall(touch_pattern, command)
    for match in touch_matches:
        # Split on whitespace to get individual files
        paths.extend(match.split())

    # Copy/move destination
    cp_mv_pattern = r'\b(?:cp|mv)\s+\S+\s+(\S+)'
    paths.extend(re.findall(cp_mv_pattern, command))

    return [p.strip('"\'') for p in paths]
```

### 4.4 Validation Functions

**Extension Check**:
```python
def has_blocked_extension(file_path: str) -> bool:
    """Check if file has blocked extension."""
    blocked_exts = {'.backup', '.bak', '.old', '.orig', '.swp', '.swo'}
    path = Path(file_path)

    # Check for ~ suffix (editor backups)
    if path.name.endswith('~'):
        return True

    # Check extensions (case-insensitive)
    ext_lower = path.suffix.lower()
    return ext_lower in blocked_exts
```

**Version Suffix Check**:
```python
def has_version_suffix(file_path: str) -> bool:
    """Check if filename has version suffix."""
    stem = Path(file_path).stem  # Filename without extension
    pattern = r'(?i)[_-]?v(ersion)?[_-]?\d+(?:[_.-]\d+)*$'
    return bool(re.search(pattern, stem))
```

**Iteration Suffix Check**:
```python
def has_iteration_suffix(file_path: str) -> bool:
    """Check if filename has iteration suffix."""
    stem = Path(file_path).stem
    suffixes = [
        'final', 'fixed', 'fix', 'update', 'updated',
        'new', 'latest', 'copy', 'backup', 'old',
        'obsolete', 'modified', 'mod', 'revised', 'rev', 'corrected'
    ]
    pattern = r'(?i)[_-](' + '|'.join(suffixes) + r')$'
    return bool(re.search(pattern, stem))
```

**Number Suffix Check**:
```python
def has_number_suffix(file_path: str) -> bool:
    """Check if filename has meaningless number suffix."""
    stem = Path(file_path).stem

    # Semantic exceptions (don't block these)
    semantic_patterns = [
        r'\bpython[23]',
        r'\bhttp2?',
        r'\bbase64',
        r'\d{4}[_-]\d{2}[_-]\d{2}',  # Date format
    ]
    for pattern in semantic_patterns:
        if re.search(pattern, stem, re.I):
            return False

    # Check for trailing numbers
    pattern = r'[_-]?\d+$'
    return bool(re.search(pattern, stem))
```

**Python Naming Check**:
```python
def has_invalid_python_naming(file_path: str) -> bool:
    """Check if .py file follows Python naming conventions."""
    if not file_path.endswith('.py'):
        return False

    filename = Path(file_path).name

    # Allowlist special Python files
    special_files = {'__init__.py', '__main__.py', 'setup.py', 'conftest.py'}
    if filename in special_files:
        return False

    stem = Path(file_path).stem

    # Valid patterns
    snake_case = r'^[a-z][a-z0-9_]*$'
    pascal_case = r'^[A-Z][a-zA-Z0-9]*$'

    if re.match(snake_case, stem) or re.match(pascal_case, stem):
        return False

    return True  # Invalid naming
```

### 4.5 Error Messages

**Template Structure**:
```
📝 Blocked: {Category} naming convention violation

File: {file_path}

Why this is blocked:
  - {Reason 1}
  - {Reason 2}
  - {Reason 3}

Use Git instead:
  {Git alternative with example commands}

Recommended alternatives:
  - {Better filename 1}
  - {Better filename 2}
  - {Better filename 3}

Learn more: {Documentation URL}
```

**Example Error Messages**:

**1. Backup Extension**:
```
📝 Blocked: Backup file extension detected

File: script.py.backup

Why this is blocked:
  - Backup files clutter project directories
  - Cannot be tracked properly by git
  - Unclear which version is current
  - Violates professional project organization

Use Git instead:
  # Stash your changes
  git stash save "temporary backup of script.py"

  # Or create a branch
  git checkout -b backup/script-changes
  git add script.py
  git commit -m "backup: save current state"

Recommended alternatives:
  - Use git stash for temporary saves
  - Create feature branches for experiments
  - Use git tags for stable versions

Learn more: https://git-scm.com/docs/git-stash
```

**2. Version Suffix**:
```
📝 Blocked: Version suffix detected in filename

File: api_v2.py

Why this is blocked:
  - Multiple versions coexist, causing confusion
  - Unclear which version is current
  - Cannot track version history properly
  - Violates semantic versioning practices

Use Git instead:
  # Use branches for new versions
  git checkout -b feature/api-v2
  # Make changes to api.py
  git commit -m "feat: add v2 API endpoints"

  # Use tags for releases
  git tag v2.0.0
  git push origin v2.0.0

Recommended alternatives:
  - Keep single file: api.py
  - Use git branches: feature/v2-api
  - Use git tags: v2.0.0, v2.1.0
  - Document versions in CHANGELOG.md

Learn more: https://semver.org/
```

**3. Python Naming**:
```
🐍 Blocked: Invalid Python module naming

File: user-handler.py

Why this is blocked:
  - Hyphens in filenames incompatible with Python imports
  - Cannot import: 'import user-handler' (syntax error)
  - Violates PEP 8 module naming conventions
  - Inconsistent with Python community standards

Use proper Python naming:
  # snake_case (preferred)
  user_handler.py → from user_handler import UserHandler

  # PascalCase (for single-class modules)
  UserHandler.py → from UserHandler import UserHandler

Recommended alternatives:
  - user_handler.py (snake_case)
  - UserHandler.py (PascalCase)

Learn more: https://peps.python.org/pep-0008/#package-and-module-names
```

---

## 5. Security and Safety

### 5.1 Security Measures

1. **Path Traversal Prevention**:
   ```python
   # Normalize paths to prevent traversal attacks
   safe_path = os.path.normpath(file_path)
   project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

   # Ensure path is within project
   if not safe_path.startswith(project_dir):
       # Still validate, but don't block external paths
       pass
   ```

2. **Input Validation**:
   - Validate all JSON inputs before processing
   - Handle malformed commands gracefully
   - Sanitize file paths for display in errors

3. **Fail-Safe Behavior**:
   - Always exit with code 0 (success)
   - On parsing errors: allow operation
   - On validation errors: allow operation
   - Only deny on clear violations

4. **Resource Limits**:
   - No file content reading (only path analysis)
   - Regex patterns use bounded quantifiers
   - No network calls or external processes

### 5.2 Error Handling

**Robustness Strategy**: "Fail open, not closed"

```python
def main():
    try:
        result = parse_hook_input()
        if result is None:
            output_decision("allow", "Failed to parse input")
            return

        tool_name, tool_input = result

        # Validation logic
        violation = validate_file_naming(tool_name, tool_input)

        if violation:
            output_decision("deny", violation, suppress_output=False)
        else:
            output_decision("allow", "Naming conventions validated")

    except Exception as e:
        # Fail-safe: allow operation on unexpected errors
        output_decision("allow", f"Hook error (allowing): {str(e)}")
```

### 5.3 Performance

**Optimization Strategies**:
1. Early returns for allowlisted files
2. Compiled regex patterns (module-level)
3. No file I/O operations
4. Minimal string operations

**Performance Targets**:
- < 50ms for Write/Edit operations
- < 100ms for Bash commands (parsing overhead)
- < 10 MB memory usage

---

## 6. Testing Strategy

### 6.1 Test Structure

**Location**: `tests/claude-hook/pre_tools/test_file_naming_enforcer.py`

**Framework**: pytest with distributed testing
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_file_naming_enforcer.py
```

### 6.2 Test Categories

**1. Blocked Extension Tests**:
```python
def test_blocks_backup_extensions():
    """Test that .backup, .bak, .old extensions are blocked."""
    assert is_blocked("script.py.backup")
    assert is_blocked("config.json.bak")
    assert is_blocked("utils.py.old")
    assert is_blocked("README.md~")
```

**2. Version Suffix Tests**:
```python
def test_blocks_version_suffixes():
    """Test that version suffixes are blocked."""
    assert is_blocked("api_v2.py")
    assert is_blocked("parser-v3.js")
    assert is_blocked("handler_version2.ts")
    assert not is_blocked("http2_client.py")  # Semantic
```

**3. Iteration Suffix Tests**:
```python
def test_blocks_iteration_suffixes():
    """Test that iteration suffixes are blocked."""
    assert is_blocked("script_final.py")
    assert is_blocked("code_fixed.js")
    assert is_blocked("test-update.py")
```

**4. Python Naming Tests**:
```python
def test_python_naming_conventions():
    """Test Python file naming conventions."""
    assert is_blocked("user-handler.py")  # kebab-case
    assert is_blocked("userHandler.py")   # camelCase
    assert not is_blocked("user_handler.py")  # snake_case
    assert not is_blocked("UserHandler.py")   # PascalCase
```

**5. Bash Command Tests**:
```python
def test_bash_redirect_detection():
    """Test file path extraction from bash redirects."""
    cmd = 'echo "data" > output_v2.txt'
    assert is_blocked_bash(cmd)
```

**6. Allowlist Tests**:
```python
def test_allowlist_files():
    """Test that standard files are always allowed."""
    assert not is_blocked("README.md")
    assert not is_blocked("setup.py")
    assert not is_blocked("__init__.py")
```

**7. Edge Cases**:
```python
def test_edge_cases():
    """Test edge cases and boundary conditions."""
    assert not is_blocked("")  # Empty path
    assert not is_blocked("v2ray.py")  # v2 in name, not suffix
    assert not is_blocked("python3_utils.py")  # Semantic
    assert not is_blocked("tests/test_api.py")  # Test file
```

### 6.3 Integration Tests

**End-to-End Tests**:
```python
def test_full_hook_execution():
    """Test complete hook execution with stdin/stdout."""
    import subprocess

    input_json = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": "script_v2.py", "content": "test"}
    })

    result = subprocess.run(
        ["uv", "run", ".claude/hooks/pre_tools/file_naming_enforcer.py"],
        input=input_json,
        capture_output=True,
        text=True
    )

    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
```

---

## 7. Configuration and Deployment

### 7.1 Settings Configuration

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
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/file_naming_enforcer.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

**Placement**: Add to existing PreToolUse hooks array

### 7.2 Installation Steps

1. **Create Hook Script**:
   ```bash
   # Script will be created at:
   .claude/hooks/pre_tools/file_naming_enforcer.py
   ```

2. **Make Executable**:
   ```bash
   chmod +x .claude/hooks/pre_tools/file_naming_enforcer.py
   ```

3. **Update Settings**:
   - Add hook configuration to `.claude/settings.json`
   - Ensure proper JSON formatting

4. **Verify Registration**:
   ```bash
   # In Claude Code
   /hooks
   # Should show file_naming_enforcer.py registered
   ```

5. **Run Tests**:
   ```bash
   uv run pytest -n auto tests/claude-hook/pre_tools/test_file_naming_enforcer.py
   ```

### 7.3 Disabling the Hook

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Write|Edit|Bash",
      //   "hooks": [
      //     {
      //       "type": "command",
      //       "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/file_naming_enforcer.py"
      //     }
      //   ]
      // }
    ]
  }
}
```

**Option 2**: Local override in `.claude/settings.local.json`
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

---

## 8. Educational Messaging

### 8.1 Key Messaging Points

**For each violation type, emphasize**:
1. **Why it's problematic**: Concrete technical issues
2. **Git alternative**: Specific commands to use instead
3. **Better practices**: Professional workflow recommendations
4. **Learning resources**: Links to documentation

### 8.2 Progressive Education

**First violation**: Detailed explanation with examples
**Subsequent violations**: Shorter message with link to docs
**Repeated violations**: Suggest disabling hook if intentional

---

## 9. Integration Considerations

### 9.1 Interaction with Other Hooks

**Complementary Hooks**:
1. `pep8_naming_enforcer.py` - Validates Python CODE naming (this validates FILE naming)
2. `tmp_creation_blocker.py` - Prevents /tmp usage (this prevents poor naming)
3. `uv_dependency_blocker.py` - No interaction

**Execution Order**: Parallel execution (no dependencies)

### 9.2 Project-Specific Customization

**Configuration File** (future enhancement):
`.claude/hooks/pre_tools/file_naming_enforcer.yaml`
```yaml
# Optional: Customize patterns
blocked_extensions:
  - .backup
  - .bak
  - .old

allowed_patterns:
  - 'test_*.py'  # Allow test files anywhere

python_naming:
  enforce: true
  allow_pascal_case: true
```

---

## 10. Known Limitations

### 10.1 Cannot Detect

1. **Indirect Creation**:
   ```bash
   FILE="script_v2.py"
   echo "data" > $FILE
   ```

2. **Complex Bash Syntax**:
   ```bash
   for i in {1..5}; do touch "file_$i.py"; done
   ```

3. **External Tool Output**:
   ```bash
   python generate.py --output script_final.py
   ```

### 10.2 Design Trade-offs

**Priority**: Prevent false negatives (missing violations) over false positives (blocking valid files)

**Rationale**:
- Missing a violation = poor project hygiene
- Blocking valid file = user can temporarily disable hook

---

## 11. Success Metrics

### 11.1 Quantitative Metrics

- **Detection Rate**: > 95% of common poor naming patterns
- **False Positive Rate**: < 1% on standard project files
- **Performance**: < 100ms execution time
- **Reliability**: Zero crashes on malformed input

### 11.2 Qualitative Metrics

- Users report cleaner project directories
- Developers learn to use git features
- Reduced code review comments about naming
- Better project organization over time

---

## 12. Future Enhancements

### 12.1 Potential Features

1. **Configurable Rules**: YAML configuration for project-specific rules
2. **Auto-Suggest**: Automatically suggest corrected filenames
3. **Git Integration**: Check if file already in git before blocking
4. **Smart Context**: Allow `_tmp` in recognized temp workflows
5. **Language-Specific Rules**: TypeScript, Go, Rust naming conventions

### 12.2 Advanced Detection

1. **Semantic Analysis**: Understand if "v2" is actually part of API name
2. **Project Structure**: Learn project conventions over time
3. **Team Patterns**: Adapt to team-specific naming preferences

---

## 13. References

### 13.1 Documentation

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Git Stash Documentation](https://git-scm.com/docs/git-stash)
- [Semantic Versioning](https://semver.org/)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)

### 13.2 Related Specifications

- [PEP 8 Naming Enforcer](./pep8-naming-enforcer-spec.md)
- [Temporary Directory Blocker](./tmp-creation-blocker-spec.md)
- [UV Dependency Blocker](./uv-dependency-blocker-spec.md)

---

## Appendix A: Complete Regex Patterns

```python
# Backup extensions
BACKUP_EXTENSIONS = r'\.(backup|bak|old|orig|swp|swo)$|~$'

# Version suffixes
VERSION_SUFFIX = r'(?i)[_-]?v(ersion)?[_-]?\d+(?:[_.-]\d+)*$'

# Iteration suffixes
ITERATION_SUFFIX = r'(?i)[_-](final|fixed?|update[d]?|new|latest|copy|backup|old|obsolete|modified|mod|revised|rev|corrected)$'

# Number suffixes (with semantic exceptions)
NUMBER_SUFFIX = r'[_-]?\d+$'
SEMANTIC_NUMBERS = r'(python[23]|http2?|base64|\d{4}[_-]\d{2}[_-]\d{2})'

# Python naming
PYTHON_SNAKE_CASE = r'^[a-z][a-z0-9_]*\.py$'
PYTHON_PASCAL_CASE = r'^[A-Z][a-zA-Z0-9]*\.py$'

# Bash file creation
BASH_REDIRECT = r'[12&]?>>?\s+([^\s;|&]+)'
BASH_TOUCH = r'\btouch\s+(.*?)(?:;|&&|\||$)'
BASH_CP_MV = r'\b(?:cp|mv)\s+\S+\s+(\S+)'
```

---

## Appendix B: Example Hook Output

**Successful Validation**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "File naming conventions validated"
  },
  "suppressOutput": false
}
```

**Blocked Operation**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "📝 Blocked: Version suffix detected...[full message]"
  },
  "suppressOutput": false
}
```

---

**End of Specification**
