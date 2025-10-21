#!/usr/bin/env python3
"""
Check UV Violations - PreToolUse Hook
======================================
Enforces the use of UV for all Python-related commands.

This hook ensures that:
- All python/pip commands are run through uv
- Modern uv syntax (uv add/remove/sync) is used instead of uv pip syntax

Usage:
    python check_uv_violations.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import json
import shlex
import sys
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    command: str
    file_path: str
    path: str


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
    Main entry point for the UV violations checker.
    
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
        
        # Only check bash/shell commands
        if tool_name not in {"Bash"}:
            # Not a command tool - allow
            output_decision("allow", "Not a command execution tool")
            return
        
        # Extract command from tool_input
        command_val = tool_input_obj.get("command")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(command_val, str):
            # No command - allow
            output_decision("allow", "No command to validate")
            return
        
        command = command_val.strip()
        if not command:
            # Empty command - allow
            output_decision("allow", "Empty command")
            return
        
        # Validate UV usage
        violation = validate_uv_usage(command)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Command follows UV usage guidelines")
            
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


def validate_uv_usage(command: str) -> str | None:
    """
    Validate that Python commands are using UV properly.
    
    Args:
        command: The command string to validate
        
    Returns:
        Violation message if found, None otherwise
    """
    # Parse the command
    try:
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return None
    except ValueError:
        # Invalid shell command syntax - allow it (shell will error)
        return None
    
    # Check for violations in order of priority
    
    # 1. Check for direct Python invocation
    python_violation = check_python_invocation(cmd_parts, command)
    if python_violation:
        return python_violation
    
    # 2. Check for direct pip invocation
    pip_violation = check_pip_invocation(cmd_parts, command)
    if pip_violation:
        return pip_violation
    
    # 3. Check for legacy uv pip syntax
    uv_pip_violation = check_uv_pip_syntax(cmd_parts, command)
    if uv_pip_violation:
        return uv_pip_violation
    
    return None


def check_python_invocation(cmd_parts: list[str], original_command: str) -> str | None:
    """
    Check for direct Python invocation without UV.
    
    Args:
        cmd_parts: Parsed command parts
        original_command: Original command string
        
    Returns:
        Violation message if found, None otherwise
    """
    if not cmd_parts:
        return None
    
    first_part = cmd_parts[0]
    
    # Check for python/python3 commands
    if first_part in {"python", "python3"} or first_part.endswith("/python") or first_part.endswith("/python3"):
        suggested = suggest_python_fix(cmd_parts)
        
        # Truncate long commands for display
        display_cmd = original_command if len(original_command) <= 50 else original_command[:47] + "..."
        
        return (
            f"🚫 Direct Python invocation detected. \n"
            f"Command: {display_cmd}. \n"
            f"Use 'uv run' for consistent environment management. \n"
            f"Suggested: {suggested}. \n"
            f"UV ensures proper dependency isolation and version consistency."
        )
    
    return None


def check_pip_invocation(cmd_parts: list[str], original_command: str) -> str | None:
    """
    Check for direct pip invocation without UV.
    
    Args:
        cmd_parts: Parsed command parts
        original_command: Original command string
        
    Returns:
        Violation message if found, None otherwise
    """
    if not cmd_parts:
        return None
    
    first_part = cmd_parts[0]
    
    # Check for pip/pip3 commands
    if first_part in {"pip", "pip3"} or first_part.endswith("/pip") or first_part.endswith("/pip3"):
        suggested = suggest_pip_fix(cmd_parts)
        
        # Truncate long commands for display
        display_cmd = original_command if len(original_command) <= 50 else original_command[:47] + "..."
        
        return (
            f"🚫 Direct pip invocation detected. \n"
            f"Command: {display_cmd}. \n"
            f"Use UV commands for better performance and consistency. \n"
            f"Suggested: {suggested}. \n"
            f"UV is 10-100x faster than pip and handles conflicts better."
        )
    
    # Check for python -m pip pattern
    if len(cmd_parts) >= 3:
        if cmd_parts[0] in {"python", "python3"} and cmd_parts[1] == "-m" and cmd_parts[2] in {"pip", "pip3"}:
            suggested = suggest_pip_fix(cmd_parts[2:])
            
            # Truncate long commands
            display_cmd = original_command if len(original_command) <= 50 else original_command[:47] + "..."
            
            return (
                f"🚫 'python -m pip' pattern detected.\n"
                f"Command: {display_cmd}. \n"
                f"Use UV commands instead of python -m pip. \n"
                f"Suggested: {suggested}. \n"
                f"UV provides faster, more reliable package management."
            )
    
    return None


def check_uv_pip_syntax(cmd_parts: list[str], original_command: str) -> str | None:
    """
    Check for legacy 'uv pip' syntax that should use modern UV commands.
    
    Args:
        cmd_parts: Parsed command parts
        original_command: Original command string
        
    Returns:
        Violation message if found, None otherwise
    """
    # Check for uv pip pattern
    if len(cmd_parts) >= 2:
        if cmd_parts[0] == "uv" and cmd_parts[1] == "pip":
            if len(cmd_parts) >= 3:
                subcommand = cmd_parts[2]
                
                # Check if this is a command that has a modern equivalent
                if subcommand in {"install", "uninstall"}:
                    suggested = suggest_modern_uv_syntax(cmd_parts)
                    
                    # Truncate long commands
                    display_cmd = original_command if len(original_command) <= 50 else original_command[:47] + "..."
                    
                    return (
                        f"⚠️ Legacy 'uv pip' syntax detected. \n"
                        f"Command: {display_cmd}. \n"
                        f"Use modern UV syntax (uv add/remove) for cleaner workflow. \n"
                        f"Suggested: {suggested}. \n"
                        f"Modern UV commands integrate better with pyproject.toml. \n"
                    )
    
    return None


def suggest_python_fix(cmd_parts: list[str]) -> str:
    """
    Suggest UV-based fix for Python invocation.

    Args:
        cmd_parts: Parsed command parts

    Returns:
        Suggested command(s) - primary and fallback
    """
    # Primary suggestion: Replace python/python3 with uv run, skipping the python command itself
    suggested_new_parts = ["uv", "run"] + cmd_parts[1:]

    # Fallback suggestion: Keep python in the command
    suggested_new_parts_with_python: list[str] = ["uv", "run"] + cmd_parts

    # Format primary suggestion
    suggestion = shlex.join(suggested_new_parts)
    if len(suggestion) > 60:
        suggestion = suggestion[:57] + "..."

    # Format fallback suggestion
    fallback = shlex.join(suggested_new_parts_with_python)
    if len(fallback) > 60:
        fallback = fallback[:57] + "..."

    # Return both suggestions
    return f"{suggestion} (or try: {fallback})"


def suggest_pip_fix(cmd_parts: list[str]) -> str:
    """
    Suggest UV-based fix for pip commands.
    
    Args:
        cmd_parts: Parsed command parts (starting with pip)
        
    Returns:
        Suggested command
    """
    if len(cmd_parts) < 2:
        return "uv add <package>"
    
    # Find the pip subcommand
    pip_index = 0
    for i, part in enumerate(cmd_parts):
        if part in {"pip", "pip3"}:
            pip_index = i
            break
    
    if pip_index + 1 >= len(cmd_parts):
        return "uv add <package>"
    
    subcommand = cmd_parts[pip_index + 1]
    remaining_args = cmd_parts[pip_index + 2:] if pip_index + 2 < len(cmd_parts) else []
    
    # Map pip commands to uv equivalents
    if subcommand == "install":
        packages: list[str] = []
        
        for i, arg in enumerate(remaining_args):
            if arg in {"-r", "--requirement"}:
                if i + 1 < len(remaining_args):
                    return "uv sync"
                continue
            elif arg in {"-e", "--editable"}:
                if i + 1 < len(remaining_args):
                    path = remaining_args[i + 1]
                    return f"uv add --editable {path}"
                continue
            elif not arg.startswith("-"):
                packages.append(arg)
        
        if packages:
            return f"uv add {' '.join(packages[:3])}"  # Limit to 3 packages
        else:
            return "uv sync"
            
    elif subcommand == "uninstall":
        packages = [arg for arg in remaining_args if not arg.startswith("-")][:3]
        if packages:
            return f"uv remove {' '.join(packages)}"
        else:
            return "uv remove <package>"
            
    elif subcommand == "freeze":
        return "uv export --no-hashes"
        
    elif subcommand == "list":
        return "uv pip list"
        
    else:
        return f"uv {subcommand}"


def suggest_modern_uv_syntax(cmd_parts: list[str]) -> str:
    """
    Suggest modern UV syntax for legacy uv pip commands.
    
    Args:
        cmd_parts: Parsed command parts (starting with 'uv')
        
    Returns:
        Suggested command
    """
    if len(cmd_parts) < 3:
        return "uv add <package>"
    
    subcommand = cmd_parts[2]
    remaining_args = cmd_parts[3:] if len(cmd_parts) > 3 else []
    
    if subcommand == "install":
        packages: list[str] = []
        editable = False
        dev = False
        
        for i, arg in enumerate(remaining_args):
            if arg in {"-r", "--requirement"}:
                return "uv sync"
            elif arg in {"-e", "--editable"}:
                editable = True
                if i + 1 < len(remaining_args):
                    packages.append(remaining_args[i + 1])
                continue
            elif arg == "--dev":
                dev = True
                continue
            elif not arg.startswith("-"):
                packages.append(arg)
        
        if packages:
            cmd = "uv add"
            if dev:
                cmd += " --dev"
            if editable:
                cmd += " --editable"
            packages_str = ' '.join(packages[:3])  # Limit to 3 packages
            return f"{cmd} {packages_str}"
        else:
            return "uv sync"
            
    elif subcommand == "uninstall":
        packages = [arg for arg in remaining_args if not arg.startswith("-")][:3]
        if packages:
            return f"uv remove {' '.join(packages)}"
        else:
            return "uv remove <package>"
    
    else:
        return shlex.join(cmd_parts)


if __name__ == "__main__":
    main()