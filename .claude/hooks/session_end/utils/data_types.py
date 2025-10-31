#!/usr/bin/env python3
"""
SessionEnd Hook Data Types
===========================

TypedDict definitions for SessionEnd hook events.

The SessionEnd event triggers during session termination.
This hook CANNOT block termination but can perform cleanup.

This is useful for:
- Cleanup operations
- Final session logging
- Saving session metrics
- Releasing resources

Usage:
    from session_end.utils.data_types import SessionEndInput, HookOutput

Dependencies:
    - Python 3.11+
"""

from typing import Literal, TypedDict


# ==================== Input Data Types ====================


class SessionEndInput(TypedDict):
    """
    Input data structure received by SessionEnd hooks via stdin.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Always "SessionEnd" for this hook type

    Example:
        >>> hook_data: SessionEndInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "SessionEnd"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SessionEnd"]


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    SessionEnd-specific output structure.

    Attributes:
        hookEventName: Must be "SessionEnd" for this hook type (Required)
        additionalContext: Additional information for logging (Optional)

    Note:
        SessionEnd hooks CANNOT block termination.
        Output is primarily for logging purposes.

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "SessionEnd",
        ...     "additionalContext": "Session cleanup completed"
        ... }
    """

    hookEventName: Literal["SessionEnd"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for SessionEnd hooks.

    Uses total=False because all fields are optional.

    Attributes:
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in transcript mode (Optional)

    Note:
        SessionEnd hooks CANNOT use decision/reason to block termination.
        The session will terminate regardless of hook output.

    Example:
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "SessionEnd",
        ...         "additionalContext": "Cleanup completed successfully"
        ...     },
        ...     "suppressOutput": True
        ... }
    """

    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
