#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
UV Workflow Enforcer - PreToolUse Hook
========================================

Enforces the use of UV for all Python-related commands during development,
providing educational guidance and command alternatives.

REFACTORED: Uses shared utilities from utils/ to reduce code duplication.
"""

import re
import sys
from typing import Optional, Pattern, Tuple

# Import shared utilities for input parsing and output formatting
try:
    from .utils import parse_hook_input, output_decision
except ImportError:
    from utils import parse_hook_input, output_decision

# Compiled regex patterns for performance
PYTHON_INTERPRETER: Pattern[str] = re.compile(r'\b(python3?(\.\d+)?)\s+')
PIP_COMMAND: Pattern[str] = re.compile(r'\bpip3?\s+(install|uninstall|list|freeze|show)')
UV_COMMAND: Pattern[str] = re.compile(r'\buv\s+(run|add|remove|sync|lock|pip)')
SYSTEM_INFO: Pattern[str] = re.compile(r'\b(python3?|pip3?)\s+(--version|-V|--help|-h)\b')
SHEBANG_CHECK: Pattern[str] = re.compile(r'(head|cat|grep).*python')
STRING_CONTEXT: Pattern[str] = re.compile(r'(echo|printf|git\s+commit).*["\'].*python.*["\']')
WHICH_PYTHON: Pattern[str] = re.compile(r'\bwhich\s+python')


def is_fallback_case(command: str) -> bool:
    """Check if command is a legitimate fallback case."""
    return bool(
        UV_COMMAND.search(command) or
        SYSTEM_INFO.search(command) or
        SHEBANG_CHECK.search(command) or
        STRING_CONTEXT.search(command) or
        WHICH_PYTHON.search(command)
    )


def detect_python_command(command: str) -> Optional[Tuple[str, str]]:
    """Detect Python interpreter invocations and suggest UV."""
    match = PYTHON_INTERPRETER.search(command)
    if not match:
        return None
    
    python_cmd = match.group(1)
    suggestion = command.replace(python_cmd, "uv run", 1)
    return (command, suggestion)


def detect_pip_command(command: str) -> Optional[Tuple[str, str, str]]:
    """Detect pip commands and suggest UV equivalents."""
    match = PIP_COMMAND.search(command)
    if not match:
        return None
    
    subcommand = match.group(1)
    
    if subcommand == "install":
        if "-r requirements.txt" in command or "-r " in command:
            suggestion = "uv sync"
            msg_type = "pip_requirements"
        elif "-e ." in command:
            suggestion = command.replace("pip", "uv pip", 1)
            msg_type = "fallback"
        else:
            pkg_match = re.search(r'install\s+([a-zA-Z0-9_\-]+)', command)
            if pkg_match:
                package = pkg_match.group(1)
                suggestion = f"uv add {package}"
            else:
                suggestion = "uv add <package>"
            msg_type = "pip_install"
    
    elif subcommand == "uninstall":
        pkg_match = re.search(r'uninstall\s+([a-zA-Z0-9_\-]+)', command)
        if pkg_match:
            package = pkg_match.group(1)
            suggestion = f"uv remove {package}"
        else:
            suggestion = "uv remove <package>"
        msg_type = "pip_install"
    
    else:
        suggestion = command.replace("pip", "uv pip", 1)
        msg_type = "fallback"
    
    return (command, suggestion, msg_type)


def detect_uv_violation(command: str) -> Optional[Tuple[str, str, str]]:
    """Detect UV workflow violations."""
    pip_result = detect_pip_command(command)
    if pip_result:
        detected, suggested, msg_type = pip_result
        return (detected, suggested, msg_type)
    
    python_result = detect_python_command(command)
    if python_result:
        detected, suggested = python_result
        return (detected, suggested, "python")
    
    return None


def generate_educational_message(detected_cmd: str, suggested_cmd: str, message_type: str) -> str:
    """Generate educational message with UV alternatives."""
    display_cmd = detected_cmd if len(detected_cmd) <= 60 else detected_cmd[:57] + "..."
    
    if message_type == "python":
        return f"""🚫 Use UV to run Python scripts

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Benefits:
• ✅ Runs in project's virtual environment automatically
• ✅ Ensures dependencies are installed
• ✅ Supports inline script metadata
• ✅ Works with any Python version

Common UV commands:
  uv run <script>                # Run script
  uv run --python 3.12 <script>  # Specific Python version
  uv run python -m <module>      # Run module

Learn more: https://docs.astral.sh/uv/guides/scripts/"""
    
    elif message_type == "pip_install":
        return f"""🚫 Use UV instead of pip for package management

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Why UV?
• ⚡ 10-100x faster dependency resolution
• 🔒 Automatic lock file management
• 📦 Virtual environment handling built-in
• 🎯 Works with pyproject.toml (modern Python standard)

Common UV commands:
  uv add <package>        # Add dependency
  uv add --dev <package>  # Add dev dependency
  uv remove <package>     # Remove dependency
  uv sync                 # Install all dependencies
  uv lock                 # Update lock file

Learn more: https://docs.astral.sh/uv/"""
    
    elif message_type == "pip_requirements":
        return f"""🚫 Use UV sync instead of pip install -r

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Why uv sync?
• 📋 Installs dependencies from pyproject.toml + uv.lock
• 🔐 Ensures exact versions from lock file
• 🎯 Creates/updates venv automatically
• ⚡ Much faster than pip

Migration path:
1. Convert requirements.txt to pyproject.toml
2. Or use: uv pip install -r requirements.txt (fallback)
3. Long-term: Move to pyproject.toml for modern Python packaging

Learn more: https://docs.astral.sh/uv/guides/projects/"""
    
    elif message_type == "fallback":
        return f"""ℹ️ Consider using UV for this operation

Command detected: {display_cmd}
UV suggestion:    {suggested_cmd}

This operation may work, but UV provides better alternatives.
The suggested command uses 'uv pip' as a fallback.

Prefer native UV commands when possible:
  uv add <package>     # Instead of pip install
  uv remove <package>  # Instead of pip uninstall
  uv sync              # Instead of pip install -r requirements.txt

Learn more: https://docs.astral.sh/uv/"""
    
    return f"""🚫 Use UV for Python workflow

Command detected: {display_cmd}
UV equivalent:    {suggested_cmd}

Learn more: https://docs.astral.sh/uv/"""


def main() -> None:
    """Main entry point for UV workflow enforcer hook."""
    try:
        # Parse input using shared utility
        parsed = parse_hook_input()
        if not parsed:
            # Error already handled by parse_hook_input
            output_decision("allow", "Failed to parse input (fail-safe)")
            return
        
        tool_name, tool_input = parsed
        
        # Only validate Bash commands
        if tool_name != "Bash":
            output_decision("allow", "Not a Bash command")
            return
        
        # Extract command from tool input
        command = tool_input.get("command", "")
        
        if not command:
            output_decision("allow", "No command to validate")
            return
        
        # Check for fallback cases first
        if is_fallback_case(command):
            output_decision("allow", "Legitimate UV fallback or system command")
            return
        
        # Detect UV violations
        violation = detect_uv_violation(command)
        
        if violation:
            detected_cmd, suggested_cmd, msg_type = violation
            message = generate_educational_message(detected_cmd, suggested_cmd, msg_type)
            output_decision("deny", message, suppress_output=True)
        else:
            output_decision("allow", "Command follows UV workflow")
    
    except Exception as e:
        # Fail-safe: allow operation on any error
        print(f"UV workflow enforcer error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}")


if __name__ == "__main__":
    main()
