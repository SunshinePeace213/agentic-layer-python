#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Unit Tests for Logging Hook Utilities
======================================

Comprehensive test suite for logging/utils module.

Test Categories:
    1. Input Parsing Tests
    2. Log Entry Creation Tests
    3. File Writing Tests
    4. Error Handling Tests

Execution:
    uv run pytest tests/claude_hook/logging/utils/test_utils.py -v

Author: Claude Code Hook Expert
Version: 2.0.0
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hook directory to path for imports
hook_dir = Path(__file__).resolve().parents[4] / ".claude" / "hooks" / "logging"
sys.path.insert(0, str(hook_dir))

from utils import (  # type: ignore  # noqa: E402
    create_log_entry,
    get_hook_event_name,
    parse_universal_input,
    write_log_entry,
)
from utils.data_types import (  # type: ignore  # noqa: E402
    PreToolUseInput,
    StopInput,
    UniversalHookInput,
)


# ==================== Test Data ====================


def create_pretooluse_input() -> PreToolUseInput:
    """Create sample PreToolUse input."""
    return PreToolUseInput(
        session_id="test_session_123",
        transcript_path="/path/to/transcript.jsonl",
        cwd="/project/root",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input={"file_path": "/test/file.py", "content": "test content"},
    )


def create_stop_input() -> StopInput:
    """Create sample Stop input."""
    return StopInput(
        session_id="test_session_456",
        transcript_path="/path/to/transcript.jsonl",
        cwd="/project/root",
        hook_event_name="Stop",
    )


# ==================== Input Parsing Tests ====================


def test_parse_valid_pretooluse_input() -> None:
    """Test parsing valid PreToolUse input."""
    hook_input = create_pretooluse_input()
    json_input = json.dumps(hook_input)

    with patch("sys.stdin", StringIO(json_input)):
        result = parse_universal_input()

    assert result is not None
    assert result.get("session_id") == "test_session_123"
    assert result.get("hook_event_name") == "PreToolUse"
    assert result.get("tool_name") == "Write"


def test_parse_valid_stop_input() -> None:
    """Test parsing valid Stop input."""
    hook_input = create_stop_input()
    json_input = json.dumps(hook_input)

    with patch("sys.stdin", StringIO(json_input)):
        result = parse_universal_input()

    assert result is not None
    assert result.get("session_id") == "test_session_456"
    assert result.get("hook_event_name") == "Stop"


def test_parse_invalid_json() -> None:
    """Test parsing invalid JSON input."""
    invalid_json = "{ this is not valid json }"

    with patch("sys.stdin", StringIO(invalid_json)):
        result = parse_universal_input()

    assert result is None


def test_parse_missing_required_fields() -> None:
    """Test parsing JSON missing required fields."""
    incomplete_input = json.dumps({"session_id": "test123"})

    with patch("sys.stdin", StringIO(incomplete_input)):
        result = parse_universal_input()

    assert result is None


def test_parse_empty_input() -> None:
    """Test parsing empty input."""
    with patch("sys.stdin", StringIO("")):
        result = parse_universal_input()

    assert result is None


def test_parse_non_dict_input() -> None:
    """Test parsing non-dictionary JSON."""
    array_input = json.dumps(["not", "a", "dict"])

    with patch("sys.stdin", StringIO(array_input)):
        result = parse_universal_input()

    assert result is None


# ==================== Hook Event Name Extraction Tests ====================


def test_get_hook_event_name_pretooluse() -> None:
    """Test extracting hook event name from PreToolUse input."""
    hook_input = create_pretooluse_input()
    event_name = get_hook_event_name(hook_input)

    assert event_name == "PreToolUse"


def test_get_hook_event_name_stop() -> None:
    """Test extracting hook event name from Stop input."""
    hook_input = create_stop_input()
    event_name = get_hook_event_name(hook_input)

    assert event_name == "Stop"


def test_get_hook_event_name_missing() -> None:
    """Test extracting hook event name when missing (should return Unknown)."""
    incomplete_input: UniversalHookInput = StopInput(
        session_id="test",
        transcript_path="/path",
        cwd="/cwd",
        hook_event_name="Stop",
    )
    # Remove hook_event_name for test
    del incomplete_input["hook_event_name"]  # type: ignore[misc]

    event_name = get_hook_event_name(incomplete_input)

    assert event_name == "Unknown"


# ==================== Log Entry Creation Tests ====================


def test_create_log_entry_has_timestamp() -> None:
    """Test that log entry contains timestamp."""
    hook_input = create_pretooluse_input()
    log_entry = create_log_entry(hook_input)

    assert "timestamp" in log_entry
    assert isinstance(log_entry["timestamp"], str)
    assert len(log_entry["timestamp"]) > 0


def test_create_log_entry_preserves_payload() -> None:
    """Test that log entry preserves complete payload."""
    hook_input = create_pretooluse_input()
    log_entry = create_log_entry(hook_input)

    assert "payload" in log_entry
    payload = log_entry["payload"]
    assert payload.get("session_id") == "test_session_123"
    assert payload.get("hook_event_name") == "PreToolUse"
    assert payload.get("tool_name") == "Write"


def test_create_log_entry_timestamp_is_iso_format() -> None:
    """Test that timestamp is in ISO 8601 format."""
    hook_input = create_pretooluse_input()
    log_entry = create_log_entry(hook_input)

    timestamp = log_entry["timestamp"]
    # ISO 8601 format should contain 'T' and potentially timezone info
    assert "T" in timestamp or ":" in timestamp


# ==================== File Writing Tests ====================


def test_write_creates_directory_structure() -> None:
    """Test that write_log_entry creates directory structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input = create_pretooluse_input()
        log_entry = create_log_entry(hook_input)

        write_log_entry("test_session", "PreToolUse", log_entry, temp_dir)

        log_dir = Path(temp_dir) / "agents" / "hook_logs" / "test_session"
        assert log_dir.exists()
        assert log_dir.is_dir()


def test_write_creates_event_specific_file() -> None:
    """Test that write_log_entry creates event-specific JSONL file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input = create_pretooluse_input()
        log_entry = create_log_entry(hook_input)

        write_log_entry("test_session", "PreToolUse", log_entry, temp_dir)

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "test_session"
            / "PreToolUse.jsonl"
        )
        assert log_file.exists()
        assert log_file.is_file()


def test_write_appends_to_existing_file() -> None:
    """Test that write_log_entry appends to existing file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input1 = create_pretooluse_input()
        hook_input2 = create_pretooluse_input()

        log_entry1 = create_log_entry(hook_input1)
        log_entry2 = create_log_entry(hook_input2)

        write_log_entry("test_session", "PreToolUse", log_entry1, temp_dir)
        write_log_entry("test_session", "PreToolUse", log_entry2, temp_dir)

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "test_session"
            / "PreToolUse.jsonl"
        )
        lines = log_file.read_text().strip().split("\n")

        assert len(lines) == 2


def test_multiple_events_same_session() -> None:
    """Test logging multiple events to same session."""
    with tempfile.TemporaryDirectory() as temp_dir:
        pretooluse_input = create_pretooluse_input()
        stop_input = create_stop_input()

        pretooluse_entry = create_log_entry(pretooluse_input)
        stop_entry = create_log_entry(stop_input)

        write_log_entry("test_session", "PreToolUse", pretooluse_entry, temp_dir)
        write_log_entry("test_session", "Stop", stop_entry, temp_dir)

        log_dir = Path(temp_dir) / "agents" / "hook_logs" / "test_session"
        pretooluse_file = log_dir / "PreToolUse.jsonl"
        stop_file = log_dir / "Stop.jsonl"

        assert pretooluse_file.exists()
        assert stop_file.exists()


def test_different_sessions_different_directories() -> None:
    """Test that different sessions create separate directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input = create_pretooluse_input()
        log_entry = create_log_entry(hook_input)

        write_log_entry("session1", "PreToolUse", log_entry, temp_dir)
        write_log_entry("session2", "PreToolUse", log_entry, temp_dir)

        session1_dir = Path(temp_dir) / "agents" / "hook_logs" / "session1"
        session2_dir = Path(temp_dir) / "agents" / "hook_logs" / "session2"

        assert session1_dir.exists()
        assert session2_dir.exists()


def test_write_log_entry_jsonl_format() -> None:
    """Test that log entries are written in JSONL format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input = create_pretooluse_input()
        log_entry = create_log_entry(hook_input)

        write_log_entry("test_session", "PreToolUse", log_entry, temp_dir)

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "test_session"
            / "PreToolUse.jsonl"
        )
        content = log_file.read_text()

        # Should be valid JSON followed by newline
        lines = content.strip().split("\n")
        parsed_entry: object = json.loads(lines[0])  # type: ignore[reportAny]

        assert isinstance(parsed_entry, dict)
        assert "timestamp" in parsed_entry
        assert "payload" in parsed_entry


# ==================== Integration Tests ====================


def test_full_workflow_pretooluse() -> None:
    """Test complete workflow: parse -> create -> write for PreToolUse."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input_dict = create_pretooluse_input()
        json_input = json.dumps(hook_input_dict)

        # Parse
        with patch("sys.stdin", StringIO(json_input)):
            parsed_input = parse_universal_input()

        assert parsed_input is not None

        # Create log entry
        log_entry = create_log_entry(parsed_input)
        event_name = get_hook_event_name(parsed_input)
        session_id = parsed_input.get("session_id", "unknown")

        # Write
        write_log_entry(session_id, event_name, log_entry, temp_dir)

        # Verify
        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "test_session_123"
            / "PreToolUse.jsonl"
        )
        assert log_file.exists()

        # Verify content
        content = log_file.read_text()
        parsed_log: object = json.loads(content.strip())  # type: ignore[reportAny]

        assert isinstance(parsed_log, dict)
        assert "payload" in parsed_log
        payload: object = parsed_log["payload"]  # type: ignore[reportUnknownVariableType]
        assert isinstance(payload, dict)
        assert payload.get("session_id") == "test_session_123"  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert payload.get("tool_name") == "Write"  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]


def test_full_workflow_stop() -> None:
    """Test complete workflow: parse -> create -> write for Stop."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_input_dict = create_stop_input()
        json_input = json.dumps(hook_input_dict)

        # Parse
        with patch("sys.stdin", StringIO(json_input)):
            parsed_input = parse_universal_input()

        assert parsed_input is not None

        # Create log entry
        log_entry = create_log_entry(parsed_input)
        event_name = get_hook_event_name(parsed_input)
        session_id = parsed_input.get("session_id", "unknown")

        # Write
        write_log_entry(session_id, event_name, log_entry, temp_dir)

        # Verify
        log_file = (
            Path(temp_dir) / "agents" / "hook_logs" / "test_session_456" / "Stop.jsonl"
        )
        assert log_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
