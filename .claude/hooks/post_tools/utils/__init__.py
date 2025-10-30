#!/usr/bin/env python3
"""
Public API for PostToolUse Shared Utilities
============================================

This module exports the shared utilities and data types used by all
PostToolUse hooks in this category.

Exports:
    Type Definitions:
        - ToolInput: TypedDict for tool input parameters
        - ToolResponse: TypedDict for tool response data
        - HookOutput: TypedDict for hook output structure
        - HookSpecificOutput: TypedDict for PostToolUse output data
        - HookInputData: TypedDict for complete hook input

    Input Parsing:
        - parse_hook_input: Parse and validate hook input from stdin
        - parse_hook_input_minimal: Parse raw input without validation

    Output Functions:
        - output_feedback: Output feedback without blocking
        - output_block: Output blocking decision with reason
        - output_result: Output raw HookOutput

    Data Extraction:
        - get_file_path: Extract file path from tool input
        - get_command: Extract command from tool input
        - was_tool_successful: Check if tool succeeded
        - get_tool_response_field: Extract field from tool response

    Validation Helpers:
        - is_python_file: Check if file is Python
        - is_within_project: Check if file is within project
        - get_project_dir: Get project directory path

Usage:
    from utils import parse_hook_input, output_feedback, ToolInput

Version:
    1.0.0
"""

from .data_types import (
    HookInputData,
    HookOutput,
    HookSpecificOutput,
    ToolInput,
    ToolResponse,
)
from .utils import (
    get_command,
    get_file_path,
    get_project_dir,
    get_tool_response_field,
    is_python_file,
    is_within_project,
    output_block,
    output_feedback,
    output_result,
    parse_hook_input,
    parse_hook_input_minimal,
    was_tool_successful,
)

__all__ = [
    # Type definitions
    "ToolInput",
    "ToolResponse",
    "HookOutput",
    "HookSpecificOutput",
    "HookInputData",
    # Input parsing
    "parse_hook_input",
    "parse_hook_input_minimal",
    # Output functions
    "output_feedback",
    "output_block",
    "output_result",
    # Data extraction
    "get_file_path",
    "get_command",
    "was_tool_successful",
    "get_tool_response_field",
    # Validation helpers
    "is_python_file",
    "is_within_project",
    "get_project_dir",
]

__version__ = "1.0.0"
