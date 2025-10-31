#!/usr/bin/env python3
"""
SessionStart Hook Data Types
=============================

TypedDict definitions for SessionStart hook events.

The SessionStart event triggers during session initialization.
Matchers: "startup", "resume", "clear", or "compact"

This is useful for:
- Loading session-specific configuration
- Setting environment variables via CLAUDE_ENV_FILE
- Initializing project state
- Restoring session context

Usage:
    from session_start.utils.data_types import SessionStartInput, HookOutput

Dependencies:
    - Python 3.11+
"""

from typing import Literal, TypeAlias, TypedDict


# ==================== Input Data Types ====================


SessionStartType: TypeAlias = Literal["startup", "resume", "clear", "compact"]
"""Type of session start operation."""


class SessionStartInput(TypedDict):
    """
    Input data structure received by SessionStart hooks via stdin.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Always "SessionStart" for this hook type
        start_type: Type of session start
        claude_env_file: Path for persisting environment variables (Optional)

    Example:
        >>> hook_data: SessionStartInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "SessionStart",
        ...     "start_type": "startup",
        ...     "claude_env_file": "/tmp/claude_env_abc123"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SessionStart"]
    start_type: SessionStartType
    claude_env_file: str  # Optional in practice, but defined in TypedDict


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    SessionStart-specific output structure.

    Attributes:
        hookEventName: Must be "SessionStart" for this hook type (Required)
        additionalContext: Additional context to inject into session (Optional)

    Note:
        SessionStart hooks can inject context via additionalContext field.
        This context becomes part of the initial system prompt.

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "SessionStart",
        ...     "additionalContext": "Project uses React 18 with TypeScript"
        ... }
    """

    hookEventName: Literal["SessionStart"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for SessionStart hooks.

    Uses total=False because all fields are optional.

    Attributes:
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in transcript mode (Optional)

    Note:
        SessionStart hooks typically do NOT use decision/reason fields
        since they cannot block session initialization.
        Use additionalContext to inject session context.

    Example (Context injection):
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "SessionStart",
        ...         "additionalContext": "Session initialized with custom config"
        ...     },
        ...     "suppressOutput": True
        ... }
    """

    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
