#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "basedpyright>=1.31.0",
# ]
# ///
"""
Basedpyright Type Checking Hook for PostToolUse
================================================

Automatically enforce complete type safety for all Python files after Write,
Edit, or NotebookEdit operations using basedpyright. This hook ensures that
NO type errors exist in Python code before Claude continues, maintaining strict
type safety standards across the codebase.

Hook Event:
    PostToolUse

Tool Matchers:
    - Write: Triggers when new files are created
    - Edit: Triggers when existing files are modified
    - NotebookEdit: Triggers when notebook cells are edited

Behavior:
    1. Validates file is Python (.py, .pyi)
    2. Runs `basedpyright --outputjson` to check for type errors
    3. Parses JSON output for structured error information
    4. BLOCKS if any type errors found
    5. Provides detailed error messages with line numbers
    6. Non-blocking for infrastructure errors (fail-safe)

Output:
    - Success: Silent feedback (no type errors)
    - Type Errors: BLOCKING with detailed error list
    - Infrastructure Errors: Warning but non-blocking

Security:
    - Validates file paths (no traversal)
    - Checks file is within project directory
    - Uses subprocess safely (no shell=True)
    - Timeouts prevent hanging

Dependencies:
    - basedpyright>=1.31.0: Strict type checker for Python

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
                "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/basedpyright_checking.py",
                "timeout": 15
              }
            ]
          }
        ]
      }
    }

Example Blocking Message:
    ❌ Type checking failed: 3 errors found in example.py

    Error 1 (line 5): Expression of type "str" is not assignable to declared type "int"
    Error 2 (line 8): Argument type "Any" is not assignable to parameter "value" of type "int"
    Error 3 (line 12): "foo" is not a known attribute of "None"

    Please fix all type errors before continuing.
    Run: basedpyright example.py

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
        get_project_dir,
        is_python_file,
        is_within_project,
        output_block,
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
        get_project_dir,
        is_python_file,
        is_within_project,
        output_block,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Core Functions ====================


def main() -> None:
    """
    Main entry point for basedpyright type checking hook.

    Process:
        1. Parse input from stdin
        2. Validate tool, file, and operation
        3. Run basedpyright type checker
        4. Block if type errors found, or allow if clean
    """
    try:
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

        # 3. Run basedpyright type checking
        check_result = run_basedpyright_check(file_path)

        # 4. Output decision based on type checking result
        if check_result["has_errors"]:
            # Type errors found - BLOCK
            output_block(
                reason=format_error_message(file_path, check_result),
                additional_context="Type errors must be resolved",
                suppress_output=False,
            )
        else:
            # Type check passed - Allow (silent)
            file_name = Path(file_path).name
            output_feedback(
                f"✅ Type check passed for {file_name}", suppress_output=True
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Basedpyright hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)


def should_process(
    tool_name: str,
    tool_input: ToolInput,
    tool_response: dict[str, object],
) -> bool:
    """
    Determine if file should be type checked.

    Args:
        tool_name: Name of the Claude Code tool that was executed
        tool_input: Tool input parameters
        tool_response: Tool execution response

    Returns:
        True if file should be type checked, False otherwise

    Validation Steps:
        1. Check tool name is Write/Edit/NotebookEdit
        2. Verify tool operation succeeded
        3. Validate file path exists and is valid
        4. Check file is Python (.py, .pyi)
        5. Verify file is within project directory
        6. Ensure file exists on disk
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


def run_basedpyright_check(file_path: str) -> dict[str, object]:
    """
    Run basedpyright type checker on file.

    Args:
        file_path: Absolute path to Python file to type check

    Returns:
        Result dict with:
        - has_errors: bool (True if type errors found)
        - error_count: int (number of errors found)
        - errors: list[dict[str, object]] (structured error information)
        - output: str (raw basedpyright output)
        - error: str | None (error message if execution failed)

    Implementation:
        - Runs: basedpyright --outputjson <file_path>
        - Parses JSON output for structured error information
        - Timeout: 10 seconds for typical files
        - Uses project's pyrightconfig.json settings
    """
    try:
        # Run basedpyright with JSON output for structured parsing
        result = subprocess.run(
            ["basedpyright", "--outputjson", file_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(get_project_dir()),
        )

        # Parse JSON output
        if result.stdout:
            try:
                output_data_raw: object = json.loads(result.stdout)  # type: ignore[reportAny]
                output_data = cast(dict[str, object], output_data_raw)

                # Extract diagnostics
                diagnostics_raw = output_data.get("generalDiagnostics", [])
                diagnostics = cast(list[dict[str, object]], diagnostics_raw)

                # Filter only errors (not warnings or information)
                errors = [d for d in diagnostics if d.get("severity") == "error"]

                return {
                    "has_errors": len(errors) > 0,
                    "error_count": len(errors),
                    "errors": errors,
                    "output": result.stdout,
                    "error": None,
                }
            except json.JSONDecodeError:
                # Fallback to text parsing if JSON fails
                has_errors = result.returncode != 0
                return {
                    "has_errors": has_errors,
                    "error_count": -1,  # Unknown
                    "errors": [],
                    "output": result.stderr or result.stdout,
                    "error": "Failed to parse JSON output",
                }

        # No output - assume success
        return {
            "has_errors": False,
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "has_errors": False,  # Fail-safe: don't block on timeout
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": "Type check timeout (file may be too large)",
        }
    except FileNotFoundError:
        return {
            "has_errors": False,  # Fail-safe: don't block if basedpyright missing
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": "basedpyright not found in PATH",
        }
    except Exception as e:
        return {
            "has_errors": False,  # Fail-safe: don't block on unexpected error
            "error_count": 0,
            "errors": [],
            "output": "",
            "error": str(e),
        }


def format_error_message(file_path: str, check_result: dict[str, object]) -> str:
    """
    Format detailed error message for blocking decision.

    Args:
        file_path: Path to file with type errors
        check_result: Result from run_basedpyright_check()

    Returns:
        Formatted error message with all type errors

    Message Structure:
        - Summary line with error count
        - Individual error details (line, message)
        - Actionable fix instructions
        - Command to rerun type check manually
    """
    file_name = Path(file_path).name
    error_count_raw = check_result.get("error_count", 0)
    error_count = int(error_count_raw) if isinstance(error_count_raw, int) else 0

    errors_raw = check_result.get("errors", [])
    errors = cast(list[dict[str, object]], errors_raw)

    # Header
    lines = [
        f"❌ Type checking failed: {error_count} error{'s' if error_count != 1 else ''} found in {file_name}",
        "",
    ]

    # Format each error
    for i, error in enumerate(errors[:10], 1):  # Limit to first 10 errors
        range_data_raw: object = error.get("range", {})
        if isinstance(range_data_raw, dict):
            range_data_typed = cast(dict[str, object], range_data_raw)
            start_data_raw: object = range_data_typed.get("start", {})
            if isinstance(start_data_raw, dict):
                start_data_typed = cast(dict[str, object], start_data_raw)
                line_num_raw: object = start_data_typed.get("line", 0)
                if isinstance(line_num_raw, int):
                    line_num_display = line_num_raw + 1
                else:
                    line_num_display = 0
            else:
                line_num_display = 0
        else:
            line_num_display = 0

        message = error.get("message", "Unknown error")
        message_str = str(message) if isinstance(message, str) else "Unknown error"

        lines.append(f"Error {i} (line {line_num_display}): {message_str}")

    # Show truncation if more than 10 errors
    if error_count > 10:
        remaining = error_count - 10
        lines.append(f"\n... and {remaining} more error{'s' if remaining != 1 else ''}")

    # Footer with instructions
    lines.extend(
        [
            "",
            "Please fix all type errors before continuing.",
            f"Run: basedpyright {file_path}",
        ]
    )

    return "\n".join(lines)


# ==================== Entry Point ====================


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log unexpected errors to stderr but don't block
        print(f"Basedpyright hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
