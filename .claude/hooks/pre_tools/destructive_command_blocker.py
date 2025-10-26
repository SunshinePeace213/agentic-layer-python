#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Destructive Command Blocker - PreToolUse Hook
==============================================
Prevents execution of dangerous bash commands to protect against data loss.

This hook validates bash commands before execution to block potentially
destructive operations that could cause system damage, data loss, or
security vulnerabilities.

Categories of Blocked Commands:
1. Destructive file operations (rm -rf /, etc.)
2. Disk overwrite operations (dd to block devices)
3. Fork bombs
4. Dangerous permission changes (chmod 777 on system files)
5. System file overwrites (redirects to /etc/, etc.)
6. Format operations (mkfs, fdisk, etc.)
7. Critical process termination (kill -9 systemd)
8. Remote code execution (curl | bash)

Usage:
    This hook is automatically invoked by Claude Code before Bash tool execution.
    It receives JSON input via stdin and outputs JSON permission decisions.

Dependencies:
    - Python >= 3.12
    - No external packages (standard library only)
    - Shared utilities from .claude/hooks/pre_tools/utils/

Exit Codes:
    0: Success (decision output via stdout)

Author: Claude Code Hook Expert
Version: 1.0.0
"""

import re
import sys
from typing import Optional, Pattern, Tuple

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Pattern Definitions ============

# Critical Paths (protected directories)
CRITICAL_PATHS: list[str] = [
    "/", "/*", "/bin", "/boot", "/etc", "/lib", "/lib64",
    "/proc", "/root", "/sbin", "/sys", "/usr", "~", "$HOME"
]

SYSTEM_DIRS_PATTERN: Pattern[str] = re.compile(
    r'/(bin|boot|dev|etc|lib|lib64|proc|root|sbin|sys|usr)(/|$)'
)

# Compiled regex patterns for performance
RM_DESTRUCTIVE: Pattern[str] = re.compile(
    r'\brm\s+.*?(-[rf]{1,2}|-[fr]{1,2}|--recursive|--force).*?\s+(~/?|/\*?(\s|$)|\$HOME/?|/bin\b|/boot\b|/etc\b|/usr\b|/sys\b|/sbin\b|/lib\b|/root\b|/proc\b)',
    re.IGNORECASE
)

DD_DISK_WRITE: Pattern[str] = re.compile(
    r'\bdd\s+.*?of=/dev/(sd[a-z]|hd[a-z]|nvme\d+n\d+|disk\d+)',
    re.IGNORECASE
)

FORK_BOMB: Pattern[str] = re.compile(
    r':\(\)\{:\|:&\};:|(\$0\s*&\s*){2,}'
)

CHMOD_DANGEROUS: Pattern[str] = re.compile(
    r'\bchmod\s+(-R\s+)?[67][67][67]\s+(/|/etc|/usr|/bin|/boot)',
    re.IGNORECASE
)

SYSTEM_FILE_REDIRECT: Pattern[str] = re.compile(
    r'>\s*/(etc|boot|sys|proc)/\S+',
    re.IGNORECASE
)

FORMAT_OPERATION: Pattern[str] = re.compile(
    r'\b(mkfs[\.\w]*|fdisk|parted|wipefs)\s+/dev/',
    re.IGNORECASE
)

KILL_CRITICAL: Pattern[str] = re.compile(
    r'\b(killall|pkill)\s+-9\s+\*|kill\s+-9\s+1\b|\bkillall.*systemd|pkill.*systemd',
    re.IGNORECASE
)

PIPE_TO_SHELL: Pattern[str] = re.compile(
    r'(wget|curl)\s+.*\|\s*(sh|bash)',
    re.IGNORECASE
)


# ============ Detection Functions ============

def detect_destructive_rm(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect destructive rm operations.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if RM_DESTRUCTIVE.search(command):
        return (
            "destructive_file_deletion",
            """🚫 CRITICAL: Destructive file deletion blocked

This command would recursively delete critical files/directories.

Safer alternatives:
  - Delete specific files: rm specific-file.txt
  - Use trash/recycle: trash {path}
  - Create backup first: tar -czf backup.tar.gz {path}
  - Test with ls first: ls {path}

Always verify paths before deletion!"""
        )
    return None


def detect_dd_disk_write(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect dd operations writing to disk devices.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if DD_DISK_WRITE.search(command):
        return (
            "disk_overwrite",
            """🚫 CRITICAL: Disk overwrite operation blocked

This dd command would overwrite a disk device, causing data loss.

Why this is dangerous:
  - Overwrites entire disk/partition
  - Cannot be undone
  - Destroys all data on the device

Safe dd usage:
  - Write to regular files: dd if=source of=backup.img
  - Always verify 'of=' parameter
  - Use 'count=' and 'bs=' for safety"""
        )
    return None


def detect_fork_bomb(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect fork bomb patterns.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if FORK_BOMB.search(command):
        return (
            "fork_bomb",
            """🚫 CRITICAL: Fork bomb detected

This command creates infinite processes, freezing your system.

Impact:
  - Exhausts all process slots
  - Makes system unresponsive
  - Requires hard reboot

If you need parallel processing:
  - Use xargs: cat list.txt | xargs -P 4 -I {} command {}
  - Use GNU parallel: parallel command ::: arg1 arg2
  - Use proper job control"""
        )
    return None


def detect_dangerous_chmod(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect dangerous permission changes.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if CHMOD_DANGEROUS.search(command):
        return (
            "dangerous_permissions",
            """🚫 Dangerous permission change blocked

This command would change permissions on critical system files.

Why this is dangerous:
  - 777 makes files world-writable (security risk)
  - System files need specific permissions
  - Can break system functionality

Safe practices:
  - Use minimal permissions: chmod 644 file.txt
  - Only modify your own files
  - Avoid recursive changes on system paths"""
        )
    return None


def detect_system_file_overwrite(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect system file overwrites.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if SYSTEM_FILE_REDIRECT.search(command):
        return (
            "system_file_overwrite",
            """🚫 System file overwrite blocked

This command would overwrite critical system files.

Protected directories:
  - /etc/     (system configuration)
  - /boot/    (bootloader)
  - /sys/     (kernel interface)
  - /proc/    (process information)

If you need to modify system files:
  - Create a backup first
  - Use proper editing tools (sudoedit)
  - Test in a container/VM"""
        )
    return None


def detect_format_operation(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect disk format operations.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if FORMAT_OPERATION.search(command):
        return (
            "format_operation",
            """🚫 CRITICAL: Disk format operation blocked

This command would format a disk, destroying all data.

Why this is blocked:
  - Formats entire disk/partition
  - Permanent data loss
  - Cannot be undone

For safe storage operations:
  - Work with disk images: mkfs.ext4 disk.img
  - Use containers/VMs for testing
  - Always verify device names"""
        )
    return None


def detect_critical_process_kill(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect critical process termination.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if KILL_CRITICAL.search(command):
        return (
            "critical_process_kill",
            """🚫 Critical process termination blocked

This would kill critical system processes.

Why this is dangerous:
  - May kill init/systemd (crash system)
  - May kill SSH/network (lose remote access)
  - SIGKILL (-9) prevents cleanup

Safe process management:
  - Use SIGTERM first: kill {pid}
  - Target specific processes by PID
  - Avoid wildcards with killall
  - Check processes first: ps aux | grep {name}"""
        )
    return None


def detect_pipe_to_shell(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect piping remote content to shell.

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    if PIPE_TO_SHELL.search(command):
        return (
            "remote_code_execution",
            """🚫 Remote code execution blocked

This command downloads and executes untrusted code.

Why this is dangerous:
  - Executes code without review
  - No security validation
  - Potential malware/backdoors

Safe alternatives:
  - Download first: wget URL -O script.sh
  - Review content: cat script.sh
  - Then execute: bash script.sh"""
        )
    return None


# ============ Main Validation ============

def validate_command(command: str) -> Optional[Tuple[str, str]]:
    """
    Validate command against all dangerous patterns.

    Checks command against all detection patterns in order of severity.
    Returns immediately upon finding first match (short-circuit evaluation).

    Args:
        command: The bash command to validate

    Returns:
        Tuple of (violation_type, message) if dangerous, None otherwise
    """
    # Check all patterns in order of severity
    checks = [
        detect_fork_bomb,              # Critical
        detect_dd_disk_write,          # Critical
        detect_format_operation,       # Critical
        detect_destructive_rm,         # Critical
        detect_system_file_overwrite,  # High
        detect_dangerous_chmod,        # High
        detect_critical_process_kill,  # Medium-High
        detect_pipe_to_shell,          # Medium-High
    ]

    for check in checks:
        result = check(command)
        if result:
            return result

    return None


def main() -> None:
    """
    Main entry point for destructive command blocker hook.

    Reads JSON input from stdin, validates bash commands, and outputs
    permission decisions. Implements fail-safe behavior on errors.

    Exit Codes:
        0: Always (decision output via stdout)
    """
    try:
        # Parse input using shared utility
        parsed = parse_hook_input()
        if not parsed:
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = parsed

        # Only validate Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Not a Bash command")
            return

        # Extract command
        command = tool_input.get("command", "")
        if not command:
            output_decision("allow", "No command to validate")
            return

        # Validate command
        violation = validate_command(command)

        if violation:
            _, message = violation
            full_message = f"{message}\n\nCommand: {command}"
            output_decision("deny", full_message, suppress_output=True)
        else:
            output_decision("allow", "Command is safe")

    except Exception as e:
        # Fail-safe: allow operation on error
        print(f"Destructive command blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
