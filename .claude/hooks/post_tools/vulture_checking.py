#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "vulture>=2.14",
# ]
# ///
"""
Vulture Checking Hook for PostToolUse
======================================

Automatically detect dead code (unused functions, classes, variables, imports,
and attributes) in Python files after Write or Edit operations using Vulture,
providing immediate feedback to Claude about potential dead code.

This hook helps maintain clean, efficient codebases by identifying code that
can be safely removed.

Hook Event:
    PostToolUse

Tool Matchers:
    - Write: Triggers when new files are created
    - Edit: Triggers when existing files are modified
    - NotebookEdit: Triggers when notebook cells are edited

Behavior:
    1. Validates file is Python (.py, .pyi)
    2. Runs `vulture` with JSON output to detect dead code
    3. Filters by confidence threshold (min: 80)
    4. Skips test files (test_*.py, *_test.py, conftest.py)
    5. Provides feedback to Claude about high-confidence findings
    6. Non-blocking (does not prevent Claude from continuing)

Output:
    - Success: Feedback message with dead code summary
    - No findings: Silent exit (no output)
    - Errors: Non-blocking, logged to stderr

Security:
    - Validates file paths (no traversal)
    - Checks file is within project directory
    - Uses subprocess safely (no shell=True)
    - Timeouts prevent hanging

Dependencies:
    - vulture>=2.14: Dead code detection with JSON output

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
                "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/vulture_checking.py",
                "timeout": 15
              }
            ]
          }
        ]
      }
    }

Example Feedback:
    ⚠️ Vulture: Found 3 unused items in example.py (function 'unused_func' at line 5, import 'os' at line 1, variable 'unused_var' at line 10)

Version:
    1.0.0

Author:
    Claude Code Hook Expert
"""

import re
import subprocess
import sys
from pathlib import Path

# Import shared utilities from post_tools/utils
try:
    from utils import (
        ToolInput,
        get_file_path,
        get_project_dir,
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
        get_project_dir,
        is_python_file,
        is_within_project,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Constants ====================

MIN_CONFIDENCE = 80
MAX_ITEMS_TO_SHOW = 3


# ==================== Core Functions ====================


def main() -> None:
    """Main entry point for vulture checking hook."""
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

    # 3. Run vulture scan
    findings = run_vulture_scan(file_path)

    # 4. Generate feedback
    feedback = generate_feedback(file_path, findings)

    # Show output if findings exist, suppress if clean
    suppress = len(findings) == 0
    output_feedback(feedback, suppress_output=suppress)


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
        True if file should be scanned for dead code, False otherwise

    Validation Steps:
        1. Check tool name is Write/Edit/NotebookEdit
        2. Check tool execution succeeded
        3. Validate file path exists
        4. Check file is Python (.py, .pyi)
        5. Check file is within project directory
        6. Check file exists on disk
        7. Skip test files (avoid false positives)
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

    # Skip test files (tests often have intentional unused code)
    if is_test_file(file_path):
        return False

    return True


def is_test_file(file_path: str) -> bool:
    """
    Check if file is a test file.

    Test files often have intentional unused code (fixtures, helpers)
    and should be skipped from dead code detection.

    Args:
        file_path: File path to check

    Returns:
        True if file appears to be a test file

    Patterns:
        - test_*.py
        - *_test.py
        - conftest.py
        - tests/ directory
        - test/ directory
    """
    path = Path(file_path)
    file_name = path.name

    # Check file name patterns
    if file_name.startswith("test_") or file_name.endswith("_test.py"):
        return True
    if file_name == "conftest.py":
        return True

    # Check if in tests directory
    parts = path.parts
    if "tests" in parts or "test" in parts:
        return True

    return False


def run_vulture_scan(file_path: str) -> list[dict[str, object]]:
    """
    Run vulture scan on file with text output parsing.

    Args:
        file_path: Absolute path to Python file

    Returns:
        List of findings (each finding is a dict with: file, line, message, confidence)
        Empty list if no findings or on error

    Implementation:
        - Runs: vulture <file_path> --min-confidence 80
        - Uses project's min_confidence setting from pyproject.toml
        - Parses text output for structured findings
        - Filters by confidence threshold
        - Returns only high-confidence findings

    Output Format (text):
        file.py:5: unused function 'func_name' (60% confidence)
        file.py:1: unused import 'os' (90% confidence)
    """
    try:
        # Get project directory to find pyproject.toml
        project_dir = get_project_dir()

        # Run vulture with text output
        # Note: vulture reads min_confidence from pyproject.toml if available
        result = subprocess.run(
            ["vulture", file_path, "--min-confidence", str(MIN_CONFIDENCE)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_dir),  # Run from project root to use pyproject.toml
        )

        # Exit code 0 = no dead code found
        # Exit code 1 = invalid arguments
        # Exit code 3 = dead code found
        if result.returncode == 0:
            return []  # No dead code found

        if result.returncode == 1:
            # Invalid arguments
            print(f"Vulture error (invalid args): {result.stderr}", file=sys.stderr)
            return []

        if result.returncode > 3:
            # Unexpected error
            print(f"Vulture error: {result.stderr}", file=sys.stderr)
            return []

        # Vulture outputs to stdout when it finds issues
        # Parse text output from stdout
        if result.stdout:
            findings: list[dict[str, object]] = []

            # Vulture text format: file.py:5: unused function 'func' (60% confidence)
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse line using regex
                # Format: <file>:<line>: <message> (<confidence>% confidence[, N lines])
                match = re.match(
                    r"^(.+?):(\d+):\s+(.+?)\s+\((\d+)%\s+confidence(?:,\s+\d+\s+lines?)?\)$",
                    line.strip(),
                )

                if match:
                    file_str, line_str, message, conf_str = match.groups()
                    confidence = int(conf_str)

                    # Only include findings meeting confidence threshold
                    if confidence >= MIN_CONFIDENCE:
                        findings.append(
                            {
                                "file": file_str,
                                "line": int(line_str),
                                "message": message,
                                "confidence": confidence,
                            }
                        )

            return findings

        return []

    except subprocess.TimeoutExpired:
        print("Vulture scan timeout", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Vulture not found (install: uv pip install vulture)", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Vulture scan error: {e}", file=sys.stderr)
        return []


def generate_feedback(
    file_path: str,
    findings: list[dict[str, object]],
) -> str:
    """
    Generate human-readable feedback message.

    Args:
        file_path: File that was scanned
        findings: List of dead code findings from vulture

    Returns:
        Feedback message for Claude (empty if no findings)

    Format:
        "⚠️ Vulture: Found N unused items in file.py (item1 at line X, item2 at line Y)"

    Examples:
        - Single finding: "⚠️ Vulture: Found 1 unused item in example.py (function 'unused_func' at line 5)"
        - Multiple findings: "⚠️ Vulture: Found 3 unused items in example.py (function 'unused_func' at line 5, import 'os' at line 1, variable 'unused_var' at line 10)"
        - Many findings: "⚠️ Vulture: Found 10 unused items in example.py (function 'unused_func' at line 5, ...7 more)"
    """
    if not findings:
        return ""

    file_name = Path(file_path).name
    count = len(findings)

    # Extract item descriptions
    items: list[str] = []

    for finding in findings[:MAX_ITEMS_TO_SHOW]:
        message = finding.get("message", "unknown")
        line = finding.get("line", 0)

        # Extract item name from message
        item_desc = extract_item_name(str(message))
        items.append(f"{item_desc} at line {line}")

    # Format item list
    if count <= MAX_ITEMS_TO_SHOW:
        item_list = ", ".join(items)
    else:
        remaining = count - MAX_ITEMS_TO_SHOW
        item_list = ", ".join(items) + f", ...{remaining} more"

    # Pluralize "item" if needed
    item_word = "item" if count == 1 else "items"

    return f"⚠️ Vulture: Found {count} unused {item_word} in {file_name} ({item_list})"


def extract_item_name(message: str) -> str:
    """
    Extract item name from vulture message.

    Args:
        message: Vulture message like "unused function 'foo'" or "unused variable 'bar'"

    Returns:
        Extracted item description with type and name

    Examples:
        "unused function 'foo'" → "function 'foo'"
        "unused variable 'bar'" → "variable 'bar'"
        "unused import 'os'" → "import 'os'"
        "unused attribute 'baz'" → "attribute 'baz'"
    """
    # Try to extract quoted name
    match = re.search(r"'([^']+)'", message)

    if match:
        item_name = match.group(1)

        # Extract item type (function, variable, import, etc.)
        message_lower = message.lower()
        if "function" in message_lower:
            return f"function '{item_name}'"
        elif "variable" in message_lower:
            return f"variable '{item_name}'"
        elif "import" in message_lower:
            return f"import '{item_name}'"
        elif "attribute" in message_lower:
            return f"attribute '{item_name}'"
        elif "class" in message_lower:
            return f"class '{item_name}'"
        else:
            return item_name

    # Fallback: return cleaned message
    return message.replace("unused ", "").strip()


# ==================== Entry Point ====================


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log unexpected errors to stderr but don't block
        print(f"Vulture hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
