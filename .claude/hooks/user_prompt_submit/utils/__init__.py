"""
UserPromptSubmit Hooks Utilities
=================================

Public API for UserPromptSubmit hook utilities.

Exports:
    - Type definitions: UserPromptSubmitInput, HookOutput, HookSpecificOutput
    - Utility functions: (to be added in future as needed)

Usage:
    from user_prompt_submit.utils import UserPromptSubmitInput, HookOutput
"""

from .data_types import (
    HookOutput,
    HookSpecificOutput,
    UserPromptSubmitInput,
)

__all__ = [
    "UserPromptSubmitInput",
    "HookOutput",
    "HookSpecificOutput",
]
