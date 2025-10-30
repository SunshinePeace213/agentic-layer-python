# PEP 8 Naming Enforcer Hook Specification

## Overview

**Hook Name:** `pep8_naming_enforcer.py`
**Hook Event:** PreToolUse
**Monitored Tools:** Write, Edit
**Version:** 1.0.0
**Author:** Claude Code Hook Expert
**Created:** 2025-10-30

## Purpose

Enforce PEP 8 naming conventions for Python code before files are written during development. This ensures consistent, Pythonic code style across the project by validating that all identifiers (classes, functions, variables, constants) follow PEP 8 naming standards.

## Problem Statement

### Current Challenges

1. **Inconsistent Naming**: Developers may use inconsistent naming conventions (camelCase, PascalCase, snake_case) inappropriately
2. **Style Drift**: Without automated enforcement, code style can drift from PEP 8 standards over time
3. **Code Review Burden**: Manual code review must catch naming violations, slowing development
4. **Learning Curve**: New Python developers may not be familiar with PEP 8 conventions
5. **Mixed Conventions**: Teams migrating from other languages may bring non-Pythonic naming patterns

### Impact

- Reduced code readability and maintainability
- Inconsistent codebase that violates community standards
- Additional time spent in code review on style issues
- Confusion for developers reading non-idiomatic Python code

## Objectives

### Primary Goals

1. **Enforce PEP 8 Naming**: Automatically validate all Python identifiers against PEP 8 standards
2. **Educational Feedback**: Provide clear, helpful error messages explaining violations and correct patterns
3. **Early Detection**: Catch naming violations before files are written, not after
4. **Zero Configuration**: Work out-of-the-box with sensible defaults
5. **Non-Disruptive**: Fail-safe behavior to avoid blocking legitimate operations

### Success Criteria

- Hook detects 95%+ of PEP 8 naming violations
- Execution time < 200ms for typical Python files
- Zero false positives for valid PEP 8 code
- Clear, actionable error messages
- No external dependencies beyond Python 3.12+

## Hook Event Selection

### PreToolUse Event

**Rationale:**
- Validates code BEFORE files are written to disk
- Prevents PEP 8 violations from entering the codebase
- Allows blocking operations with educational feedback
- Supports permissionDecision output format

**Alternative Considered:**
- PostToolUse: Rejected because violations would already be written to disk
- UserPromptSubmit: Rejected because it lacks access to file content
- SessionStart: Rejected because it runs too early in the workflow

## Monitored Tools

### Write Tool

**Purpose:** Validate naming conventions when creating new Python files

**Input Parameters:**
- `file_path`: Path to the file being created
- `content`: Full content of the new file

**Validation Logic:**
1. Check if file extension is `.py`
2. Parse content with Python AST
3. Extract and validate all identifiers
4. Allow or deny based on validation results

### Edit Tool

**Purpose:** Validate naming conventions when modifying existing Python files

**Input Parameters:**
- `file_path`: Path to the file being edited
- `old_string`: Content being replaced
- `new_string`: New content being inserted

**Validation Logic:**
1. Check if file extension is `.py`
2. For comprehensive validation: Read full file content and apply `new_string`
3. Parse complete file with Python AST
4. Extract and validate all identifiers
5. Allow or deny based on validation results

**Note:** Edit tool validation should check the ENTIRE file after edits, not just the changed section, to ensure overall file consistency.

## PEP 8 Naming Convention Rules

### 1. Class Names

**Rule:** CapWords (CamelCase)
**Pattern:** `^[A-Z][a-zA-Z0-9]*$`

**Valid Examples:**
- `MyClass`
- `HTTPServer`
- `UserProfile`
- `DatabaseConnection`

**Invalid Examples:**
- `myClass` (starts with lowercase)
- `my_class` (uses underscores)
- `MYCLASS` (all uppercase - reserved for constants)
- `My_Class` (mixed style)

**Special Cases:**
- Exception classes should end with "Error" suffix if representing errors
- Acronyms should be capitalized: `HTTPServerError` preferred over `HttpServerError`

### 2. Function and Method Names

**Rule:** lowercase_with_underscores (snake_case)
**Pattern:** `^[a-z_][a-z0-9_]*$`

**Valid Examples:**
- `get_user_data`
- `calculate_total`
- `process_payment`
- `send_email`

**Invalid Examples:**
- `getUserData` (camelCase)
- `GetUserData` (PascalCase)
- `get-user-data` (hyphens not allowed)
- `GetUser_Data` (mixed style)

**Special Cases:**
- Magic methods: `__init__`, `__str__`, `__repr__` (ALLOWED)
- Private methods: `_internal_method`, `_validate` (ALLOWED)
- Name mangling: `__private_method` (ALLOWED)
- mixedCase: Only allowed for backward compatibility in existing codebases

### 3. Variables

**Rule:** lowercase_with_underscores (snake_case)
**Pattern:** `^[a-z_][a-z0-9_]*$`

**Valid Examples:**
- `user_count`
- `total_price`
- `is_valid`
- `max_retries`

**Invalid Examples:**
- `userCount` (camelCase)
- `UserCount` (PascalCase)
- `USER_COUNT` (all uppercase - this is a constant)

**Special Cases:**
- Loop variables: `i`, `j`, `k` (ALLOWED as single-char exceptions)
- Private variables: `_internal_state` (ALLOWED)
- Trailing underscore: `class_`, `type_` (ALLOWED for keyword conflicts)

### 4. Constants

**Rule:** UPPER_CASE_WITH_UNDERSCORES
**Pattern:** `^[A-Z][A-Z0-9_]*$`

**Valid Examples:**
- `MAX_SIZE`
- `DEFAULT_TIMEOUT`
- `API_KEY`
- `HTTP_STATUS_OK`

**Invalid Examples:**
- `max_size` (lowercase - this is a variable)
- `MaxSize` (PascalCase - this is a class)
- `Max_Size` (mixed case)

**Detection Logic:**
- Constants are module-level assignments with ALL_CAPS names
- Distinguish from classes by context (assignment vs class definition)
- Consider only assignments at module level (not inside functions/classes)

### 5. Module-Level Private Names

**Rule:** Single leading underscore for internal use
**Pattern:** `^_[a-z][a-z0-9_]*$`

**Valid Examples:**
- `_internal_function`
- `_private_constant`
- `_helper_method`

**Purpose:** Indicates "internal use" - not imported by `from module import *`

### 6. Type Variables

**Rule:** CapWords with short names preferred
**Pattern:** `^[A-Z][a-zA-Z0-9]*(_co|_contra)?$`

**Valid Examples:**
- `T`
- `AnyStr`
- `Num`
- `T_co` (covariant)
- `T_contra` (contravariant)

**Detection Logic:**
- TypeVar assignments at module level
- Short CapWords names (1-10 chars typically)

### 7. Reserved Names to Avoid

**Never Use:**
- `l` (lowercase L) - looks like 1
- `O` (uppercase O) - looks like 0
- `I` (uppercase I) - looks like 1

**Validation:** Flag these as violations even if they match patterns

## Implementation Architecture

### File Structure

```
.claude/hooks/pre_tools/
├── pep8_naming_enforcer.py       # Main hook implementation
├── utils/
│   ├── __init__.py               # Public API exports
│   ├── data_types.py             # TypedDict definitions (existing)
│   └── utils.py                  # Shared utilities (existing)
└── tests/
    └── test_pep8_naming_enforcer.py  # Unit tests

specs/experts/cc_hook_expert/pre_tools/
└── pep8-naming-enforcer-spec.md  # This specification

tests/claude-hook/pre_tools/
└── test_pep8_naming_enforcer.py  # Integration tests
```

### Dependencies

**UV Script Metadata:**
```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**Standard Library Only:**
- `ast` - Python AST parsing
- `os` - Path operations
- `sys` - I/O and exit codes
- `json` - Input/output parsing
- `re` - Regular expressions for pattern matching
- `pathlib` - Path handling

### Input Schema

**JSON Input (via stdin):**
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/src/mymodule.py",
    "content": "class myClass:\n    pass"
  }
}
```

**For Edit Tool:**
```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/project/src/mymodule.py",
    "old_string": "class MyClass:",
    "new_string": "class myClass:"
  }
}
```

### Output Schema

**Success (Allow):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "All identifiers follow PEP 8 naming conventions"
  },
  "suppressOutput": true
}
```

**Failure (Deny):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🐍 Blocked: PEP 8 naming convention violations\n\nFile: /project/src/mymodule.py\n\n❌ Violations found:\n\n1. Class 'myClass' (line 1)\n   Issue: Class names must use CapWords (CamelCase)\n   Suggestion: Rename to 'MyClass'\n   Rule: PEP 8 requires class names to start with uppercase and use CapWords\n\n2. Function 'GetUserData' (line 4)\n   Issue: Function names must use lowercase_with_underscores\n   Suggestion: Rename to 'get_user_data'\n   Rule: PEP 8 requires function names to be lowercase with underscores\n\nTotal violations: 2\n\nLearn more: https://peps.python.org/pep-0008/#naming-conventions"
  },
  "suppressOutput": true
}
```

**Error (Fail-Safe Allow):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Hook error (fail-safe): Unable to parse Python syntax"
  }
}
```

## Core Logic Flow

### Main Execution Flow

```
1. Parse input from stdin
   ↓
2. Validate tool name (Write or Edit)
   ↓
3. Extract file path from tool_input
   ↓
4. Check if file is Python (.py extension)
   ↓
5. Get file content:
   - Write: Use tool_input.content directly
   - Edit: Read current file + apply edit to get final content
   ↓
6. Parse content with Python AST
   ↓
7. Extract all identifiers using AST visitor
   ↓
8. Validate each identifier against PEP 8 rules
   ↓
9. Collect all violations
   ↓
10. Output decision:
    - No violations: Allow
    - Has violations: Deny with detailed message
    - Parse error: Allow (fail-safe)
```

### AST Visitor Implementation

**Classes to Extract:**

1. **ClassDef** - Class definitions
   - Validate: `class_name` against CapWords pattern
   - Store: name, line number, column offset

2. **FunctionDef / AsyncFunctionDef** - Function/method definitions
   - Validate: `function_name` against lowercase_with_underscores pattern
   - Handle exceptions: `__magic__` methods, `_private` methods
   - Store: name, line number, is_magic, is_private

3. **Assign** - Variable assignments
   - Validate: target names against lowercase_with_underscores pattern
   - Detect constants: module-level ALL_CAPS assignments
   - Store: name, line number, is_constant, scope

4. **Name (Store context)** - Variable assignments
   - Validate: variable names in assignments
   - Store: name, line number, context

5. **arg** - Function arguments
   - Validate: parameter names against lowercase_with_underscores pattern
   - Handle exceptions: `self`, `cls`
   - Store: name, line number

**Visitor Pattern:**
```python
class PEP8NamingVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.scope_stack = []  # Track module/class/function scope

    def visit_ClassDef(self, node):
        self.validate_class_name(node)
        self.scope_stack.append(('class', node.name))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        self.validate_function_name(node)
        self.scope_stack.append(('function', node.name))
        # Validate function arguments
        for arg in node.args.args:
            self.validate_argument_name(arg)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node):
        # Determine if constant (module-level + ALL_CAPS)
        is_module_level = len(self.scope_stack) == 0
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.validate_variable_or_constant(target, is_module_level)
        self.generic_visit(node)
```

### Validation Functions

**1. Class Name Validation:**
```python
def validate_class_name(name: str, line: int) -> Optional[Violation]:
    """
    Validate class name follows CapWords convention.

    Rules:
    - Must start with uppercase letter
    - Can contain letters and numbers
    - No underscores (except for special cases)

    Returns:
        Violation if invalid, None if valid
    """
    # Allow special cases
    if name.startswith('_'):  # Private classes allowed
        return None

    # Check CapWords pattern
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="class",
            expected_pattern="CapWords (e.g., MyClass, HTTPServer)",
            suggestion=to_cap_words(name)
        )
    return None
```

**2. Function Name Validation:**
```python
def validate_function_name(name: str, line: int) -> Optional[Violation]:
    """
    Validate function name follows lowercase_with_underscores convention.

    Rules:
    - Must be lowercase with underscores
    - Can start with underscore (private)
    - Magic methods (__method__) allowed

    Returns:
        Violation if invalid, None if valid
    """
    # Allow magic methods
    if name.startswith('__') and name.endswith('__'):
        return None

    # Allow private methods
    if name.startswith('_'):
        name = name[1:]  # Check remaining part

    # Check lowercase_with_underscores pattern
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="function",
            expected_pattern="lowercase_with_underscores (e.g., get_user_data)",
            suggestion=to_snake_case(name)
        )
    return None
```

**3. Variable/Constant Validation:**
```python
def validate_variable_or_constant(name: str, line: int, is_module_level: bool) -> Optional[Violation]:
    """
    Validate variable or constant name.

    Rules:
    - Module-level ALL_CAPS: Constant (UPPER_CASE_WITH_UNDERSCORES)
    - Otherwise: Variable (lowercase_with_underscores)

    Returns:
        Violation if invalid, None if valid
    """
    # Reserved names check
    if name in ('l', 'O', 'I'):
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="reserved",
            expected_pattern="Avoid single-char names that look like numbers",
            suggestion=get_alternative_name(name)
        )

    # Detect constant (module-level + ALL_CAPS)
    if is_module_level and name.isupper() and '_' in name:
        # Validate constant pattern
        if not re.match(r'^[A-Z][A-Z0-9_]*$', name):
            return Violation(
                identifier_name=name,
                line_number=line,
                violation_type="constant",
                expected_pattern="UPPER_CASE_WITH_UNDERSCORES",
                suggestion=to_upper_snake_case(name)
            )
    else:
        # Validate variable pattern
        # Allow trailing underscore (keyword conflicts)
        clean_name = name.rstrip('_')
        if not re.match(r'^[a-z_][a-z0-9_]*$', clean_name):
            return Violation(
                identifier_name=name,
                line_number=line,
                violation_type="variable",
                expected_pattern="lowercase_with_underscores",
                suggestion=to_snake_case(name)
            )

    return None
```

### Name Conversion Utilities

**1. Convert to CapWords:**
```python
def to_cap_words(name: str) -> str:
    """Convert snake_case or camelCase to CapWords."""
    # Handle snake_case: user_profile -> UserProfile
    if '_' in name:
        parts = name.split('_')
        return ''.join(part.capitalize() for part in parts if part)

    # Handle camelCase: userProfile -> UserProfile
    if name and name[0].islower():
        return name[0].upper() + name[1:]

    return name
```

**2. Convert to snake_case:**
```python
def to_snake_case(name: str) -> str:
    """Convert CapWords or camelCase to snake_case."""
    # Insert underscore before uppercase letters
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()
```

**3. Convert to UPPER_SNAKE_CASE:**
```python
def to_upper_snake_case(name: str) -> str:
    """Convert any case to UPPER_SNAKE_CASE."""
    snake = to_snake_case(name)
    return snake.upper()
```

## Error Messages

### Comprehensive Denial Message Format

```
🐍 Blocked: PEP 8 naming convention violations

File: {file_path}

❌ Violations found:

{violation_list}

Total violations: {count}

PEP 8 Naming Quick Reference:
  • Classes: CapWords (MyClass, HTTPServer)
  • Functions: lowercase_with_underscores (get_user, calculate_total)
  • Variables: lowercase_with_underscores (user_count, is_valid)
  • Constants: UPPER_CASE_WITH_UNDERSCORES (MAX_SIZE, API_KEY)
  • Private: _leading_underscore (_internal_method, _private_var)

Learn more: https://peps.python.org/pep-0008/#naming-conventions
```

### Individual Violation Format

```
{number}. {identifier_type} '{identifier_name}' (line {line_number})
   Issue: {description}
   Suggestion: Rename to '{suggested_name}'
   Rule: {pep8_rule_explanation}
```

### Example Violation Messages

**Class Violation:**
```
1. Class 'userProfile' (line 5)
   Issue: Class names must use CapWords (CamelCase)
   Suggestion: Rename to 'UserProfile'
   Rule: PEP 8 requires class names to start with uppercase and use CapWords
```

**Function Violation:**
```
2. Function 'GetUserData' (line 12)
   Issue: Function names must use lowercase_with_underscores
   Suggestion: Rename to 'get_user_data'
   Rule: PEP 8 requires function names to be lowercase with underscores
```

**Variable Violation:**
```
3. Variable 'userName' (line 18)
   Issue: Variable names must use lowercase_with_underscores
   Suggestion: Rename to 'user_name'
   Rule: PEP 8 requires variable names to be lowercase with underscores
```

**Constant Violation:**
```
4. Constant 'maxSize' (line 3)
   Issue: Module-level constants must use UPPER_CASE_WITH_UNDERSCORES
   Suggestion: Rename to 'MAX_SIZE'
   Rule: PEP 8 requires constants to be all uppercase with underscores
```

**Reserved Name Violation:**
```
5. Variable 'l' (line 25)
   Issue: Single-char name 'l' looks like number 1
   Suggestion: Use a descriptive name like 'line' or 'length'
   Rule: PEP 8 prohibits using 'l', 'O', 'I' as they're indistinguishable from numbers
```

## Edge Cases and Special Handling

### 1. Magic Methods (Dunder Methods)

**Handling:** ALLOW all `__method__` patterns without validation

**Examples:**
- `__init__`, `__str__`, `__repr__` ✓ Allowed
- `__add__`, `__eq__`, `__call__` ✓ Allowed
- Custom: `__my_custom_method__` ✓ Allowed

**Logic:** Check if name matches pattern `^__[a-z_]+__$`

### 2. Private/Internal Names

**Handling:** ALLOW single or double leading underscore

**Examples:**
- `_internal_function` ✓ Allowed (internal use)
- `_validate` ✓ Allowed
- `__private_attr` ✓ Allowed (name mangling)
- `_MyPrivateClass` ✓ Allowed (private class)

**Logic:** Check if name starts with `_` before applying main validation

### 3. Keyword Conflicts

**Handling:** ALLOW trailing underscore for keyword conflicts

**Examples:**
- `class_` ✓ Allowed (avoids 'class' keyword)
- `type_` ✓ Allowed (avoids 'type' keyword)
- `id_` ✓ Allowed (avoids shadowing 'id' builtin)

**Logic:** Strip trailing underscore before pattern validation

### 4. Single-Character Variables

**Handling:** ALLOW common single-char loop variables, BLOCK reserved names

**Allowed:**
- `i`, `j`, `k` ✓ (common loop counters)
- `x`, `y`, `z` ✓ (coordinates)
- `n`, `m` ✓ (mathematical variables)
- `f`, `e` ✓ (file, exception in context)

**Blocked:**
- `l` ✗ (looks like 1)
- `O` ✗ (looks like 0)
- `I` ✗ (looks like 1)

**Logic:** Explicit whitelist for common patterns, explicit blocklist for reserved

### 5. Type Variables

**Handling:** ALLOW short CapWords type variables

**Examples:**
- `T` ✓ Allowed (generic type)
- `AnyStr` ✓ Allowed (string type)
- `T_co` ✓ Allowed (covariant)
- `T_contra` ✓ Allowed (contravariant)

**Detection:** TypeVar assignments at module level OR CapWords < 3 chars

### 6. Test Files and Fixtures

**Handling:** Apply same rules (no special relaxation)

**Rationale:** Test code should also follow PEP 8 conventions for consistency

**Alternative:** Could add configuration option to relax rules for test files in future

### 7. Mixed Case for Backward Compatibility

**Handling:** ALLOW with optional warning (configurable)

**Example:** Legacy codebases using `mixedCase` for functions

**Logic:** Detect mixed case pattern, allow but optionally warn

### 8. Non-Python Files

**Handling:** ALLOW immediately (skip validation)

**Detection:** Check file extension != `.py`

**Examples:**
- `config.json` ✓ Skipped
- `README.md` ✓ Skipped
- `script.sh` ✓ Skipped

### 9. Empty or Invalid Python Files

**Handling:** ALLOW (fail-safe behavior)

**Cases:**
- Empty file content
- Syntax errors (can't parse AST)
- Invalid Python (corrupted file)

**Logic:** Try to parse, catch exceptions, allow on error

### 10. Generated Code Markers

**Handling:** ALLOW files with auto-generation markers

**Detection:** Check for special comments:
- `# This file is auto-generated`
- `# DO NOT EDIT`
- `# Generated by ...`

**Logic:** Scan first 5 lines for generation markers, skip validation if found

### 11. Third-Party Integration Code

**Handling:** Apply same rules (no special handling)

**Rationale:** Project code should follow PEP 8 even when interfacing with third-party libraries

**Note:** If third-party library requires non-PEP-8 names (e.g., Django's `setUp`), developers can:
1. Temporarily disable hook
2. Use thin adapter layer with PEP-8 compliant wrappers

### 12. Acronyms and Abbreviations

**Handling:** Follow PEP 8 guidance on acronyms

**Classes with Acronyms:**
- `HTTPServer` ✓ Preferred (all caps)
- `HttpServer` ✓ Acceptable
- `HTTPserver` ✗ Invalid (mixed)

**Logic:** Allow both all-caps and capitalized-first patterns for acronyms in class names

## Security and Safety

### Security Measures

1. **Input Validation**
   - Validate all input from stdin before processing
   - Sanitize file paths to prevent traversal attacks
   - Limit file size to prevent DoS (skip files > 10 MB)

2. **Safe AST Parsing**
   - Use `ast.parse()` with safe mode
   - Catch all parsing exceptions
   - Never execute code, only analyze structure

3. **Resource Limits**
   - Timeout: 60 seconds (configurable)
   - Memory: < 50 MB for typical files
   - Max file size: 10 MB (skip larger files)

4. **Fail-Safe Behavior**
   - Allow operation on any error
   - Never block due to hook bugs
   - Log errors to stderr for debugging

5. **No Code Execution**
   - Hook only analyzes static code structure
   - Never imports or executes user code
   - Pure AST inspection only

### Error Handling Strategy

```python
def main():
    try:
        # Main validation logic
        result = validate_pep8_naming()
        output_decision(result)
    except SyntaxError:
        # Invalid Python syntax - allow (user will see Python error later)
        output_decision("allow", "Unable to parse Python syntax (fail-safe)")
    except Exception as e:
        # Unexpected error - fail-safe allow
        print(f"PEP 8 naming enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Privacy and Data Handling

1. **No Data Retention**: Hook doesn't store or transmit file contents
2. **Local Processing**: All validation happens locally
3. **No Network Calls**: Hook never makes external requests
4. **Minimal Logging**: Only log to stderr for debugging, no file logging

## Performance Considerations

### Expected Performance

- **Typical Python File (< 500 lines):** < 50ms
- **Medium File (500-2000 lines):** < 150ms
- **Large File (2000-5000 lines):** < 300ms
- **Very Large File (> 5000 lines):** Skip validation (performance)

### Optimization Strategies

1. **Early Exit**
   - Check file extension first
   - Skip non-Python files immediately

2. **Single-Pass AST**
   - Use visitor pattern for one-pass analysis
   - Collect all violations in single traversal

3. **Efficient Pattern Matching**
   - Compile regex patterns once at module level
   - Cache pattern matching results

4. **Memory Efficiency**
   - Stream processing where possible
   - Don't load entire AST if not needed
   - Clear violation list after output

5. **Size Limits**
   - Skip files > 10 MB
   - Provide quick message about size limit

### Performance Monitoring

Include execution time in debug output:
```python
import time
start_time = time.time()
# ... validation logic ...
elapsed = time.time() - start_time
if elapsed > 0.2:  # Log slow executions
    print(f"PEP 8 validation took {elapsed:.2f}s", file=sys.stderr)
```

## Testing Strategy

### Unit Tests

**Location:** `tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py`

**Test Categories:**

1. **Class Name Validation**
   - Valid: `MyClass`, `HTTPServer`, `_PrivateClass`
   - Invalid: `myClass`, `my_class`, `MYCLASS`

2. **Function Name Validation**
   - Valid: `get_user`, `_private_func`, `__magic__`
   - Invalid: `GetUser`, `getUser`, `GET_USER`

3. **Variable Name Validation**
   - Valid: `user_count`, `_private_var`, `i`, `j`
   - Invalid: `userName`, `UserName`, `l`, `O`, `I`

4. **Constant Name Validation**
   - Valid: `MAX_SIZE`, `API_KEY`, `HTTP_OK`
   - Invalid: `maxSize`, `Max_Size`, `max_size` (at module level)

5. **Edge Cases**
   - Magic methods: `__init__`, `__str__`
   - Private names: `_internal`, `__private`
   - Keyword conflicts: `class_`, `type_`
   - Single-char: `i`, `j`, `x`, `y`, `n`
   - Reserved: `l`, `O`, `I`
   - Type variables: `T`, `AnyStr`, `T_co`

6. **Tool Integration**
   - Write tool with valid Python
   - Write tool with invalid Python
   - Edit tool with valid Python
   - Edit tool with invalid Python
   - Non-Python files

7. **Error Handling**
   - Syntax errors in Python code
   - Empty file content
   - Invalid JSON input
   - Missing file_path
   - Parse failures

8. **Performance**
   - Small files (< 100 lines)
   - Medium files (500 lines)
   - Large files (2000+ lines)
   - Execution time < 200ms

### Integration Tests

**Manual Testing:**
```bash
# Test with valid Python
echo '{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "test.py",
    "content": "class MyClass:\n    def get_data(self):\n        return 42"
  }
}' | uv run .claude/hooks/pre_tools/pep8_naming_enforcer.py

# Test with invalid Python
echo '{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "test.py",
    "content": "class myClass:\n    def GetData(self):\n        userName = \"test\"\n        return userName"
  }
}' | uv run .claude/hooks/pre_tools/pep8_naming_enforcer.py

# Test with non-Python file
echo '{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "config.json",
    "content": "{\"key\": \"value\"}"
  }
}' | uv run .claude/hooks/pre_tools/pep8_naming_enforcer.py
```

### Test Coverage Goals

- **Line Coverage:** > 90%
- **Branch Coverage:** > 85%
- **Edge Case Coverage:** 100% of identified edge cases
- **Validation Rule Coverage:** 100% of PEP 8 naming rules

### Continuous Testing

**Test Execution:**
```bash
# Run all tests
uv run pytest -n auto tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py

# Run with coverage
uv run pytest --cov=.claude/hooks/pre_tools/pep8_naming_enforcer \
  --cov-report=html \
  tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py

# Run specific test category
uv run pytest -k "test_class_names" tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py
```

## Configuration

### Settings.json Registration

**Location:** `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/pep8_naming_enforcer.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Configuration Options (Future Enhancement)

**Planned configuration options in hook script:**

```python
# Configuration constants (can be overridden via environment variables)
MAX_FILE_SIZE_MB = int(os.environ.get("PEP8_MAX_FILE_SIZE_MB", "10"))
SKIP_TEST_FILES = os.environ.get("PEP8_SKIP_TEST_FILES", "false").lower() == "true"
ALLOW_MIXED_CASE = os.environ.get("PEP8_ALLOW_MIXED_CASE", "false").lower() == "true"
WARN_ON_MIXED_CASE = os.environ.get("PEP8_WARN_MIXED_CASE", "true").lower() == "true"
SKIP_GENERATED_FILES = os.environ.get("PEP8_SKIP_GENERATED", "true").lower() == "true"
```

**Environment Variables:**
- `PEP8_MAX_FILE_SIZE_MB`: Maximum file size to validate (default: 10)
- `PEP8_SKIP_TEST_FILES`: Skip validation for test files (default: false)
- `PEP8_ALLOW_MIXED_CASE`: Allow mixedCase for backward compatibility (default: false)
- `PEP8_WARN_MIXED_CASE`: Warn but don't block mixed case (default: true)
- `PEP8_SKIP_GENERATED`: Skip auto-generated files (default: true)

### Disabling the Hook

**Option 1: Comment out in settings.json**
```json
{
  "hooks": {
    "PreToolUse": [
      // Temporarily disabled
      // {
      //   "matcher": "Write|Edit",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2: Local override (gitignored)**

Create `.claude/settings.local.json`:
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3: Rename or delete script**
```bash
mv .claude/hooks/pre_tools/pep8_naming_enforcer.py \
   .claude/hooks/pre_tools/pep8_naming_enforcer.py.disabled
```

## Integration with Existing Hooks

### Hook Execution Order

PreToolUse hooks run in parallel by default, so execution order doesn't matter for this hook.

**Current PreToolUse Hooks:**
1. `uv_dependency_blocker.py` (Write|Edit matcher)
2. `uv_workflow_enforcer.py` (Bash matcher)
3. `tmp_creation_blocker.py` (Write|Edit|Bash matcher)
4. `universal_hook_logger.py` (* matcher)
5. **`pep8_naming_enforcer.py`** (Write|Edit matcher) ← NEW

**No Conflicts:**
- Different tools or independent validation
- All hooks can run in parallel
- Each hook has independent decision logic

### Shared Utilities

**Uses existing utilities:**
- `utils/data_types.py` - TypedDict definitions
- `utils/utils.py` - `parse_hook_input()`, `output_decision()`

**New utility functions (if needed):**
Could add to `utils/utils.py`:
- `is_python_file(file_path: str) -> bool`
- `read_file_safely(file_path: str, max_size: int) -> Optional[str]`

## Documentation

### User-Facing Documentation

**Location:** `.claude/hooks/pre_tools/README.md`

Add section documenting the hook:
- Purpose and benefits
- How it works
- Examples of blocked/allowed operations
- Error message format
- Configuration options
- Disabling instructions
- Testing instructions
- Performance characteristics

### Developer Documentation

**Inline Documentation:**
- Comprehensive docstrings for all functions
- Type hints for all parameters and return values
- Inline comments for complex logic
- Example usage in docstrings

**Specification:**
- This specification document serves as primary developer reference
- Keep specification updated with implementation changes
- Document all design decisions and rationale

## Success Metrics

### Functional Metrics

1. **Detection Accuracy**
   - Target: 95%+ of PEP 8 naming violations detected
   - Measure: Test suite coverage of PEP 8 rules

2. **False Positive Rate**
   - Target: < 1% false positives on valid PEP 8 code
   - Measure: Test with large corpus of PEP 8 compliant code

3. **Performance**
   - Target: < 200ms for 90% of files
   - Measure: Performance test suite

4. **Reliability**
   - Target: Zero crashes, always fail-safe
   - Measure: Error handling test coverage

### User Experience Metrics

1. **Message Clarity**
   - Target: Developers understand violations without external docs
   - Measure: User feedback, violation message clarity

2. **Actionability**
   - Target: All violations include concrete suggestions
   - Measure: Code review of violation messages

3. **Non-Disruptiveness**
   - Target: No false blocking of legitimate operations
   - Measure: User reports of incorrect blocking

## Future Enhancements

### Phase 2 Features

1. **Configuration File**
   - `.pep8naming.json` for per-project configuration
   - Allow/deny lists for specific patterns
   - Custom severity levels (error vs warning)

2. **Auto-Fix Suggestions**
   - Generate patch files with corrected names
   - Interactive fix mode via Claude Code

3. **Incremental Validation**
   - For Edit tool, only validate changed sections
   - Faster performance for large files

4. **Custom Rules**
   - Project-specific naming conventions
   - Domain-specific abbreviation allowlists

5. **IDE Integration**
   - Export violations in LSP format
   - Real-time validation in editor

6. **Reporting**
   - Generate HTML reports of violations
   - Track violation trends over time
   - Export to CSV for analysis

### Long-Term Vision

1. **Full PEP 8 Enforcement**
   - Extend beyond naming to line length, imports, etc.
   - Comprehensive Python style enforcement

2. **ML-Based Suggestions**
   - Learn from project-specific patterns
   - Suggest contextually appropriate names

3. **Team Consistency**
   - Shared configuration across team
   - Consistency scoring and dashboards

## Appendix

### Related PEP 8 Sections

- **PEP 8 - Naming Conventions:** https://peps.python.org/pep-0008/#naming-conventions
- **PEP 8 - Package and Module Names:** https://peps.python.org/pep-0008/#package-and-module-names
- **PEP 8 - Class Names:** https://peps.python.org/pep-0008/#class-names
- **PEP 8 - Function and Variable Names:** https://peps.python.org/pep-0008/#function-and-variable-names
- **PEP 8 - Constants:** https://peps.python.org/pep-0008/#constants

### References

- **PEP 8:** https://peps.python.org/pep-0008/
- **Python AST Documentation:** https://docs.python.org/3/library/ast.html
- **Claude Code Hooks Guide:** `.claude/ai_docs/claude-code-hooks.md`
- **UV Scripts Guide:** `.claude/ai_docs/uv-scripts-guide.md`

### Glossary

- **AST:** Abstract Syntax Tree - tree representation of Python code structure
- **CapWords:** Capitalized words with no separators (MyClass, HTTPServer)
- **snake_case:** Lowercase with underscores (get_user_data)
- **UPPER_SNAKE_CASE:** Uppercase with underscores (MAX_SIZE)
- **Magic method:** Special Python methods like `__init__`, `__str__`
- **Name mangling:** Python's double-underscore attribute name transformation
- **PreToolUse:** Hook event that runs before tool execution
- **Fail-safe:** Behavior that allows operations on errors to avoid disrupting development

---

**Specification Version:** 1.0.0
**Last Updated:** 2025-10-30
**Status:** Ready for Implementation
