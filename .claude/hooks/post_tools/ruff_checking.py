#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruff>=0.8.0",
# ]
# ///
"""
Ruff Checking Hook for PostToolUse
===================================

Automatically format and check Python files after Write, Edit, or NotebookEdit
operations using Ruff, providing immediate feedback to Claude about code style
issues and lint violations.

This hook ensures consistent code formatting and adherence to Python best
practices across the codebase.

Hook Event:
    PostToolUse

Tool Matchers:
    - Write: Triggers when new files are created
    - Edit: Triggers when existing files are modified
    - NotebookEdit: Triggers when notebook cells are edited

Behavior:
    1. Validates file is Python (.py, .pyi)
    2. Runs `ruff format` to fix formatting
    3. Runs `ruff check --fix` to auto-fix lint violations
    4. Provides feedback to Claude about changes made
    5. Non-blocking (does not prevent Claude from continuing)

Output:
    - Success: Feedback message with formatting/linting summary
    - No changes: Silent exit (no output)
    - Errors: Warning message with suggestions

Security:
    - Validates file paths (no traversal)
    - Checks file is within project directory
    - Uses subprocess safely (no shell=True)
    - Timeouts prevent hanging

Dependencies:
    - ruff>=0.8.0: Modern linter and formatter

Configuration:
    Add to .claude/settings.json:
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Write|Edit|NotebookEdit",
            "hooks": [
              {
                "type": "command",
                "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/ruff_checking.py",
                "timeout": 30
              }
            ]
          }
        ]
      }
    }

Example Feedback:
    ✅ Ruff: formatted + fixed 3 lint issues in example.py
    ⚠️ Ruff: 2 remaining issues in example.py (run: ruff check example.py)

Version:
    1.0.0

Author:
    Claude Code Hook Expert
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

# Import shared utilities from post_tools/utils
try:
    from utils import (
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )
except ImportError:
    # Fallback for testing or direct execution
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from utils import (  # type: ignore[reportMissingImports]
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Core Functions ====================


def main() -> None:
    """Main entry point for ruff checking hook."""
    # 1. Parse input
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # 2. Validate tool and file
    if not should_process(tool_name, tool_input, tool_response):
        output_feedback("", suppress_output=True)
        return

    file_path = get_file_path(tool_input)

    # 3. Run ruff format and check
    format_result = run_ruff_format(file_path)
    check_result = run_ruff_check(file_path)

    # 4. Generate feedback
    feedback = generate_feedback(file_path, format_result, check_result)
    output_feedback(feedback, suppress_output=True)


def should_process(
    tool_name: str,
    tool_input: ToolInput,
    tool_response: dict[str, object],
) -> bool:
    """
    Determine if file should be processed.

    Args:
        tool_name: Name of the tool that was executed
        tool_input: Tool input parameters
        tool_response: Tool execution response

    Returns:
        True if file should be formatted/checked, False otherwise

    Validation Steps:
        1. Check tool name is Write/Edit/NotebookEdit
        2. Check tool execution succeeded
        3. Validate file path exists
        4. Check file is Python (.py, .pyi)
        5. Check file is within project directory
        6. Check file exists on disk
    """
    # Check tool name
    if tool_name not in ["Write", "Edit", "NotebookEdit"]:
        return False

    # Check tool success
    if not was_tool_successful(tool_response):
        return False

    # Get and validate file path
    file_path = get_file_path(tool_input)
    if not file_path:
        return False

    # Check if Python file
    if not is_python_file(file_path):
        return False

    # Check if within project
    if not is_within_project(file_path):
        return False

    # Check if file exists
    if not Path(file_path).exists():
        return False

    return True


def run_ruff_format(file_path: str) -> dict[str, object]:
    """
    Run ruff format on file.

    Args:
        file_path: Absolute path to Python file

    Returns:
        Result dict with:
        - success: bool (True if command succeeded)
        - formatted: bool (True if file was reformatted)
        - error: Optional[str] (error message if failed)

    Process:
        1. Run `ruff format --check` to see if formatting needed
        2. If needed, run `ruff format` to actually format
        3. Return result indicating success and whether formatting was applied
    """
    try:
        # Run ruff format --check first to see if formatting needed
        check_result = subprocess.run(
            ["ruff", "format", "--check", file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        needs_formatting = check_result.returncode != 0

        if needs_formatting:
            # Actually format the file
            format_result = subprocess.run(
                ["ruff", "format", file_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return {
                "success": format_result.returncode == 0,
                "formatted": True,
                "error": format_result.stderr
                if format_result.returncode != 0
                else None,
            }

        return {"success": True, "formatted": False, "error": None}

    except subprocess.TimeoutExpired:
        return {"success": False, "formatted": False, "error": "Timeout"}
    except FileNotFoundError:
        return {"success": False, "formatted": False, "error": "Ruff not found"}
    except Exception as e:
        return {"success": False, "formatted": False, "error": str(e)}


def run_ruff_check(file_path: str) -> dict[str, object]:
    """
    Run ruff check --fix on file.

    Args:
        file_path: Absolute path to Python file

    Returns:
        Result dict with:
        - success: bool (True if command succeeded)
        - fixed_count: int (number of auto-fixed violations)
        - remaining_count: int (number of unfixed violations)
        - error: Optional[str] (error message if failed)

    Process:
        1. Run `ruff check --fix --output-format=json`
        2. Parse JSON output to count fixed and remaining violations
        3. Return result with counts and success status

    Note:
        Ruff outputs JSON array of violation objects. Each violation has
        a "fix" field if it was auto-fixed.
    """
    try:
        # Run ruff check --fix --output-format=json
        result = subprocess.run(
            ["ruff", "check", "--fix", "--output-format=json", file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse JSON output
        if result.stdout:
            violations_raw: object = json.loads(result.stdout)  # type: ignore[reportAny]
            # Type: should be a list of violation dicts
            violations: list[dict[str, object]] = cast(
                list[dict[str, object]], violations_raw
            )

            # Count fixed vs remaining violations
            fixed = sum(1 for v in violations if v.get("fix"))
            remaining = len(violations) - fixed

            return {
                "success": True,
                "fixed_count": fixed,
                "remaining_count": remaining,
                "error": None,
            }

        # No violations found
        return {"success": True, "fixed_count": 0, "remaining_count": 0, "error": None}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": "Timeout",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": "Invalid JSON",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": "Ruff not found",
        }
    except Exception as e:
        return {
            "success": False,
            "fixed_count": 0,
            "remaining_count": 0,
            "error": str(e),
        }


def generate_feedback(
    file_path: str,
    format_result: dict[str, object],
    check_result: dict[str, object],
) -> str:
    """
    Generate human-readable feedback message.

    Args:
        file_path: File that was processed
        format_result: Result from run_ruff_format()
        check_result: Result from run_ruff_check()

    Returns:
        Feedback message for Claude (empty if no changes)

    Message Format:
        - Success: "✅ Ruff: [changes] in [file]"
        - Warnings: "⚠️ Ruff: [issue] in [file] (run: ...)"
        - Multiple messages joined with " | "

    Examples:
        - "✅ Ruff: formatted in example.py"
        - "✅ Ruff: fixed 3 lint issues in example.py"
        - "✅ Ruff: formatted + fixed 2 lint issues in example.py"
        - "⚠️ Ruff: 1 remaining issue in example.py (run: ruff check ...)"
        - ""  (no changes made)
    """
    file_name = Path(file_path).name
    messages: list[str] = []

    # Check for errors
    if not format_result.get("success"):
        error = format_result.get("error", "Unknown error")
        messages.append(f"⚠️ Ruff format error in {file_name}: {error}")

    if not check_result.get("success"):
        error = check_result.get("error", "Unknown error")
        messages.append(f"⚠️ Ruff check error in {file_name}: {error}")

    # Report changes
    formatted_val = format_result.get("formatted", False)
    formatted = bool(formatted_val) if formatted_val is not None else False

    fixed_count_val = check_result.get("fixed_count", 0)
    fixed_count = int(fixed_count_val) if isinstance(fixed_count_val, (int, str, float)) else 0

    remaining_count_val = check_result.get("remaining_count", 0)
    remaining_count = int(remaining_count_val) if isinstance(remaining_count_val, (int, str, float)) else 0

    if formatted or fixed_count > 0:
        parts: list[str] = []
        if formatted:
            parts.append("formatted")
        if fixed_count > 0:
            parts.append(
                f"fixed {fixed_count} lint issue{'s' if fixed_count != 1 else ''}"
            )

        messages.append(f"✅ Ruff: {' + '.join(parts)} in {file_name}")

    # Warn about remaining issues
    if remaining_count > 0:
        messages.append(
            f"⚠️ Ruff: {remaining_count} remaining issue{'s' if remaining_count != 1 else ''} "
            f"in {file_name} (run: ruff check {file_path})"
        )

    return " | ".join(messages) if messages else ""


# ==================== Entry Point ====================


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log unexpected errors to stderr but don't block
        print(f"Ruff hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
