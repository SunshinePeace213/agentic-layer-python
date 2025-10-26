#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
PEP 8 Naming Convention Enforcer - PreToolUse Hook
===================================================
Enforces PEP 8 naming conventions for Python code before files are written.

Usage:
    Automatically invoked by Claude Code PreToolUse hook system
"""

import ast
import re
import sys
from pathlib import Path

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision, get_file_path
except ImportError:
    # Fallback for direct script execution
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from utils import parse_hook_input, output_decision, get_file_path  # type: ignore[import-not-found]


def validate_class_name(name: str, lineno: int) -> str | None:
    """
    Validate class name follows PascalCase convention.

    Returns:
        Violation message if invalid, None otherwise
    """
    # Allow magic classes (e.g., __MagicClass__)
    if name.startswith('__') and name.endswith('__'):
        return None

    # Check if name starts with uppercase and follows PascalCase pattern
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        suggestion = to_pascal_case(name)
        return (
            f"Class name '{name}' violates PEP 8\n"
            f"  - Rule: Class names should use PascalCase\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    return None


def validate_function_name(name: str, lineno: int) -> str | None:
    """
    Validate function/method name follows snake_case convention.

    Returns:
        Violation message if invalid, None otherwise
    """
    # Allow magic methods (e.g., __init__, __str__)
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

    return None


def validate_variable_name(name: str, lineno: int) -> str | None:
    """
    Validate variable name follows snake_case convention.

    Returns:
        Violation message if invalid, None otherwise
    """
    # Detect camelCase (lowercase followed by uppercase)
    if re.search(r'[a-z][A-Z]', name):
        suggestion = to_snake_case(name)
        return (
            f"Variable name '{name}' violates PEP 8\n"
            f"  - Rule: Variable names should use snake_case\n"
            f"  - Suggestion: Rename to '{suggestion}'\n"
            f"  - Line: {lineno}"
        )

    return None


def validate_constant_name(name: str, lineno: int) -> str | None:
    """
    Validate constant name follows UPPER_CASE convention.

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


def check_forbidden_patterns(name: str, lineno: int) -> str | None:
    """
    Check for forbidden naming patterns.

    Returns:
        Violation message if invalid, None otherwise
    """
    # Check if it's the 'list' builtin
    if name == "list":
        return (
            f"Name '{name}' shadows Python builtin\n"
            f"  - Rule: Never shadow built-in names\n"
            f"  - Line: {lineno}"
        )

    return None


def to_upper_case(name: str) -> str:
    """Convert name to UPPER_CASE."""
    # Convert to snake_case first, then upper
    snake = to_snake_case(name)
    return snake.upper()


def to_snake_case(name: str) -> str:
    """Convert name to snake_case."""
    # Handle PascalCase and camelCase
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


class SimpleValidator(ast.NodeVisitor):
    """Minimal AST visitor to find naming violations."""

    def __init__(self):
        self.violations: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        violation = validate_class_name(node.name, node.lineno)
        if violation:
            self.violations.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        violation = validate_function_name(node.name, node.lineno)
        if violation:
            self.violations.append(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                violation = validate_variable_name(target.id, node.lineno)
                if violation:
                    self.violations.append(target.id)
        self.generic_visit(node)


def validate_python_code(code: str, file_path: str) -> str | None:
    """
    Validate Python code against PEP 8 naming conventions.

    Returns:
        Formatted violation message if violations found, None otherwise
    """
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError:
        return None

    validator = SimpleValidator()
    validator.visit(tree)

    if validator.violations:
        return f"Violations detected: {', '.join(validator.violations)}"

    return None


def is_python_file(file_path: str) -> bool:
    """Check if file is a Python source file."""
    return Path(file_path).suffix == '.py'


def main() -> None:
    """Main entry point for PEP 8 naming enforcement hook."""
    # Parse input using shared utility
    result = parse_hook_input()
    if result is None:
        return

    _tool_name, tool_input = result
    file_path = get_file_path(tool_input)

    # Check if it's a Python file
    if not is_python_file(file_path):
        output_decision("allow", "Not a Python file")
        return

    # Validate Python code
    content = tool_input.get("content", "")
    violation_msg = validate_python_code(content, file_path)

    if violation_msg is None:
        # No violations - allow
        output_decision("allow", "PEP 8 naming conventions followed")
    else:
        # Violations found - deny
        output_decision("deny", violation_msg)


def to_pascal_case(name: str) -> str:
    """Convert name to PascalCase."""
    # Split on underscores and capitalize
    words = name.split('_')
    return ''.join(word.capitalize() for word in words if word)


if __name__ == "__main__":
    main()
