# PostToolUse Hooks

This directory contains Claude Code hooks that execute after tools have completed their operations.

## Available Hooks

### unified_python_antipattern_hook.py

**Purpose**: Detects 40+ Python-specific antipatterns across 7 categories using AST-based analysis, providing comprehensive code quality feedback beyond what formatters and type checkers catch.

**Hook Event**: PostToolUse
**Monitored Tools**: Write, Edit, NotebookEdit
**Version**: 1.0.0

#### Why Use This Hook?

Type checkers like basedpyright catch type errors, and linters like ruff catch style issues, but many Python antipatterns go undetected:

- **Runtime Issues**: Mutable defaults, dangerous functions like eval(), assert in production code
- **Security Vulnerabilities**: SQL injection, command injection, hardcoded secrets, weak cryptography
- **Performance Problems**: String concatenation in loops, inefficient operations
- **Python Gotchas**: Using `is` for equality, modifying lists while iterating, silent exception swallowing
- **Complexity Issues**: Too many parameters, high cyclomatic complexity, overly long functions
- **Resource Management**: Missing context managers, unreleased resources
- **Code Organization**: Wildcard imports, poor structure

This hook uses Python's AST (Abstract Syntax Tree) to analyze code structure and detect these antipatterns that are legal Python but represent poor practices.

#### Detected Antipattern Categories

**1. Runtime Antipatterns** (R001-R011):
- R001: Mutable default arguments (HIGH)
- R002: Dangerous functions (eval, exec) (HIGH)
- R003: Bare except clauses (MEDIUM)
- R004: Assert statements in production (HIGH)
- R005: Global keyword misuse (MEDIUM)
- R006: Mutable class variables (HIGH)
- R008: Shadowing builtins (MEDIUM)
- R009: __eq__ without __hash__ (HIGH)

**2. Performance Antipatterns** (P001-P010):
- P001: String concatenation in loops (MEDIUM)
- P005: List concatenation in loops (MEDIUM)

**3. Complexity Antipatterns** (C001-C010):
- C003: High cyclomatic complexity (HIGH)
- C004: Too many parameters (>7) (MEDIUM)
- C005: Unnecessary else after return (LOW)
- C010: Long functions (>50 lines) (HIGH)

**4. Security Antipatterns** (S001-S010):
- S001: SQL injection (CRITICAL)
- S002: Command injection (shell=True) (CRITICAL)
- S003: Hardcoded secrets (CRITICAL)
- S004: Weak cryptography (MD5, SHA1) (HIGH)
- S005: Unsafe deserialization (pickle) (HIGH)
- S007: Weak random for security (HIGH)

**5. Code Organization** (O001-O007):
- O003: Wildcard imports (HIGH)

**6. Resource Management** (M001-M005):
- M003: __enter__ not returning self (MEDIUM)

**7. Python Gotchas** (G001-G010):
- G001: Using 'is' with literals (HIGH)
- G002: Using == with None (MEDIUM)
- G003: Type checking with type() (MEDIUM)
- G004: Modifying list while iterating (HIGH)
- G005: Silent exception swallowing (HIGH)
- G006: Comparing with True/False (LOW)

#### Example Output

**Non-Critical Issues** (Warning, Non-Blocking):
```
⚠️ Python antipatterns detected in example.py:

[R001:HIGH] Mutable default argument on line 5
  def process_items(items=[]):
  Fix: Use None and create mutable object inside function

[P001:MEDIUM] String/list concatenation in loop using += on line 9
  result += str(item)
  Fix: Use list.append() and ''.join() for strings

2 issues found (1 HIGH, 1 MEDIUM)
```

**Critical Issues** (Blocking):
```
❌ CRITICAL security issue detected in database.py

[S001:CRITICAL] Potential SQL injection (f-string in execute) on line 15
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

  This allows SQL injection attacks!

  Fix: Use parameterized queries:
  query = "SELECT * FROM users WHERE id = %s"
  cursor.execute(query, (user_id,))

Please fix this security vulnerability before continuing.
```

#### Configuration

The hook is configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/unified_python_antipattern_hook.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Environment Variables**:
- `PYTHON_ANTIPATTERN_ENABLED`: Enable/disable hook (default: "true")
- `PYTHON_ANTIPATTERN_LEVELS`: Severity levels to report (default: "CRITICAL,HIGH,MEDIUM,LOW")
- `PYTHON_ANTIPATTERN_BLOCK_CRITICAL`: Block on critical issues (default: "true")
- `PYTHON_ANTIPATTERN_DISABLED`: Comma-separated pattern IDs to disable (e.g., "R001,P001,C005")
- `PYTHON_ANTIPATTERN_MAX_ISSUES`: Maximum issues to report (default: "10")
- `PYTHON_ANTIPATTERN_SKIP_TESTS`: Skip test files (default: "false")

**Example Configuration**:
```bash
# Disable specific patterns
export PYTHON_ANTIPATTERN_DISABLED="C005,G006"

# Only report critical and high severity
export PYTHON_ANTIPATTERN_LEVELS="CRITICAL,HIGH"

# Don't block on critical (warning only)
export PYTHON_ANTIPATTERN_BLOCK_CRITICAL="false"
```

#### Behavior

**When Hook Triggers**:
- Write tool creates new Python file → Analyzes for antipatterns
- Edit tool modifies existing Python file → Analyzes for antipatterns
- NotebookEdit tool modifies notebook cell → Analyzes Python code

**Blocking vs Non-Blocking**:
- **Non-Blocking** (default): Provides warnings for CRITICAL, HIGH, MEDIUM, LOW issues
- **Blocking**: Stops Claude's flow if CRITICAL security issues found (configurable)

**What Gets Analyzed**:
- File extension: `.py`, `.pyi` only
- File location: Must be within `$CLAUDE_PROJECT_DIR`
- File size: Up to 10,000 lines (larger files skipped)
- Valid Python: Syntax errors are skipped (caught by other tools)

**What Gets Skipped**:
- Non-Python files
- Files outside project directory
- Files with syntax errors
- Very large files (>10,000 lines)
- Failed tool operations
- Test files (if `PYTHON_ANTIPATTERN_SKIP_TESTS="true"`)

#### Testing

**Unit Tests**:
```bash
# Run comprehensive test suite (43 tests)
uv run pytest tests/claude_hook/post_tools/test_unified_python_antipattern.py -v

# Run with coverage
uv run pytest tests/claude_hook/post_tools/test_unified_python_antipattern.py --cov --cov-report=html
```

**Manual Testing**:
```bash
# Test with mock input
echo '{"session_id":"test","transcript_path":"/tmp/test.jsonl","cwd":"'$(pwd)'","hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"'$(pwd)'/test.py","content":"dummy"},"tool_response":{"filePath":"'$(pwd)'/test.py","success":true}}' | uv run .claude/hooks/post_tools/unified_python_antipattern_hook.py
```

#### Performance

- **Execution Time**: < 1 second for typical files (<1000 lines)
- **Memory Usage**: < 50 MB for most files
- **Analysis Method**: AST traversal (no code execution)
- **Timeout**: 30 seconds (configurable)
- **Dependencies**: None (uses only Python standard library)

#### Security

The hook is safe because:
- **No Code Execution**: Only parses AST, never executes code
- **Path Validation**: Prevents path traversal attacks
- **Project Boundary**: Only analyzes files within project
- **Safe Subprocess**: No subprocess calls, pure Python
- **Error Isolation**: Exceptions never crash Claude
- **Read-Only**: Analyzes but never modifies files

#### Integration with Other Hooks

**Execution Order** (all run in parallel but reported sequentially):
1. **unified_python_antipattern_hook.py** - Detects antipatterns
2. **ruff_checking.py** - Formats and lints code
3. **basedpyright_checking.py** - Type checks code
4. **vulture_checking.py** - Finds dead code

**Complementary Coverage**:
- **This Hook**: Runtime issues, security, Python gotchas, complexity
- **Ruff**: Style issues, simple lint violations
- **basedpyright**: Type safety, type annotations
- **Vulture**: Unused code, imports, functions

Together, these hooks provide comprehensive Python code quality enforcement.

#### Known Limitations

- **AST-based**: Can only detect patterns visible in code structure
- **No Dataflow Analysis**: Cannot track variable values across scopes
- **Context-Limited**: Some patterns need broader context than single file
- **False Positives**: Some patterns may be intentional (use env vars to disable)
- **No Auto-Fix**: Only detects and reports, doesn't automatically fix

**Patterns Not Detected**:
- Cross-file circular dependencies
- Race conditions in concurrent code
- Logic errors requiring runtime analysis
- Patterns requiring whole-program analysis

#### Troubleshooting

**Hook not detecting expected issues**:
- Verify pattern is implemented (check test suite)
- Check if pattern is disabled: `echo $PYTHON_ANTIPATTERN_DISABLED`
- Verify severity level is enabled: `echo $PYTHON_ANTIPATTERN_LEVELS`
- Enable debug mode: `export PYTHON_ANTIPATTERN_DEBUG=true`

**Too many false positives**:
- Disable specific patterns: `export PYTHON_ANTIPATTERN_DISABLED="R001,C005"`
- Reduce severity levels: `export PYTHON_ANTIPATTERN_LEVELS="CRITICAL,HIGH"`
- Adjust max issues: `export PYTHON_ANTIPATTERN_MAX_ISSUES="5"`

**Critical issues blocking workflow**:
- Disable blocking: `export PYTHON_ANTIPATTERN_BLOCK_CRITICAL="false"`
- Or fix the security issues (recommended)

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/post_tools/unified_python_antipattern-spec.md)
- [Test Suite](../../../tests/claude_hook/post_tools/test_unified_python_antipattern.py)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)

---

### ruff_checking.py

**Purpose**: Automatically formats and checks Python files after Write, Edit, or NotebookEdit operations using Ruff, providing immediate feedback about code style issues and lint violations.

**Hook Event**: PostToolUse
**Monitored Tools**: Write, Edit, NotebookEdit
**Version**: 1.0.0

#### Why Use This Hook?

During AI-assisted development, Claude Code generates significant amounts of Python code that may not adhere to consistent style and quality standards:

- **Inconsistent Formatting**: Code generated at different times may have different spacing, indentation, or line breaks
- **Lint Violations**: Claude may produce code with common Python antipatterns (unused imports, undefined names, etc.)
- **Manual Cleanup Burden**: Developers must manually run formatters and linters after each generation
- **Style Drift**: Without automated enforcement, code style can drift from project standards
- **Slower Feedback Loop**: Discovering formatting issues later in the workflow slows development
- **Context Switching**: Constantly switching between generating code and formatting it breaks flow

This hook ensures every Python file is automatically formatted and linted immediately after creation or modification, maintaining consistent code quality throughout development.

#### How It Works

The hook intercepts PostToolUse operations for Write, Edit, and NotebookEdit tools:

1. **Validate Target**: Checks if the file is Python (.py, .pyi) and within project directory
2. **Run Formatting**: Executes `ruff format` to apply consistent code style
3. **Run Linting**: Executes `ruff check --fix` to auto-fix common violations
4. **Provide Feedback**: Sends informative messages to Claude about changes made
5. **Non-Blocking**: Never blocks operations - formatting/linting happens in background

#### Detected and Fixed Issues

**Formatting Issues Fixed**:
- Inconsistent indentation (spaces vs tabs)
- Line length violations (> 88 characters default)
- Trailing whitespace
- Missing blank lines (between classes/functions)
- Quote style inconsistencies
- Spacing around operators and commas
- Import statement ordering

**Lint Issues Auto-Fixed**:
- Unused imports (`import os` when os is never used)
- Unused variables (`x = 42` when x is never referenced)
- Undefined names (typos in variable/function names)
- Star import usage (`from module import *`)
- Multiple statements on one line
- Unnecessary pass statements
- Redundant return statements

**Lint Issues Reported** (cannot auto-fix):
- Complexity warnings
- Security issues
- Performance concerns
- Style violations requiring manual review

#### Examples

**Auto-Formatted Code**:
```python
# Before: Written by Claude with inconsistent formatting
def calculate_total(items,tax_rate):
  total=sum([item["price"]for item in items])
  return total*(1+tax_rate)

# After: Automatically formatted by ruff_checking.py
def calculate_total(items, tax_rate):
    total = sum([item["price"] for item in items])
    return total * (1 + tax_rate)
```

**Auto-Fixed Lint Issues**:
```python
# Before: Written by Claude with unused imports
import os
import sys
import json

def parse_config(text):
    return json.loads(text)

# After: Ruff automatically removes unused imports
import json

def parse_config(text):
    return json.loads(text)
```

**Feedback Messages**:
```
✅ Ruff: formatted in example.py
✅ Ruff: fixed 2 lint issues in example.py
✅ Ruff: formatted + fixed 3 lint issues in example.py
⚠️ Ruff: 1 remaining issue in example.py (run: ruff check example.py)
```

#### Behavior Details

**When Hook Triggers**:
- Write tool creates new Python file → Formats and checks
- Edit tool modifies existing Python file → Formats and checks
- NotebookEdit tool modifies notebook cell → Formats and checks Python code

**What Gets Validated**:
- File extension: `.py`, `.pyi` (Python stub files)
- File location: Must be within `$CLAUDE_PROJECT_DIR`
- Tool success: Only processes if tool execution succeeded
- File existence: Verifies file exists before processing

**What Gets Skipped**:
- Non-Python files (`.js`, `.json`, `.md`, etc.)
- Files outside project directory
- Failed tool operations
- Missing or deleted files
- Empty files

**Feedback Modes**:
- **Silent**: No changes needed, no output
- **Success**: "✅ Ruff: [changes] in [file]"
- **Warning**: "⚠️ Ruff: [remaining issues] (run: ...)"
- **Error**: "⚠️ Ruff [format/check] error: [message]"

#### Configuration

The hook is registered in `.claude/settings.json`:

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

**Configuration Options**:
- `timeout`: Maximum execution time (default: 30 seconds)
- `matcher`: Tool patterns to trigger on (Write|Edit|NotebookEdit)

**Ruff Configuration**:
Ruff respects project-level configuration files:
- `pyproject.toml` - `[tool.ruff]` section
- `ruff.toml` - Dedicated Ruff configuration
- `.ruff.toml` - Hidden Ruff configuration

Example `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Ignore line length

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PostToolUse": [
      // {
      //   "matcher": "Write|Edit|NotebookEdit",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PostToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the comprehensive test suite:
```bash
uv run pytest -n auto tests/claude_hook/post_tools/test_ruff_checking.py
```

Manual testing with real hook input:
```bash
# Create test input
cat > ./workspace/test_hook_input.json << 'EOF'
{
  "session_id": "test123",
  "transcript_path": "/tmp/transcript.jsonl",
  "cwd": "/project",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/example.py",
    "content": "def foo( ):\n  return  42"
  },
  "tool_response": {
    "filePath": "/project/example.py",
    "success": true
  }
}
EOF

# Test the hook
cat ./workspace/test_hook_input.json | uv run .claude/hooks/post_tools/ruff_checking.py
```

**Expected Output**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Ruff: formatted in example.py"
  },
  "suppressOutput": true
}
```

#### Performance

- **Execution Time**: < 2 seconds for typical Python files (< 1000 lines)
- **Memory Usage**: < 30 MB for typical files
- **File Size Handling**: Efficiently processes files up to several MB
- **Parallel Safe**: Can run alongside other PostToolUse hooks
- **Timeout Protection**: 10-second timeout per ruff command (format/check)
- **Dependencies**: Ruff (installed via UV inline script metadata)

**Performance Optimizations**:
- Checks if formatting needed before actually formatting
- Uses ruff's parallel processing for multi-file projects
- JSON output parsing for efficient violation counting
- Early exit for non-Python files

#### Security

The hook implements several security measures:

- **Path Validation**: Prevents path traversal attacks (no `..` in paths)
- **Project Boundary**: Only processes files within `$CLAUDE_PROJECT_DIR`
- **Safe Subprocess**: Uses `subprocess.run()` without `shell=True`
- **Timeout Protection**: Both format and check operations have 10-second timeouts
- **Error Isolation**: Exceptions never crash Claude, always fail-safe to allow
- **No Code Execution**: Ruff only parses and formats, never executes code
- **Read-Only Analysis**: Hook analyzes but modifications are done by ruff itself

#### Integration with Other Tools

**Works Well With**:
- **basedpyright**: Type checking (separate hook or manual)
- **pytest**: Testing framework (run separately)
- **mypy**: Alternative type checker
- **black**: Alternative formatter (use ruff or black, not both)
- **flake8**: Alternative linter (ruff replaces flake8)
- **isort**: Import sorting (ruff includes isort functionality)

**Replaces**:
- black (ruff format is black-compatible)
- flake8 (ruff check covers flake8 rules)
- isort (ruff handles import sorting)
- pyupgrade (ruff includes pyupgrade rules)
- autoflake (ruff removes unused imports)

**Relationship with Pre-Tool Hooks**:
- `pep8_naming_enforcer.py` (PreToolUse) validates naming before write
- `ruff_checking.py` (PostToolUse) formats/lints after write
- Together: Complete code quality enforcement

#### Known Limitations

The hook cannot:
- **Fix All Lint Issues**: Some require manual intervention (complexity, logic errors)
- **Handle Syntax Errors**: Files with syntax errors are skipped (Python will catch them)
- **Process Large Files Instantly**: Very large files (> 100k lines) may timeout
- **Customize Per-File**: Uses project-wide ruff configuration
- **Validate Notebook Metadata**: Only processes Python code cells in notebooks

**Syntax Error Behavior**:
```python
# If Claude writes this invalid code:
def foo(
# Hook will skip it (ruff can't format invalid syntax)
# Python will error when you try to run it
```

**Workaround**: Fix syntax errors, then re-run ruff manually or edit the file again.

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON (use `jq . .claude/settings.json`)
3. Ensure script is executable: `chmod +x .claude/hooks/post_tools/ruff_checking.py`
4. Check ruff is available: `uv run ruff --version`
5. Enable debug mode: `claude --debug`

**No feedback shown**:
- Hook uses `suppressOutput: true` by default (feedback shown only in transcript mode)
- Press Ctrl-R to enable transcript mode and see hook output
- Check `.claude/hooks/universal_hook_logger.py` logs for execution history

**Formatting not applied**:
- Check if file was actually modified (use `git diff`)
- Verify ruff configuration isn't disabling formatting
- Check ruff logs: `uv run ruff format --check file.py --verbose`
- File may already be formatted correctly

**Timeout errors**:
- Large files may exceed 10-second timeout per operation
- Increase timeout in settings.json
- Or process large files in smaller chunks
- Or disable hook temporarily for large refactorings

**Ruff not found**:
- Hook uses UV to install ruff automatically
- Ensure UV is installed: `uv --version`
- Check inline script metadata is correct
- Manually test: `uv run --with ruff ruff --version`

**Different results than manual ruff**:
- Hook runs in UV environment with specific ruff version
- Manual ruff may use different version/configuration
- Check ruff version: `uv run ruff --version`
- Use same configuration for consistency

#### False Positives vs False Negatives

**Trade-off**: Prioritize code quality over potential noise

- **False Positive**: Format already-good code → Minor inconvenience (very low cost)
- **False Negative**: Miss formatting issues → Inconsistent codebase (higher cost)

**Decision**: Run on all Python files, even if no changes needed (silent success).

**Mitigation**: Ruff is very fast (<100ms for most files), minimal overhead.

#### Relationship with Ruff Configuration

**Configuration Precedence** (highest to lowest):
1. Command-line flags (not used by hook)
2. `ruff.toml` or `.ruff.toml` in project root
3. `[tool.ruff]` in `pyproject.toml`
4. Ruff defaults (black-compatible)

**Recommended Setup**:
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]
ignore = [
    "E501",  # Line too long (let formatter handle)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

#### Cross-Platform Support

The hook works on:
- **Unix/Linux**: Full support, optimal performance
- **macOS**: Full support, symlink resolution
- **Windows**: Full support, handles Windows paths correctly

**Path Handling**:
- Uses `pathlib.Path` for cross-platform path operations
- Normalizes paths to handle different separators
- Resolves symlinks on Unix/macOS
- Handles Windows drive letters correctly

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/post_tools/ruff-checking-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Test Suite](../../../tests/claude_hook/post_tools/test_ruff_checking.py)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)
- [Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)

---

### basedpyright_checking.py

**Purpose**: Automatically enforces complete type safety for all Python files after Write, Edit, or NotebookEdit operations using basedpyright strict type checking.

**Hook Event**: PostToolUse
**Monitored Tools**: Write, Edit, NotebookEdit
**Version**: 1.0.0

#### Why Use This Hook?

Type safety is crucial for maintaining reliable Python codebases:

- **Catch Type Errors Early**: Detect type mismatches before runtime
- **Enforce Type Annotations**: Ensure all code has proper type hints
- **Prevent Any Types**: Block usage of `Any` type (reportAny=true)
- **Strict Checking**: basedpyright is stricter than mypy or pyright
- **Zero Tolerance**: No type errors allowed, period
- **Documentation**: Type hints serve as inline documentation
- **Refactoring Safety**: Type checker catches breaking changes

This hook ensures that Claude Code cannot proceed if type errors exist, maintaining strict type safety standards across your entire codebase.

#### How It Works

The hook executes after file modifications:

1. **Validate Target**: Checks if file is Python (.py, .pyi) and within project
2. **Run Type Checker**: Executes `basedpyright --outputjson <file>`
3. **Parse Results**: Parses JSON output for structured error information
4. **Block on Errors**: BLOCKS Claude's workflow if any type errors found
5. **Provide Details**: Shows each error with line number and explanation
6. **Fail-Safe**: Infrastructure errors are non-blocking (missing basedpyright, etc.)

#### Detected Type Issues

**Type Errors Caught**:
- Type mismatches (`str` assigned to `int` variable)
- Missing type annotations on function parameters/returns
- Usage of `Any` type (reportAny=true)
- Unknown attributes on objects
- Incorrect argument types in function calls
- Missing return statements in typed functions
- Incompatible type assignments
- Union type errors
- Generic type parameter mismatches
- Protocol implementation errors

**Configuration**: Uses `pyrightconfig.json` in project root:
```json
{
  "typeCheckingMode": "strict",
  "reportAny": true,
  "reportMissingTypeStubs": true,
  "reportUnknownVariableType": true,
  "pythonVersion": "3.12"
}
```

#### Example Output

**Blocking on Type Errors**:
```
❌ Type checking failed: 3 errors found in example.py

Error 1 (line 5): Expression of type "str" is not assignable to declared type "int"
  Variable "count" has type "int" but receives "str"

Error 2 (line 8): Argument of type "Any" is not assignable to parameter "value" of type "int" in function "process"
  Type parameter is unknown

Error 3 (line 12): "foo" is not a known attribute of "None"
  Object of type "None" has no attribute "foo"

Please fix all type errors before continuing.
Run: basedpyright /path/to/example.py
```

**Silent Success** (no type errors):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Type check passed for example.py"
  },
  "suppressOutput": true
}
```

#### Configuration

Hook registration in `.claude/settings.json`:

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

**Timeout**: 15 seconds (sufficient for most files)

**Project Configuration** (`pyrightconfig.json`):
```json
{
  "typeCheckingMode": "strict",
  "reportAny": true,
  "reportMissingTypeStubs": false,
  "reportUnknownVariableType": true,
  "reportUnknownParameterType": true,
  "reportUnknownMemberType": false,
  "pythonVersion": "3.12",
  "pythonPlatform": "All"
}
```

#### Disabling the Hook

**Temporarily disable** (for rapid prototyping):
```bash
# Comment out in .claude/settings.json
# Or use .claude/settings.local.json to override
```

**Skip specific files**:
- Add `# type: ignore` at file top
- Use `# pyright: basic` for less strict checking
- Exclude in `pyrightconfig.json`: `"exclude": ["tests/", "scripts/"]`

#### Testing

Run tests:
```bash
uv run pytest tests/claude_hook/post_tools/test_basedpyright_checking.py -v
```

Manual test with hook input:
```bash
echo '{
  "session_id": "test",
  "transcript_path": "/tmp/transcript.jsonl",
  "cwd": "'$(pwd)'",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {"file_path": "'$(pwd)'/example.py"},
  "tool_response": {"success": true}
}' | uv run .claude/hooks/post_tools/basedpyright_checking.py
```

#### Performance

- **Execution Time**: < 3 seconds for typical files (< 1000 lines)
- **Memory Usage**: < 100 MB for typical files
- **Incremental**: basedpyright caches type information for faster subsequent checks
- **Parallel Safe**: Can run alongside other hooks
- **Dependencies**: basedpyright (installed via UV)

#### Security

- **Path Validation**: Prevents path traversal attacks
- **Project Boundary**: Only checks files within `$CLAUDE_PROJECT_DIR`
- **Safe Subprocess**: Uses `subprocess.run()` without `shell=True`
- **Timeout Protection**: 15-second timeout prevents hanging
- **Error Isolation**: Infrastructure errors don't crash Claude
- **No Code Execution**: Only analyzes, never executes code

#### Integration with Other Tools

**Works Well With**:
- **ruff**: Formatting and linting (separate concerns)
- **mypy**: Alternative type checker (use one or the other)
- **pytest**: Testing framework
- **vulture**: Dead code detection

**Relationship with Other Hooks**:
- Runs AFTER ruff (formatting should be done before type checking)
- Runs BEFORE vulture (dead code detection)
- Independent of antipattern hook (different concerns)

#### Known Limitations

- **Blocking**: Will stop Claude's workflow on ANY type error
- **Strict Mode**: May catch false positives in valid dynamic Python code
- **Third-Party Stubs**: Requires type stubs for external libraries
- **Learning Curve**: Team must understand Python type system
- **Configuration Sensitive**: pyrightconfig.json must be properly configured

**When Type Checking May Fail**:
- Missing type stubs for third-party libraries
- Dynamic code that's hard to type (e.g., `getattr`, `setattr`)
- Incomplete type annotations in existing code
- Complex generic types

**Workarounds**:
- Use `# type: ignore` comments for specific lines
- Install type stubs: `pip install types-requests`
- Use `cast()` for complex type assertions
- Gradually adopt type hints (start with `# pyright: basic`)

#### Troubleshooting

**Hook always blocking**:
- Check `pyrightconfig.json` is not too strict
- Verify type annotations are complete
- Install missing type stubs for libraries
- Use `# type: ignore` for unavoidable dynamic code

**basedpyright not found**:
- Hook uses UV to install automatically
- Ensure UV is available: `uv --version`
- Check inline script dependencies
- Manually test: `uv run --with basedpyright basedpyright --version`

**Different results than manual basedpyright**:
- Hook uses specific basedpyright version from UV
- Manual basedpyright may use different version
- Check version: `uv run basedpyright --version`
- Ensure same `pyrightconfig.json` configuration

**Performance issues**:
- Large files (>5000 lines) may timeout
- Increase timeout in settings.json: `"timeout": 30`
- Consider splitting large files
- Or temporarily disable for large refactorings

#### Related Documentation

- [basedpyright Documentation](https://docs.basedpyright.com/)
- [Python Type Hints Guide](https://docs.python.org/3/library/typing.html)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [pyrightconfig Schema](https://github.com/DetachHead/basedpyright/blob/main/docs/configuration.md)

---

### vulture_checking.py

**Purpose**: Automatically detects dead code (unused functions, classes, variables, imports, and attributes) in Python files after Write or Edit operations.

**Hook Event**: PostToolUse
**Monitored Tools**: Write, Edit, NotebookEdit
**Version**: 1.0.0

#### Why Use This Hook?

Dead code accumulates in codebases over time and causes problems:

- **Code Bloat**: Unused code makes files unnecessarily large
- **Maintenance Burden**: Dead code must still be maintained and understood
- **Confusion**: Developers waste time reading unused functions
- **Security Risk**: Unused code may contain vulnerabilities
- **Performance**: Import overhead for unused modules
- **Refactoring Safety**: Dead code detection helps identify breaking changes
- **Clean Codebase**: Easier to navigate and understand

This hook identifies dead code immediately after Claude writes it, allowing for quick cleanup before it becomes technical debt.

#### How It Works

The hook executes after file modifications:

1. **Validate Target**: Checks if file is Python (.py, .pyi) and within project
2. **Skip Test Files**: Automatically skips test_*.py, *_test.py, conftest.py
3. **Run Vulture**: Executes `vulture --min-confidence 80 <file>`
4. **Parse Output**: Extracts unused items with their locations
5. **Provide Feedback**: Non-blocking warning about dead code
6. **Suppress Noise**: Only reports high-confidence findings (80%+)

#### Detected Dead Code

**Types of Dead Code Detected**:
- **Unused Functions**: Functions never called
- **Unused Classes**: Classes never instantiated
- **Unused Methods**: Methods never called
- **Unused Variables**: Variables assigned but never read
- **Unused Imports**: Imported modules never used
- **Unused Attributes**: Class attributes never accessed
- **Unused Properties**: Property methods never called
- **Unused Arguments**: Function parameters never used

**Confidence Levels**:
- 100%: Definitely unused (imports, obvious cases)
- 80-99%: Very likely unused (high confidence)
- 60-79%: Possibly unused (not reported by default)
- < 60%: Uncertain (noise)

#### Examples

**Dead Code Detected**:
```python
import os  # ❌ Unused import
import json

def process_data(data):  # ❌ Unused function
    return json.loads(data)

def main():
    unused_var = 42  # ❌ Unused variable
    result = json.loads('{"key": "value"}')
    print(result)

if __name__ == "__main__":
    main()
```

**Feedback Output**:
```
⚠️ Vulture: Found 3 unused items in example.py (import 'os' at line 1, function 'process_data' at line 4, variable 'unused_var' at line 9)
```

**Clean Code** (no warnings):
```python
import json

def process_data(data):
    return json.loads(data)

def main():
    result = process_data('{"key": "value"}')
    print(result)

if __name__ == "__main__":
    main()
```

#### Configuration

Hook registration in `.claude/settings.json`:

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

**Environment Variables**:
- `VULTURE_MIN_CONFIDENCE`: Minimum confidence threshold (default: "80")
- `VULTURE_SKIP_TESTS`: Skip test files (default: "true")

**Example Configuration**:
```bash
# Lower threshold for more findings (may include false positives)
export VULTURE_MIN_CONFIDENCE="60"

# Check test files too
export VULTURE_SKIP_TESTS="false"
```

**Vulture Whitelist** (`.vulture_whitelist.py`):
Create a whitelist file to mark intentionally unused code:
```python
# .vulture_whitelist.py
# Mark these as used even if they appear unused

# Fixture used by pytest
def test_fixture():
    pass

# Public API that external code uses
def public_api_function():
    pass

# Django model fields (appear unused but accessed dynamically)
class Model:
    field_name = None
```

#### Behavior Details

**When Hook Triggers**:
- Write tool creates new Python file → Scans for dead code
- Edit tool modifies existing Python file → Scans for dead code
- NotebookEdit tool modifies notebook cell → Scans Python code

**What Gets Skipped**:
- Test files: `test_*.py`, `*_test.py`, `tests.py`, `conftest.py`
- Non-Python files
- Files outside project directory
- Files with syntax errors
- Failed tool operations

**Feedback Behavior**:
- **Findings**: Non-blocking warning with summary
- **No findings**: Silent exit (no output)
- **Errors**: Non-blocking, logged to stderr

#### Testing

Run tests:
```bash
uv run pytest tests/claude_hook/post_tools/test_vulture_checking.py -v
```

Manual test:
```bash
# Create test file with dead code
cat > test_dead_code.py << 'EOF'
import os
import json

def unused_function():
    pass

def main():
    unused_var = 42
    print(json.dumps({"test": "value"}))

if __name__ == "__main__":
    main()
EOF

# Test the hook
echo '{
  "session_id": "test",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {"file_path": "'$(pwd)'/test_dead_code.py"},
  "tool_response": {"success": true},
  "cwd": "'$(pwd)'"
}' | uv run .claude/hooks/post_tools/vulture_checking.py
```

#### Performance

- **Execution Time**: < 2 seconds for typical files
- **Memory Usage**: < 50 MB for typical files
- **Scalability**: Handles files up to several thousand lines
- **Timeout**: 15 seconds (configurable)
- **Dependencies**: Vulture (installed via UV)

#### Security

- **Path Validation**: Prevents path traversal
- **Project Boundary**: Only scans files within project
- **Safe Subprocess**: No shell execution
- **Timeout Protection**: 15-second timeout
- **Error Isolation**: Never crashes Claude
- **No Code Execution**: Only analyzes, never runs code

#### Integration with Other Tools

**Complementary Tools**:
- **basedpyright**: Type checking (detects type errors)
- **ruff**: Formatting and linting (detects style issues)
- **antipattern hook**: Detects code antipatterns
- **error handling reminder**: Educational feedback

**Execution Order**:
All PostToolUse hooks run in parallel, so order doesn't matter.

#### Known Limitations

**False Positives**:
- Public API functions (used by external code)
- Test fixtures (used by pytest dynamically)
- Django model fields (accessed via ORM)
- Dynamic attribute access (getattr/setattr)
- Abstract base class methods (overridden in subclasses)
- `__init__.py` exports (imported elsewhere)

**Mitigation**:
- Use `.vulture_whitelist.py` to mark intentionally unused code
- Skip test files (default behavior)
- Increase confidence threshold
- Use `# type: ignore[unused-ignore]` comments

**Cannot Detect**:
- Cross-file dependencies without full project scan
- Code used via dynamic imports
- Code used in other modules
- Code accessed via reflection

#### Troubleshooting

**Too many false positives**:
- Increase confidence: `export VULTURE_MIN_CONFIDENCE="90"`
- Create `.vulture_whitelist.py` for known false positives
- Skip specific patterns in whitelist

**Legitimate code flagged as unused**:
- Public APIs: Add to whitelist
- Test fixtures: Ensure test files are skipped
- Django models: Use whitelist for dynamically accessed fields
- Dynamic code: Use whitelist or lower confidence

**Hook not detecting obvious dead code**:
- Check confidence level: `echo $VULTURE_MIN_CONFIDENCE`
- Verify vulture version: `uv run vulture --version`
- Test manually: `uv run vulture --min-confidence 80 file.py`

**vulture not found**:
- Hook uses UV to install automatically
- Ensure UV is available: `uv --version`
- Manually test: `uv run --with vulture vulture --version`

#### Related Documentation

- [Vulture Documentation](https://github.com/jendrikseipp/vulture)
- [Dead Code Wikipedia](https://en.wikipedia.org/wiki/Dead_code)

---

### error_handling_reminder.py

**Purpose**: Educational awareness hook that gently reminds Claude to consider error handling and logging when risky code patterns are detected, without blocking workflow.

**Hook Event**: PostToolUse
**Monitored Tools**: Write, Edit, NotebookEdit
**Version**: 1.0.0

#### Why Use This Hook?

Claude Code often writes Python code involving exception handling, async operations, database calls, and API endpoints. While Claude understands error handling conceptually, it may not always include sufficient logging or error handling in every scenario:

- **Educational**: Provides gentle reminders about error handling best practices
- **Non-Intrusive**: Never blocks Claude's workflow
- **Context-Aware**: Detects risky patterns that commonly need error handling
- **Actionable**: Provides specific recommendations based on detected patterns
- **Best Practices**: Includes tips for proper error handling and logging
- **Self-Assessment**: Helps Claude improve error handling practices over time

This hook acts as a code review assistant, reminding Claude to add proper error handling and logging where needed.

#### How It Works

The hook uses AST-based pattern detection:

1. **Validate Target**: Checks if file is Python and within project
2. **Parse to AST**: Analyzes code structure (no execution)
3. **Detect Patterns**: Identifies four types of risky patterns
4. **Calculate Risk Score**: Sums up all detected issues
5. **Check Threshold**: Only triggers if score >= threshold (default: 2)
6. **Generate Message**: Creates educational feedback with recommendations
7. **Non-Blocking**: Always exits successfully (exit code 0)

#### Detected Patterns

**1. Try/Except Without Logging** (Score: +1 per block):
```python
# ❌ Risky: No logging in except block
try:
    data = fetch_from_database(user_id)
    return process(data)
except Exception:
    return None  # Error silently swallowed
```

**Recommendation**: Add logging statements in exception handlers for debugging.

**2. Async Functions Without Error Handling** (Score: +1 per function):
```python
# ❌ Risky: No error handling
async def fetch_user_profile(user_id):
    response = await http_client.get(f"/users/{user_id}")
    return response.json()  # What if request fails?
```

**Recommendation**: Add try/except to handle async errors and network failures.

**3. Database Operations Without Error Handling** (Score: +1 per operation):
```python
# ❌ Risky: No transaction handling
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()  # What if query fails?
```

**Recommendation**: Ensure transactions have proper error handling and logging.

**4. API Endpoints Without Error Handling** (Score: +1 per endpoint):
```python
# ❌ Risky: No error handling
from flask import Flask, jsonify

@app.route("/users/<user_id>")
def get_user(user_id):
    user = database.query(User).filter_by(id=user_id).first()
    return jsonify(user.to_dict())  # What if user not found?
```

**Recommendation**: Consider adding error handling to return appropriate HTTP status codes.

#### Example Output

**Multiple Risky Patterns Detected**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ERROR HANDLING SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Risky Patterns Detected in api.py

   ❓ Found 1 try-except block - Consider adding logging in except blocks for debugging
   ❓ Found 1 async function without error handling - Add try/except to handle async errors
   ❓ Found 1 database operation - Ensure transactions have proper error handling and logging
   ❓ Found 1 API endpoint - Consider adding error handling to return appropriate HTTP status codes

   💡 Error Handling Best Practices:
      - Add logging statements in exception handlers for debugging
      - Use structured logging with context (e.g., user_id, request_id)
      - Wrap await calls in try/except when dealing with external services
      - Use transactions with proper commit/rollback
      - Return appropriate HTTP status codes (400, 404, 500, etc.)
      - Log errors with request context (endpoint, method, params)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Safe Code** (no output - silent exit):
```python
import logging

logger = logging.getLogger(__name__)

async def fetch_user_profile(user_id):
    try:
        response = await http_client.get(f"/users/{user_id}")
        logger.info(f"Fetched profile for user {user_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        raise
```

#### Configuration

Hook registration in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/error_handling_reminder.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Environment Variables**:
```bash
# Enable/disable the hook
ERROR_HANDLING_REMINDER_ENABLED=true  # default: true

# Minimum risk score to trigger reminder (1-10)
ERROR_HANDLING_REMINDER_MIN_SCORE=2  # default: 2

# Include best practice tips in output
ERROR_HANDLING_REMINDER_INCLUDE_TIPS=true  # default: true

# Enable debug logging to stderr
ERROR_HANDLING_REMINDER_DEBUG=false  # default: false
```

**Example Configuration**:
```bash
# Strict mode: Warn on any single issue
export ERROR_HANDLING_REMINDER_MIN_SCORE=1

# Brief mode: Only show issues, no tips
export ERROR_HANDLING_REMINDER_INCLUDE_TIPS=false

# Disabled for rapid prototyping
export ERROR_HANDLING_REMINDER_ENABLED=false
```

#### Behavior Details

**Risk Score Calculation**:
```
total_risk_score =
    except_blocks_without_logging +
    async_functions_without_error_handling +
    db_operations_without_error_handling +
    endpoints_without_error_handling
```

**Threshold Logic**:
- Score < threshold: Silent exit (no feedback)
- Score >= threshold: Show educational reminder
- Default threshold: 2 (requires at least 2 issues)

**What Gets Analyzed**:
- File extension: `.py`, `.pyi` only
- File location: Must be within project directory
- File size: Up to 10,000 lines (larger files skipped)
- Valid Python: Syntax errors silently skipped

**What Gets Skipped**:
- Non-Python files
- Files outside project directory
- Files with syntax errors (other tools handle)
- Very large files (> 10,000 lines)
- Failed tool operations

#### Testing

Run comprehensive test suite:
```bash
# Run all tests
uv run pytest tests/claude_hook/post_tools/test_error_handling_reminder.py -v

# Run with coverage
uv run pytest --cov=.claude/hooks/post_tools/error_handling_reminder \
  tests/claude_hook/post_tools/test_error_handling_reminder.py

# Run specific test
uv run pytest tests/claude_hook/post_tools/test_error_handling_reminder.py::test_detect_try_except_without_logging -v
```

Test coverage includes:
- Configuration loading (environment variables)
- File validation (paths, extensions, project boundary)
- Pattern detection for all four pattern types
- Risk scoring and threshold comparison
- Message generation and formatting
- Error handling and graceful degradation
- Full integration workflow

#### Performance

- **Execution Time**: < 1 second for typical files (< 1000 lines)
- **Memory Usage**: < 50 MB for typical files
- **Analysis Method**: AST traversal (no code execution)
- **Timeout**: 15 seconds (configurable)
- **Dependencies**: None (uses only Python standard library)

#### Security

- **No Code Execution**: Only parses AST, never executes code
- **Path Validation**: Prevents path traversal attacks
- **Project Boundary**: Only analyzes files within project
- **Safe Processing**: No subprocess calls, pure Python
- **Error Isolation**: Exceptions never crash Claude
- **Read-Only**: Analyzes but never modifies files

#### Integration with Other Hooks

**Complementary Hooks**:
- **antipattern hook**: Detects structural antipatterns (different focus)
- **basedpyright**: Type checking (different concern)
- **ruff**: Style and linting (different scope)
- **vulture**: Dead code detection (orthogonal)

**Execution**: All PostToolUse hooks run in parallel (order doesn't matter).

#### Known Limitations

**AST-Based Detection**:
- Cannot track variable values across scopes
- No dataflow analysis
- May miss context-specific patterns
- False positives possible (intentional patterns)

**Patterns Not Detected**:
- Error handling in parent functions
- Centralized exception handlers (middleware)
- Context managers that handle errors
- Logging in finally blocks (vs except blocks)

**False Positives**:
- Test code (expected to test error conditions)
- Example/demo code (simplified intentionally)
- Code with external error handling (middleware, decorators)

#### Troubleshooting

**Too many reminders**:
- Increase threshold: `export ERROR_HANDLING_REMINDER_MIN_SCORE=3`
- Disable tips: `export ERROR_HANDLING_REMINDER_INCLUDE_TIPS=false`
- Disable hook: `export ERROR_HANDLING_REMINDER_ENABLED=false`

**Missing obvious issues**:
- Lower threshold: `export ERROR_HANDLING_REMINDER_MIN_SCORE=1`
- Enable debug mode: `export ERROR_HANDLING_REMINDER_DEBUG=true`
- Check file isn't skipped (syntax errors, size, location)

**Hook not triggering**:
- Verify hook is registered: `/hooks` command in Claude Code
- Check environment variables: `env | grep ERROR_HANDLING`
- Test manually with sample input
- Enable Claude Code debug mode: `claude --debug`

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/post_tools/error_handling_reminder-spec.md)
- [Test Suite](../../../tests/claude_hook/post_tools/test_error_handling_reminder.py)
- [Python Logging Guide](https://docs.python.org/3/howto/logging.html)
- [Error Handling Best Practices](https://docs.python.org/3/tutorial/errors.html)

---

## Shared Utilities

All PostToolUse hooks share common utilities from the `utils/` directory:

### data_types.py
- TypedDict definitions for type safety
- `ToolInput`, `HookOutput`, `HookSpecificOutput`
- `ToolResponse` for tool execution results

**Supported Tool Parameters**:
- `file_path`: File path (Read, Write, Edit, NotebookEdit tools)
- `content`: File content (Write tool)
- `old_string`: String to replace (Edit tool)
- `new_string`: Replacement string (Edit tool)
- `replace_all`: Replace all occurrences flag (Edit tool)
- `notebook_path`: Notebook file path (NotebookEdit tool)
- `cell_id`: Cell identifier (NotebookEdit tool)

### utils.py
- `parse_hook_input()`: Parse JSON from stdin with full tool support
- `output_feedback()`: Format and output JSON feedback for Claude
- `get_file_path()`: Extract file path from tool input
- `is_python_file()`: Check if file is Python (.py, .pyi)
- `is_within_project()`: Validate file is within project directory
- `was_tool_successful()`: Check if tool execution succeeded

### Usage Example

```python
from utils import (
    get_file_path,
    is_python_file,
    is_within_project,
    output_feedback,
    parse_hook_input,
    was_tool_successful,
)


def main():
    # Parse input from Claude
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # Validate tool execution succeeded
    if not was_tool_successful(tool_response):
        output_feedback("", suppress_output=True)
        return

    # Extract and validate file path
    file_path = get_file_path(tool_input)
    if not file_path or not is_python_file(file_path):
        output_feedback("", suppress_output=True)
        return

    # Validate within project
    if not is_within_project(file_path):
        output_feedback("", suppress_output=True)
        return

    # Process the file
    result_message = process_file(file_path)

    # Send feedback to Claude
    output_feedback(result_message, suppress_output=True)


if __name__ == "__main__":
    main()
```

---

## Hook Development Guidelines

When creating new PostToolUse hooks:

1. **Follow Shared Utilities**: Use functions from `utils/` for consistency
2. **Non-Blocking**: PostToolUse hooks should never block (exit with code 0)
3. **Feedback Pattern**: Use JSON output with `hookSpecificOutput` field
4. **Suppress Output**: Set `suppressOutput: true` for background processing
5. **File Validation**: Always check file type, location, and existence
6. **Error Handling**: Catch all exceptions, fail gracefully
7. **Timeout Protection**: Set reasonable timeouts (30-60 seconds)
8. **Testing**: Write comprehensive unit tests
9. **Documentation**: Update this README with your hook details
10. **Security**: Validate all inputs, never execute untrusted code

**Template Structure**:
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["package==version"]
# ///
"""Hook description."""

from utils import parse_hook_input, output_feedback


def main() -> None:
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # Your hook logic here
    feedback = process_tool_output(tool_name, tool_input, tool_response)

    output_feedback(feedback, suppress_output=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log error but don't block
        print(f"Hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
```
