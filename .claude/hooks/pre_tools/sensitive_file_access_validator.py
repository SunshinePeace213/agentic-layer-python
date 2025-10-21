#!/usr/bin/env python3
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

import json
import re
import sys
from pathlib import Path
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    file_path: str
    path: str
    command: str
    content: str


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
    Main entry point for the write validation hook.
    
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
        
        # Only validate file-related tools
        file_tools = {"Read", "Edit", "MultiEdit", "Write", "Bash"}
        
        if tool_name not in file_tools:
            # Not a file operation tool - allow
            output_decision("allow", "Not a file operation tool")
            return
        
        # Create typed tool input
        typed_tool_input = ToolInput()
        
        # Extract relevant fields
        file_path_val = tool_input_obj.get("file_path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val
        
        path_val = tool_input_obj.get("path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(path_val, str):
            typed_tool_input["path"] = path_val
        
        command_val = tool_input_obj.get("command")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(command_val, str):
            typed_tool_input["command"] = command_val
        
        # Validate the file operation
        violation = validate_file_operation(tool_name, typed_tool_input)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "File operation is safe")
            
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
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if file_path:
            # Determine operation type
            operation = "read" if tool_name in {"Read", "view"} else "write"
            
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
    if operation == "write":
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
