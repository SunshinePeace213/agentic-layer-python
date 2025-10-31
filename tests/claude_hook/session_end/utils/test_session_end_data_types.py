#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for SessionEnd Hook Data Types
======================================

Validates TypedDict definitions for SessionEnd hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from session_end.utils.data_types import (  # type: ignore[import-untyped]
    HookOutput,
    SessionEndInput,
)


def test_session_end_input_structure():
    """Test SessionEndInput TypedDict structure."""
    end_input: SessionEndInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "SessionEnd",
    }
    assert end_input["session_id"] == "test_session_123"
    assert end_input["hook_event_name"] == "SessionEnd"


def test_hook_output_structure():
    """Test HookOutput structure for cleanup."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "SessionEnd",
            "additionalContext": "Cleanup completed successfully",
        },
        "suppressOutput": True,
    }
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionEnd"
    assert (
        output["hookSpecificOutput"]["additionalContext"]
        == "Cleanup completed successfully"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
