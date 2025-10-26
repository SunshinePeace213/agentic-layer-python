#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Temporary Directory Creation Blocker - PreToolUse Hook
======================================================
Prevents file creation in system temp directories for better observability.
"""

import os
import re
from pathlib import Path

# Import shared utilities
try:
    from .utils.utils import parse_hook_input, output_decision
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision
    from utils.data_types import ToolInput


TEMP_DIRECTORIES = [
    "/tmp/",
    "/var/tmp/",
    "/private/tmp/",  # macOS specific
    "/dev/shm/",      # Shared memory temp
    "/run/shm/",      # Alternative shared memory location
]


def check_path_is_temp_directory(file_path: str) -> bool:
    """Check if path is in a temp directory."""
    # First check the original path (for absolute paths)
    if any(file_path.startswith(temp_dir) for temp_dir in TEMP_DIRECTORIES):
        return True

    # Then check normalized path (for relative paths and symlinks)
    normalized = normalize_path(file_path)
    return any(normalized.startswith(temp_dir) for temp_dir in TEMP_DIRECTORIES)


def normalize_path(file_path: str) -> str:
    """Normalize path for reliable comparison."""
    try:
        # Get project directory with fallback
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Convert to absolute path if relative
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_dir, file_path)

        # Resolve symlinks and normalize
        return str(Path(file_path).resolve())
    except Exception:
        # If normalization fails, return original path
        return file_path


def suggest_alternative_path(blocked_path: str) -> str:
    """Generate project-local alternative path."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    filename = os.path.basename(blocked_path)

    # Suggest project-local temp directory
    alternative = os.path.join(project_dir, "temp", filename)
    return alternative


def format_denial_message(blocked_path: str) -> str:
    """Format denial message with alternative suggestion."""
    alternative = suggest_alternative_path(blocked_path)

    return (
        f"🚫 Blocked file creation in system temp directory.\n"
        f"Path: {blocked_path}\n"
        f"Policy: Never create files in system temp paths for better observability.\n"
        f"Alternative: Use project directory instead:\n"
        f"  - Create: {alternative}\n"
        f"  - Then add 'temp/' to .gitignore if needed\n"
    )


def check_bash_temp_file_creation(command: str) -> str | None:
    """Check bash command for temp file creation."""
    # Look for file redirections (>, >>)
    redirect_pattern = r'>>\s*([^\s;|&]+)|>\s*([^\s;|&]+)'
    matches: list[tuple[str, str]] = re.findall(redirect_pattern, command)

    for match_group in matches:
        # Extract the file path (from either capture group)
        file_path: str = match_group[0] if match_group[0] else match_group[1]

        if file_path and check_path_is_temp_directory(file_path):
            display_cmd = command if len(command) <= 60 else command[:57] + "..."
            alternative_cmd = command.replace(file_path, "./temp/" + os.path.basename(file_path))

            return (
                f"🚫 Bash command attempts to create file in temp directory.\n"
                f"Command: {display_cmd}\n"
                f"Policy: Never create files in system temp paths.\n"
                f"Alternative: Use project directory:\n"
                f"  {alternative_cmd}\n"
            )

    # Look for touch, echo >, cat > commands with temp paths
    file_creation_patterns: list[tuple[str, str]] = [
        (r'touch\s+([^\s;|&]+)', 'touch'),
        (r'echo\s+.*?\s*>\s*([^\s;|&]+)', 'echo >'),
        (r'cat\s+.*?\s*>\s*([^\s;|&]+)', 'cat >'),
    ]

    for pattern, _cmd_name in file_creation_patterns:
        pattern_matches: list[str] = re.findall(pattern, command)
        for file_path_match in pattern_matches:
            if file_path_match and check_path_is_temp_directory(file_path_match):
                display_cmd = command if len(command) <= 60 else command[:57] + "..."
                return (
                    f"🚫 Bash command attempts to create file in temp directory.\n"
                    f"Command: {display_cmd}\n"
                    f"Policy: Never create files in system temp paths.\n"
                    f"Alternative: Use project directory instead\n"
                )

    return None


def validate_file_creation(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Validate file creation operation.

    Returns:
        Violation message if temp directory detected, None otherwise
    """
    # Handle Write and NotebookEdit tools
    if tool_name in {"Write", "NotebookEdit"}:
        file_path = tool_input.get("file_path", "")
        if file_path and check_path_is_temp_directory(file_path):
            return format_denial_message(file_path)

    # Handle Bash commands
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            violation = check_bash_temp_file_creation(command)
            if violation:
                return violation

    return None


def main() -> None:
    """Main entry point."""
    parsed = parse_hook_input()
    if not parsed:
        output_decision("allow", "Invalid input format, allowing operation")
        return

    tool_name, tool_input = parsed

    # Validate file creation
    violation = validate_file_creation(tool_name, tool_input)

    if violation:
        output_decision("deny", violation, suppress_output=True)
    else:
        output_decision("allow", "File operation is safe")


if __name__ == "__main__":
    main()
