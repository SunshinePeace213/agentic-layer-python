#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for Global Hook Utilities Data Types
===========================================

Validates TypedDict definitions and type aliases for common hook types.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from utils.data_types import (  # type: ignore[import-untyped]
    BaseHookInput,
    CommonFields,
    ContinueDecision,
    HookEventName,
    StopReason,
)


def test_common_fields_structure():
    """Test CommonFields TypedDict structure."""
    fields: CommonFields = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "PreToolUse",
    }
    assert fields["session_id"] == "test123"
    assert fields["transcript_path"] == "/path/to/transcript.jsonl"
    assert fields["cwd"] == "/project/root"
    assert fields["hook_event_name"] == "PreToolUse"


def test_base_hook_input_structure():
    """Test BaseHookInput TypedDict structure."""
    hook_input: BaseHookInput = {
        "session_id": "abc123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/current/dir",
        "hook_event_name": "Stop",
    }
    assert hook_input["session_id"] == "abc123"
    assert hook_input["hook_event_name"] == "Stop"


def test_hook_event_name_type_alias():
    """Test HookEventName type alias accepts valid values."""
    valid_names: list[HookEventName] = [
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "Stop",
        "SubagentStop",
        "PreCompact",
        "SessionStart",
        "SessionEnd",
        "Notification",
    ]
    assert len(valid_names) == 9


def test_continue_decision_type_alias():
    """Test ContinueDecision type alias accepts valid values."""
    decision_continue: ContinueDecision = "continue"
    decision_block: ContinueDecision = "block"
    assert decision_continue == "continue"
    assert decision_block == "block"


def test_stop_reason_type_alias():
    """Test StopReason type alias accepts valid values."""
    valid_reasons: list[StopReason] = [
        "message",
        "error",
        "timeout",
        "user_interrupt",
    ]
    assert len(valid_reasons) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
