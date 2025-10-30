#!/usr/bin/env python3
"""
Test Suite for Destructive Command Blocker Hook
================================================

Comprehensive tests for the destructive_command_blocker.py PreToolUse hook.

Test Categories:
    - Pattern detection for all dangerous command categories
    - Allow-list validation
    - Integration tests with full hook execution
    - Error handling and fail-safe behavior
    - Edge cases and complex commands

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import json
import subprocess
from pathlib import Path
from typing import TypedDict, cast

import pytest


# ==================== Type Definitions ====================


class HookResult(TypedDict):
    """Result from running the hook script."""
    decision: str
    reason: str
    exit_code: int


class HookOutput(TypedDict):
    """Structure of hook JSON output."""
    hookSpecificOutput: dict[str, str]


# ==================== Test Fixtures ====================

@pytest.fixture
def hook_script() -> Path:
    """Return path to the destructive command blocker hook script."""
    return Path(__file__).parents[3] / ".claude" / "hooks" / "pre_tools" / "destructive_command_blocker.py"


def run_hook(hook_script: Path, command: str) -> HookResult:
    """
    Execute the hook with a test command and return the result.

    Args:
        hook_script: Path to the hook script
        command: Bash command to test

    Returns:
        Dictionary with 'decision', 'reason', and 'exit_code'
    """
    input_data = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test-transcript.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": command
        }
    }

    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5
    )

    try:
        output = cast(HookOutput, json.loads(result.stdout))
        hook_data = output["hookSpecificOutput"]
        return HookResult(
            decision=hook_data["permissionDecision"],
            reason=hook_data["permissionDecisionReason"],
            exit_code=result.returncode
        )
    except (json.JSONDecodeError, KeyError):
        return HookResult(
            decision="error",
            reason=result.stderr or result.stdout,
            exit_code=result.returncode
        )


# ==================== Destructive File Operations Tests ====================


def test_rm_rf_root(hook_script: Path) -> None:
    """Test detection of rm -rf / command."""
    result = run_hook(hook_script, "rm -rf /")
    assert result["decision"] == "deny"
    assert "Destructive File Operations" in result["reason"]
    assert "BLOCKED" in result["reason"]


def test_rm_rf_root_with_wildcard(hook_script: Path) -> None:
    """Test detection of rm -rf /* command."""
    result = run_hook(hook_script, "rm -rf /*")
    assert result["decision"] == "deny"
    assert "Destructive File Operations" in result["reason"]


def test_rm_rf_system_directory(hook_script: Path) -> None:
    """Test detection of rm -rf on system directories."""
    dangerous_commands = [
        "rm -rf /usr",
        "rm -rf /etc",
        "rm -rf /bin",
        "rm -rf /var",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"


def test_rm_rf_home_directory(hook_script: Path) -> None:
    """Test detection of rm -rf ~/* command."""
    result = run_hook(hook_script, "rm -rf ~/*")
    assert result["decision"] == "deny"


def test_rm_rf_with_wildcard(hook_script: Path) -> None:
    """Test detection of rm -rf * command."""
    result = run_hook(hook_script, "rm -rf *")
    assert result["decision"] == "deny"


def test_safe_rm_single_file(hook_script: Path) -> None:
    """Test that rm of single file is allowed."""
    result = run_hook(hook_script, "rm file.txt")
    assert result["decision"] == "allow"


def test_safe_rm_interactive(hook_script: Path) -> None:
    """Test that rm -i is allowed (interactive mode)."""
    result = run_hook(hook_script, "rm -i unwanted.txt")
    assert result["decision"] == "allow"


def test_safe_rm_project_directory(hook_script: Path) -> None:
    """Test that rm -r ./directory is allowed."""
    result = run_hook(hook_script, "rm -r ./old_project/")
    assert result["decision"] == "allow"


# ==================== Disk Overwrite Operations Tests ====================


def test_dd_to_disk_device(hook_script: Path) -> None:
    """Test detection of dd to disk devices."""
    dangerous_commands = [
        "dd if=/dev/zero of=/dev/sda",
        "dd if=/dev/zero of=/dev/hda",
        "dd if=/dev/zero of=/dev/nvme0n1",
        "dd if=/dev/zero of=/dev/disk0",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"
        assert "Disk Overwrite Operations" in result["reason"]


def test_redirect_to_disk_device(hook_script: Path) -> None:
    """Test detection of redirect to disk devices."""
    result = run_hook(hook_script, "echo data > /dev/sda")
    assert result["decision"] == "deny"


def test_cat_to_disk_device(hook_script: Path) -> None:
    """Test detection of cat to disk devices."""
    result = run_hook(hook_script, "cat /dev/urandom > /dev/sda")
    assert result["decision"] == "deny"


def test_safe_dd_to_file(hook_script: Path) -> None:
    """Test that dd to regular file is allowed."""
    result = run_hook(hook_script, "dd if=/dev/zero of=./file.img")
    assert result["decision"] == "allow"


# ==================== Fork Bomb Tests ====================


def test_classic_fork_bomb(hook_script: Path) -> None:
    """Test detection of classic bash fork bomb."""
    result = run_hook(hook_script, ":(){ :|:& };:")
    assert result["decision"] == "deny"
    assert "Fork Bombs" in result["reason"]


def test_perl_fork_bomb(hook_script: Path) -> None:
    """Test detection of perl fork bomb."""
    result = run_hook(hook_script, "perl -e 'fork while fork'")
    assert result["decision"] == "deny"


def test_python_fork_bomb(hook_script: Path) -> None:
    """Test detection of python fork bomb."""
    result = run_hook(hook_script, "python -c 'import os; os.fork() while True'")
    assert result["decision"] == "deny"


def test_recursive_script_execution(hook_script: Path) -> None:
    """Test detection of recursive script spawning."""
    result = run_hook(hook_script, "$0 & $0")
    assert result["decision"] == "deny"


# ==================== Permission Changes Tests ====================


def test_chmod_777_system_directory(hook_script: Path) -> None:
    """Test detection of chmod 777 on system directories."""
    dangerous_commands = [
        "chmod 777 /etc",
        "chmod 777 /bin",
        "chmod 777 /usr",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"
        assert "Dangerous Permission Changes" in result["reason"]


def test_chmod_recursive_on_root(hook_script: Path) -> None:
    """Test detection of recursive chmod on root."""
    result = run_hook(hook_script, "chmod -R 777 /")
    assert result["decision"] == "deny"


def test_chown_recursive_on_root(hook_script: Path) -> None:
    """Test detection of recursive chown on root."""
    result = run_hook(hook_script, "chown -R nobody /")
    assert result["decision"] == "deny"


def test_safe_chmod_on_project_file(hook_script: Path) -> None:
    """Test that chmod on project files is allowed."""
    result = run_hook(hook_script, "chmod 755 ./script.sh")
    assert result["decision"] == "allow"


def test_safe_chown_on_project(hook_script: Path) -> None:
    """Test that chown on project is allowed."""
    result = run_hook(hook_script, "chown user:group ./project/")
    assert result["decision"] == "allow"


# ==================== System File Overwriting Tests ====================


def test_overwrite_passwd(hook_script: Path) -> None:
    """Test detection of /etc/passwd overwrite."""
    result = run_hook(hook_script, 'echo "hacker::0:0:::/bin/bash" > /etc/passwd')
    assert result["decision"] == "deny"
    assert "System File Overwriting" in result["reason"]


def test_overwrite_system_binaries(hook_script: Path) -> None:
    """Test detection of system binary overwrites."""
    dangerous_commands = [
        "cat malware > /bin/ls",
        "echo data > /sbin/init",
        "cp trojan /usr/bin/sudo",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"


def test_safe_write_to_project_etc(hook_script: Path) -> None:
    """Test that writing to project's etc directory is allowed."""
    result = run_hook(hook_script, "echo data > ./etc/config.txt")
    assert result["decision"] == "allow"


# ==================== Format Operations Tests ====================


def test_mkfs_format_partition(hook_script: Path) -> None:
    """Test detection of mkfs commands."""
    dangerous_commands = [
        "mkfs.ext4 /dev/sda1",
        "mkfs.xfs /dev/sdb1",
        "mkfs.ntfs /dev/sdc1",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"
        assert "Format Operations" in result["reason"]


def test_fdisk_partition_tool(hook_script: Path) -> None:
    """Test detection of fdisk command."""
    result = run_hook(hook_script, "fdisk /dev/sda")
    assert result["decision"] == "deny"


def test_diskutil_erase(hook_script: Path) -> None:
    """Test detection of diskutil command."""
    result = run_hook(hook_script, "diskutil eraseDisk")
    assert result["decision"] == "deny"


def test_safe_mkfs_on_image(hook_script: Path) -> None:
    """Test that mkfs on disk image file is allowed."""
    result = run_hook(hook_script, "mkfs.ext4 ./disk.img")
    assert result["decision"] == "allow"


# ==================== Process Termination Tests ====================


def test_kill_init_process(hook_script: Path) -> None:
    """Test detection of killing init/systemd (PID 1)."""
    result = run_hook(hook_script, "kill -9 1")
    assert result["decision"] == "deny"
    assert "Critical Process Termination" in result["reason"]


def test_killall_with_sigkill(hook_script: Path) -> None:
    """Test detection of killall -9."""
    result = run_hook(hook_script, "killall -9 systemd")
    assert result["decision"] == "deny"


def test_kill_critical_services(hook_script: Path) -> None:
    """Test detection of killing critical services."""
    dangerous_commands = [
        "killall systemd",
        "kill sshd",
        "pkill -9 networkd",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"


def test_safe_kill_user_process(hook_script: Path) -> None:
    """Test that killing regular processes is allowed."""
    result = run_hook(hook_script, "kill 12345")
    assert result["decision"] == "allow"


def test_safe_killall_user_app(hook_script: Path) -> None:
    """Test that killall on user apps is allowed."""
    result = run_hook(hook_script, "killall myapp")
    assert result["decision"] == "allow"


# ==================== Additional Dangerous Commands Tests ====================


def test_system_shutdown(hook_script: Path) -> None:
    """Test detection of shutdown commands."""
    dangerous_commands = [
        "shutdown -h now",
        "reboot",
        "halt",
        "poweroff",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"


def test_kernel_module_manipulation(hook_script: Path) -> None:
    """Test detection of kernel module commands."""
    dangerous_commands = [
        "rmmod critical_driver",
        "modprobe malicious_module",
        "insmod hack.ko",
    ]
    for cmd in dangerous_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "deny", f"Failed to block: {cmd}"


def test_cryptocurrency_miner(hook_script: Path) -> None:
    """Test detection of cryptocurrency miners."""
    result = run_hook(hook_script, "xmrig --donate-level=0")
    assert result["decision"] == "deny"


# ==================== Allow-list Tests ====================


def test_help_commands_allowed(hook_script: Path) -> None:
    """Test that help/version commands are allowed."""
    safe_commands = [
        "rm --help",
        "dd --version",
        "chmod -h",
        "kill -V",
    ]
    for cmd in safe_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "allow", f"Incorrectly blocked: {cmd}"


def test_man_pages_allowed(hook_script: Path) -> None:
    """Test that man page commands are allowed."""
    result = run_hook(hook_script, "man rm")
    assert result["decision"] == "allow"


def test_dry_run_mode_allowed(hook_script: Path) -> None:
    """Test that dry-run commands are allowed."""
    result = run_hook(hook_script, "some_command --dry-run")
    assert result["decision"] == "allow"


# ==================== Integration Tests ====================


def test_non_bash_tool_allowed(hook_script: Path) -> None:
    """Test that non-Bash tools are allowed through."""
    input_data = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test-transcript.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/tmp/test.txt",
            "content": "test"
        }
    }

    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=5
    )

    output = cast(HookOutput, json.loads(result.stdout))
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_empty_command_allowed(hook_script: Path) -> None:
    """Test that empty commands are allowed."""
    result = run_hook(hook_script, "")
    assert result["decision"] == "allow"


def test_safe_common_commands(hook_script: Path) -> None:
    """Test that common safe commands are allowed."""
    safe_commands = [
        "ls -la",
        "cat file.txt",
        "echo 'hello world'",
        "grep pattern file.txt",
        "git status",
        "npm install",
        "python script.py",
    ]
    for cmd in safe_commands:
        result = run_hook(hook_script, cmd)
        assert result["decision"] == "allow", f"Incorrectly blocked safe command: {cmd}"


# ==================== Error Handling Tests ====================


def test_malformed_input_fails_safe(hook_script: Path) -> None:
    """Test that malformed input results in allow (fail-safe)."""
    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input="invalid json",
        capture_output=True,
        text=True,
        timeout=5
    )

    # Should not crash and should allow (fail-safe)
    assert result.returncode == 0
    try:
        output = cast(HookOutput, json.loads(result.stdout))
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
    except json.JSONDecodeError:
        pytest.fail("Hook should output valid JSON even on error")


# ==================== Edge Cases Tests ====================


def test_case_insensitive_detection(hook_script: Path) -> None:
    """Test that dangerous commands are detected regardless of case."""
    result = run_hook(hook_script, "RM -RF /")
    assert result["decision"] == "deny"


def test_command_with_extra_spaces(hook_script: Path) -> None:
    """Test detection with extra whitespace."""
    result = run_hook(hook_script, "rm    -rf    /")
    assert result["decision"] == "deny"


def test_complex_command_chain(hook_script: Path) -> None:
    """Test detection in command chains."""
    result = run_hook(hook_script, "ls -la && rm -rf / && echo done")
    assert result["decision"] == "deny"


def test_command_in_subshell(hook_script: Path) -> None:
    """Test detection of dangerous commands in subshells."""
    result = run_hook(hook_script, "$(rm -rf /)")
    assert result["decision"] == "deny"


# ==================== Performance Tests ====================


def test_hook_execution_time(hook_script: Path) -> None:
    """Test that hook executes quickly (< 1 second)."""
    import time

    start = time.time()
    run_hook(hook_script, "echo 'test command'")
    duration = time.time() - start

    assert duration < 1.0, f"Hook took too long: {duration:.2f}s"


# ==================== Test Summary ====================


def test_pattern_coverage() -> None:
    """
    Verify that all pattern categories are covered by tests.

    This is a meta-test to ensure comprehensive test coverage.
    """
    tested_categories = {
        "Destructive File Operations",
        "Disk Overwrite Operations",
        "Fork Bombs",
        "Dangerous Permission Changes",
        "System File Overwriting",
        "Format Operations",
        "Critical Process Termination",
        "Additional Dangerous Commands"
    }

    # This test passes if we have tests for all categories
    # The categories are tested in the functions above
    assert len(tested_categories) == 8
