#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Dependency Blocker - PreToolUse Hook
========================================
Prevents direct editing of Python dependency files to enforce UV command usage.

This hook ensures all dependency changes are managed through UV commands,
maintaining consistency, reproducibility, and proper dependency tracking.

Blocked Files:
- requirements.txt - Legacy pip requirements format
- pyproject.toml - Modern Python project metadata (PEP 621)
- uv.lock - UV lock file for reproducible installs
- Pipfile - Pipenv dependency specification
- Pipfile.lock - Pipenv lock file

Blocked Tools:
- Write: Creating or overwriting dependency files
- Edit: Inline editing of dependency files
- MultiEdit: Multi-file edits including dependency files
- Bash: Shell commands that modify dependency files

Usage:
    This hook is automatically invoked by Claude Code before tool operations.
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

import os
import re
import sys
from typing import Optional

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Dependency File Definitions ============

DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
}


# ============ Detection Functions ============

def is_dependency_file(file_path: str) -> bool:
    """
    Check if a file path represents a dependency file.

    Args:
        file_path: Absolute or relative file path

    Returns:
        True if file is a dependency file, False otherwise

    Examples:
        >>> is_dependency_file("/project/requirements.txt")
        True
        >>> is_dependency_file("./pyproject.toml")
        True
        >>> is_dependency_file("/project/src/main.py")
        False
        >>> is_dependency_file("/project/requirements.txt.bak")
        False
    """
    if not file_path:
        return False

    filename = os.path.basename(file_path)
    return filename in DEPENDENCY_FILES


def extract_file_paths_from_bash(command: str) -> list[str]:
    """
    Extract file paths from bash commands that might modify files.

    Detects:
    - Redirect operators: >, >>, 2>, &>
    - Inline edit commands: sed -i, perl -i
    - Text editors: vi, vim, nano, emacs

    Args:
        command: Shell command string

    Returns:
        List of file paths found in the command

    Examples:
        >>> extract_file_paths_from_bash("echo 'test' > requirements.txt")
        ['requirements.txt']
        >>> extract_file_paths_from_bash("sed -i 's/old/new/' pyproject.toml")
        ['pyproject.toml']
    """
    paths: list[str] = []

    # Pattern 1: Redirect operators (>, >>, 2>, &>)
    redirect_pattern = re.compile(r'(?:>>?|2>>?|&>>?)\s+([^\s;|&<>]+)')
    paths.extend(redirect_pattern.findall(command))

    # Pattern 2: Inline edit commands (sed -i, perl -i)
    # Matches sed -i, sed -i.bak, perl -i -pe, etc.
    # Captures the last argument as the file path
    inline_edit_pattern = re.compile(r'\b(?:sed|perl)\s+(?:-[a-z]*i(?:\.[a-z]+)?(?:\s+-[a-z]+)*)\s+(?:.*?\s+)?([^\s;|&<>]+)$')
    inline_matches: list[str] = inline_edit_pattern.findall(command)
    # Only add if match doesn't start with a quote (likely a substitution pattern)
    filtered_matches: list[str] = [m for m in inline_matches if not m.startswith("'") and not m.startswith('"')]
    paths.extend(filtered_matches)

    # Additional simpler pattern for common sed/perl cases
    # Matches: sed -i 'pattern' file or sed -i "pattern" file
    sed_simple = re.compile(r'\b(?:sed|perl)\s+(?:-[a-z.]+\s+)?["\'][^"\']+["\']\s+([^\s;|&<>]+)')
    paths.extend(sed_simple.findall(command))

    # Pattern 3: Text editors (vi, vim, nano, emacs)
    editor_pattern = re.compile(r'\b(?:vi|vim|nano|emacs)\s+([^\s;|&<>]+)')
    paths.extend(editor_pattern.findall(command))

    return paths


# ============ UV Alternative Suggestions ============

def get_uv_alternatives(filename: str) -> str:
    """
    Get UV command alternatives based on the dependency file.

    Args:
        filename: Name of the dependency file

    Returns:
        Formatted string with UV alternatives
    """
    if filename == "requirements.txt":
        return """Recommended UV commands:
  - Add package:        uv add <package>
  - Add with version:   uv add "package>=1.0,<2.0"
  - Add dev package:    uv add --dev <package>
  - Remove package:     uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync all:           uv sync
  - Install from lock:  uv sync --frozen

Note: UV uses pyproject.toml for dependency tracking (modern standard)"""

    elif filename == "pyproject.toml":
        return """Recommended UV commands:
  - Add dependency:     uv add <package>
  - Add dev dependency: uv add --dev <package>
  - Add with group:     uv add --group <group> <package>
  - Remove dependency:  uv remove <package>
  - Update package:     uv add --upgrade <package>
  - Sync dependencies:  uv sync
  - Lock dependencies:  uv lock

Manual edits to pyproject.toml should be followed by: uv lock"""

    elif filename == "uv.lock":
        return """Recommended UV commands:
  - Regenerate lock:    uv lock
  - Update all:         uv lock --upgrade
  - Update package:     uv lock --upgrade-package <package>
  - Sync from lock:     uv sync --frozen

IMPORTANT: Never edit uv.lock manually!
This file is auto-generated by UV and ensures reproducibility."""

    elif filename in ("Pipfile", "Pipfile.lock"):
        return """Recommended UV commands:
  - Add dependency:     uv add <package>
  - Add dev dependency: uv add --dev <package>
  - Remove dependency:  uv remove <package>
  - Sync dependencies:  uv sync

Note: Consider migrating from Pipenv to UV for better performance:
  1. Review Pipfile dependencies
  2. Use: uv add <package1> <package2> ...
  3. UV will create pyproject.toml and uv.lock
  4. Safely remove Pipfile after migration"""

    else:
        return """Recommended UV commands:
  - Add package:        uv add <package>
  - Remove package:     uv remove <package>
  - Sync dependencies:  uv sync
  - Lock dependencies:  uv lock"""


# ============ Validation Functions ============

def validate_write_operation(file_path: str) -> Optional[str]:
    """
    Validate Write tool operations on dependency files.

    Args:
        file_path: Target file path

    Returns:
        Error message if invalid, None if valid

    Examples:
        >>> validate_write_operation("requirements.txt")
        "📦 Blocked: Direct editing of requirements.txt..."

        >>> validate_write_operation("src/main.py")
        None
    """
    if not is_dependency_file(file_path):
        return None

    filename = os.path.basename(file_path)
    alternatives = get_uv_alternatives(filename)

    return f"""📦 Blocked: Direct editing of {filename}

Why this is blocked:
  - Manual edits bypass UV's dependency resolution
  - Changes won't be reflected in uv.lock
  - Risk of dependency conflicts
  - No validation of version constraints
  - Breaks project reproducibility

{alternatives}

For migration from requirements.txt:
  1. Review existing requirements.txt
  2. Use: uv add <package1> <package2> ...
  3. Or manually add to pyproject.toml [project.dependencies]
  4. Run: uv lock to generate lock file
  5. Safely delete old requirements.txt after migration"""


def validate_edit_operation(file_path: str) -> Optional[str]:
    """
    Validate Edit tool operations on dependency files.

    Args:
        file_path: Target file path

    Returns:
        Error message if invalid, None if valid
    """
    # Same logic as validate_write_operation
    return validate_write_operation(file_path)


def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash commands that might modify dependency files.

    Args:
        command: Shell command to validate

    Returns:
        Error message if invalid, None if valid

    Examples:
        >>> validate_bash_command("echo 'requests' > requirements.txt")
        "📦 Blocked: Shell modification of requirements.txt..."

        >>> validate_bash_command("cat requirements.txt")
        None
    """
    # Extract file paths from command
    file_paths = extract_file_paths_from_bash(command)

    # Check if any are dependency files
    for file_path in file_paths:
        if is_dependency_file(file_path):
            filename = os.path.basename(file_path)
            alternatives = get_uv_alternatives(filename)

            return f"""📦 Blocked: Shell modification of {filename}

Command: {command}

Why this is blocked:
  - Bypasses UV dependency management
  - Won't update uv.lock
  - Risk of syntax errors
  - No validation or conflict resolution

{alternatives}"""

    return None


# ============ Main Entry Point ============

def main() -> None:
    """
    Main entry point for UV dependency blocker hook.

    Reads JSON input from stdin, validates operations, and outputs
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

        # Handle file-based tools (Write, Edit, MultiEdit)
        if tool_name in {"Write", "Edit", "MultiEdit"}:
            file_path = tool_input.get("file_path", "")
            if not file_path:
                output_decision("allow", "No file path to validate")
                return

            error = validate_write_operation(file_path)
            if error:
                output_decision("deny", error, suppress_output=True)
            else:
                output_decision("allow", "File is not a dependency file")

        # Handle Bash commands
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if not command:
                output_decision("allow", "No command to validate")
                return

            error = validate_bash_command(command)
            if error:
                output_decision("deny", error, suppress_output=True)
            else:
                output_decision("allow", "Command does not modify dependency files")

        else:
            # Other tools - allow
            output_decision("allow", f"Tool '{tool_name}' not monitored by this hook")

    except Exception as e:
        # Fail-safe: allow operation on error
        print(f"UV dependency blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
