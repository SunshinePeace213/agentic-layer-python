#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Workflow Enforcer - PreToolUse Hook
=======================================
Enforces uv-based Python workflow by blocking direct python/pip usage.

This hook ensures all Python script execution uses 'uv run' and all
package installations use 'uv add' for better performance and consistency.

Blocked Patterns:
- python script.py / python3 script.py
- pip install package / pip3 install package
- python -m pip install package

Allowed Patterns:
- uv run script.py
- uv add package
- python -c "code" (one-liners)
- shell queries (which python, etc.)

Usage:
    This hook is automatically invoked by Claude Code before Bash execution.
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

import re
import sys
from typing import Optional, Tuple

# Import shared utilities
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision


# ============ Pattern Definitions ============

PYTHON_SCRIPT_PATTERN: re.Pattern[str] = re.compile(
    r'\b(?:python3?|/usr/bin/python3?)\s+(?!-[cm]\b).*?[\w\./\-]+\.py\b',
    re.IGNORECASE
)

PIP_INSTALL_PATTERN: re.Pattern[str] = re.compile(
    r'\b(?:pip3?|python3?\s+-m\s+pip)\s+install\b',
    re.IGNORECASE
)


# ============ Detection Functions ============

def detect_python_script_execution(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect direct python/python3 script execution.

    Args:
        command: The bash command to analyze

    Returns:
        Tuple of (violation_type, message) if detected, None otherwise

    Examples:
        >>> detect_python_script_execution("python script.py")
        ("direct_python_execution", "...")
        >>> detect_python_script_execution("uv run script.py")
        None
    """
    if PYTHON_SCRIPT_PATTERN.search(command):
        return (
            "direct_python_execution",
            f"""🐍 UV Workflow Required: Direct python execution blocked

Use uv for better performance and dependency management.

Your command: {command}

Recommended alternative:
  uv run <script>.py [args]

Why use uv run:
  - Automatically manages virtual environments
  - Respects inline script dependencies (PEP 723)
  - Faster execution with optimized caching
  - Consistent environment across all executions

Examples:
  uv run script.py --arg value
  uv run --no-project script.py  # Skip project deps
  uv run --with requests script.py  # Add runtime dep

Note: python -c and python -m are still allowed for quick commands."""
        )
    return None


def detect_pip_install(command: str) -> Optional[Tuple[str, str]]:
    """
    Detect pip install commands.

    Args:
        command: The bash command to analyze

    Returns:
        Tuple of (violation_type, message) if detected, None otherwise

    Examples:
        >>> detect_pip_install("pip install requests")
        ("pip_install_blocked", "...")
        >>> detect_pip_install("uv add requests")
        None
    """
    if PIP_INSTALL_PATTERN.search(command):
        return (
            "pip_install_blocked",
            f"""📦 UV Package Management Required: pip install blocked

Use uv for better performance and consistent dependency tracking.

Your command: {command}

Recommended alternatives:
  uv add <package>              # Add production dependency
  uv add --dev <package>        # Add development dependency
  uv add "package>=1.0,<2.0"    # With version constraints

Why use uv add:
  - 10-100x faster than pip install
  - Automatically updates pyproject.toml
  - Creates/updates uv.lock for reproducibility
  - Better dependency resolution
  - Unified project management

For requirements.txt migration:
  1. Review requirements.txt
  2. Use: uv add <package1> <package2> <package3>
  3. Or manually add to pyproject.toml dependencies"""
        )
    return None


def should_allow_command(command: str) -> bool:
    """
    Check if command should be allowed despite containing 'python' keyword.

    Allowed patterns:
    - python -c "code"  # One-liner
    - python -m module  # Module execution (context-dependent)
    - which python      # Shell queries
    - echo "python"     # String literals
    - type python       # Shell introspection
    - uv run python script.py  # UV-managed execution

    Args:
        command: The bash command to analyze

    Returns:
        True if command should be allowed, False otherwise

    Examples:
        >>> should_allow_command('python -c "print(1)"')
        True
        >>> should_allow_command("which python")
        True
        >>> should_allow_command("uv run python script.py")
        True
        >>> should_allow_command("python script.py")
        False
    """
    # Check for uv run (which manages the execution)
    if re.search(r'\buv\s+run\b', command):
        return True

    # Check for one-liners
    if re.search(r'\bpython3?\s+-c\s+', command):
        return True

    # Check for shell queries
    if re.search(r'\b(which|type|command\s+-v)\s+python3?\b', command):
        return True

    # Check for echo/printf (not execution)
    if re.search(r'\b(echo|printf)\s+.*python', command):
        return True

    return False


def validate_command(command: str) -> Optional[Tuple[str, str]]:
    """
    Validate command against all patterns.

    Args:
        command: The bash command to analyze

    Returns:
        Tuple of (violation_type, message) if violation detected, None otherwise

    Examples:
        >>> validate_command("python script.py")
        ("direct_python_execution", "...")
        >>> validate_command("uv run script.py")
        None
    """
    # Check edge cases first (allow patterns)
    if should_allow_command(command):
        return None

    # Check for direct python script execution
    violation = detect_python_script_execution(command)
    if violation:
        return violation

    # Check for pip install
    violation = detect_pip_install(command)
    if violation:
        return violation

    return None


def main() -> None:
    """Main entry point for UV workflow enforcer hook."""
    try:
        # Parse hook input
        parsed = parse_hook_input()
        if not parsed:
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = parsed

        # Only process Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Not a Bash command")
            return

        # Get command from tool input
        command = tool_input.get("command", "")
        if not command:
            output_decision("allow", "No command provided")
            return

        # Validate command
        violation = validate_command(command)

        if violation:
            _, message = violation
            output_decision("deny", message, suppress_output=True)
        else:
            output_decision("allow", "Command follows UV workflow")

    except Exception as e:
        # Fail-safe: allow on any error to not break Claude operations
        print(f"UV workflow enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
