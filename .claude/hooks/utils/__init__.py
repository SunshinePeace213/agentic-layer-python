#!/usr/bin/env python3
"""
Global Hook Utilities
=====================

Public API for utilities shared across all Claude Code hooks.

Exports:
    - Common type definitions
    - Shared constants

Usage:
    from hooks.utils import BaseHookInput, HookEventName
"""

from .data_types import (
    BaseHookInput,
    CommonFields,
    ContinueDecision,
    HookEventName,
    StopReason,
)

__all__ = [
    "BaseHookInput",
    "CommonFields",
    "ContinueDecision",
    "HookEventName",
    "StopReason",
]
