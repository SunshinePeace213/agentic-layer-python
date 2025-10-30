#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Sensitive File Access Validator Hook
======================================

Prevents Claude Code from reading and writing sensitive files and system locations
during development. This hook serves as a critical security control to protect
credentials, secrets, private keys, and system files.

Purpose:
    Block access to sensitive files that could expose:
    - Credentials and secrets (environment variables, API keys, tokens)
    - Private keys (SSH keys, TLS certificates, GPG keys)
    - Configuration files (user authentication configs, cloud provider credentials)
    - System locations (critical system directories and configuration)

Hook Event: PreToolUse
Monitored Tools: Read, Write, Edit, Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with secure alternatives

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision, get_file_path
from utils.data_types import ToolInput


# ==================== Sensitive File Patterns ====================

# Category 1: Environment Variables
ENV_PATTERNS = [
    ('.env', 'environment variables'),
    ('.env.local', 'local environment variables'),
    ('.env.production', 'production environment'),
    ('.env.development', 'development environment'),
    ('.env.test', 'test environment'),
    ('.env.staging', 'staging environment'),
]

# Category 2: SSH Private Keys
SSH_KEY_PATTERNS = [
    ('id_rsa', 'SSH private key'),
    ('id_dsa', 'SSH private key'),
    ('id_ecdsa', 'SSH private key'),
    ('id_ed25519', 'SSH private key'),
    ('id_ed25519_sk', 'SSH security key'),
]

# Category 3: Certificates and Private Keys
CERT_PATTERNS = [
    ('.pem', 'certificate/key file'),
    ('.key', 'private key file'),
    ('.crt', 'certificate file'),
    ('.cer', 'certificate file'),
    ('.pfx', 'certificate archive'),
    ('.p12', 'certificate archive'),
    ('cert.pem', 'certificate file'),
    ('privkey.pem', 'private key file'),
    ('fullchain.pem', 'certificate chain'),
]

# Category 4: Cloud Provider Credentials
CLOUD_PATTERNS = [
    ('.aws/credentials', 'AWS credentials'),
    ('.aws/config', 'AWS configuration'),
    ('.azure/credentials', 'Azure credentials'),
    ('.config/gcloud/', 'Google Cloud credentials'),
    ('.docker/config.json', 'Docker registry credentials'),
    ('.kube/config', 'Kubernetes credentials'),
]

# Category 5: Package Manager Credentials
PACKAGE_PATTERNS = [
    ('.npmrc', 'npm credentials'),
    ('.pypirc', 'PyPI credentials'),
    ('.gem/credentials', 'RubyGems credentials'),
    ('.cargo/credentials', 'Cargo credentials'),
    ('.nuget/', 'NuGet credentials'),
]

# Category 6: VCS and Tool Credentials
VCS_PATTERNS = [
    ('.gitconfig', 'Git configuration'),
    ('.git-credentials', 'Git credentials'),
    ('.netrc', 'network credentials'),
    ('.hgrc', 'Mercurial configuration'),
]

# Category 7: Database Credentials
DB_PATTERNS = [
    ('.pgpass', 'PostgreSQL password file'),
    ('.my.cnf', 'MySQL credentials'),
    ('database.yml', 'Rails database config'),
]

# Category 8: Generic Credentials
GENERIC_PATTERNS = [
    ('credentials.json', 'credentials file'),
    ('credentials.yaml', 'credentials file'),
    ('secrets.json', 'secrets file'),
    ('secrets.yaml', 'secrets file'),
    ('secrets.toml', 'secrets file'),
    ('token', 'token file'),
    ('api_key', 'API key file'),
    ('service-account', 'service account credentials'),
    ('client_secret', 'OAuth client secret'),
]

# Combine all sensitive patterns
SENSITIVE_PATTERNS = (
    ENV_PATTERNS +
    SSH_KEY_PATTERNS +
    CERT_PATTERNS +
    CLOUD_PATTERNS +
    PACKAGE_PATTERNS +
    VCS_PATTERNS +
    DB_PATTERNS +
    GENERIC_PATTERNS
)

# Template/example file patterns (allowed)
ALLOWED_PATTERNS = [
    '.sample',
    '.example',
    '.template',
    '.dist',
    '.default',
    'example.',
    'sample.',
]

# System directories (write-only protection)
UNIX_SYSTEM_DIRS = [
    '/etc',
    '/usr',
    '/bin',
    '/sbin',
    '/boot',
    '/sys',
    '/proc',
    '/dev',
    '/lib',
    '/lib64',
    '/root',
]

WINDOWS_SYSTEM_DIRS = [
    'C:\\Windows',
    'C:\\Program Files',
    'C:\\Program Files (x86)',
]

# Protected configuration directories (write-only protection)
PROTECTED_CONFIG_DIRS = [
    '/.ssh/',
    '/.gnupg/',
    '/.aws/',
    '/.azure/',
    '/.docker/',
    '/.kube/',
    '/.config/gcloud/',
    '/.config/gh/',
]


# ==================== Bash Command Detection ====================

# Commands that read files
READ_COMMANDS = [
    'cat', 'less', 'more', 'head', 'tail',
    'grep', 'awk', 'sed', 'tac', 'strings',
]

# Commands that copy/move files
COPY_MOVE_COMMANDS = [
    'cp', 'mv', 'rsync', 'scp',
]

# Redirect patterns for write operations
REDIRECT_PATTERNS = [
    r'>\s*',      # stdout redirect
    r'>>\s*',     # stdout append
    r'2>\s*',     # stderr redirect
    r'&>\s*',     # both redirect
    r'&>>\s*',    # both append
]


# ==================== Error Message Templates ====================

def format_env_message(file_path: str, operation: str) -> str:
    """Format error message for environment variable file access."""
    op_verb = "reading" if operation == "read" else "writing to"
    return f"""🚫 Blocked {op_verb} environment variables file.

Path: {file_path}
File Type: Environment variables containing secrets and configuration

Why this is blocked:
  - Environment files contain sensitive credentials and API keys
  - {operation.capitalize()}ing .env exposes secrets in session transcripts and logs
  - Security policy requires secrets to remain outside version control
  - Exposing credentials creates security vulnerabilities

Secure alternatives:
  • Read template structure: Read('.env.sample')
  • Check if file exists: Bash('test -f .env && echo exists')
  • Document required variables in README
  • Use environment variable documentation tools

To understand .env structure:
  1. Create/read .env.sample with placeholder values
  2. Document each variable's purpose and format
  3. Never commit actual .env to version control

This protection prevents accidental credential exposure."""


def format_ssh_key_message(file_path: str, operation: str) -> str:
    """Format error message for SSH key access."""
    op_verb = "reading" if operation == "read" else "writing"
    return f"""🚫 Blocked {op_verb} SSH private key file.

Path: {file_path}
File Type: SSH private key for authentication

Why this is blocked:
  - SSH private keys provide authentication credentials
  - {'Reading' if operation == 'read' else 'Writing'} keys exposes them in session logs
  - Keys should never be created from templates or copied
  - Compromised keys create security vulnerabilities

Secure alternatives:
  • Generate new key: Bash('ssh-keygen -t ed25519 -C "email"')
  • Document key setup: Write('SSH_SETUP.md', '...')
  • Create key generation script: Write('scripts/generate_ssh_key.sh', '...')

To set up SSH keys properly:
  1. Use ssh-keygen with strong key type (ed25519, RSA 4096+)
  2. Protect with strong passphrase
  3. Set correct permissions (600 for private, 644 for public)
  4. Add public key to authorized services

This protection prevents insecure key {operation}."""


def format_cloud_credentials_message(file_path: str, operation: str) -> str:
    """Format error message for cloud credentials access."""
    op_verb = "reading" if operation == "read" else "writing to"
    cloud_provider = "AWS" if ".aws" in file_path.lower() else \
                     "Azure" if ".azure" in file_path.lower() else \
                     "Google Cloud" if "gcloud" in file_path.lower() else \
                     "Cloud provider"

    return f"""🚫 Blocked {op_verb} {cloud_provider} credentials file.

Path: {file_path}
File Type: {cloud_provider} access keys and secrets

Why this is blocked:
  - {cloud_provider} credentials provide broad cloud infrastructure access
  - {operation.capitalize()}ing credentials exposes them in session logs
  - Credential exposure can lead to unauthorized cloud usage
  - Security best practices require keeping credentials secure

Secure alternatives:
  • Check configuration: Bash('aws configure list')  # for AWS
  • Read documentation: Read('CLOUD_SETUP.md')
  • Create example config: Write('.aws/credentials.example', '...')
  • Use CLI to verify setup: Bash('aws sts get-caller-identity')

To work with cloud configuration:
  1. Use cloud CLI commands for setup
  2. Document required permissions in README
  3. Use IAM roles when possible (no credentials needed)
  4. Create example files with placeholder values

This protection prevents credential exposure."""


def format_system_directory_message(file_path: str) -> str:
    """Format error message for system directory write attempts."""
    return f"""⛔ Blocked writing to system directory.

Path: {file_path}
Directory: System configuration

Why this is blocked:
  - System directories contain critical OS configuration
  - Modifying system files can break system functionality
  - Requires elevated permissions (root/sudo)
  - Unintended changes can make system unstable or unbootable

Secure alternatives:
  • Document required changes: Write('SYSTEM_CONFIG.md', '...')
  • Create configuration script: Write('scripts/setup_config.sh', '...')
  • Use user-level configuration when possible
  • Manually apply changes with sudo after review

To modify system files safely:
  1. Exit Claude Code
  2. Review required changes thoroughly
  3. Make backup: sudo cp /path/file /path/file.backup
  4. Apply changes manually with sudo
  5. Test system functionality

This protection prevents accidental system damage."""


def format_generic_sensitive_message(file_path: str, file_type: str, operation: str) -> str:
    """Format generic error message for sensitive file access."""
    op_verb = "reading" if operation == "read" else "writing to"
    return f"""🚫 Blocked {op_verb} sensitive {file_type}.

Path: {file_path}
File Type: {file_type}

Why this is blocked:
  - This file contains or may contain sensitive credentials
  - {operation.capitalize()}ing exposes secrets in session logs
  - Security best practices require protecting credential files
  - Exposing credentials creates security vulnerabilities

Secure alternatives:
  • Create template file: Write('{os.path.basename(file_path)}.example', '...')
  • Document setup process: Write('CREDENTIALS_SETUP.md', '...')
  • Check if file exists: Bash('test -f {os.path.basename(file_path)} && echo exists')
  • Use secure credential management tools

To work with credentials safely:
  1. Create example/template files with placeholders
  2. Document where to obtain each credential
  3. Never commit actual credentials to version control
  4. Use environment variables or secret management tools

This protection prevents accidental credential exposure."""


def format_bash_command_message(command: str, file_path: str, file_type: str, operation: str) -> str:
    """Format error message for bash commands with sensitive file operations."""
    op_verb = "read from" if operation == "read" else "write to"
    return f"""🚫 Bash command attempts to {op_verb} sensitive file.

Command: {command}
File Path: {file_path}
File Type: {file_type}

Why this is blocked:
  - Command {operation}s sensitive file that may contain credentials
  - {operation.capitalize()} operations expose secrets in session logs
  - Security best practices require protecting credential files

Secure alternatives:
  • Create template: Write('{os.path.basename(file_path)}.sample', '...')
  • Document setup: Write('SETUP.md', '...')
  • Check existence: Bash('test -f {os.path.basename(file_path)} && echo exists')

To work safely:
  1. Use template files with placeholder values
  2. Document credential setup process
  3. Never commit actual credentials to version control
  4. Handle credentials manually outside Claude Code

This protection prevents insecure credential {operation}."""


# ==================== Validation Logic ====================


def is_template_file(file_path: str) -> bool:
    """
    Check if file path is a template/example file (allowed).

    Args:
        file_path: Path to check

    Returns:
        True if file is a template, False otherwise

    Examples:
        >>> is_template_file(".env.sample")
        True
        >>> is_template_file("example.env")
        True
        >>> is_template_file(".env")
        False
    """
    path_lower = file_path.lower()
    return any(pattern in path_lower for pattern in ALLOWED_PATTERNS)


def is_sensitive_file(file_path: str) -> Optional[tuple[str, str]]:
    """
    Check if file path matches sensitive patterns.

    Args:
        file_path: Path to check

    Returns:
        Tuple of (pattern, description) if sensitive, None otherwise

    Examples:
        >>> is_sensitive_file("/path/.env")
        ('.env', 'environment variables')
        >>> is_sensitive_file("/path/.env.sample")
        None
        >>> is_sensitive_file("/home/user/.ssh/id_rsa")
        ('id_rsa', 'SSH private key')
    """
    path_lower = file_path.lower()

    # Check if template file (allowed)
    if is_template_file(path_lower):
        return None

    # Check against sensitive patterns
    for pattern, description in SENSITIVE_PATTERNS:
        if pattern.lower() in path_lower:
            return (pattern, description)

    return None


def is_system_directory(file_path: str) -> bool:
    """
    Check if path is in a protected system directory.

    Args:
        file_path: Path to check

    Returns:
        True if in system directory, False otherwise

    Examples:
        >>> is_system_directory("/etc/hosts")
        True
        >>> is_system_directory("/home/user/file.txt")
        False
    """
    try:
        # Check both original and resolved paths (for symlinks like /etc -> /private/etc)
        paths_to_check = [
            str(Path(file_path).expanduser()),  # Original path with ~ expanded
            str(Path(file_path).resolve())      # Resolved path (follows symlinks)
        ]

        # Check Unix system directories
        for path_str in paths_to_check:
            for sys_dir in UNIX_SYSTEM_DIRS:
                if path_str.startswith(sys_dir):
                    return True

        # Check Windows system directories
        for path_str in paths_to_check:
            for sys_dir in WINDOWS_SYSTEM_DIRS:
                if path_str.startswith(sys_dir):
                    return True

        return False
    except Exception:
        # Path resolution error: fail-safe, allow
        return False


def is_protected_config_directory(file_path: str) -> bool:
    """
    Check if path is in a protected configuration directory.

    Args:
        file_path: Path to check

    Returns:
        True if in protected config directory, False otherwise

    Examples:
        >>> is_protected_config_directory("/home/user/.ssh/id_rsa")
        True
        >>> is_protected_config_directory("/home/user/project/file.txt")
        False
    """
    try:
        path_str = str(Path(file_path).resolve()).lower()

        # Check protected config directories
        for config_dir in PROTECTED_CONFIG_DIRS:
            if config_dir.lower() in path_str:
                return True

        return False
    except Exception:
        # Path resolution error: fail-safe, allow
        return False


def parse_bash_command(command: str) -> list[tuple[str, str]]:
    """
    Parse bash command to extract file operations.

    Args:
        command: Bash command string

    Returns:
        List of (operation_type, file_path) tuples

    Examples:
        >>> parse_bash_command("cat .env")
        [('read', '.env')]
        >>> parse_bash_command("echo SECRET > .env")
        [('write', '.env')]
    """
    operations: list[tuple[str, str]] = []

    # Split on command separators
    separators = ['&&', '||', ';', '|']
    segments: list[str] = [command]
    for sep in separators:
        new_segments: list[str] = []
        for seg in segments:
            parts: list[str] = seg.split(sep)
            new_segments.extend(parts)
        segments = new_segments

    for segment in segments:
        segment = segment.strip()

        # Check for read operations
        for read_cmd in READ_COMMANDS:
            pattern = rf'\b{re.escape(read_cmd)}\b\s+(.+)'
            match = re.search(pattern, segment)
            if match:
                # Extract file arguments (simple extraction)
                args = match.group(1).strip()
                # Remove common flags
                args = re.sub(r'-[a-zA-Z]+\s+', '', args)
                # Split by spaces and take file-like arguments
                for arg in args.split():
                    arg = arg.strip('"\'')
                    if arg and not arg.startswith('-'):
                        operations.append(('read', arg))

        # Check for write operations (redirects)
        for redirect_pattern in REDIRECT_PATTERNS:
            pattern = redirect_pattern + r'(\S+)'
            matches = re.finditer(pattern, segment)
            for match in matches:
                file_path = match.group(1).strip('"\'')
                operations.append(('write', file_path))

        # Check for copy/move operations
        for copy_cmd in COPY_MOVE_COMMANDS:
            pattern = rf'\b{re.escape(copy_cmd)}\b\s+(.+)'
            match = re.search(pattern, segment)
            if match:
                # Extract file arguments (last argument is usually destination)
                args = match.group(1).strip()
                # Remove common flags
                args = re.sub(r'-[a-zA-Z]+\s+', '', args)
                # Split and check all arguments
                for arg in args.split():
                    arg = arg.strip('"\'')
                    if arg and not arg.startswith('-'):
                        operations.append(('write', arg))

    return operations


def validate_file_path(file_path: str, operation: str) -> Optional[str]:
    """
    Validate file path for sensitive patterns.

    Args:
        file_path: File path to validate
        operation: 'read' or 'write'

    Returns:
        Error message if violation found, None otherwise
    """
    if not file_path:
        return None

    try:
        # Normalize path for sensitive file detection
        path = Path(file_path).resolve()
        path_str = str(path)

        # Check if sensitive file FIRST (before directory checks)
        # This ensures more specific error messages (e.g., "SSH key" vs "system directory")
        result = is_sensitive_file(path_str)
        if result:
            pattern, description = result

            # Generate appropriate error message based on file type
            if '.env' in pattern:
                return format_env_message(path_str, operation)
            elif pattern in ['id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', 'id_ed25519_sk']:
                return format_ssh_key_message(path_str, operation)
            elif '.aws' in pattern or '.azure' in pattern or 'gcloud' in pattern:
                return format_cloud_credentials_message(path_str, operation)
            else:
                return format_generic_sensitive_message(path_str, description, operation)

        # For write operations, check system directories
        # Check AFTER sensitive files to ensure specific messages take priority
        if operation == "write":
            # Check original path before resolution for symlinks like /etc -> /private/etc
            if is_system_directory(file_path):
                path_to_show = str(Path(file_path).resolve())
                return format_system_directory_message(path_to_show)

            if is_protected_config_directory(file_path):
                path_to_show = str(Path(file_path).resolve())
                return format_system_directory_message(path_to_show)

        return None

    except Exception:
        # Path resolution error: fail-safe, allow
        return None


def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for sensitive file operations.

    Args:
        command: Bash command string

    Returns:
        Error message if violation found, None otherwise
    """
    if not command:
        return None

    try:
        # Parse command to extract file operations
        operations = parse_bash_command(command)

        # Validate each operation
        for operation_type, file_path in operations:
            # Check if sensitive file
            try:
                path = Path(file_path).resolve()
                path_str = str(path)
            except Exception:
                # Can't resolve path, check as-is
                path_str = file_path

            result = is_sensitive_file(path_str)
            if result:
                _pattern, description = result
                return format_bash_command_message(command, path_str, description, operation_type)

            # For write operations, check system directories
            if operation_type == "write":
                if is_system_directory(path_str):
                    return format_bash_command_message(command, path_str, "system directory", operation_type)

        return None

    except Exception:
        # Parse error: fail-safe, allow
        return None


def validate_file_operation(tool_name: str, tool_input: ToolInput) -> Optional[str]:
    """
    Validate file operation based on tool and input.

    Args:
        tool_name: Name of the tool being used
        tool_input: Tool input parameters

    Returns:
        Error message if violation found, None otherwise
    """
    if tool_name == "Bash":
        # Validate bash command
        command = tool_input.get("command", "")
        return validate_bash_command(command)

    elif tool_name in ["Read", "Write", "Edit"]:
        # Validate file path
        file_path = get_file_path(tool_input)
        operation = "read" if tool_name == "Read" else "write"
        return validate_file_path(file_path, operation)

    return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and input
        3. Validate for sensitive file access
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

        # Only process file operation tools
        if tool_name not in {"Read", "Write", "Edit", "Bash"}:
            output_decision("allow", "Not a file operation tool")
            return

        # Validate file operation
        error_message = validate_file_operation(tool_name, tool_input)

        # Output decision
        if error_message:
            # Sensitive file detected: deny with educational message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # File operation is safe: allow
            output_decision("allow", "File operation is safe")

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Sensitive file validator error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
