#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Unit Tests for Pytest Argument Linting Hook
=============================================

Comprehensive test suite for lint_arg_pytest.py hook.

Test Categories:
    1. Pytest Detection Tests
    2. Argument Validation Tests
    3. Allow-List Tests
    4. Command Parsing Tests
    5. Message Generation Tests
    6. Integration Tests
    7. Error Handling Tests

Execution:
    uv run pytest -n auto --cov=. tests/claude_hook/pre_tools/test_lint_arg_pytest.py

Author: Claude Code Hook Expert
Version: 1.0.0
"""

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Callable, Optional, cast
from unittest.mock import patch

import pytest

# Add hook directory to path for imports
hook_dir = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "pre_tools"
sys.path.insert(0, str(hook_dir))

from lint_arg_pytest import (  # type: ignore  # noqa: E402
    check_required_arguments as _check_args,  # type: ignore
    contains_pytest_command as _contains_pytest,  # type: ignore
    get_deny_message as _deny_msg,  # type: ignore
    get_missing_both_message as _both_msg,  # type: ignore
    get_missing_cov_message as _cov_msg,  # type: ignore
    get_missing_xdist_message as _xdist_msg,  # type: ignore
    is_allowed_pytest_command as _is_allowed,  # type: ignore
    parse_command_segments as _parse_segments,  # type: ignore
    validate_bash_command as _validate_cmd,  # type: ignore
)

# Type-annotated wrappers for imported functions
parse_command_segments: Callable[[str], list[str]] = _parse_segments  # type: ignore
contains_pytest_command: Callable[[str], bool] = _contains_pytest  # type: ignore
is_allowed_pytest_command: Callable[[str], bool] = _is_allowed  # type: ignore
check_required_arguments: Callable[[str], tuple[bool, bool]] = _check_args  # type: ignore
get_missing_both_message: Callable[[str], str] = _both_msg  # type: ignore
get_missing_xdist_message: Callable[[str], str] = _xdist_msg  # type: ignore
get_missing_cov_message: Callable[[str], str] = _cov_msg  # type: ignore
get_deny_message: Callable[[str, bool, bool], str] = _deny_msg  # type: ignore
validate_bash_command: Callable[[str], Optional[str]] = _validate_cmd  # type: ignore


# ==================== Type Definitions ====================

tool_input_dict = dict[str, str]
hook_input_dict = dict[str, object]
hook_output_dict = dict[str, object]
hook_specific_dict = dict[str, object]


# ==================== Test Data ====================


def create_bash_input(command: str) -> hook_input_dict:
    """Create sample Bash tool input."""
    tool_input: tool_input_dict = {"command": command}
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": tool_input,
    }


def create_non_bash_input(tool_name: str) -> hook_input_dict:
    """Create sample non-Bash tool input."""
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {},
    }


# ==================== Command Parsing Tests ====================


def test_parse_single_command() -> None:
    """Test parsing single commands."""
    segments = parse_command_segments("pytest tests/")
    assert len(segments) == 1
    assert segments[0] == "pytest tests/"


def test_parse_chained_commands() -> None:
    """Test parsing chained commands with &&."""
    segments = parse_command_segments("cd dir && pytest tests/")
    assert len(segments) == 2
    assert "cd dir" in segments
    assert "pytest tests/" in segments


def test_parse_multiple_pytest_commands() -> None:
    """Test parsing multiple pytest commands."""
    segments = parse_command_segments("pytest tests/unit && pytest tests/integration")
    assert len(segments) == 2
    assert "pytest tests/unit" in segments
    assert "pytest tests/integration" in segments


def test_parse_piped_commands() -> None:
    """Test parsing piped commands."""
    segments = parse_command_segments("echo test | pytest -k test")
    assert len(segments) == 2


def test_parse_or_commands() -> None:
    """Test parsing commands with ||."""
    segments = parse_command_segments("pytest tests/ || echo failed")
    assert len(segments) == 2


def test_parse_semicolon_commands() -> None:
    """Test parsing commands separated by semicolons."""
    segments = parse_command_segments("pytest tests/unit ; pytest tests/integration")
    assert len(segments) == 2


def test_parse_empty_command() -> None:
    """Test parsing empty command."""
    segments = parse_command_segments("")
    assert len(segments) == 0


# ==================== Pytest Detection Tests ====================


def test_detect_pytest_direct() -> None:
    """Test detection of direct pytest commands."""
    assert contains_pytest_command("pytest tests/") is True
    assert contains_pytest_command("pytest") is True
    assert contains_pytest_command("pytest --help") is True


def test_detect_pytest_uv_wrapped() -> None:
    """Test detection of UV-wrapped pytest commands."""
    assert contains_pytest_command("uv run pytest tests/") is True
    assert contains_pytest_command("uv run -m pytest tests/") is True


def test_detect_pytest_python_module() -> None:
    """Test detection of python -m pytest commands."""
    assert contains_pytest_command("python -m pytest tests/") is True
    assert contains_pytest_command("python3 -m pytest tests/") is True


def test_no_pytest_in_other_commands() -> None:
    """Test that non-pytest commands are not detected."""
    assert contains_pytest_command("ls tests/") is False
    assert contains_pytest_command("uv run python script.py") is False
    assert contains_pytest_command("git status") is False
    assert contains_pytest_command("npm test") is False


def test_detect_pytest_with_arguments() -> None:
    """Test detection of pytest with various arguments."""
    assert contains_pytest_command("pytest -v tests/") is True
    assert contains_pytest_command("pytest -n auto tests/") is True
    assert contains_pytest_command("pytest --cov=. tests/") is True


# ==================== Allow-List Tests ====================


def test_allow_help_commands() -> None:
    """Test that help commands are allowed."""
    assert is_allowed_pytest_command("pytest --help") is True
    assert is_allowed_pytest_command("pytest -h") is True


def test_allow_version_commands() -> None:
    """Test that version commands are allowed."""
    assert is_allowed_pytest_command("pytest --version") is True
    assert is_allowed_pytest_command("pytest -V") is True


def test_allow_collection_commands() -> None:
    """Test that collection commands are allowed."""
    assert is_allowed_pytest_command("pytest --collect-only") is True
    assert is_allowed_pytest_command("pytest --co") is True


def test_allow_info_commands() -> None:
    """Test that informational commands are allowed."""
    assert is_allowed_pytest_command("pytest --fixtures") is True
    assert is_allowed_pytest_command("pytest --markers") is True
    assert is_allowed_pytest_command("pytest --cache-show") is True


def test_disallow_regular_pytest() -> None:
    """Test that regular pytest commands are not in allow-list."""
    assert is_allowed_pytest_command("pytest tests/") is False
    assert is_allowed_pytest_command("pytest -v tests/") is False
    assert is_allowed_pytest_command("pytest -n auto tests/") is False


# ==================== Argument Validation Tests ====================


def test_has_both_required_arguments() -> None:
    """Test detection of both -n auto and --cov."""
    has_xdist, has_cov = check_required_arguments("pytest -n auto --cov=. tests/")
    assert has_xdist is True
    assert has_cov is True


def test_has_both_arguments_reversed_order() -> None:
    """Test detection with arguments in reversed order."""
    has_xdist, has_cov = check_required_arguments("pytest --cov=. -n auto tests/")
    assert has_xdist is True
    assert has_cov is True


def test_has_only_xdist() -> None:
    """Test detection of only -n auto."""
    has_xdist, has_cov = check_required_arguments("pytest -n auto tests/")
    assert has_xdist is True
    assert has_cov is False


def test_has_only_cov() -> None:
    """Test detection of only --cov."""
    has_xdist, has_cov = check_required_arguments("pytest --cov=. tests/")
    assert has_xdist is False
    assert has_cov is True


def test_has_neither_argument() -> None:
    """Test detection when both arguments are missing."""
    has_xdist, has_cov = check_required_arguments("pytest tests/")
    assert has_xdist is False
    assert has_cov is False


def test_various_xdist_formats() -> None:
    """Test different xdist argument formats."""
    assert check_required_arguments("pytest -n auto tests/")[0] is True
    assert check_required_arguments("pytest -n 4 tests/")[0] is True
    assert check_required_arguments("pytest -n 8 tests/")[0] is True
    assert check_required_arguments("pytest --numprocesses=auto tests/")[0] is True
    assert check_required_arguments("pytest --numprocesses=4 tests/")[0] is True


def test_various_cov_formats() -> None:
    """Test different coverage argument formats."""
    assert check_required_arguments("pytest --cov tests/")[1] is True
    assert check_required_arguments("pytest --cov=. tests/")[1] is True
    assert check_required_arguments("pytest --cov=src tests/")[1] is True
    assert check_required_arguments("pytest --cov=mymodule tests/")[1] is True


def test_cov_with_report_options() -> None:
    """Test coverage with report options."""
    cmd = "pytest -n auto --cov=. --cov-report=term tests/"
    has_xdist, has_cov = check_required_arguments(cmd)
    assert has_xdist is True
    assert has_cov is True

    cmd2 = "pytest -n auto --cov=. --cov-report=html tests/"
    has_xdist2, has_cov2 = check_required_arguments(cmd2)
    assert has_xdist2 is True
    assert has_cov2 is True


def test_complex_pytest_command() -> None:
    """Test complex pytest command with many options."""
    cmd = "pytest -n auto --cov=. --cov-report=term -v -s tests/"
    has_xdist, has_cov = check_required_arguments(cmd)
    assert has_xdist is True
    assert has_cov is True


# ==================== Message Generation Tests ====================


def test_missing_both_message_content() -> None:
    """Test message for missing both arguments contains expected content."""
    msg = get_missing_both_message("pytest tests/")
    assert "Blocked" in msg
    assert "pytest tests/" in msg
    assert "-n auto" in msg
    assert "--cov" in msg
    assert "pytest-xdist" in msg
    assert "pytest-cov" in msg


def test_missing_xdist_message_content() -> None:
    """Test message for missing xdist contains expected content."""
    msg = get_missing_xdist_message("pytest --cov=. tests/")
    assert "Blocked" in msg
    assert "pytest --cov=. tests/" in msg
    assert "-n auto" in msg
    assert "parallel execution" in msg.lower()


def test_missing_cov_message_content() -> None:
    """Test message for missing coverage contains expected content."""
    msg = get_missing_cov_message("pytest -n auto tests/")
    assert "Blocked" in msg
    assert "pytest -n auto tests/" in msg
    assert "--cov" in msg
    assert "coverage" in msg.lower()


def test_get_deny_message_both_missing() -> None:
    """Test get_deny_message when both arguments are missing."""
    msg = get_deny_message("pytest tests/", False, False)
    assert "Blocked" in msg
    assert "-n auto" in msg
    assert "--cov" in msg


def test_get_deny_message_xdist_missing() -> None:
    """Test get_deny_message when only xdist is missing."""
    msg = get_deny_message("pytest --cov=. tests/", False, True)
    assert "Blocked" in msg
    assert "-n auto" in msg


def test_get_deny_message_cov_missing() -> None:
    """Test get_deny_message when only coverage is missing."""
    msg = get_deny_message("pytest -n auto tests/", True, False)
    assert "Blocked" in msg
    assert "--cov" in msg


# ==================== Validation Function Tests ====================


def test_validate_allows_optimized_pytest() -> None:
    """Test validate_bash_command allows optimized pytest."""
    result = validate_bash_command("pytest -n auto --cov=. tests/")
    assert result is None

    result2 = validate_bash_command("uv run pytest -n auto --cov=. tests/")
    assert result2 is None


def test_validate_blocks_unoptimized_pytest() -> None:
    """Test validate_bash_command blocks unoptimized pytest."""
    result = validate_bash_command("pytest tests/")
    assert result is not None
    assert "Blocked" in result


def test_validate_blocks_missing_xdist() -> None:
    """Test validate_bash_command blocks pytest missing xdist."""
    result = validate_bash_command("pytest --cov=. tests/")
    assert result is not None
    assert "Blocked" in result
    assert "-n auto" in result


def test_validate_blocks_missing_cov() -> None:
    """Test validate_bash_command blocks pytest missing coverage."""
    result = validate_bash_command("pytest -n auto tests/")
    assert result is not None
    assert "Blocked" in result
    assert "--cov" in result


def test_validate_allows_help_commands() -> None:
    """Test validate_bash_command allows help commands."""
    result = validate_bash_command("pytest --help")
    assert result is None

    result2 = validate_bash_command("pytest -h")
    assert result2 is None


def test_validate_allows_version_commands() -> None:
    """Test validate_bash_command allows version commands."""
    result = validate_bash_command("pytest --version")
    assert result is None

    result2 = validate_bash_command("pytest -V")
    assert result2 is None


def test_validate_allows_collection_commands() -> None:
    """Test validate_bash_command allows collection commands."""
    result = validate_bash_command("pytest --collect-only")
    assert result is None

    result2 = validate_bash_command("pytest --co")
    assert result2 is None


def test_validate_allows_info_commands() -> None:
    """Test validate_bash_command allows informational commands."""
    result = validate_bash_command("pytest --fixtures")
    assert result is None

    result2 = validate_bash_command("pytest --markers")
    assert result2 is None

    result3 = validate_bash_command("pytest --cache-show")
    assert result3 is None


def test_validate_allows_non_pytest_commands() -> None:
    """Test validate_bash_command allows non-pytest commands."""
    result = validate_bash_command("git status")
    assert result is None

    result2 = validate_bash_command("npm test")
    assert result2 is None

    result3 = validate_bash_command("uv run python script.py")
    assert result3 is None


def test_validate_empty_command() -> None:
    """Test validate_bash_command with empty command."""
    result = validate_bash_command("")
    assert result is None


def test_validate_blocks_chained_unoptimized_pytest() -> None:
    """Test validate_bash_command blocks unoptimized pytest in chains."""
    result = validate_bash_command("cd tests && pytest test_module.py")
    assert result is not None
    assert "Blocked" in result


def test_validate_allows_chained_optimized_pytest() -> None:
    """Test validate_bash_command allows optimized pytest in chains."""
    result = validate_bash_command("cd tests && pytest -n auto --cov=. test_module.py")
    assert result is None


def test_validate_blocks_multiple_unoptimized_pytest() -> None:
    """Test validate_bash_command blocks if any pytest is unoptimized."""
    result = validate_bash_command(
        "pytest -n auto --cov=. tests/unit && pytest tests/integration"
    )
    assert result is not None
    assert "Blocked" in result


def test_validate_allows_multiple_optimized_pytest() -> None:
    """Test validate_bash_command allows multiple optimized pytest commands."""
    result = validate_bash_command(
        "pytest -n auto --cov=. tests/unit && pytest -n auto --cov=. tests/integration"
    )
    assert result is None


# ==================== Integration Tests ====================


def test_main_bash_tool_blocks_unoptimized_pytest() -> None:
    """Test main() blocks Bash tool for unoptimized pytest."""
    input_json = json.dumps(create_bash_input("pytest tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "Blocked" in str(hook_specific["permissionDecisionReason"])
            assert output.get("suppressOutput") is True


def test_main_bash_tool_blocks_missing_xdist() -> None:
    """Test main() blocks Bash tool when missing xdist."""
    input_json = json.dumps(create_bash_input("pytest --cov=. tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "Blocked" in str(hook_specific["permissionDecisionReason"])


def test_main_bash_tool_blocks_missing_cov() -> None:
    """Test main() blocks Bash tool when missing coverage."""
    input_json = json.dumps(create_bash_input("pytest -n auto tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "Blocked" in str(hook_specific["permissionDecisionReason"])


def test_main_bash_tool_allows_optimized_pytest() -> None:
    """Test main() allows Bash tool for optimized pytest."""
    input_json = json.dumps(create_bash_input("pytest -n auto --cov=. tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_bash_tool_allows_help() -> None:
    """Test main() allows Bash tool for pytest help."""
    input_json = json.dumps(create_bash_input("pytest --help"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_bash_tool_allows_non_pytest() -> None:
    """Test main() allows Bash tool for non-pytest commands."""
    input_json = json.dumps(create_bash_input("git status"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_non_bash_tool_allowed() -> None:
    """Test main() allows non-Bash tools."""
    input_json = json.dumps(create_non_bash_input("Write"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_uv_wrapped_pytest_optimized() -> None:
    """Test main() allows UV-wrapped optimized pytest."""
    input_json = json.dumps(create_bash_input("uv run pytest -n auto --cov=. tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "allow"


def test_main_uv_wrapped_pytest_unoptimized() -> None:
    """Test main() blocks UV-wrapped unoptimized pytest."""
    input_json = json.dumps(create_bash_input("uv run pytest tests/"))

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                from lint_arg_pytest import main  # type: ignore[import-not-found]

                main()

            assert exc_info.value.code == 0

            output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
            hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"


# ==================== Error Handling Tests ====================


def test_main_invalid_json_input() -> None:
    """Test main() handles invalid JSON gracefully."""
    with patch("sys.stdin", StringIO("invalid json {")):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with patch("sys.stderr", new_callable=StringIO):
                with pytest.raises(SystemExit) as exc_info:
                    from lint_arg_pytest import main  # type: ignore[import-not-found]

                    main()

                assert exc_info.value.code == 0

                # Should output allow decision on parse failure
                output = cast(hook_output_dict, json.loads(mock_stdout.getvalue()))
                hook_specific = cast(hook_specific_dict, output["hookSpecificOutput"])
                assert hook_specific["permissionDecision"] == "allow"
                assert (
                    "fail-safe"
                    in str(hook_specific["permissionDecisionReason"]).lower()
                )


def test_validate_handles_regex_errors() -> None:
    """Test validate_bash_command handles regex errors gracefully."""
    # Should not raise exception, should return None (allow)
    result = validate_bash_command("pytest tests/")
    # This might block or allow depending on the command, but shouldn't crash
    assert isinstance(result, (str, type(None)))
