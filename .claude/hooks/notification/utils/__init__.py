#!/usr/bin/env python3
"""
Notification Hook Utilities
============================

Public API for Notification hook utilities.

Exports:
    - Type definitions: NotificationInput, HookOutput, HookSpecificOutput
"""

from .data_types import (
    HookOutput,
    HookSpecificOutput,
    NotificationInput,
)

__all__ = [
    "NotificationInput",
    "HookOutput",
    "HookSpecificOutput",
]
