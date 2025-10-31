#!/usr/bin/env python3
"""
Logging Hook Utilities - Data Types
====================================

TypedDict definitions for universal hook logging across all events.

Usage:
    from logging.utils.data_types import UniversalHookInput, LogEntry

Dependencies:
    - Python 3.11+ (for typing.TypedDict)
    - No external packages required
"""

from typing import Literal, TypeAlias, TypedDict, Union


# ==================== Event-Specific Input Types ====================


class PreToolUseInput(TypedDict):
    """PreToolUse hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, object]


class PostToolUseInput(TypedDict):
    """PostToolUse hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, object]
    tool_response: dict[str, object]


class UserPromptSubmitInput(TypedDict):
    """UserPromptSubmit hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["UserPromptSubmit"]
    prompt: str


class StopInput(TypedDict):
    """Stop hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["Stop"]


class SubagentStopInput(TypedDict):
    """SubagentStop hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SubagentStop"]


class SessionStartInput(TypedDict, total=False):
    """SessionStart hook input structure.

    Uses total=False because claude_env_file is optional.

    Required fields:
        session_id: Session identifier
        transcript_path: Path to transcript file
        cwd: Current working directory
        hook_event_name: Event name ("SessionStart")
        start_type: Type of session start

    Optional fields:
        claude_env_file: Path to environment file (may not be present)
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SessionStart"]
    start_type: Literal["startup", "resume", "clear", "compact"]
    claude_env_file: str


class SessionEndInput(TypedDict):
    """SessionEnd hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SessionEnd"]


class PreCompactInput(TypedDict):
    """PreCompact hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PreCompact"]
    compact_type: Literal["manual", "auto"]


class NotificationInput(TypedDict):
    """Notification hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["Notification"]
    notification_type: str
    notification_data: dict[str, object]


# ==================== Universal Type Union ====================


UniversalHookInput: TypeAlias = Union[
    PreToolUseInput,
    PostToolUseInput,
    UserPromptSubmitInput,
    StopInput,
    SubagentStopInput,
    SessionStartInput,
    SessionEndInput,
    PreCompactInput,
    NotificationInput,
]
"""Union type representing any possible hook event input."""


# ==================== Log Entry Types ====================


class LogEntry(TypedDict):
    """
    Enriched log entry structure written to JSONL files.

    Attributes:
        timestamp: ISO 8601 timestamp when log entry was created
        payload: Complete hook input data (full payload)
    """

    timestamp: str
    payload: UniversalHookInput
