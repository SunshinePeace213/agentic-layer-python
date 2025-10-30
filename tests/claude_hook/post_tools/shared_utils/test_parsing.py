#!/usr/bin/env python3
"""
Unit Tests for PostToolUse Shared Utilities - Input Parsing

Tests the parse_hook_input and parse_hook_input_minimal functions.
"""

import json
from io import StringIO

import pytest

from utils import parse_hook_input, parse_hook_input_minimal

class TestParseHookInput:
    """Tests for parse_hook_input function."""

    def test_parse_valid_input_write_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing complete valid input for Write tool."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/file.py",
                "content": "print('hello')"
            },
            "tool_response": {
                "filePath": "/path/to/file.py",
                "success": True
            }
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, tool_input, tool_response = result
        assert tool_name == "Write"
        assert tool_input.get("file_path") == "/path/to/file.py"
        assert tool_input.get("content") == "print('hello')"
        assert tool_response.get("filePath") == "/path/to/file.py"
        assert tool_response.get("success") is True

    def test_parse_valid_input_edit_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing input for Edit tool."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/path/to/file.py",
                "old_string": "old text",
                "new_string": "new text",
                "replace_all": False
            },
            "tool_response": {
                "success": True
            }
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, tool_input, _tool_response = result
        assert tool_name == "Edit"
        assert tool_input.get("file_path") == "/path/to/file.py"
        assert tool_input.get("old_string") == "old text"
        assert tool_input.get("new_string") == "new text"
        assert tool_input.get("replace_all") is False

    def test_parse_valid_input_bash_tool(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing input for Bash tool."""
        hook_input: dict[str, object] = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "echo hello"
            },
            "tool_response": {}
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, tool_input, _tool_response = result
        assert tool_name == "Bash"
        assert tool_input.get("command") == "echo hello"

    def test_parse_minimal_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing minimal valid input."""
        hook_input: dict[str, object] = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {},
            "tool_response": {}
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, tool_input, tool_response = result
        assert tool_name == "Write"
        assert isinstance(tool_input, dict)
        assert isinstance(tool_response, dict)

    def test_parse_with_empty_tool_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing input with empty tool_response dict."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/path/to/file.py"},
            "tool_response": {}
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, _tool_input, tool_response = result
        assert tool_name == "Read"
        assert tool_response == {}

    def test_parse_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of malformed JSON."""
        monkeypatch.setattr('sys.stdin', StringIO("invalid json {"))

        result = parse_hook_input()
        assert result is None

    def test_parse_missing_tool_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of missing tool_name field."""
        hook_input: dict[str, object] = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_input": {},
            "tool_response": {}
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is None

    def test_parse_with_additional_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing preserves additional fields in tool_input."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Glob",
            "tool_input": {
                "pattern": "**/*.py",
                "path": "/some/path"
            },
            "tool_response": {}
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input()
        assert result is not None

        tool_name, tool_input, _tool_response = result
        assert tool_name == "Glob"
        assert tool_input.get("pattern") == "**/*.py"
        assert tool_input.get("path") == "/some/path"


class TestParseHookInputMinimal:
    """Tests for parse_hook_input_minimal function."""

    def test_parse_minimal_valid_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing raw input without validation."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project/root",
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "test.py"},
            "tool_response": {"success": True},
            "custom_field": "custom_value"
        }

        monkeypatch.setattr('sys.stdin', StringIO(json.dumps(hook_input)))

        result = parse_hook_input_minimal()
        assert result is not None
        assert result["session_id"] == "test123"
        assert result["tool_name"] == "Write"
        assert result["custom_field"] == "custom_value"  # type: ignore[index]

    def test_parse_minimal_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of malformed JSON in minimal parser."""
        monkeypatch.setattr('sys.stdin', StringIO("invalid json"))

        result = parse_hook_input_minimal()
        assert result is None

    def test_parse_minimal_empty_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test parsing empty dictionary."""
        monkeypatch.setattr('sys.stdin', StringIO("{}"))

        result = parse_hook_input_minimal()
        assert result is not None
        assert result == {}
