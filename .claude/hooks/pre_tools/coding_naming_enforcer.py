#!/usr/bin/env python3
"""
PEP 8 Coding Naming Convention Enforcer - PreToolUse Hook
==========================================================
Enforces PEP 8 naming conventions for Python code before files are written.

This hook enforces:
- snake_case for variables and functions
- PascalCase for classes
- UPPER_CASE for constants
- No camelCase or mixedCase (except in specific contexts)
- Valid Python identifiers

Usage:
    python coding_naming_enforcer.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import ast
import json
import re
import sys
from typing import Literal, TypedDict


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""

    file_path: str
    content: str
    new_string: str
    old_string: str


class HookSpecificOutput(TypedDict):
    """Type definition for hook-specific output."""

    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutput(TypedDict, total=False):
    """Type definition for complete hook output."""

    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


def main() -> None:
    """
    Main entry point for the PEP 8 naming convention enforcer.

    Reads hook data from stdin and outputs JSON decision.
    """
    try:
        # Read input from stdin
        input_text = sys.stdin.read()

        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)

        # Parse JSON
        try:
            parsed_json = json.loads(input_text)  # type: ignore[reportAny]
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)

        # Validate input structure
        if not isinstance(parsed_json, dict):
            # Invalid format - non-blocking error
            print("Error: Input must be a JSON object", file=sys.stderr)
            sys.exit(1)

        # Extract fields with type checking
        tool_name_obj = parsed_json.get("tool_name", "")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        tool_input_obj = parsed_json.get("tool_input", {})  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]

        if not isinstance(tool_name_obj, str):
            # Missing tool_name - allow operation
            output_decision("allow", "Missing or invalid tool_name")
            return

        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - allow operation
            output_decision("allow", "Invalid tool_input format")
            return

        tool_name: str = tool_name_obj

        # Create typed tool input
        typed_tool_input = ToolInput()

        # Extract relevant fields
        file_path_val = tool_input_obj.get("file_path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val

        content_val = tool_input_obj.get("content")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(content_val, str):
            typed_tool_input["content"] = content_val

        new_string_val = tool_input_obj.get("new_string")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(new_string_val, str):
            typed_tool_input["new_string"] = new_string_val

        old_string_val = tool_input_obj.get("old_string")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(old_string_val, str):
            typed_tool_input["old_string"] = old_string_val

        # Check for PEP 8 naming violations
        violation = check_pep8_naming(tool_name, typed_tool_input)

        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "PEP 8 naming conventions are correct")

    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False,
) -> None:
    """
    Output a properly formatted JSON decision.

    Args:
        decision: Permission decision
        reason: Reason for the decision
        suppress_output: Whether to suppress output in transcript mode
    """
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }

    # Only add suppressOutput if it's True
    if suppress_output:
        output["suppressOutput"] = True

    try:
        print(json.dumps(output))
        sys.exit(0)  # Success - JSON output controls permission
    except (TypeError, ValueError) as e:
        # Failed to serialize JSON - non-blocking error
        print(f"Error: Failed to serialize output JSON: {e}", file=sys.stderr)
        sys.exit(1)


def check_pep8_naming(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Check for PEP 8 naming convention violations.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        Violation message if found, None otherwise
    """
    # Only check Write and Edit tools
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return None

    # Get file path
    file_path = tool_input.get("file_path", "")

    # Only check Python files
    if not file_path or not file_path.endswith(".py"):
        return None

    # Get content to check
    content = None
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")

    if not content:
        return None

    # Parse and check the Python code
    return parse_and_check_code(content, file_path)


def parse_and_check_code(code: str, file_path: str) -> str | None:
    """
    Parse Python code and check for PEP 8 naming violations.

    Args:
        code: Python code to check
        file_path: Path to the file (for error messages)

    Returns:
        Violation message if found, None otherwise
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # If code has syntax errors, let Python's own error handling deal with it
        return None

    violations: list[str] = []

    # Analyze the AST
    for node in ast.walk(tree):
        # Check function and method definitions
        if isinstance(node, ast.FunctionDef):
            violation = check_function_name(node.name, node.lineno)
            if violation:
                violations.append(violation)

        # Check class definitions
        elif isinstance(node, ast.ClassDef):
            violation = check_class_name(node.name, node.lineno)
            if violation:
                violations.append(violation)

        # Check variable assignments (for constants and variables)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    violation = check_variable_name(
                        target.id,
                        node.lineno,
                        is_module_level=True,
                    )
                    if violation:
                        violations.append(violation)

    if violations:
        violation_text = "\n".join(violations[:5])  # Limit to first 5 violations
        if len(violations) > 5:
            violation_text += f"\n... and {len(violations) - 5} more violations"

        return (
            f"🐍 PEP 8 Naming Convention Violations Found\n"
            f"File: {file_path}\n\n"
            f"{violation_text}\n\n"
            f"PEP 8 Guidelines:\n"
            f"- Functions/variables: snake_case\n"
            f"  (e.g., user_name, calculate_total)\n"
            f"- Classes: PascalCase\n"
            f"  (e.g., UserProfile, DataProcessor)\n"
            f"- Constants: UPPER_CASE\n"
            f"  (e.g., MAX_VALUE, API_KEY)\n"
            f"- No camelCase or mixedCase for regular identifiers"
        )

    return None


def check_function_name(name: str, lineno: int) -> str | None:
    """
    Check if a function name follows PEP 8 conventions.

    Args:
        name: Function name
        lineno: Line number in source code

    Returns:
        Violation message if found, None otherwise
    """
    # Skip dunder methods
    if name.startswith("__") and name.endswith("__"):
        return None

    # Skip private methods (single underscore is fine)
    # Just check the naming pattern

    # Check if it's snake_case
    if not is_snake_case(name):
        suggested = to_snake_case(name)
        return (
            f"Line {lineno}: Function '{name}' should be snake_case. "
            f"Suggested: '{suggested}'"
        )

    return None


def check_class_name(name: str, lineno: int) -> str | None:
    """
    Check if a class name follows PEP 8 conventions.

    Args:
        name: Class name
        lineno: Line number in source code

    Returns:
        Violation message if found, None otherwise
    """
    # Check if it's PascalCase
    if not is_pascal_case(name):
        suggested = to_pascal_case(name)
        return (
            f"Line {lineno}: Class '{name}' should be PascalCase. "
            f"Suggested: '{suggested}'"
        )

    return None


def check_variable_name(name: str, lineno: int, is_module_level: bool) -> str | None:
    """
    Check if a variable name follows PEP 8 conventions.

    Args:
        name: Variable name
        lineno: Line number in source code
        is_module_level: Whether this is a module-level assignment

    Returns:
        Violation message if found, None otherwise
    """
    # Skip private variables (they can have underscores)
    # Skip dunder variables
    if name.startswith("__") and name.endswith("__"):
        return None

    # Check if it's a constant (all uppercase)
    if name.isupper() and "_" in name or len(name) > 1 and name.isupper():
        # This is likely a constant - it's fine
        return None

    # Check if it's supposed to be a constant but isn't all uppercase
    if is_module_level and has_uppercase(name) and not is_snake_case(name):
        # Could be either a wrongly named constant or wrongly named variable
        if any(c.isupper() for c in name) and any(c.islower() for c in name):
            # Mixed case - likely meant to be a variable
            suggested = to_snake_case(name)
            return (
                f"Line {lineno}: Variable '{name}' should be snake_case. "
                f"Suggested: '{suggested}'"
            )

    # Regular variable - should be snake_case
    if not is_snake_case(name):
        suggested = to_snake_case(name)
        return (
            f"Line {lineno}: Variable '{name}' should be snake_case. "
            f"Suggested: '{suggested}'"
        )

    return None


def is_snake_case(name: str) -> bool:
    """
    Check if a name follows snake_case convention.

    Args:
        name: Name to check

    Returns:
        True if name is snake_case, False otherwise
    """
    # Allow leading underscores (private/protected)
    cleaned = name.lstrip("_")

    # Empty or all underscores
    if not cleaned:
        return True

    # Should be all lowercase with underscores
    # No consecutive underscores, no trailing underscores
    pattern = r"^[a-z0-9_]*[a-z0-9]$|^[a-z0-9]$"
    return bool(re.match(pattern, cleaned))


def is_pascal_case(name: str) -> bool:
    """
    Check if a name follows PascalCase convention.

    Args:
        name: Name to check

    Returns:
        True if name is PascalCase, False otherwise
    """
    # Allow leading underscores (private classes)
    cleaned = name.lstrip("_")

    # Empty or all underscores
    if not cleaned:
        return True

    # Should start with uppercase, no underscores
    # Pattern: uppercase letter, followed by alphanumeric
    pattern = r"^[A-Z][a-zA-Z0-9]*$"
    return bool(re.match(pattern, cleaned))


def has_uppercase(name: str) -> bool:
    """
    Check if a name contains any uppercase letters.

    Args:
        name: Name to check

    Returns:
        True if name has uppercase letters, False otherwise
    """
    return any(c.isupper() for c in name)


def to_snake_case(name: str) -> str:
    """
    Convert a name to snake_case.

    Args:
        name: Name to convert

    Returns:
        snake_case version of the name
    """
    # Preserve leading underscores
    leading_underscores = len(name) - len(name.lstrip("_"))
    prefix = "_" * leading_underscores
    cleaned = name.lstrip("_")

    # Insert underscores before uppercase letters
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", cleaned)

    # Convert to lowercase
    snake = snake.lower()

    return prefix + snake


def to_pascal_case(name: str) -> str:
    """
    Convert a name to PascalCase.

    Args:
        name: Name to convert

    Returns:
        PascalCase version of the name
    """
    # Preserve leading underscores
    leading_underscores = len(name) - len(name.lstrip("_"))
    prefix = "_" * leading_underscores
    cleaned = name.lstrip("_")

    # Split by underscores and capitalize each part
    parts = cleaned.split("_")
    pascal = "".join(word.capitalize() for word in parts if word)

    return prefix + pascal


if __name__ == "__main__":
    main()
