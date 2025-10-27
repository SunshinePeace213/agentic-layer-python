#!/usr/bin/env python3
"""
Comprehensive pytest-based tests for the tmp_creation_blocker PreToolUse hook.

Test Categories:
1. Path Detection Tests
2. Bash Command Parsing Tests
3. Integration Tests - Write Tool
4. Integration Tests - Edit Tool
5. Integration Tests - NotebookEdit Tool
6. Integration Tests - Bash Tool
7. Edge Cases and Error Handling

Usage:
    # Run all tests
    uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py -v

    # Run with coverage
    uv run pytest --cov=.claude/hooks/pre_tools/tmp_creation_blocker.py \
        .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py

    # Run distributed (parallel)
    uv run pytest -n auto .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tmp_creation_blocker import (
        check_path_is_temp_directory,
        extract_bash_output_paths,
        generate_project_alternative,
        get_all_temp_directories,
        validate_file_path,
        main,
    )
except ImportError:
    pytest.skip("Could not import tmp_creation_blocker", allow_module_level=True)


# ==================== Path Detection Tests ====================

class TestPathDetection:
    """Test detection of system temporary directories."""

    def test_detect_tmp_directory(self):
        """Test detection of /tmp paths."""
        assert check_path_is_temp_directory("/tmp/file.txt") is True

    def test_detect_var_tmp_directory(self):
        """Test detection of /var/tmp paths."""
        assert check_path_is_temp_directory("/var/tmp/data.json") is True

    def test_detect_private_tmp_directory(self):
        """Test detection of /private/tmp paths (macOS)."""
        assert check_path_is_temp_directory("/private/tmp/output.txt") is True

    def test_detect_private_var_tmp_directory(self):
        """Test detection of /private/var/tmp paths (macOS)."""
        assert check_path_is_temp_directory("/private/var/tmp/data.csv") is True

    def test_allow_project_directory(self):
        """Test that project directories are allowed."""
        assert check_path_is_temp_directory("/project/tmp/file.txt") is False
        assert check_path_is_temp_directory("/home/user/code/output.txt") is False
        assert check_path_is_temp_directory("./local/temp.txt") is False

    def test_allow_relative_tmp_in_project(self):
        """Test that ./tmp/ in project is allowed (not system /tmp)."""
        # Relative path to project's tmp directory
        assert check_path_is_temp_directory("./tmp/file.txt") is False
        assert check_path_is_temp_directory("tmp/file.txt") is False

    def test_handle_empty_file_path(self):
        """Test handling of empty file path."""
        assert check_path_is_temp_directory("") is False

    def test_handle_invalid_path(self):
        """Test handling of invalid path that cannot be resolved."""
        # Should not crash, should fail-safe to False
        assert check_path_is_temp_directory("\x00invalid\x00") is False


# ==================== Bash Command Parsing Tests ====================

class TestBashCommandParsing:
    """Test extraction of file paths from bash commands."""

    def test_extract_redirect_path(self):
        """Test extracting path from redirect operator."""
        paths = extract_bash_output_paths("echo test > /tmp/output.txt")
        assert "/tmp/output.txt" in paths

    def test_extract_append_redirect(self):
        """Test extracting path from append redirect."""
        paths = extract_bash_output_paths("echo test >> /var/tmp/log.txt")
        assert "/var/tmp/log.txt" in paths

    def test_extract_stderr_redirect(self):
        """Test extracting path from stderr redirect."""
        paths = extract_bash_output_paths("command 2> /tmp/error.log")
        assert "/tmp/error.log" in paths

    def test_extract_touch_path(self):
        """Test extracting path from touch command."""
        paths = extract_bash_output_paths("touch /tmp/newfile.txt")
        assert "/tmp/newfile.txt" in paths

    def test_extract_tee_path(self):
        """Test extracting path from tee command."""
        paths = extract_bash_output_paths("echo data | tee /tmp/output.txt")
        assert "/tmp/output.txt" in paths

    def test_extract_multiple_paths(self):
        """Test extracting multiple paths from one command."""
        paths = extract_bash_output_paths("echo a > /tmp/a.txt && echo b > /tmp/b.txt")
        assert "/tmp/a.txt" in paths
        assert "/tmp/b.txt" in paths

    def test_extract_no_paths(self):
        """Test command with no file creation."""
        paths = extract_bash_output_paths("echo hello world")
        assert len(paths) == 0

    def test_extract_touch_with_flags(self):
        """Test touch command with flags."""
        paths = extract_bash_output_paths("touch -a /tmp/file.txt")
        assert "/tmp/file.txt" in paths


# ==================== Alternative Path Generation Tests ====================

class TestAlternativePathGeneration:
    """Test generation of project-relative alternative paths."""

    def test_generate_alternative_from_tmp(self):
        """Test alternative path suggestion from /tmp."""
        alternative = generate_project_alternative("/tmp/output.txt", "/project")
        assert alternative == "./tmp/output.txt"

    def test_generate_alternative_preserves_filename(self):
        """Test that filename is preserved in alternative."""
        alternative = generate_project_alternative("/var/tmp/data.csv", "/project")
        assert "data.csv" in alternative

    def test_generate_alternative_with_nested_path(self):
        """Test alternative for nested temp path."""
        alternative = generate_project_alternative("/tmp/subdir/file.txt", "/project")
        assert "file.txt" in alternative


# ==================== Validation Tests ====================

class TestValidation:
    """Test file path validation logic."""

    def test_validate_allows_project_path(self):
        """Test validation allows project paths."""
        result = validate_file_path("/project/output.txt", "/project")
        assert result is None

    def test_validate_blocks_tmp_path(self):
        """Test validation blocks /tmp paths."""
        result = validate_file_path("/tmp/output.txt", "/project")
        assert result is not None
        assert "/tmp/output.txt" in result
        assert "Blocked" in result

    def test_validate_provides_alternatives(self):
        """Test validation provides alternative suggestions."""
        result = validate_file_path("/tmp/data.txt", "/project")
        assert result is not None
        assert "./tmp/" in result
        assert "./output/" in result


# ==================== Integration Tests - Write Tool ====================

class TestWriteToolIntegration:
    """Test full hook execution with Write tool."""

    def test_hook_blocks_write_to_tmp(self):
        """Test full hook execution blocking Write to /tmp."""
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
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
                assert "/tmp/test.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]
                assert output.get("suppressOutput") is True

    def test_hook_allows_write_to_project(self):
        """Test hook allows Write to project directory."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/project/output.txt", "content": "hello"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_write_to_relative_tmp(self):
        """Test hook allows Write to relative ./tmp path."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "./tmp/test.txt", "content": "hello"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Integration Tests - Edit Tool ====================

class TestEditToolIntegration:
    """Test full hook execution with Edit tool."""

    def test_hook_blocks_edit_to_tmp(self):
        """Test hook blocks Edit to /tmp."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/test.txt",
                "old_string": "old",
                "new_string": "new"
            }
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_edit_to_project(self):
        """Test hook allows Edit to project directory."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/project/test.txt",
                "old_string": "old",
                "new_string": "new"
            }
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Integration Tests - NotebookEdit Tool ====================

class TestNotebookEditToolIntegration:
    """Test full hook execution with NotebookEdit tool."""

    def test_hook_blocks_notebook_edit_to_tmp(self):
        """Test hook blocks NotebookEdit to /tmp."""
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
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_notebook_edit_to_project(self):
        """Test hook allows NotebookEdit to project directory."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "NotebookEdit",
            "tool_input": {"file_path": "/project/notebook.ipynb", "new_source": "code"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Integration Tests - Bash Tool ====================

class TestBashToolIntegration:
    """Test full hook execution with Bash tool."""

    def test_hook_blocks_bash_redirect_to_tmp(self):
        """Test hook blocks Bash redirect to /tmp."""
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
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
                assert "/tmp/output.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]
                assert "echo test > /tmp/output.txt" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_blocks_bash_touch_to_tmp(self):
        """Test hook blocks Bash touch to /tmp."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "touch /var/tmp/file.txt"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_blocks_bash_tee_to_tmp(self):
        """Test hook blocks Bash tee to /tmp."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo data | tee /tmp/output.txt"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_hook_allows_bash_redirect_to_project(self):
        """Test hook allows Bash redirect to project directory."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo test > ./output.txt"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_bash_no_file_creation(self):
        """Test hook allows Bash commands that don't create files."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Edge Cases and Error Handling ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_hook_handles_empty_file_path(self):
        """Test handling of empty file path."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "", "content": "hello"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_handles_empty_command(self):
        """Test handling of empty bash command."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": ""}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_handles_invalid_json(self):
        """Test handling of invalid JSON input."""
        input_text = "invalid json"

        with patch('sys.stdin', StringIO(input_text)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
                assert "fail-safe" in output["hookSpecificOutput"]["permissionDecisionReason"].lower()

    def test_hook_allows_other_tools(self):
        """Test that hook allows tools it doesn't monitor."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"}
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_handles_missing_tool_input(self):
        """Test handling when tool_input is missing."""
        input_json = json.dumps({
            "session_id": "test123",
            "transcript_path": "/path/to/transcript",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write"
        })

        with patch('sys.stdin', StringIO(input_json)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = json.loads(mock_stdout.getvalue())
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Performance Tests ====================

class TestPerformance:
    """Test performance characteristics of the hook."""

    def test_get_all_temp_directories_returns_list(self):
        """Test that get_all_temp_directories returns a valid list."""
        temp_dirs = get_all_temp_directories()
        assert isinstance(temp_dirs, list)
        assert len(temp_dirs) > 0

    def test_validation_is_fast(self):
        """Test that validation completes quickly."""
        import time
        start = time.time()
        for _ in range(100):
            check_path_is_temp_directory("/tmp/test.txt")
        elapsed = time.time() - start
        # Should complete 100 checks in less than 1 second
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
