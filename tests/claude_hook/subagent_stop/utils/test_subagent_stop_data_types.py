#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for SubagentStop Hook Data Types
========================================

Validates TypedDict definitions for SubagentStop hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from subagent_stop.utils.data_types import (  # type: ignore[import-untyped]
    HookOutput,
    HookSpecificOutput,
    SubagentStopInput,
)


def test_subagent_stop_input_structure():
    """Test SubagentStopInput TypedDict structure."""
    subagent_input: SubagentStopInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "SubagentStop",
        "subagent_id": "subagent_xyz789",
    }
    assert subagent_input["session_id"] == "test_session_123"
    assert subagent_input["hook_event_name"] == "SubagentStop"
    assert subagent_input["subagent_id"] == "subagent_xyz789"


def test_hook_specific_output_structure():
    """Test HookSpecificOutput structure."""
    output: HookSpecificOutput = {
        "hookEventName": "SubagentStop",
        "additionalContext": "Subagent completed successfully",
    }
    assert output["hookEventName"] == "SubagentStop"
    assert output["additionalContext"] == "Subagent completed successfully"


def test_hook_output_structure():
    """Test HookOutput structure."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": "Metrics logged",
        },
        "suppressOutput": True,
    }
    assert output["hookSpecificOutput"]["hookEventName"] == "SubagentStop"
    assert output["suppressOutput"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
