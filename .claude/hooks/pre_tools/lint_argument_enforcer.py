#!/usr/bin/env python3
"""
Check Config Violations - PreToolUse Hook
==========================================
Enforces configuration standards for development tools before execution.

This hook ensures that:
- ruff is always called with the --config parameter (pointing to pyproject.toml)
- basedpyright is always called with --level error (to avoid pedantic warnings)

Usage:
    python check_config_violations.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import json
import shlex
import sys
from pathlib import Path
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
    Main entry point for the config violations checker.
    
    Reads hook data from stdin and validates tool configurations.
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
        
        # Validate the command configuration
        violation = validate_command_config(command)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Command configuration is correct")
            
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


def validate_command_config(command: str) -> str | None:
    """
    Validate command configuration for ruff and basedpyright.
    
    Args:
        command: The command string to validate
        
    Returns:
        Violation message if found, None otherwise
    """
    # Parse the command to identify tools and arguments
    try:
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return None
    except ValueError:
        # Invalid shell command syntax - allow it (shell will error)
        return None
    
    # Check for ruff
    ruff_violation = check_ruff_config(cmd_parts, command)
    if ruff_violation:
        return ruff_violation
    
    # Check for basedpyright
    basedpyright_violation = check_basedpyright_config(cmd_parts, command)
    if basedpyright_violation:
        return basedpyright_violation
    
    return None


def check_ruff_config(cmd_parts: list[str], original_command: str) -> str | None:
    """
    Check if ruff command has proper --config parameter.
    
    Args:
        cmd_parts: Parsed command parts
        original_command: Original command string
        
    Returns:
        Violation message if found, None otherwise
    """
    # Check if this is a ruff command
    is_ruff = False
    
    for i, part in enumerate(cmd_parts):
        # Direct invocation or path to ruff
        if "ruff" in part.lower():
            is_ruff = True
            break
        # Python module invocation
        if i >= 2 and cmd_parts[i-2].endswith("python") and cmd_parts[i-1] == "-m" and part == "ruff":
            is_ruff = True
            break
    
    if not is_ruff:
        return None
    
    # Check if --config is present
    has_config = False
    config_path = None
    
    for i, part in enumerate(cmd_parts):
        if part == "--config":
            has_config = True
            if i + 1 < len(cmd_parts):
                config_path = cmd_parts[i + 1]
            break
        elif part.startswith("--config="):
            has_config = True
            config_path = part.split("=", 1)[1]
            break
    
    if not has_config:
        # No --config parameter found
        suggested_fix = suggest_ruff_fix(cmd_parts)
        display_cmd = original_command if len(original_command) <= 60 else original_command[:57] + "..."
        
        return (
            f"📝 Ruff requires --config parameter. \n"
            f"Command: {display_cmd}. \n"
            f"Policy: Always specify configuration file for consistent linting. \n"
            f"Suggested: {suggested_fix}. \n"
            f"This ensures all team members use the same rules and settings."
        )
    
    # Optionally validate config file exists
    if config_path and not Path(config_path).exists():
        # Check common config file names
        common_configs = ["pyproject.toml", "ruff.toml", ".ruff.toml"]
        if config_path not in common_configs:
            # Check if any common config exists
            for cfg in common_configs:
                if Path(cfg).exists():
                    return (
                        f"⚠️ Config file '{config_path}' not found. \n"
                        f"Found '{cfg}' in current directory. \n"
                        f"Command: {original_command[:60]}... \n"
                        f"Suggested: Use --config {cfg}"
                    )
    
    return None


def check_basedpyright_config(cmd_parts: list[str], original_command: str) -> str | None:
    """
    Check if basedpyright command has proper --level error parameter.
    
    Args:
        cmd_parts: Parsed command parts
        original_command: Original command string
        
    Returns:
        Violation message if found, None otherwise
    """
    # Check if this is a basedpyright command
    is_basedpyright = False
    
    for part in cmd_parts:
        # Check for basedpyright in the command
        if "basedpyright" in part.lower() or "pyright" in part.lower():
            is_basedpyright = True
            break
    
    if not is_basedpyright:
        return None
    
    # Check for --level parameter
    has_level = False
    level_value = None
    
    for i, part in enumerate(cmd_parts):
        if part == "--level":
            has_level = True
            if i + 1 < len(cmd_parts):
                level_value = cmd_parts[i + 1]
            break
        elif part.startswith("--level="):
            has_level = True
            level_value = part.split("=", 1)[1]
            break
    
    if not has_level:
        # No --level parameter found
        suggested_fix = suggest_basedpyright_fix(cmd_parts, "missing")
        display_cmd = original_command if len(original_command) <= 60 else original_command[:57] + "..."
        
        return (
            f"🔍 Basedpyright requires --level error. \n"
            f"Command: {display_cmd}. \n"
            f"Policy: Only report errors, not pedantic warnings. \n"
            f"Suggested: {suggested_fix}. \n"
            f"This avoids overwhelming output with minor style issues."
        )
    
    if level_value and level_value.lower() != "error":
        # Wrong level specified
        suggested_fix = suggest_basedpyright_fix(cmd_parts, "wrong", level_value)
        display_cmd = original_command if len(original_command) <= 60 else original_command[:57] + "..."
        
        return (
            f"⚠️ Basedpyright level must be 'error', not '{level_value}'. \n"
            f"Command: {display_cmd}. \n"
            f"Policy: Focus on actual errors, skip pedantic warnings. \n"
            f"Suggested: {suggested_fix}. \n"
            f"Level '{level_value}' includes too many minor issues."
        )
    
    return None


def suggest_ruff_fix(cmd_parts: list[str]) -> str:
    """
    Suggest a fix for ruff configuration violations.
    
    Args:
        cmd_parts: Parsed command parts
        
    Returns:
        Suggested fixed command
    """
    # Find where to insert --config
    insert_index = -1
    for i, part in enumerate(cmd_parts):
        if "ruff" in part:
            insert_index = i + 1
            # Skip subcommands like 'check' or 'format'
            if insert_index < len(cmd_parts) and not cmd_parts[insert_index].startswith("-"):
                insert_index += 1
            break
    
    # Look for common config files in order of preference
    config_file = "pyproject.toml"  # Default
    config_files = ["pyproject.toml", "ruff.toml", ".ruff.toml"]
    
    for cfg in config_files:
        if Path(cfg).exists():
            config_file = cfg
            break
    
    # Build fixed command
    if insert_index > 0 and insert_index <= len(cmd_parts):
        fixed_parts = cmd_parts[:insert_index] + ["--config", config_file] + cmd_parts[insert_index:]
        fixed_command = shlex.join(fixed_parts)
    else:
        # Fallback: append at the end
        fixed_command = shlex.join(cmd_parts) + f" --config {config_file}"
    
    # Truncate if too long
    if len(fixed_command) > 60:
        fixed_command = fixed_command[:57] + "..."
    
    return fixed_command


def suggest_basedpyright_fix(cmd_parts: list[str], issue_type: str, current_level: str = "") -> str:
    """
    Suggest a fix for basedpyright configuration violations.
    
    Args:
        cmd_parts: Parsed command parts
        issue_type: Type of issue ("missing" or "wrong")
        current_level: Current level value if wrong
        
    Returns:
        Suggested fixed command
    """
    if issue_type == "missing":
        # Add --level error
        insert_index = -1
        for i, part in enumerate(cmd_parts):
            if "pyright" in part.lower():
                insert_index = i + 1
                break
        
        if insert_index > 0 and insert_index <= len(cmd_parts):
            fixed_parts = cmd_parts[:insert_index] + ["--level", "error"] + cmd_parts[insert_index:]
            fixed_command = shlex.join(fixed_parts)
        else:
            # Fallback: append at the end
            fixed_command = shlex.join(cmd_parts) + " --level error"
    
    elif issue_type == "wrong":
        # Replace existing level
        fixed_parts: list[str] = []
        skip_next = False
        
        for i, part in enumerate(cmd_parts):
            if skip_next:
                fixed_parts.append("error")
                skip_next = False
            elif part == "--level":
                fixed_parts.append(part)
                skip_next = True
            elif part.startswith("--level="):
                fixed_parts.append("--level=error")
            else:
                fixed_parts.append(part)
        
        fixed_command = shlex.join(fixed_parts)
    
    else:
        fixed_command = shlex.join(cmd_parts)
    
    # Truncate if too long
    if len(fixed_command) > 60:
        fixed_command = fixed_command[:57] + "..."
    
    return fixed_command


if __name__ == "__main__":
    main()