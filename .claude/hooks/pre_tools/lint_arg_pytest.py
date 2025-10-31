#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Pytest Argument Linting Hook
==============================

Enforces standardized pytest execution patterns in Claude Code by validating that
pytest commands include performance-optimizing and coverage-tracking arguments.

Purpose:
    Ensure consistent, high-performance test execution by requiring:
    - pytest-xdist for parallel execution (-n auto)
    - pytest-cov for coverage tracking (--cov)

Hook Event: PreToolUse
Monitored Tools: Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with specific corrected command examples

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-31
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Command Pattern Definitions ====================

# Allow-list patterns: Commands that don't need optimization arguments
ALLOWED_PYTEST_PATTERNS = [
    # Help/version commands (informational only)
    r"\bpytest\s+(?:--help|-h)\b",
    r"\bpytest\s+(?:--version|-V)\b",
    # Collection-only (no execution)
    r"\bpytest\s+--collect-only",
    r"\bpytest\s+--co\b",
    # Cache/fixture info (no execution)
    r"\bpytest\s+--cache-show",
    r"\bpytest\s+--fixtures",
    r"\bpytest\s+--markers",
]

# Required argument patterns
XDIST_PATTERNS = [
    r"-n\s+(?:auto|\d+)",  # -n auto or -n 4
    r"--numprocesses=(?:auto|\d+)",  # --numprocesses=auto
]

COV_PATTERNS = [
    r"--cov(?:=[\w./]+)?",  # --cov or --cov=. or --cov=src
]


# ==================== Command Parsing Functions ====================


def parse_command_segments(command: str) -> list[str]:
    """
    Split command into segments for independent validation.

    Handles command separators: ;, &&, ||, |

    Args:
        command: Full bash command string

    Returns:
        List of command segments to validate independently

    Examples:
        >>> parse_command_segments("cd dir && pytest tests/")
        ['cd dir', 'pytest tests/']
        >>> parse_command_segments("pytest tests/unit && pytest tests/integration")
        ['pytest tests/unit', 'pytest tests/integration']
    """
    if not command:
        return []

    # Split on common command separators
    segments = re.split(r"\s*(?:&&|\|\||;|\|)\s*", command)

    return [seg.strip() for seg in segments if seg.strip()]


def contains_pytest_command(command_segment: str) -> bool:
    """
    Check if command segment contains a pytest invocation.

    Args:
        command_segment: Single command to check

    Returns:
        True if command contains pytest, False otherwise

    Examples:
        >>> contains_pytest_command("pytest tests/")
        True
        >>> contains_pytest_command("uv run pytest tests/")
        True
        >>> contains_pytest_command("python -m pytest tests/")
        True
        >>> contains_pytest_command("ls tests/")
        False
    """
    pytest_patterns = [
        r"\bpytest\b",
        r"\bpython3?\s+-m\s+pytest\b",
    ]

    for pattern in pytest_patterns:
        if re.search(pattern, command_segment):
            return True

    return False


def is_allowed_pytest_command(command_segment: str) -> bool:
    """
    Check if pytest command is allowed without additional validation.

    Args:
        command_segment: Single command to check

    Returns:
        True if command is informational or already optimized

    Examples:
        >>> is_allowed_pytest_command("pytest --help")
        True
        >>> is_allowed_pytest_command("pytest --version")
        True
        >>> is_allowed_pytest_command("pytest --collect-only")
        True
        >>> is_allowed_pytest_command("pytest tests/")
        False
    """
    for pattern in ALLOWED_PYTEST_PATTERNS:
        if re.search(pattern, command_segment):
            return True

    return False


def check_required_arguments(command_segment: str) -> tuple[bool, bool]:
    """
    Check if pytest command has required arguments.

    Args:
        command_segment: Pytest command to validate

    Returns:
        Tuple of (has_xdist, has_cov)
        - has_xdist: True if -n auto or similar is present
        - has_cov: True if --cov is present

    Examples:
        >>> check_required_arguments("pytest -n auto --cov=. tests/")
        (True, True)
        >>> check_required_arguments("pytest -n auto tests/")
        (True, False)
        >>> check_required_arguments("pytest --cov=. tests/")
        (False, True)
        >>> check_required_arguments("pytest tests/")
        (False, False)
    """
    # Check for parallel execution argument
    has_xdist = any(re.search(p, command_segment) for p in XDIST_PATTERNS)

    # Check for coverage argument
    has_cov = any(re.search(p, command_segment) for p in COV_PATTERNS)

    return (has_xdist, has_cov)


# ==================== Message Generation Functions ====================


def get_missing_both_message(command: str) -> str:
    """
    Generate denial message for pytest missing both required arguments.

    Args:
        command: Original command that was blocked

    Returns:
        Formatted error message with recommendations
    """
    return f"""🚫 Blocked: Pytest command missing performance optimization arguments

Command: {command}

Why this is blocked:
  - Missing parallel execution (-n auto) wastes CPU resources
  - Missing coverage tracking (--cov) provides no quality metrics
  - Sequential execution is significantly slower in CI/CD
  - No coverage data means quality regressions go unnoticed
  - Inconsistent with project testing standards

Required Arguments:

  Parallel Execution (pytest-xdist):
    -n auto                      # Use all available CPU cores
    -n 4                         # Use specific number of cores
    --numprocesses=auto          # Long-form alternative

  Coverage Tracking (pytest-cov):
    --cov=.                      # Track coverage for current directory
    --cov=src                    # Track coverage for specific directory
    --cov-report=term            # Add terminal coverage report
    --cov-report=html            # Generate HTML coverage report

Recommended Command:

  pytest -n auto --cov=. tests/
  pytest -n auto --cov=. --cov-report=term tests/
  pytest -n auto --cov=src --cov-report=html tests/

With UV (recommended):

  uv run pytest -n auto --cov=. tests/

Learn more:
  - pytest-xdist: https://pytest-xdist.readthedocs.io/
  - pytest-cov: https://pytest-cov.readthedocs.io/"""


def get_missing_xdist_message(command: str) -> str:
    """
    Generate denial message for pytest missing parallel execution argument.

    Args:
        command: Original command that was blocked

    Returns:
        Formatted error message with recommendations
    """
    return f"""🚫 Blocked: Pytest command missing parallel execution argument

Command: {command}

Why this is blocked:
  - Sequential test execution wastes available CPU cores
  - Significantly slower than parallel execution
  - CI/CD pipelines take longer than necessary
  - pytest-xdist is configured but not being utilized
  - Inconsistent with project performance standards

Add Parallel Execution:

  -n auto                      # Use all available CPU cores (recommended)
  -n 4                         # Use specific number of cores
  --numprocesses=auto          # Long-form alternative

Recommended Command:

  pytest -n auto --cov=. tests/
  uv run pytest -n auto --cov=. tests/

Learn more: https://pytest-xdist.readthedocs.io/"""


def get_missing_cov_message(command: str) -> str:
    """
    Generate denial message for pytest missing coverage tracking argument.

    Args:
        command: Original command that was blocked

    Returns:
        Formatted error message with recommendations
    """
    return f"""🚫 Blocked: Pytest command missing coverage tracking argument

Command: {command}

Why this is blocked:
  - No coverage metrics means code quality is unmeasured
  - Quality regressions and untested code go unnoticed
  - pytest-cov is configured but not being utilized
  - Missing valuable feedback on test effectiveness
  - Inconsistent with project quality standards

Add Coverage Tracking:

  --cov=.                      # Track coverage for current directory
  --cov=src                    # Track coverage for specific directory
  --cov-report=term            # Add terminal coverage report
  --cov-report=html            # Generate HTML coverage report
  --cov-report=term --cov-report=html  # Multiple report formats

Recommended Command:

  pytest -n auto --cov=. tests/
  pytest -n auto --cov=. --cov-report=term tests/
  uv run pytest -n auto --cov=. tests/

Learn more: https://pytest-cov.readthedocs.io/"""


def get_deny_message(command: str, has_xdist: bool, has_cov: bool) -> str:
    """
    Generate appropriate denial message based on missing arguments.

    Args:
        command: Full original command
        has_xdist: Whether parallel execution argument is present
        has_cov: Whether coverage argument is present

    Returns:
        Formatted error message with recommendations
    """
    if not has_xdist and not has_cov:
        return get_missing_both_message(command)
    if not has_xdist:
        return get_missing_xdist_message(command)
    if not has_cov:
        return get_missing_cov_message(command)
    # Should not reach here
    return ""


# ==================== Validation Functions ====================


def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for pytest argument requirements.

    Args:
        command: Bash command to validate

    Returns:
        None if validation passes, error message string if validation fails

    Examples:
        >>> validate_bash_command("pytest -n auto --cov=. tests/")
        None
        >>> validate_bash_command("pytest tests/")
        '🚫 Blocked: Pytest command missing...'
    """
    if not command:
        return None

    try:
        # Parse command into segments
        segments = parse_command_segments(command)

        # Check each segment
        for segment in segments:
            # Skip if not a pytest command
            if not contains_pytest_command(segment):
                continue

            # Allow informational commands
            if is_allowed_pytest_command(segment):
                continue

            # Check for required arguments
            has_xdist, has_cov = check_required_arguments(segment)

            # If missing any required argument, deny
            if not has_xdist or not has_cov:
                return get_deny_message(command, has_xdist, has_cov)

        # All pytest commands have required arguments
        return None

    except re.error:
        # Regex error: fail-safe, allow
        return None
    except Exception:
        # Any other parsing error: fail-safe, allow
        return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and command
        3. Validate bash commands for pytest argument requirements
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

        # Only validate Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Tool is not Bash")
            return

        # Extract command from tool input
        command = tool_input.get("command", "")

        # Validate command
        error_message = validate_bash_command(command)

        # Output decision
        if error_message:
            # Validation failed: deny with helpful message
            output_decision("deny", error_message, suppress_output=True)
        else:
            # Validation passed: allow
            output_decision(
                "allow",
                "Pytest command has required optimization arguments or not a pytest command",
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Pytest argument linter error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
