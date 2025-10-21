#!/usr/bin/env python3
"""
Check Tmp Violation - PreToolUse Hook
======================================
Prevents file creation in /tmp directory for better observability.

This hook enforces the policy:
- Never create files in /tmp
- Use current directory or home directory instead
- Keep all test scripts and temporary files visible

Usage:
    python check_tmp_violation.py

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
    Main entry point for the tmp violation checker.
    
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
        
        # Check for /tmp usage
        violation = check_tmp_usage(tool_name, typed_tool_input)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation["reason"], suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "No /tmp usage detected")
            
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


def check_tmp_usage(tool_name: str, tool_input: ToolInput) -> dict[str, str] | None:
    """
    Check if an operation uses /tmp directory.
    
    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        
    Returns:
        Violation dict with reason if /tmp usage detected, None otherwise
    """
    # File-based tools
    if tool_name in {"Write", "Edit", "MultiEdit", "Read"}:
        # Check file_path parameter
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if file_path and is_tmp_path(file_path):
            operation = "read from" if tool_name in {"Read", "view"} else "write to"
            alternative = get_alternative_path(file_path)
            
            reason = (
                f"🚫 Cannot {operation} /tmp directory. \n"
                f"Path: {file_path}. \n"
                f"Policy: Never use /tmp for file operations (poor observability). \n"
                f"Alternative: {alternative}. \n"
                f"Best practices: Use current directory (./) for test scripts, \n"
                f"create 'scripts' or 'tests' subdirectory for organization."
            )
            
            return {"reason": reason}
    
    # Bash/shell commands
    elif tool_name in {"bash", "shell", "bash_tool", "shell_tool"}:
        command = tool_input.get("command", "")
        if command:
            tmp_path = detect_tmp_in_command(command)
            if tmp_path:
                alternative = get_alternative_command(command)
                
                # Truncate long commands for display
                display_cmd = command if len(command) <= 50 else command[:47] + "..."
                
                reason = (
                    f"🚫 Command uses /tmp path: {tmp_path}. \n"
                    f"Command: {display_cmd}. \n"
                    f"Policy: Never use /tmp for file operations. \n"
                    f"Alternative: {alternative}. \n"
                    f"Examples: python ./test.py, echo 'data' > ./output.txt"
                )
                
                return {"reason": reason}
    
    return None


def is_tmp_path(file_path: str) -> bool:
    """
    Check if a file path is in /tmp directory.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if it's in /tmp, False otherwise
    """
    try:
        path = Path(file_path).resolve()
        path_str = str(path)
    except (ValueError, RuntimeError, OSError):
        # If we can't resolve, check the string directly
        path_str = file_path
    
    # Normalize path separators
    path_str = path_str.replace('\\', '/')
    
    # Check various tmp locations
    tmp_prefixes = ['/tmp/', '/var/tmp/', 'tmp/']
    tmp_exact = ['/tmp', '/var/tmp', 'tmp']
    
    return (
        any(path_str.startswith(prefix) for prefix in tmp_prefixes) or
        path_str in tmp_exact
    )


def detect_tmp_in_command(command: str) -> str | None:
    """
    Detect /tmp usage in bash commands.
    
    Args:
        command: Bash command to check
        
    Returns:
        /tmp path if detected, None otherwise
    """
    # Patterns that indicate /tmp usage
    tmp_patterns = [
        r'/tmp(?:/[^\s]*)?',      # /tmp or /tmp/file
        r'/var/tmp(?:/[^\s]*)?',  # /var/tmp or /var/tmp/file
    ]
    
    for pattern in tmp_patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(0)
    
    return None


def get_alternative_path(tmp_path: str) -> str:
    """
    Suggest an alternative path to /tmp.
    
    Args:
        tmp_path: The /tmp path being used
        
    Returns:
        Suggested alternative path
    """
    try:
        filename = Path(tmp_path).name
    except (ValueError, RuntimeError):
        filename = "test_file"
    
    if not filename or filename == 'tmp':
        filename = 'test_file'
    
    # Suggest alternatives based on file extension
    ext = Path(filename).suffix.lower()
    
    if ext == '.py':
        return f"Use './{filename}' or './scripts/{filename}'"
    elif ext == '.sh':
        return f"Use './scripts/{filename}'"
    elif ext in ['.txt', '.log']:
        return f"Use './{filename}' or './logs/{filename}'"
    else:
        return f"Use './{filename}' in the current directory"


def get_alternative_command(command: str) -> str:
    """
    Suggest an alternative command without /tmp.
    
    Args:
        command: Command using /tmp
        
    Returns:
        Suggested alternative
    """
    # Provide context-aware suggestions
    if 'python' in command.lower():
        return "python ./test_script.py"
    elif '>' in command:
        return "echo 'content' > ./output.txt"
    elif 'mkdir' in command.lower():
        return "mkdir ./test_dir"
    elif 'touch' in command.lower():
        return "touch ./test_file"
    else:
        return "Use current directory (.) or home directory (~) instead of /tmp"


if __name__ == "__main__":
    main()