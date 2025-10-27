#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Temporary Directory Creation Blocker - PreToolUse Hook
=======================================================
Prevents file creation in system temporary directories during Claude Code operations.

This hook ensures all generated files remain within the project directory for better
observability, version control, and workflow management.

Blocked Directories:
- /tmp/
- /var/tmp/
- $TMPDIR/
- /private/tmp/ (macOS)
- /private/var/tmp/ (macOS)
- C:\\Temp\\ (Windows)
- %TEMP%\\ (Windows)

Usage:
    This hook is automatically invoked by Claude Code before file operations.
    It receives JSON input via stdin and outputs JSON permission decisions.

Dependencies:
    - Python >= 3.12
    - No external packages (standard library only)
    - Shared utilities from .claude/hooks/pre_tools/utils/

Exit Codes:
    0: Success (decision output via stdout)

Author: Claude Code Hook Expert
Version: 2.0.0
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Temporary Directory Definitions ============

# Known system temporary directory paths (normalized, absolute)
SYSTEM_TEMP_DIRS = [
    "/tmp",
    "/var/tmp",
    "/private/tmp",
    "/private/var/tmp",
]

# Windows temporary directories
WINDOWS_TEMP_DIRS = [
    r"C:\Temp",
    r"C:\Windows\Temp",
]

# Environment variable names that point to temp directories
TEMP_ENV_VARS = ["TMPDIR", "TEMP", "TMP"]


# ============ Path Detection Functions ============

def get_all_temp_directories() -> list[str]:
    """
    Get all system temporary directories for the current platform.

    Returns:
        List of normalized absolute paths to temporary directories
    """
    temp_dirs: list[str] = []

    # Add Unix/Linux/macOS standard paths
    if os.name != 'nt':  # Not Windows
        temp_dirs.extend(SYSTEM_TEMP_DIRS)

    # Add Windows paths
    if os.name == 'nt':
        temp_dirs.extend(WINDOWS_TEMP_DIRS)

    # Add directories from environment variables
    for env_var in TEMP_ENV_VARS:
        env_value = os.environ.get(env_var)
        if env_value and os.path.isdir(env_value):
            # Normalize and resolve symlinks
            try:
                resolved = str(Path(env_value).resolve())
                if resolved not in temp_dirs:
                    temp_dirs.append(resolved)
            except (OSError, ValueError):
                # Skip if path resolution fails
                pass

    return temp_dirs


def check_path_is_temp_directory(file_path: str) -> bool:
    """
    Check if a file path is within a system temporary directory.

    Args:
        file_path: Path to check (can be relative or absolute)

    Returns:
        True if path is in a temporary directory, False otherwise
    """
    if not file_path:
        return False

    try:
        # Convert to absolute path
        abs_path = os.path.abspath(file_path)

        # Normalize path separators
        normalized_path = os.path.normpath(abs_path)

        # Get all temp directories for current platform
        temp_dirs = get_all_temp_directories()

        # Check if path starts with any temp directory
        for temp_dir in temp_dirs:
            temp_dir_norm = os.path.normpath(temp_dir)

            # Check if file is within temp directory
            # Use os.path.commonpath to ensure proper directory boundary checking
            try:
                common = os.path.commonpath([normalized_path, temp_dir_norm])
                if common == temp_dir_norm:
                    return True
            except ValueError:
                # Paths on different drives (Windows)
                continue

    except (OSError, ValueError):
        # If path resolution fails, allow operation (fail-safe)
        return False

    return False


def extract_bash_output_paths(command: str) -> list[str]:
    """
    Extract file paths from bash commands that create/write files.

    Handles:
    - Redirects: > file, >> file, 2> file
    - Touch: touch file
    - Echo: echo text > file
    - Cat: cat input > output
    - Tee: command | tee file

    Args:
        command: Bash command string

    Returns:
        List of file paths found in the command
    """
    paths: list[str] = []

    # Pattern 1: Redirect operators (>, >>, 2>, &>)
    # Matches: echo "text" > /tmp/file.txt
    redirect_pattern = re.compile(r'(?:>>?|2>>?|&>>?)\s+([^\s;|&<>]+)')
    paths.extend(redirect_pattern.findall(command))

    # Pattern 2: Touch command
    # Matches: touch /tmp/file.txt
    touch_pattern = re.compile(r'\btouch\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)')
    paths.extend(touch_pattern.findall(command))

    # Pattern 3: Tee command
    # Matches: command | tee /tmp/file.txt
    tee_pattern = re.compile(r'\btee\s+(?:-[a-z]+\s+)*([^\s;|&<>]+)')
    paths.extend(tee_pattern.findall(command))

    return paths


def generate_project_alternative(temp_path: str, _project_dir: str) -> str:
    """
    Generate a project-relative alternative path suggestion.

    Args:
        temp_path: Original temporary directory path
        _project_dir: Current project directory (reserved for future use)

    Returns:
        Suggested project-relative path
    """
    # Extract filename from temp path
    filename = os.path.basename(temp_path)

    # Suggest creating in ./tmp/ subdirectory
    return f"./tmp/{filename}"


# ============ Main Validation ============

def validate_file_path(file_path: str, project_dir: str) -> Optional[str]:
    """
    Validate that a file path is not in a system temporary directory.

    Args:
        file_path: Path to validate
        project_dir: Current project directory

    Returns:
        Error message if invalid, None if valid
    """
    if check_path_is_temp_directory(file_path):
        alternative = generate_project_alternative(file_path, project_dir)

        return f"""📂 Blocked: File creation in system temporary directory

Path: {file_path}

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: {alternative}
  - Use project subdirectory: ./output/{os.path.basename(file_path)}
  - Use workspace directory: ./workspace/{os.path.basename(file_path)}

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable."""

    return None


def main() -> None:
    """
    Main entry point for temporary directory creation blocker hook.

    Reads JSON input from stdin, validates file paths, and outputs
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

        # Get current project directory
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Handle file-based tools (Write, Edit, MultiEdit, NotebookEdit)
        if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            file_path = tool_input.get("file_path", "")
            if not file_path:
                output_decision("allow", "No file path to validate")
                return

            error = validate_file_path(file_path, project_dir)
            if error:
                output_decision("deny", error, suppress_output=True)
            else:
                output_decision("allow", "Path is not in system temporary directory")

        # Handle Bash commands
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if not command:
                output_decision("allow", "No command to validate")
                return

            # Extract file paths from bash command
            paths = extract_bash_output_paths(command)

            # Validate each extracted path
            for path in paths:
                error = validate_file_path(path, project_dir)
                if error:
                    # Add command context to error message
                    full_message = f"{error}\n\nCommand: {command}"
                    output_decision("deny", full_message, suppress_output=True)
                    return

            output_decision("allow", "Command does not write to temporary directories")

        else:
            # Other tools - allow
            output_decision("allow", f"Tool '{tool_name}' not monitored by this hook")

    except Exception as e:
        # Fail-safe: allow operation on error
        print(f"Temporary directory blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
