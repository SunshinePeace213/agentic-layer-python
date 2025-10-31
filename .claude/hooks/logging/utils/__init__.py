#!/usr/bin/env python3
"""
Logging Hook Utilities
=======================

Public API for universal hook logging utilities.

Exports:
    - Type definitions (UniversalHookInput, LogEntry, event-specific inputs)
    - Utility functions (parse, create, write)

Usage:
    from logging.utils import parse_universal_input, create_log_entry, write_log_entry
"""

from .data_types import (
    LogEntry,
    NotificationInput,
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UniversalHookInput,
    UserPromptSubmitInput,
)
from .utils import (
    create_log_entry,
    get_hook_event_name,
    parse_universal_input,
    write_log_entry,
)

__all__ = [
    # Data types
    "UniversalHookInput",
    "LogEntry",
    "PreToolUseInput",
    "PostToolUseInput",
    "UserPromptSubmitInput",
    "StopInput",
    "SubagentStopInput",
    "SessionStartInput",
    "SessionEndInput",
    "PreCompactInput",
    "NotificationInput",
    # Utility functions
    "parse_universal_input",
    "get_hook_event_name",
    "create_log_entry",
    "write_log_entry",
]
