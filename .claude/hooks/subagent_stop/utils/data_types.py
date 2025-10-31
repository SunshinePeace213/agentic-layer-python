#!/usr/bin/env python3
"""
SubagentStop Hook Data Types
=============================

TypedDict definitions for SubagentStop hook events.

The SubagentStop event triggers when a subagent (Task tool) completes.
This is useful for:
- Tracking subagent performance
- Aggregating subagent results
- Debugging subagent behavior
- Usage metrics

Usage:
    from subagent_stop.utils.data_types import SubagentStopInput, HookOutput

Dependencies:
    - Python 3.11+
"""

from typing import Literal, TypedDict


# ==================== Input Data Types ====================


class SubagentStopInput(TypedDict):
    """
    Input data structure received by SubagentStop hooks via stdin.

    Attributes:
        session_id: Unique identifier for the Claude Code session
        transcript_path: Absolute path to the session transcript JSONL file
        cwd: Current working directory when hook is invoked
        hook_event_name: Always "SubagentStop" for this hook type
        subagent_id: Unique identifier for the subagent that stopped

    Example:
        >>> hook_data: SubagentStopInput = {
        ...     "session_id": "abc123",
        ...     "transcript_path": "/path/to/transcript.jsonl",
        ...     "cwd": "/project/root",
        ...     "hook_event_name": "SubagentStop",
        ...     "subagent_id": "subagent_xyz"
        ... }
    """

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["SubagentStop"]
    subagent_id: str


# ==================== Output Data Types ====================


class HookSpecificOutput(TypedDict, total=False):
    """
    SubagentStop-specific output structure.

    Attributes:
        hookEventName: Must be "SubagentStop" for this hook type (Required)
        additionalContext: Additional information for Claude (Optional)

    Example:
        >>> hook_specific: HookSpecificOutput = {
        ...     "hookEventName": "SubagentStop",
        ...     "additionalContext": "Subagent completed successfully"
        ... }
    """

    hookEventName: Literal["SubagentStop"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """
    Complete output structure for SubagentStop hooks.

    Uses total=False because all fields are optional.

    Attributes:
        decision: Whether to block continuation (Optional, at TOP LEVEL)
        reason: Explanation for the decision (Optional, at TOP LEVEL)
        hookSpecificOutput: Event-specific output data (Optional)
        suppressOutput: Flag to hide output in transcript mode (Optional)

    Example:
        >>> output: HookOutput = {
        ...     "hookSpecificOutput": {
        ...         "hookEventName": "SubagentStop",
        ...         "additionalContext": "Metrics logged"
        ...     },
        ...     "suppressOutput": True
        ... }
    """

    decision: Literal["block"]
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool
