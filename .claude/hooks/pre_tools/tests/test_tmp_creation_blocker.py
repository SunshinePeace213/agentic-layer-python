#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
"""
Unit tests for tmp_creation_blocker.py hook.

Tests validation of file creation in temporary directories.
"""

import json
import sys
from io import StringIO
from pathlib import Path
from typing import cast
from unittest.mock import patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_detect_tmp_directory():
    """Test detection of /tmp paths."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/tmp/file.txt") is True


def test_detect_var_tmp_directory():
    """Test detection of /var/tmp paths."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/var/tmp/data.json") is True


def test_allow_project_directory():
    """Test that project directories are allowed."""
    from tmp_creation_blocker import check_path_is_temp_directory

    assert check_path_is_temp_directory("/project/temp/file.txt") is False
    assert check_path_is_temp_directory("/home/user/code/output.txt") is False


def test_hook_blocks_write_to_tmp():
    """Test full hook execution blocking Write to /tmp."""
    from tmp_creation_blocker import main

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt", "content": "hello"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
            hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "/tmp/test.txt" in str(hook_specific["permissionDecisionReason"])


def test_hook_blocks_notebook_edit_to_tmp():
    """Test hook blocks NotebookEdit to /tmp."""
    from tmp_creation_blocker import main

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "NotebookEdit",
        "tool_input": {"file_path": "/tmp/notebook.ipynb", "new_source": "code"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
            hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"


def test_hook_blocks_bash_redirect_to_tmp():
    """Test hook blocks Bash redirect to /tmp."""
    from tmp_creation_blocker import main

    input_json = json.dumps({
        "session_id": "test123",
        "transcript_path": "/path/to/transcript",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test > /tmp/output.txt"}
    })

    with patch('sys.stdin', StringIO(input_json)):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
            hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
            assert hook_specific["permissionDecision"] == "deny"
            assert "/tmp/output.txt" in str(hook_specific["permissionDecisionReason"])


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
