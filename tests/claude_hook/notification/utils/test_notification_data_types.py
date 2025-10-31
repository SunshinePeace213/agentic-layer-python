#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for Notification Hook Data Types
========================================

Validates TypedDict definitions for Notification hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from notification.utils.data_types import (  # type: ignore[import-untyped]
    HookOutput,
    NotificationInput,
)


def test_notification_input_structure():
    """Test NotificationInput TypedDict structure."""
    notification: NotificationInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "Notification",
        "message": "Claude is waiting for your input",
    }
    assert notification["hook_event_name"] == "Notification"
    assert notification["message"] == "Claude is waiting for your input"


def test_hook_output_structure():
    """Test HookOutput structure for notifications."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "Notification",
            "additionalContext": "Voice alert triggered",
        },
        "suppressOutput": True,
    }
    assert output["hookSpecificOutput"]["hookEventName"] == "Notification"
    assert output["hookSpecificOutput"]["additionalContext"] == "Voice alert triggered"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
