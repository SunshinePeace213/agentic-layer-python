#!/usr/bin/env python3
"""
Global Hook Utilities - Data Types
===================================

Common TypedDict definitions shared across all Claude Code hooks.

Usage:
    from hooks.utils.data_types import BaseHookInput, CommonFields

Dependencies:
    - Python 3.11+ (for typing.TypedDict)
"""

from typing import Literal, TypeAlias, TypedDict


# ==================== Common Base Types ====================


class CommonFields(TypedDict):
    """Fields common to all hook events."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str


class BaseHookInput(TypedDict):
    """Base input structure for all hooks (minimum required fields)."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str


# ==================== Type Aliases ====================
# Note: Type aliases use CapWords convention per typing best practices
# to distinguish them from regular variables


HookEventName: TypeAlias = Literal[
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
    "Notification",
]
"""All valid hook event names."""


ContinueDecision: TypeAlias = Literal["continue", "block"]
"""Decision for whether to continue or block execution."""


StopReason: TypeAlias = Literal["message", "error", "timeout", "user_interrupt"]
"""Possible reasons for stopping execution."""
