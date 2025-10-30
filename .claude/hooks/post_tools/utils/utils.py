#!/usr/bin/env python3
"""
Shared Utilities for PostToolUse Hooks
=======================================

Common utility functions for PostToolUse hooks.
Provides input parsing, output formatting, and validation helpers.

Usage:
    from .utils import parse_hook_input, output_feedback, output_block

Dependencies:
    - Python 3.12+ (for improved typing features)
    - No external packages required
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple, cast

try:
    from .data_types import HookOutput, HookSpecificOutput, ToolInput
except ImportError:
    from data_types import HookOutput, HookSpecificOutput, ToolInput


# ==================== Input Parsing Functions ====================


def parse_hook_input() -> Optional[Tuple[str, ToolInput, dict[str, object]]]:
    """
    Parse and validate hook input from stdin.

    Returns:
        Tuple of (tool_name, tool_input, tool_response) or None if parsing fails

    Example:
        >>> result = parse_hook_input()
        >>> if result is None:
        ...     output_feedback("")
        ...     return
        >>> tool_name, tool_input, tool_response = result
        >>> file_path = tool_input.get("file_path", "")
        >>> success = tool_response.get("success", True)

    Error Handling:
        - Returns None for invalid JSON
        - Returns None for missing required fields
        - Logs warnings to stderr for debugging
    """
    try:
        input_text = sys.stdin.read()
        # json.loads returns Any, but we know it's a dict at runtime
        parsed_json = cast(dict[str, object], json.loads(input_text))
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON input: {e}", file=sys.stderr)
        return None

    # Extract and validate tool_name
    tool_name_obj = parsed_json.get("tool_name", "")
    tool_name = str(tool_name_obj) if isinstance(tool_name_obj, str) else ""

    if not tool_name:
        print("Warning: Missing tool_name in hook input", file=sys.stderr)
        return None

    # Extract and validate tool_input
    tool_input_obj = parsed_json.get("tool_input", {})
    if not isinstance(tool_input_obj, dict):
        tool_input_obj = {}

    typed_tool_input = ToolInput()

    # Validate and extract file_path
    if "file_path" in tool_input_obj:
        file_path_val: object = tool_input_obj["file_path"]  # type: ignore[reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val

    # Validate and extract content
    if "content" in tool_input_obj:
        content_val: object = tool_input_obj["content"]  # type: ignore[reportUnknownVariableType]
        if isinstance(content_val, str):
            typed_tool_input["content"] = content_val

    # Validate and extract command
    if "command" in tool_input_obj:
        command_val: object = tool_input_obj["command"]  # type: ignore[reportUnknownVariableType]
        if isinstance(command_val, str):
            typed_tool_input["command"] = command_val

    # Validate and extract old_string (Edit tool)
    if "old_string" in tool_input_obj:
        old_string_val: object = tool_input_obj["old_string"]  # type: ignore[reportUnknownVariableType]
        if isinstance(old_string_val, str):
            typed_tool_input["old_string"] = old_string_val

    # Validate and extract new_string (Edit tool)
    if "new_string" in tool_input_obj:
        new_string_val: object = tool_input_obj["new_string"]  # type: ignore[reportUnknownVariableType]
        if isinstance(new_string_val, str):
            typed_tool_input["new_string"] = new_string_val

    # Validate and extract replace_all (Edit tool)
    if "replace_all" in tool_input_obj:
        replace_all_val: object = tool_input_obj["replace_all"]  # type: ignore[reportUnknownVariableType]
        if isinstance(replace_all_val, bool):
            typed_tool_input["replace_all"] = replace_all_val

    # Validate and extract pattern (Glob tool)
    if "pattern" in tool_input_obj:
        pattern_val: object = tool_input_obj["pattern"]  # type: ignore[reportUnknownVariableType]
        if isinstance(pattern_val, str):
            typed_tool_input["pattern"] = pattern_val

    # Validate and extract path (Glob/Grep tools)
    if "path" in tool_input_obj:
        path_val: object = tool_input_obj["path"]  # type: ignore[reportUnknownVariableType]
        if isinstance(path_val, str):
            typed_tool_input["path"] = path_val

    # Extract tool_response (always a dict, even if empty)
    tool_response_obj = parsed_json.get("tool_response", {})
    if not isinstance(tool_response_obj, dict):
        tool_response: dict[str, object] = {}
    else:
        tool_response = cast(dict[str, object], tool_response_obj)

    return (tool_name, typed_tool_input, tool_response)


def parse_hook_input_minimal() -> Optional[dict[str, object]]:
    """
    Parse raw hook input without validation (for advanced usage).

    Returns:
        Raw dictionary from stdin JSON or None if parsing fails

    Use Case:
        - Hooks that need access to custom/additional fields
        - Debugging and logging hooks

    Example:
        >>> raw_input = parse_hook_input_minimal()
        >>> if raw_input is None:
        ...     sys.exit(0)
        >>> session_id = raw_input.get("session_id", "unknown")
        >>> custom_field = raw_input.get("custom_field", "")
    """
    try:
        input_text = sys.stdin.read()
        parsed_json = cast(dict[str, object], json.loads(input_text))
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON input: {e}", file=sys.stderr)
        return None


# ==================== Output Functions ====================


def output_feedback(context: str, suppress_output: bool = False) -> None:
    """
    Output feedback to Claude without blocking.

    Parameters:
        context: Feedback message to inject into Claude's context
        suppress_output: Hide from transcript mode (Ctrl-R)

    Behavior:
        - Outputs JSON with additionalContext in hookSpecificOutput
        - Does not include decision field (non-blocking)
        - Exit code 0

    Output Structure:
        {
          "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "feedback message"
          },
          "suppressOutput": true  // if suppress_output=True
        }

    Example:
        >>> output_feedback(
        ...     "✅ Ruff formatted file.py: Fixed 3 lint violations",
        ...     suppress_output=True
        ... )
    """
    output: HookOutput = {}

    if context or not suppress_output:
        # Only include hookSpecificOutput if we have content or need to show output
        hook_specific: HookSpecificOutput = {"hookEventName": "PostToolUse"}
        if context:
            hook_specific["additionalContext"] = context
        output["hookSpecificOutput"] = hook_specific

    if suppress_output:
        output["suppressOutput"] = True

    print(json.dumps(output))
    sys.exit(0)


def output_block(
    reason: str, additional_context: str = "", suppress_output: bool = False
) -> None:
    """
    Block Claude's continuation with error message.

    Parameters:
        reason: Explanation for blocking (goes to top-level reason field)
        additional_context: Optional additional info for hookSpecificOutput
        suppress_output: Hide from transcript mode

    Behavior:
        - Outputs JSON with decision="block" and reason at TOP LEVEL
        - Optionally includes additionalContext in hookSpecificOutput
        - Blocks Claude's flow until issue resolved
        - Exit code 0

    Output Structure:
        {
          "decision": "block",
          "reason": "explanation for blocking",
          "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "optional additional context"
          },
          "suppressOutput": true  // if suppress_output=True
        }

    Example:
        >>> output_block(
        ...     reason="❌ Type checking failed with 5 errors. Fix before continuing.",
        ...     additional_context="Run: basedpyright file.py",
        ...     suppress_output=True
        ... )

    Use Case:
        Critical validation failures that require user intervention

    Important:
        In PostToolUse, decision and reason are at TOP LEVEL, not inside hookSpecificOutput!
    """
    output: HookOutput = {"decision": "block", "reason": reason}

    hook_specific: HookSpecificOutput = {"hookEventName": "PostToolUse"}
    if additional_context:
        hook_specific["additionalContext"] = additional_context
    output["hookSpecificOutput"] = hook_specific

    if suppress_output:
        output["suppressOutput"] = True

    print(json.dumps(output))
    sys.exit(0)


def output_result(hook_output: HookOutput) -> None:
    """
    Output raw HookOutput structure (advanced usage).

    Parameters:
        hook_output: Complete HookOutput dictionary

    Example:
        >>> output: HookOutput = {
        ...     "decision": "block",
        ...     "reason": "Critical error detected",
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "PostToolUse",
        ...         "additionalContext": "Additional info"
        ...     },
        ...     "suppressOutput": True
        ... }
        >>> output_result(output)

    Note:
        Most hooks should use output_feedback() or output_block() instead.
        This function is for advanced cases requiring full control over output.
    """
    print(json.dumps(hook_output))
    sys.exit(0)


# ==================== Data Extraction Functions ====================


def get_file_path(tool_input: ToolInput) -> str:
    """
    Extract file path from tool input.

    Returns:
        File path string (empty if not present)

    Example:
        >>> file_path = get_file_path(tool_input)
        >>> if file_path.endswith(".py"):
        ...     validate_python_file(file_path)
    """
    return tool_input.get("file_path", "")


def get_command(tool_input: ToolInput) -> str:
    """
    Extract command from Bash tool input.

    Returns:
        Command string (empty if not present)

    Example:
        >>> command = get_command(tool_input)
        >>> if "rm -rf" in command:
        ...     output_block("Destructive command blocked")
    """
    return tool_input.get("command", "")


def was_tool_successful(tool_response: dict[str, object]) -> bool:
    """
    Check if tool execution succeeded.

    Parameters:
        tool_response: Tool response dictionary

    Returns:
        True if success, False otherwise

    Logic:
        Checks for 'success' field in tool_response.
        Returns tool_response.get("success", True) (default True if not present).

    Example:
        >>> if not was_tool_successful(tool_response):
        ...     # Tool failed, skip validation
        ...     output_feedback("")
        ...     return
    """
    return bool(tool_response.get("success", True))


def get_tool_response_field(
    tool_response: dict[str, object], field: str, default: object = None
) -> object:
    """
    Safely extract a field from tool_response.

    Parameters:
        tool_response: Tool response dictionary
        field: Field name to extract
        default: Default value if field not present

    Returns:
        Field value or default

    Example:
        >>> file_path = get_tool_response_field(tool_response, "filePath", "")
        >>> success = get_tool_response_field(tool_response, "success", True)
    """
    return tool_response.get(field, default)


# ==================== Validation Helper Functions ====================


def is_python_file(file_path: str) -> bool:
    """
    Check if file is a Python file.

    Returns:
        True if .py or .pyi extension

    Example:
        >>> if is_python_file(file_path):
        ...     run_python_validators(file_path)
    """
    return file_path.endswith(".py") or file_path.endswith(".pyi")


def is_within_project(file_path: str) -> bool:
    """
    Check if file is within project directory.

    Returns:
        True if file is within CLAUDE_PROJECT_DIR

    Security:
        Prevents path traversal attacks

    Example:
        >>> if not is_within_project(file_path):
        ...     output_feedback("Skipped: File outside project", suppress_output=True)
        ...     return
    """
    try:
        project_dir = get_project_dir()
        file_abs = Path(file_path).resolve()
        project_abs = project_dir.resolve()

        # Check if file_abs is relative to project_abs
        file_abs.relative_to(project_abs)
        return True
    except (ValueError, OSError):
        return False


def get_project_dir() -> Path:
    """
    Get absolute path to project directory.

    Returns:
        Path object for CLAUDE_PROJECT_DIR

    Example:
        >>> project_dir = get_project_dir()
        >>> config_file = project_dir / "pyproject.toml"
    """
    project_dir_str = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir_str)
