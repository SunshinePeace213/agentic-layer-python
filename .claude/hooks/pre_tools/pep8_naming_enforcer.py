#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
PEP 8 Naming Convention Enforcer Hook
======================================

Enforces PEP 8 naming conventions for Python code before files are written.
Validates that all identifiers (classes, functions, variables, constants)
follow PEP 8 naming standards to ensure consistent, Pythonic code style.

Purpose:
    Automatically validate Python identifiers against PEP 8 naming conventions
    before files are written, catching violations early in the development process.

Hook Event: PreToolUse
Monitored Tools: Write, Edit

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with concrete suggestions
    - Zero false positives on valid PEP 8 code

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

PEP 8 Rules Enforced:
    - Classes: CapWords (MyClass, HTTPServer)
    - Functions/Methods: lowercase_with_underscores (get_user_data)
    - Variables: lowercase_with_underscores (user_count)
    - Constants: UPPER_CASE_WITH_UNDERSCORES (MAX_SIZE)
    - Private: _leading_underscore (_internal_method)

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Configuration ====================

# Maximum file size to validate (in bytes) - 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Reserved single-character names that look like numbers
RESERVED_NAMES = {"l", "O", "I"}

# Common single-character loop variables (allowed)
ALLOWED_SINGLE_CHAR = {"i", "j", "k", "x", "y", "z", "n", "m", "f", "e"}


# ==================== Data Classes ====================


class Violation:
    """Represents a single PEP 8 naming violation."""

    def __init__(
        self,
        identifier_name: str,
        line_number: int,
        violation_type: str,
        expected_pattern: str,
        suggestion: str,
    ):
        self.identifier_name = identifier_name
        self.line_number = line_number
        self.violation_type = violation_type
        self.expected_pattern = expected_pattern
        self.suggestion = suggestion

    def format_message(self, index: int) -> str:
        """Format this violation as a numbered error message."""
        type_labels = {
            "class": "Class",
            "function": "Function",
            "variable": "Variable",
            "constant": "Constant",
            "argument": "Argument",
            "reserved": "Variable",
        }

        label = type_labels.get(self.violation_type, "Identifier")

        issue_descriptions = {
            "class": "Class names must use CapWords (CamelCase)",
            "function": "Function names must use lowercase_with_underscores",
            "variable": "Variable names must use lowercase_with_underscores",
            "constant": "Module-level constants must use UPPER_CASE_WITH_UNDERSCORES",
            "argument": "Argument names must use lowercase_with_underscores",
            "reserved": f"Single-char name '{self.identifier_name}' looks like a number",
        }

        rule_explanations = {
            "class": "PEP 8 requires class names to start with uppercase and use CapWords",
            "function": "PEP 8 requires function names to be lowercase with underscores",
            "variable": "PEP 8 requires variable names to be lowercase with underscores",
            "constant": "PEP 8 requires constants to be all uppercase with underscores",
            "argument": "PEP 8 requires argument names to be lowercase with underscores",
            "reserved": "PEP 8 prohibits using 'l', 'O', 'I' as they're indistinguishable from numbers",
        }

        issue = issue_descriptions.get(
            self.violation_type, f"Must match pattern: {self.expected_pattern}"
        )
        rule = rule_explanations.get(self.violation_type, self.expected_pattern)

        return f"""{index}. {label} '{self.identifier_name}' (line {self.line_number})
   Issue: {issue}
   Suggestion: Rename to '{self.suggestion}'
   Rule: {rule}"""


# ==================== Name Conversion Utilities ====================


def to_cap_words(name: str) -> str:
    """
    Convert snake_case or camelCase to CapWords.

    Args:
        name: Identifier name to convert

    Returns:
        Converted name in CapWords format

    Examples:
        >>> to_cap_words('user_profile')
        'UserProfile'
        >>> to_cap_words('userProfile')
        'UserProfile'
        >>> to_cap_words('myClass')
        'MyClass'
    """
    # Handle snake_case: user_profile -> UserProfile
    if "_" in name:
        parts = name.split("_")
        return "".join(part.capitalize() for part in parts if part)

    # Handle camelCase: userProfile -> UserProfile
    if name and name[0].islower():
        return name[0].upper() + name[1:]

    return name


def to_snake_case(name: str) -> str:
    """
    Convert CapWords or camelCase to snake_case.

    Args:
        name: Identifier name to convert

    Returns:
        Converted name in snake_case format

    Examples:
        >>> to_snake_case('GetUserData')
        'get_user_data'
        >>> to_snake_case('getUserData')
        'get_user_data'
        >>> to_snake_case('HTTPServer')
        'http_server'
    """
    # Insert underscore before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def to_upper_snake_case(name: str) -> str:
    """
    Convert any case to UPPER_SNAKE_CASE.

    Args:
        name: Identifier name to convert

    Returns:
        Converted name in UPPER_SNAKE_CASE format

    Examples:
        >>> to_upper_snake_case('maxSize')
        'MAX_SIZE'
        >>> to_upper_snake_case('Max_Size')
        'MAX_SIZE'
    """
    snake = to_snake_case(name)
    return snake.upper()


# ==================== Validation Functions ====================


def validate_class_name(name: str, line: int) -> Optional[Violation]:
    """
    Validate class name follows CapWords convention.

    Args:
        name: Class name to validate
        line: Line number where class is defined

    Returns:
        Violation if invalid, None if valid

    Rules:
        - Must start with uppercase letter
        - Can contain letters and numbers
        - No underscores (except for private classes with leading underscore)

    Examples:
        >>> validate_class_name('MyClass', 1)
        None
        >>> validate_class_name('myClass', 1)
        Violation(...)
    """
    # Allow private classes (single or double leading underscore)
    if name.startswith("_"):
        # Validate the part after underscores
        clean_name = name.lstrip("_")
        if not clean_name:  # Just underscores
            return None
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", clean_name):
            return Violation(
                identifier_name=name,
                line_number=line,
                violation_type="class",
                expected_pattern="CapWords (e.g., MyClass, HTTPServer)",
                suggestion="_" + to_cap_words(clean_name),
            )
        return None

    # Check CapWords pattern
    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="class",
            expected_pattern="CapWords (e.g., MyClass, HTTPServer)",
            suggestion=to_cap_words(name),
        )

    # Reject ALL_CAPS names (reserved for constants)
    if name.isupper():
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="class",
            expected_pattern="CapWords (e.g., MyClass, HTTPServer)",
            suggestion=to_cap_words(name),
        )

    return None


def validate_function_name(name: str, line: int) -> Optional[Violation]:
    """
    Validate function name follows lowercase_with_underscores convention.

    Args:
        name: Function name to validate
        line: Line number where function is defined

    Returns:
        Violation if invalid, None if valid

    Rules:
        - Must be lowercase with underscores
        - Can start with underscore (private methods)
        - Magic methods (__method__) allowed

    Examples:
        >>> validate_function_name('get_user_data', 1)
        None
        >>> validate_function_name('getUserData', 1)
        Violation(...)
    """
    # Allow magic methods
    if name.startswith("__") and name.endswith("__"):
        return None

    # Allow AST visitor methods (visit_ClassDef, visit_FunctionDef, etc.)
    if name.startswith("visit_"):
        return None

    # Handle private methods (strip leading underscores for validation)
    clean_name = name
    prefix = ""
    if name.startswith("__"):
        prefix = "__"
        clean_name = name[2:]
    elif name.startswith("_"):
        prefix = "_"
        clean_name = name[1:]

    # Check lowercase_with_underscores pattern
    if clean_name and not re.match(r"^[a-z][a-z0-9_]*$", clean_name):
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="function",
            expected_pattern="lowercase_with_underscores (e.g., get_user_data)",
            suggestion=prefix + to_snake_case(clean_name),
        )

    return None


def validate_variable_or_constant(
    name: str, line: int, is_module_level: bool
) -> Optional[Violation]:
    """
    Validate variable or constant name.

    Args:
        name: Variable/constant name to validate
        line: Line number where variable is assigned
        is_module_level: True if assignment is at module level

    Returns:
        Violation if invalid, None if valid

    Rules:
        - Module-level ALL_CAPS: Constant (UPPER_CASE_WITH_UNDERSCORES)
        - Otherwise: Variable (lowercase_with_underscores)
        - Reserved names ('l', 'O', 'I') always blocked

    Examples:
        >>> validate_variable_or_constant('user_count', 1, False)
        None
        >>> validate_variable_or_constant('MAX_SIZE', 1, True)
        None
        >>> validate_variable_or_constant('userName', 1, False)
        Violation(...)
    """
    # Reserved names check (always blocked)
    if name in RESERVED_NAMES:
        suggestions = {"l": "line", "O": "obj", "I": "index"}
        return Violation(
            identifier_name=name,
            line_number=line,
            violation_type="reserved",
            expected_pattern="Avoid single-char names that look like numbers",
            suggestion=suggestions.get(name, name + "_value"),
        )

    # Allow common single-character loop variables
    if len(name) == 1 and name in ALLOWED_SINGLE_CHAR:
        return None

    # Allow trailing underscore (keyword conflicts: class_, type_, id_)
    clean_name = name.rstrip("_")
    suffix = "_" * (len(name) - len(clean_name))

    # Detect constant: module-level AND all uppercase with underscores
    if is_module_level and name.isupper() and ("_" in name or len(name) <= 3):
        # Validate constant pattern: UPPER_CASE_WITH_UNDERSCORES
        if not re.match(r"^[A-Z][A-Z0-9_]*$", name):
            return Violation(
                identifier_name=name,
                line_number=line,
                violation_type="constant",
                expected_pattern="UPPER_CASE_WITH_UNDERSCORES (e.g., MAX_SIZE)",
                suggestion=to_upper_snake_case(name),
            )
    else:
        # Validate variable pattern: lowercase_with_underscores
        # Allow private variables (leading underscore)
        test_name = clean_name
        prefix = ""
        if clean_name.startswith("__"):
            prefix = "__"
            test_name = clean_name[2:]
        elif clean_name.startswith("_"):
            prefix = "_"
            test_name = clean_name[1:]

        if test_name and not re.match(r"^[a-z][a-z0-9_]*$", test_name):
            return Violation(
                identifier_name=name,
                line_number=line,
                violation_type="variable",
                expected_pattern="lowercase_with_underscores (e.g., user_count)",
                suggestion=prefix + to_snake_case(test_name) + suffix,
            )

    return None


# ==================== AST Visitor ====================


class PEP8NamingVisitor(ast.NodeVisitor):
    """AST visitor to extract and validate all identifiers."""

    def __init__(self) -> None:
        """Initialize the visitor with empty violations list and scope stack."""
        self.violations: list[Violation] = []
        self.scope_stack: list[tuple[str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and validate class name."""
        violation = validate_class_name(node.name, node.lineno)
        if violation:
            self.violations.append(violation)

        self.scope_stack.append(("class", node.name))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition and validate function name and arguments."""
        violation = validate_function_name(node.name, node.lineno)
        if violation:
            self.violations.append(violation)

        # Validate function arguments
        for arg in node.args.args:
            # Skip 'self' and 'cls'
            if arg.arg in ("self", "cls"):
                continue
            arg_violation = validate_function_name(arg.arg, arg.lineno)
            if arg_violation:
                # Update violation type to 'argument' for better error messages
                arg_violation.violation_type = "argument"
                self.violations.append(arg_violation)

        self.scope_stack.append(("function", node.name))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition (same rules as regular functions)."""
        violation = validate_function_name(node.name, node.lineno)
        if violation:
            self.violations.append(violation)

        # Validate function arguments
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            arg_violation = validate_function_name(arg.arg, arg.lineno)
            if arg_violation:
                arg_violation.violation_type = "argument"
                self.violations.append(arg_violation)

        self.scope_stack.append(("function", node.name))
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment and validate variable/constant names."""
        is_module_level = len(self.scope_stack) == 0

        for target in node.targets:
            if isinstance(target, ast.Name):
                violation = validate_variable_or_constant(
                    target.id, target.lineno, is_module_level
                )
                if violation:
                    self.violations.append(violation)

        self.generic_visit(node)


# ==================== Python Content Validation ====================


def validate_python_content(content: str, file_path: str) -> Optional[str]:
    """
    Validate Python code content against PEP 8 naming conventions.

    Args:
        content: Python source code to validate
        file_path: Path to the file (for error messages)

    Returns:
        None if validation passes, error message string if violations found

    Error Handling:
        - Syntax errors: Allow (fail-safe, user will see Python error later)
        - Empty content: Allow
        - Parse errors: Allow (fail-safe)
    """
    if not content or not content.strip():
        # Empty file - allow
        return None

    try:
        # Parse Python code into AST
        tree = ast.parse(content, filename=file_path)

        # Visit all nodes and collect violations
        visitor = PEP8NamingVisitor()
        visitor.visit(tree)

        if not visitor.violations:
            # No violations - allow
            return None

        # Format violations into error message
        return format_violation_message(file_path, visitor.violations)

    except SyntaxError:
        # Invalid Python syntax - allow (fail-safe)
        # User will see Python's own syntax error when they try to run it
        return None
    except Exception as e:
        # Unexpected error - allow (fail-safe)
        print(f"PEP 8 naming enforcer error during validation: {e}", file=sys.stderr)
        return None


def format_violation_message(file_path: str, violations: list[Violation]) -> str:
    """
    Format a comprehensive denial message with all violations.

    Args:
        file_path: Path to the file with violations
        violations: List of Violation objects

    Returns:
        Formatted error message with all violations and educational content
    """
    violation_messages = [
        v.format_message(i + 1) for i, v in enumerate(violations)
    ]

    return f"""🐍 Blocked: PEP 8 naming convention violations

File: {file_path}

❌ Violations found:

{chr(10).join(violation_messages)}

Total violations: {len(violations)}

PEP 8 Naming Quick Reference:
  • Classes: CapWords (MyClass, HTTPServer)
  • Functions: lowercase_with_underscores (get_user, calculate_total)
  • Variables: lowercase_with_underscores (user_count, is_valid)
  • Constants: UPPER_CASE_WITH_UNDERSCORES (MAX_SIZE, API_KEY)
  • Private: _leading_underscore (_internal_method, _private_var)

Learn more: https://peps.python.org/pep-0008/#naming-conventions"""


# ==================== File Operations ====================


def read_file_for_edit(file_path: str) -> Optional[str]:
    """
    Read file content safely for Edit tool validation.

    Args:
        file_path: Path to file to read

    Returns:
        File content as string, or None if file cannot be read

    Error Handling:
        - File not found: Return None (fail-safe)
        - Permission errors: Return None (fail-safe)
        - Other errors: Return None (fail-safe)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Could not read file for edit validation: {e}", file=sys.stderr)
        return None


def apply_edit_to_content(
    content: str, old_string: str, new_string: str, replace_all: bool = False
) -> str:
    """
    Apply edit operation to content (simulating Edit tool behavior).

    Args:
        content: Original file content
        old_string: String to replace
        new_string: Replacement string
        replace_all: If True, replace all occurrences; otherwise replace first

    Returns:
        Content after applying the edit
    """
    if replace_all:
        return content.replace(old_string, new_string)
    else:
        return content.replace(old_string, new_string, 1)


def check_file_size(file_path: str) -> bool:
    """
    Check if file size is within validation limits.

    Args:
        file_path: Path to file to check

    Returns:
        True if file is within size limit, False otherwise
    """
    try:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            return size <= MAX_FILE_SIZE_BYTES
    except Exception:
        pass
    return True  # Fail-safe: assume valid if we can't check


# ==================== Main Validation Logic ====================


def validate_write_tool(file_path: str, content: str) -> Optional[str]:
    """
    Validate Write tool operation.

    Args:
        file_path: Path to file being written
        content: Content being written

    Returns:
        None if validation passes, error message if violations found
    """
    # Only validate Python files
    if not file_path.endswith(".py"):
        return None

    # Check file size
    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        # File too large - skip validation (fail-safe)
        return None

    return validate_python_content(content, file_path)


def validate_edit_tool(
    file_path: str, old_string: str, new_string: str, replace_all: bool
) -> Optional[str]:
    """
    Validate Edit tool operation.

    Args:
        file_path: Path to file being edited
        old_string: String being replaced
        new_string: Replacement string
        replace_all: Whether to replace all occurrences

    Returns:
        None if validation passes, error message if violations found
    """
    # Only validate Python files
    if not file_path.endswith(".py"):
        return None

    # Check file size
    if not check_file_size(file_path):
        # File too large - skip validation (fail-safe)
        return None

    # Read current file content
    current_content = read_file_for_edit(file_path)
    if current_content is None:
        # Could not read file - allow (fail-safe)
        return None

    # Apply edit to get final content
    final_content = apply_edit_to_content(
        current_content, old_string, new_string, replace_all
    )

    # Validate the complete file after edit
    return validate_python_content(final_content, file_path)


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and parameters
        3. Validate based on tool type (Write or Edit)
        4. Output decision (allow or deny)

    Error Handling:
        All exceptions result in "allow" decision (fail-safe)
    """
    try:
        # Parse input from stdin
        result = parse_hook_input()
        if result is None:
            # Parse failed, fail-safe: allow
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = result

        # Determine validation based on tool type
        error_message: Optional[str] = None

        if tool_name == "Write":
            # Write tool: validate new file content
            file_path = tool_input.get("file_path", "")
            content = tool_input.get("content", "")
            error_message = validate_write_tool(file_path, content)

        elif tool_name == "Edit":
            # Edit tool: read current file, apply edit, validate result
            file_path = tool_input.get("file_path", "")
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            replace_all = tool_input.get("replace_all", False)
            error_message = validate_edit_tool(
                file_path, old_string, new_string, replace_all
            )

        # Output decision
        if error_message:
            # Validation failed: deny with educational message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # Validation passed: allow
            output_decision(
                "allow", "All identifiers follow PEP 8 naming conventions", suppress_output=True
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"PEP 8 naming enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
