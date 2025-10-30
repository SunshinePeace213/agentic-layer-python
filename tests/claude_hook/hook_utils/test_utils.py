#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
"""
Unit tests for utils module.

Tests utility functions for PreToolUse hooks.
"""

import json
from io import StringIO
from typing import cast
from unittest.mock import patch
import pytest

from utils.utils import parse_hook_input, output_decision, get_file_path
from utils.data_types import ToolInput


def test_parse_hook_input_valid():
    """Test parsing valid hook input."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/test.py", "content": "print('hi')"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Write"
    assert tool_input.get("file_path") == "/test.py"
    assert tool_input.get("content") == "print('hi')"


def test_output_decision_allow():
    """Test output_decision with allow."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            output_decision("allow", "Test reason")
        assert exc_info.value.code == 0

        output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
        hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
        assert hook_specific["permissionDecision"] == "allow"
        assert hook_specific["permissionDecisionReason"] == "Test reason"
        assert "suppressOutput" not in output


def test_output_decision_with_suppress_output():
    """Test output_decision with suppress_output=True."""
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            output_decision("deny", "Test reason", suppress_output=True)
        assert exc_info.value.code == 0

        output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
        hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
        assert hook_specific["permissionDecision"] == "deny"
        assert output["suppressOutput"] is True


# def test_output_decision_logs_decision():
#     """Test that output_decision logs the permission decision."""
#     with patch('sys.stdout', new_callable=StringIO):
#         with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
#             with pytest.raises(SystemExit):
#                 output_decision("deny", "Security violation detected")

#             stderr_output = mock_stderr.getvalue()
#             assert "deny" in stderr_output or "Security violation" in stderr_output


def test_get_file_path_from_file_path():
    """Test get_file_path extracts from file_path field."""
    tool_input: ToolInput = {"file_path": "/path/to/file"}
    assert get_file_path(tool_input) == "/path/to/file"


def test_parse_hook_input_with_non_string_values():
    """Test parse_hook_input filters out non-string values in tool_input."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": 123,  # Non-string value
            "content": ["invalid", "list"],  # Non-string value
            "other_field": None
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Write"
    # Non-string values should be filtered out
    assert "file_path" not in tool_input
    assert "content" not in tool_input


def test_parse_hook_input_extracts_command():
    """Test parse_hook_input extracts command field for Bash tool."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Bash"
    assert tool_input.get("command") == "echo hello"


def test_parse_hook_input_extracts_edit_tool_parameters():
    """Test parse_hook_input extracts Edit tool parameters (old_string, new_string, replace_all)."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/path/to/file.py",
            "old_string": "old text",
            "new_string": "new text",
            "replace_all": False
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Edit"
    assert tool_input.get("file_path") == "/path/to/file.py"
    assert tool_input.get("old_string") == "old text"
    assert tool_input.get("new_string") == "new text"
    assert tool_input.get("replace_all") is False


def test_parse_hook_input_edit_tool_with_replace_all_true():
    """Test parse_hook_input extracts Edit tool parameters with replace_all=True."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/path/to/file.py",
            "old_string": "old_func",
            "new_string": "new_func",
            "replace_all": True
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Edit"
    assert tool_input.get("replace_all") is True


def test_parse_hook_input_edit_tool_without_replace_all():
    """Test parse_hook_input handles Edit tool without replace_all parameter."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/path/to/file.py",
            "old_string": "old text",
            "new_string": "new text"
            # replace_all is optional, not included
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Edit"
    assert tool_input.get("file_path") == "/path/to/file.py"
    assert tool_input.get("old_string") == "old text"
    assert tool_input.get("new_string") == "new text"
    assert "replace_all" not in tool_input  # Should not be present


def test_parse_hook_input_filters_non_boolean_replace_all():
    """Test parse_hook_input filters out non-boolean replace_all values."""
    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/path/to/file.py",
            "old_string": "old",
            "new_string": "new",
            "replace_all": "true"  # String instead of boolean
        }
    })

    with patch('sys.stdin', StringIO(input_json)):
        result = parse_hook_input()

    assert result is not None
    tool_name, tool_input = result
    assert tool_name == "Edit"
    # Non-boolean replace_all should be filtered out
    assert "replace_all" not in tool_input


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
