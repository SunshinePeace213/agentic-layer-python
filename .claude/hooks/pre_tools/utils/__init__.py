#!/usr/bin/env python3
"""
Public API for PreToolUse Shared Utilities
===========================================

This module exports the shared utilities and data types used by all
PreToolUse hooks in this category.

Exports:
    - ToolInput: TypedDict for tool input parameters
    - HookOutput: TypedDict for hook output structure
    - HookSpecificOutput: TypedDict for permission decision data
    - PermissionDecision: Type alias for permission decisions
    - ValidationResult: Type alias for validation results
    - parse_hook_input: Parse and validate hook input from stdin
    - output_decision: Output formatted JSON decision and exit
    - get_file_path: Extract file path from tool input

Usage:
    from utils import parse_hook_input, output_decision, ToolInput
"""

from .data_types import (
    ToolInput,
    HookOutput,
    HookSpecificOutput,
    PermissionDecision,
    ValidationResult,
)
from .utils import (
    parse_hook_input,
    output_decision,
    get_file_path,
)

__all__ = [
    "ToolInput",
    "HookOutput",
    "HookSpecificOutput",
    "PermissionDecision",
    "ValidationResult",
    "parse_hook_input",
    "output_decision",
    "get_file_path",
]
