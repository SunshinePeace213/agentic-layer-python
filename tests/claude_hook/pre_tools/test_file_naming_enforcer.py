#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-xdist>=3.0.0",
# ]
# ///
"""
Unit Tests for File Naming Convention Enforcer Hook
====================================================

Comprehensive test suite for file_naming_enforcer.py hook.

Test Categories:
    1. Blocked Extension Tests
    2. Version Suffix Tests
    3. Iteration Suffix Tests
    4. Number Suffix Tests
    5. Test/Temp Location Tests
    6. Python Naming Tests
    7. Bash Command Parsing Tests
    8. Allowlist Tests
    9. Integration Tests
    10. Error Handling Tests

Execution:
    uv run pytest -n auto tests/claude-hook/pre_tools/test_file_naming_enforcer.py

Author: Claude Code Hook Expert
Version: 1.0.0
"""

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Callable, Optional, TypedDict
from unittest.mock import patch
import pytest

# Add hook directory to path for imports
hook_dir = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "pre_tools"
sys.path.insert(0, str(hook_dir))

from file_naming_enforcer import (  # type: ignore  # noqa: E402
    is_allowlisted as _is_allowlisted,  # type: ignore
    has_blocked_extension as _has_blocked_ext,  # type: ignore
    has_version_suffix as _has_version_suffix,  # type: ignore
    has_iteration_suffix as _has_iteration_suffix,  # type: ignore
    has_number_suffix as _has_number_suffix,  # type: ignore
    is_test_temp_in_wrong_location as _is_test_temp_wrong,  # type: ignore
    has_invalid_python_naming as _has_invalid_python,  # type: ignore
    extract_file_paths_from_bash as _extract_bash_paths,  # type: ignore
    validate_file_path as _validate_path,  # type: ignore
)

# Type-annotated wrappers for imported functions
is_allowlisted: Callable[[str], bool] = _is_allowlisted  # type: ignore
has_blocked_extension: Callable[[str], bool] = _has_blocked_ext  # type: ignore
has_version_suffix: Callable[[str], bool] = _has_version_suffix  # type: ignore
has_iteration_suffix: Callable[[str], bool] = _has_iteration_suffix  # type: ignore
has_number_suffix: Callable[[str], bool] = _has_number_suffix  # type: ignore
is_test_temp_in_wrong_location: Callable[[str], bool] = _is_test_temp_wrong  # type: ignore
has_invalid_python_naming: Callable[[str], bool] = _has_invalid_python  # type: ignore
extract_file_paths_from_bash: Callable[[str], list[str]] = _extract_bash_paths  # type: ignore
validate_file_path: Callable[[str], Optional[str]] = _validate_path  # type: ignore


# ==================== Test Data ====================


class ToolInput(TypedDict, total=False):
    """Tool input structure."""
    file_path: str
    content: str
    command: str


class HookSpecificOutput(TypedDict, total=False):
    """Hook specific output structure."""
    hookEventName: str
    permissionDecision: str
    permissionDecisionReason: str


class HookOutput(TypedDict):
    """Hook output structure."""
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


class HookInput(TypedDict):
    """Hook input structure."""
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput


def create_write_input(file_path: str) -> HookInput:
    """Create sample Write tool input."""
    tool_input: ToolInput = {
        "file_path": file_path,
        "content": "print('hello')",
    }
    return HookInput(
        session_id="test123",
        transcript_path="/path/to/transcript.jsonl",
        cwd="/project",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input=tool_input,
    )


def create_bash_input(command: str) -> HookInput:
    """Create sample Bash tool input."""
    tool_input: ToolInput = {"command": command}
    return HookInput(
        session_id="test123",
        transcript_path="/path/to/transcript.jsonl",
        cwd="/project",
        hook_event_name="PreToolUse",
        tool_name="Bash",
        tool_input=tool_input,
    )


# ==================== Allowlist Tests ====================


def test_allowlist_readme() -> None:
    """Test that README.md is allowlisted."""
    assert is_allowlisted("README.md") is True
    assert is_allowlisted("readme.md") is True
    assert is_allowlisted("Readme.md") is True


def test_allowlist_setup_py() -> None:
    """Test that setup.py is allowlisted."""
    assert is_allowlisted("setup.py") is True
    assert is_allowlisted("Setup.py") is True


def test_allowlist_init_py() -> None:
    """Test that __init__.py is allowlisted."""
    assert is_allowlisted("__init__.py") is True
    assert is_allowlisted("__main__.py") is True


def test_allowlist_config_files() -> None:
    """Test that config files are allowlisted."""
    assert is_allowlisted(".env.example") is True
    assert is_allowlisted(".env.local") is True
    assert is_allowlisted("config.yaml") is True
    assert is_allowlisted("settings.json") is True


# ==================== Blocked Extension Tests ====================


def test_blocks_backup_extension() -> None:
    """Test that .backup extension is blocked."""
    assert has_blocked_extension("script.py.backup") is True
    assert has_blocked_extension("config.json.backup") is True
    assert has_blocked_extension("main.py.BACKUP") is True


def test_blocks_bak_extension() -> None:
    """Test that .bak extension is blocked."""
    assert has_blocked_extension("script.py.bak") is True
    assert has_blocked_extension("config.json.bak") is True
    assert has_blocked_extension("data.txt.BAK") is True


def test_blocks_old_extension() -> None:
    """Test that .old extension is blocked."""
    assert has_blocked_extension("utils.py.old") is True
    assert has_blocked_extension("config.json.old") is True


def test_blocks_orig_extension() -> None:
    """Test that .orig extension is blocked."""
    assert has_blocked_extension("README.md.orig") is True
    assert has_blocked_extension("main.py.orig") is True


def test_blocks_tilde_suffix() -> None:
    """Test that tilde suffix is blocked."""
    assert has_blocked_extension("main.py~") is True
    assert has_blocked_extension("config.txt~") is True


def test_blocks_vim_swap_files() -> None:
    """Test that Vim swap files are blocked."""
    assert has_blocked_extension("file.swp") is True
    assert has_blocked_extension("file.swo") is True


def test_allows_normal_extensions() -> None:
    """Test that normal extensions are allowed."""
    assert has_blocked_extension("script.py") is False
    assert has_blocked_extension("config.json") is False
    assert has_blocked_extension("data.txt") is False


# ==================== Version Suffix Tests ====================


def test_blocks_version_suffix_underscore() -> None:
    """Test that _v<number> suffix is blocked."""
    assert has_version_suffix("api_v2.py") is True
    assert has_version_suffix("parser_v3.js") is True
    assert has_version_suffix("handler_v10.ts") is True


def test_blocks_version_suffix_hyphen() -> None:
    """Test that -v<number> suffix is blocked."""
    assert has_version_suffix("parser-v3.js") is True
    assert has_version_suffix("handler-v2.ts") is True


def test_blocks_version_word() -> None:
    """Test that _version<number> suffix is blocked."""
    assert has_version_suffix("api_version2.py") is True
    assert has_version_suffix("parser-version3.js") is True


def test_blocks_version_no_separator() -> None:
    """Test that v<number> at end is blocked."""
    assert has_version_suffix("handlerv2.py") is True
    assert has_version_suffix("apiv3.js") is True


def test_allows_semantic_version_in_name() -> None:
    """Test that semantic version names are allowed."""
    # These have 'v2' or 'v3' in the middle, not as a suffix
    assert has_version_suffix("http2_client.py") is False
    assert has_version_suffix("python3_wrapper.py") is False


def test_allows_normal_files() -> None:
    """Test that normal files without version suffixes are allowed."""
    assert has_version_suffix("api.py") is False
    assert has_version_suffix("parser.js") is False
    assert has_version_suffix("handler.ts") is False


# ==================== Iteration Suffix Tests ====================


def test_blocks_final_suffix() -> None:
    """Test that _final suffix is blocked."""
    assert has_iteration_suffix("script_final.py") is True
    assert has_iteration_suffix("code-final.js") is True
    assert has_iteration_suffix("test_FINAL.py") is True


def test_blocks_fixed_suffix() -> None:
    """Test that _fixed suffix is blocked."""
    assert has_iteration_suffix("code_fixed.js") is True
    assert has_iteration_suffix("bug-fixed.py") is True
    assert has_iteration_suffix("utils_fix.js") is True


def test_blocks_update_suffix() -> None:
    """Test that _update suffix is blocked."""
    assert has_iteration_suffix("script_update.py") is True
    assert has_iteration_suffix("test-updated.py") is True


def test_blocks_new_suffix() -> None:
    """Test that _new suffix is blocked."""
    assert has_iteration_suffix("handler_new.ts") is True
    assert has_iteration_suffix("script-new.py") is True


def test_blocks_copy_suffix() -> None:
    """Test that _copy suffix is blocked."""
    assert has_iteration_suffix("utils_copy.py") is True
    assert has_iteration_suffix("main-copy.js") is True


def test_blocks_old_suffix() -> None:
    """Test that _old suffix is blocked."""
    assert has_iteration_suffix("parser_old.py") is True
    assert has_iteration_suffix("handler-old.ts") is True


def test_allows_iteration_in_middle() -> None:
    """Test that iteration words in middle of name are allowed."""
    assert has_iteration_suffix("copy_handler.py") is False
    assert has_iteration_suffix("new_parser.js") is False
    assert has_iteration_suffix("final_result.py") is False


# ==================== Number Suffix Tests ====================


def test_blocks_trailing_number() -> None:
    """Test that trailing numbers are blocked."""
    assert has_number_suffix("file2.py") is True
    assert has_number_suffix("script3.js") is True
    assert has_number_suffix("code10.ts") is True


def test_blocks_underscore_number() -> None:
    """Test that _<number> suffix is blocked."""
    assert has_number_suffix("utils_2.py") is True
    assert has_number_suffix("helper_3.js") is True


def test_blocks_hyphen_number() -> None:
    """Test that -<number> suffix is blocked."""
    assert has_number_suffix("parser-2.ts") is True
    assert has_number_suffix("handler-3.py") is True


def test_allows_semantic_numbers() -> None:
    """Test that semantic numbers are allowed."""
    assert has_number_suffix("python3_wrapper.py") is False
    assert has_number_suffix("http2_client.js") is False
    assert has_number_suffix("base64_encoder.py") is False


def test_allows_date_format() -> None:
    """Test that date formats are allowed."""
    assert has_number_suffix("report_2025_10_30.txt") is False
    assert has_number_suffix("log-2024-12-01.txt") is False


def test_allows_normal_files_without_numbers() -> None:
    """Test that normal files are allowed."""
    assert has_number_suffix("script.py") is False
    assert has_number_suffix("utils.js") is False


# ==================== Test/Temp Location Tests ====================


def test_blocks_test_suffix_in_src() -> None:
    """Test that _test suffix in src directory is blocked."""
    assert is_test_temp_in_wrong_location("src/api_test.py") is True
    assert is_test_temp_in_wrong_location("lib/utils_test.js") is True


def test_blocks_tmp_suffix_outside_tmp() -> None:
    """Test that _tmp suffix outside tmp directory is blocked."""
    assert is_test_temp_in_wrong_location("src/data_tmp.py") is True
    assert is_test_temp_in_wrong_location("lib/utils_tmp.js") is True


def test_blocks_temp_suffix_outside_temp() -> None:
    """Test that _temp suffix outside temp directory is blocked."""
    assert is_test_temp_in_wrong_location("src/file_temp.py") is True


def test_allows_test_in_tests_directory() -> None:
    """Test that test files in tests/ directory are allowed."""
    assert is_test_temp_in_wrong_location("tests/api_test.py") is False
    assert is_test_temp_in_wrong_location("test/utils_test.js") is False
    assert is_test_temp_in_wrong_location("__tests__/component_test.jsx") is False


def test_allows_temp_in_temp_directory() -> None:
    """Test that temp files in temp/ directory are allowed."""
    assert is_test_temp_in_wrong_location("tmp/scratch_tmp.py") is False
    assert is_test_temp_in_wrong_location("temp/data_temp.json") is False
    assert is_test_temp_in_wrong_location(".tmp/file_tmp.txt") is False


def test_allows_files_without_test_temp() -> None:
    """Test that normal files are allowed."""
    assert is_test_temp_in_wrong_location("src/api.py") is False
    assert is_test_temp_in_wrong_location("lib/utils.js") is False


# ==================== Python Naming Tests ====================


def test_blocks_kebab_case_python() -> None:
    """Test that kebab-case in .py files is blocked."""
    assert has_invalid_python_naming("user-handler.py") is True
    assert has_invalid_python_naming("api-client.py") is True


def test_blocks_camel_case_python() -> None:
    """Test that camelCase in .py files is blocked."""
    assert has_invalid_python_naming("userHandler.py") is True
    assert has_invalid_python_naming("apiClient.py") is True


def test_blocks_mixed_case_python() -> None:
    """Test that mixed case in .py files is blocked."""
    assert has_invalid_python_naming("User_Handler.py") is True
    assert has_invalid_python_naming("API_Endpoint.py") is True


def test_allows_snake_case_python() -> None:
    """Test that snake_case in .py files is allowed."""
    assert has_invalid_python_naming("user_handler.py") is False
    assert has_invalid_python_naming("api_client.py") is False


def test_allows_pascal_case_python() -> None:
    """Test that PascalCase in .py files is allowed."""
    assert has_invalid_python_naming("UserHandler.py") is False
    assert has_invalid_python_naming("ApiClient.py") is False


def test_allows_special_python_files() -> None:
    """Test that special Python files are allowed."""
    assert has_invalid_python_naming("__init__.py") is False
    assert has_invalid_python_naming("__main__.py") is False
    assert has_invalid_python_naming("setup.py") is False
    assert has_invalid_python_naming("conftest.py") is False


def test_ignores_non_python_files() -> None:
    """Test that non-.py files are not validated."""
    assert has_invalid_python_naming("user-handler.js") is False
    assert has_invalid_python_naming("api-client.ts") is False


# ==================== Bash Command Parsing Tests ====================


def test_extracts_redirect_output() -> None:
    """Test extraction of file paths from redirects."""
    paths = extract_file_paths_from_bash('echo "data" > output.txt')
    assert "output.txt" in paths

    paths = extract_file_paths_from_bash("cat input.txt >> log.txt")
    assert "log.txt" in paths


def test_extracts_touch_command() -> None:
    """Test extraction of file paths from touch command."""
    paths = extract_file_paths_from_bash("touch file.txt")
    assert "file.txt" in paths

    paths = extract_file_paths_from_bash("touch file1.txt file2.txt")
    assert "file1.txt" in paths
    assert "file2.txt" in paths


def test_extracts_cp_destination() -> None:
    """Test extraction of destination from cp command."""
    paths = extract_file_paths_from_bash("cp main.py main_v2.py")
    assert "main_v2.py" in paths


def test_extracts_mv_destination() -> None:
    """Test extraction of destination from mv command."""
    paths = extract_file_paths_from_bash("mv old.py new_v2.py")
    assert "new_v2.py" in paths


def test_strips_quotes() -> None:
    """Test that quotes are stripped from extracted paths."""
    paths = extract_file_paths_from_bash('touch "file.txt"')
    assert "file.txt" in paths

    paths = extract_file_paths_from_bash("touch 'output.log'")
    assert "output.log" in paths


# ==================== Validate File Path Tests ====================


def test_validate_allows_good_names() -> None:
    """Test that valid file names are allowed."""
    assert validate_file_path("script.py") is None
    assert validate_file_path("utils.js") is None
    assert validate_file_path("user_handler.py") is None


def test_validate_blocks_backup_files() -> None:
    """Test that backup files are blocked."""
    error = validate_file_path("script.py.backup")
    assert error is not None
    assert "Backup file extension detected" in error


def test_validate_blocks_version_files() -> None:
    """Test that version suffixed files are blocked."""
    error = validate_file_path("api_v2.py")
    assert error is not None
    assert "Version suffix detected" in error


def test_validate_blocks_iteration_files() -> None:
    """Test that iteration suffixed files are blocked."""
    error = validate_file_path("script_final.py")
    assert error is not None
    assert "Iteration suffix detected" in error


def test_validate_allows_allowlisted_files() -> None:
    """Test that allowlisted files bypass all checks."""
    # README.md would normally trigger nothing, but test it's explicitly allowed
    assert validate_file_path("README.md") is None
    assert validate_file_path("setup.py") is None


# ==================== Integration Tests ====================


def run_hook_with_input(hook_input: HookInput) -> HookOutput:
    """Helper to run hook with test input and return parsed output."""
    import file_naming_enforcer  # type: ignore

    # Capture stdin and stdout
    input_json = json.dumps(hook_input)

    with patch("sys.stdin", StringIO(input_json)):
        with patch("sys.stdout", StringIO()) as mock_stdout:
            with patch("sys.exit"):  # Prevent actual exit
                file_naming_enforcer.main()  # type: ignore

            output = mock_stdout.getvalue()
            if output:
                result: HookOutput = json.loads(output)  # type: ignore[assignment]
                return result

    return HookOutput(
        hookSpecificOutput=HookSpecificOutput(
            permissionDecision="allow",
            permissionDecisionReason="No output",
        ),
        suppressOutput=False,
    )


def test_integration_write_good_file() -> None:
    """Test Write tool with valid file name."""
    hook_input = create_write_input("user_handler.py")
    output = run_hook_with_input(hook_input)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert hook_output.get("permissionDecision") == "allow"


def test_integration_write_bad_file() -> None:
    """Test Write tool with invalid file name."""
    hook_input = create_write_input("script_v2.py")
    output = run_hook_with_input(hook_input)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert hook_output.get("permissionDecision") == "deny"
    reason = hook_output.get("permissionDecisionReason", "")
    assert "Version suffix detected" in str(reason)


def test_integration_bash_redirect_bad_file() -> None:
    """Test Bash tool with redirect to bad file name."""
    hook_input = create_bash_input('echo "data" > output_v2.txt')
    output = run_hook_with_input(hook_input)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert hook_output.get("permissionDecision") == "deny"


def test_integration_bash_touch_bad_file() -> None:
    """Test Bash tool with touch of bad file name."""
    hook_input = create_bash_input("touch script_final.py")
    output = run_hook_with_input(hook_input)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert hook_output.get("permissionDecision") == "deny"


def test_integration_allowlisted_file() -> None:
    """Test that allowlisted files are always allowed."""
    hook_input = create_write_input("README.md")
    output = run_hook_with_input(hook_input)

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert hook_output.get("permissionDecision") == "allow"


# ==================== Error Handling Tests ====================


def test_handles_empty_file_path() -> None:
    """Test that empty file path is handled gracefully."""
    assert validate_file_path("") is None


def test_handles_malformed_input() -> None:
    """Test that malformed input doesn't crash the hook."""
    malformed_input = HookInput(
        session_id="test123",
        transcript_path="/path/to/transcript.jsonl",
        cwd="/project",
        hook_event_name="PreToolUse",
        tool_name="Write",
        tool_input=ToolInput(),  # Missing file_path
    )

    # Should not raise exception
    output = run_hook_with_input(malformed_input)
    assert "hookSpecificOutput" in output


# ==================== Edge Cases ====================


def test_v2ray_allowed() -> None:
    """Test that v2ray (semantic name) is allowed."""
    assert has_version_suffix("v2ray.py") is False
    assert validate_file_path("v2ray.py") is None


def test_python3_utils_allowed() -> None:
    """Test that python3_utils (semantic) is allowed."""
    assert has_number_suffix("python3_utils.py") is False
    assert validate_file_path("python3_utils.py") is None


def test_case_insensitive_iteration() -> None:
    """Test that iteration suffixes are case-insensitive."""
    assert has_iteration_suffix("script_FINAL.py") is True
    assert has_iteration_suffix("code_Fixed.js") is True


def test_case_insensitive_version() -> None:
    """Test that version suffixes are case-insensitive."""
    assert has_version_suffix("api_V2.py") is True
    assert has_version_suffix("parser_VERSION3.js") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
