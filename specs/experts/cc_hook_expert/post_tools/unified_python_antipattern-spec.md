# Unified Python Antipattern Hook - Specification

## 1. Overview

### Purpose
Detect Python-specific antipatterns not covered by type checkers (basedpyright) or dead code detectors (vulture) after Write, Edit, or NotebookEdit operations. This hook focuses on runtime issues, security vulnerabilities, performance problems, and code quality concerns that are legal Python code but represent poor practices.

### Problem Statement
Type checkers and linters catch syntax and type errors, but many Python antipatterns go undetected:
- **Runtime issues**: Mutable defaults, late binding closures, global misuse
- **Security vulnerabilities**: Weak cryptography, SQL injection, hardcoded secrets
- **Performance problems**: String concatenation in loops, inefficient operations
- **Complexity issues**: Too many parameters, deeply nested code
- **Python gotchas**: Using `is` for equality, modifying lists while iterating

These issues can lead to bugs, security breaches, poor performance, and maintenance nightmares.

### Objectives
1. **Comprehensive Detection**: Cover 40+ Python antipatterns across 7 categories
2. **AST-based Analysis**: Use Python's `ast` module for accurate pattern detection
3. **Contextual Feedback**: Provide clear explanations and fix suggestions
4. **Configurable Severity**: Allow per-pattern severity configuration
5. **Non-blocking by Default**: Warning mode for most patterns, blocking only for critical security issues
6. **Performance Optimized**: Complete analysis within 15-second timeout

## 2. Hook Configuration

### Event Type
**PostToolUse** - Analyzes Python files after they are written or edited

### Matcher Pattern
```json
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
```

### Why PostToolUse?
- Analyzes actual file content after modification
- Provides feedback for Claude to fix in next iteration
- Non-blocking design allows iteration
- Complements basedpyright (types) and vulture (dead code)

## 3. Antipattern Categories

### 3.1 Runtime Antipatterns
Issues that cause runtime errors or unexpected behavior:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| R001 | Mutable default arguments | HIGH | `def foo(x=[])` - defaults shared across calls |
| R002 | Dangerous functions | HIGH | Using `eval()`, `exec()`, `compile()` unsafely |
| R003 | Bare except | MEDIUM | `except:` without exception type |
| R004 | Assert in production | HIGH | Using `assert` for validation (disabled with -O) |
| R005 | Global misuse | MEDIUM | Overusing `global` keyword |
| R006 | Mutable class variables | HIGH | Class attributes that are mutable (lists, dicts) |
| R007 | Late binding closures | MEDIUM | Loop variables in lambdas/closures |
| R008 | Shadowing builtins | MEDIUM | Using `list`, `dict`, `id`, etc. as variable names |
| R009 | __eq__ without __hash__ | HIGH | Defining __eq__ makes objects unhashable by default |
| R010 | Missing super() call | MEDIUM | Not calling super().__init__() in inheritance |
| R011 | Modifying dict while iterating | HIGH | Dictionary changed size during iteration |

### 3.2 Performance Antipatterns
Code that works but performs poorly:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| P001 | String concatenation in loops | MEDIUM | Using `+` or `+=` for strings in loops |
| P002 | Repeated attribute access | LOW | Multiple `self.x.y.z` calls in method |
| P003 | Inefficient containment checks | MEDIUM | `x in list` in loops - should use set |
| P004 | Unnecessary lambda | LOW | `lambda x: func(x)` - just use `func` |
| P005 | List concatenation in loops | MEDIUM | Using `+` for lists in loops |
| P006 | Not using list comprehensions | LOW | Traditional loop when comprehension is clearer |
| P007 | Unnecessary list() conversions | LOW | Converting iterables unnecessarily |
| P008 | Using keys() unnecessarily | LOW | `for key in dict.keys()` - `.keys()` is implicit |
| P009 | range(len()) instead of enumerate | LOW | `range(len(items))` when enumerate() is better |
| P010 | Repeated list.append in loop | LOW | Should use list comprehension or extend |

### 3.3 Complexity Antipatterns
Code that is hard to understand or maintain:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| C001 | Complex list comprehension | MEDIUM | Nested comprehensions or complex logic |
| C002 | Nested function complexity | MEDIUM | Functions nested more than 2 levels |
| C003 | Cyclomatic complexity | HIGH | Function complexity > 15 |
| C004 | Too many arguments | MEDIUM | Function with > 7 parameters |
| C005 | Unnecessary else after return | LOW | `else` block after `return` statement |
| C006 | Deep nesting | HIGH | More than 4 levels of indentation |
| C007 | Complex boolean expressions | MEDIUM | Boolean expressions with > 3 operators |
| C008 | Too many return statements | MEDIUM | Function with > 5 return statements |
| C009 | Boolean trap | LOW | Function calls with unclear boolean args |
| C010 | Long function | HIGH | Function with > 50 lines of code |

### 3.4 Security Antipatterns
Potential security vulnerabilities:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| S001 | SQL injection | CRITICAL | String formatting in SQL queries |
| S002 | Command injection | CRITICAL | shell=True with user input |
| S003 | Hardcoded secrets | CRITICAL | API keys, passwords in source code |
| S004 | Weak cryptography | HIGH | Using MD5, SHA1 for security |
| S005 | Unsafe deserialization | HIGH | pickle.load, yaml.load without Loader |
| S006 | Insecure tempfile | HIGH | Using tempfile.mktemp() - race condition |
| S007 | Weak random for security | HIGH | Using random module for crypto |
| S008 | Path traversal | HIGH | User input in file paths without validation |
| S009 | Unsafe XML parsing | MEDIUM | XML parsing without defusedxml |
| S010 | Bind to 0.0.0.0 | MEDIUM | Listening on all interfaces |

### 3.5 Code Organization
Code structure and import issues:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| O001 | File too long | MEDIUM | File with > 500 lines |
| O002 | Poor import organization | LOW | Imports not grouped by stdlib/3rd-party/local |
| O003 | Wildcard imports | HIGH | `from module import *` |
| O004 | Circular imports | HIGH | Circular import dependencies |
| O005 | Import inside function | MEDIUM | Imports not at module level (without reason) |
| O006 | Multiple statements per line | LOW | `x = 1; y = 2` on same line |
| O007 | Inconsistent naming | LOW | Mixed snake_case and camelCase |

### 3.6 Resource Management
File handles, connections, and resource leaks:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| M001 | File not using context manager | HIGH | `f = open()` without `with` statement |
| M002 | Missing context manager | MEDIUM | Resources not using context managers |
| M003 | Not returning self in __enter__ | MEDIUM | Context manager protocol violation |
| M004 | Socket not closed | HIGH | Network sockets not properly closed |
| M005 | Database connection leak | HIGH | DB connections not closed |

### 3.7 Python Gotchas
Common Python mistakes and pitfalls:

| ID | Pattern | Severity | Description |
|----|---------|----------|-------------|
| G001 | Using is for equality | HIGH | `x is 5` instead of `x == 5` |
| G002 | Using == for identity | MEDIUM | `x == None` instead of `x is None` |
| G003 | Type checking with type() | MEDIUM | Using `type(x) == int` instead of `isinstance()` |
| G004 | Modifying list while iterating | HIGH | Changing list in for loop over same list |
| G005 | Silent exception swallowing | HIGH | Empty except block with pass |
| G006 | Comparing with True/False | LOW | `if x == True` instead of `if x` |
| G007 | Mutable as dict/set key | HIGH | Using list/dict as dictionary key |
| G008 | Not using enumerate | LOW | Using range(len()) pattern |
| G009 | Comparing types incorrectly | MEDIUM | Anti-pattern type comparisons |
| G010 | Using += with strings in loop | HIGH | Performance gotcha |

## 4. Input Schema

### Hook Input (via stdin)
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "..."
  },
  "tool_response": {
    "filePath": "/path/to/file.py",
    "success": true
  }
}
```

### Required Fields
- `tool_name`: Must be "Write", "Edit", or "NotebookEdit"
- `tool_input.file_path`: Path to Python file
- `tool_response.success`: Must be true (skip if tool failed)

## 5. Output Schema

### Success (No Issues)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ No antipatterns detected in file.py"
  },
  "suppressOutput": true
}
```

### Warnings (Issues Found - Non-blocking)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "⚠️ Python antipatterns found in file.py:\n\n[R001:HIGH] Mutable default argument on line 5\n  def process(items=[]):  # <- This list is shared across calls\n  \n  Fix: Use None and create inside function:\n  def process(items=None):\n      if items is None:\n          items = []\n\n[P001:MEDIUM] String concatenation in loop on line 12\n  result += item  # <- Creates new string each iteration\n  \n  Fix: Use list and join:\n  parts.append(item)\n  result = ''.join(parts)\n\n2 issues found (1 HIGH, 1 MEDIUM)"
  },
  "suppressOutput": false
}
```

### Blocked (Critical Security Issue)
```json
{
  "decision": "block",
  "reason": "❌ CRITICAL security issue detected in file.py",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "[S001:CRITICAL] SQL injection vulnerability on line 15\n  query = f\"SELECT * FROM users WHERE id = {user_id}\"\n  \n  This allows SQL injection attacks!\n  \n  Fix: Use parameterized queries:\n  query = \"SELECT * FROM users WHERE id = %s\"\n  cursor.execute(query, (user_id,))\n\nPlease fix this security vulnerability before continuing."
  },
  "suppressOutput": false
}
```

## 6. Detection Implementation

### AST-Based Analysis
Use Python's `ast` module for accurate pattern detection:

```python
import ast
from typing import List, Dict

class AntipatternDetector(ast.NodeVisitor):
    """AST visitor for detecting Python antipatterns."""

    def __init__(self):
        self.issues: List[Dict[str, object]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for antipatterns."""
        # Check for mutable default arguments
        self._check_mutable_defaults(node)
        # Check function complexity
        self._check_function_complexity(node)
        # Check parameter count
        self._check_parameter_count(node)
        # Continue traversal
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check comparison operations."""
        # Check for 'is' used with literals
        self._check_is_with_literals(node)
        # Check for == with None
        self._check_equality_with_none(node)
        self.generic_visit(node)
```

### Pattern Detection Methods

#### Mutable Default Arguments (R001)
```python
def _check_mutable_defaults(self, node: ast.FunctionDef) -> None:
    """Detect mutable default arguments."""
    for arg in node.args.defaults + node.args.kw_defaults:
        if arg is None:
            continue
        if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
            self.issues.append({
                'id': 'R001',
                'severity': 'HIGH',
                'line': arg.lineno,
                'message': 'Mutable default argument',
                'suggestion': 'Use None and create inside function'
            })
```

#### String Concatenation in Loops (P001)
```python
def _check_string_concatenation_in_loops(self, node: ast.For) -> None:
    """Detect string concatenation in loops."""
    for child in ast.walk(node):
        if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
            # Check if target is likely a string
            if self._is_string_concatenation(child):
                self.issues.append({
                    'id': 'P001',
                    'severity': 'MEDIUM',
                    'line': child.lineno,
                    'message': 'String concatenation in loop',
                    'suggestion': 'Use list.append() and str.join()'
                })
```

#### SQL Injection (S001)
```python
def _check_sql_injection(self, node: ast.Call) -> None:
    """Detect potential SQL injection."""
    # Check for execute() calls with f-strings or % formatting
    if self._is_sql_execute_call(node):
        if self._has_string_formatting(node.args[0]):
            self.issues.append({
                'id': 'S001',
                'severity': 'CRITICAL',
                'line': node.lineno,
                'message': 'Potential SQL injection vulnerability',
                'suggestion': 'Use parameterized queries'
            })
```

## 7. Configuration

### Environment Variables

```bash
# Enable/disable hook
export PYTHON_ANTIPATTERN_ENABLED="true"

# Severity levels to report (comma-separated)
export PYTHON_ANTIPATTERN_LEVELS="CRITICAL,HIGH,MEDIUM"

# Block on critical issues
export PYTHON_ANTIPATTERN_BLOCK_CRITICAL="true"

# Specific patterns to disable (comma-separated IDs)
export PYTHON_ANTIPATTERN_DISABLED="P004,C005,G008"

# Maximum issues to report
export PYTHON_ANTIPATTERN_MAX_ISSUES="10"

# Debug mode
export PYTHON_ANTIPATTERN_DEBUG="false"
```

### Project Configuration (.claude/settings.json)

```json
{
  "env": {
    "PYTHON_ANTIPATTERN_ENABLED": "true",
    "PYTHON_ANTIPATTERN_LEVELS": "CRITICAL,HIGH,MEDIUM",
    "PYTHON_ANTIPATTERN_BLOCK_CRITICAL": "true",
    "PYTHON_ANTIPATTERN_DISABLED": "C005,G008"
  },
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

### Per-File Configuration

Support inline configuration comments:
```python
# antipattern: disable=R001,P001
def my_function(items=[]):  # This is intentional
    pass
```

## 8. Dependencies (UV Script Metadata)

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

Uses only Python standard library:
- `ast`: Abstract Syntax Tree analysis
- `json`: Input/output parsing
- `sys`: stdin/stdout/stderr
- `os`: Environment variables
- `pathlib`: Path manipulation
- `re`: Regular expressions
- `typing`: Type hints

## 9. Error Handling

### Fail-Safe Philosophy
**Always fail-safe to "allow"** - Never block valid operations due to hook errors.

### Error Scenarios

1. **Parse Error**: File is not valid Python
   - Decision: `allow` (non-blocking feedback)
   - Message: "Syntax error detected, skipping antipattern check"

2. **AST Error**: Cannot parse file to AST
   - Decision: `allow`
   - Message: "Failed to analyze file structure"

3. **Timeout**: Analysis takes too long
   - Decision: `allow`
   - Timeout: 30 seconds (configured in settings.json)

4. **Large File**: File too large to analyze efficiently
   - Decision: `allow` (skip analysis)
   - Max size: 10,000 lines

### Logging
```python
import sys

def log_error(message: str) -> None:
    """Log error to stderr for debugging."""
    print(f"[unified_python_antipattern] ERROR: {message}", file=sys.stderr)
```

## 10. Implementation Structure

### File Organization
```
.claude/hooks/post_tools/
├── unified_python_antipattern_hook.py   # Main hook implementation
└── utils/                                # Shared utilities
    ├── __init__.py                       # Public API exports
    ├── data_types.py                     # TypedDict definitions
    └── utils.py                          # Shared functions
```

### Module Structure

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Unified Python Antipattern Hook for PostToolUse
================================================

Detects Python-specific antipatterns across 7 categories:
- Runtime issues
- Performance problems
- Complexity concerns
- Security vulnerabilities
- Code organization
- Resource management
- Python gotchas
"""

# Standard library imports
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set

# Import shared utilities
try:
    from utils import (
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_block,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from utils import (  # type: ignore
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_block,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Data Structures ====================

@dataclass
class Issue:
    """Represents a detected antipattern issue."""
    id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    line: int
    column: int
    message: str
    suggestion: str
    code_snippet: str = ""


# ==================== Configuration ====================

class Config:
    """Hook configuration from environment variables."""

    def __init__(self):
        self.enabled = os.getenv("PYTHON_ANTIPATTERN_ENABLED", "true").lower() == "true"
        self.levels = set(os.getenv("PYTHON_ANTIPATTERN_LEVELS", "CRITICAL,HIGH,MEDIUM,LOW").split(","))
        self.block_critical = os.getenv("PYTHON_ANTIPATTERN_BLOCK_CRITICAL", "true").lower() == "true"
        self.disabled_patterns = set(os.getenv("PYTHON_ANTIPATTERN_DISABLED", "").split(","))
        self.max_issues = int(os.getenv("PYTHON_ANTIPATTERN_MAX_ISSUES", "10"))
        self.debug = os.getenv("PYTHON_ANTIPATTERN_DEBUG", "false").lower() == "true"


# ==================== Main Detector ====================

class AntipatternDetector(ast.NodeVisitor):
    """AST visitor for detecting Python antipatterns."""

    def __init__(self, source_code: str, config: Config):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.config = config
        self.issues: List[Issue] = []
        self.current_loop_depth = 0
        self.current_function: Optional[ast.FunctionDef] = None

    # Visitor methods for each node type...


# ==================== Entry Point ====================

def main() -> None:
    """Main entry point for unified antipattern hook."""
    pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Antipattern hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
```

## 11. Testing Strategy

### Test Structure
```
tests/claude_hook/post_tools/
├── test_unified_python_antipattern.py
└── fixtures/
    ├── mutable_defaults.py
    ├── sql_injection.py
    ├── string_concatenation.py
    └── various_antipatterns.py
```

### Test Categories

#### 11.1 Runtime Antipattern Tests
```python
def test_detect_mutable_default():
    """Test detection of mutable default arguments."""
    code = """
def process(items=[]):
    items.append(1)
    return items
"""
    issues = detect_antipatterns(code)
    assert any(i.id == 'R001' for i in issues)

def test_detect_late_binding_closure():
    """Test detection of late binding in closures."""
    code = """
funcs = [lambda x: x + i for i in range(10)]
"""
    issues = detect_antipatterns(code)
    assert any(i.id == 'R007' for i in issues)
```

#### 11.2 Security Antipattern Tests
```python
def test_detect_sql_injection():
    """Test SQL injection detection."""
    code = """
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
"""
    issues = detect_antipatterns(code)
    assert any(i.id == 'S001' and i.severity == 'CRITICAL' for i in issues)

def test_detect_hardcoded_secret():
    """Test hardcoded secret detection."""
    code = """
API_KEY = "sk_live_abc123xyz"
PASSWORD = "super_secret_pass"
"""
    issues = detect_antipatterns(code)
    assert any(i.id == 'S003' for i in issues)
```

#### 11.3 Performance Tests
```python
def test_detect_string_concat_in_loop():
    """Test string concatenation in loop detection."""
    code = """
result = ""
for item in items:
    result += str(item)
"""
    issues = detect_antipatterns(code)
    assert any(i.id == 'P001' for i in issues)
```

#### 11.4 Integration Tests
```python
def test_full_file_analysis():
    """Test complete file analysis."""
    with open("fixtures/various_antipatterns.py") as f:
        code = f.read()
    issues = detect_antipatterns(code)
    assert len(issues) >= 5  # File has multiple antipatterns

def test_configuration_filtering():
    """Test that configuration properly filters issues."""
    config = Config()
    config.levels = {"CRITICAL", "HIGH"}
    # Should only report CRITICAL and HIGH issues
```

### Test Execution
```bash
# Run all tests
uv run pytest tests/claude_hook/post_tools/test_unified_python_antipattern.py -n auto -v

# Run with coverage
uv run pytest tests/claude_hook/post_tools/test_unified_python_antipattern.py --cov --cov-report=html

# Run specific test category
uv run pytest tests/claude_hook/post_tools/test_unified_python_antipattern.py -k "security" -v
```

## 12. Performance Optimization

### Analysis Limits
```python
MAX_FILE_LINES = 10_000  # Skip files larger than this
MAX_ANALYSIS_TIME = 25   # Seconds (with 30s total timeout)
```

### Caching Strategy
```python
# Cache AST parsing for session
_ast_cache: Dict[str, ast.Module] = {}

def get_cached_ast(file_path: str, content: str) -> Optional[ast.Module]:
    """Get cached AST or parse and cache."""
    cache_key = f"{file_path}:{hash(content)}"
    if cache_key in _ast_cache:
        return _ast_cache[cache_key]

    try:
        tree = ast.parse(content, filename=file_path)
        _ast_cache[cache_key] = tree
        return tree
    except SyntaxError:
        return None
```

### Early Exit Optimization
```python
def should_skip_file(file_path: str) -> bool:
    """Check if file should be skipped."""
    # Skip test files
    if "test" in Path(file_path).parts:
        return True

    # Skip large files
    if Path(file_path).stat().st_size > 500_000:  # 500KB
        return True

    return False
```

## 13. Output Formatting

### Issue Report Format
```python
def format_issue_report(issues: List[Issue], file_path: str) -> str:
    """Format issues for display."""
    if not issues:
        return f"✅ No antipatterns detected in {Path(file_path).name}"

    # Group by severity
    by_severity = {
        'CRITICAL': [],
        'HIGH': [],
        'MEDIUM': [],
        'LOW': []
    }
    for issue in issues:
        by_severity[issue.severity].append(issue)

    # Build report
    lines = [f"⚠️ Python antipatterns found in {Path(file_path).name}:\n"]

    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        for issue in by_severity[severity]:
            lines.append(f"[{issue.id}:{severity}] {issue.message} on line {issue.line}")
            if issue.code_snippet:
                lines.append(f"  {issue.code_snippet}")
            lines.append(f"  \n  Fix: {issue.suggestion}\n")

    # Summary
    count = len(issues)
    counts = {s: len(by_severity[s]) for s in by_severity if by_severity[s]}
    summary = ", ".join(f"{n} {s}" for s, n in counts.items())
    lines.append(f"{count} issue{'s' if count != 1 else ''} found ({summary})")

    return "\n".join(lines)
```

## 14. Security Considerations

### Path Validation
```python
def validate_file_path(file_path: str) -> bool:
    """Ensure file path is within project directory."""
    try:
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
        file_abs = Path(file_path).resolve()
        file_abs.relative_to(project_dir)
        return True
    except (ValueError, OSError):
        return False
```

### Safe File Reading
```python
def safe_read_file(file_path: str) -> Optional[str]:
    """Safely read file content."""
    try:
        # Size limit
        if Path(file_path).stat().st_size > 1_048_576:  # 1MB
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, UnicodeDecodeError):
        return None
```

## 15. Future Enhancements

### Potential Improvements
1. **Machine Learning**: Train model for context-aware antipattern detection
2. **Auto-fix Suggestions**: Generate Edit tool calls for automatic fixes
3. **Project-wide Analysis**: Check for cross-file antipatterns
4. **Custom Patterns**: Allow users to define custom antipatterns
5. **IDE Integration**: Export findings for IDE consumption
6. **Metrics Dashboard**: Track antipattern trends over time

## 16. Implementation Checklist

- [ ] Create hook script with UV metadata
- [ ] Implement AST visitor base class
- [ ] Implement runtime antipattern detectors (R001-R011)
- [ ] Implement performance antipattern detectors (P001-P010)
- [ ] Implement complexity antipattern detectors (C001-C010)
- [ ] Implement security antipattern detectors (S001-S010)
- [ ] Implement code organization detectors (O001-O007)
- [ ] Implement resource management detectors (M001-M005)
- [ ] Implement Python gotcha detectors (G001-G010)
- [ ] Add configuration management
- [ ] Implement output formatting
- [ ] Add error handling and fail-safe mechanisms
- [ ] Write comprehensive unit tests (40+ patterns)
- [ ] Test with real-world Python files
- [ ] Add inline documentation
- [ ] Update .claude/settings.json
- [ ] Create README documentation
- [ ] Performance testing and optimization

## 17. Success Criteria

### Functional Requirements
✅ Detects 40+ Python antipatterns across 7 categories
✅ Uses AST analysis for accurate detection
✅ Provides clear, actionable feedback
✅ Configurable severity levels and pattern filtering
✅ Non-blocking by default, blocks only critical security issues
✅ Fails safe on errors

### Performance Requirements
✅ Completes analysis within 30-second timeout
✅ Handles files up to 10,000 lines
✅ No noticeable impact on Claude Code responsiveness
✅ Efficient AST traversal and pattern matching

### Quality Requirements
✅ 95%+ test coverage for detection logic
✅ All tests pass with pytest
✅ Type checking passes with basedpyright
✅ Clear documentation with examples
✅ False positive rate < 5%

---

**Specification Version**: 1.0
**Last Updated**: 2025-10-31
**Author**: Claude Code Hook Expert
**Status**: Ready for Implementation
