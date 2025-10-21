#!/usr/bin/env python3
"""
Check Requirements Violation - PreToolUse Hook
===============================================
Prevents direct editing of dependency files, enforcing use of uv commands.

Policy enforced:
- Never edit requirements.txt directly - use uv add/remove
- Never edit pyproject.toml directly - use uv commands
- Never edit uv.lock - it's auto-generated
- Never edit pipfile - it's auto-generated
- Never edit pipfile.lock - it's auto-generated

Usage:
    python check_requirements_violation.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import json
import re
import sys
from pathlib import Path
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    file_path: str
    path: str
    command: str
    content: str


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
    Main entry point for the requirements violation checker.
    
    Reads hook data from stdin and outputs JSON decision.
    """
    try:
        # Read input from stdin
        input_text = sys.stdin.read()
        
        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)
        
        # Parse JSON - unavoidable Any type from json.loads
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
            # Missing or invalid tool_name - allow operation
            output_decision("allow", "Missing or invalid tool_name")
            return
        
        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - allow operation
            output_decision("allow", "Invalid tool_input format")
            return
        
        tool_name: str = tool_name_obj
        
        # Create typed tool input
        typed_tool_input = ToolInput()
        
        # Safely extract known fields
        file_path_val = tool_input_obj.get("file_path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val
        
        path_val = tool_input_obj.get("path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(path_val, str):
            typed_tool_input["path"] = path_val
        
        command_val = tool_input_obj.get("command")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(command_val, str):
            typed_tool_input["command"] = command_val
        
        # Check for dependency file violations
        violation = check_dependency_file_edit(tool_name, typed_tool_input)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Operation does not edit dependency files")
        
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False
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
            "permissionDecisionReason": reason
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


def check_dependency_file_edit(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Check if operation edits dependency files.
    
    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        
    Returns:
        Violation message if found, None otherwise
    """
    # Tools that can edit files
    write_tools = {
        "Write", "Edit", "MultiEdit"
    }
    
    # Check bash commands
    if tool_name in {"Bash"}:
        command = tool_input.get("command", "")
        if command:
            violation = check_bash_dependency_edit(command)
            if violation:
                return violation
    
    # Check file edit tools
    if tool_name in write_tools:
        # Get file path
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if file_path:
            violation = check_if_dependency_file(file_path)
            if violation:
                return violation
    
    return None


def check_if_dependency_file(file_path: str) -> str | None:
    """
    Check if a file is a dependency file that shouldn't be edited.
    
    Args:
        file_path: Path to check
        
    Returns:
        Violation message if it's a dependency file, None otherwise
    """
    try:
        path = Path(file_path)
        filename = path.name.lower()
    except (ValueError, OSError):
        # Invalid path - allow operation
        return None
    
    # Check for various dependency files
    if filename == "requirements.txt" or filename.endswith("requirements.txt"):
        return (
            f"🚫 Direct editing of {path.name} blocked. \n"
            "Use 'uv add <package>' to add dependencies or 'uv remove <package>' to remove them. \n"
            "For version constraints use 'uv add \"package>=1.0\"'. \n"
            "This ensures proper dependency resolution and maintains consistency."
        )
    
    if "requirements" in filename and filename.endswith(".txt"):
        return (
            f"🚫 Direct editing of {path.name} blocked. \n"
            "Use UV commands: 'uv add <package>' to add, 'uv remove <package>' to remove. \n"
            "UV automatically manages dependency versions and conflicts."
        )
    
    if filename == "pyproject.toml":
        return (
            "🚫 Direct editing of pyproject.toml blocked. \n"
            "Use UV commands: 'uv add <package>' for production deps, "
            "'uv add --dev <package>' for dev dependencies, "
            "'uv add --optional <group> <package>' for optional groups. \n"
            "This ensures proper TOML formatting and dependency resolution."
        )
    
    if filename == "uv.lock":
        return (
            "⛔ Never edit uv.lock directly! "
            "This file is auto-generated by UV. \n"
            "Use 'uv add', 'uv remove', or 'uv sync' to update dependencies, "
            "and uv.lock will be updated automatically. \n"
            "Manual edits will cause inconsistencies."
        )
    
    if filename in {"pipfile", "pipfile.lock"}:
        return (
            f"🚫 Direct editing of {path.name} blocked. \n"
            "This project uses UV for dependency management. \n"
            "Migrate from Pipenv: use 'uv add' instead of 'pipenv install', "
            "'uv remove' instead of 'pipenv uninstall'."
        )
    
    return None


def check_bash_dependency_edit(command: str) -> str | None:
    """
    Check if a bash command edits dependency files.
    
    Args:
        command: Bash command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    command_lower = command.lower()
    
    # Dependency files to protect
    dependency_files = [
        ("requirements.txt", "requirements.txt"),
        ("pyproject.toml", "pyproject.toml"),
        ("uv.lock", "uv.lock"),
        ("pipfile", "Pipfile"),
        ("pipfile.lock", "Pipfile.lock")
    ]
    
    # Edit operation patterns
    edit_patterns = [
        (r'\becho\s+.*>\s*', "echo redirect"),
        (r'\becho\s+.*>>\s*', "echo append"),
        (r'\bcat\s+.*>\s*', "cat redirect"),
        (r'\bsed\s+-i', "sed in-place edit"),
        (r'\b(nano|vim?|emacs|code)\s+', "text editor"),
        (r'\btee\s+', "tee command"),
    ]
    
    # Check each dependency file
    for file_lower, file_actual in dependency_files:
        if file_lower in command_lower:
            # Check for edit operations
            for pattern, operation in edit_patterns:
                if re.search(pattern + r'.*' + file_lower, command_lower):
                    return (
                        f"🚫 Bash command attempts to edit {file_actual} using {operation}. \n"
                        f"Use UV commands instead: {get_uv_suggestion(file_actual)}. \n"
                        f"Example: 'uv add requests' instead of editing the file directly."
                    )
            
            # Check for simple redirects
            if '>' in command and file_lower in command_lower:
                return (
                    f"🚫 Bash command attempts to write to {file_actual}. \n"
                    f"Use UV commands instead: {get_uv_suggestion(file_actual)}. \n"
                    f"UV handles dependency resolution and version conflicts automatically."
                )
    
    return None


def get_uv_suggestion(filename: str) -> str:
    """
    Get UV command suggestion for a specific file.
    
    Args:
        filename: Name of the dependency file
        
    Returns:
        Appropriate UV command suggestion
    """
    suggestions = {
        "requirements.txt": "'uv add <package>' or 'uv remove <package>'",
        "pyproject.toml": "'uv add', 'uv remove', or 'uv add --dev'",
        "uv.lock": "'uv sync' or 'uv lock' (never edit directly)",
        "Pipfile": "'uv add' and 'uv remove' (migrate from pipenv)",
        "Pipfile.lock": "'uv sync' (migrate from pipenv)",
    }
    
    return suggestions.get(filename, "'uv add' or 'uv remove'")


if __name__ == "__main__":
    main()