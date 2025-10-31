#!/usr/bin/env python3
"""
Notification Hook Data Types
=============================

TypedDict definitions for Notification hook events.

The Notification event triggers when Claude sends notifications such as:
- Permission requests
- Input idle timeouts
- System messages

This is useful for:
- User alerts (audio, visual)
- Logging notification history
- Custom notification handling
- Integration with external systems

Usage:
    from notification.utils.data_types import NotificationInput, HookOutput

Dependencies:
    - Python 3.11+
"""

from typing import Literal, TypedDict


# ==================== Input Data Types ====================


class NotificationInput(TypedDict):
    """
    Input data structure received by Notification hooks via stdin.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Always "Notification" for this hook type
        message: The notification message text

    Example:
        >>> hook_data: NotificationInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "Notification",
        ...     "message": "Claude is waiting for your input"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["Notification"]
    message: str


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    Notification-specific output structure.

    Attributes:
        hookEventName: Must be "Notification" for this hook type (Required)
        additionalContext: Additional information (Optional)

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "Notification",
        ...     "additionalContext": "Voice alert triggered"
        ... }
    """

    hookEventName: Literal["Notification"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for Notification hooks.

    Uses total=False because all fields are optional.

    Attributes:
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in transcript mode (Optional)

    Note:
        Notification hooks typically do NOT block (no decision field).
        They are primarily for logging and user alerts.

    Example:
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "Notification",
        ...         "additionalContext": "Notification logged"
        ...     },
        ...     "suppressOutput": True
        ... }
    """

    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
