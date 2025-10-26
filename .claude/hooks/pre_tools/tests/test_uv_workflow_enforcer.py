#!/usr/bin/env python3
"""
Tests for UV Workflow Enforcer Hook
=====================================

Test suite for the UV workflow enforcement PreToolUse hook.
Validates detection of python/pip commands and UV alternatives.
"""

import json
import subprocess
from pathlib import Path


# Get the hook script path
HOOK_SCRIPT = Path(__file__).parent.parent / "uv_workflow_enforcer.py"


def run_hook(tool_name: str, command: str) -> dict:
    """
    Run the hook with test input and return parsed output.

    Args:
        tool_name: Name of the tool being used (e.g., "Bash")
        command: The bash command to validate

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    result = subprocess.run(
        ["uv", "run", str(HOOK_SCRIPT)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)


def test_uv_run_command_is_allowed():
    """UV run commands should be allowed without warnings."""
    output = run_hook("Bash", "uv run script.py")
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "UV run command should be allowed"


def test_python_script_execution_is_blocked():
    """Python script execution should be blocked with UV suggestion."""
    output = run_hook("Bash", "python script.py")
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny", \
        "Python script execution should be denied"
    assert "uv run" in output["hookSpecificOutput"]["permissionDecisionReason"], \
        "Should suggest uv run"


def test_pip_install_is_blocked():
    """Pip install should be blocked with uv add suggestion."""
    output = run_hook("Bash", "pip install requests")
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny", \
        "Pip install should be denied"
    assert "uv add" in output["hookSpecificOutput"]["permissionDecisionReason"], \
        "Should suggest uv add"


def test_python_version_is_allowed():
    """Python --version should be allowed as system info command."""
    output = run_hook("Bash", "python --version")
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Python --version should be allowed"


if __name__ == "__main__":
    print("Running UV Workflow Enforcer tests...")

    tests = [
        test_uv_run_command_is_allowed,
        test_python_script_execution_is_blocked,
        test_pip_install_is_blocked,
        test_python_version_is_allowed,
    ]

    for test_func in tests:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
        except Exception as e:
            print(f"✗ {test_func.__name__}: ERROR - {e}")
