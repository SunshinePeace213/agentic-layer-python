#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Integration Tests for Universal Hook Logger
============================================

End-to-end tests for the universal_hook_logger.py script.

Test Categories:
    1. Hook Execution Tests
    2. File Output Tests
    3. Error Handling Tests
    4. Multiple Event Tests

Execution:
    uv run pytest -n auto --cov=.claude/hooks/logging tests/claude_hook/logging/test_universal_hook_logger.py -v

Author: Claude Code Hook Expert
Version: 2.0.0
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


# ==================== Test Data ====================


def create_pretooluse_payload() -> dict[str, object]:
    """Create a sample PreToolUse payload."""
    return {
        "session_id": "integration_test_123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/test/file.py", "content": "test content"},
    }


def create_stop_payload() -> dict[str, object]:
    """Create a sample Stop payload."""
    return {
        "session_id": "integration_test_456",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "Stop",
    }


def create_sessionstart_payload() -> dict[str, object]:
    """Create a sample SessionStart payload."""
    return {
        "session_id": "integration_test_789",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "SessionStart",
        "start_type": "startup",
    }


# ==================== Hook Execution Tests ====================


def test_hook_executes_successfully_pretooluse() -> None:
    """Test that hook executes successfully for PreToolUse event."""
    with tempfile.TemporaryDirectory() as temp_dir:
        payload = create_pretooluse_payload()
        json_input = json.dumps(payload)

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        result = subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        assert result.returncode == 0
        assert result.stderr == ""


def test_hook_executes_successfully_stop() -> None:
    """Test that hook executes successfully for Stop event."""
    with tempfile.TemporaryDirectory() as temp_dir:
        payload = create_stop_payload()
        json_input = json.dumps(payload)

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        result = subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        assert result.returncode == 0
        assert result.stderr == ""


def test_hook_creates_log_file() -> None:
    """Test that hook creates log file in correct location."""
    with tempfile.TemporaryDirectory() as temp_dir:
        payload = create_pretooluse_payload()
        json_input = json.dumps(payload)

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "integration_test_123"
            / "PreToolUse.jsonl"
        )

        assert log_file.exists()
        assert log_file.is_file()


def test_hook_writes_valid_jsonl() -> None:
    """Test that hook writes valid JSONL content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        payload = create_pretooluse_payload()
        json_input = json.dumps(payload)

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "integration_test_123"
            / "PreToolUse.jsonl"
        )

        content = log_file.read_text()
        lines = content.strip().split("\n")

        # Should be one line of valid JSON
        assert len(lines) == 1
        log_entry: object = json.loads(lines[0])  # type: ignore[reportAny]

        assert isinstance(log_entry, dict)
        assert "timestamp" in log_entry
        assert "payload" in log_entry


def test_hook_preserves_payload_data() -> None:
    """Test that hook preserves complete payload in log."""
    with tempfile.TemporaryDirectory() as temp_dir:
        payload = create_pretooluse_payload()
        json_input = json.dumps(payload)

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        log_file = (
            Path(temp_dir)
            / "agents"
            / "hook_logs"
            / "integration_test_123"
            / "PreToolUse.jsonl"
        )

        content = log_file.read_text()
        log_entry: object = json.loads(content.strip())  # type: ignore[reportAny]

        assert isinstance(log_entry, dict)
        logged_payload: object = log_entry["payload"]  # type: ignore[reportUnknownVariableType]
        assert isinstance(logged_payload, dict)
        assert logged_payload.get("session_id") == "integration_test_123"  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert logged_payload.get("hook_event_name") == "PreToolUse"  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert logged_payload.get("tool_name") == "Write"  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]


# ==================== Error Handling Tests ====================


def test_hook_handles_invalid_json_gracefully() -> None:
    """Test that hook handles invalid JSON without crashing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        invalid_json = "{ this is not valid json }"

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        result = subprocess.run(
            ["uv", "run", str(hook_script)],
            input=invalid_json,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        # Should exit 0 (non-blocking) even on error
        assert result.returncode == 0


def test_hook_handles_missing_fields_gracefully() -> None:
    """Test that hook handles missing required fields gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        incomplete_payload = json.dumps({"session_id": "test123"})

        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        result = subprocess.run(
            ["uv", "run", str(hook_script)],
            input=incomplete_payload,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        # Should exit 0 (non-blocking) even on error
        assert result.returncode == 0


# ==================== Multiple Event Tests ====================


def test_hook_logs_multiple_events_same_session() -> None:
    """Test logging multiple events to same session."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        # Log PreToolUse event
        pretooluse_payload: dict[str, object] = {
            "session_id": "multi_test",
            "transcript_path": "/path",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {},
        }

        subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json.dumps(pretooluse_payload),
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        # Log Stop event
        stop_payload = {
            "session_id": "multi_test",
            "transcript_path": "/path",
            "cwd": "/project",
            "hook_event_name": "Stop",
        }

        subprocess.run(
            ["uv", "run", str(hook_script)],
            input=json.dumps(stop_payload),
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": temp_dir},
        )

        # Verify both files exist
        log_dir = Path(temp_dir) / "agents" / "hook_logs" / "multi_test"
        pretooluse_file = log_dir / "PreToolUse.jsonl"
        stop_file = log_dir / "Stop.jsonl"

        assert pretooluse_file.exists()
        assert stop_file.exists()


def test_hook_appends_to_existing_log() -> None:
    """Test that hook appends to existing log file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hook_script = (
            Path(__file__).resolve().parents[3]
            / ".claude"
            / "hooks"
            / "logging"
            / "universal_hook_logger.py"
        )

        payload: dict[str, object] = {
            "session_id": "append_test",
            "transcript_path": "/path",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {},
        }

        # Log twice
        for _ in range(2):
            subprocess.run(
                ["uv", "run", str(hook_script)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env={"CLAUDE_PROJECT_DIR": temp_dir},
            )

        log_file = (
            Path(temp_dir) / "agents" / "hook_logs" / "append_test" / "PreToolUse.jsonl"
        )

        content = log_file.read_text()
        lines = content.strip().split("\n")

        # Should have 2 lines
        assert len(lines) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
