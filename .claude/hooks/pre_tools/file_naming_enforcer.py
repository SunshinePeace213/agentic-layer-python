#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
File Naming Convention Enforcer Hook
=====================================

Prevents creation of files with poor naming conventions during Claude Code
development operations. Enforces professional file naming standards by blocking
temporary-style naming patterns, version suffixes, and non-standard conventions.

Purpose:
    Enforce professional naming, promote Git usage, maintain clean projects,
    and follow language conventions. Provides educational feedback with better
    alternatives.

Hook Event: PreToolUse
Monitored Tools: Write, Edit, Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with Git alternatives
    - Zero external dependencies

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Blocked Patterns:
    - Backup extensions: .backup, .bak, .old, .orig
    - Version suffixes: _v2, _v3, file_v2.py
    - Iteration suffixes: _final, _fixed, _update, _new, _copy
    - Number suffixes: file2.py, script_2.py (except semantic)
    - Test/temp markers: _test, _tmp outside proper directories
    - Python-specific: kebab-case, camelCase for .py files

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


# ==================== Configuration ====================

# Standard files that are always allowed
ALLOWLIST_FILES = {
    "readme.md",
    "license",
    "changelog.md",
    "setup.py",
    "pyproject.toml",
    "requirements.txt",
    "makefile",
    "dockerfile",
    ".gitignore",
    "__init__.py",
    "__main__.py",
    "conftest.py",
    ".env.example",
    ".env.local",
    ".env.test",
    "config.yaml",
    "settings.json",
    ".prettierrc",
    ".eslintrc",
    "tsconfig.json",
}

# Blocked file extensions
BLOCKED_EXTENSIONS = {".backup", ".bak", ".old", ".orig", ".swp", ".swo"}

# Iteration suffix patterns
ITERATION_SUFFIXES = [
    "final",
    "fixed",
    "fix",
    "update",
    "updated",
    "new",
    "latest",
    "copy",
    "backup",
    "old",
    "obsolete",
    "modified",
    "mod",
    "revised",
    "rev",
    "corrected",
]

# Semantic number patterns (allowed)
SEMANTIC_PATTERNS = [
    r"\bpython[23]",
    r"\bhttp2?",
    r"\bbase64",
    r"\d{4}[_-]\d{2}[_-]\d{2}",  # Date format
]


# ==================== Validation Functions ====================


def is_allowlisted(file_path: str) -> bool:
    """Check if file is in the allowlist."""
    filename = Path(file_path).name.lower()
    return filename in ALLOWLIST_FILES


def has_blocked_extension(file_path: str) -> bool:
    """Check if file has blocked extension."""
    path = Path(file_path)

    # Check for ~ suffix (editor backups)
    if path.name.endswith("~"):
        return True

    # Check extensions (case-insensitive)
    ext_lower = path.suffix.lower()
    return ext_lower in BLOCKED_EXTENSIONS


def has_version_suffix(file_path: str) -> bool:
    """Check if filename has version suffix."""
    stem = Path(file_path).stem
    pattern = r"(?i)[_-]?v(ersion)?[_-]?\d+(?:[_.-]\d+)*$"
    return bool(re.search(pattern, stem))


def has_iteration_suffix(file_path: str) -> bool:
    """Check if filename has iteration suffix."""
    stem = Path(file_path).stem
    pattern = r"(?i)[_-](" + "|".join(ITERATION_SUFFIXES) + r")$"
    return bool(re.search(pattern, stem))


def has_number_suffix(file_path: str) -> bool:
    """Check if filename has meaningless number suffix."""
    stem = Path(file_path).stem

    # Check semantic exceptions first (don't block these)
    for pattern in SEMANTIC_PATTERNS:
        if re.search(pattern, stem, re.I):
            return False

    # Check for trailing numbers
    pattern = r"[_-]?\d+$"
    return bool(re.search(pattern, stem))


def is_test_temp_in_wrong_location(file_path: str) -> bool:
    """Check if test/temp marker is outside proper directories."""
    stem = Path(file_path).stem.lower()

    # Check if file has test/temp suffix
    if not re.search(r"[_-](test|tmp|temp)$", stem, re.I):
        return False

    # Check if in proper directory
    path_lower = file_path.lower()
    proper_dirs = ["tests/", "test/", "__tests__/", "tmp/", "temp/", ".tmp/"]

    return not any(proper_dir in path_lower for proper_dir in proper_dirs)


def has_invalid_python_naming(file_path: str) -> bool:
    """Check if .py file follows Python naming conventions."""
    if not file_path.endswith(".py"):
        return False

    filename = Path(file_path).name

    # Allowlist special Python files
    special_files = {"__init__.py", "__main__.py", "setup.py", "conftest.py"}
    if filename in special_files:
        return False

    stem = Path(file_path).stem

    # Valid patterns
    snake_case = r"^[a-z][a-z0-9_]*$"
    pascal_case = r"^[A-Z][a-zA-Z0-9]*$"

    if re.match(snake_case, stem) or re.match(pascal_case, stem):
        return False

    return True  # Invalid naming


# ==================== Bash Command Parsing ====================


def extract_file_paths_from_bash(command: str) -> list[str]:
    """Extract file paths from bash command."""
    paths: list[str] = []

    # Redirect operators: >, >>, 2>, &>
    redirect_pattern = r"[12&]?>>?\s+([^\s;|&]+)"
    paths.extend(re.findall(redirect_pattern, command))

    # Touch command
    touch_pattern = r"\btouch\s+(.*?)(?:;|&&|\||$)"
    touch_matches: list[str] = re.findall(touch_pattern, command)
    for match in touch_matches:
        # Split on whitespace to get individual files
        file_parts: list[str] = match.split()
        paths.extend(file_parts)

    # Copy/move destination
    cp_mv_pattern = r"\b(?:cp|mv)\s+\S+\s+(\S+)"
    paths.extend(re.findall(cp_mv_pattern, command))

    # Clean up quotes
    return [p.strip('"\'') for p in paths]


# ==================== Error Messages ====================


def create_error_message(violation_type: str, file_path: str) -> str:
    """Create detailed error message with Git alternatives."""
    messages = {
        "backup_extension": f"""📝 Blocked: Backup file extension detected

File: {file_path}

Why this is blocked:
  - Backup files clutter project directories
  - Cannot be tracked properly by git
  - Unclear which version is current
  - Violates professional project organization

Use Git instead:
  # Stash your changes
  git stash save "temporary backup of {Path(file_path).name}"

  # Or create a branch
  git checkout -b backup/changes
  git add {Path(file_path).name}
  git commit -m "backup: save current state"

Recommended alternatives:
  - Use git stash for temporary saves
  - Create feature branches for experiments
  - Use git tags for stable versions

Learn more: https://git-scm.com/docs/git-stash""",
        "version_suffix": f"""📝 Blocked: Version suffix detected in filename

File: {file_path}

Why this is blocked:
  - Multiple versions coexist, causing confusion
  - Unclear which version is current
  - Cannot track version history properly
  - Violates semantic versioning practices

Use Git instead:
  # Use branches for new versions
  git checkout -b feature/v2
  # Make changes to the original file
  git commit -m "feat: add v2 implementation"

  # Use tags for releases
  git tag v2.0.0
  git push origin v2.0.0

Recommended alternatives:
  - Keep single file: {Path(file_path).stem.split('_v')[0]}{Path(file_path).suffix}
  - Use git branches: feature/v2
  - Use git tags: v2.0.0, v2.1.0
  - Document versions in CHANGELOG.md

Learn more: https://semver.org/""",
        "iteration_suffix": f"""📝 Blocked: Iteration suffix detected in filename

File: {file_path}

Why this is blocked:
  - Unclear what "final" or "fixed" actually means
  - Accumulates multiple versions of same file
  - Violates version control best practices
  - Makes project directory cluttered

Use Git instead:
  # Make changes and commit with descriptive message
  git add {Path(file_path).name}
  git commit -m "fix: correct validation logic"

  # Or create a feature branch
  git checkout -b fix/improvements
  git add {Path(file_path).name}
  git commit -m "refactor: improve implementation"

Recommended alternatives:
  - Use descriptive git commit messages
  - Create feature branches for changes
  - Use git reflog to track iterations
  - Trust version control history

Learn more: https://git-scm.com/docs/git-commit""",
        "number_suffix": f"""📝 Blocked: Meaningless number suffix detected

File: {file_path}

Why this is blocked:
  - Numbers provide no semantic meaning
  - Hard to maintain and understand
  - Indicates poor organization
  - Should use descriptive names or git

Use Git instead:
  # Use descriptive names
  {Path(file_path).stem.rstrip('0123456789_-')}_<descriptive_name>{Path(file_path).suffix}

  # Or use git branches
  git checkout -b feature/iteration-2
  # Make changes to original file

Recommended alternatives:
  - Use descriptive names: user_handler.py, api_client.py
  - Use git branches: feature/v2, experiment/approach-2
  - Use git tags for versions: v2.0.0
  - Add semantic suffixes: parser_async.py, client_v2_compatible.py

Learn more: https://git-scm.com/docs/git-branch""",
        "test_temp_wrong_location": f"""📝 Blocked: Test/temp file in wrong location

File: {file_path}

Why this is blocked:
  - Test files should be in tests/ directory
  - Temp files should be in tmp/ or temp/ directory
  - Violates project organization standards
  - Confuses production code with test code

Move to proper location:
  # For test files:
  tests/{Path(file_path).name}
  tests/test_{Path(file_path).name}

  # For temp files:
  tmp/{Path(file_path).name}
  temp/{Path(file_path).name}

Recommended alternatives:
  - Move test files to tests/ directory
  - Move temp files to tmp/ directory
  - Use .gitignore for temp directories
  - Follow standard project structure

Learn more: https://docs.pytest.org/en/stable/""",
        "python_naming": f"""🐍 Blocked: Invalid Python module naming

File: {file_path}

Why this is blocked:
  - Hyphens in filenames incompatible with Python imports
  - Cannot import: 'import {Path(file_path).stem}' (syntax error)
  - Violates PEP 8 module naming conventions
  - Inconsistent with Python community standards

Use proper Python naming:
  # snake_case (preferred)
  {Path(file_path).stem.replace('-', '_')}.py

  # PascalCase (for single-class modules)
  {''.join(word.capitalize() for word in Path(file_path).stem.replace('-', '_').split('_'))}.py

Recommended alternatives:
  - Use snake_case: user_handler.py, api_client.py
  - Use PascalCase: UserHandler.py, ApiClient.py
  - Avoid hyphens, camelCase, and mixed case

Learn more: https://peps.python.org/pep-0008/#package-and-module-names""",
    }

    return messages.get(violation_type, f"File naming violation: {file_path}")


# ==================== Main Validation Logic ====================


def validate_file_path(file_path: str) -> Optional[str]:
    """
    Validate a single file path against all naming rules.

    Returns:
        None if valid, error message string if invalid
    """
    # Check allowlist first
    if is_allowlisted(file_path):
        return None

    # Check blocked extensions
    if has_blocked_extension(file_path):
        return create_error_message("backup_extension", file_path)

    # Check version suffixes
    if has_version_suffix(file_path):
        return create_error_message("version_suffix", file_path)

    # Check iteration suffixes
    if has_iteration_suffix(file_path):
        return create_error_message("iteration_suffix", file_path)

    # Check number suffixes
    if has_number_suffix(file_path):
        return create_error_message("number_suffix", file_path)

    # Check test/temp in wrong location
    if is_test_temp_in_wrong_location(file_path):
        return create_error_message("test_temp_wrong_location", file_path)

    # Check Python naming conventions
    if has_invalid_python_naming(file_path):
        return create_error_message("python_naming", file_path)

    return None


def validate_write_tool(file_path: str) -> Optional[str]:
    """Validate Write tool operation."""
    return validate_file_path(file_path)


def validate_edit_tool(file_path: str) -> Optional[str]:
    """Validate Edit tool operation."""
    return validate_file_path(file_path)


def validate_bash_tool(command: str) -> Optional[str]:
    """Validate Bash tool operation."""
    # Extract file paths from command
    file_paths = extract_file_paths_from_bash(command)

    # Validate each extracted file path
    for file_path in file_paths:
        error = validate_file_path(file_path)
        if error:
            return error

    return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and parameters
        3. Validate based on tool type (Write, Edit, or Bash)
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

        # Determine validation based on tool type
        error_message: Optional[str] = None

        if tool_name == "Write":
            # Write tool: validate file path
            file_path = tool_input.get("file_path", "")
            if file_path:
                error_message = validate_write_tool(file_path)

        elif tool_name == "Edit":
            # Edit tool: validate file path
            file_path = tool_input.get("file_path", "")
            if file_path:
                error_message = validate_edit_tool(file_path)

        elif tool_name == "Bash":
            # Bash tool: parse command and validate file paths
            command = tool_input.get("command", "")
            if command:
                error_message = validate_bash_tool(command)

        # Output decision
        if error_message:
            # Validation failed: deny with educational message
            output_decision("deny", error_message, suppress_output=False)
        else:
            # Validation passed: allow
            output_decision(
                "allow",
                "File naming conventions validated",
                suppress_output=True,
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"File naming enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
