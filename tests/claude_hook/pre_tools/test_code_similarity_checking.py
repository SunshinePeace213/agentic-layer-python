#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Unit Tests for Code Similarity Checking Hook
==============================================

Comprehensive test suite for code_similarity_checking.py hook.

Test Categories:
    1. Pattern Detection Tests
    2. File Search Tests
    3. Similarity Calculation Tests
    4. Directory Monitoring Tests
    5. Integration Tests
    6. Error Handling Tests
    7. Edge Cases

Execution:
    uv run pytest -n auto tests/claude_hook/pre_tools/test_code_similarity_checking.py

Author: Claude Code Hook Expert
Version: 1.0.0
"""

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Callable, Optional, TypedDict, cast
from unittest.mock import patch

import pytest

# Add hook directory to path for imports
hook_dir = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "pre_tools"
sys.path.insert(0, str(hook_dir))

from code_similarity_checking import (  # type: ignore  # noqa: E402
    calculate_similarity as _calc_sim,  # type: ignore
    create_similarity_error_message as _create_err_msg,  # type: ignore
    detect_versioned_pattern as _detect_pattern,  # type: ignore
    find_similar_files as _find_similar,  # type: ignore
    get_file_content as _get_content,  # type: ignore
    is_allowed_extension as _is_allowed_ext,  # type: ignore
    is_in_monitored_directory as _is_monitored,  # type: ignore
    quick_similarity_check as _quick_sim,  # type: ignore
    validate_write_operation as _validate_write,  # type: ignore
)

# Type-annotated wrappers for imported functions
detect_versioned_pattern: Callable[[str], Optional[str]] = _detect_pattern  # type: ignore
is_allowed_extension: Callable[[str], bool] = _is_allowed_ext  # type: ignore
is_in_monitored_directory: Callable[[str], bool] = _is_monitored  # type: ignore
find_similar_files: Callable[[str, str], list[str]] = _find_similar  # type: ignore
calculate_similarity: Callable[[str, str], float] = _calc_sim  # type: ignore
quick_similarity_check: Callable[[str, str], Optional[float]] = _quick_sim  # type: ignore
get_file_content: Callable[[str], Optional[str]] = _get_content  # type: ignore
validate_write_operation: Callable[[str, str], Optional[str]] = _validate_write  # type: ignore
create_similarity_error_message: Callable[[str, str, float], str] = _create_err_msg  # type: ignore


# ==================== Type Definitions ====================


class HookSpecificOutputDict(TypedDict):
    """Type definition for hook specific output."""

    hookEventName: str
    permissionDecision: str
    permissionDecisionReason: str


class HookOutputDict(TypedDict):
    """Type definition for hook output."""

    hookSpecificOutput: HookSpecificOutputDict
    suppressOutput: bool


# ==================== Fixtures ====================


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory with test files."""
    # Create directory structure
    (tmp_path / "utils").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "other").mkdir()

    # Create sample files
    sample_content = """#!/usr/bin/env python3
def hello_world():
    print("Hello, world!")
    return 42

if __name__ == "__main__":
    hello_world()
"""

    similar_content = """#!/usr/bin/env python3
def hello_world():
    print("Hello, world!")
    print("Additional line")
    return 42

if __name__ == "__main__":
    hello_world()
"""

    different_content = """#!/usr/bin/env python3
def goodbye_world():
    print("Goodbye, world!")
    return 0

def main():
    goodbye_world()
"""

    (tmp_path / "utils" / "helper.py").write_text(sample_content)
    (tmp_path / "utils" / "helper_old.py").write_text(similar_content)
    (tmp_path / "src" / "main.py").write_text(different_content)

    return tmp_path


# ==================== Pattern Detection Tests ====================


class TestPatternDetection:
    """Test versioned pattern detection."""

    def test_detect_version_suffix(self) -> None:
        """Test version suffix pattern detection."""
        assert detect_versioned_pattern("file_v2.py") == "file.py"
        assert detect_versioned_pattern("script_v10.py") == "script.py"
        assert detect_versioned_pattern("utils/parser_version2.py") == "utils/parser.py"
        assert detect_versioned_pattern("module_v1_final.py") is not None

    def test_detect_number_suffix(self) -> None:
        """Test number suffix detection."""
        assert detect_versioned_pattern("file_2.py") == "file.py"
        assert detect_versioned_pattern("script-3.py") == "script.py"
        assert detect_versioned_pattern("test_10.py") == "test.py"

    def test_detect_parentheses_number(self) -> None:
        """Test parentheses number pattern."""
        assert detect_versioned_pattern("file (2).py") == "file.py"
        assert detect_versioned_pattern("script (10).py") == "script.py"

    def test_detect_date_suffix(self) -> None:
        """Test date suffix detection."""
        assert detect_versioned_pattern("backup_20240101.py") == "backup.py"
        assert detect_versioned_pattern("file_20231231.py") == "file.py"

    def test_detect_iteration_suffix(self) -> None:
        """Test iteration suffix detection."""
        assert detect_versioned_pattern("file_copy.py") == "file.py"
        assert detect_versioned_pattern("script_backup.py") == "script.py"
        assert detect_versioned_pattern("module_old.py") == "module.py"
        assert detect_versioned_pattern("code_new.py") == "code.py"
        assert detect_versioned_pattern("test_final.py") == "test.py"

    def test_detect_backup_extensions(self) -> None:
        """Test backup extension detection."""
        assert detect_versioned_pattern("file.py.bak") == "file.py"
        assert detect_versioned_pattern("script.py~") == "script.py"
        assert detect_versioned_pattern("code.py.old") == "code.py"
        assert detect_versioned_pattern("test.py.orig") == "test.py"

    def test_no_pattern_detected(self) -> None:
        """Test files without version patterns."""
        assert detect_versioned_pattern("file.py") is None
        assert detect_versioned_pattern("normal_script.py") is None
        assert detect_versioned_pattern("utils/helper.py") is None
        assert detect_versioned_pattern("test_module.py") is None

    def test_semantic_numbers_not_detected(self) -> None:
        """Test that semantic numbers are not falsely detected."""
        # These should not be detected as version patterns
        assert detect_versioned_pattern("python3.py") is None
        assert detect_versioned_pattern("http2_client.py") is None
        assert detect_versioned_pattern("base64_encoder.py") is None

    def test_path_with_directories(self) -> None:
        """Test pattern detection with directory paths."""
        result1 = detect_versioned_pattern("src/utils/parser_v2.py")
        assert result1 is not None and "parser.py" in result1

        result2 = detect_versioned_pattern("./utils/helper_2.py")
        assert result2 is not None and "helper.py" in result2


class TestAllowedExtensions:
    """Test allowed extension checking."""

    def test_backup_extension_allowed(self) -> None:
        """Test .backup extension is allowed."""
        assert is_allowed_extension("file.py.backup") is True
        assert is_allowed_extension("utils/script.py.backup") is True

    def test_other_extensions_not_allowed(self) -> None:
        """Test other extensions are not allowed."""
        assert is_allowed_extension("file.py.bak") is False
        assert is_allowed_extension("file.py") is False
        assert is_allowed_extension("file.py.old") is False


class TestMonitoredDirectories:
    """Test monitored directory checking."""

    def test_monitored_directory(self, temp_project_dir: Path) -> None:
        """Test files in monitored directories."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            assert is_in_monitored_directory(
                str(temp_project_dir / "utils" / "file.py")
            )
            assert is_in_monitored_directory(str(temp_project_dir / "src" / "file.py"))

    def test_non_monitored_directory(self, temp_project_dir: Path) -> None:
        """Test files outside monitored directories."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            # 'other' is not in default monitored dirs
            result = is_in_monitored_directory(
                str(temp_project_dir / "other" / "file.py")
            )
            # Should return False since 'other' is not monitored
            assert result is False


# ==================== Similarity Calculation Tests ====================


class TestSimilarityCalculation:
    """Test content similarity calculation."""

    def test_identical_content(self) -> None:
        """Test similarity of identical content."""
        content = "print('hello world')\n"
        similarity = calculate_similarity(content, content)
        assert similarity == 1.0

    def test_very_similar_content(self) -> None:
        """Test similarity of very similar content."""
        content1 = """def hello():
    print("Hello")
    return 42
"""
        content2 = """def hello():
    print("Hello")
    print("Extra line")
    return 42
"""
        similarity = calculate_similarity(content1, content2)
        # Should be high similarity (>0.7) but not identical
        assert 0.7 <= similarity < 1.0

    def test_different_content(self) -> None:
        """Test similarity of different content."""
        content1 = """def hello():
    print("Hello")
"""
        content2 = """def goodbye():
    print("Goodbye")
    print("See you later")
    print("Farewell")
"""
        similarity = calculate_similarity(content1, content2)
        # Should be low similarity
        assert similarity < 0.6

    def test_empty_content(self) -> None:
        """Test similarity with empty content."""
        content = "print('hello')\n"
        similarity1 = calculate_similarity("", content)
        similarity2 = calculate_similarity(content, "")
        similarity3 = calculate_similarity("", "")

        assert similarity1 == 0.0
        assert similarity2 == 0.0
        assert similarity3 == 1.0  # Empty equals empty


class TestQuickSimilarityCheck:
    """Test quick similarity check optimization."""

    def test_identical_quick_check(self) -> None:
        """Test quick check detects identical content."""
        content = "print('hello world')\n"
        result = quick_similarity_check(content, content)
        assert result == 1.0

    def test_very_different_size_quick_check(self) -> None:
        """Test quick check detects very different sizes."""
        content1 = "x" * 1000
        content2 = "y" * 100
        result = quick_similarity_check(content1, content2)
        assert result == 0.0

    def test_empty_content_quick_check(self) -> None:
        """Test quick check with empty content."""
        content = "print('hello')\n"
        result1 = quick_similarity_check("", content)
        result2 = quick_similarity_check(content, "")

        assert result1 == 0.0
        assert result2 == 0.0

    def test_needs_full_check(self) -> None:
        """Test quick check returns None when full check needed."""
        content1 = "def hello():\n    print('Hello')\n"
        content2 = "def hello():\n    print('Hi')\n"
        result = quick_similarity_check(content1, content2)
        # Should return None (needs full check)
        assert result is None


# ==================== File Operations Tests ====================


class TestFileOperations:
    """Test file reading and searching."""

    def test_get_file_content_success(self, temp_project_dir: Path) -> None:
        """Test reading file content successfully."""
        file_path = temp_project_dir / "utils" / "helper.py"
        content = get_file_content(str(file_path))

        assert content is not None
        assert "hello_world" in content

    def test_get_file_content_nonexistent(self) -> None:
        """Test reading nonexistent file."""
        content = get_file_content("/nonexistent/file.py")
        assert content is None

    def test_find_similar_files(self, temp_project_dir: Path) -> None:
        """Test finding similar files."""
        base_path = str(temp_project_dir / "utils" / "helper.py")
        directory = str(temp_project_dir / "utils")

        similar_files = find_similar_files(base_path, directory)

        # Should find both helper.py and helper_old.py
        assert len(similar_files) >= 1
        assert any("helper" in f for f in similar_files)

    def test_find_similar_files_nonexistent_dir(self) -> None:
        """Test finding files in nonexistent directory."""
        similar_files = find_similar_files("file.py", "/nonexistent/dir")
        assert similar_files == []


# ==================== Integration Tests ====================


class TestValidateWriteOperation:
    """Test main validation logic."""

    def test_allow_first_file(self, temp_project_dir: Path) -> None:
        """Test allowing first file without similar existing files."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "new_module.py")
            content = "def new_function():\n    pass\n"

            error = validate_write_operation(file_path, content)
            assert error is None

    def test_allow_different_content(self, temp_project_dir: Path) -> None:
        """Test allowing file with different content."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "helper_v2.py")
            # Very different content from existing helper.py
            content = (
                """def completely_different():
    return "totally new implementation"
    # Many more lines to ensure difference
"""
                * 10
            )

            error = validate_write_operation(file_path, content)
            # Should allow due to low similarity
            assert error is None

    def test_deny_similar_content(self, temp_project_dir: Path) -> None:
        """Test denying file with very similar content."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            # Get existing content
            existing_file = temp_project_dir / "utils" / "helper.py"
            existing_content = existing_file.read_text()

            # Create new versioned file with nearly identical content
            file_path = str(temp_project_dir / "utils" / "helper_v2.py")
            # Slightly modify but keep very similar (>85%)
            content = existing_content.replace("Hello", "Hello")

            error = validate_write_operation(file_path, content)
            # Should deny due to high similarity
            assert error is not None
            assert "Duplicate File Detected" in error
            assert "helper.py" in error

    def test_allow_no_version_pattern(self, temp_project_dir: Path) -> None:
        """Test allowing file without version pattern."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "new_helper.py")
            content = "def new_helper():\n    pass\n"

            error = validate_write_operation(file_path, content)
            # Should allow because no version pattern detected
            assert error is None

    def test_allow_backup_extension(self, temp_project_dir: Path) -> None:
        """Test allowing .backup extension."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "helper.py.backup")
            content = "any content here"

            error = validate_write_operation(file_path, content)
            # Should allow because .backup is allowed extension
            assert error is None

    def test_allow_outside_monitored_dirs(self, temp_project_dir: Path) -> None:
        """Test allowing files outside monitored directories."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            # 'other' is not in monitored directories
            file_path = str(temp_project_dir / "other" / "file_v2.py")
            content = "def test():\n    pass\n"

            error = validate_write_operation(file_path, content)
            # Should allow because directory is not monitored
            assert error is None

    def test_hook_disabled(self, temp_project_dir: Path) -> None:
        """Test hook behavior when disabled."""
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_PROJECT_DIR": str(temp_project_dir),
                "CODE_SIMILARITY_ENABLED": "false",
            },
        ):
            file_path = str(temp_project_dir / "utils" / "helper_v2.py")
            content = "any content"

            # Reimport to pick up new environment variable
            import importlib
            import code_similarity_checking

            importlib.reload(code_similarity_checking)
            validate_func: Callable[[str, str], Optional[str]] = (
                code_similarity_checking.validate_write_operation  # type: ignore
            )

            error = validate_func(file_path, content)
            # Should allow because hook is disabled
            assert error is None


# ==================== Error Message Tests ====================


class TestErrorMessages:
    """Test error message generation."""

    def test_create_similarity_error_message(self) -> None:
        """Test error message creation."""
        new_file = "utils/parser_v2.py"
        existing_file = "utils/parser.py"
        similarity = 0.87

        message = create_similarity_error_message(new_file, existing_file, similarity)

        assert "Duplicate File Detected" in message
        assert new_file in message
        assert existing_file in message
        assert "87%" in message
        assert "Edit(" in message
        assert "git" in message.lower()


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_content(self, temp_project_dir: Path) -> None:
        """Test validation with empty content."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "empty_v2.py")
            content = ""

            error = validate_write_operation(file_path, content)
            # Should handle gracefully
            assert error is None

    def test_very_large_similarity_difference(self, temp_project_dir: Path) -> None:
        """Test with very different file sizes."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            file_path = str(temp_project_dir / "utils" / "helper_v2.py")
            # Very large content, completely different
            content = "x" * 10000

            error = validate_write_operation(file_path, content)
            # Should allow due to size difference
            assert error is None

    def test_special_characters_in_path(self, temp_project_dir: Path) -> None:
        """Test handling paths with special characters."""
        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            # Create directory with spaces
            special_dir = temp_project_dir / "utils with spaces"
            special_dir.mkdir()

            file_path = str(special_dir / "file_v2.py")
            content = "def test():\n    pass\n"

            # Should handle gracefully without crashing
            error = validate_write_operation(file_path, content)
            # Allow because no similar file exists
            assert error is None


# ==================== Main Entry Point Test ====================


class TestMainEntryPoint:
    """Test the main() function and CLI integration."""

    def test_main_write_tool_deny(self, temp_project_dir: Path) -> None:
        """Test main function denies similar file."""
        # Get existing content
        existing_file = temp_project_dir / "utils" / "helper.py"
        existing_content = existing_file.read_text()

        # Prepare hook input
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": str(temp_project_dir),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(temp_project_dir / "utils" / "helper_v2.py"),
                "content": existing_content,  # Same content
            },
        }

        # Mock stdin
        stdin_data = json.dumps(hook_input)

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(temp_project_dir)}):
            # Reload module to pick up new environment variable
            import importlib
            import code_similarity_checking

            importlib.reload(code_similarity_checking)

            with patch("sys.stdin", StringIO(stdin_data)):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    try:
                        code_similarity_checking.main()  # type: ignore
                    except SystemExit:
                        pass

                    output = mock_stdout.getvalue()
                    result = cast(HookOutputDict, json.loads(output))

                    # Should deny due to identical content
                    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert (
                        "Duplicate"
                        in result["hookSpecificOutput"]["permissionDecisionReason"]
                    )

    def test_main_non_write_tool(self) -> None:
        """Test main function allows non-Write tools."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/tmp",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.py"},
        }

        stdin_data = json.dumps(hook_input)

        with patch("sys.stdin", StringIO(stdin_data)):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                from code_similarity_checking import main  # type: ignore

                try:
                    main()  # type: ignore
                except SystemExit:
                    pass

                output = mock_stdout.getvalue()
                result = cast(HookOutputDict, json.loads(output))

                # Should allow non-Write tools
                assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_main_error_handling(self) -> None:
        """Test main function error handling."""
        # Invalid JSON input
        stdin_data = "invalid json"

        with patch("sys.stdin", StringIO(stdin_data)):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                from code_similarity_checking import main  # type: ignore

                try:
                    main()  # type: ignore
                except SystemExit:
                    pass

                output = mock_stdout.getvalue()
                result = cast(HookOutputDict, json.loads(output))

                # Should fail-safe to allow
                assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
                reason: str = result["hookSpecificOutput"]["permissionDecisionReason"]
                assert "fail-safe" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
