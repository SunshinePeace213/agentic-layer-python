#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Workflow Enforcer Hook
==========================

Enforces UV-based Python workflow by preventing direct execution of `pip`,
`python`, and `python3` commands. Ensures consistent, high-performance package
management and script execution across all Claude Code operations.

Purpose:
    Block direct pip/python/python3 command execution to:
    - Maintain UV's lock file consistency
    - Leverage UV's automatic environment management
    - Ensure reproducibility across team members
    - Utilize UV's performance optimizations

Hook Event: PreToolUse
Monitored Tools: Bash

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with specific UV command alternatives

Dependencies:
    - Python 3.12+
    - Standard library only
    - Shared utilities from .claude/hooks/pre_tools/utils

Author: Claude Code Hook Expert
Version: 2.0.0
Last Updated: 2025-10-30
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Command Pattern Definitions ====================

# Allow-list patterns: Commands that already use UV or are informational
ALLOWED_PATTERNS = [
    r'\buv\s+run\s+python\b',       # uv run python script.py
    r'\buv\s+run\s+python3\b',      # uv run python3 script.py
    r'\buv\s+pip\s+',                # uv pip install
    r'\buv\s+tool\s+run\s+',         # uv tool run
    r'head.*\.py.*#!.*python',       # Shebang checks (read-only)
    r'grep.*"#!.*python"',           # Shebang searches (read-only)
    r'\bpython3?\s+(?:--help|-h)\b', # Help commands (informational)
]

# Block patterns: Direct pip usage
PIP_PATTERNS = [
    (r'\bpip\s+\w+', "pip"),                    # pip install, pip uninstall, etc.
    (r'\bpip3\s+\w+', "pip"),                   # pip3 install
    (r'\bpython3?\s+-m\s+pip\b', "pip"),        # python -m pip install
]

# Block patterns: Direct python usage
PYTHON_PATTERNS = [
    (r'\bpython\s+[^\s-].*\.py\b', "python"),   # python script.py
    (r'\bpython3\s+[^\s-].*\.py\b', "python3"), # python3 script.py
    (r'\bpython\s+-m\s+\w+', "python"),         # python -m module
    (r'\bpython3\s+-m\s+\w+', "python3"),       # python3 -m module
    (r'\bpython\s+-c\s+', "python"),            # python -c "code"
    (r'\bpython3\s+-c\s+', "python3"),          # python3 -c "code"
    (r'\bpython\s*$', "python"),                # python (REPL)
    (r'\bpython3\s*$', "python3"),              # python3 (REPL)
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
        >>> parse_command_segments("cd dir && python script.py")
        ['cd dir', 'python script.py']
        >>> parse_command_segments("pip install pkg1 pkg2")
        ['pip install pkg1 pkg2']
        >>> parse_command_segments("echo test | python -")
        ['echo test', 'python -']
    """
    if not command:
        return []

    # Split on common command separators
    # Simple approach using regex to handle most common cases
    segments = re.split(r'\s*(?:&&|\|\||;|\|)\s*', command)

    return [seg.strip() for seg in segments if seg.strip()]


def is_allowed_command(command_segment: str) -> bool:
    """
    Check if command segment matches allow-list patterns.

    Args:
        command_segment: Single command to check

    Returns:
        True if command is allowed (uses UV or is informational)

    Examples:
        >>> is_allowed_command("uv run python script.py")
        True
        >>> is_allowed_command("uv pip install requests")
        True
        >>> is_allowed_command("python --help")
        True
        >>> is_allowed_command("python script.py")
        False
    """
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command_segment):
            return True
    return False


def detect_blocked_command(command_segment: str) -> tuple[bool, str, str]:
    """
    Detect if command uses blocked pip/python/python3 patterns.

    Args:
        command_segment: Single command to check

    Returns:
        Tuple of (is_blocked, command_type, detected_command)
        - is_blocked: True if command should be denied
        - command_type: "pip", "python", "python3", or ""
        - detected_command: The specific command that was detected

    Examples:
        >>> detect_blocked_command("pip install requests")
        (True, 'pip', 'pip install')
        >>> detect_blocked_command("python script.py")
        (True, 'python', 'python script.py')
        >>> detect_blocked_command("uv run python script.py")
        (False, '', '')
    """
    # First check allow-list (early return for UV commands)
    if is_allowed_command(command_segment):
        return (False, "", "")

    # Check pip patterns
    for pattern, cmd_type in PIP_PATTERNS:
        match = re.search(pattern, command_segment)
        if match:
            return (True, cmd_type, match.group())

    # Check python patterns
    for pattern, cmd_type in PYTHON_PATTERNS:
        match = re.search(pattern, command_segment)
        if match:
            return (True, cmd_type, match.group())

    return (False, "", "")


# ==================== Message Generation Functions ====================


def get_pip_denial_message(command: str) -> str:
    """
    Generate denial message for blocked pip commands.

    Args:
        command: Original command that was blocked

    Returns:
        Formatted error message with UV alternatives
    """
    return f"""🚫 Blocked: Direct pip usage bypasses UV dependency management

Command: {command}

Why this is blocked:
  - Bypasses UV's lock file (uv.lock)
  - Breaks reproducibility for your team
  - Misses UV's parallel installation optimizations
  - Installs into wrong environment
  - Creates dependency drift over time

Use UV instead:

  For project dependencies:
    uv add requests              # Add to project + update lock file
    uv add --dev pytest          # Add dev dependency
    uv add 'requests>=2.28'      # Add with version constraint

  For one-off installations:
    uv pip install requests      # Use UV's pip interface
    uv tool install ruff         # Install CLI tools

  To sync environment:
    uv sync                      # Install from lock file
    uv sync --all-extras         # Include all optional dependencies

Learn more: https://docs.astral.sh/uv/concepts/dependencies/"""


def get_python_denial_message(command: str, python_cmd: str) -> str:
    """
    Generate denial message for blocked python/python3 commands.

    Args:
        command: Original command that was blocked
        python_cmd: Type of python command ("python" or "python3")

    Returns:
        Formatted error message with UV alternatives
    """
    return f"""🚫 Blocked: Direct {python_cmd} execution bypasses UV environment management

Command: {command}

Why this is blocked:
  - Uses system Python instead of project-specified version
  - Misses dependencies from UV's managed environment
  - Doesn't respect requires-python constraints
  - Breaks isolation between projects
  - Inconsistent behavior across team members

Use UV instead:

  For script execution:
    uv run script.py --arg value # Run with UV-managed environment
    uv run --python 3.12 main.py # Use specific Python version
    uv run --no-project main.py  # Run without project dependencies

  For module execution:
    uv run -m pytest tests/      # Run Python modules
    uv run -m http.server 8000   # Run standard library modules

  For inline code:
    uv run - <<EOF
    print('hello from UV')
    EOF

  For REPL:
    uv run python                # Start Python REPL with UV environment

Learn more: https://docs.astral.sh/uv/guides/scripts/"""


def get_deny_message(command: str, command_type: str, _detected_command: str) -> str:
    """
    Generate appropriate denial message based on command type.

    Args:
        command: Full original command
        command_type: Type of blocked command ("pip", "python", "python3")
        _detected_command: Specific command pattern detected (reserved for future use)

    Returns:
        Formatted error message with UV command alternatives
    """
    if command_type == "pip":
        return get_pip_denial_message(command)
    elif command_type in ("python", "python3"):
        return get_python_denial_message(command, command_type)
    else:
        return f"Blocked: {command}"


# ==================== Validation Functions ====================


def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for pip/python/python3 usage.

    Args:
        command: Bash command to validate

    Returns:
        None if validation passes, error message string if validation fails
    """
    if not command:
        return None

    try:
        # Parse command into segments
        segments = parse_command_segments(command)

        # Check each segment
        for segment in segments:
            is_blocked, cmd_type, detected = detect_blocked_command(segment)

            if is_blocked:
                return get_deny_message(command, cmd_type, detected)

    except re.error:
        # Regex error: fail-safe, allow
        return None
    except Exception:
        # Any other parsing error: fail-safe, allow
        return None

    return None


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and command
        3. Validate bash commands for pip/python/python3 usage
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
            output_decision("allow", "Command uses UV workflow or no blocked patterns detected")

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"UV workflow enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
