#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Temporary Directory Creation Blocker - PreToolUse Hook
========================================================
Prevents file creation in system temp directories for better observability.
"""

import os

try:
    from .utils.data_types import ToolInput
except ImportError:
    from utils.data_types import ToolInput


TEMP_DIRECTORIES = [
    "/tmp/",
    "/var/tmp/",
]


def check_path_is_temp_directory(file_path: str) -> bool:
    """Check if a file path is within a system temporary directory."""
    for temp_dir in TEMP_DIRECTORIES:
        if file_path.startswith(temp_dir):
            return True
    return False


def validate_file_creation(tool_name: str, tool_input: ToolInput) -> str | None:
    """Validate file creation operation against temp directory policy."""
    if tool_name in ("Write", "NotebookEdit"):
        file_path = tool_input.get("file_path", "")
        if file_path and check_path_is_temp_directory(file_path):
            alternative = suggest_alternative_path(file_path)
            return f"""🚫 Blocked file creation in system temp directory.
Path: {file_path}
Policy: Never create files in system temp paths for better observability.
Alternative: Use project directory instead:
  - Create: {alternative}
  - Then add 'temp/' to .gitignore if needed"""
    return None


def suggest_alternative_path(blocked_path: str) -> str:
    """Generate a project-local alternative path for a blocked temp file."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    filename = os.path.basename(blocked_path)
    alternative = os.path.join(project_dir, "temp", filename)
    return alternative


def main() -> None:
    """Main entry point for the tmp_creation_blocker hook."""
    import json
    import sys
    from typing import cast

    input_text = sys.stdin.read()
    parsed_json = cast(dict[str, object], json.loads(input_text))
    tool_input = cast(dict[str, str], parsed_json.get("tool_input", {}))
    file_path = str(tool_input.get("file_path", ""))

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Blocked: {file_path}"
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
