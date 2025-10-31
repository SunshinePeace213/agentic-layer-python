#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for SessionStart Hook Data Types
========================================

Validates TypedDict definitions for SessionStart hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from session_start.utils.data_types import (  # type: ignore[import-untyped]
    HookOutput,
    SessionStartInput,
    SessionStartType,
)


def test_session_start_input_startup():
    """Test SessionStartInput with startup type."""
    start_input: SessionStartInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "SessionStart",
        "start_type": "startup",
        "claude_env_file": "/tmp/claude_env_test123",
    }
    assert start_input["start_type"] == "startup"
    assert start_input["hook_event_name"] == "SessionStart"


def test_session_start_type_values():
    """Test SessionStartType accepts all valid values."""
    startup: SessionStartType = "startup"
    resume: SessionStartType = "resume"
    clear: SessionStartType = "clear"
    compact: SessionStartType = "compact"

    assert startup == "startup"
    assert resume == "resume"
    assert clear == "clear"
    assert compact == "compact"


def test_hook_output_with_context_injection():
    """Test HookOutput for context injection."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "Project uses React 18 with TypeScript",
        },
        "suppressOutput": True,
    }
    assert (
        output["hookSpecificOutput"]["additionalContext"]
        == "Project uses React 18 with TypeScript"
    )
    assert output["suppressOutput"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
