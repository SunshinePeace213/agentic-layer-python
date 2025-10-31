#!/usr/bin/env python3
"""
Stop Hook Data Types
====================

TypedDict definitions for Stop hook events.

The Stop event triggers when the main Claude Code agent finishes responding,
but NOT when the user interrupts. This is useful for:
- Session cleanup
- Final validation checks
- Usage tracking
- Performance metrics

Usage:
    from stop.utils.data_types import StopInput, HookOutput

Dependencies:
    - Python 3.11+
"""

from typing import Literal, TypedDict


# ==================== Input Data Types ====================


class StopInput(TypedDict):
    """
    Input data structure received by Stop hooks via stdin.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Always "Stop" for this hook type

    Example:
        >>> hook_data: StopInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "Stop"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["Stop"]


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    Stop-specific output structure.

    Attributes:
        hookEventName: Must be "Stop" for this hook type (Required)
        additionalContext: Additional information for Claude (Optional)

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "Stop",
        ...     "additionalContext": "Session metrics logged"
        ... }
    """

    hookEventName: Literal["Stop"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for Stop hooks.

    Uses total=False because all fields are optional.

    Attributes:
        decision: Whether to block continuation (Optional, at TOP LEVEL)
        reason: Explanation for the decision (Optional, at TOP LEVEL)
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in transcript mode (Optional)

    Decision Field Semantics:
        - Omitted: Non-blocking (default)
        - "block": Block continuation (rare, for critical issues)

    Example (Non-blocking):
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "Stop",
        ...         "additionalContext": "Session completed successfully"
        ...     },
        ...     "suppressOutput": True
        ... }

    Example (Blocking):
        >>> output: HookOutput = {
        ...     "decision": "block",
        ...     "reason": "Critical validation failed",
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "Stop",
        ...         "additionalContext": "Review errors before continuing"
        ...     }
        ... }
    """

    decision: Literal["block"]
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
