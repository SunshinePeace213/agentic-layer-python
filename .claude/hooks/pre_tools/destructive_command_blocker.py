#!/usr/bin/env python3
"""
Unified Bash Validation - PreToolUse Hook
==========================================
Prevents execution of dangerous bash commands in Claude Code.

This hook validates bash commands before execution to prevent:
- Destructive rm operations (rm -rf /, etc.)
- Disk overwrite operations (dd)
- Fork bombs
- Dangerous permission changes
- System file overwrites
- Format operations
- Critical process termination

Usage:
    python unified_bash_validation.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import json
import re
import sys
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    command: str
    file_path: str
    path: str


class HookSpecificOutput(TypedDict):
    """Type definition for hook-specific output."""
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutput(TypedDict, total=False):
    """Type definition for complete hook output."""
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


def main() -> None:
    """
    Main entry point for the bash validation hook.
    
    Reads hook data from stdin and outputs JSON decision.
    """
    try:
        # Read input from stdin
        input_text = sys.stdin.read()
        
        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)
        
        # Parse JSON
        try:
            parsed_json = json.loads(input_text)  # type: ignore[reportAny]
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Validate input structure
        if not isinstance(parsed_json, dict):
            # Invalid format - non-blocking error
            print("Error: Input must be a JSON object", file=sys.stderr)
            sys.exit(1)
        
        # Extract fields with type checking
        tool_name_obj = parsed_json.get("tool_name", "")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        tool_input_obj = parsed_json.get("tool_input", {})  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        
        if not isinstance(tool_name_obj, str):
            # Missing tool_name - allow operation
            output_decision("allow", "Missing or invalid tool_name")
            return
        
        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - allow operation
            output_decision("allow", "Invalid tool_input format")
            return
        
        tool_name: str = tool_name_obj
        
        # Only validate bash/shell commands
        if tool_name not in {"Bash"}:
            # Not a bash command - allow
            output_decision("allow", "Not a bash/shell command tool")
            return
        
        # Extract command from tool_input
        command_val = tool_input_obj.get("command")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(command_val, str):
            # No command - allow
            output_decision("allow", "No command to validate")
            return
        
        command = command_val.strip()
        if not command:
            # Empty command - allow
            output_decision("allow", "Empty command")
            return
        
        # Validate the command
        violation = validate_bash_command(command)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Command is safe to execute")
            
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False
) -> None:
    """
    Output a properly formatted JSON decision.
    
    Args:
        decision: Permission decision
        reason: Reason for the decision
        suppress_output: Whether to suppress output in transcript mode
    """
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }
    
    # Only add suppressOutput if it's True
    if suppress_output:
        output["suppressOutput"] = True
    
    try:
        print(json.dumps(output))
        sys.exit(0)  # Success - JSON output controls permission
    except (TypeError, ValueError) as e:
        # Failed to serialize JSON - non-blocking error
        print(f"Error: Failed to serialize output JSON: {e}", file=sys.stderr)
        sys.exit(1)


def validate_bash_command(command: str) -> str | None:
    """
    Validate a bash command for dangerous patterns.
    
    Args:
        command: The bash command to validate
        
    Returns:
        Violation message if found, None otherwise
    """
    # Run all checkers
    checkers = [
        check_dangerous_rm,
        check_dangerous_dd,
        check_fork_bomb,
        check_dangerous_chmod,
        check_format_commands,
        check_dangerous_overwrite,
    ]
    
    for checker_func in checkers:
        violation = checker_func(command)
        if violation:
            return violation
    
    return None


def check_dangerous_rm(command: str) -> str | None:
    """
    Check for dangerous rm commands.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    # Normalize command
    normalized = ' '.join(command.lower().split())
    
    # Check for rm -rf patterns
    rf_patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',
        r'\brm\s+--force\s+--recursive',
    ]
    
    for pattern in rf_patterns:
        if re.search(pattern, normalized):
            # Check for dangerous paths - these are the targets after rm -rf
            # Extract the part after the flags
            parts = command.split()
            targets: list[str] = []
            skip_next = False
            
            for i, part in enumerate(parts):
                if skip_next:
                    skip_next = False
                    continue
                if part == 'rm':
                    continue
                if part.startswith('-'):
                    # Skip flags and their arguments
                    if part in ['-rf', '-fr', '-r', '-f', '--recursive', '--force']:
                        continue
                    skip_next = True
                else:
                    # This is a target path
                    targets.append(part)
            
            # Check each target for dangerous patterns
            dangerous_checks = [
                ('/', 'root directory /'),
                ('/*', 'root with wildcard /*'),
                ('~', 'home directory ~'),
                ('~/', 'home directory path'),
                ('$HOME', 'HOME environment variable'),
                ('..', 'parent directory ..'),
                ('.', 'current directory .'),
                ('*', 'wildcard *'),
            ]
            
            for target in targets:
                for dangerous_path, description in dangerous_checks:
                    # Exact match or path-based match
                    if target == dangerous_path or (dangerous_path != '*' and target.startswith(dangerous_path)):
                        # Truncate long commands
                        display_cmd = command if len(command) <= 60 else command[:57] + "..."
                        
                        return (
                            f"🔴 CRITICAL: Dangerous rm -rf targeting {description}. \n"
                            f"Command: {display_cmd}. \n"
                            f"This would recursively delete critical system files. \n"
                            f"Alternative: Use specific paths and avoid recursive deletion of system directories. \n"
                            f"Always double-check rm commands before execution. \n"
                        )
    
    # Check for rm with recursive flag on system paths
    if re.search(r'\brm\s+.*-[a-z]*r', normalized):
        system_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/sys', '/proc', '/boot', '/lib']
        for path in system_paths:
            if path in normalized:
                return (
                    f"⛔ Blocked recursive rm targeting system path {path}. \n"
                    f"Command: {command[:60]}... \n"
                    f"Recursive deletion in system directories can break your system. \n"
                    f"Alternative: Delete specific files or use non-recursive rm. \n"
                )
    
    return None


def check_dangerous_dd(command: str) -> str | None:
    """
    Check for dangerous dd commands that could overwrite disks.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    normalized = command.lower()
    
    if 'dd' not in normalized:
        return None
    
    # Check for dd writing to disk devices
    dangerous_targets = [
        r'of=/dev/[sh]d[a-z]',  # /dev/sda, /dev/hda, etc.
        r'of=/dev/nvme',         # NVMe devices
        r'of=/dev/disk',         # Disk devices
        r'of=/dev/loop',         # Loop devices (can be dangerous)
    ]
    
    for pattern in dangerous_targets:
        if re.search(pattern, normalized):
            return (
                f"🔴 CRITICAL: dd command targeting disk device detected. \n"
                f"Command: {command[:60]}... \n"
                f"This could destroy all data on the disk! "
                f"Alternative: Verify the target device carefully. \n"
                f"Use 'lsblk' to check disk layout before using dd. \n"
            )
    
    # Check for dd with no limit (could fill disk)
    if 'dd' in normalized and 'if=/dev/zero' in normalized and 'count=' not in normalized:
        return (
            f"⚠️ dd from /dev/zero without count limit detected. \n"
            f"Command: {command[:60]}... \n"
            f"This could fill the entire disk with zeros. \n"
            f"Alternative: Add 'count=' parameter to limit data written. \n"
            f"Example: dd if=/dev/zero of=file bs=1M count=100 \n"
        )
    
    return None


def check_fork_bomb(command: str) -> str | None:
    """
    Check for fork bomb patterns.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    # Remove spaces for pattern matching
    no_spaces = command.replace(' ', '')
    
    # Classic fork bomb patterns
    fork_patterns = [
        r':\(\)\{:\|:&\};:',  # Classic bash fork bomb
        r':\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:',  # With spaces
        r'\$0\s*&\s*\$0',  # Self-referencing fork
    ]
    
    for pattern in fork_patterns:
        if re.search(pattern, command) or re.search(pattern, no_spaces):
            return (
                f"💣 FORK BOMB DETECTED! "
                f"Command: {command[:40]}... \n"
                f"This creates infinite processes and will crash the system. \n"
                f"Fork bombs consume all available resources. \n"
                f"There is no safe alternative - this pattern must never be executed. \n"
            )
    
    return None


def check_dangerous_chmod(command: str) -> str | None:
    """
    Check for dangerous chmod operations.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    normalized = command.lower()
    
    if 'chmod' not in normalized:
        return None
    
    # Check for chmod 777 on system directories
    if re.search(r'chmod\s+.*777', normalized):
        system_paths = ['/', '/etc', '/usr', '/bin', '/sbin', '/var', '/home']
        for path in system_paths:
            if path in normalized:
                return (
                    f"🔓 Security risk: chmod 777 on system directory {path}. \n"
                    f"Command: {command[:60]}... \n"
                    f"This gives everyone full access to critical files. \n"
                    f"Alternative: Use restrictive permissions like 755 or 644. \n"
                    f"Never use 777 on system directories. \n"
                )
    
    # Check for recursive chmod on root
    if re.search(r'chmod\s+.*-[rR]', normalized):
        if any(path in command for path in ['/', '/*', '$HOME', '~']):
            return (
                f"⛔ Blocked recursive chmod on critical directory. \n"
                f"Command: {command[:60]}... \n"
                f"Recursive permission changes could break the system. \n"
                f"Alternative: Change permissions on specific files only. \n"
                f"Avoid recursive operations on system directories. \n"
            )
    
    return None


def check_format_commands(command: str) -> str | None:
    """
    Check for disk format commands.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    normalized = command.lower()
    
    # Format command patterns
    format_commands = ['mkfs', 'mke2fs', 'mkswap', 'fdisk', 'parted']
    
    for fmt_cmd in format_commands:
        if fmt_cmd in normalized:
            # Check if targeting a device
            if re.search(r'/dev/[sh]d[a-z]', normalized) or '/dev/nvme' in normalized:
                return (
                    f"💾 DISK FORMAT COMMAND DETECTED! "
                    f"Command uses {fmt_cmd}: {command[:50]}... \n"
                    f"This will destroy ALL data on the disk! "
                    f"Alternative: Ensure you have complete backups. \n"
                    f"Double-check the device name with 'lsblk' before formatting. \n"
                )
    
    return None


def check_dangerous_overwrite(command: str) -> str | None:
    """
    Check for commands that overwrite critical files.
    
    Args:
        command: Command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    normalized = command.lower()
    
    # Critical files that shouldn't be overwritten
    critical_files = [
        ('/etc/passwd', 'user account file'),
        ('/etc/shadow', 'password file'),
        ('/etc/sudoers', 'sudo configuration'),
        ('/boot/grub', 'bootloader'),
        ('/etc/fstab', 'filesystem mounts'),
        ('/etc/hosts', 'hostname resolution'),
    ]
    
    # Check for redirect overwrites
    if '>' in command:  # Output redirect
        for critical_file, description in critical_files:
            if critical_file in normalized:
                return (
                    f"🚫 Command would overwrite critical {description}. \n"
                    f"Path: {critical_file}. \n"
                    f"Command: {command[:50]}... \n"
                    f"This could make the system unbootable or inaccessible. \n"
                    f"Alternative: Back up the file first, or append with '>>'. \n"
                )
    
    # Check for mv/cp to critical locations
    if re.search(r'\b(mv|cp)\b', normalized):
        for critical_file, description in critical_files:
            if critical_file in normalized:
                return (
                    f"⚠️ Command could overwrite critical {description}. \n"
                    f"Path: {critical_file}. \n"
                    f"Command: {command[:50]}... \n"
                    f"Alternative: Create a backup first with 'cp {critical_file} {critical_file}.bak'. \n"
                )
    
    return None


if __name__ == "__main__":
    main()
