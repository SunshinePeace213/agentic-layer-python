#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Unified Sensitive File Access (Write/Edit) Validation - PreToolUse Hook
===========================================
Prevents reading and writing of sensitive files and system locations.

This hook validates file operations to prevent:
- Reading sensitive files (.env, SSH keys, etc.)
- Writing to system directories
- Modifying critical configuration files
- Accessing credential files

Usage:
    python unified_write_validation.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import re
from pathlib import Path

# Import shared utilities and types
try:
    from .utils.utils import parse_hook_input, output_decision, get_file_path
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision, get_file_path
    from utils.data_types import ToolInput


def main() -> None:
    """
    Main entry point for the write validation hook.

    Reads hook data from stdin and outputs JSON decision.
    """
    # Parse input using shared utility
    parsed = parse_hook_input()
    if not parsed:
        return  # Error already handled

    tool_name, tool_input = parsed

    # Only validate file-related tools
    file_tools = {"Read", "Edit", "Write", "Bash"}

    if tool_name not in file_tools:
        output_decision("allow", "Not a file operation tool")
        return

    # Validate the file operation
    violation = validate_file_operation(tool_name, tool_input)

    if violation:
        # Deny operation with detailed reason
        output_decision("deny", violation, suppress_output=True)
    else:
        # Allow operation
        output_decision("allow", "File operation is safe")


def validate_file_operation(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Validate file operations for security concerns.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        Violation message if found, None otherwise
    """
    # Handle file-based tools
    if tool_name in {"Read", "Edit", "MultiEdit", "Write"}:
        file_path = get_file_path(tool_input)
        if file_path:
            # Determine operation type
            operation = "Read" if tool_name in {"Read"} else "Write"

            # Check for violations
            violation = check_file_path_violations(file_path, operation)
            if violation:
                return violation
    
    # Handle bash/shell commands
    elif tool_name in {"Bash"}:
        command = tool_input.get("command", "")
        if command:
            violations = check_bash_file_operations(command)
            if violations:
                # Return the first violation (most critical)
                return violations[0]
    
    return None


def check_file_path_violations(file_path: str, operation: str) -> str | None:
    """
    Check if a file path violates security rules.
    
    Args:
        file_path: Path to check
        operation: Type of operation (read/write)
        
    Returns:
        Violation message if found, None otherwise
    """
    path = Path(file_path)
    path_str = str(path).lower()
    
    # Check for sensitive files (both read and write)
    sensitive_files = [
        ('.env', 'environment variables'),
        ('.env.local', 'local environment variables'),
        ('.env.production', 'production environment'),
        ('.env.development', 'development environment'),
        ('.env.test', 'test environment'),
        ('id_rsa', 'SSH private key'),
        ('id_dsa', 'SSH private key'),
        ('id_ecdsa', 'SSH private key'),
        ('id_ed25519', 'SSH private key'),
        ('.pem', 'certificate/key file'),
        ('.key', 'private key file'),
        ('.pfx', 'certificate file'),
        ('.p12', 'certificate file'),
        ('credentials', 'credentials'),
        ('secrets', 'secrets'),
        ('.aws/credentials', 'AWS credentials'),
        ('.docker/config.json', 'Docker credentials'),
        ('.npmrc', 'npm credentials'),
        ('.pypirc', 'PyPI credentials'),
        ('.gitconfig', 'Git configuration'),
        ('.netrc', 'network credentials'),
    ]
    
    # Allow template/example files
    allowed_patterns = ['.sample', '.example', '.template', '.dist']
    
    for sensitive_file, description in sensitive_files:
        if sensitive_file in path_str:
            # Check if it's an allowed template file
            if any(pattern in path_str for pattern in allowed_patterns):
                continue
            
            action = "reading" if operation == "read" else "writing to"
            
            return (
                f"🚫 Blocked {action} {description} file. \n"
                f"Path: {file_path}. \n"
                f"Security policy: Never access sensitive files directly. \n"
                f"Alternative: Use {sensitive_file}.sample or {sensitive_file}.example for templates. \n"
            )
    
    # Additional write-only restrictions
    if operation == "Write":
        # Block writes to system directories
        system_dirs = [
            '/etc', '/usr', '/bin', '/sbin', '/boot', 
            '/sys', '/proc', '/dev', '/lib', '/lib64'
        ]
        
        for sys_dir in system_dirs:
            if str(path).startswith(sys_dir):
                return (
                    f"⛔ Blocked writing to system directory. \n"
                    f"Path: {file_path}. \n"
                    f"Security policy: System directories are read-only. \n"
                    f"Alternative: Use user directories like /home or current directory. \n"
                    f"System modifications require proper permissions and procedures. \n"
                )
        
        # Block writes to home config directories
        config_patterns = [
            '/.ssh/', '/.gnupg/', '/.aws/', '/.docker/',
            '/.kube/', '/.config/gcloud/', '/.azure/'
        ]
        
        for config_pattern in config_patterns:
            if config_pattern in str(path):
                return (
                    f"⚠️ Blocked writing to configuration directory. \n"
                    f"Path: {file_path}. \n"
                    f"Security policy: User configuration directories are protected. \n"
                    f"Alternative: Create example configs with .sample extension. \n"
                    f"Manual configuration is safer for sensitive settings. \n"
                )
    
    return None


def check_bash_file_operations(command: str) -> list[str]:
    """
    Check bash commands for file operations that violate security rules.
    
    Args:
        command: Bash command to check
        
    Returns:
        List of violation messages
    """
    violations: list[str] = []
    
    # Truncate long commands for display
    display_cmd = command if len(command) <= 60 else command[:57] + "..."
    
    # Patterns for detecting file operations on sensitive files
    sensitive_patterns = [
        (r'\.env\b(?!\.sample|\.example|\.template)', '.env file'),
        (r'id_rsa\b', 'SSH private key'),
        (r'id_dsa\b', 'SSH private key'),
        (r'\.pem\b', 'certificate/key file'),
        (r'\.key\b', 'private key file'),
        (r'credentials\b', 'credentials file'),
        (r'\.aws/credentials', 'AWS credentials'),
        (r'\.npmrc\b', 'npm credentials'),
        (r'\.pypirc\b', 'PyPI credentials'),
    ]
    
    # Commands that read files
    read_commands = ['cat', 'less', 'more', 'head', 'tail', 'grep', 'awk', 'sed', 'echo', 'touch', 'open']
    
    # Check for read operations
    for cmd in read_commands:
        if cmd in command:
            for pattern, description in sensitive_patterns:
                if re.search(pattern, command):
                    violations.append(
                        f"🚫 Bash command attempts to read {description}. \n"
                        f"Command: {display_cmd}. \n"
                        f"Security policy: Sensitive files must not be exposed. \n"
                        f"Alternative: Use template files or environment variables. \n"
                    )
                    break
    
    # Check for write operations (redirects)
    if '>' in command or '>>' in command:
        for pattern, description in sensitive_patterns:
            if re.search(pattern, command):
                violations.append(
                    f"🚫 Bash command attempts to write to {description}. \n"
                    f"Command: {display_cmd}. \n"
                    f"Security policy: Never create sensitive files directly. \n"
                    f"Alternative: Create .sample or .example templates instead. \n"
                )
                break
        
        # Check for writes to system directories
        system_patterns = [
            r'>\s*/etc/', r'>\s*/usr/', r'>\s*/bin/', 
            r'>\s*/sbin/', r'>\s*/boot/', r'>\s*/sys/'
        ]
        
        for sys_pattern in system_patterns:
            if re.search(sys_pattern, command):
                violations.append(
                    f"⛔ Bash command attempts to write to system directory. \n "
                    f"Command: {display_cmd}. \n"
                    f"Security policy: System directories are protected. \n"
                    f"Alternative: Use user directories for file operations. \n"
                )
                break
    
    # Check for copy/move operations on sensitive files
    if re.search(r'\b(cp|mv)\b', command):
        for pattern, description in sensitive_patterns:
            if re.search(pattern, command):
                violations.append(
                    f"⚠️ Bash command attempts to copy/move {description}. \n"
                    f"Command: {display_cmd}. \n"
                    f"Security policy: Sensitive files must not be duplicated. \n"
                    f"Alternative: Handle credentials through secure channels. \n"
                )
                break
    
    return violations


if __name__ == "__main__":
    main()
