#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Unit Tests for Temporary Directory Creation Blocker Hook
=========================================================

Comprehensive test suite for tmp_creation_blocker.py hook.

Test Categories:
    1. Path Detection Tests
    2. Bash Command Parsing Tests
    3. Integration Tests
    4. Error Handling Tests
    5. Cross-Platform Tests

Execution:
    uv run pytest -n auto tests/claude-hook/pre_tools/test_tmp_creation_blocker.py

Author: Claude Code Hook Expert
Version: 2.1.0
"""

import json
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Callable, Optional, cast
from unittest.mock import patch
import pytest

# Add hook directory to path for imports
hook_dir = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "pre_tools"
sys.path.insert(0, str(hook_dir))

from tmp_creation_blocker import (  # type: ignore  # noqa: E402
    check_path_is_temp_directory as _check_path,  # type: ignore
    extract_bash_output_paths as _extract_paths,  # type: ignore
    generate_project_alternative as _gen_alternative,  # type: ignore
    format_deny_message as _format_msg,  # type: ignore
    validate_file_path as _validate_path,  # type: ignore
    validate_bash_command as _validate_cmd,  # type: ignore
    get_all_temp_directories as _get_temp_dirs,  # type: ignore
)

# Type-annotated wrappers for imported functions
# These are dynamically imported, so we suppress type checking
check_path_is_temp_directory: Callable[[str], bool] = _check_path  # type: ignore
extract_bash_output_paths: Callable[[str], list[str]] = _extract_paths  # type: ignore
generate_project_alternative: Callable[[str, str], str] = _gen_alternative  # type: ignore
format_deny_message: Callable[[str, str], str] = _format_msg  # type: ignore
validate_file_path: Callable[[str, str], Optional[str]] = _validate_path  # type: ignore
validate_bash_command: Callable[[str, str], Optional[str]] = _validate_cmd  # type: ignore
get_all_temp_directories: Callable[[], list[str]] = _get_temp_dirs  # type: ignore


# ==================== Type Definitions ====================

# Type aliases for test data
ToolInputDict = dict[str, str]
HookInputDict = dict[str, object]
HookOutputDict = dict[str, object]
HookSpecificDict = dict[str, object]


# ==================== Test Data ====================


def create_write_input(file_path: str) -> HookInputDict:
    """Create sample Write tool input."""
    tool_input: ToolInputDict = {
        "file_path": file_path,
        "content": '{"test": true}',
    }
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": tool_input,
    }


def create_bash_input(command: str) -> HookInputDict:
    """Create sample Bash tool input."""
    tool_input: ToolInputDict = {"command": command}
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": tool_input,
    }


# ==================== Path Detection Tests ====================


def test_unix_temp_directory_detection() -> None:
    """Test detection of Unix/Linux temporary directories."""
    assert check_path_is_temp_directory("/tmp/file.txt") is True
    assert check_path_is_temp_directory("/var/tmp/data.json") is True


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
def test_macos_temp_directory_detection() -> None:
    """Test detection of macOS-specific temporary directories."""
    assert check_path_is_temp_directory("/private/tmp/file.txt") is True
    assert check_path_is_temp_directory("/private/var/tmp/output.log") is True


@pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
def test_windows_temp_directory_detection() -> None:
    """Test detection of Windows temporary directories."""
    assert check_path_is_temp_directory(r"C:\Temp\file.txt") is True
    assert check_path_is_temp_directory(r"C:\Windows\Temp\data.json") is True


def test_project_path_allowed() -> None:
    """Test project-relative paths are allowed."""
    assert check_path_is_temp_directory("./tmp/file.txt") is False
    assert check_path_is_temp_directory("./output/data.json") is False
    # Absolute path outside temp directories
    assert check_path_is_temp_directory("/home/user/project/tmp/file.txt") is False


def test_empty_path_allowed() -> None:
    """Test empty path returns False (allowed)."""
    assert check_path_is_temp_directory("") is False


def test_relative_path_normalization() -> None:
    """Test relative paths are properly normalized."""
    # Relative path that doesn't resolve to temp directory
    assert check_path_is_temp_directory("./data.json") is False
    # Complex relative path
    assert check_path_is_temp_directory("../project/tmp/file.txt") is False


def test_environment_variable_temp_detection() -> None:
    """Test temp directory detection via environment variables."""
    # Get actual temp directories
    temp_dirs = get_all_temp_directories()
    # Should include at least one temp directory
    assert len(temp_dirs) > 0
    # Check if TMPDIR is in the list (if set)
    if "TMPDIR" in os.environ:
        tmpdir_value = os.environ["TMPDIR"]
        if os.path.isdir(tmpdir_value):
            # Path under TMPDIR should be detected
            test_path = os.path.join(tmpdir_value, "test.txt")
            assert check_path_is_temp_directory(test_path) is True


# ==================== Bash Command Parsing Tests ====================


def test_redirect_operator_parsing() -> None:
    """Test detection of redirect operators in bash commands."""
    # Single redirect
    paths = extract_bash_output_paths('echo "text" > /tmp/output.txt')
    assert "/tmp/output.txt" in paths

    # Append redirect
    paths = extract_bash_output_paths("cat input.txt >> /tmp/log.txt")
    assert "/tmp/log.txt" in paths

    # Error redirect
    paths = extract_bash_output_paths("command 2> /tmp/errors.log")
    assert "/tmp/errors.log" in paths

    # Combined redirect
    paths = extract_bash_output_paths("command &> /tmp/output.log")
    assert "/tmp/output.log" in paths


def test_touch_command_parsing() -> None:
    """Test detection of touch commands."""
    # Simple touch
    paths = extract_bash_output_paths("touch /tmp/marker.txt")
    assert "/tmp/marker.txt" in paths

    # Touch with flags
    paths = extract_bash_output_paths("touch -a /tmp/file.txt")
    assert "/tmp/file.txt" in paths


def test_tee_command_parsing() -> None:
    """Test detection of tee commands."""
    # Simple tee
    paths = extract_bash_output_paths("ls -la | tee /tmp/listing.txt")
    assert "/tmp/listing.txt" in paths

    # Tee with flags
    paths = extract_bash_output_paths("command | tee -a /tmp/output.log")
    assert "/tmp/output.log" in paths


def test_complex_bash_command() -> None:
    """Test complex commands with multiple file outputs."""
    cmd = 'echo "data" > /tmp/out.txt && cat /tmp/out.txt >> /var/tmp/log.txt'
    paths = extract_bash_output_paths(cmd)
    assert "/tmp/out.txt" in paths
    assert "/var/tmp/log.txt" in paths


def test_bash_command_with_project_paths() -> None:
    """Test bash commands with project-relative paths are not flagged."""
    # Project-relative paths should not be detected as problematic
    paths = extract_bash_output_paths('echo "data" > ./tmp/output.txt')
    # Path is extracted, but validation will allow it
    assert "./tmp/output.txt" in paths
    # Verify it's not detected as temp directory
    assert check_path_is_temp_directory("./tmp/output.txt") is False


def test_bash_command_no_file_output() -> None:
    """Test bash commands without file outputs return empty list."""
    # Command with no file creation
    paths = extract_bash_output_paths("ls -la")
    assert len(paths) == 0

    # Command with input redirect only
    paths = extract_bash_output_paths("cat < input.txt")
    assert len(paths) == 0


# ==================== Alternative Path Generation Tests ====================


def test_generate_project_alternative() -> None:
    """Test generation of project-relative alternatives."""
    alt = generate_project_alternative("/tmp/data.json", "/project")
    assert alt == "./tmp/data.json"

    alt = generate_project_alternative("/var/tmp/output.txt", "/project")
    assert alt == "./tmp/output.txt"


def test_format_deny_message() -> None:
    """Test formatting of denial messages."""
    msg = format_deny_message("/tmp/data.json", "/project")
    assert "Blocked" in msg
    assert "/tmp/data.json" in msg
    assert "./tmp/data.json" in msg
    assert "mkdir -p ./tmp" in msg


# ==================== Validation Function Tests ====================


def test_validate_file_path_blocks_temp() -> None:
    """Test validate_file_path blocks temp directory paths."""
    result = validate_file_path("/tmp/file.txt", "/project")
    assert result is not None
    assert "Blocked" in result


def test_validate_file_path_allows_project() -> None:
    """Test validate_file_path allows project paths."""
    result = validate_file_path("./tmp/file.txt", "/project")
    assert result is None

    result = validate_file_path("/home/user/project/file.txt", "/project")
    assert result is None


def test_validate_file_path_empty() -> None:
    """Test validate_file_path with empty path."""
    result = validate_file_path("", "/project")
    assert result is None


def test_validate_bash_command_blocks_temp() -> None:
    """Test validate_bash_command blocks temp directory writes."""
    result = validate_bash_command('echo "test" > /tmp/output.txt', "/project")
    assert result is not None
    assert "Blocked" in result


def test_validate_bash_command_allows_project() -> None:
    """Test validate_bash_command allows project writes."""
    result = validate_bash_command('echo "test" > ./tmp/output.txt', "/project")
    assert result is None


def test_validate_bash_command_empty() -> None:
    """Test validate_bash_command with empty command."""
    result = validate_bash_command("", "/project")
    assert result is None


def test_validate_bash_command_no_output() -> None:
    """Test validate_bash_command with commands that don't create files."""
    result = validate_bash_command("ls -la", "/project")
    assert result is None

    result = validate_bash_command("git status", "/project")
    assert result is None


# ==================== Integration Tests ====================


def test_main_write_tool_blocked() -> None:
    """Test main() blocks Write tool when writing to /tmp/."""
    input_json = json.dumps(create_write_input("/tmp/test.txt"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                # Import and run main
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "Blocked" in str(hook_specific["permissionDecisionReason"])
            assert output.get("suppressOutput") is True


def test_main_write_tool_allowed() -> None:
    """Test main() allows Write tool when writing to project directory."""
    input_json = json.dumps(create_write_input("./tmp/test.txt"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_bash_tool_blocked() -> None:
    """Test main() blocks Bash tool when redirecting to /tmp/."""
    input_json = json.dumps(create_bash_input('echo "output" > /tmp/result.txt'))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"


def test_main_bash_tool_allowed() -> None:
    """Test main() allows Bash tool when redirecting to project directory."""
    input_json = json.dumps(create_bash_input('echo "output" > ./tmp/result.txt'))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


# ==================== Error Handling Tests ====================


def test_fail_safe_on_invalid_json() -> None:
    """Test hook allows operation on invalid JSON input."""
    with patch("sys.stdin", StringIO("invalid json")):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            # Should output "allow" decision on error
            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_fail_safe_on_missing_tool_name() -> None:
    """Test hook allows operation when tool_name is missing."""
    input_json = json.dumps(
        {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            # Missing tool_name
            "tool_input": {"file_path": "/tmp/test.txt"},
        }
    )

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from tmp_creation_blocker import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(HookSpecificDict, output["hookSpecificOutput"])
            # Should allow since tool_name is empty/missing
            assert hook_specific["permissionDecision"] == "allow"


def test_check_path_is_temp_directory_handles_invalid_path() -> None:
    """Test check_path_is_temp_directory handles invalid paths gracefully."""
    # Invalid paths should return False (fail-safe)
    result = check_path_is_temp_directory("\x00invalid")
    assert result is False


def test_extract_bash_output_paths_handles_invalid_regex() -> None:
    """Test extract_bash_output_paths handles edge cases."""
    # Complex command should not crash
    result = extract_bash_output_paths("command with ;;; invalid >>> syntax")
    # Should return list (possibly empty), not crash
    assert isinstance(result, list)


# ==================== Cross-Platform Tests ====================


@pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
def test_unix_temp_directories_included() -> None:
    """Test Unix temporary directories are included in detection list."""
    temp_dirs = get_all_temp_directories()
    assert "/tmp" in temp_dirs


@pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
def test_windows_temp_directories_included() -> None:
    """Test Windows temporary directories are included in detection list."""
    temp_dirs = get_all_temp_directories()
    # At least one Windows temp dir should be present
    assert any(
        dir_path in temp_dirs for dir_path in [r"C:\Temp", r"C:\Windows\Temp"]
    )


# ==================== Test Execution ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
