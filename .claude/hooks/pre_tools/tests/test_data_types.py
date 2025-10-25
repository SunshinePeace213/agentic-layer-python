#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
"""
Unit tests for data_types module.

Tests TypedDict definitions and type aliases for PreToolUse hooks.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_types import (
    ToolInput,
    HookInputData,
    HookSpecificOutput,
)


def test_tool_input_accepts_required_fields():
    """Test that ToolInput accepts required fields."""
    tool_input: ToolInput = {
        "file_path": "/path/to/file",
        "content": "file content"
    }
    assert tool_input["file_path"] == "/path/to/file"
    assert tool_input["content"] == "file content"


def test_tool_input_partial_dictionary():
    """Test that ToolInput allows partial dictionaries (total=False)."""
    tool_input: ToolInput = {"file_path": "/path/to/file"}
    assert "file_path" in tool_input
    assert "content" not in tool_input


def test_tool_input_extended_usage():
    """Test that hooks can extend ToolInput with additional fields via dict."""
    # Raw tool_input_obj from Claude Code can have any fields
    raw_tool_input: dict[str, str] = {
        "command": "ls -la",
        "file_path": "/path/to/file",
        "path": "/alternative/path",
        "content": "file content"
    }

    # Hooks access additional fields via .get()
    assert raw_tool_input.get("command") == "ls -la"
    assert raw_tool_input.get("path") == "/alternative/path"

    # Shared ToolInput only includes core fields
    typed_input: ToolInput = {
        "file_path": raw_tool_input["file_path"],
        "content": raw_tool_input["content"]
    }
    assert typed_input["file_path"] == "/path/to/file"


def test_hook_input_data_structure():
    """Test HookInputData structure is correct."""
    hook_data: HookInputData = {
        "session_id": "abc123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "test.py", "content": "..."}
    }
    assert hook_data["session_id"] == "abc123"
    assert hook_data["hook_event_name"] == "PreToolUse"
    assert hook_data["tool_name"] == "Write"


def test_hook_specific_output_structure():
    """Test HookSpecificOutput structure is correct."""
    hook_output: HookSpecificOutput = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": "Safe operation"
    }
    assert hook_output["hookEventName"] == "PreToolUse"
    assert hook_output["permissionDecision"] == "allow"
    assert hook_output["permissionDecisionReason"] == "Safe operation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
