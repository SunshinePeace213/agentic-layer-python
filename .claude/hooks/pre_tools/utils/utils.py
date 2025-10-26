#!/usr/bin/env python3
"""
Shared Utilities for PreToolUse Hooks
======================================

Common utility functions for PreToolUse hooks.
"""

import json
import sys
from typing import Literal, Optional, Tuple, cast

try:
    from .data_types import ToolInput
except ImportError:
    from data_types import ToolInput

def parse_hook_input() -> Optional[Tuple[str, ToolInput]]:
    """Parse and validate hook input from stdin."""
    input_text = sys.stdin.read()
    # json.loads returns Any, but we know it's a dict at runtime
    parsed_json = cast(dict[str, object], json.loads(input_text))

    # Extract and validate tool_name
    tool_name_obj = parsed_json.get("tool_name", "")
    tool_name = str(tool_name_obj) if isinstance(tool_name_obj, str) else ""

    # Extract and validate tool_input
    tool_input_obj = parsed_json.get("tool_input", {})
    if not isinstance(tool_input_obj, dict):
        tool_input_obj = {}

    typed_tool_input = ToolInput()

    # Validate file_path is a string before adding
    if "file_path" in tool_input_obj:
        file_path_val: object = tool_input_obj["file_path"]  # type: ignore[reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val

    # Validate content is a string before adding
    if "content" in tool_input_obj:
        content_val: object = tool_input_obj["content"]  # type: ignore[reportUnknownVariableType]
        if isinstance(content_val, str):
            typed_tool_input["content"] = content_val

    # Validate command is a string before adding
    if "command" in tool_input_obj:
        command_val: object = tool_input_obj["command"]  # type: ignore[reportUnknownVariableType]
        if isinstance(command_val, str):
            typed_tool_input["command"] = command_val

    return (tool_name, typed_tool_input)


def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False
) -> None:
    """Output a properly formatted JSON decision and exit."""
    try:
        from .data_types import HookOutput
    except ImportError:
        from data_types import HookOutput
        
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }

    if suppress_output:
        output["suppressOutput"] = True

    print(json.dumps(output))
    sys.exit(0)


def get_file_path(tool_input: ToolInput) -> str:
    """Extract file path from tool input."""
    return tool_input.get("file_path", "")
