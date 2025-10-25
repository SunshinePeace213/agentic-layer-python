#!/usr/bin/env python3
"""
Shared Data Types for PreToolUse Hooks
=======================================

Centralized TypedDict definitions used across all PreToolUse hooks.
Ensures consistent input/output formats and type safety.

Usage:
    from .data_types import ToolInput, HookOutput, PermissionDecision

Type Safety:
    All TypedDict classes use total=False or total=True as appropriate
    to enforce correct usage patterns.

Dependencies:
    - Python 3.11+ (for typing.TypedDict)
    - No external packages required
"""

from typing import TypedDict, Literal

# ==================== Input Data Types ====================

class ToolInput(TypedDict, total=False):
    """
    Type definition for tool input parameters from Claude Code.

    This represents the SHARED fields used by the parse_hook_input() utility.
    Individual hooks may access additional fields directly from tool_input_obj.

    Uses total=False to allow partial dictionaries since different
    tools provide different sets of parameters.

    Attributes:
        file_path: File path (for Read/Write/Edit/MultiEdit tools)
        content: File content string (for Write tool)

    Note:
        Hooks that need additional fields (e.g., 'command' for Bash validation,
        'path' for Glob operations) should access them directly from the raw
        tool_input dict using .get(), or define their own extended TypedDict.

    Example:
        >>> tool_input: ToolInput = {
        ...     "file_path": "/path/to/file.py",
        ...     "content": "print('hello')"
        ... }
    """
    file_path: str
    content: str


class HookInputData(TypedDict):
    """
    Complete input data structure received by PreToolUse hooks via stdin.

    This represents the full JSON object sent by Claude Code to hooks.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Name of the hook event (always "PreToolUse" for these hooks)
        tool_name: Name of the Claude Code tool being invoked (e.g., "Bash", "Write")
        tool_input: Tool-specific input parameters (parsed into ToolInput)

    Example:
        >>> hook_data: HookInputData = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "PreToolUse",
        ...     "tool_name": "Write",
        ...     "tool_input": {"file_path": "test.py", "content": "..."}
        ... }
    """
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, str]  # Will be parsed into ToolInput


# ==================== Output Data Types ====================

class HookSpecificOutput(TypedDict):
    """
    PreToolUse-specific output structure for permission decisions.

    Attributes:
        hookEventName: Must be "PreToolUse" for this hook type
        permissionDecision: Whether to allow, deny, or ask user for permission
        permissionDecisionReason: Human-readable explanation of the decision
    """
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for PreToolUse hooks.

    Uses total=False because suppressOutput is optional.

    Attributes:
        hookSpecificOutput: Required permission decision data
        suppressOutput: Optional flag to hide output in Claude Code transcript mode
    """
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


# ==================== Type Aliases ====================

PermissionDecision = Literal["allow", "deny", "ask"]
"""Type alias for permission decisions."""

ValidationResult = str | None
"""Type alias for validation function results (None = passed, str = error message)."""
