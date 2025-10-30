#!/usr/bin/env python3
"""
Unit Tests for Vulture Checking Hook
=====================================

Comprehensive test suite for the vulture_checking.py PostToolUse hook.

Test Categories:
    1. Input Validation Tests
    2. Test File Detection Tests
    3. Vulture Scan Tests
    4. Feedback Generation Tests
    5. Message Parsing Tests
    6. Integration Tests
    7. Error Handling Tests

Usage:
    uv run pytest -n auto tests/claude_hook/post_tools/test_vulture_checking.py
    uv run pytest -v tests/claude_hook/post_tools/test_vulture_checking.py::TestShouldProcess

Dependencies:
    - pytest
    - pytest-xdist (for parallel execution)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

# Add the hook directory to sys.path so we can import the hook module
HOOK_DIR = (
    Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "post_tools"
)
sys.path.insert(0, str(HOOK_DIR))

import vulture_checking  # Import the hook module  # noqa: E402


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
    file_path.write_text("def foo():\n    return 42\n")
    return file_path


@pytest.fixture
def python_file_with_dead_code(temp_project_dir: Path) -> Path:
    """
    Create a Python file with dead code for testing.

    Args:
        temp_project_dir: Temporary project directory fixture

    Returns:
        Path to created Python file with dead code
    """
    file_path = temp_project_dir / "dead_code.py"
    content = """import os
import sys

def unused_func():
    pass

def main():
    print('hello')

if __name__ == '__main__':
    main()
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def python_test_file(temp_project_dir: Path) -> Path:
    """
    Create a test file for testing.

    Args:
        temp_project_dir: Temporary project directory fixture

    Returns:
        Path to created test file
    """
    tests_dir = temp_project_dir / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_example.py"
    test_file.write_text("import pytest\n\ndef test_foo():\n    assert True\n")
    return test_file


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
            "content": "def foo():\n    return 42\n",
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
        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_process_valid_edit_tool(self, sample_python_file: Path) -> None:
        """Test that valid Edit tool operations are processed."""
        result = vulture_checking.should_process(
            tool_name="Edit",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_process_valid_notebookedit_tool(
        self, sample_python_file: Path
    ) -> None:
        """Test that valid NotebookEdit tool operations are processed."""
        result = vulture_checking.should_process(
            tool_name="NotebookEdit",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is True

    def test_should_skip_non_write_edit_tools(self, sample_python_file: Path) -> None:
        """Test that non-Write/Edit/NotebookEdit tools are skipped."""
        result = vulture_checking.should_process(
            tool_name="Read",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_when_tool_failed(self, sample_python_file: Path) -> None:
        """Test that files are skipped when tool_response.success=False."""
        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(sample_python_file)},
            tool_response={"success": False},
        )
        assert result is False

    def test_should_skip_non_python_files(self, temp_project_dir: Path) -> None:
        """Test that non-Python files are skipped."""
        js_file = temp_project_dir / "test.js"
        js_file.write_text("console.log('hello');")

        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(js_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_files_outside_project(self, tmp_path: Path) -> None:
        """Test that files outside project directory are skipped."""
        outside_file = tmp_path / "outside.py"
        outside_file.write_text("print('hello')")

        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(outside_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_missing_file_path(self) -> None:
        """Test that missing file_path is skipped."""
        from utils import ToolInput  # type: ignore[reportMissingImports]

        empty_input = ToolInput()
        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input=empty_input,
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_nonexistent_file(self, temp_project_dir: Path) -> None:
        """Test that nonexistent files are skipped."""
        nonexistent_file = temp_project_dir / "nonexistent.py"

        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(nonexistent_file)},
            tool_response={"success": True},
        )
        assert result is False

    def test_should_skip_test_files(self, python_test_file: Path) -> None:
        """Test that test files are skipped to avoid false positives."""
        result = vulture_checking.should_process(
            tool_name="Write",
            tool_input={"file_path": str(python_test_file)},
            tool_response={"success": True},
        )
        assert result is False


class TestIsTestFile:
    """Test the is_test_file() function."""

    def test_is_test_file_with_test_prefix(self, temp_project_dir: Path) -> None:
        """Test detection of test_*.py files."""
        test_file = temp_project_dir / "test_example.py"
        test_file.write_text("def test_foo(): pass")

        assert vulture_checking.is_test_file(str(test_file)) is True

    def test_is_test_file_with_test_suffix(self, temp_project_dir: Path) -> None:
        """Test detection of *_test.py files."""
        test_file = temp_project_dir / "example_test.py"
        test_file.write_text("def test_foo(): pass")

        assert vulture_checking.is_test_file(str(test_file)) is True

    def test_is_test_file_conftest(self, temp_project_dir: Path) -> None:
        """Test detection of conftest.py."""
        conftest = temp_project_dir / "conftest.py"
        conftest.write_text("import pytest")

        assert vulture_checking.is_test_file(str(conftest)) is True

    def test_is_test_file_in_tests_directory(self, temp_project_dir: Path) -> None:
        """Test detection of files in tests/ directory."""
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "example.py"
        test_file.write_text("def foo(): pass")

        assert vulture_checking.is_test_file(str(test_file)) is True

    def test_is_test_file_in_test_directory(self, temp_project_dir: Path) -> None:
        """Test detection of files in test/ directory."""
        test_dir = temp_project_dir / "test"
        test_dir.mkdir()
        test_file = test_dir / "example.py"
        test_file.write_text("def foo(): pass")

        assert vulture_checking.is_test_file(str(test_file)) is True

    def test_is_not_test_file_regular(self, temp_project_dir: Path) -> None:
        """Test that regular files are not detected as test files."""
        regular_file = temp_project_dir / "example.py"
        regular_file.write_text("def foo(): pass")

        assert vulture_checking.is_test_file(str(regular_file)) is False

    def test_is_not_test_file_with_test_in_name(self, temp_project_dir: Path) -> None:
        """Test that files with 'test' in middle are not detected as test files."""
        file_with_test = temp_project_dir / "testing_utils.py"
        file_with_test.write_text("def foo(): pass")

        assert vulture_checking.is_test_file(str(file_with_test)) is False


class TestRunVultureScan:
    """Test the run_vulture_scan() function."""

    def test_run_vulture_scan_with_dead_code(
        self, python_file_with_dead_code: Path
    ) -> None:
        """Test detection of dead code."""
        findings = vulture_checking.run_vulture_scan(str(python_file_with_dead_code))

        # Should find unused imports and unused function
        assert len(findings) >= 1
        # Verify structure of findings
        for finding in findings:
            assert isinstance(finding, dict)
            assert "file" in finding or "message" in finding
            assert "line" in finding
            assert "confidence" in finding
            # All findings should meet confidence threshold
            assert finding["confidence"] >= vulture_checking.MIN_CONFIDENCE

    def test_run_vulture_scan_no_dead_code(self, sample_python_file: Path) -> None:
        """Test clean file with no dead code."""
        findings = vulture_checking.run_vulture_scan(str(sample_python_file))

        assert len(findings) == 0

    def test_run_vulture_scan_filters_low_confidence(
        self, temp_project_dir: Path
    ) -> None:
        """Test that low-confidence findings are filtered out."""
        # Create file that might generate low-confidence findings
        file_path = temp_project_dir / "example.py"
        file_path.write_text("class MyClass:\n    def __init__(self):\n        pass\n")

        findings = vulture_checking.run_vulture_scan(str(file_path))

        # All returned findings should meet confidence threshold
        for finding in findings:
            confidence_val = finding.get("confidence", 0)
            assert isinstance(confidence_val, int)
            assert int(confidence_val) >= vulture_checking.MIN_CONFIDENCE

    @patch("subprocess.run")
    def test_run_vulture_scan_handles_timeout(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test timeout handling for vulture scan."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="vulture", timeout=10)

        findings = vulture_checking.run_vulture_scan(str(sample_python_file))

        assert findings == []

    @patch("subprocess.run")
    def test_run_vulture_scan_handles_invalid_json(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test handling of malformed JSON from vulture."""
        mock_result = MagicMock()
        mock_result.stdout = "not json"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        findings = vulture_checking.run_vulture_scan(str(sample_python_file))

        assert findings == []

    @patch("subprocess.run")
    def test_run_vulture_scan_handles_missing_vulture(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test error handling when vulture is not installed."""
        mock_run.side_effect = FileNotFoundError("vulture not found")

        findings = vulture_checking.run_vulture_scan(str(sample_python_file))

        assert findings == []

    @patch("subprocess.run")
    def test_run_vulture_scan_handles_error_exit_code(
        self, mock_run: MagicMock, sample_python_file: Path
    ) -> None:
        """Test handling of vulture error exit code (2)."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = "Syntax error"
        mock_run.return_value = mock_result

        findings = vulture_checking.run_vulture_scan(str(sample_python_file))

        assert findings == []


class TestGenerateFeedback:
    """Test the generate_feedback() function."""

    def test_generate_feedback_single_finding(self, sample_python_file: Path) -> None:
        """Test feedback with single dead code finding."""
        findings: list[dict[str, object]] = [
            {
                "file": str(sample_python_file),
                "line": 5,
                "message": "unused function 'unused_func'",
                "confidence": 100,
            }
        ]

        feedback = vulture_checking.generate_feedback(str(sample_python_file), findings)

        assert "⚠️ Vulture:" in feedback
        assert "1 unused item" in feedback
        assert "example.py" in feedback
        assert "function 'unused_func'" in feedback
        assert "line 5" in feedback

    def test_generate_feedback_multiple_findings(
        self, sample_python_file: Path
    ) -> None:
        """Test feedback with multiple findings."""
        findings: list[dict[str, object]] = [
            {
                "file": str(sample_python_file),
                "line": 1,
                "message": "unused import 'os'",
                "confidence": 90,
            },
            {
                "file": str(sample_python_file),
                "line": 5,
                "message": "unused function 'helper'",
                "confidence": 100,
            },
            {
                "file": str(sample_python_file),
                "line": 10,
                "message": "unused variable 'result'",
                "confidence": 85,
            },
        ]

        feedback = vulture_checking.generate_feedback(str(sample_python_file), findings)

        assert "⚠️ Vulture:" in feedback
        assert "3 unused items" in feedback
        assert "example.py" in feedback
        assert "import 'os'" in feedback
        assert "line 1" in feedback
        assert "function 'helper'" in feedback
        assert "line 5" in feedback
        assert "variable 'result'" in feedback
        assert "line 10" in feedback

    def test_generate_feedback_many_findings(self, sample_python_file: Path) -> None:
        """Test feedback truncation for many findings."""
        findings: list[dict[str, object]] = [
            {
                "file": str(sample_python_file),
                "line": i,
                "message": f"unused function 'func{i}'",
                "confidence": 90,
            }
            for i in range(10)
        ]

        feedback = vulture_checking.generate_feedback(str(sample_python_file), findings)

        assert "⚠️ Vulture:" in feedback
        assert "10 unused items" in feedback
        assert "...7 more" in feedback
        # Should only show first 3 items
        assert "func0" in feedback
        assert "func1" in feedback
        assert "func2" in feedback

    def test_generate_feedback_no_findings(self, sample_python_file: Path) -> None:
        """Test that empty feedback is returned for clean files."""
        findings: list[dict[str, object]] = []

        feedback = vulture_checking.generate_feedback(str(sample_python_file), findings)

        assert feedback == ""


class TestExtractItemName:
    """Test the extract_item_name() function."""

    def test_extract_item_name_function(self) -> None:
        """Test extraction of function names from vulture messages."""
        message = "unused function 'foo'"
        result = vulture_checking.extract_item_name(message)
        assert result == "function 'foo'"

    def test_extract_item_name_variable(self) -> None:
        """Test extraction of variable names."""
        message = "unused variable 'bar'"
        result = vulture_checking.extract_item_name(message)
        assert result == "variable 'bar'"

    def test_extract_item_name_import(self) -> None:
        """Test extraction of import names."""
        message = "unused import 'os'"
        result = vulture_checking.extract_item_name(message)
        assert result == "import 'os'"

    def test_extract_item_name_attribute(self) -> None:
        """Test extraction of attribute names."""
        message = "unused attribute 'baz'"
        result = vulture_checking.extract_item_name(message)
        assert result == "attribute 'baz'"

    def test_extract_item_name_class(self) -> None:
        """Test extraction of class names."""
        message = "unused class 'MyClass'"
        result = vulture_checking.extract_item_name(message)
        assert result == "class 'MyClass'"

    def test_extract_item_name_fallback(self) -> None:
        """Test fallback for unparseable messages."""
        message = "unknown message format"
        result = vulture_checking.extract_item_name(message)
        assert "unknown message format" in result


class TestMainIntegration:
    """Integration tests for the main() function."""

    @patch("sys.stdin")
    @patch("vulture_checking.output_feedback")
    def test_full_workflow_write_tool(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        mock_hook_input_write: dict[str, object],
    ) -> None:
        """Test complete workflow for Write tool."""
        mock_stdin.read.return_value = cast(str, json.dumps(mock_hook_input_write))

        vulture_checking.main()

        # Verify output_feedback was called
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        # First positional arg is the feedback message
        feedback = cast(str, call_args[0][0])
        # Should have feedback (empty or with content)
        assert isinstance(feedback, str)

    @patch("sys.stdin")
    @patch("vulture_checking.output_feedback")
    def test_full_workflow_edit_tool(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        mock_hook_input_edit: dict[str, object],
    ) -> None:
        """Test complete workflow for Edit tool."""
        mock_stdin.read.return_value = cast(str, json.dumps(mock_hook_input_edit))

        vulture_checking.main()

        # Verify output_feedback was called
        mock_output.assert_called_once()

    @patch("sys.stdin")
    @patch("vulture_checking.output_feedback")
    def test_handles_invalid_json_input(
        self, mock_output: MagicMock, mock_stdin: MagicMock
    ) -> None:
        """Test handling of invalid JSON input."""
        mock_stdin.read.return_value = cast(str, "not valid json")

        vulture_checking.main()

        # Should exit gracefully
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        feedback = cast(str, call_args[0][0])
        assert feedback == ""

    @patch("sys.stdin")
    @patch("vulture_checking.output_feedback")
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
        mock_stdin.read.return_value = cast(str, json.dumps(hook_input))

        vulture_checking.main()

        # Should exit silently
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        feedback = cast(str, call_args[0][0])
        assert feedback == ""

    @patch("sys.stdin")
    @patch("vulture_checking.output_feedback")
    def test_skips_test_files(
        self,
        mock_output: MagicMock,
        mock_stdin: MagicMock,
        python_test_file: Path,
    ) -> None:
        """Test that test files are skipped in main workflow."""
        hook_input = {
            "session_id": "test123",
            "tool_name": "Write",
            "tool_input": {"file_path": str(python_test_file)},
            "tool_response": {"success": True},
        }
        mock_stdin.read.return_value = cast(str, json.dumps(hook_input))

        vulture_checking.main()

        # Should exit silently (test files are skipped)
        mock_output.assert_called_once()
        call_args = mock_output.call_args
        assert call_args is not None
        feedback = cast(str, call_args[0][0])
        assert feedback == ""


# ==================== Test Execution ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
