# Hook Code Quality Refactoring Specification

## Purpose and Objectives

Refactor the `sensitive_file_access_validator.py` PreToolUse hook (and related pre_tools hooks) to improve code quality, maintainability, and developer experience through:

1. **Structured Logging**: Replace `print()` statements with Python's standard `logging` module
2. **Type Safety**: Add comprehensive type annotations for `basedpyright` compliance
3. **Code Quality**: Ensure compliance with `ruff` linting standards
4. **Dead Code Elimination**: Pass `vulture` checks for unused code detection
5. **Preserve Functionality**: Maintain all existing security validation behavior

## Context and Background

### Current State

The pre_tools hooks currently have several code quality issues:

- **46 print() statements** across 10 files in `.claude/hooks/pre_tools/`
- Type annotations are incomplete or inconsistent
- No centralized logging infrastructure
- Output is primarily for debugging, not production monitoring

### Hook Execution Environment

- Hooks run via: `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/<hook-name>.py`
- UV script metadata defines inline dependencies
- JSON input via stdin, output via stdout/stderr
- 60-second default timeout
- Exit codes: 0 (success), 2 (blocking error), other (non-blocking error)

### Files in Scope

**Primary Target:**
- `.claude/hooks/pre_tools/sensitive_file_access_validator.py` - Main security validation hook

**Supporting Infrastructure:**
- `.claude/hooks/pre_tools/utils.py` - Shared utilities
- `.claude/hooks/pre_tools/data_types.py` - Type definitions
- `.claude/hooks/pre_tools/__init__.py` - Package initialization

**Test Infrastructure:**
- `.claude/hooks/pre_tools/tests/test_utils.py` - Utility tests
- `.claude/hooks/pre_tools/tests/test_data_types.py` - Type tests
- **New:** `.claude/hooks/pre_tools/tests/test_sensitive_file_access_validator.py` - Hook tests

## Technical Design

### 1. Logging Architecture

#### Log Levels Strategy

```python
# DEBUG: Detailed diagnostic information
logger.debug("Parsing tool input: %s", tool_name)

# INFO: Confirmation of expected behavior
logger.info("File operation validated: %s - %s", operation, file_path)

# WARNING: Potential issues that don't block execution
logger.warning("Template file access detected: %s", file_path)

# ERROR: Blocking security violations
logger.error("Blocked sensitive file access: %s - %s", operation, file_path)
```

#### Log Output Strategy

**For Hooks (stdout consumed by Claude Code):**
- Logs should go to **stderr** to avoid interfering with JSON output on stdout
- Use structured logging format for parsing
- Include session context when available

**Configuration:**
```python
import logging
import sys
import os

def setup_logging() -> logging.Logger:
    """
    Configure logging for PreToolUse hooks.

    Logs to stderr to avoid interfering with JSON output on stdout.
    Log level controlled by HOOK_LOG_LEVEL environment variable.
    """
    log_level = os.environ.get("HOOK_LOG_LEVEL", "INFO")

    logger = logging.getLogger("pre_tools")
    logger.setLevel(getattr(logging, log_level))

    # Stream handler for stderr
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(getattr(logging, log_level))

    # Structured format with context
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(name)s.%(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
```

#### Migration from Print Statements

**Before:**
```python
print(f"Validation successful: {file_path}")
```

**After:**
```python
logger.info("Validation successful: %s", file_path)
```

**Mapping Print to Log Levels:**
- Diagnostic prints → `logger.debug()`
- Status updates → `logger.info()`
- Security warnings → `logger.warning()` or `logger.error()`
- Errors/violations → `logger.error()`

### 2. Type Safety Improvements

#### Current Type Issues

From code analysis:
1. Missing return type annotations in several functions
2. Inconsistent use of `str | None` vs `Optional[str]`
3. `Any` types in utils.py that should be more specific
4. Missing type annotations in test files

#### Required Changes

**utils.py - parse_hook_input():**
```python
from typing import Optional, Tuple
from data_types import ToolInput

def parse_hook_input() -> Optional[Tuple[str, ToolInput]]:
    """Parse and validate hook input from stdin."""
    try:
        input_text = sys.stdin.read()
        parsed_json: dict[str, Any] = json.loads(input_text)

        tool_name: str = parsed_json.get("tool_name", "")
        tool_input_raw: dict[str, str] = parsed_json.get("tool_input", {})

        # Build typed tool input
        tool_input = ToolInput()
        if "file_path" in tool_input_raw:
            tool_input["file_path"] = tool_input_raw["file_path"]
        if "command" in tool_input_raw:
            tool_input["command"] = tool_input_raw["command"]
        if "content" in tool_input_raw:
            tool_input["content"] = tool_input_raw["content"]

        return (tool_name, tool_input)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse hook input: %s", e)
        return None
```

**sensitive_file_access_validator.py:**
```python
def validate_file_operation(
    tool_name: str,
    tool_input: ToolInput
) -> str | None:
    """
    Validate file operations for security concerns.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        Violation message if found, None otherwise
    """
    # Implementation...
```

#### basedpyright Configuration

Add to `pyproject.toml`:
```toml
[tool.basedpyright]
include = ["src", ".claude/hooks/pre_tools"]
pythonVersion = "3.12"
typeCheckingMode = "recommended"
reportMissingTypeStubs = false
reportUnknownMemberType = false
reportUnknownVariableType = false
reportUnknownArgumentType = false
```

### 3. Ruff Compliance

#### Current Configuration

From `pyproject.toml`:
- Line length: 88 (Black-compatible)
- Target: Python 3.12
- Enabled rules: E4, E7, E9, F (Pyflakes + subset of pycodestyle)

#### Required Changes

1. **Import sorting**: Ensure standard library, third-party, and local imports are properly separated
2. **Line length**: Keep all lines ≤ 88 characters
3. **Unused imports**: Remove any unused imports
4. **Quote consistency**: Use double quotes for strings

**Example Fix:**
```python
# Before (mixed imports)
import re
from pathlib import Path
import sys
from utils import parse_hook_input
import json

# After (sorted imports)
import json
import re
import sys
from pathlib import Path

from data_types import ToolInput
from utils import parse_hook_input, output_decision, get_file_path
```

#### Ruff Check Command

```bash
ruff check .claude/hooks/pre_tools/sensitive_file_access_validator.py
ruff format .claude/hooks/pre_tools/sensitive_file_access_validator.py
```

### 4. Vulture Dead Code Detection

#### Configuration

From `pyproject.toml`:
- Min confidence: 80%
- Ignore decorators: @app.route, @pytest.fixture, @click.command
- Ignore names: test_*, Test*, setUp, tearDown
- Exclude: */migrations/*, */tests/*

#### Expected Issues

Vulture may flag:
1. Unused imports after cleanup
2. Unused variables in validation functions
3. Unused parameters in hook functions

#### Resolution Strategy

1. **Remove truly unused code**: Delete imports, functions, variables not referenced
2. **Mark intentional unused**: Use `# noqa: vulture` for required but seemingly unused code
3. **Refactor to use**: If code should be used but isn't, integrate it properly

**Example:**
```python
# Intentionally unused parameter (required by interface)
def validate_file_operation(
    tool_name: str,
    tool_input: ToolInput  # noqa: vulture - required by hook interface
) -> str | None:
    """Validate file operations."""
    pass
```

### 5. UV Script Metadata

All hook scripts must include UV metadata for logging dependency:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**Note:** Standard library `logging` module requires no external dependencies.

## Implementation Plan

### Phase 1: Infrastructure Setup (TDD Green)

**Objective:** Establish logging infrastructure without changing existing behavior

1. **Add logging setup function to utils.py**
   - Write test: `test_setup_logging_returns_logger()`
   - Implement: `setup_logging() -> logging.Logger`
   - Verify: Logger configured correctly, outputs to stderr

2. **Update data_types.py for stricter typing**
   - No new tests needed (structural change)
   - Add missing type annotations
   - Run basedpyright to verify

3. **Update __init__.py to expose logging**
   - Export `setup_logging` function
   - No behavioral change

### Phase 2: Refactor sensitive_file_access_validator.py (TDD Refactor)

**Objective:** Replace print statements with logging while preserving behavior

#### Step 1: Add Tests (TDD Red → Green)

Create `tests/test_sensitive_file_access_validator.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from sensitive_file_access_validator import (
    validate_file_operation,
    check_file_path_violations,
    check_bash_file_operations
)
from data_types import ToolInput


class TestValidateFileOperation:
    """Test file operation validation."""

    def test_blocks_env_file_read(self):
        """Should block reading .env files."""
        tool_input: ToolInput = {"file_path": "/project/.env"}
        violation = validate_file_operation("Read", tool_input)
        assert violation is not None
        assert "environment variables" in violation

    def test_allows_env_sample_file_read(self):
        """Should allow reading .env.sample files."""
        tool_input: ToolInput = {"file_path": "/project/.env.sample"}
        violation = validate_file_operation("Read", tool_input)
        assert violation is None

    def test_blocks_ssh_key_write(self):
        """Should block writing SSH private keys."""
        tool_input: ToolInput = {"file_path": "/home/user/.ssh/id_rsa"}
        violation = validate_file_operation("Write", tool_input)
        assert violation is not None
        assert "SSH private key" in violation

    def test_blocks_system_directory_write(self):
        """Should block writing to /etc."""
        tool_input: ToolInput = {"file_path": "/etc/hosts"}
        violation = validate_file_operation("Write", tool_input)
        assert violation is not None
        assert "system directory" in violation

    def test_allows_normal_file_operations(self):
        """Should allow normal project file operations."""
        tool_input: ToolInput = {"file_path": "/project/src/main.py"}
        violation = validate_file_operation("Write", tool_input)
        assert violation is None


class TestCheckBashFileOperations:
    """Test bash command validation."""

    def test_blocks_cat_env_file(self):
        """Should block 'cat .env' command."""
        violations = check_bash_file_operations("cat /project/.env")
        assert len(violations) > 0
        assert any(".env" in v for v in violations)

    def test_allows_cat_env_sample(self):
        """Should allow 'cat .env.sample' command."""
        violations = check_bash_file_operations("cat /project/.env.sample")
        assert len(violations) == 0

    def test_blocks_redirect_to_etc(self):
        """Should block redirects to /etc."""
        violations = check_bash_file_operations("echo 'test' > /etc/config")
        assert len(violations) > 0
        assert any("system directory" in v for v in violations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 2: Type Annotation Pass

1. Run basedpyright before changes
2. Add missing type annotations
3. Fix type errors
4. Run basedpyright again to verify

**Files to update:**
- `sensitive_file_access_validator.py`
- `utils.py`
- `data_types.py`

#### Step 3: Logging Migration (Refactor Phase)

**Prerequisites:**
- All tests must be passing
- Basedpyright checks passing
- Ruff checks passing

**Changes:**
1. Import logging at top of file
2. Initialize logger: `logger = setup_logging()`
3. Replace each print() with appropriate log level
4. Preserve all output messages (meaningful logs)

**Example transformations:**

```python
# Before
def validate_file_operation(tool_name: str, tool_input: ToolInput) -> str | None:
    print(f"Validating {tool_name} operation")
    # validation logic

# After
def validate_file_operation(tool_name: str, tool_input: ToolInput) -> str | None:
    logger.debug("Validating %s operation on %s", tool_name, tool_input.get("file_path", "N/A"))
    # validation logic
```

#### Step 4: Code Quality Pass

1. **Run ruff check:** `ruff check .claude/hooks/pre_tools/sensitive_file_access_validator.py`
2. **Fix issues:** Apply ruff suggestions
3. **Run ruff format:** `ruff format .claude/hooks/pre_tools/sensitive_file_access_validator.py`
4. **Run vulture:** `vulture .claude/hooks/pre_tools/sensitive_file_access_validator.py`
5. **Remove dead code:** Delete or mark unused code
6. **Verify tests still pass**

### Phase 3: Update Supporting Files

Apply same process to:
- `utils.py` - Add logging, fix types
- `data_types.py` - Complete type annotations
- `__init__.py` - Export logging utilities

### Phase 4: Validation

**Final Checklist:**
- [ ] All print() statements replaced with logging
- [ ] basedpyright passes: `basedpyright .claude/hooks/pre_tools/`
- [ ] ruff passes: `ruff check .claude/hooks/pre_tools/`
- [ ] vulture passes: `vulture .claude/hooks/pre_tools/ --min-confidence 80`
- [ ] All tests pass: `pytest .claude/hooks/pre_tools/tests/ -v`
- [ ] Hook functionality preserved (manual test with Claude Code)
- [ ] Log output meaningful and at appropriate levels

## Testing Strategy

### Test Categories

1. **Unit Tests** - Individual function behavior
   - `test_validate_file_operation()`
   - `test_check_file_path_violations()`
   - `test_check_bash_file_operations()`

2. **Integration Tests** - Hook end-to-end behavior
   - Test with JSON input via stdin
   - Verify JSON output format
   - Test exit codes

3. **Type Tests** - basedpyright compliance
   - Run basedpyright on all files
   - No type errors allowed

4. **Linting Tests** - Code quality
   - Run ruff check
   - Run vulture
   - No violations allowed

### Test Execution Commands

```bash
# Run all tests
pytest .claude/hooks/pre_tools/tests/ -v

# Type checking
basedpyright .claude/hooks/pre_tools/

# Linting
ruff check .claude/hooks/pre_tools/
ruff format --check .claude/hooks/pre_tools/

# Dead code detection
vulture .claude/hooks/pre_tools/ --min-confidence 80
```

### TDD Principles to Follow

From `ai_docs/tdd.md`:

1. **Red-Green-Refactor Cycle**
   - Write ONE failing test at a time
   - Implement minimal code to pass
   - Refactor only when tests are green

2. **Incremental Development**
   - Each step addresses ONE specific issue
   - No anticipatory coding

3. **Tidy First Approach**
   - Separate structural changes (logging migration) from behavioral changes
   - Never mix structural and behavioral changes
   - Validate with tests before and after each change

4. **Code Quality Standards**
   - Eliminate duplication
   - Express intent clearly through naming
   - Keep methods small and focused

## Expected Outcomes

### Before Refactoring

**Issues:**
- 46 print statements across files
- Incomplete type coverage
- Potential basedpyright errors
- Unknown dead code

**Example Code:**
```python
def validate_file_operation(tool_name, tool_input):
    print(f"Validating {tool_name}")
    if file_path:
        print(f"Checking {file_path}")
    # ...
```

### After Refactoring

**Improvements:**
- Zero print statements (all logging)
- 100% type annotation coverage
- basedpyright clean
- ruff clean
- vulture clean
- Meaningful, structured logs

**Example Code:**
```python
import logging
from typing import Optional

logger = logging.getLogger("pre_tools.sensitive_file_access_validator")

def validate_file_operation(
    tool_name: str,
    tool_input: ToolInput
) -> Optional[str]:
    """
    Validate file operations for security concerns.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        Violation message if found, None otherwise
    """
    file_path = tool_input.get("file_path", "")
    logger.debug("Validating %s operation: %s", tool_name, file_path)

    violation = check_file_path_violations(file_path, "write")
    if violation:
        logger.error("Security violation detected: %s", violation)
        return violation

    logger.info("Validation passed for %s: %s", tool_name, file_path)
    return None
```

## Security Considerations

### Logging Safety

**Sensitive Data Handling:**
- Never log file contents
- Never log credentials or secrets
- Log file paths only (safe for security auditing)
- Use log levels to control verbosity

**Example - Safe Logging:**
```python
# SAFE: Log file path and decision
logger.error("Blocked access to sensitive file: %s", file_path)

# UNSAFE: Never log file contents
# logger.debug("File content: %s", content)  # DON'T DO THIS
```

### Hook Behavior Preservation

**Critical Requirements:**
1. All security validations must remain in place
2. Exit codes must remain unchanged
3. JSON output format must remain unchanged
4. No new blocking behaviors introduced

## Rollback Strategy

If issues arise during refactoring:

1. **Test Failures**: Revert last change, fix tests first
2. **Type Errors**: Add `type: ignore` comments temporarily, fix incrementally
3. **Hook Failures**: Revert to last working commit
4. **Performance Issues**: Review logging overhead, adjust log levels

## Dependencies

### Python Packages (via UV)

**Standard Library (no dependencies):**
- `logging` - Logging infrastructure
- `typing` - Type annotations
- `json` - JSON parsing
- `sys` - System interfaces
- `pathlib` - Path operations
- `re` - Regular expressions

**Development Tools (project-level):**
- `basedpyright>=1.31.5` - Type checking
- `ruff>=0.13.2` - Linting and formatting
- `vulture>=2.14` - Dead code detection
- `pytest>=7.0.0` - Testing framework (via UV script metadata)

### UV Script Metadata

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

## Success Criteria

### Code Quality Metrics

- [ ] **Zero print statements** in production hooks
- [ ] **100% basedpyright pass rate** (no type errors)
- [ ] **100% ruff pass rate** (no linting violations)
- [ ] **Zero vulture warnings** at 80% confidence
- [ ] **100% test pass rate** (all tests green)

### Functional Requirements

- [ ] All existing security validations preserved
- [ ] Hook exit codes unchanged
- [ ] JSON output format unchanged
- [ ] Hook execution time ≤ 100ms (performance baseline)
- [ ] Logs provide meaningful debugging information

### Documentation

- [ ] All functions have docstrings with type information
- [ ] README updated with logging configuration instructions
- [ ] Examples of log output provided
- [ ] Migration notes for other hooks

## Future Extensions

After successful refactoring of `sensitive_file_access_validator.py`:

1. **Apply to all pre_tools hooks** - Migrate remaining 10 files
2. **Centralized logging config** - Shared configuration module
3. **Structured logging** - JSON-formatted logs for parsing
4. **Log aggregation** - Integration with logging services
5. **Performance monitoring** - Log execution times
6. **Security audit logging** - Dedicated security log channel

## References

### Documentation

- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Claude Code Hooks](../../../ai_docs/claude-code-hooks.md)
- [TDD Fundamentals](../../../ai_docs/tdd.md)

### Python Resources

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [PEP 723 - Inline Script Metadata](https://peps.python.org/pep-0723/)

### Tools

- [basedpyright](https://github.com/DetachHead/basedpyright)
- [ruff](https://github.com/astral-sh/ruff)
- [vulture](https://github.com/jendrikseipp/vulture)
- [pytest](https://docs.pytest.org/)

---

**Document Version:** 1.0
**Created:** 2025-10-25
**Author:** Claude Code Hook Expert
**Status:** Ready for Implementation
