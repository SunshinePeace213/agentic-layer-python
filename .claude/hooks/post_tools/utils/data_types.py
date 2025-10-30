#!/usr/bin/env python3
"""
Shared Data Types for PostToolUse Hooks
========================================

Centralized TypedDict definitions used across all PostToolUse hooks.
Ensures consistent input/output formats and type safety.

Usage:
    from .data_types import ToolInput, HookOutput, post_tool_decision

Type Safety:
    All TypedDict classes use total=False or total=True as appropriate
    to enforce correct usage patterns.

Dependencies:
    - Python 3.12+ (for improved typing features)
    - No external packages required
"""

from typing import Literal, TypedDict

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
        command: Shell command string (for Bash tool)
        old_string: String to replace (for Edit tool)
        new_string: Replacement string (for Edit tool)
        replace_all: Replace all occurrences flag (for Edit tool)
        pattern: Glob pattern (for Glob tool)
        path: Search path (for Glob/Grep tools)

    Note:
        Hooks that need additional fields should access them directly
        from the raw tool_input dict using .get(), or define their own
        extended TypedDict.

    Example:
        >>> # Write operation
        >>> tool_input: ToolInput = {
        ...     "file_path": "/path/to/file.py",
        ...     "content": "print('hello')"
        ... }
        >>> # Edit operation
        >>> tool_input: ToolInput = {
        ...     "file_path": "/path/to/file.py",
        ...     "old_string": "old text",
        ...     "new_string": "new text",
        ...     "replace_all": False
        ... }
        >>> # Bash operation
        >>> tool_input: ToolInput = {
        ...     "command": "echo hello"
        ... }
    """

    file_path: str
    content: str
    command: str
    old_string: str
    new_string: str
    replace_all: bool
    pattern: str
    path: str


class ToolResponse(TypedDict, total=False):
    """
    Type definition for tool response from tool execution.

    This represents the response returned by Claude Code tools after execution.
    Structure varies by tool type.

    Uses total=False because different tools return different response structures.

    Attributes:
        filePath: File path (Write/Edit tools)
        success: Success status (Write/Edit tools)

    Note:
        Different tools return different response structures.
        Always check for expected fields with .get() and provide defaults.
        Use get_tool_response_field() helper for safe field extraction.

    Example:
        >>> # Write tool response
        >>> tool_response: ToolResponse = {
        ...     "filePath": "/path/to/file.py",
        ...     "success": True
        ... }
        >>> # Some tools may return minimal or different structures
        >>> tool_response: ToolResponse = {}
    """

    filePath: str
    success: bool


class HookInputData(TypedDict):
    """
    Complete input data structure received by PostToolUse hooks via stdin.

    This represents the full JSON object sent by Claude Code to hooks.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Name of the hook event (always "PostToolUse" for these hooks)
        tool_name: Name of the Claude Code tool that was executed (e.g., "Bash", "Write")
        tool_input: Tool-specific input parameters (parse into ToolInput)
        tool_response: Tool execution response (parse into ToolResponse)

    Key Difference from PreToolUse:
        PostToolUse includes tool_response (result of tool execution) instead of
        tool_output/tool_error. The hook runs AFTER tool completes.

    Example:
        >>> hook_data: HookInputData = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "PostToolUse",
        ...     "tool_name": "Write",
        ...     "tool_input": {"file_path": "test.py", "content": "..."},
        ...     "tool_response": {"filePath": "test.py", "success": True}
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, object]  # Dynamic structure varies by tool
    tool_response: dict[str, object]  # Dynamic structure varies by tool


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    PostToolUse-specific output structure.

    Attributes:
        hookEventName: Must be "PostToolUse" for this hook type (Required)
        additionalContext: Additional information for Claude (Optional)

    Note:
        In PostToolUse, this structure is much simpler than PreToolUse.
        The decision and reason fields are at the TOP LEVEL of HookOutput,
        not inside hookSpecificOutput.

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "PostToolUse",
        ...     "additionalContext": "Validation passed with 3 warnings"
        ... }
    """

    hookEventName: Literal["PostToolUse"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for PostToolUse hooks.

    Uses total=False because all top-level fields are optional.

    Attributes:
        decision: Whether to block Claude's continuation (Optional, at TOP LEVEL)
        reason: Explanation for the decision (Optional, at TOP LEVEL)
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in Claude Code transcript mode (Optional)

    Key Differences from PreToolUse:
        - decision and reason are at TOP LEVEL (not inside hookSpecificOutput)
        - decision is "block" or omitted (not "allow"/"deny"/"ask")
        - hookSpecificOutput only contains hookEventName and additionalContext
        - All fields are optional (total=False)

    Decision Field Semantics:
        - Omitted/undefined: Non-blocking (default)
        - "block": Block Claude's continuation (rare, for critical issues)

    Example (Non-blocking feedback):
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "PostToolUse",
        ...         "additionalContext": "File validated successfully"
        ...     },
        ...     "suppressOutput": True
        ... }

    Example (Blocking with reason):
        >>> output: HookOutput = {
        ...     "decision": "block",
        ...     "reason": "Type checking failed with 5 errors",
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "PostToolUse",
        ...         "additionalContext": "Run: basedpyright file.py"
        ...     },
        ...     "suppressOutput": True
        ... }
    """

    decision: Literal["block"]
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
