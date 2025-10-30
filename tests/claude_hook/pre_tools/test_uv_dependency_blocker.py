#!/usr/bin/env python3
"""
Unit Tests for UV Dependency Blocker Hook
==========================================

Comprehensive test suite for the uv_dependency_blocker.py hook.

Test Categories:
    - Dependency file detection
    - Path handling (absolute, relative, subdirectories)
    - Message generation
    - Integration tests (Write/Edit tools)
    - Error handling
    - Cross-platform compatibility

Test Framework: pytest with distributed testing
Execution: uv run pytest -n auto tests/claude-hook/pre_tools/test_uv_dependency_blocker.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest


# Path to the hook script
HOOK_SCRIPT = Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "pre_tools" / "uv_dependency_blocker.py"


def run_hook(input_data: object) -> object:
    """
    Execute the hook script with given input data.

    Args:
        input_data: Dictionary to pass as JSON to the hook

    Returns:
        Parsed JSON output from the hook
    """
    result = subprocess.run(
        ["uv", "run", str(HOOK_SCRIPT)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )

    # Parse JSON output - using object type to avoid Any
    return cast(object, json.loads(result.stdout))


def get_output_dict(output: object) -> dict[str, object]:
    """Cast output to dict for accessing fields."""
    return cast(dict[str, object], output)


def get_hook_specific_output(output: object) -> dict[str, object]:
    """Extract hookSpecificOutput from output."""
    output_dict = get_output_dict(output)
    hook_specific = cast(dict[str, object], output_dict["hookSpecificOutput"])
    return hook_specific


def get_permission_decision(output: object) -> str:
    """Extract permissionDecision from output."""
    hook_specific = get_hook_specific_output(output)
    return cast(str, hook_specific["permissionDecision"])


def get_permission_reason(output: object) -> str:
    """Extract permissionDecisionReason from output."""
    hook_specific = get_hook_specific_output(output)
    return cast(str, hook_specific["permissionDecisionReason"])


def get_suppress_output(output: object) -> bool:
    """Extract suppressOutput flag from output."""
    output_dict = get_output_dict(output)
    return cast(bool, output_dict.get("suppressOutput", False))


# ==================== Dependency File Detection Tests ====================


def test_uv_lock_detection():
    """Test detection of uv.lock file."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "uv.lock", "content": "# Modified lock file"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"
    reason = get_permission_reason(output)
    assert "uv.lock" in reason
    assert "never be edited manually" in reason


def test_pyproject_toml_detection():
    """Test detection of pyproject.toml file."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "./pyproject.toml", "old_string": "old", "new_string": "new"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"
    assert "pyproject.toml" in get_permission_reason(output)
    assert "uv add" in get_permission_reason(output)


def test_requirements_txt_variants():
    """Test detection of requirements.txt variants."""
    variants = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "requirements-prod.txt",
        "requirements_local.txt",
    ]

    for variant in variants:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": variant, "content": "requests==2.31.0"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "deny", f"Failed for {variant}"
        assert "requirements.txt" in get_permission_reason(output).lower()


def test_pipfile_detection():
    """Test detection of Pipfile and Pipfile.lock."""
    files = ["Pipfile", "Pipfile.lock"]

    for file in files:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file, "content": "content"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "deny", f"Failed for {file}"
        assert "pipfile" in get_permission_reason(output).lower()


def test_case_insensitive_matching():
    """Test case-insensitive file matching (Windows/macOS)."""
    files = ["UV.LOCK", "PyProject.Toml", "Requirements.TXT", "PIPFILE", "pipfile.lock"]

    for file in files:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file, "content": "content"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "deny", f"Case-insensitive match failed for {file}"


def test_non_dependency_files():
    """Test that regular Python files are not detected."""
    files = [
        "main.py",
        "requirements.md",
        "test_requirements.py",
        "uv.py",
        "setup.py",
        "README.md",
    ]

    for file in files:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file, "content": "print('hello')"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "allow", f"Non-dependency file incorrectly blocked: {file}"


# ==================== Path Handling Tests ====================


def test_absolute_path_detection():
    """Test dependency file detection with absolute paths."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/home/user/project/uv.lock", "content": "content"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"


def test_relative_path_detection():
    """Test dependency file detection with relative paths."""
    paths = ["./requirements.txt", "../requirements-dev.txt", "docs/requirements.txt"]

    for path in paths:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": "requests==2.31.0"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "deny", f"Relative path not detected: {path}"


def test_subdirectory_detection():
    """Test dependency files in subdirectories."""
    paths = [
        "backend/requirements.txt",
        "services/api/pyproject.toml",
        "docs/examples/requirements-docs.txt",
    ]

    for path in paths:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": "content"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "deny", f"Subdirectory path not detected: {path}"


# ==================== Message Generation Tests ====================


def test_uv_lock_message_content():
    """Test that uv.lock denial message contains appropriate commands."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "uv.lock", "content": "content"},
    }

    output = run_hook(input_data)
    message = get_permission_reason(output)

    assert "uv lock" in message
    assert "never be edited manually" in message
    assert "uv add" in message


def test_pyproject_toml_message_content():
    """Test that pyproject.toml denial message contains appropriate commands."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "pyproject.toml", "content": "content"},
    }

    output = run_hook(input_data)
    message = get_permission_reason(output)

    assert "uv add" in message
    assert "uv remove" in message
    assert "temporarily disable" in message.lower()


def test_requirements_txt_message_content():
    """Test that requirements.txt denial message contains migration guidance."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "requirements.txt", "content": "content"},
    }

    output = run_hook(input_data)
    message = get_permission_reason(output)

    assert "uv add" in message
    assert ("migrate" in message.lower() or "migrating" in message.lower())
    assert "uv pip" in message


def test_pipfile_message_content():
    """Test that Pipfile denial message contains appropriate commands."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "Pipfile", "content": "content"},
    }

    output = run_hook(input_data)
    message = get_permission_reason(output)

    assert "pipenv" in message.lower()
    assert ("migrate" in message.lower() or "migrating" in message.lower())


# ==================== Integration Tests ====================


def test_write_tool_blocked_uv_lock():
    """Test Write tool blocked when writing to uv.lock."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "uv.lock", "content": "# Modified lock file"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"
    assert cast(str, get_hook_specific_output(output)["hookEventName"]) == "PreToolUse"
    assert get_suppress_output(output) is True


def test_edit_tool_blocked_pyproject():
    """Test Edit tool blocked when editing pyproject.toml."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "./pyproject.toml",
            "old_string": "old_dep",
            "new_string": "new_dep",
        },
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"
    assert cast(str, get_hook_specific_output(output)["hookEventName"]) == "PreToolUse"
    assert get_suppress_output(output) is True


def test_write_tool_allowed_regular_file():
    """Test Write tool allowed for non-dependency files."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "main.py", "content": "print('hello')"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "allow"


def test_edit_tool_allowed_regular_file():
    """Test Edit tool allowed for non-dependency files."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "src/utils.py",
            "old_string": "def old_func():",
            "new_string": "def new_func():",
        },
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "allow"


def test_other_tools_allowed():
    """Test that non-Write/Edit tools are allowed."""
    tools = ["Read", "Bash", "Glob", "Grep"]

    for tool in tools:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": {"file_path": "uv.lock"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "allow", f"Tool {tool} should be allowed"


# ==================== Error Handling Tests ====================


def test_fail_safe_on_missing_file_path():
    """Test hook allows operation when file_path is missing."""
    tool_input: dict[str, str] = {}  # Missing file_path - empty dict
    input_data: object = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": tool_input,
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "allow"


def test_empty_file_path_handling():
    """Test hook handles empty file_path gracefully."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "", "content": "test"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "allow"


# ==================== Cross-Platform Tests ====================


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_path_detection():
    """Test dependency file detection with Windows paths."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "C:\\project\\uv.lock", "content": "content"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "deny"


# ==================== Edge Cases ====================


def test_requirements_without_extension():
    """Test that 'requirements' without .txt extension is not blocked."""
    input_data = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "requirements", "content": "content"},
    }

    output = run_hook(input_data)

    assert get_permission_decision(output) == "allow"


def test_requirements_in_filename():
    """Test that files with 'requirements' in middle are not blocked."""
    files = [
        "test_requirements.py",
        "check_requirements.py",
        "requirements_parser.py",
    ]

    for file in files:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file, "content": "content"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "allow", f"File incorrectly blocked: {file}"


def test_file_with_similar_name():
    """Test files with similar names to dependency files."""
    files = [
        "uv_lock.py",
        "pyproject_parser.py",
        "pipfile_reader.py",
        "my_requirements.py",
    ]

    for file in files:
        input_data = {
            "session_id": "test123",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": file, "content": "content"},
        }

        output = run_hook(input_data)

        assert get_permission_decision(output) == "allow", f"File incorrectly blocked: {file}"
