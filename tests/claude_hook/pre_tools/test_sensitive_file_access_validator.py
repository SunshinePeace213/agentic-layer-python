#!/usr/bin/env python3
"""
Tests for Sensitive File Access Validator Hook
================================================

Comprehensive test suite for the sensitive file access validator hook.
Tests cover all sensitive file categories, bash command parsing, path
normalization, and edge cases.

Test Categories:
    - Unit tests for sensitive file detection
    - Unit tests for path normalization
    - Integration tests for each tool (Read, Write, Edit, Bash)
    - Bash command parsing tests
    - Edge case tests
    - Performance tests

Usage:
    uv run pytest -n auto tests/claude-hook/pre_tools/test_sensitive_file_access_validator.py
"""

import json
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest


# ==================== Type Protocols ====================


class IsTemplateFileProtocol(Protocol):
    """Protocol for is_template_file function."""

    def __call__(self, file_path: str) -> bool: ...


class IsSensitiveFileProtocol(Protocol):
    """Protocol for is_sensitive_file function."""

    def __call__(self, file_path: str) -> tuple[str, str] | None: ...


class ParseBashCommandProtocol(Protocol):
    """Protocol for parse_bash_command function."""

    def __call__(self, command: str) -> list[tuple[str, str]]: ...


# Type for hook output JSON
class HookOutput(Protocol):
    """Protocol for hook output structure."""

    hookSpecificOutput: dict[str, object]
    suppressOutput: bool | None


# ==================== Test Fixtures ====================


@pytest.fixture
def hook_script() -> Path:
    """Get path to the hook script."""
    return Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "pre_tools" / "sensitive_file_access_validator.py"


@pytest.fixture
def temp_sensitive_files(tmp_path: Path) -> Path:
    """Create temporary sensitive files for testing."""
    # Create .env file
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=value")

    # Create .env.sample (should be allowed)
    env_sample = tmp_path / ".env.sample"
    env_sample.write_text("SECRET=your_secret_here")

    # Create SSH key
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    ssh_key = ssh_dir / "id_rsa"
    ssh_key.write_text("-----BEGIN PRIVATE KEY-----")

    return tmp_path


def run_hook(hook_script: Path, input_data: Mapping[str, object]) -> dict[str, object]:
    """
    Run hook with given input data.

    Args:
        hook_script: Path to hook script
        input_data: Input JSON data

    Returns:
        Parsed JSON output from hook
    """
    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode != 0:
        raise RuntimeError(f"Hook failed: {result.stderr}")

    output = cast(dict[str, object], json.loads(result.stdout))
    return output


def get_hook_output(result: dict[str, object]) -> dict[str, object]:
    """Extract and cast hookSpecificOutput from result."""
    return cast(dict[str, object], result["hookSpecificOutput"])


def get_permission_decision(result: dict[str, object]) -> str:
    """Extract permission decision from hook result."""
    hook_specific = get_hook_output(result)
    return cast(str, hook_specific["permissionDecision"])


def get_permission_reason(result: dict[str, object]) -> str:
    """Extract permission decision reason from hook result."""
    hook_specific = get_hook_output(result)
    return cast(str, hook_specific["permissionDecisionReason"])


# ==================== Unit Tests ====================


def test_is_template_file(hook_script: Path) -> None:
    """Test template file detection."""
    # Import the hook module dynamically
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("sensitive_file_access_validator", hook_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec from {hook_script}")

    validator_module = importlib.util.module_from_spec(spec)
    sys.modules["sensitive_file_access_validator"] = validator_module
    spec.loader.exec_module(validator_module)

    is_template_file = cast(IsTemplateFileProtocol, validator_module.is_template_file)

    # Test template files (should be allowed)
    assert is_template_file(".env.sample")
    assert is_template_file(".env.example")
    assert is_template_file("example.env")
    assert is_template_file("sample.config")
    assert is_template_file("config.template")

    # Test non-template files (should not be allowed)
    assert not is_template_file(".env")
    assert not is_template_file("credentials.json")
    assert not is_template_file("secrets.yaml")


def test_is_sensitive_file(hook_script: Path) -> None:
    """Test sensitive file detection."""
    # Import the hook module dynamically
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("sensitive_file_access_validator", hook_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec from {hook_script}")

    validator_module = importlib.util.module_from_spec(spec)
    sys.modules["sensitive_file_access_validator"] = validator_module
    spec.loader.exec_module(validator_module)

    is_sensitive_file = cast(IsSensitiveFileProtocol, validator_module.is_sensitive_file)

    # Test environment variables
    assert is_sensitive_file("/path/.env") is not None
    assert is_sensitive_file("/path/.env.production") is not None

    # Test SSH keys
    assert is_sensitive_file("/home/user/.ssh/id_rsa") is not None
    assert is_sensitive_file("/home/user/.ssh/id_ed25519") is not None

    # Test certificates
    assert is_sensitive_file("/path/cert.pem") is not None
    assert is_sensitive_file("/path/private.key") is not None

    # Test cloud credentials
    assert is_sensitive_file("/home/user/.aws/credentials") is not None
    assert is_sensitive_file("/home/user/.kube/config") is not None

    # Test generic credentials
    assert is_sensitive_file("/path/credentials.json") is not None
    assert is_sensitive_file("/path/secrets.yaml") is not None

    # Test template files (should be allowed)
    assert is_sensitive_file("/path/.env.sample") is None
    assert is_sensitive_file("/path/credentials.example") is None

    # Test normal files (should be allowed)
    assert is_sensitive_file("/path/data.json") is None
    assert is_sensitive_file("/path/config.py") is None


def test_parse_bash_command(hook_script: Path) -> None:
    """Test bash command parsing."""
    # Import the hook module dynamically
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("sensitive_file_access_validator", hook_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec from {hook_script}")

    validator_module = importlib.util.module_from_spec(spec)
    sys.modules["sensitive_file_access_validator"] = validator_module
    spec.loader.exec_module(validator_module)

    parse_bash_command = cast(ParseBashCommandProtocol, validator_module.parse_bash_command)

    # Test read operations
    ops = parse_bash_command("cat .env")
    assert any(op[0] == "read" and ".env" in op[1] for op in ops)

    ops = parse_bash_command("less ~/.ssh/id_rsa")
    assert any(op[0] == "read" for op in ops)

    # Test write operations (redirects)
    ops = parse_bash_command("echo SECRET > .env")
    assert any(op[0] == "write" and ".env" in op[1] for op in ops)

    ops = parse_bash_command("echo data >> credentials.json")
    assert any(op[0] == "write" and "credentials.json" in op[1] for op in ops)

    # Test copy operations
    ops = parse_bash_command("cp source.txt .env")
    assert any(op[0] == "write" for op in ops)

    # Test command chains
    ops = parse_bash_command("cd ~/.ssh && cat id_rsa")
    assert any(op[0] == "read" for op in ops)


# ==================== Integration Tests ====================


def test_read_env_file_blocked(hook_script: Path) -> None:
    """Test that reading .env file is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": ".env"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    assert ".env" in get_permission_reason(result)
    assert cast(bool, result["suppressOutput"]) is True


def test_read_env_sample_allowed(hook_script: Path) -> None:
    """Test that reading .env.sample is allowed."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": ".env.sample"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "allow"


def test_write_ssh_key_blocked(hook_script: Path) -> None:
    """Test that writing SSH key is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "~/.ssh/id_rsa",
            "content": "-----BEGIN PRIVATE KEY-----"
        }
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    assert "SSH" in get_permission_reason(result)


def test_edit_credentials_blocked(hook_script: Path) -> None:
    """Test that editing credentials file is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "credentials.json",
            "old_string": "old",
            "new_string": "new"
        }
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    hook_specific = cast(dict[str, object], result["hookSpecificOutput"])
    reason = cast(str, hook_specific["permissionDecisionReason"])
    assert "credentials" in reason.lower()


def test_write_normal_file_allowed(hook_script: Path) -> None:
    """Test that writing normal files is allowed."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "data.json",
            "content": '{"key": "value"}'
        }
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "allow"


# ==================== Bash Command Tests ====================


def test_bash_cat_env_blocked(hook_script: Path) -> None:
    """Test that 'cat .env' is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "cat .env"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    assert ".env" in get_permission_reason(result)


def test_bash_redirect_env_blocked(hook_script: Path) -> None:
    """Test that redirecting to .env is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo SECRET=value > .env"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    assert ".env" in get_permission_reason(result)


def test_bash_cp_credentials_blocked(hook_script: Path) -> None:
    """Test that copying to credentials file is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "cp source.txt credentials.json"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


def test_bash_safe_command_allowed(hook_script: Path) -> None:
    """Test that safe bash commands are allowed."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "allow"


def test_bash_env_exists_check_allowed(hook_script: Path) -> None:
    """Test that checking .env existence is allowed."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "test -f .env && echo exists"}
    }

    result = run_hook(hook_script, input_data)

    # This should be allowed as 'test' is not a read command we detect
    assert get_permission_decision(result) == "allow"


# ==================== Cloud Credentials Tests ====================


def test_read_aws_credentials_blocked(hook_script: Path) -> None:
    """Test that reading AWS credentials is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "~/.aws/credentials"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    assert "AWS" in get_permission_reason(result)


def test_read_kube_config_blocked(hook_script: Path) -> None:
    """Test that reading Kubernetes config is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "~/.kube/config"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


# ==================== System Directory Tests ====================


def test_write_to_etc_blocked(hook_script: Path) -> None:
    """Test that writing to /etc is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/etc/hosts",
            "content": "127.0.0.1 localhost"
        }
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
    hook_specific = cast(dict[str, object], result["hookSpecificOutput"])
    reason = cast(str, hook_specific["permissionDecisionReason"])
    assert "system" in reason.lower()


def test_write_to_ssh_dir_blocked(hook_script: Path) -> None:
    """Test that writing to .ssh directory is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "~/.ssh/authorized_keys",
            "content": "ssh-rsa ..."
        }
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


# ==================== Edge Case Tests ====================


def test_empty_file_path(hook_script: Path) -> None:
    """Test handling of empty file path."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": ""}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "allow"


def test_malformed_json(hook_script: Path) -> None:
    """Test handling of malformed JSON input."""
    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input="{invalid json",
        capture_output=True,
        text=True,
        timeout=5
    )

    # Should not crash, should output valid JSON with allow decision
    assert result.returncode == 0
    output = cast(dict[str, object], json.loads(result.stdout))
    hook_specific = cast(dict[str, object], output["hookSpecificOutput"])
    assert hook_specific["permissionDecision"] == "allow"


def test_non_file_tool(hook_script: Path) -> None:
    """Test that non-file tools are allowed."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Glob",
        "tool_input": {"pattern": "*.py"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "allow"


def test_case_insensitive_matching(hook_script: Path) -> None:
    """Test case-insensitive file matching."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": ".ENV"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


def test_path_traversal(hook_script: Path) -> None:
    """Test path traversal attack prevention."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "../../.env"}
    }

    result = run_hook(hook_script, input_data)

    # Should still detect .env regardless of path traversal
    assert get_permission_decision(result) == "deny"


# ==================== Performance Tests ====================


def test_hook_performance(hook_script: Path) -> None:
    """Test that hook executes quickly."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": ".env"}
    }

    start = time.time()
    result = run_hook(hook_script, input_data)
    duration = time.time() - start

    assert duration < 1.0  # Should complete in less than 1 second
    assert get_permission_decision(result) == "deny"


def test_bash_parsing_performance(hook_script: Path) -> None:
    """Test bash command parsing performance."""
    # Complex command with multiple operations
    complex_command = "cd /tmp && cat file1.txt && grep pattern file2.txt | awk '{print $1}' > output.txt"

    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": complex_command}
    }

    start = time.time()
    result = run_hook(hook_script, input_data)
    duration = time.time() - start

    assert duration < 1.0  # Should complete in less than 1 second
    assert get_permission_decision(result) == "allow"


# ==================== Certificate Tests ====================


def test_read_pem_file_blocked(hook_script: Path) -> None:
    """Test that reading .pem files is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "privkey.pem"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


def test_read_key_file_blocked(hook_script: Path) -> None:
    """Test that reading .key files is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "private.key"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


# ==================== Package Manager Credentials Tests ====================


def test_read_npmrc_blocked(hook_script: Path) -> None:
    """Test that reading .npmrc is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "~/.npmrc"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"


def test_read_pypirc_blocked(hook_script: Path) -> None:
    """Test that reading .pypirc is blocked."""
    input_data = {
        "session_id": "test",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/home/user",
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "~/.pypirc"}
    }

    result = run_hook(hook_script, input_data)

    assert get_permission_decision(result) == "deny"
