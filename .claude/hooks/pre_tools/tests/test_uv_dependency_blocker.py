#!/usr/bin/env python3
"""
Comprehensive pytest-based tests for the uv_dependency_blocker PreToolUse hook.

Test Categories:
1. File Detection Tests
2. Bash Command Parsing Tests
3. Validation Function Tests
4. Integration Tests - Write Tool
5. Integration Tests - Edit Tool
6. Integration Tests - MultiEdit Tool
7. Integration Tests - Bash Tool
8. Edge Cases and Error Handling

Usage:
    # Run all tests
    uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py -v

    # Run with coverage
    uv run pytest --cov=.claude/hooks/pre_tools/uv_dependency_blocker.py \
        .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py

    # Run distributed (parallel)
    uv run pytest -n auto .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py
"""

import json
import sys
from io import StringIO
from pathlib import Path
from typing import NotRequired, TypedDict, cast
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class HookSpecificOutput(TypedDict):
    """Type definition for hook specific output."""
    hookEventName: str
    permissionDecision: str
    permissionDecisionReason: str


class HookOutputResult(TypedDict):
    """Type definition for hook output result."""
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: NotRequired[bool]

try:
    from uv_dependency_blocker import (
        is_dependency_file,
        extract_file_paths_from_bash,
        get_uv_alternatives,
        validate_write_operation,
        validate_edit_operation,
        validate_bash_command,
        main,
        DEPENDENCY_FILES,
    )
except ImportError:
    pytest.skip("Could not import uv_dependency_blocker", allow_module_level=True)


# ==================== File Detection Tests ====================

class TestFileDetection:
    """Test detection of dependency files."""

    def test_detect_requirements_txt(self):
        """Test detection of requirements.txt."""
        assert is_dependency_file("requirements.txt") is True
        assert is_dependency_file("./requirements.txt") is True
        assert is_dependency_file("/path/to/requirements.txt") is True

    def test_detect_pyproject_toml(self):
        """Test detection of pyproject.toml."""
        assert is_dependency_file("pyproject.toml") is True
        assert is_dependency_file("./pyproject.toml") is True
        assert is_dependency_file("/project/pyproject.toml") is True

    def test_detect_uv_lock(self):
        """Test detection of uv.lock."""
        assert is_dependency_file("uv.lock") is True
        assert is_dependency_file("./uv.lock") is True
        assert is_dependency_file("/workspace/uv.lock") is True

    def test_detect_pipfile(self):
        """Test detection of Pipfile."""
        assert is_dependency_file("Pipfile") is True
        assert is_dependency_file("./Pipfile") is True
        assert is_dependency_file("/app/Pipfile") is True

    def test_detect_pipfile_lock(self):
        """Test detection of Pipfile.lock."""
        assert is_dependency_file("Pipfile.lock") is True
        assert is_dependency_file("./Pipfile.lock") is True
        assert is_dependency_file("/home/user/project/Pipfile.lock") is True

    def test_allow_non_dependency_files(self):
        """Test that non-dependency files are not detected."""
        assert is_dependency_file("main.py") is False
        assert is_dependency_file("README.md") is False
        assert is_dependency_file("config.json") is False
        assert is_dependency_file("src/utils.py") is False

    def test_reject_similar_filenames(self):
        """Test that similar but different filenames are not detected."""
        assert is_dependency_file("requirements.txt.bak") is False
        assert is_dependency_file("requirements_old.txt") is False
        assert is_dependency_file("pyproject.toml.template") is False
        assert is_dependency_file("uv.lock.backup") is False

    def test_handle_empty_file_path(self):
        """Test handling of empty file path."""
        assert is_dependency_file("") is False

    def test_dependency_files_set_complete(self):
        """Test that DEPENDENCY_FILES set contains all expected files."""
        expected = {"requirements.txt", "pyproject.toml", "uv.lock", "Pipfile", "Pipfile.lock"}
        assert DEPENDENCY_FILES == expected


# ==================== Bash Command Parsing Tests ====================

class TestBashCommandParsing:
    """Test extraction of file paths from bash commands."""

    def test_extract_redirect_output(self):
        """Test extraction from redirect operators (>)."""
        paths = extract_file_paths_from_bash("echo 'requests' > requirements.txt")
        assert "requirements.txt" in paths

    def test_extract_append_redirect(self):
        """Test extraction from append operators (>>)."""
        paths = extract_file_paths_from_bash("cat file >> pyproject.toml")
        assert "pyproject.toml" in paths

    def test_extract_stderr_redirect(self):
        """Test extraction from stderr redirect (2>)."""
        paths = extract_file_paths_from_bash("command 2> uv.lock")
        assert "uv.lock" in paths

    def test_extract_all_redirect(self):
        """Test extraction from all output redirect (&>)."""
        paths = extract_file_paths_from_bash("build &> Pipfile")
        assert "Pipfile" in paths

    def test_extract_sed_inline_edit(self):
        """Test extraction from sed -i commands."""
        paths = extract_file_paths_from_bash("sed -i 's/old/new/' requirements.txt")
        assert "requirements.txt" in paths

    def test_extract_sed_inline_with_backup(self):
        """Test extraction from sed -i.bak commands."""
        paths = extract_file_paths_from_bash("sed -i.bak 's/foo/bar/' pyproject.toml")
        assert "pyproject.toml" in paths

    def test_extract_perl_inline_edit(self):
        """Test extraction from perl -i commands."""
        paths = extract_file_paths_from_bash("perl -i -pe 's/old/new/' uv.lock")
        assert "uv.lock" in paths

    def test_extract_vi_editor(self):
        """Test extraction from vi editor command."""
        paths = extract_file_paths_from_bash("vi requirements.txt")
        assert "requirements.txt" in paths

    def test_extract_vim_editor(self):
        """Test extraction from vim editor command."""
        paths = extract_file_paths_from_bash("vim pyproject.toml")
        assert "pyproject.toml" in paths

    def test_extract_nano_editor(self):
        """Test extraction from nano editor command."""
        paths = extract_file_paths_from_bash("nano Pipfile")
        assert "Pipfile" in paths

    def test_extract_emacs_editor(self):
        """Test extraction from emacs editor command."""
        paths = extract_file_paths_from_bash("emacs uv.lock")
        assert "uv.lock" in paths

    def test_extract_multiple_paths(self):
        """Test extraction of multiple file paths from complex commands."""
        paths = extract_file_paths_from_bash("echo foo > requirements.txt && sed -i 's/a/b/' pyproject.toml")
        assert "requirements.txt" in paths
        assert "pyproject.toml" in paths

    def test_allow_read_operations(self):
        """Test that read-only operations don't extract paths."""
        paths = extract_file_paths_from_bash("cat requirements.txt")
        assert len(paths) == 0

    def test_allow_grep_operations(self):
        """Test that grep operations don't extract paths."""
        paths = extract_file_paths_from_bash("grep 'package' pyproject.toml")
        assert len(paths) == 0


# ==================== UV Alternatives Tests ====================

class TestUVAlternatives:
    """Test UV alternative command generation."""

    def test_alternatives_for_requirements_txt(self):
        """Test alternatives for requirements.txt."""
        alternatives = get_uv_alternatives("requirements.txt")
        assert "uv add" in alternatives
        assert "uv remove" in alternatives
        assert "uv sync" in alternatives
        assert "pyproject.toml" in alternatives

    def test_alternatives_for_pyproject_toml(self):
        """Test alternatives for pyproject.toml."""
        alternatives = get_uv_alternatives("pyproject.toml")
        assert "uv add" in alternatives
        assert "uv add --dev" in alternatives
        assert "uv lock" in alternatives

    def test_alternatives_for_uv_lock(self):
        """Test alternatives for uv.lock."""
        alternatives = get_uv_alternatives("uv.lock")
        assert "uv lock" in alternatives
        assert "Never edit uv.lock manually" in alternatives
        assert "auto-generated" in alternatives

    def test_alternatives_for_pipfile(self):
        """Test alternatives for Pipfile."""
        alternatives = get_uv_alternatives("Pipfile")
        assert "uv add" in alternatives
        assert "migrating from Pipenv" in alternatives

    def test_alternatives_for_pipfile_lock(self):
        """Test alternatives for Pipfile.lock."""
        alternatives = get_uv_alternatives("Pipfile.lock")
        assert "uv add" in alternatives
        assert "migrating from Pipenv" in alternatives

    def test_alternatives_for_unknown_file(self):
        """Test alternatives for unknown files (fallback)."""
        alternatives = get_uv_alternatives("unknown.txt")
        assert "uv add" in alternatives
        assert "uv remove" in alternatives


# ==================== Validation Function Tests ====================

class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_write_operation_blocks_requirements_txt(self):
        """Test that write operations on requirements.txt are blocked."""
        result = validate_write_operation("requirements.txt")
        assert result is not None
        assert "Blocked" in result
        assert "requirements.txt" in result
        assert "uv add" in result

    def test_validate_write_operation_blocks_pyproject_toml(self):
        """Test that write operations on pyproject.toml are blocked."""
        result = validate_write_operation("pyproject.toml")
        assert result is not None
        assert "Blocked" in result
        assert "pyproject.toml" in result

    def test_validate_write_operation_blocks_uv_lock(self):
        """Test that write operations on uv.lock are blocked."""
        result = validate_write_operation("uv.lock")
        assert result is not None
        assert "Blocked" in result
        assert "Never edit uv.lock manually" in result

    def test_validate_write_operation_allows_normal_files(self):
        """Test that write operations on normal files are allowed."""
        assert validate_write_operation("main.py") is None
        assert validate_write_operation("README.md") is None
        assert validate_write_operation("src/utils.py") is None

    def test_validate_edit_operation_blocks_dependency_files(self):
        """Test that edit operations on dependency files are blocked."""
        result = validate_edit_operation("requirements.txt")
        assert result is not None
        assert "Blocked" in result

    def test_validate_edit_operation_allows_normal_files(self):
        """Test that edit operations on normal files are allowed."""
        assert validate_edit_operation("config.py") is None

    def test_validate_bash_command_blocks_redirect(self):
        """Test that bash redirects to dependency files are blocked."""
        result = validate_bash_command("echo 'requests' > requirements.txt")
        assert result is not None
        assert "Blocked" in result
        assert "requirements.txt" in result
        assert "echo 'requests' > requirements.txt" in result

    def test_validate_bash_command_blocks_sed(self):
        """Test that sed inline edits on dependency files are blocked."""
        result = validate_bash_command("sed -i 's/old/new/' pyproject.toml")
        assert result is not None
        assert "Blocked" in result
        assert "pyproject.toml" in result

    def test_validate_bash_command_blocks_editor(self):
        """Test that editor commands on dependency files are blocked."""
        result = validate_bash_command("vim uv.lock")
        assert result is not None
        assert "Blocked" in result
        assert "uv.lock" in result

    def test_validate_bash_command_allows_read(self):
        """Test that read-only bash commands are allowed."""
        assert validate_bash_command("cat requirements.txt") is None
        assert validate_bash_command("grep package pyproject.toml") is None
        assert validate_bash_command("less uv.lock") is None

    def test_validate_bash_command_allows_normal_operations(self):
        """Test that normal bash commands are allowed."""
        assert validate_bash_command("echo hello > output.txt") is None
        assert validate_bash_command("sed -i 's/a/b/' config.txt") is None


# ==================== Integration Tests - Write Tool ====================

class TestWriteToolIntegration:
    """Integration tests for Write tool operations."""

    def test_write_tool_blocks_requirements_txt(self):
        """Test Write tool blocking for requirements.txt."""
        mock_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "requirements.txt",
                "content": "requests>=2.28.0"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "requirements.txt" in result["hookSpecificOutput"]["permissionDecisionReason"]
                    assert "uv add" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_write_tool_blocks_pyproject_toml(self):
        """Test Write tool blocking for pyproject.toml."""
        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "pyproject.toml",
                "content": "[project]\nname = 'test'"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "pyproject.toml" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_write_tool_allows_normal_files(self):
        """Test Write tool allows normal file operations."""
        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "main.py",
                "content": "print('hello')"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Integration Tests - Edit Tool ====================

class TestEditToolIntegration:
    """Integration tests for Edit tool operations."""

    def test_edit_tool_blocks_uv_lock(self):
        """Test Edit tool blocking for uv.lock."""
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "uv.lock",
                "old_string": "old",
                "new_string": "new"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "uv.lock" in result["hookSpecificOutput"]["permissionDecisionReason"]
                    assert "Never edit uv.lock manually" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_edit_tool_allows_normal_files(self):
        """Test Edit tool allows normal file edits."""
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "config.py",
                "old_string": "DEBUG = False",
                "new_string": "DEBUG = True"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Integration Tests - MultiEdit Tool ====================

class TestMultiEditToolIntegration:
    """Integration tests for MultiEdit tool operations."""

    def test_multiedit_tool_blocks_pipfile(self):
        """Test MultiEdit tool blocking for Pipfile."""
        mock_input = json.dumps({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": "Pipfile",
                "edits": [{"old": "old", "new": "new"}]
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "Pipfile" in result["hookSpecificOutput"]["permissionDecisionReason"]


# ==================== Integration Tests - Bash Tool ====================

class TestBashToolIntegration:
    """Integration tests for Bash tool operations."""

    def test_bash_tool_blocks_redirect_to_requirements(self):
        """Test Bash tool blocking redirects to requirements.txt."""
        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": "echo 'django>=4.0' >> requirements.txt"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "requirements.txt" in result["hookSpecificOutput"]["permissionDecisionReason"]
                    assert "echo 'django>=4.0' >> requirements.txt" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_bash_tool_blocks_sed_on_pyproject(self):
        """Test Bash tool blocking sed on pyproject.toml."""
        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": "sed -i 's/version = \"1.0\"/version = \"2.0\"/' pyproject.toml"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "pyproject.toml" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_bash_tool_allows_read_operations(self):
        """Test Bash tool allows read operations on dependency files."""
        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": "cat requirements.txt | grep requests"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_bash_tool_allows_normal_operations(self):
        """Test Bash tool allows normal bash operations."""
        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": "python script.py > output.log"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Edge Cases and Error Handling ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file_path(self):
        """Test handling of empty file path."""
        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "",
                "content": "test"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
                    assert "No file path" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_empty_bash_command(self):
        """Test handling of empty bash command."""
        mock_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {
                "command": ""
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
                    assert "No command" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        mock_input = "invalid json"

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.stderr', new=StringIO()):
                    with patch('sys.exit'):
                        main()
                        output = mock_stdout.getvalue()
                        result = cast(HookOutputResult, json.loads(output))

                        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
                        assert "fail-safe" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_unmonitored_tool(self):
        """Test handling of unmonitored tools."""
        mock_input = json.dumps({
            "tool_name": "Read",
            "tool_input": {
                "file_path": "requirements.txt"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
                    assert "not monitored" in result["hookSpecificOutput"]["permissionDecisionReason"]

    def test_suppress_output_flag(self):
        """Test that suppressOutput flag is set for deny decisions."""
        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "uv.lock",
                "content": "modified"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert result.get("suppressOutput") is True

    def test_path_with_directory_prefix(self):
        """Test dependency files with directory prefixes."""
        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/root/requirements.txt",
                "content": "test"
            }
        })

        with patch('sys.stdin', StringIO(mock_input)):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                with patch('sys.exit'):
                    main()
                    output = mock_stdout.getvalue()
                    result = cast(HookOutputResult, json.loads(output))

                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
