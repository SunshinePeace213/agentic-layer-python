#!/usr/bin/env python3
"""
Test Suite for PEP 8 Naming Enforcer Hook
==========================================

Comprehensive tests for the pep8_naming_enforcer.py hook implementation.

Test Coverage:
    - Class name validation
    - Function name validation
    - Variable name validation
    - Constant name validation
    - Edge cases (magic methods, private names, etc.)
    - Tool integration (Write, Edit)
    - Error handling
    - Performance

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

import pytest


# Type definitions for hook output
class HookSpecificOutput(TypedDict):
    """Hook-specific output from pep8_naming_enforcer."""
    hookEventName: str
    permissionDecision: str
    permissionDecisionReason: str


class HookOutput(TypedDict):
    """Complete hook output structure."""
    hookSpecificOutput: HookSpecificOutput


# Path to hook script
HOOK_SCRIPT = (
    Path(__file__).parent.parent.parent.parent
    / ".claude"
    / "hooks"
    / "pre_tools"
    / "pep8_naming_enforcer.py"
)


def run_hook(tool_name: str, tool_input: Mapping[str, object]) -> tuple[int, str, str]:
    """
    Run the hook script with provided input.

    Args:
        tool_name: Name of the tool (Write or Edit)
        tool_input: Tool input parameters

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    hook_input = {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/test/project",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }

    input_json = json.dumps(hook_input)

    result = subprocess.run(
        ["uv", "run", str(HOOK_SCRIPT)],
        input=input_json,
        capture_output=True,
        text=True,
    )

    return result.returncode, result.stdout, result.stderr


def parse_hook_output(stdout: str) -> HookOutput:
    """Parse JSON output from hook."""
    return cast(HookOutput, json.loads(stdout))


# ==================== Class Name Tests ====================


def test_valid_class_names():
    """Test that valid class names are allowed."""
    valid_classes = [
        "class MyClass:\n    pass",
        "class HTTPServer:\n    pass",
        "class UserProfile:\n    pass",
        "class DatabaseConnection:\n    pass",
    ]

    for code in valid_classes:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0, f"Should allow valid class: {code}"
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_invalid_class_names():
    """Test that invalid class names are blocked."""
    invalid_cases = [
        ("class myClass:\n    pass", "myClass", "MyClass"),
        ("class my_class:\n    pass", "my_class", "MyClass"),
        ("class MYCLASS:\n    pass", "MYCLASS", "Myclass"),
        ("class My_Class:\n    pass", "My_Class", "MyClass"),
    ]

    for code, invalid_name, _ in invalid_cases:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0, "Hook should exit successfully"
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert invalid_name in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_private_class_names():
    """Test that private class names are allowed."""
    private_classes = [
        "class _PrivateClass:\n    pass",
        "class _InternalHelper:\n    pass",
        "class __PrivateClass:\n    pass",
    ]

    for code in private_classes:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Function Name Tests ====================


def test_valid_function_names():
    """Test that valid function names are allowed."""
    valid_functions = [
        "def get_user_data():\n    pass",
        "def calculate_total():\n    pass",
        "def send_email():\n    pass",
        "def _private_function():\n    pass",
    ]

    for code in valid_functions:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_invalid_function_names():
    """Test that invalid function names are blocked."""
    invalid_cases = [
        ("def GetUserData():\n    pass", "GetUserData", "get_user_data"),
        ("def getUserData():\n    pass", "getUserData", "get_user_data"),
        ("def GET_USER_DATA():\n    pass", "GET_USER_DATA", "get_user_data"),
    ]

    for code, invalid_name, _ in invalid_cases:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert invalid_name in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_magic_methods():
    """Test that magic methods are allowed."""
    magic_methods = [
        "class MyClass:\n    def __init__(self):\n        pass",
        "class MyClass:\n    def __str__(self):\n        pass",
        "class MyClass:\n    def __repr__(self):\n        pass",
        "class MyClass:\n    def __add__(self, other):\n        pass",
    ]

    for code in magic_methods:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Variable Name Tests ====================


def test_valid_variable_names():
    """Test that valid variable names are allowed."""
    valid_variables = [
        "user_count = 10",
        "total_price = 99.99",
        "is_valid = True",
        "_private_var = 42",
    ]

    for code in valid_variables:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_invalid_variable_names():
    """Test that invalid variable names are blocked."""
    invalid_cases = [
        ("userName = 'test'", "userName", "user_name"),
        ("UserName = 'test'", "UserName", "user_name"),
        ("userCount = 10", "userCount", "user_count"),
    ]

    for code, invalid_name, _ in invalid_cases:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert invalid_name in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_single_character_variables():
    """Test that common single-char variables are allowed."""
    allowed_single_chars = ["i = 0", "j = 1", "k = 2", "x = 10", "y = 20", "n = 100"]

    for code in allowed_single_chars:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_reserved_names():
    """Test that reserved names (l, O, I) are blocked."""
    reserved_names = ["l = []", "O = object()", "I = 1"]

    for code in reserved_names:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_trailing_underscore():
    """Test that trailing underscores (keyword conflicts) are allowed."""
    trailing_underscore = ["class_ = MyClass", "type_ = str", "id_ = 123"]

    for code in trailing_underscore:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Constant Name Tests ====================


def test_valid_constants():
    """Test that valid constants are allowed."""
    valid_constants = [
        "MAX_SIZE = 100",
        "API_KEY = 'secret'",
        "DEFAULT_TIMEOUT = 30",
        "HTTP_STATUS_OK = 200",
    ]

    for code in valid_constants:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_invalid_constants():
    """Test that invalid constant names are blocked."""
    # Module-level all-caps should be treated as constants
    invalid_constants = [
        "maxSize = 100",  # Should be MAX_SIZE if constant
        "Max_Size = 100",  # Mixed case
    ]

    for code in invalid_constants:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


# ==================== Argument Name Tests ====================


def test_valid_argument_names():
    """Test that valid argument names are allowed."""
    valid_args = [
        "def func(user_id):\n    pass",
        "def func(first_name, last_name):\n    pass",
        "def method(self, value):\n    pass",
        "def classmethod(cls, value):\n    pass",
    ]

    for code in valid_args:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_invalid_argument_names():
    """Test that invalid argument names are blocked."""
    invalid_args = [
        ("def func(userId):\n    pass", "userId"),
        ("def func(UserID):\n    pass", "UserID"),
    ]

    for code, invalid_name in invalid_args:
        exit_code, stdout, _ = run_hook(
            "Write", {"file_path": "test.py", "content": code}
        )
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert invalid_name in output["hookSpecificOutput"]["permissionDecisionReason"]


# ==================== Tool Integration Tests ====================


def test_write_tool_with_valid_python():
    """Test Write tool with valid Python code."""
    code = """
class UserProfile:
    def __init__(self):
        self.user_name = ""

    def get_user_name(self):
        return self.user_name
"""
    exit_code, stdout, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_write_tool_with_invalid_python():
    """Test Write tool with invalid Python naming."""
    code = """
class userProfile:
    def GetUserName(self):
        userName = "test"
        return userName
"""
    exit_code, stdout, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    # Should mention all 3 violations
    hook_specific = output["hookSpecificOutput"]
    assert isinstance(hook_specific, dict)
    reason = str(hook_specific["permissionDecisionReason"])
    assert "userProfile" in reason
    assert "GetUserName" in reason
    assert "userName" in reason


def test_non_python_files():
    """Test that non-Python files are skipped."""
    non_python = [
        {"file_path": "config.json", "content": '{"key": "value"}'},
        {"file_path": "README.md", "content": "# README"},
        {"file_path": "script.sh", "content": "#!/bin/bash\necho hello"},
    ]

    for tool_input in non_python:
        exit_code, stdout, _ = run_hook("Write", tool_input)
        assert exit_code == 0
        output = parse_hook_output(stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_empty_python_file():
    """Test that empty Python files are allowed."""
    exit_code, stdout, _ = run_hook("Write", {"file_path": "test.py", "content": ""})
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_python_syntax_error():
    """Test that syntax errors result in allow (fail-safe)."""
    invalid_syntax = "def func(\n    pass"  # Missing closing paren
    exit_code, stdout, _ = run_hook(
        "Write", {"file_path": "test.py", "content": invalid_syntax}
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Edit Tool Tests ====================


def test_edit_tool_creates_valid_file(tmp_path: Path) -> None:
    """Test Edit tool with changes that result in valid Python."""
    # Create a temporary file
    test_file = tmp_path / "test.py"
    test_file.write_text("class MyClass:\n    pass")

    # Edit to add a valid method
    exit_code, stdout, _ = run_hook(
        "Edit",
        {
            "file_path": str(test_file),
            "old_string": "class MyClass:\n    pass",
            "new_string": "class MyClass:\n    def get_value(self):\n        return 42",
            "replace_all": False,
        },
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_edit_tool_creates_invalid_file(tmp_path: Path) -> None:
    """Test Edit tool with changes that result in invalid naming."""
    # Create a temporary file
    test_file = tmp_path / "test.py"
    test_file.write_text("class MyClass:\n    pass")

    # Edit to add an invalid method name
    exit_code, stdout, _ = run_hook(
        "Edit",
        {
            "file_path": str(test_file),
            "old_string": "class MyClass:\n    pass",
            "new_string": "class MyClass:\n    def GetValue(self):\n        return 42",
            "replace_all": False,
        },
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "GetValue" in output["hookSpecificOutput"]["permissionDecisionReason"]


# ==================== Complex Real-World Tests ====================


def test_complex_valid_module():
    """Test a complete, valid Python module."""
    code = '''
"""Module docstring."""

import os
from typing import Optional

MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30


class UserService:
    """User service class."""

    def __init__(self):
        self._users = {}

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user by ID."""
        return self._users.get(user_id)

    def create_user(self, username: str, email: str) -> dict:
        """Create a new user."""
        user_id = len(self._users) + 1
        new_user = {
            "id": user_id,
            "username": username,
            "email": email,
        }
        self._users[user_id] = new_user
        return new_user

    def _validate_email(self, email: str) -> bool:
        """Internal email validation."""
        return "@" in email


def main():
    """Main entry point."""
    service = UserService()
    user = service.create_user("john_doe", "john@example.com")
    print(user)


if __name__ == "__main__":
    main()
'''
    exit_code, stdout, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_complex_invalid_module():
    """Test a module with multiple naming violations."""
    code = '''
"""Module with naming violations."""

maxRetries = 3  # Should be MAX_RETRIES


class userService:  # Should be UserService
    """User service class."""

    def GetUser(self, userId):  # Should be get_user, user_id
        """Get user by ID."""
        userName = "test"  # Should be user_name
        return userName


def MainFunction():  # Should be main_function
    """Main function."""
    pass
'''
    exit_code, stdout, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    hook_specific = output["hookSpecificOutput"]
    assert isinstance(hook_specific, dict)
    reason = str(hook_specific["permissionDecisionReason"])
    # Check for all violations
    assert "maxRetries" in reason
    assert "userService" in reason
    assert "GetUser" in reason
    assert "userId" in reason
    assert "userName" in reason
    assert "MainFunction" in reason


# ==================== Error Handling Tests ====================


def test_invalid_json_input():
    """Test that invalid JSON results in fail-safe allow."""
    result = subprocess.run(
        ["uv", "run", str(HOOK_SCRIPT)],
        input="invalid json",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = parse_hook_output(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_missing_file_path():
    """Test that missing file_path results in allow (skip validation)."""
    exit_code, stdout, _ = run_hook("Write", {"content": "class MyClass:\n    pass"})
    assert exit_code == 0
    output = parse_hook_output(stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# ==================== Performance Tests ====================


def test_performance_small_file():
    """Test that validation completes quickly for small files."""
    import time

    code = """
class MyClass:
    def get_value(self):
        return 42
"""
    start_time = time.time()
    exit_code, _, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    elapsed = time.time() - start_time

    assert exit_code == 0
    assert elapsed < 2.0  # Should complete in under 2 seconds (including uv overhead)


def test_performance_medium_file():
    """Test that validation completes reasonably for medium files."""
    import time

    # Generate a medium-sized file with 50 classes
    classes = [f"class MyClass{i}:\n    def get_value_{i}(self):\n        return {i}\n" for i in range(50)]
    code = "\n".join(classes)

    start_time = time.time()
    exit_code, _, _ = run_hook(
        "Write", {"file_path": "test.py", "content": code}
    )
    elapsed = time.time() - start_time

    assert exit_code == 0
    assert elapsed < 3.0  # Should complete in under 3 seconds


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
