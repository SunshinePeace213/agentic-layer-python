#!/usr/bin/env python3
"""
Unit Tests for PostToolUse Shared Utilities - Data Extraction Functions

Tests the data extraction and validation helper functions.
"""

import os
from pathlib import Path

import pytest

from utils import (
    ToolInput,
    get_command,
    get_file_path,
    get_project_dir,
    get_tool_response_field,
    is_python_file,
    is_within_project,
    was_tool_successful,
)


class TestGetFilePath:
    """Tests for get_file_path function."""

    def test_get_file_path_present(self) -> None:
        """Test extracting file_path when present."""
        tool_input: ToolInput = {"file_path": "/path/to/file.py"}
        assert get_file_path(tool_input) == "/path/to/file.py"

    def test_get_file_path_absent(self) -> None:
        """Test extracting file_path when absent."""
        tool_input: ToolInput = {}
        assert get_file_path(tool_input) == ""

    def test_get_file_path_empty_string(self) -> None:
        """Test extracting empty file_path."""
        tool_input: ToolInput = {"file_path": ""}
        assert get_file_path(tool_input) == ""


class TestGetCommand:
    """Tests for get_command function."""

    def test_get_command_present(self) -> None:
        """Test extracting command when present."""
        tool_input: ToolInput = {"command": "echo hello"}
        assert get_command(tool_input) == "echo hello"

    def test_get_command_absent(self) -> None:
        """Test extracting command when absent."""
        tool_input: ToolInput = {}
        assert get_command(tool_input) == ""

    def test_get_command_complex(self) -> None:
        """Test extracting complex command."""
        tool_input: ToolInput = {"command": "git commit -m 'test message'"}
        assert get_command(tool_input) == "git commit -m 'test message'"


class TestWasToolSuccessful:
    """Tests for was_tool_successful function."""

    def test_tool_success_true(self) -> None:
        """Test tool_response with success=True."""
        tool_response: dict[str, object] = {"success": True}
        assert was_tool_successful(tool_response) is True

    def test_tool_success_false(self) -> None:
        """Test tool_response with success=False."""
        tool_response: dict[str, object] = {"success": False}
        assert was_tool_successful(tool_response) is False

    def test_tool_success_absent(self) -> None:
        """Test tool_response without success field (defaults to True)."""
        tool_response: dict[str, object] = {}
        assert was_tool_successful(tool_response) is True

    def test_tool_success_with_additional_fields(self) -> None:
        """Test tool_response with additional fields."""
        tool_response: dict[str, object] = {
            "success": True,
            "filePath": "/path/to/file.py",
            "other": "data"
        }
        assert was_tool_successful(tool_response) is True


class TestGetToolResponseField:
    """Tests for get_tool_response_field function."""

    def test_get_field_present(self) -> None:
        """Test extracting field when present."""
        tool_response: dict[str, object] = {"filePath": "/path/to/file.py"}
        assert get_tool_response_field(tool_response, "filePath") == "/path/to/file.py"

    def test_get_field_absent_with_default(self) -> None:
        """Test extracting field when absent with default value."""
        tool_response: dict[str, object] = {}
        assert get_tool_response_field(tool_response, "filePath", "") == ""

    def test_get_field_absent_without_default(self) -> None:
        """Test extracting field when absent without default (returns None)."""
        tool_response: dict[str, object] = {}
        assert get_tool_response_field(tool_response, "filePath") is None

    def test_get_field_with_various_types(self) -> None:
        """Test extracting fields of various types."""
        tool_response: dict[str, object] = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3]
        }
        assert get_tool_response_field(tool_response, "string") == "value"
        assert get_tool_response_field(tool_response, "number") == 42
        assert get_tool_response_field(tool_response, "boolean") is True
        assert get_tool_response_field(tool_response, "list") == [1, 2, 3]


class TestIsPythonFile:
    """Tests for is_python_file function."""

    def test_python_file_py_extension(self) -> None:
        """Test identifying .py files."""
        assert is_python_file("test.py") is True
        assert is_python_file("/path/to/file.py") is True
        assert is_python_file("module/submodule/script.py") is True

    def test_python_file_pyi_extension(self) -> None:
        """Test identifying .pyi stub files."""
        assert is_python_file("test.pyi") is True
        assert is_python_file("/path/to/stub.pyi") is True

    def test_non_python_files(self) -> None:
        """Test identifying non-Python files."""
        assert is_python_file("test.txt") is False
        assert is_python_file("README.md") is False
        assert is_python_file("config.json") is False
        assert is_python_file("test.pyc") is False
        assert is_python_file("test") is False

    def test_edge_cases(self) -> None:
        """Test edge cases."""
        assert is_python_file("") is False
        assert is_python_file(".py") is True
        assert is_python_file("file.PY") is False  # Case sensitive


class TestIsWithinProject:
    """Tests for is_within_project function."""

    def test_file_within_project(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test file within project directory."""
        project_dir = "/project/root"
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", project_dir)

        # Absolute path within project
        assert is_within_project("/project/root/file.py") is True
        assert is_within_project("/project/root/subdir/file.py") is True

    def test_file_outside_project(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test file outside project directory."""
        project_dir = "/project/root"
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", project_dir)

        # File outside project
        assert is_within_project("/other/path/file.py") is False
        assert is_within_project("/project/other/file.py") is False

    def test_path_traversal_attack(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test detection of path traversal attempts."""
        project_dir = "/project/root"
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", project_dir)

        # These should be caught by path resolution
        # Note: The actual behavior depends on how resolve() handles these
        result = is_within_project("/project/root/../../../etc/passwd")
        # After resolution, this path is outside project
        assert result is False


class TestGetProjectDir:
    """Tests for get_project_dir function."""

    def test_get_project_dir_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting project directory from environment variable."""
        expected_dir = "/custom/project/path"
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", expected_dir)

        project_dir = get_project_dir()
        assert str(project_dir) == expected_dir

    def test_get_project_dir_default_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting project directory defaults to cwd when env var not set."""
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        project_dir = get_project_dir()
        assert project_dir == Path(os.getcwd())

    def test_get_project_dir_returns_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_project_dir returns Path object."""
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/path")

        project_dir = get_project_dir()
        assert isinstance(project_dir, Path)
