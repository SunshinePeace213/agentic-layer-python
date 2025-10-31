#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for Stop Hook Data Types
================================

Validates TypedDict definitions for Stop hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from stop.utils.data_types import (  # type: ignore[import-untyped]
    HookOutput,
    HookSpecificOutput,
    StopInput,
)


def test_stop_input_structure():
    """Test StopInput TypedDict structure."""
    stop_input: StopInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "Stop",
    }
    assert stop_input["session_id"] == "test_session_123"
    assert stop_input["hook_event_name"] == "Stop"
    assert stop_input["cwd"] == "/project/root"


def test_hook_specific_output_structure():
    """Test HookSpecificOutput structure."""
    output: HookSpecificOutput = {
        "hookEventName": "Stop",
        "additionalContext": "Session metrics logged",
    }
    assert output["hookEventName"] == "Stop"
    assert output["additionalContext"] == "Session metrics logged"


def test_hook_output_non_blocking():
    """Test HookOutput for non-blocking scenario."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "Completed successfully",
        },
        "suppressOutput": True,
    }
    assert output["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert output["suppressOutput"] is True


def test_hook_output_blocking():
    """Test HookOutput for blocking scenario."""
    output: HookOutput = {
        "decision": "block",
        "reason": "Critical validation failed",
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "Review errors",
        },
    }
    assert output["decision"] == "block"
    assert output["reason"] == "Critical validation failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
