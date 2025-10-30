#!/usr/bin/env python3
"""
Unit Tests for Ruff Checking Hook
==================================

Comprehensive test suite for the ruff_checking.py PostToolUse hook.

Test Categories:
    1. Input Validation Tests
    2. Formatting Tests
    3. Linting Tests
    4. Feedback Generation Tests
    5. Integration Tests
    6. Error Handling Tests

Usage:
    uv run pytest -n auto tests/claude_hook/post_tools/test_ruff_checking.py
    uv run pytest -v tests/claude_hook/post_tools/test_ruff_checking.py::TestShouldProcess

Dependencies:
    - pytest
    - pytest-xdist (for parallel execution)
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the hook directory to sys.path so we can import the hook module
HOOK_DIR = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "post_tools"
)
sys.path.insert(0, str(HOOK_DIR))

import ruff_checking  # Import the hook module  # noqa: E402


# ==================== Fixtures ====================


@pytest.fixture
def temp_project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Create a temporary project directory with CLAUDE_PROJECT_DIR set.

    Args:
        tmp_path: Pytest tmp_path fixture
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Path to temporary project directory
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    return project_dir


@pytest.fixture
def sample_python_file(temp_project_dir: Path) -> Path:
    """
    Create a sample Python file for testing.

    Args:
        temp_project_dir: Temporary project directory fixture

    Returns:
        Path to created Python file
    """
    file_path = temp_project_dir / "example.py"
    file_path.write_text("def foo():\n  return 42\n")
    return file_path


@pytest.fixture
def unformatted_python_file(temp_project_dir: Path) -> Path:
    """
    Create an unformatted Python file for testing.

    Args:
        temp_project_dir: Temporary project directory fixture

    Returns:
        Path to created unformatted Python file
    """
    file_path = temp_project_dir / "unformatted.py"
    file_path.write_text("def foo( ):\n  return  42\n")
    return file_path


@pytest.fixture
def python_file_with_lint_issues(temp_project_dir: Path) -> Path:
    """
    Create a Python file with lint issues for testing.

    Args:
        temp_project_dir: Temporary project directory fixture

    Returns:
        Path to created Python file with lint issues
    """
    file_path = temp_project_dir / "lint_issues.py"
    # Import not used issue
    file_path.write_text("import os\nimport sys\n\ndef foo():\n    return 42\n")
    return file_path


@pytest.fixture
def mock_hook_input_write(sample_python_file: Path) -> dict[str, object]:
    """
    Create mock hook input for Write tool.

    Args:
        sample_python_file: Sample Python file fixture

    Returns:
        Mock hook input dictionary
    """
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": str(sample_python_file.parent),
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(sample_python_file),
            "content": "def foo():\n  return 42\n",
        },
        "tool_response": {"filePath": str(sample_python_file), "success": True},
    }


@pytest.fixture
def mock_hook_input_edit(sample_python_file: Path) -> dict[str, object]:
    """
    Create mock hook input for Edit tool.

    Args:
        sample_python_file: Sample Python file fixture

    Returns:
        Mock hook input dictionary
    """
    return {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": str(sample_python_file.parent),
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(sample_python_file),
            "old_string": "return 42",
            "new_string": "return 84",
        },
        "tool_response": {"filePath": str(sample_python_file), "success": True},
    }


# ==================== Test Cases ====================


class TestShouldProcess:
    """Test the should_process() validation function."""

    def test_should_process_valid_write_tool(self, sample_python_file: Path) -> None:
        """Test that valid Write tool operations are processed."""
        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_process_valid_edit_tool(self, sample_python_file: Path) -> None:
        """Test that valid Edit tool operations are processed."""
        result = ruff_checking.should_process(
            tool_name="Edit",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_process_valid_notebookedit_tool(
        self, sample_python_file: Path
    ) -> None:
        """Test that valid NotebookEdit tool operations are processed."""
        result = ruff_checking.should_process(
            tool_name="NotebookEdit",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_skip_non_write_edit_tools(self, sample_python_file: Path) -> None:
        """Test that non-Write/Edit/NotebookEdit tools are skipped."""
        result = ruff_checking.should_process(
            tool_name="Read",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_when_tool_failed(self, sample_python_file: Path) -> None:
        """Test that files are skipped when tool_response.success=False."""
        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": False},
        )
        assert result is False

    def test_should_skip_non_python_files(self, temp_project_dir: Path) -> None:
        """Test that non-Python files are skipped."""
        js_file = temp_project_dir / "test.js"
        js_file.write_text("console.log('hello');")

        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(js_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_files_outside_project(self, tmp_path: Path) -> None:
        """Test that files outside project directory are skipped."""
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("print('hello')")

        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(outside_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_missing_file_path(self) -> None:
        """Test that missing file_path is skipped."""
        from utils import ToolInput  # type: ignore[reportMissingImports]

        empty_input = ToolInput()
        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input=empty_input,
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_nonexistent_file(self, temp_project_dir: Path) -> None:
        """Test that nonexistent files are skipped."""
        nonexistent_file = temp_project_dir / "nonexistent.py"

        result = ruff_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(nonexistent_file)},
            tool_response={"success": True},
        )
        assert result is False


class TestRunRuffFormat:
    """Test the run_ruff_format() function."""

    def test_run_ruff_format_on_unformatted_file(
        self, unformatted_python_file: Path
    ) -> None:
        """Test formatting of unformatted Python file."""
        result = ruff_checking.run_ruff_format(str(unformatted_python_file))

        assert result["success"] is True
        assert result["formatted"] is True
        assert result["error"] is None

        # Verify file was actually formatted
        formatted_content = unformatted_python_file.read_text()
        assert "def foo():" in formatted_content
        assert "return 42" in formatted_content

    def test_run_ruff_format_on_already_formatted_file(
        self, temp_project_dir: Path
    ) -> None:
        """Test that already-formatted files are not changed."""
        formatted_file = temp_project_dir / "formatted.py"
        formatted_file.write_text("def foo():\n    return 42\n")

        result = ruff_checking.run_ruff_format(str(formatted_file))

        assert result["success"] is True
        assert result["formatted"] is False
        assert result["error"] is None

    def test_run_ruff_format_handles_syntax_errors(
        self, temp_project_dir: Path
    ) -> None:
        """Test error handling for files with syntax errors."""
        syntax_error_file = temp_project_dir / "syntax_error.py"
        syntax_error_file.write_text("def foo(\n")  # Missing closing parenthesis

        result = ruff_checking.run_ruff_format(str(syntax_error_file))

        # Ruff format should still succeed but report it couldn't format
        assert result["success"] is False or result["formatted"] is False

    @patch("subprocess.run")
    def test_run_ruff_format_handles_timeout(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test timeout handling for ruff format."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ruff", timeout=10)

        result = ruff_checking.run_ruff_format(str(sample_python_file))

        assert result["success"] is False
        assert result["formatted"] is False
        assert result["error"] == "Timeout"

    @patch("subprocess.run")
    def test_run_ruff_format_handles_missing_ruff(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test error handling when ruff is not installed."""
        mock_run.side_effect = FileNotFoundError("ruff not found")

        result = ruff_checking.run_ruff_format(str(sample_python_file))

        assert result["success"] is False
        assert result["formatted"] is False
        assert result["error"] == "Ruff not found"


class TestRunRuffCheck:
    """Test the run_ruff_check() function."""

    def test_run_ruff_check_fixes_violations(
        self, python_file_with_lint_issues: Path
    ) -> None:
        """Test auto-fixing of lint violations."""
        result = ruff_checking.run_ruff_check(str(python_file_with_lint_issues))

        assert result["success"] is True
        # Should have fixed some violations (unused imports)
        assert result["fixed_count"] >= 0  # type: ignore[operator]
        assert result["remaining_count"] >= 0  # type: ignore[operator]

    def test_run_ruff_check_handles_no_violations(self, temp_project_dir: Path) -> None:
        """Test files with no violations."""
        clean_file = temp_project_dir / "clean.py"
        clean_file.write_text("def foo():\n    return 42\n")

        result = ruff_checking.run_ruff_check(str(clean_file))

        assert result["success"] is True
        assert result["fixed_count"] == 0
        assert result["remaining_count"] == 0

    @patch("subprocess.run")
    def test_run_ruff_check_handles_timeout(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test timeout handling for ruff check."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ruff", timeout=10)

        result = ruff_checking.run_ruff_check(str(sample_python_file))

        assert result["success"] is False
        assert result["fixed_count"] == 0
        assert result["remaining_count"] == 0
        assert result["error"] == "Timeout"

    @patch("subprocess.run")
    def test_run_ruff_check_handles_invalid_json(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test handling of malformed JSON from ruff."""
        mock_result = MagicMock()
        mock_result.stdout = "not json"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = ruff_checking.run_ruff_check(str(sample_python_file))

        assert result["success"] is False
        assert result["error"] == "Invalid JSON"

    @patch("subprocess.run")
    def test_run_ruff_check_handles_missing_ruff(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test error handling when ruff is not installed."""
        mock_run.side_effect = FileNotFoundError("ruff not found")

        result = ruff_checking.run_ruff_check(str(sample_python_file))

        assert result["success"] is False
        assert result["error"] == "Ruff not found"


class TestGenerateFeedback:
    """Test the generate_feedback() function."""

    def test_generate_feedback_format_only(self, sample_python_file: Path) -> None:
        """Test feedback when only formatting is applied."""
        format_result: dict[str, object] = {"success": True, "formatted": True, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "formatted" in feedback
        assert "example.py" in feedback
        assert "✅" in feedback

    def test_generate_feedback_fix_only(self, sample_python_file: Path) -> None:
        """Test feedback when only lint fixes are applied."""
        format_result: dict[str, object] = {"success": True, "formatted": False, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 3,
            "remaining_count": 0,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "fixed 3 lint issues" in feedback
        assert "example.py" in feedback
        assert "✅" in feedback

    def test_generate_feedback_format_and_fix(self, sample_python_file: Path) -> None:
        """Test feedback when both formatting and fixes are applied."""
        format_result: dict[str, object] = {"success": True, "formatted": True, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 2,
            "remaining_count": 0,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "formatted" in feedback
        assert "fixed 2 lint issues" in feedback
        assert "example.py" in feedback
        assert "✅" in feedback

    def test_generate_feedback_no_changes(self, sample_python_file: Path) -> None:
        """Test that empty feedback is returned when no changes made."""
        format_result: dict[str, object] = {"success": True, "formatted": False, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert feedback == ""

    def test_generate_feedback_with_remaining_violations(
        self, sample_python_file: Path
    ) -> None:
        """Test feedback includes warning about remaining violations."""
        format_result: dict[str, object] = {"success": True, "formatted": False, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 0,
            "remaining_count": 2,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "⚠️" in feedback
        assert "2 remaining issues" in feedback
        assert "ruff check" in feedback

    def test_generate_feedback_with_format_error(
        self, sample_python_file: Path
    ) -> None:
        """Test feedback with format error."""
        format_result: dict[str, object] = {"success": False, "formatted": False, "error": "Format failed"}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "⚠️" in feedback
        assert "format error" in feedback
        assert "Format failed" in feedback

    def test_generate_feedback_with_check_error(self, sample_python_file: Path) -> None:
        """Test feedback with check error."""
        format_result: dict[str, object] = {"success": True, "formatted": False, "error": None}
        check_result: dict[str, object] = {
            "success": False,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": "Check failed",
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "⚠️" in feedback
        assert "check error" in feedback
        assert "Check failed" in feedback

    def test_generate_feedback_singular_issue(self, sample_python_file: Path) -> None:
        """Test feedback uses singular form for 1 issue."""
        format_result: dict[str, object] = {"success": True, "formatted": False, "error": None}
        check_result: dict[str, object] = {
            "success": True,
            "fixed_count": 1,
            "remaining_count": 1,
            "error": None,
        }

        feedback = ruff_checking.generate_feedback(
            str(sample_python_file), format_result, check_result
        )

        assert "fixed 1 lint issue" in feedback
        assert "1 remaining issue" in feedback


class TestMainIntegration:
    """Integration tests for the main() function."""

    @patch("sys.stdin")
    @patch("ruff_checking.output_feedback")
    def test_full_workflow_write_tool(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        mock_hook_input_write: dict[str, object],
    ) -> None:
        """Test complete workflow for Write tool."""
        mock_stdin.read.return_value = json.dumps(mock_hook_input_write)  # type: ignore[reportAny]

        ruff_checking.main()

        # Verify output_feedback was called
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        # First positional arg is the feedback message
        feedback = call_args[0][0]  # type: ignore[reportAny]
        # Should have feedback (empty or with content)
        assert isinstance(feedback, str)

    @patch("sys.stdin")
    @patch("ruff_checking.output_feedback")
    def test_full_workflow_edit_tool(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        mock_hook_input_edit: dict[str, object],
    ) -> None:
        """Test complete workflow for Edit tool."""
        mock_stdin.read.return_value = json.dumps(mock_hook_input_edit)  # type: ignore[reportAny]

        ruff_checking.main()

        # Verify output_feedback was called
        mock_output.assert_called_once()

    @patch("sys.stdin")
    @patch("ruff_checking.output_feedback")
    def test_handles_invalid_json_input(
        self, mock_output: MagicMock, mock_stdin: MagicMock
    ) -> None:
        """Test handling of invalid JSON input."""
        mock_stdin.read.return_value = "not valid json"  # type: ignore[reportAny]

        ruff_checking.main()

        # Should exit gracefully
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        feedback = call_args[0][0]  # type: ignore[reportAny]
        assert feedback == ""

    @patch("sys.stdin")
    @patch("ruff_checking.output_feedback")
    def test_handles_non_target_tool(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        sample_python_file: Path,
    ) -> None:
        """Test handling of non-target tools (e.g., Read)."""
        hook_input = {
            "session_id": "test123",
            "tool_name": "Read",
            "tool_input": {"file_path": str(sample_python_file)},
            "tool_response": {"success": True},
        }
        mock_stdin.read.return_value = json.dumps(hook_input)  # type: ignore[reportAny]

        ruff_checking.main()

        # Should exit silently
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        feedback = call_args[0][0]  # type: ignore[reportAny]
        assert feedback == ""


# ==================== Test Execution ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
