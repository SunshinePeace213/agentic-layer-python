#!/usr/bin/env python3
"""
Shared Data Types for UserPromptSubmit Hooks
=============================================

Centralized TypedDict definitions used across all UserPromptSubmit hooks.
Ensures consistent input/output formats and type safety.

Usage:
    from .data_types import UserPromptSubmitInput, HookOutput

Type Safety:
    All TypedDict classes use total=False or total=True as appropriate
    to enforce correct usage patterns.

Dependencies:
    - Python 3.11+ (for improved typing features)
    - No external packages required
"""

from typing import Literal, TypedDict


# ==================== Input Data Types ====================


class UserPromptSubmitInput(TypedDict):
    """
    Complete input data structure received by UserPromptSubmit hooks via stdin.

    This represents the full JSON object sent by Claude Code to hooks.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Name of the hook event (always "UserPromptSubmit")
        prompt: User's submitted prompt text

    Example:
        >>> hook_data: UserPromptSubmitInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "UserPromptSubmit",
        ...     "prompt": "Add a new feature to handle user authentication"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    UserPromptSubmit-specific output structure.

    Attributes:
        hookEventName: Must be "UserPromptSubmit" for this hook type (Required)
        additionalContext: Additional information for Claude (Optional)

    Note:
        In UserPromptSubmit, the decision and reason fields are at the TOP LEVEL
        of HookOutput, not inside hookSpecificOutput.

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "UserPromptSubmit",
        ...     "additionalContext": "Prompt validated successfully"
        ... }
    """

    hookEventName: Literal["UserPromptSubmit"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for UserPromptSubmit hooks.

    Uses total=False because all top-level fields are optional.

    Attributes:
        decision: Whether to block the prompt (Optional, at TOP LEVEL)
        reason: Explanation for the decision (Optional, at TOP LEVEL)
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in Claude Code transcript mode (Optional)

    Decision Field Semantics:
        - Omitted/undefined: Non-blocking (default)
        - "block": Block the prompt from being processed

    Example (Non-blocking feedback):
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "UserPromptSubmit",
        ...         "additionalContext": "Prompt context enhanced"
        ...     },
        ...     "suppressOutput": True
        ... }

    Example (Blocking with reason):
        >>> output: HookOutput = {
        ...     "decision": "block",
        ...     "reason": "Prompt contains sensitive information",
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "UserPromptSubmit",
        ...         "additionalContext": "Remove API keys before submitting"
        ...     },
        ...     "suppressOutput": False
        ... }
    """

    decision: Literal["block"]
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
