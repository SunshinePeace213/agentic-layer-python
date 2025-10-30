#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Dependency Blocker Hook
===========================

Prevents direct editing of Python dependency files to enforce the use of UV commands
for dependency management during development.

Purpose:
    Block direct edits to dependency files (uv.lock, pyproject.toml, requirements.txt, etc.)
    to ensure consistency, reproducibility, and proper dependency tracking through UV's
    advanced dependency resolution and lock file management.

Hook Event: PreToolUse
Monitored Tools: Write, Edit

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with UV command alternatives

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-30
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Constants ====================

# Python dependency file patterns
DEPENDENCY_FILE_PATTERNS = {
    "uv.lock": "uv.lock",
    "pyproject.toml": "pyproject.toml",
    "pipfile": "Pipfile",
    "pipfile.lock": "Pipfile.lock",
}


# ==================== Dependency File Detection ====================


def is_dependency_file(file_path: str) -> tuple[bool, str]:
    """
    Check if file path is a Python dependency file.

    Args:
        file_path: Path to check (can be absolute or relative)

    Returns:
        Tuple of (is_dependency_file, file_type)
        - is_dependency_file: True if it's a dependency file
        - file_type: One of "uv.lock", "pyproject.toml", "requirements.txt",
                     "Pipfile", "Pipfile.lock", or ""

    Examples:
        >>> is_dependency_file("/project/uv.lock")
        (True, "uv.lock")
        >>> is_dependency_file("./requirements-dev.txt")
        (True, "requirements.txt")
        >>> is_dependency_file("/project/src/main.py")
        (False, "")
    """
    if not file_path:
        return (False, "")

    # Extract basename for pattern matching
    filename = os.path.basename(file_path).lower()

    # Check exact matches (case-insensitive)
    if filename in DEPENDENCY_FILE_PATTERNS:
        return (True, DEPENDENCY_FILE_PATTERNS[filename])

    # requirements.txt variants (case-insensitive)
    # Pattern: requirements*.txt catches all variants
    if filename.startswith("requirements") and filename.endswith(".txt"):
        return (True, "requirements.txt")

    return (False, "")


# ==================== Error Messages ====================


def get_deny_message(file_type: str, file_path: str) -> str:
    """
    Generate appropriate denial message based on file type.

    Args:
        file_type: Type of dependency file
        file_path: Full path to the file

    Returns:
        Formatted error message with UV command alternatives
    """
    messages = {
        "uv.lock": f"""🔒 Blocked: Direct editing of UV lock file

File: {file_path}

UV lock files are automatically generated and should never be edited manually.

To update the lock file:
  uv lock                    # Regenerate lock file from dependencies
  uv lock --upgrade          # Upgrade all dependencies to latest compatible versions
  uv lock --upgrade-package <pkg>  # Upgrade specific package

To add dependencies:
  uv add <package>           # Add to dependencies and update lock
  uv add --dev <package>     # Add to dev dependencies

To remove dependencies:
  uv remove <package>        # Remove and update lock

Learn more: https://docs.astral.sh/uv/concepts/dependencies/""",

        "pyproject.toml": f"""📦 Blocked: Direct editing of pyproject.toml

File: {file_path}

Direct edits bypass UV's dependency management. Use UV commands for consistency.

Common operations:
  uv add <package>           # Add dependency
  uv add --dev <package>     # Add dev dependency
  uv add --optional <group> <package>  # Add to optional group
  uv remove <package>        # Remove dependency
  uv lock                    # Update lock file after changes

For non-dependency edits (metadata, tool config):
  - Temporarily disable this hook if needed
  - Use uv init for initial project setup

Learn more: https://docs.astral.sh/uv/concepts/dependencies/""",

        "requirements.txt": f"""📋 Blocked: Direct editing of requirements file

File: {file_path}

Direct edits to requirements.txt bypass UV's dependency resolution.

Migrate to modern UV workflow:
  uv add <package>           # Add dependency (updates pyproject.toml + uv.lock)
  uv remove <package>        # Remove dependency
  uv sync                    # Sync environment from lock file

If you must use requirements.txt:
  uv pip install <package>   # Install and update requirements.txt
  uv pip compile requirements.in -o requirements.txt  # Compile from .in file

Consider migrating to pyproject.toml for better dependency management.

Learn more: https://docs.astral.sh/uv/pip/compile/""",

        "Pipfile": f"""🔧 Blocked: Direct editing of Pipfile

File: {file_path}

Pipfile/Pipfile.lock should be managed by pipenv or migrated to UV.

If using Pipenv:
  pipenv install <package>   # Add dependency
  pipenv install --dev <package>  # Add dev dependency
  pipenv uninstall <package> # Remove dependency

Consider migrating to UV for better performance:
  # Export current dependencies
  pipenv requirements > requirements.txt

  # Migrate to UV
  uv init
  uv add $(cat requirements.txt | grep -v '^#' | grep -v '^-e')

Learn more: https://docs.astral.sh/uv/guides/projects/""",

        "Pipfile.lock": f"""🔧 Blocked: Direct editing of Pipfile.lock

File: {file_path}

Pipfile.lock is automatically generated by pipenv and should never be edited manually.

To update the lock file:
  pipenv lock                # Regenerate lock file
  pipenv update              # Update dependencies and lock file
  pipenv update <package>    # Update specific package

Consider migrating to UV for better performance:
  pipenv requirements > requirements.txt
  uv init && uv add $(cat requirements.txt | grep -v '^#')

Learn more: https://docs.astral.sh/uv/guides/projects/""",
    }

    return messages.get(file_type, "")


# ==================== Validation Functions ====================


def validate_file_operation(file_path: str) -> Optional[str]:
    """
    Validate that file operation is not targeting a dependency file.

    Args:
        file_path: Path to validate

    Returns:
        None if validation passes, error message string if validation fails
    """
    if not file_path:
        return None

    is_dep_file, file_type = is_dependency_file(file_path)

    if is_dep_file:
        return get_deny_message(file_type, file_path)

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
        # Parse input from stdin
        result = parse_hook_input()
        if result is None:
            # Parse failed, fail-safe: allow
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = result

        # Only validate Write and Edit tools
        if tool_name not in ("Write", "Edit"):
            output_decision("allow", "Tool does not modify files")
            return

        # Extract file path
        file_path = tool_input.get("file_path", "")

        # Validate file operation
        error_message = validate_file_operation(file_path)

        # Output decision
        if error_message:
            # Validation failed: deny with helpful message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # Validation passed: allow
            output_decision("allow", "Not a Python dependency file")

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"UV dependency blocker error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
