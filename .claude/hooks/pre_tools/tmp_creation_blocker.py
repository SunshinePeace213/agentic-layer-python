#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
r"""
Temporary Directory Creation Blocker Hook
==========================================

Prevents file creation in system temporary directories during Claude Code development,
encouraging the use of project-local directories instead.

Purpose:
    Block file creation in system temp directories (e.g., /tmp/, C:\Temp\, $TMPDIR)
    to ensure better observability, version control integration, and workflow management.

Hook Event: PreToolUse
Monitored Tools: Write, Edit, Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Helpful error messages with project-relative alternatives

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 2.1.0
Last Updated: 2025-10-30
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Constants ====================

# Unix/Linux/macOS temporary directories
SYSTEM_TEMP_DIRS: list[str] = [
    "/tmp",
    "/var/tmp",
    "/private/tmp",  # macOS
    "/private/var/tmp",  # macOS
]

# Windows temporary directories
WINDOWS_TEMP_DIRS: list[str] = [
    "C:\\Temp",
    "C:\\Windows\\Temp",
]

# Environment variables that may contain temp directory paths
TEMP_ENV_VARS = ["TMPDIR", "TEMP", "TMP"]


# ==================== Temporary Directory Detection ====================


def get_all_temp_directories() -> list[str]:
    """
    Get all system temporary directories for current platform.

    Returns:
        List of absolute paths to system temporary directories

    Examples:
        >>> # On Unix-like systems
        >>> dirs = get_all_temp_directories()
        >>> "/tmp" in dirs
        True
        >>> # On Windows
        >>> "C:\\Temp" in dirs  # (if on Windows)
        True
    """
    temp_dirs: list[str] = []

    # Add platform-specific standard paths
    if os.name != "nt":  # Unix-like (Linux, macOS)
        temp_dirs.extend(SYSTEM_TEMP_DIRS)
    else:  # Windows
        temp_dirs.extend(WINDOWS_TEMP_DIRS)

    # Add directories from environment variables
    for env_var in TEMP_ENV_VARS:
        env_value = os.environ.get(env_var)
        if env_value and os.path.isdir(env_value):
            # Resolve symlinks and normalize path
            resolved: str = str(Path(env_value).resolve())
            if resolved not in temp_dirs:
                temp_dirs.append(resolved)

    return temp_dirs


def check_path_is_temp_directory(file_path: str) -> bool:
    """
    Check if file path is within a system temporary directory.

    Args:
        file_path: Path to check (can be absolute or relative)

    Returns:
        True if path is in a system temp directory, False otherwise

    Security:
        - Normalizes paths to prevent traversal attacks
        - Resolves symlinks for accurate comparison
        - Uses os.path.commonpath for proper boundary checking
        - Fails safe (returns False on errors)

    Examples:
        >>> check_path_is_temp_directory("/tmp/file.txt")
        True
        >>> check_path_is_temp_directory("./tmp/file.txt")
        False
        >>> check_path_is_temp_directory("/home/user/project/tmp/file.txt")
        False
    """
    if not file_path:
        return False

    try:
        # Convert to absolute path and resolve symlinks
        # This ensures /var/... and /private/var/... are treated as the same
        resolved_path = str(Path(file_path).resolve())
        normalized_path = os.path.normpath(resolved_path)

        # Check against all temp directories
        for temp_dir in get_all_temp_directories():
            temp_dir_norm = os.path.normpath(temp_dir)

            # Use os.path.commonpath for proper boundary checking
            try:
                common = os.path.commonpath([normalized_path, temp_dir_norm])
                if common == temp_dir_norm:
                    return True
            except ValueError:
                # Paths on different drives (Windows) or invalid paths
                continue

    except (OSError, ValueError):
        # Fail-safe: allow on error (don't block valid operations)
        return False

    return False


# ==================== Bash Command Parsing ====================


def extract_bash_output_paths(command: str) -> list[str]:
    """
    Extract file paths from bash commands that create/write files.

    Detects:
        - Redirect operators: >, >>, 2>, &>
        - touch command: touch file1 file2
        - tee command: command | tee file

    Args:
        command: Bash command string to parse

    Returns:
        List of file paths that would be created/written by the command

    Examples:
        >>> extract_bash_output_paths('echo "text" > /tmp/output.txt')
        ['/tmp/output.txt']
        >>> extract_bash_output_paths('touch /tmp/file1.txt /tmp/file2.txt')
        ['/tmp/file1.txt', '/tmp/file2.txt']
        >>> extract_bash_output_paths('ls -la | tee /tmp/listing.txt')
        ['/tmp/listing.txt']
    """
    paths: list[str] = []

    try:
        # Pattern 1: Redirect operators (>, >>, 2>, &>)
        # Matches: echo "text" > /tmp/file.txt
        # Note: Non-greedy matching to handle multiple redirects
        redirect_pattern = re.compile(r"(?:>>?|2>>?|&>>?)\s+([^\s;|&<>]+)")
        paths.extend(redirect_pattern.findall(command))

        # Pattern 2: Touch command
        # Matches: touch /tmp/file.txt
        # Handles flags like: touch -a /tmp/file.txt
        touch_pattern = re.compile(r"\btouch\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)")
        paths.extend(touch_pattern.findall(command))

        # Pattern 3: Tee command
        # Matches: command | tee /tmp/file.txt
        # Handles flags like: tee -a /tmp/file.txt
        tee_pattern = re.compile(r"\btee\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)")
        paths.extend(tee_pattern.findall(command))

    except re.error:
        # Regex error: fail-safe, return empty list
        return []

    return paths


# ==================== Alternative Path Generation ====================


def generate_project_alternative(temp_path: str, _project_dir: str) -> str:
    """
    Generate project-relative alternative path suggestion.

    Args:
        temp_path: Original temporary directory path
        _project_dir: Project root directory path (reserved for future use)

    Returns:
        Suggested project-relative path

    Examples:
        >>> generate_project_alternative("/tmp/data.json", "/project")
        './tmp/data.json'
        >>> generate_project_alternative("/var/tmp/output.txt", "/project")
        './tmp/output.txt'
    """
    filename = os.path.basename(temp_path)
    return f"./tmp/{filename}"


def format_deny_message(blocked_path: str, project_dir: str) -> str:
    """
    Format a helpful denial message with alternatives.

    Args:
        blocked_path: Path that was blocked
        project_dir: Project root directory

    Returns:
        Formatted error message with explanation and alternatives
    """
    alternative = generate_project_alternative(blocked_path, project_dir)

    return f"""📂 Blocked: File creation in system temporary directory

Path: {blocked_path}

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: {alternative}
  - Use project subdirectory: ./output/{os.path.basename(blocked_path)}
  - Use workspace directory: ./workspace/{os.path.basename(blocked_path)}

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable."""


# ==================== Validation Functions ====================


def validate_file_path(file_path: str, project_dir: str) -> Optional[str]:
    """
    Validate a file path is not in a system temporary directory.

    Args:
        file_path: Path to validate
        project_dir: Project root directory

    Returns:
        None if validation passes, error message string if validation fails
    """
    if not file_path:
        return None

    if check_path_is_temp_directory(file_path):
        return format_deny_message(file_path, project_dir)

    return None


def validate_bash_command(command: str, project_dir: str) -> Optional[str]:
    """
    Validate a bash command doesn't write to system temporary directories.

    Args:
        command: Bash command to validate
        project_dir: Project root directory

    Returns:
        None if validation passes, error message string if validation fails
    """
    if not command:
        return None

    # Extract all output paths from the command
    output_paths = extract_bash_output_paths(command)

    # Check each path
    for path in output_paths:
        if check_path_is_temp_directory(path):
            return format_deny_message(path, project_dir)

    return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and parameters
        3. Validate based on tool type
        4. Output decision (allow or deny)

    Error Handling:
        All exceptions result in "allow" decision (fail-safe)
    """
    try:
        # Get project directory (fallback to cwd if not set)
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Parse input from stdin
        result = parse_hook_input()
        if result is None:
            # Parse failed, fail-safe: allow
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = result

        # Determine validation based on tool type
        error_message: Optional[str] = None

        if tool_name in ("Write", "Edit"):
            # File operation tools: validate file_path
            file_path = tool_input.get("file_path", "")
            error_message = validate_file_path(file_path, project_dir)

        elif tool_name == "Bash":
            # Bash tool: parse command and validate output paths
            command = tool_input.get("command", "")
            error_message = validate_bash_command(command, project_dir)

        # Output decision
        if error_message:
            # Validation failed: deny with helpful message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # Validation passed: allow
            output_decision("allow", "Path is not in system temporary directory")

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Temporary directory blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
