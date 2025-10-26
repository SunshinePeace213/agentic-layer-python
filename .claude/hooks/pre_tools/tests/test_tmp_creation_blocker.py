#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///

"""
Tests for tmp_creation_blocker.py hook
========================================

Tests the temporary directory creation blocker hook that prevents
file creation in system temp directories (/tmp, /var/tmp, etc.).

Run:
    uv run pytest .claude/hooks/pre_tools/tests/test_tmp_creation_blocker.py -v
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_types import ToolInput


class TestPathDetection:
    """Test detection of temporary directory paths."""

    def test_detect_tmp_directory(self):
        """Should detect /tmp paths as temporary directories."""
        from tmp_creation_blocker import check_path_is_temp_directory

        assert check_path_is_temp_directory("/tmp/file.txt") is True

    def test_detect_var_tmp_directory(self):
        """Should detect /var/tmp paths as temporary directories."""
        from tmp_creation_blocker import check_path_is_temp_directory

        assert check_path_is_temp_directory("/var/tmp/data.json") is True

    def test_allow_project_directory(self):
        """Should allow project-local directories (not temp)."""
        from tmp_creation_blocker import check_path_is_temp_directory

        assert check_path_is_temp_directory("/project/temp/file.txt") is False


class TestValidateFileCreation:
    """Test validation of file creation operations."""

    def test_blocks_write_to_tmp(self):
        """Should block Write tool creating files in /tmp."""
        from tmp_creation_blocker import validate_file_creation

        tool_input: ToolInput = {"file_path": "/tmp/test.txt"}
        violation = validate_file_creation("Write", tool_input)

        assert violation is not None
        assert "/tmp/test.txt" in violation
        assert "Alternative" in violation or "alternative" in violation

    def test_allows_write_to_project(self):
        """Should allow Write tool creating files in project directory."""
        from tmp_creation_blocker import validate_file_creation

        tool_input: ToolInput = {"file_path": "/project/output.txt"}
        violation = validate_file_creation("Write", tool_input)

        assert violation is None

    def test_blocks_notebook_edit_to_tmp(self):
        """Should block NotebookEdit tool creating files in /tmp."""
        from tmp_creation_blocker import validate_file_creation

        tool_input: ToolInput = {"file_path": "/tmp/notebook.ipynb"}
        violation = validate_file_creation("NotebookEdit", tool_input)

        assert violation is not None
        assert "/tmp/notebook.ipynb" in violation


class TestSuggestAlternativePath:
    """Test alternative path suggestion functionality."""

    def test_suggest_alternative_for_tmp_file(self):
        """Should suggest project-local alternative for /tmp file."""
        import os
        from tmp_creation_blocker import suggest_alternative_path

        os.environ["CLAUDE_PROJECT_DIR"] = "/test/project"

        alternative = suggest_alternative_path("/tmp/debug.log")

        assert alternative == "/test/project/temp/debug.log"
        assert "/tmp" not in alternative


class TestMainIntegration:
    """Test full hook execution via main() function."""

    def test_main_blocks_tmp_write(self):
        """Should block Write to /tmp via main() function."""
        import json
        from io import StringIO
        from typing import cast
        from unittest.mock import patch
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
                try:
                    main()
                except SystemExit:
                    pass

                output = cast(dict[str, object], json.loads(mock_stdout.getvalue()))
                hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
                assert hook_specific["permissionDecision"] == "deny"
                assert "/tmp/test.txt" in str(hook_specific["permissionDecisionReason"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
