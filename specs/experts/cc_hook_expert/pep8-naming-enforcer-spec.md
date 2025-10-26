# PEP 8 Naming Convention Enforcer - Hook Specification

## 1. Overview

### Purpose
The `pep8_naming_enforcer.py` hook enforces PEP 8 naming conventions for Python code before files are written during development. This ensures consistent, Pythonic code style across the project by validating that all identifiers (classes, functions, variables, constants) follow PEP 8 naming standards.

### Problem Statement
During development, Claude Code may generate Python code with inconsistent naming conventions:
- camelCase function names instead of snake_case
- lowercase class names instead of PascalCase
- Mixed naming styles for constants
- Non-Pythonic identifier patterns
- Names that shadow Python builtins

These inconsistencies:
- Violate Python community standards (PEP 8)
- Reduce code readability and maintainability
- Make code reviews more difficult
- Create technical debt requiring later refactoring
- Can confuse developers familiar with Python conventions

### Solution
Intercept Python file write/edit operations **before** execution and validate all identifiers against comprehensive PEP 8 naming rules. Block operations that violate conventions with clear, actionable feedback on how to fix the issues.

### PEP 8 Naming Rules Enforced

#### Core Rules
1. **snake_case for variables and functions**
   - Lowercase letters with underscores
   - Example: `my_variable`, `calculate_total()`

2. **PascalCase for classes**
   - Capitalize first letter of each word, no underscores
   - Example: `MyClass`, `DatabaseConnection`

3. **UPPER_CASE for constants**
   - All uppercase letters with underscores
   - Example: `MAX_SIZE`, `DEFAULT_TIMEOUT`

4. **No camelCase or mixedCase** (except specific contexts)
   - Forbidden: `myFunction`, `MyVariable`
   - Exception: When overriding external library methods

5. **Valid Python identifiers**
   - Must start with letter or underscore
   - Contains only letters, numbers, underscores
   - Cannot be Python keywords

#### Additional PEP 8 Rules
6. **Module names**: lowercase_with_underscores, short, no dashes
7. **Package names**: lowercase, preferably without underscores
8. **Private identifiers**: Single leading underscore (`_private_method`)
9. **Name mangling**: Double leading underscore (`__mangled_attr`)
10. **Magic methods**: Double underscores both sides (`__init__`, `__str__`)
11. **Type variables**: Usually short PascalCase (`T`, `KT`, `VT`)
12. **Exception classes**: Suffix with "Error" or "Exception"
13. **Avoid confusing names**: Single `l`, `O`, `I` characters
14. **No builtin shadowing**: Avoid names like `list`, `dict`, `str`

## 2. Hook Configuration

### Event Type
**PreToolUse** - Intercepts tool execution before file write/edit operations occur

### Tool Matchers
```json
"matcher": "Write|Edit|MultiEdit|NotebookEdit"
```

**Rationale:**
- `Write` - Primary file creation tool
- `Edit` - File modification tool
- `MultiEdit` - Multiple file edit operations
- `NotebookEdit` - Jupyter notebook cell edits (Python code cells)

**File Filtering:**
Only validate files with Python extensions:
- `.py` - Standard Python files
- `.pyw` - Python Windows GUI scripts
- `.ipynb` - Jupyter notebooks (validate code cells only)

### Hook Registration
Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/pep8_naming_enforcer.py"
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
    "file_path": "/project/module.py",
    "content": "class myClass:\n    def MyMethod(self):\n        pass"
  }
}
```

**Tool-Specific Input Fields:**
- **Write**: `file_path` (string), `content` (string)
- **Edit**: `file_path` (string), `old_string` (string), `new_string` (string)
- **MultiEdit**: `edits` (array of edit operations)
- **NotebookEdit**: `notebook_path` (string), `new_source` (string), `cell_type` (string)

### Output Schema

Returns JSON with permission decision:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 PEP 8 Naming Convention Violations Detected\n\nFile: /project/module.py\n\nViolations found:\n  1. Class name 'myClass' violates PEP 8\n     - Rule: Class names should use PascalCase\n     - Suggestion: Rename to 'MyClass'\n     - Line: 1\n\n  2. Method name 'MyMethod' violates PEP 8\n     - Rule: Function/method names should use snake_case\n     - Suggestion: Rename to 'my_method'\n     - Line: 2\n\nPEP 8 Reference: https://pep8.org/#naming-conventions\n"
  },
  "suppressOutput": false
}
```

**Permission Decision Values:**
- `"allow"` - No violations found, proceed with operation
- `"deny"` - Violations detected, block with detailed feedback
- `"ask"` - Not used (future: could ask user to override for intentional violations)

### Exit Codes
Always exits with `0` (success) since JSON output controls the decision.

## 4. Validation Rules

### Identifier Classification

Using Python's `ast` module, classify identifiers by their AST node type:

```python
import ast

class IdentifierType:
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE_LEVEL_VARIABLE = "module_variable"
    PARAMETER = "parameter"
    TYPE_VARIABLE = "type_variable"
```

### Detection Strategy

```python
class PEP8Validator(ast.NodeVisitor):
    """AST visitor to validate PEP 8 naming conventions."""

    def visit_ClassDef(self, node):
        # Validate class name: PascalCase
        validate_class_name(node.name, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Validate function/method name: snake_case
        validate_function_name(node.name, node.lineno)
        # Validate parameters
        for arg in node.args.args:
            validate_parameter_name(arg.arg, arg.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Classify as constant or variable based on context
        for target in node.targets:
            if isinstance(target, ast.Name):
                if is_module_level(node) and is_all_caps(target.id):
                    validate_constant_name(target.id, node.lineno)
                else:
                    validate_variable_name(target.id, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        # Handle type-annotated assignments (e.g., x: int = 5)
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if is_module_level(node) and is_all_caps(name):
                validate_constant_name(name, node.lineno)
            else:
                validate_variable_name(name, node.lineno)
        self.generic_visit(node)
```

### Validation Functions

#### 1. Class Names (PascalCase)
```python
def validate_class_name(name: str, lineno: int) -> str | None:
    """
    Validate class name follows PascalCase convention.

    Rules:
    - Must start with uppercase letter
    - Each word capitalized, no underscores (except special cases)
    - Exception: Type variables (T, KT, VT)
    - Exception: Private classes (_PrivateClass)
    - Exception: Special classes (__SpecialClass)

    Returns:
        Violation message if invalid, None otherwise
    """
    # Allow private classes
    if name.startswith('_') and not name.startswith('__'):
        name = name[1:]  # Check rest of name

    # Allow magic classes
    if name.startswith('__') and name.endswith('__'):
        return None

    # Check PascalCase pattern
    if not re.match(r'^[A-Z][a-z0-9]*(?:[A-Z][a-z0-9]*)*$', name):
        suggestion = to_pascal_case(name)
        return (
            f"Class name '{name}' violates PEP 8\n"
            f"  - Rule: Class names should use PascalCase\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    # Check for Exception suffix if it's an exception class
    # (Would need AST context to determine if it inherits from Exception)

    return None
```

#### 2. Function/Method Names (snake_case)
```python
def validate_function_name(name: str, lineno: int) -> str | None:
    """
    Validate function/method name follows snake_case convention.

    Rules:
    - Lowercase letters and underscores only
    - Exception: Magic methods (__init__, __str__)
    - Exception: Private methods (_private_method)
    - Exception: Test methods (test_*)
    - Exception: Overridden library methods (e.g., mixins)

    Returns:
        Violation message if invalid, None otherwise
    """
    # Allow magic methods
    if name.startswith('__') and name.endswith('__'):
        return None

    # Strip leading underscores for validation
    clean_name = name.lstrip('_')

    # Check snake_case pattern
    if not re.match(r'^[a-z][a-z0-9_]*$', clean_name):
        suggestion = to_snake_case(name)
        return (
            f"Function name '{name}' violates PEP 8\n"
            f"  - Rule: Function/method names should use snake_case\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    # Check for consecutive underscores
    if '__' in clean_name:
        return (
            f"Function name '{name}' contains double underscores\n"
            f"  - Rule: Avoid consecutive underscores in names\n"
            f"  - Line: {lineno}"
        )

    return None
```

#### 3. Constant Names (UPPER_CASE)
```python
def validate_constant_name(name: str, lineno: int) -> str | None:
    """
    Validate constant name follows UPPER_CASE convention.

    Rules:
    - All uppercase letters and underscores only
    - Module-level or class-level assignments
    - Exception: Private constants (_PRIVATE_CONSTANT)

    Returns:
        Violation message if invalid, None otherwise
    """
    # Strip leading underscores
    clean_name = name.lstrip('_')

    # Check UPPER_CASE pattern
    if not re.match(r'^[A-Z][A-Z0-9_]*$', clean_name):
        suggestion = to_upper_case(name)
        return (
            f"Constant name '{name}' violates PEP 8\n"
            f"  - Rule: Constants should use UPPER_CASE\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    return None
```

#### 4. Variable Names (snake_case)
```python
def validate_variable_name(name: str, lineno: int) -> str | None:
    """
    Validate variable name follows snake_case convention.

    Rules:
    - Lowercase letters, numbers, and underscores
    - Exception: Single character loop counters (i, j, k)
    - Exception: Single character exception handlers (e)
    - Exception: Single character file handles (f)
    - Exception: Private variables (_private_var)

    Returns:
        Violation message if invalid, None otherwise
    """
    # Allow single character names in specific contexts
    if len(name) == 1 and name in 'ijkefxyz':
        return None

    # Allow type variables (T, KT, VT, etc.)
    if re.match(r'^[A-Z]{1,3}T?$', name):
        return None

    # Strip leading underscores
    clean_name = name.lstrip('_')

    # Check snake_case pattern
    if not re.match(r'^[a-z][a-z0-9_]*$', clean_name):
        suggestion = to_snake_case(name)
        return (
            f"Variable name '{name}' violates PEP 8\n"
            f"  - Rule: Variable names should use snake_case\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    return None
```

#### 5. Forbidden Patterns
```python
def check_forbidden_patterns(name: str, lineno: int) -> str | None:
    """
    Check for forbidden naming patterns.

    Rules:
    - No single 'l', 'O', 'I' (confusing)
    - No builtin shadowing (list, dict, str, etc.)
    - No camelCase (except in specific contexts)

    Returns:
        Violation message if invalid, None otherwise
    """
    # Confusing single characters
    if name in ['l', 'O', 'I']:
        return (
            f"Name '{name}' is confusing\n"
            f"  - Rule: Avoid single characters 'l', 'O', 'I'\n"
            f"  - Reason: Easily confused with 1, 0, 1\n"
            f"  - Line: {lineno}"
        )

    # Builtin shadowing
    BUILTINS = {
        'list', 'dict', 'str', 'int', 'float', 'bool', 'tuple',
        'set', 'frozenset', 'bytes', 'bytearray', 'type', 'object',
        'len', 'range', 'map', 'filter', 'zip', 'sum', 'min', 'max',
        'all', 'any', 'input', 'print', 'open', 'file', 'id', 'hash'
    }

    if name in BUILTINS:
        return (
            f"Name '{name}' shadows Python builtin\n"
            f"  - Rule: Never shadow built-in names\n"
            f"  - Suggestion: Use '{name}_value' or '{name}_obj'\n"
            f"  - Line: {lineno}"
        )

    # Detect camelCase
    if re.match(r'^[a-z]+[A-Z]', name):
        suggestion = to_snake_case(name)
        return (
            f"Name '{name}' uses camelCase\n"
            f"  - Rule: Use snake_case for variables/functions\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    return None
```

### Helper Functions for Name Conversion

```python
def to_snake_case(name: str) -> str:
    """Convert name to snake_case."""
    # Handle PascalCase and camelCase
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def to_pascal_case(name: str) -> str:
    """Convert name to PascalCase."""
    # Split on underscores and capitalize
    words = name.split('_')
    return ''.join(word.capitalize() for word in words)


def to_upper_case(name: str) -> str:
    """Convert name to UPPER_CASE."""
    # Convert to snake_case first, then upper
    snake = to_snake_case(name)
    return snake.upper()
```

## 5. File Type Detection

### Python File Extensions
```python
PYTHON_EXTENSIONS = {'.py', '.pyw'}

def is_python_file(file_path: str) -> bool:
    """Check if file is a Python source file."""
    return Path(file_path).suffix in PYTHON_EXTENSIONS


def is_jupyter_notebook(file_path: str) -> bool:
    """Check if file is a Jupyter notebook."""
    return Path(file_path).suffix == '.ipynb'
```

### Jupyter Notebook Handling
For `NotebookEdit` tool:
- Extract `cell_type` from tool_input
- Only validate if `cell_type == "code"`
- Parse `new_source` as Python code
- Apply same validation rules as `.py` files

```python
def validate_notebook_cell(tool_input: ToolInput) -> str | None:
    """Validate Jupyter notebook code cell."""
    cell_type = tool_input.get("cell_type", "")

    # Only validate code cells
    if cell_type != "code":
        return None

    source_code = tool_input.get("new_source", "")
    return validate_python_code(source_code, "<notebook cell>")
```

## 6. Exclusions and Exceptions

### Files to Skip
```python
EXCLUDED_PATTERNS = [
    # Test files with non-standard naming
    'test_*.py',
    '*_test.py',
    'conftest.py',

    # Migration scripts
    '**/migrations/*.py',
    '**/alembic/versions/*.py',

    # Auto-generated files
    '*_pb2.py',  # Protocol buffers
    '*_pb2_grpc.py',
    '**/node_modules/**',

    # Virtual environments
    '**/venv/**',
    '**/.venv/**',
    '**/env/**',

    # Build artifacts
    '**/build/**',
    '**/dist/**',
    '**/__pycache__/**',
]

def should_skip_file(file_path: str) -> bool:
    """Check if file should be excluded from validation."""
    from pathlib import Path
    import fnmatch

    path = Path(file_path)

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(str(path), pattern):
            return True

    return False
```

### Context-Aware Exceptions

#### Exception 1: Test Methods
```python
# Allow test methods with descriptive names
def is_test_method(name: str, class_context: str | None) -> bool:
    """Check if method is a test method."""
    if name.startswith('test_'):
        return True

    # Allow setUp, tearDown, setUpClass, tearDownClass
    if name in {'setUp', 'tearDown', 'setUpClass', 'tearDownClass'}:
        return True

    return False
```

#### Exception 2: Override Methods
```python
# Allow method names that override library methods
OVERRIDE_METHODS = {
    'setUp', 'tearDown',  # unittest
    'setUpClass', 'tearDownClass',  # unittest
    'runTest',  # unittest
    'toString', 'toJSON',  # Common overrides
}

def is_override_method(name: str) -> bool:
    """Check if method name is a known override."""
    return name in OVERRIDE_METHODS
```

#### Exception 3: Magic/Dunder Methods
```python
def is_magic_method(name: str) -> bool:
    """Check if method is a Python magic method."""
    return name.startswith('__') and name.endswith('__')
```

## 7. Error Messages and Suggestions

### Violation Report Format
```python
class ViolationReport:
    """Structure for PEP 8 violations."""

    def __init__(self):
        self.violations: list[dict] = []

    def add_violation(
        self,
        name: str,
        violation_type: str,
        rule: str,
        suggestion: str,
        lineno: int
    ) -> None:
        """Add a violation to the report."""
        self.violations.append({
            'name': name,
            'type': violation_type,
            'rule': rule,
            'suggestion': suggestion,
            'line': lineno
        })

    def format_message(self, file_path: str) -> str:
        """Format violations as user-friendly message."""
        if not self.violations:
            return ""

        lines = [
            "🚫 PEP 8 Naming Convention Violations Detected\n",
            f"File: {file_path}\n",
            f"\nFound {len(self.violations)} violation(s):\n"
        ]

        for i, violation in enumerate(self.violations, 1):
            lines.append(
                f"  {i}. {violation['type']} '{violation['name']}' violates PEP 8\n"
                f"     - Rule: {violation['rule']}\n"
                f"     - Suggestion: {violation['suggestion']}\n"
                f"     - Line: {violation['line']}\n"
            )

        lines.append("\nPEP 8 Reference: https://pep8.org/#naming-conventions\n")

        return "".join(lines)
```

### Example Violation Messages

#### Class Name Violation
```
🚫 PEP 8 Naming Convention Violations Detected

File: /project/models.py

Found 1 violation(s):
  1. Class 'userModel' violates PEP 8
     - Rule: Class names should use PascalCase
     - Suggestion: Rename to 'UserModel'
     - Line: 15

PEP 8 Reference: https://pep8.org/#naming-conventions
```

#### Function Name Violation
```
🚫 PEP 8 Naming Convention Violations Detected

File: /project/utils.py

Found 2 violation(s):
  1. Function 'CalculateTotal' violates PEP 8
     - Rule: Function names should use snake_case
     - Suggestion: Rename to 'calculate_total'
     - Line: 23

  2. Function 'getValue' violates PEP 8
     - Rule: Function names should use snake_case (no camelCase)
     - Suggestion: Rename to 'get_value'
     - Line: 45

PEP 8 Reference: https://pep8.org/#naming-conventions
```

## 8. Code Structure

### File Location
```
.claude/hooks/pre_tools/pep8_naming_enforcer.py
```

### Code Organization
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
PEP 8 Naming Convention Enforcer - PreToolUse Hook
===================================================
Enforces PEP 8 naming conventions for Python code before files are written.

This hook validates:
- Class names (PascalCase)
- Function/method names (snake_case)
- Variable names (snake_case)
- Constant names (UPPER_CASE)
- No camelCase or forbidden patterns
- No builtin shadowing

Usage:
    Automatically invoked by Claude Code PreToolUse hook system

Exit codes:
    0: Success (JSON output controls permission)
"""

import ast
import re
from pathlib import Path
from typing import Literal

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision, get_file_path
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision, get_file_path
    from utils.data_types import ToolInput


# ==================== Main Entry Point ====================

def main() -> None:
    """Main entry point for PEP 8 naming enforcement hook."""
    # Parse hook input
    parsed = parse_hook_input()
    if not parsed:
        return  # Error already handled

    tool_name, tool_input = parsed

    # Only validate Write/Edit tools for Python files
    if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        output_decision("allow", "Not a file write/edit tool")
        return

    # Get file path and check if Python file
    file_path = get_file_path(tool_input)
    if not file_path:
        output_decision("allow", "No file path provided")
        return

    # Check file exclusions
    if should_skip_file(file_path):
        output_decision("allow", f"File excluded from validation: {file_path}")
        return

    # Only validate Python files
    if not is_python_file(file_path) and not is_jupyter_notebook(file_path):
        output_decision("allow", "Not a Python file")
        return

    # Extract code content based on tool type
    code_content = extract_code_content(tool_name, tool_input)
    if not code_content:
        output_decision("allow", "No code content to validate")
        return

    # Validate Python code
    violations = validate_python_code(code_content, file_path)

    if violations:
        # Deny with detailed violation report
        output_decision("deny", violations, suppress_output=False)
    else:
        # Allow operation
        output_decision("allow", "PEP 8 naming conventions followed")


# ==================== Validation Logic ====================

def validate_python_code(code: str, file_path: str) -> str | None:
    """
    Validate Python code against PEP 8 naming conventions.

    Args:
        code: Python source code to validate
        file_path: Path to the file (for error messages)

    Returns:
        Formatted violation message if violations found, None otherwise
    """
    # Parse code into AST
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as e:
        # Allow files with syntax errors (not our concern)
        return None

    # Collect violations
    report = ViolationReport()
    validator = PEP8NameValidator(report)
    validator.visit(tree)

    # Format and return violations
    if report.violations:
        return report.format_message(file_path)

    return None


# ==================== AST Visitor ====================

class PEP8NameValidator(ast.NodeVisitor):
    """AST visitor to validate PEP 8 naming conventions."""

    def __init__(self, report: 'ViolationReport'):
        self.report = report
        self.scope_stack: list[str] = []  # Track if we're in class/function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Validate class name."""
        violation = validate_class_name(node.name, node.lineno)
        if violation:
            self.report.add_violation_from_message(violation, "Class")

        # Enter class scope
        self.scope_stack.append('class')
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Validate function/method name."""
        # Check if it's a special method or override
        if not is_magic_method(node.name) and not is_override_method(node.name):
            violation = validate_function_name(node.name, node.lineno)
            if violation:
                self.report.add_violation_from_message(violation, "Function")

        # Validate parameters
        for arg in node.args.args:
            if arg.arg != 'self' and arg.arg != 'cls':
                violation = validate_parameter_name(arg.arg, arg.lineno)
                if violation:
                    self.report.add_violation_from_message(violation, "Parameter")

        # Enter function scope
        self.scope_stack.append('function')
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Validate variable/constant assignment."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._validate_assignment(target.id, node.lineno)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Validate annotated assignment."""
        if isinstance(node.target, ast.Name):
            self._validate_assignment(node.target.id, node.lineno)

        self.generic_visit(node)

    def _validate_assignment(self, name: str, lineno: int) -> None:
        """Validate assignment based on context."""
        # Check if module-level (constant) or local (variable)
        is_module_level = len(self.scope_stack) == 0
        is_all_caps = name.isupper() and '_' not in name or re.match(r'^[A-Z_]+$', name)

        if is_module_level and is_all_caps:
            # Module-level constant
            violation = validate_constant_name(name, lineno)
            if violation:
                self.report.add_violation_from_message(violation, "Constant")
        else:
            # Variable
            violation = validate_variable_name(name, lineno)
            if violation:
                self.report.add_violation_from_message(violation, "Variable")

        # Check forbidden patterns
        violation = check_forbidden_patterns(name, lineno)
        if violation:
            self.report.add_violation_from_message(violation, "Name")


# ==================== Violation Report ====================

class ViolationReport:
    """Collects and formats PEP 8 naming violations."""

    def __init__(self):
        self.violations: list[dict] = []

    def add_violation_from_message(self, message: str, violation_type: str) -> None:
        """Parse violation message and add to report."""
        self.violations.append({
            'type': violation_type,
            'message': message
        })

    def format_message(self, file_path: str) -> str:
        """Format violations as user-friendly message."""
        if not self.violations:
            return ""

        lines = [
            "🚫 PEP 8 Naming Convention Violations Detected\n\n",
            f"File: {file_path}\n\n",
            f"Found {len(self.violations)} violation(s):\n\n"
        ]

        for i, violation in enumerate(self.violations, 1):
            lines.append(f"  {i}. {violation['message']}\n")

        lines.append("\nPEP 8 Reference: https://pep8.org/#naming-conventions\n")

        return "".join(lines)


# ==================== Validation Functions ====================

def validate_class_name(name: str, lineno: int) -> str | None:
    """Validate class name follows PascalCase."""
    # [Implementation as specified above]
    pass


def validate_function_name(name: str, lineno: int) -> str | None:
    """Validate function/method name follows snake_case."""
    # [Implementation as specified above]
    pass


def validate_constant_name(name: str, lineno: int) -> str | None:
    """Validate constant name follows UPPER_CASE."""
    # [Implementation as specified above]
    pass


def validate_variable_name(name: str, lineno: int) -> str | None:
    """Validate variable name follows snake_case."""
    # [Implementation as specified above]
    pass


def validate_parameter_name(name: str, lineno: int) -> str | None:
    """Validate parameter name follows snake_case."""
    # Same as validate_variable_name
    return validate_variable_name(name, lineno)


def check_forbidden_patterns(name: str, lineno: int) -> str | None:
    """Check for forbidden naming patterns."""
    # [Implementation as specified above]
    pass


# ==================== Helper Functions ====================

def is_python_file(file_path: str) -> bool:
    """Check if file is a Python source file."""
    return Path(file_path).suffix in {'.py', '.pyw'}


def is_jupyter_notebook(file_path: str) -> bool:
    """Check if file is a Jupyter notebook."""
    return Path(file_path).suffix == '.ipynb'


def should_skip_file(file_path: str) -> bool:
    """Check if file should be excluded from validation."""
    # [Implementation as specified above]
    pass


def extract_code_content(tool_name: str, tool_input: ToolInput) -> str | None:
    """Extract code content based on tool type."""
    if tool_name == "Write":
        return tool_input.get("content", "")

    elif tool_name == "Edit":
        # For Edit, validate the new_string
        return tool_input.get("new_string", "")

    elif tool_name == "NotebookEdit":
        # Only validate code cells
        cell_type = tool_input.get("cell_type", "")
        if cell_type == "code":
            return tool_input.get("new_source", "")

    return None


def is_magic_method(name: str) -> bool:
    """Check if method is a Python magic method."""
    return name.startswith('__') and name.endswith('__')


def is_override_method(name: str) -> bool:
    """Check if method name is a known override."""
    OVERRIDE_METHODS = {
        'setUp', 'tearDown', 'setUpClass', 'tearDownClass',
        'runTest', 'toString', 'toJSON'
    }
    return name in OVERRIDE_METHODS


def to_snake_case(name: str) -> str:
    """Convert name to snake_case."""
    # [Implementation as specified above]
    pass


def to_pascal_case(name: str) -> str:
    """Convert name to PascalCase."""
    # [Implementation as specified above]
    pass


def to_upper_case(name: str) -> str:
    """Convert name to UPPER_CASE."""
    # [Implementation as specified above]
    pass


if __name__ == "__main__":
    main()
```

## 9. Dependencies

### Python Version
- **Requires:** Python 3.12+
- **Rationale:** Uses modern type hints (`str | None` union syntax)

### Standard Library Packages
- `ast` - Abstract Syntax Tree parsing and analysis
- `re` - Regular expression pattern matching
- `pathlib` - Path manipulation
- `json` - Input/output serialization (via shared utils)
- `sys` - stdin/stdout/exit (via shared utils)
- `typing` - Type hints (Literal, etc.)

### External Packages
- **None** - Only uses Python standard library

### Shared Utilities
```python
from .utils.utils import parse_hook_input, output_decision, get_file_path
from .utils.data_types import ToolInput
```

**Benefits:**
- Consistent input parsing
- Standardized JSON output format
- Reduced code duplication
- Centralized bug fixes

## 10. Testing Strategy

### Test File Location
```
.claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py
```

### Test Categories

#### 1. Unit Tests - Class Name Validation
```python
def test_valid_class_names():
    """Test valid PascalCase class names."""
    assert validate_class_name("MyClass", 1) is None
    assert validate_class_name("DatabaseConnection", 1) is None
    assert validate_class_name("HTTPServer", 1) is None
    assert validate_class_name("_PrivateClass", 1) is None
    assert validate_class_name("__MagicClass__", 1) is None


def test_invalid_class_names():
    """Test invalid class names."""
    assert validate_class_name("myClass", 1) is not None
    assert validate_class_name("my_class", 1) is not None
    assert validate_class_name("MYCLASS", 1) is not None
    assert validate_class_name("myclass", 1) is not None
```

#### 2. Unit Tests - Function Name Validation
```python
def test_valid_function_names():
    """Test valid snake_case function names."""
    assert validate_function_name("my_function", 1) is None
    assert validate_function_name("calculate_total", 1) is None
    assert validate_function_name("_private_method", 1) is None
    assert validate_function_name("__init__", 1) is None
    assert validate_function_name("__str__", 1) is None


def test_invalid_function_names():
    """Test invalid function names."""
    assert validate_function_name("myFunction", 1) is not None
    assert validate_function_name("MyFunction", 1) is not None
    assert validate_function_name("MYFUNCTION", 1) is not None
    assert validate_function_name("my__function", 1) is not None
```

#### 3. Unit Tests - Constant Name Validation
```python
def test_valid_constant_names():
    """Test valid UPPER_CASE constant names."""
    assert validate_constant_name("MAX_SIZE", 1) is None
    assert validate_constant_name("DEFAULT_TIMEOUT", 1) is None
    assert validate_constant_name("API_KEY", 1) is None
    assert validate_constant_name("_PRIVATE_CONSTANT", 1) is None


def test_invalid_constant_names():
    """Test invalid constant names."""
    assert validate_constant_name("maxSize", 1) is not None
    assert validate_constant_name("max_size", 1) is not None
    assert validate_constant_name("MaxSize", 1) is not None
```

#### 4. Unit Tests - Variable Name Validation
```python
def test_valid_variable_names():
    """Test valid snake_case variable names."""
    assert validate_variable_name("my_var", 1) is None
    assert validate_variable_name("total_count", 1) is None
    assert validate_variable_name("i", 1) is None  # Loop counter
    assert validate_variable_name("e", 1) is None  # Exception
    assert validate_variable_name("_private_var", 1) is None


def test_invalid_variable_names():
    """Test invalid variable names."""
    assert validate_variable_name("myVar", 1) is not None
    assert validate_variable_name("MyVar", 1) is not None
    assert validate_variable_name("MYVAR", 1) is not None
```

#### 5. Unit Tests - Forbidden Patterns
```python
def test_confusing_names():
    """Test confusing single character names."""
    assert check_forbidden_patterns("l", 1) is not None
    assert check_forbidden_patterns("O", 1) is not None
    assert check_forbidden_patterns("I", 1) is not None


def test_builtin_shadowing():
    """Test detection of builtin shadowing."""
    assert check_forbidden_patterns("list", 1) is not None
    assert check_forbidden_patterns("dict", 1) is not None
    assert check_forbidden_patterns("str", 1) is not None
    assert check_forbidden_patterns("print", 1) is not None


def test_camelCase_detection():
    """Test detection of camelCase."""
    assert check_forbidden_patterns("myVariable", 1) is not None
    assert check_forbidden_patterns("getValue", 1) is not None
```

#### 6. Integration Tests - Full AST Validation
```python
def test_validate_compliant_code():
    """Test validation of PEP 8 compliant code."""
    code = '''
class MyClass:
    """Example class."""

    MAX_SIZE = 100

    def __init__(self):
        self.my_variable = 0

    def calculate_total(self, items):
        total = 0
        for i in items:
            total += i
        return total
'''
    violations = validate_python_code(code, "test.py")
    assert violations is None


def test_validate_non_compliant_code():
    """Test validation detects violations."""
    code = '''
class myClass:
    def MyMethod(self):
        myVariable = 10
        return myVariable
'''
    violations = validate_python_code(code, "test.py")
    assert violations is not None
    assert "myClass" in violations
    assert "MyMethod" in violations
    assert "myVariable" in violations
```

#### 7. Integration Tests - Full Hook Execution
```python
def test_hook_denies_violations():
    """Test hook denies file write with PEP 8 violations."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/project/module.py",
            "content": "class myClass:\n    pass"
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = json.loads(mock_stdout.getvalue())
            assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
            assert "myClass" in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_hook_allows_compliant_code():
    """Test hook allows compliant Python code."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/project/module.py",
            "content": "class MyClass:\n    pass"
        }
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
uv run pytest .claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py -v

# Run with coverage
uv run pytest .claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py --cov=.claude/hooks/pre_tools --cov-report=html

# Run specific test category
uv run pytest .claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py::test_valid_class_names -v
```

## 11. Security Considerations

### Input Validation
- **Code Injection**: Only parse code with `ast.parse()`, never use `eval()` or `exec()`
- **Path Traversal**: Validate file paths, check for `../` patterns
- **Malicious Code**: AST parsing is safe, doesn't execute code
- **Large Files**: Limit AST parsing to reasonable file sizes (< 1MB)

### Safe Failure Modes
- **Syntax Errors**: Allow files with syntax errors (not our concern)
- **Parse Errors**: Fail open (allow) if AST parsing fails unexpectedly
- **Invalid Input**: Allow operation with debug logging
- **Missing Fields**: Allow operation if required fields missing

### Defense in Depth
```python
def validate_python_code(code: str, file_path: str) -> str | None:
    """Validate with comprehensive error handling."""
    try:
        # Limit file size
        if len(code) > 1_000_000:  # 1MB limit
            return None  # Allow large files

        # Parse code (safe, doesn't execute)
        tree = ast.parse(code, filename=file_path)

        # Validate
        report = ViolationReport()
        validator = PEP8NameValidator(report)
        validator.visit(tree)

        if report.violations:
            return report.format_message(file_path)

        return None

    except SyntaxError:
        # Allow files with syntax errors
        return None

    except Exception as e:
        # Unexpected error - fail open
        print(f"Validation error: {e}", file=sys.stderr)
        return None
```

## 12. Error Handling

### Graceful Degradation
```python
def main() -> None:
    """Main entry point with comprehensive error handling."""
    try:
        # Parse input
        parsed = parse_hook_input()
        if not parsed:
            output_decision("allow", "Invalid input format")
            return

        tool_name, tool_input = parsed

        # Validate tool type
        if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            output_decision("allow", "Not a file write/edit tool")
            return

        # Extract and validate code
        file_path = get_file_path(tool_input)
        if not file_path:
            output_decision("allow", "No file path provided")
            return

        # ... validation logic ...

    except Exception as e:
        # Unexpected error - fail open to avoid blocking workflows
        output_decision("allow", f"Hook error (allowing operation): {str(e)}")
```

### Edge Cases
1. **Empty file**: Allow (no code to validate)
2. **Syntax errors**: Allow (let Python interpreter handle it)
3. **Non-Python files**: Skip validation
4. **Generated files**: Skip via exclusion patterns
5. **Test files**: Allow special naming conventions
6. **Notebooks**: Only validate code cells

## 13. Performance Considerations

### Optimization Strategies
- **Early Exit**: Return immediately for non-Python files
- **File Size Limit**: Skip validation for very large files (> 1MB)
- **AST Caching**: Consider caching AST for repeated validations (future)
- **Minimal I/O**: All validation in-memory, no disk operations

### Expected Performance
- **Small files (< 10KB)**: < 50ms
- **Medium files (10-100KB)**: < 200ms
- **Large files (100KB-1MB)**: < 1s
- **Memory Usage**: < 10MB per validation

### Performance Measurement
```python
import time

def validate_python_code(code: str, file_path: str) -> str | None:
    """Validate with performance tracking."""
    start_time = time.time()

    # ... validation logic ...

    elapsed = (time.time() - start_time) * 1000
    if elapsed > 500:
        print(f"Slow validation: {elapsed:.2f}ms for {file_path}", file=sys.stderr)

    return result
```

## 14. Integration Considerations

### Coexistence with Other Hooks
This hook will run alongside existing PreToolUse hooks:
- `universal_hook_logger.py` - Logging (no conflicts)
- `sensitive_file_access_validator.py` - Security (complementary)
- `uv_workflow_enforcer.py` - UV workflow (no overlap)
- `tmp_creation_blocker.py` - Temp file blocking (no overlap)

**Execution Order**: Hooks run in **parallel**, so order doesn't matter.

### Configuration Merge Strategy
Add new hook entry to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/pep8_naming_enforcer.py"
          }
        ]
      }
    ]
  }
}
```

### Environment Variables
- `CLAUDE_PROJECT_DIR` - Project root directory (for path resolution)

## 15. Rollback Strategy

### Disabling the Hook
**Temporary Disable:**
```json
// In .claude/settings.local.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": []
      }
    ]
  }
}
```

**Permanent Removal:**
1. Remove hook entry from `.claude/settings.json`
2. Delete: `.claude/hooks/pre_tools/pep8_naming_enforcer.py`
3. Delete: `.claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py`

### Monitoring During Rollout
1. Review blocked operations in session transcript
2. Check for false positives
3. Monitor performance impact
4. Gather user feedback

## 16. Future Enhancements

### Potential Improvements
1. **Configurable Rules**
   - Allow users to enable/disable specific rules
   - Custom naming conventions per project

2. **Auto-Fix Mode**
   - Automatically rename identifiers (with confirmation)
   - Generate refactoring suggestions

3. **Severity Levels**
   - Warning vs Error violations
   - Allow warnings but block errors

4. **Integration with Linters**
   - Parse `.flake8`, `pyproject.toml` configuration
   - Respect existing linter rules

5. **IDE Integration**
   - Export violations in LSP format
   - Real-time feedback in editor

### Configuration Schema (Future)
```json
{
  "hooks": {
    "pep8_naming_enforcer": {
      "enabled": true,
      "rules": {
        "class_names": "PascalCase",
        "function_names": "snake_case",
        "allow_camelCase_overrides": true
      },
      "exclude_patterns": ["test_*.py"],
      "severity": "error"
    }
  }
}
```

## 17. Documentation and Communication

### User-Facing Documentation
Add to `.claude/hooks/pre_tools/README.md`:

```markdown
### pep8_naming_enforcer.py

**Purpose:** Enforces PEP 8 naming conventions for Python code.

**Rules Enforced:**
- Class names: PascalCase
- Function/method names: snake_case
- Variable names: snake_case
- Constants: UPPER_CASE
- No camelCase or forbidden patterns

**Example Violations:**
```python
# ❌ Violations
class myClass:  # Should be MyClass
    def MyMethod(self):  # Should be my_method
        myVariable = 10  # Should be my_variable

# ✅ Compliant
class MyClass:
    def my_method(self):
        my_variable = 10
```

**How to Disable:** Comment out in `.claude/settings.json` or use `.claude/settings.local.json` override.
```

## 18. Success Criteria

### Functional Requirements
- ✅ Validate class names (PascalCase)
- ✅ Validate function names (snake_case)
- ✅ Validate variable names (snake_case)
- ✅ Validate constant names (UPPER_CASE)
- ✅ Detect camelCase and forbidden patterns
- ✅ Detect builtin shadowing
- ✅ Handle Write, Edit, and NotebookEdit tools
- ✅ Provide actionable suggestions

### Non-Functional Requirements
- ✅ Execution time < 500ms for typical files
- ✅ Zero false negatives (all violations detected)
- ✅ Minimal false positives (< 2% legitimate code blocked)
- ✅ Clear, actionable error messages
- ✅ 90%+ test coverage
- ✅ No external dependencies

### User Experience
- ✅ Clear explanation of violations
- ✅ Actionable renaming suggestions
- ✅ PEP 8 reference link provided
- ✅ No disruption to compliant workflows

## 19. Implementation Checklist

### Phase 1: Core Development
- [ ] Create `pep8_naming_enforcer.py` with UV script metadata
- [ ] Implement `main()` function with error handling
- [ ] Implement `validate_python_code()` with AST parsing
- [ ] Implement `PEP8NameValidator` AST visitor class
- [ ] Implement validation functions (class, function, variable, constant)
- [ ] Implement `check_forbidden_patterns()` for builtin shadowing
- [ ] Implement `ViolationReport` class for formatting
- [ ] Implement helper functions (name conversion, file detection)
- [ ] Add comprehensive docstrings and type hints

### Phase 2: Testing
- [ ] Create `test_pep8_naming_enforcer.py` in tests directory
- [ ] Write unit tests for class name validation (10+ cases)
- [ ] Write unit tests for function name validation (10+ cases)
- [ ] Write unit tests for variable name validation (10+ cases)
- [ ] Write unit tests for constant name validation (10+ cases)
- [ ] Write unit tests for forbidden patterns (10+ cases)
- [ ] Write integration tests for AST validation (5+ cases)
- [ ] Write integration tests for full hook execution (5+ cases)
- [ ] Run tests and verify 100% pass rate
- [ ] Verify test coverage > 90%

### Phase 3: Integration
- [ ] Update `.claude/settings.json` with hook configuration
- [ ] Test hook with real Claude Code session
- [ ] Verify coexistence with other PreToolUse hooks
- [ ] Test on various Python file types (.py, .pyw, .ipynb)
- [ ] Performance benchmarking

### Phase 4: Documentation
- [ ] Add section to `.claude/hooks/pre_tools/README.md`
- [ ] Create usage examples
- [ ] Document exclusion patterns
- [ ] Update this spec with lessons learned

### Phase 5: Validation
- [ ] Manual testing with compliant code
- [ ] Manual testing with non-compliant code
- [ ] Security review (code injection, AST safety)
- [ ] User acceptance testing
- [ ] Final adjustments based on feedback

## 20. Appendix

### Example Scenarios

#### Scenario 1: Non-Compliant Class Name
**Input:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/models.py",
    "content": "class userModel:\n    pass"
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 PEP 8 Naming Convention Violations Detected\n\nFile: /project/models.py\n\nFound 1 violation(s):\n\n  1. Class 'userModel' violates PEP 8\n     - Rule: Class names should use PascalCase\n     - Suggestion: Rename to 'UserModel'\n     - Line: 1\n\nPEP 8 Reference: https://pep8.org/#naming-conventions\n"
  },
  "suppressOutput": false
}
```

#### Scenario 2: Multiple Violations
**Input:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/utils.py",
    "content": "def CalculateTotal():\n    myVariable = 10\n    return myVariable"
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 PEP 8 Naming Convention Violations Detected\n\nFile: /project/utils.py\n\nFound 2 violation(s):\n\n  1. Function 'CalculateTotal' violates PEP 8\n     - Rule: Function names should use snake_case\n     - Suggestion: Rename to 'calculate_total'\n     - Line: 1\n\n  2. Variable 'myVariable' violates PEP 8\n     - Rule: Variable names should use snake_case (no camelCase)\n     - Suggestion: Rename to 'my_variable'\n     - Line: 2\n\nPEP 8 Reference: https://pep8.org/#naming-conventions\n"
  },
  "suppressOutput": false
}
```

#### Scenario 3: Compliant Code
**Input:**
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/models.py",
    "content": "class UserModel:\n    MAX_SIZE = 100\n\n    def __init__(self):\n        self.total_count = 0\n\n    def calculate_total(self, items):\n        return sum(items)"
  }
}
```

**Output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "PEP 8 naming conventions followed"
  },
  "suppressOutput": false
}
```

### PEP 8 Quick Reference

| Identifier Type | Convention | Example |
|----------------|------------|---------|
| Class | PascalCase | `MyClass`, `UserModel` |
| Function | snake_case | `my_function`, `calculate_total` |
| Method | snake_case | `get_value`, `process_data` |
| Variable | snake_case | `my_variable`, `total_count` |
| Constant | UPPER_CASE | `MAX_SIZE`, `DEFAULT_TIMEOUT` |
| Private | _leading | `_private_method`, `_internal_var` |
| Magic | __double__ | `__init__`, `__str__` |
| Module | snake_case | `my_module.py` |

### References
- **PEP 8**: https://pep8.org/#naming-conventions
- **Claude Code Hooks Documentation**: `ai_docs/claude-code-hooks.md`
- **UV Scripts Guide**: `ai_docs/uv-scripts-guide.md`
- **Python AST Documentation**: https://docs.python.org/3/library/ast.html
- **Existing Hook Implementation**: `.claude/hooks/pre_tools/sensitive_file_access_validator.py`
- **Shared Utilities**: `.claude/hooks/pre_tools/utils/`

---

**Specification Version**: 1.0
**Created**: 2025-10-26
**Author**: Claude Code Hook Expert
**Status**: Ready for Implementation
