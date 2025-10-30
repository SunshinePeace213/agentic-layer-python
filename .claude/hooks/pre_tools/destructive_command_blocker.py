#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Destructive Command Blocker Hook
==================================

Prevents execution of dangerous bash commands in Claude Code during development
by validating bash commands before execution to protect against accidental system damage.

Purpose:
    Block potentially destructive bash commands that could cause:
    - Permanent data loss
    - System instability
    - Security compromises
    - Irreversible system damage

Hook Event: PreToolUse
Monitored Tool: Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with safe alternatives

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Dangerous Command Patterns ====================

# Category 1: Destructive File Operations
DESTRUCTIVE_FILE_PATTERNS = [
    # Recursive deletion of root or system directories
    (r'\brm\s+.*-[rf]+.*\s+/', "rm -rf with root path"),
    (r'\brm\s+-[rf]+\s+/', "rm -rf of root"),
    (r'\brm\s+.*-[rf]+.*\s+/\s*$', "rm -rf ending with root"),
    (r'\brm\s+.*-[rf]+.*\s+/\w+', "rm -rf of system directory"),

    # Deletion of home directory
    (r'\brm\s+.*-[rf]+.*\s+~/', "rm -rf of home directory"),

    # Deletion of all files
    (r'\brm\s+.*-[rf]+.*\s+\*', "rm -rf with wildcard"),
    (r'\brm\s+-[rf]+\s+\.\*', "rm -rf of dot files"),

    # Critical system directories
    (r'\brm\s+.*-[rf]+.*/(?:bin|boot|dev|etc|lib|proc|root|sbin|sys|usr|var)\b',
     "rm -rf of system directory"),
]

# Category 2: Disk Overwrite Operations
DISK_OVERWRITE_PATTERNS = [
    # Direct disk writes
    (r'>\s*/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+|disk\d+)', "write to disk device"),
    (r'\bdd\s+.*of=/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+|disk\d+)', "dd to disk device"),

    # Random data overwrites
    (r'/dev/(?:zero|random|urandom)\s*>\s*/dev/(?:sd|hd|nvme|disk)',
     "overwrite disk with random"),

    # Disk device manipulation
    (r'\b(?:cat|tee)\s+.*>\s*/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+)',
     "write to disk via cat/tee"),
]

# Category 3: Fork Bombs
FORK_BOMB_PATTERNS = [
    # Classic fork bombs
    (r':\(\)\{.*:\|:.*\}.*;:', "bash fork bomb"),
    (r'\(\)\s*\{\s*\(\)\s*\|\s*\(\)\s*&\s*\}', "function fork bomb"),

    # Perl/Python fork bombs
    (r'perl.*fork.*while', "perl fork bomb"),
    (r'python.*os\.fork.*while', "python fork bomb"),

    # Recursive process spawning
    (r'\$0\s*&\s*\$0', "recursive script execution"),
]

# Category 4: Dangerous Permission Changes
PERMISSION_PATTERNS = [
    # World-writable sensitive directories
    (r'\bchmod\s+.*777\s+/(?:etc|bin|sbin|boot|usr)', "chmod 777 on system directory"),

    # Recursive permission changes on root
    (r'\bchmod\s+.*-R.*\s+/', "recursive chmod on root"),
    (r'\bchown\s+.*-R.*\s+/', "recursive chown on root"),

    # SUID/SGID on dangerous locations
    (r'\bchmod\s+.*[24][0-9]{3}\s+/', "SUID/SGID on system files"),
]

# Category 5: System File Overwriting
SYSTEM_FILE_PATTERNS = [
    # Critical system files
    (r'>\s*/(?:etc/(?:passwd|shadow|group|sudoers|fstab|hosts))',
     "overwrite system config"),
    (r'>\s*/boot/', "overwrite boot files"),

    # System binaries (redirect)
    (r'>\s*/(?:bin|sbin|usr/bin|usr/sbin)/', "overwrite system binaries"),

    # System binaries (copy operations)
    (r'\b(?:cp|mv)\s+.*\s+/(?:bin|sbin|usr/bin|usr/sbin)/',
     "copy to system binaries"),

    # Kernel/system files
    (r'>\s*/proc/', "write to proc filesystem"),
    (r'>\s*/sys/', "write to sys filesystem"),
]

# Category 6: Format Operations
FORMAT_PATTERNS = [
    # Filesystem creation (formatting) - must be on device, not file
    (r'\bmkfs\.(?:ext[234]|xfs|btrfs|ntfs|fat32)\s+/dev/', "format filesystem"),
    (r'\bmke2fs\s+/dev/', "ext filesystem format"),

    # Partition manipulation
    (r'\b(?:fdisk|parted|gparted|diskutil)\b', "partition tool"),

    # Disk erasure
    (r'\bshred\s+.*--remove', "secure file deletion"),
    (r'\bwipe\s+', "secure wipe command"),
]

# Category 7: Critical Process Termination
PROCESS_KILL_PATTERNS = [
    # Kill all processes
    (r'\bkillall\s+-9', "killall with SIGKILL"),
    (r'\bkill\s+.*-9\s+1\b', "kill init/systemd"),

    # Kill critical services
    (r'\bkill(?:all)?\s+.*\b(?:systemd|init|launchd|sshd|networkd)\b',
     "kill critical service"),

    # pkill dangerous patterns
    (r'\bpkill\s+-9', "pkill with SIGKILL"),
]

# Category 8: Additional Dangerous Commands
ADDITIONAL_DANGEROUS_PATTERNS = [
    # Kernel module manipulation
    (r'\b(?:rmmod|modprobe|insmod)\b', "kernel module manipulation"),

    # System shutdown/reboot
    (r'\b(?:shutdown|reboot|halt|poweroff|init\s+[06])\b', "system shutdown"),

    # Memory/system information exposure
    (r'/dev/mem', "direct memory access"),
    (r'/dev/kmem', "kernel memory access"),

    # Cryptocurrency miners (CPU exhaustion)
    (r'\b(?:xmrig|minerd|cpuminer|ethminer)\b', "cryptocurrency miner"),

    # Network flooding/attacks
    (r'\bhping3\b.*--flood', "network flood attack"),
    (r'\bnmap\b.*-sS.*-p-', "aggressive port scan"),

    # System configuration corruption
    (r'\bsysctl\s+.*kernel\.panic', "kernel panic trigger"),
]

# Organize all patterns by category
DANGEROUS_PATTERNS = {
    "Destructive File Operations": DESTRUCTIVE_FILE_PATTERNS,
    "Disk Overwrite Operations": DISK_OVERWRITE_PATTERNS,
    "Fork Bombs": FORK_BOMB_PATTERNS,
    "Dangerous Permission Changes": PERMISSION_PATTERNS,
    "System File Overwriting": SYSTEM_FILE_PATTERNS,
    "Format Operations": FORMAT_PATTERNS,
    "Critical Process Termination": PROCESS_KILL_PATTERNS,
    "Additional Dangerous Commands": ADDITIONAL_DANGEROUS_PATTERNS,
}


# ==================== Allow-list Patterns ====================

ALLOWED_PATTERNS = [
    # Safe rm with confirmation
    r'\brm\s+.*-i',  # Interactive mode (prompts for confirmation)

    # Help/version queries (read-only)
    r'\b(?:rm|dd|chmod|kill)\s+(?:--help|-h|--version|-V)\b',

    # Man pages (documentation)
    r'\bman\s+(?:rm|dd|chmod|kill)',

    # Dry-run/preview modes
    r'\b\w+\s+.*(?:--dry-run|--simulate|-n)\b',

    # Project-local operations only
    r'^\s*rm\s+.*\./[^/]',  # rm starting with ./
]


# ==================== Category-Specific Messages ====================

CATEGORY_MESSAGES = {
    "Destructive File Operations": {
        "danger": """  - Attempts to recursively delete large portions of the filesystem
  - Will destroy critical system files and data
  - Results in permanent, irreversible data loss
  - Can make the system completely unbootable
  - No recovery possible without backups""",
        "alternatives": """  - Delete specific files: rm file.txt
  - Delete with confirmation: rm -i unwanted_files
  - Delete project files only: rm -r ./old_project/
  - Preview deletion: ls -R directory_to_delete/"""
    },
    "Disk Overwrite Operations": {
        "danger": """  - Directly writes to disk devices, bypassing filesystem
  - Can corrupt or destroy entire disk partitions
  - Will erase all data on affected disks
  - May make system completely unbootable
  - Typically requires privileged access but extremely dangerous""",
        "alternatives": """  - Create disk images: dd if=/dev/zero of=./file.img
  - Use filesystem tools: rsync, cp, mv
  - Backup before operations: Always backup first
  - Test in virtual machines: Practice with VMs first"""
    },
    "Fork Bombs": {
        "danger": """  - Creates exponentially growing processes
  - Will exhaust all system resources (CPU, memory, PIDs)
  - Makes system completely unresponsive
  - Requires hard reboot to recover
  - Can cause data loss in running applications""",
        "alternatives": """  - Use loops with limits: for i in {1..10}; do ...; done
  - Use process pools: xargs -P 4
  - Use proper background jobs: command &
  - Use job control: bg, fg, jobs"""
    },
    "Dangerous Permission Changes": {
        "danger": """  - Compromises system security by making files world-writable
  - Can allow unauthorized access to sensitive system files
  - May enable privilege escalation attacks
  - Recursive changes affect entire directory trees
  - Difficult to reverse once applied""",
        "alternatives": """  - Set specific permissions: chmod 755 ./script.sh
  - Minimal required permissions: chmod 644 ./config.txt
  - Change project ownership only: chown user:group ./project/
  - Use ACLs for complex permissions: setfacl"""
    },
    "System File Overwriting": {
        "danger": """  - Overwrites critical system configuration files
  - Can compromise system authentication and security
  - May render system unbootable
  - Corrupts kernel and boot files
  - Requires system reinstallation to recover""",
        "alternatives": """  - Write to project directories: echo "data" > ./config.txt
  - Use proper configuration tools: sudoedit, visudo
  - Create local config files: ./local/config
  - Never redirect to system directories"""
    },
    "Format Operations": {
        "danger": """  - Formats disks and partitions, erasing all data
  - Destroys filesystem structure permanently
  - All files on affected partitions are lost
  - No recovery possible after formatting
  - Can affect system boot partitions""",
        "alternatives": """  - Format disk images: mkfs.ext4 ./disk.img
  - Use cloud storage for data
  - Backup before formatting: Always backup first
  - Test with virtual disks first"""
    },
    "Critical Process Termination": {
        "danger": """  - Kills essential system processes
  - Can make system unstable or unresponsive
  - May cause data loss in running applications
  - System services may not restart properly
  - Could require system reboot""",
        "alternatives": """  - Kill specific processes: kill 12345
  - Graceful termination: kill -TERM process_name
  - Kill user apps only: killall myapp
  - Check before killing: ps aux | grep process_name"""
    },
    "Additional Dangerous Commands": {
        "danger": """  - Can compromise system stability and security
  - May exhaust system resources
  - Could enable network attacks
  - Difficult or impossible to reverse
  - May violate security policies""",
        "alternatives": """  - Use proper system tools
  - Test in isolated environments
  - Consult documentation first
  - Consider safer alternatives"""
    }
}


# ==================== Validation Logic ====================


def is_allowed_command(command: str) -> bool:
    """
    Check if command matches allow-list patterns.

    Args:
        command: Bash command to check

    Returns:
        True if command is explicitly allowed, False otherwise

    Examples:
        >>> is_allowed_command("rm --help")
        True
        >>> is_allowed_command("rm -i file.txt")
        True
        >>> is_allowed_command("rm -rf /")
        False
    """
    for pattern in ALLOWED_PATTERNS:
        try:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        except re.error:
            # Regex error: skip this pattern
            continue
    return False


def format_deny_message(command: str, category: str, description: str) -> str:
    """
    Format comprehensive denial message with explanation and alternatives.

    Args:
        command: The dangerous command that was blocked
        category: Category of dangerous command
        description: Pattern description that matched

    Returns:
        Formatted error message with educational content
    """
    messages = CATEGORY_MESSAGES.get(category, {
        "danger": "  - This command could cause system damage",
        "alternatives": "  - Use safer alternatives"
    })

    message = f"""⚠️ BLOCKED: Dangerous command detected

Command: {command}
Category: {category}
Pattern: {description}

Why this is dangerous:
{messages["danger"]}

Safe alternatives:
{messages["alternatives"]}

If you absolutely must run this command:
  1. Exit Claude Code
  2. Run the command manually in a terminal
  3. Understand the risks fully before proceeding

This protection exists to prevent accidental system damage."""

    return message


def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for dangerous patterns.

    Args:
        command: Bash command to validate

    Returns:
        None if safe, error message string if dangerous

    Examples:
        >>> validate_bash_command("ls -la")
        None
        >>> validate_bash_command("rm -rf /")
        '⚠️ BLOCKED: Dangerous command detected...'
    """
    if not command:
        return None

    try:
        # Step 1: Check allow-list (early return for safe patterns)
        if is_allowed_command(command):
            return None

        # Step 2: Check each dangerous pattern category
        for category, patterns in DANGEROUS_PATTERNS.items():
            for pattern, description in patterns:
                try:
                    if re.search(pattern, command, re.IGNORECASE):
                        return format_deny_message(command, category, description)
                except re.error:
                    # Regex error for this pattern: skip it
                    continue

        # Step 3: No dangerous patterns found
        return None

    except Exception:
        # Any other error: fail-safe, allow
        return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and command
        3. Validate command for dangerous patterns
        4. Output decision (allow or deny)

    Error Handling:
        All exceptions result in "allow" decision (fail-safe)
    """
    try:
        # Parse input from stdin
        result = parse_hook_input()
        if result is None:
            # Parse failed, fail-safe: allow
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = result

        # Only process Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Not a Bash command")
            return

        # Extract command
        command = tool_input.get("command", "")

        # Validate command
        error_message = validate_bash_command(command)

        # Output decision
        if error_message:
            # Dangerous command detected: deny with educational message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # Command is safe: allow
            output_decision("allow", "Command is safe")

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Destructive command blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
