#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
Tests for PreCompact Hook Data Types
======================================

Validates TypedDict definitions for PreCompact hook events.
"""

import sys
from pathlib import Path

import pytest

# Add .claude/hooks to path for imports
hooks_path = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_path))

from pre_compact.utils.data_types import (  # type: ignore[import-untyped]
    CompactType,
    HookOutput,
    PreCompactInput,
)


def test_pre_compact_input_manual():
    """Test PreCompactInput with manual compact_type."""
    compact_input: PreCompactInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "PreCompact",
        "compact_type": "manual",
    }
    assert compact_input["compact_type"] == "manual"
    assert compact_input["hook_event_name"] == "PreCompact"


def test_pre_compact_input_auto():
    """Test PreCompactInput with auto compact_type."""
    compact_input: PreCompactInput = {
        "session_id": "test_session_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "PreCompact",
        "compact_type": "auto",
    }
    assert compact_input["compact_type"] == "auto"


def test_compact_type_values():
    """Test CompactType accepts valid values."""
    manual: CompactType = "manual"
    auto: CompactType = "auto"
    assert manual == "manual"
    assert auto == "auto"


def test_hook_output_allow_compaction():
    """Test HookOutput for allowing compaction."""
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": "Backup saved",
        },
        "suppressOutput": True,
    }
    assert "decision" not in output
    assert output["hookSpecificOutput"]["hookEventName"] == "PreCompact"


def test_hook_output_block_compaction():
    """Test HookOutput for blocking compaction."""
    output: HookOutput = {
        "decision": "block",
        "reason": "Important debugging context in progress",
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": "Complete current task first",
        },
    }
    assert output["decision"] == "block"
    assert output["reason"] == "Important debugging context in progress"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
