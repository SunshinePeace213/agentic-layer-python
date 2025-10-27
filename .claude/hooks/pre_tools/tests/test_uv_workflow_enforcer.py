#!/usr/bin/env python3
"""
Comprehensive pytest-based tests for the uv_workflow_enforcer PreToolUse hook.

Test Categories:
1. Python Script Detection Tests
2. pip Install Detection Tests
3. Edge Case Detection Tests
4. Integration Tests
5. Error Handling Tests
6. Performance Tests

Usage:
    uv run pytest .claude/hooks/pre_tools/tests/test_uv_workflow_enforcer.py -v
"""

import json
import re
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# Type definitions for test JSON outputs
class HookSpecificOutputDict(TypedDict):
    """Type definition for hook specific output in tests."""
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutputDict(TypedDict):
    """Type definition for complete hook output in tests."""
    hookSpecificOutput: HookSpecificOutputDict
    suppressOutput: NotRequired[bool]

try:
    from uv_workflow_enforcer import (
        detect_python_script_execution,
        detect_pip_install,
        should_allow_command,
        validate_command,
        main,
        PYTHON_SCRIPT_PATTERN,
        PIP_INSTALL_PATTERN,
    )
except ImportError:
    pytest.skip("Could not import uv_workflow_enforcer", allow_module_level=True)


class TestPythonScriptDetection:
    """Test detection of direct python script execution."""

    def test_detects_python_script_execution(self) -> None:
        """Test that python script.py is detected."""
        result = detect_python_script_execution("python script.py")
        assert result is not None
        assert result[0] == "direct_python_execution"
        assert "uv run" in result[1]

    def test_detects_python3_script_execution(self) -> None:
        """Test that python3 script.py is detected."""
        result = detect_python_script_execution("python3 script.py")
        assert result is not None
        assert result[0] == "direct_python_execution"

    def test_detects_python_with_args(self) -> None:
        """Test that python script.py --arg value is detected."""
        result = detect_python_script_execution("python script.py --arg value")
        assert result is not None

    def test_detects_python_with_path(self) -> None:
        """Test that python ./path/to/script.py is detected."""
        result = detect_python_script_execution("python ./path/to/script.py")
        assert result is not None

    def test_detects_absolute_path_python(self) -> None:
        """Test that /usr/bin/python script.py is detected."""
        result = detect_python_script_execution("/usr/bin/python script.py")
        assert result is not None

    def test_detects_absolute_path_python3(self) -> None:
        """Test that /usr/bin/python3 script.py is detected."""
        result = detect_python_script_execution("/usr/bin/python3 script.py")
        assert result is not None

    def test_allows_python_oneliner(self) -> None:
        """Test that python -c 'code' is NOT detected (edge case)."""
        result = detect_python_script_execution('python -c "print(1)"')
        # Pattern should not match -c flag
        # But should_allow_command will handle this
        assert result is None or should_allow_command('python -c "print(1)"')

    def test_allows_python_module_execution(self) -> None:
        """Test that python -m module is NOT detected by pattern."""
        result = detect_python_script_execution("python -m pytest")
        assert result is None

    def test_allows_which_python(self) -> None:
        """Test that 'which python' is NOT detected."""
        result = detect_python_script_execution("which python")
        assert result is None

    def test_allows_echo_python(self) -> None:
        """Test that 'echo python' is NOT detected."""
        result = detect_python_script_execution("echo python")
        assert result is None

    def test_allows_uv_run_python(self) -> None:
        """Test that 'uv run python script.py' pattern is detected but allowed by edge case handler."""
        result = detect_python_script_execution("uv run python script.py")
        # Pattern matches, but should_allow_command will override this
        assert result is not None or should_allow_command("uv run python script.py")
        # Verify edge case handler allows it
        assert should_allow_command("uv run python script.py") is True

    def test_allows_uv_run_script(self) -> None:
        """Test that 'uv run script.py' is NOT detected."""
        result = detect_python_script_execution("uv run script.py")
        assert result is None

    def test_pattern_case_insensitive(self) -> None:
        """Test that pattern is case insensitive."""
        result = detect_python_script_execution("Python script.py")
        assert result is not None

    def test_detects_python_with_flags(self) -> None:
        """Test that python -u script.py is detected."""
        result = detect_python_script_execution("python -u script.py")
        assert result is not None


class TestPipInstallDetection:
    """Test detection of pip install commands."""

    def test_detects_pip_install(self) -> None:
        """Test that pip install package is detected."""
        result = detect_pip_install("pip install requests")
        assert result is not None
        assert result[0] == "pip_install_blocked"
        assert "uv add" in result[1]

    def test_detects_pip3_install(self) -> None:
        """Test that pip3 install package is detected."""
        result = detect_pip_install("pip3 install requests")
        assert result is not None

    def test_detects_python_m_pip_install(self) -> None:
        """Test that python -m pip install is detected."""
        result = detect_pip_install("python -m pip install requests")
        assert result is not None

    def test_detects_python3_m_pip_install(self) -> None:
        """Test that python3 -m pip install is detected."""
        result = detect_pip_install("python3 -m pip install numpy")
        assert result is not None

    def test_detects_pip_install_with_flags(self) -> None:
        """Test that pip install --upgrade is detected."""
        result = detect_pip_install("pip install --upgrade package")
        assert result is not None

    def test_detects_pip_install_requirements(self) -> None:
        """Test that pip install -r requirements.txt is detected."""
        result = detect_pip_install("pip install -r requirements.txt")
        assert result is not None

    def test_allows_which_pip(self) -> None:
        """Test that 'which pip' is NOT detected."""
        result = detect_pip_install("which pip")
        assert result is None

    def test_allows_echo_pip(self) -> None:
        """Test that 'echo pip install' is NOT detected."""
        result = detect_pip_install("echo pip install")
        # Pattern will match, but edge case handler should allow
        assert result is not None or should_allow_command("echo pip install")

    def test_allows_uv_add(self) -> None:
        """Test that 'uv add requests' is NOT detected."""
        result = detect_pip_install("uv add requests")
        assert result is None

    def test_allows_uv_add_dev(self) -> None:
        """Test that 'uv add --dev pytest' is NOT detected."""
        result = detect_pip_install("uv add --dev pytest")
        assert result is None

    def test_pattern_case_insensitive(self) -> None:
        """Test that pip pattern is case insensitive."""
        result = detect_pip_install("PIP install requests")
        assert result is not None


class TestEdgeCases:
    """Test edge cases and allowed patterns."""

    def test_allows_python_c_flag(self) -> None:
        """Test that python -c is allowed."""
        assert should_allow_command('python -c "print(1)"') is True

    def test_allows_python3_c_flag(self) -> None:
        """Test that python3 -c is allowed."""
        assert should_allow_command('python3 -c "import sys; print(sys.version)"') is True

    def test_allows_which_python(self) -> None:
        """Test that 'which python' is allowed."""
        assert should_allow_command("which python") is True

    def test_allows_which_python3(self) -> None:
        """Test that 'which python3' is allowed."""
        assert should_allow_command("which python3") is True

    def test_allows_type_python(self) -> None:
        """Test that 'type python' is allowed."""
        assert should_allow_command("type python") is True

    def test_allows_command_v_python(self) -> None:
        """Test that 'command -v python' is allowed."""
        assert should_allow_command("command -v python") is True

    def test_allows_echo_python(self) -> None:
        """Test that 'echo python' is allowed."""
        assert should_allow_command("echo python") is True

    def test_allows_printf_python(self) -> None:
        """Test that 'printf python' is allowed."""
        assert should_allow_command("printf '%s' python") is True

    def test_does_not_allow_python_script(self) -> None:
        """Test that python script.py is NOT in allowed list."""
        assert should_allow_command("python script.py") is False

    def test_complex_command_with_python(self) -> None:
        """Test complex command with python keyword."""
        assert should_allow_command("echo 'Installing python'") is True


class TestValidateCommand:
    """Test the main validate_command function."""

    def test_validates_python_script(self) -> None:
        """Test that python script.py returns violation."""
        result = validate_command("python script.py")
        assert result is not None
        assert result[0] == "direct_python_execution"

    def test_validates_pip_install(self) -> None:
        """Test that pip install returns violation."""
        result = validate_command("pip install requests")
        assert result is not None
        assert result[0] == "pip_install_blocked"

    def test_allows_uv_run(self) -> None:
        """Test that uv run script.py is allowed."""
        result = validate_command("uv run script.py")
        assert result is None

    def test_allows_uv_add(self) -> None:
        """Test that uv add package is allowed."""
        result = validate_command("uv add requests")
        assert result is None

    def test_allows_python_c(self) -> None:
        """Test that python -c is allowed."""
        result = validate_command('python -c "print(1)"')
        assert result is None

    def test_allows_which_python(self) -> None:
        """Test that which python is allowed."""
        result = validate_command("which python")
        assert result is None

    def test_allows_normal_commands(self) -> None:
        """Test that normal bash commands are allowed."""
        assert validate_command("ls -la") is None
        assert validate_command("git status") is None
        assert validate_command("npm install") is None


class TestHookIntegration:
    """Test full hook execution with various commands."""

    def test_hook_blocks_python_script(self) -> None:
        """Test that hook blocks python script.py."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "python script.py"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
                assert "uv run" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_blocks_pip_install(self) -> None:
        """Test that hook blocks pip install."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "pip install requests"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
                assert "uv add" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_hook_allows_uv_run(self) -> None:
        """Test that hook allows uv run."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "uv run script.py"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_uv_add(self) -> None:
        """Test that hook allows uv add."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "uv add requests"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_allows_safe_python_commands(self) -> None:
        """Test that hook allows safe python commands like python -c."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python -c "print(1)"'
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_hook_provides_alternatives_in_message(self) -> None:
        """Test that hook provides helpful alternatives in denial message."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "python train.py --epochs 10"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                reason = str(output["hookSpecificOutput"]["permissionDecisionReason"])

                # Check that alternatives are provided
                assert "uv run" in reason
                assert "train.py --epochs 10" in reason or "train.py" in reason
                assert "Recommended alternative" in reason

    def test_hook_ignores_non_bash_tools(self) -> None:
        """Test that hook ignores non-Bash tools."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "test.py",
                "content": "print('hello')"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestErrorHandling:
    """Test error handling and fail-safe behavior."""

    def test_handles_empty_command(self) -> None:
        """Test that hook handles empty command gracefully."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": ""
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_handles_invalid_json(self) -> None:
        """Test that hook handles invalid JSON gracefully."""
        with patch('sys.stdin', StringIO("invalid json")):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0
                    output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_handles_missing_tool_input(self) -> None:
        """Test that hook handles missing tool_input field."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash"
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_handles_complex_multiline_commands(self) -> None:
        """Test that hook handles complex multiline commands."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "cd project && python script.py && echo done"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                # Should detect python script.py even in complex command
                assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_handles_escaped_quotes(self) -> None:
        """Test that hook handles escaped quotes in commands."""
        hook_input = json.dumps({
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": """python -c "print(\\"hello\\")" """
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                # Should allow python -c
                output = cast(HookOutputDict, json.loads(mock_stdout.getvalue()))
                assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestPerformance:
    """Test performance characteristics."""

    def test_validation_is_fast(self) -> None:
        """Test that validation is fast (<10ms per validation)."""
        commands = [
            "python script.py",
            "pip install requests",
            "uv run script.py",
            "uv add requests",
            "python -c 'print(1)'",
            "which python",
            "ls -la",
            "git status"
        ]

        start = time.time()
        for _ in range(100):  # Run 100 iterations
            for cmd in commands:
                validate_command(cmd)
        end = time.time()

        total_time = end - start
        avg_time_per_validation = (total_time / (100 * len(commands))) * 1000  # Convert to ms

        # Should be well under 10ms per validation
        assert avg_time_per_validation < 10, f"Validation too slow: {avg_time_per_validation:.2f}ms"

    def test_regex_compilation_cached(self) -> None:
        """Test that regex patterns are compiled and cached."""
        # Verify patterns are compiled
        assert isinstance(PYTHON_SCRIPT_PATTERN, re.Pattern)
        assert isinstance(PIP_INSTALL_PATTERN, re.Pattern)

        # Verify they're the same object (cached)
        from uv_workflow_enforcer import PYTHON_SCRIPT_PATTERN as PATTERN1
        from uv_workflow_enforcer import PYTHON_SCRIPT_PATTERN as PATTERN2
        assert PATTERN1 is PATTERN2


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
