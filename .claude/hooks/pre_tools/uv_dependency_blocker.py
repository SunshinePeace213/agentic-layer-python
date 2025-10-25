#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""UV Dependency Blocker - PreToolUse Hook"""

from pathlib import Path

try:
    from .utils.utils import parse_hook_input, output_decision, get_file_path
    from .utils.data_types import ToolInput
except ImportError:
    from utils.utils import parse_hook_input, output_decision, get_file_path
    from utils.data_types import ToolInput


def validate_dependency_file_edit(tool_input: ToolInput) -> str | None:
    """
    Validate that dependency files are not being directly edited.

    Args:
        tool_input: Tool input parameters containing file_path

    Returns:
        Violation message if found, None otherwise
    """
    file_path = get_file_path(tool_input)
    if not file_path:
        return None

    # Check if this is a protected dependency file
    is_protected, file_type = is_protected_dependency_file(file_path)

    if is_protected and file_type:
        # Get the filename for the message
        filename = Path(file_path).name
        return generate_violation_message(file_type, filename)

    return None


def is_protected_dependency_file(file_path: str) -> tuple[bool, str | None]:
    """
    Check if a file path represents a protected dependency file.

    Args:
        file_path: Path to check

    Returns:
        (is_protected, file_type) - tuple indicating protection status and file type
    """
    path = Path(file_path).resolve()
    filename = path.name.lower()

    # Check for template/example files (allowed)
    if any(ext in filename for ext in [".sample", ".example", ".template", ".dist"]):
        return (False, None)

    # Check against protected filenames
    protected_files = {
        "requirements.txt": "requirements file",
        "pyproject.toml": "project configuration",
        "uv.lock": "UV lock file",
        "pipfile": "Pipfile configuration",
        "pipfile.lock": "Pipfile lock file",
    }

    # Check for exact matches
    if filename in protected_files:
        return (True, protected_files[filename])

    # Check for requirements variants (requirements-dev.txt, requirements-test.txt, etc.)
    if filename.startswith("requirements") and filename.endswith(".txt"):
        return (True, "requirements file")

    return (False, None)


def generate_violation_message(file_type: str, file_name: str) -> str:
    """
    Generate helpful violation message with UV command alternatives.

    Args:
        file_type: Type of protected file
        file_name: Name of the file being edited

    Returns:
        Formatted violation message
    """
    messages = {
        "requirements file": f"""🚫 Cannot edit {file_name} directly.

Use UV commands instead:
  • Add dependency: uv add <package>
  • Remove dependency: uv remove <package>
  • Install all: uv sync

Direct edits bypass dependency resolution and may cause version conflicts.""",
        "project configuration": f"""🚫 Cannot edit {file_name} directly.

Use UV commands instead:
  • Add dependency: uv add <package>
  • Add dev dependency: uv add --dev <package>
  • Remove dependency: uv remove <package>

UV manages dependencies in pyproject.toml automatically.""",
        "UV lock file": f"""🚫 Cannot edit {file_name} - this file is auto-generated.

The lock file is automatically updated by UV commands:
  • uv add <package>
  • uv remove <package>
  • uv sync

Manual edits will be overwritten and may corrupt the lock state.""",
        "Pipfile configuration": f"""🚫 Cannot edit {file_name} directly.

Consider migrating to modern UV workflow:
  • UV uses pyproject.toml (industry standard)
  • Faster dependency resolution
  • Better compatibility

Or use: pipenv install/uninstall for Pipfile management""",
        "Pipfile lock file": f"""🚫 Cannot edit {file_name} - this file is auto-generated.

Consider migrating to modern UV workflow:
  • UV uses pyproject.toml (industry standard)
  • Faster dependency resolution
  • Better compatibility

Or use: pipenv install/uninstall for Pipfile management""",
    }

    return messages.get(
        file_type,
        f"🚫 Cannot edit {file_name} directly. Use UV commands for dependency management.",
    )


def main() -> None:
    """Main entry point for the UV dependency blocker hook."""
    # Parse input using shared utility
    parsed = parse_hook_input()
    if not parsed:
        return  # Error already handled by utility

    tool_name, tool_input = parsed

    # Only validate file edit tools
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        output_decision("allow", "Not a file edit tool")
        return

    # Validate the file path
    violation = validate_dependency_file_edit(tool_input)

    if violation:
        # Deny operation with helpful message
        output_decision("deny", violation, suppress_output=True)
    else:
        # Allow operation
        output_decision("allow", "Not a protected dependency file")


if __name__ == "__main__":
    main()
