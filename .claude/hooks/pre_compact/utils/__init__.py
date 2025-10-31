#!/usr/bin/env python3
"""
PreCompact Hook Utilities
==========================

Public API for PreCompact hook utilities.

Exports:
    - Type definitions: PreCompactInput, HookOutput, HookSpecificOutput, CompactType
"""

from .data_types import (
    CompactType,
    HookOutput,
    HookSpecificOutput,
    PreCompactInput,
)

__all__ = [
    "PreCompactInput",
    "HookOutput",
    "HookSpecificOutput",
    "CompactType",
]
