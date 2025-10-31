#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Context Bundle Builder - Claude Code Hook (JSONL version)
Tracks files accessed (Read/Write) and user prompts during a Claude Code session
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import cast


def handle_file_operations(input_data: dict[str, object]) -> None:
    """Handle Read/Write tool operations."""
    # Extract relevant data with proper type casting
    session_id_obj = input_data.get("session_id", "unknown")
    session_id = str(session_id_obj) if isinstance(session_id_obj, str) else "unknown"

    tool_name_obj = input_data.get("tool_name", "")
    tool_name = str(tool_name_obj) if isinstance(tool_name_obj, str) else ""

    tool_input_obj = input_data.get("tool_input", {})
    tool_response_obj = input_data.get("tool_response", {})

    # Validate tool_input and tool_response are dicts
    if not isinstance(tool_input_obj, dict):
        sys.exit(0)
    tool_input = cast(dict[str, object], tool_input_obj)

    if not isinstance(tool_response_obj, dict):
        tool_response: dict[str, object] = {}
    else:
        tool_response = cast(dict[str, object], tool_response_obj)

    # Only process Read and Write tools
    if tool_name not in ["Read", "Write"]:
        sys.exit(0)

    # Extract file path
    file_path_obj = tool_input.get("file_path")
    if not isinstance(file_path_obj, str) or not file_path_obj:
        sys.exit(0)
    file_path = file_path_obj

    # Check if Write operation was successful
    if tool_name == "Write" and tool_response:
        success_obj = tool_response.get("success", True)
        success = bool(success_obj) if success_obj is not None else True
        if not success:
            sys.exit(0)

    # Convert to relative path and create log entry
    file_path_relative = _convert_to_relative_path(file_path)
    log_entry = _create_file_operation_log_entry(
        tool_name, file_path_relative, tool_input
    )

    # Write to JSONL file
    write_log_entry(session_id, log_entry)


def handle_user_prompt(input_data: dict[str, object]) -> None:
    """Handle UserPromptSubmit events."""
    # Extract relevant data with proper type casting
    session_id_obj = input_data.get("session_id", "unknown")
    session_id = str(session_id_obj) if isinstance(session_id_obj, str) else "unknown"

    prompt_obj = input_data.get("prompt", "")
    if not isinstance(prompt_obj, str) or not prompt_obj:
        sys.exit(0)
    prompt = prompt_obj

    # Create minimal log entry for prompt
    log_entry: dict[str, object] = {
        "operation": "prompt",
        "prompt": prompt[:500],  # Limit prompt length to avoid huge logs
    }

    # Write to JSONL file
    write_log_entry(session_id, log_entry)


def write_log_entry(session_id: str, log_entry: dict[str, object]) -> None:
    """Write a log entry to the JSONL file."""
    # Generate filename with correct format: YYYY-MM-DD-DAY-HH-MM-SS-session_id.jsonl
    now = datetime.now()
    date_part = now.strftime("%Y-%m-%d")  # "2025-10-31"
    day_part = now.strftime("%a").upper()  # "FRI"
    time_part = now.strftime("%H-%M-%S")  # "14-30-45"
    filename = f"{date_part}-{day_part}-{time_part}-{session_id}.jsonl"

    # Create directory structure
    bundle_dir = Path("agents/context_bundles")
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Use JSONL file (JSON Lines format)
    bundle_file = bundle_dir / filename

    # Append to JSONL file (atomic operation for small writes)
    try:
        with open(bundle_file, "a") as f:
            # Write as a single line of JSON
            f.write(json.dumps(log_entry) + "\n")
    except IOError as e:
        print(f"Error appending to context bundle: {e}", file=sys.stderr)
        sys.exit(1)


def _convert_to_relative_path(file_path: str) -> str:
    """Convert absolute path to relative path."""
    try:
        # Use CLAUDE_PROJECT_DIR if available, otherwise use cwd
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        abs_path = Path(file_path).resolve()
        project_path = Path(project_dir).resolve()

        # Try to make path relative to project directory
        try:
            relative_path = abs_path.relative_to(project_path)
            return str(relative_path)
        except ValueError:
            # If file is outside project directory, keep absolute path
            return file_path
    except OSError as e:
        # Log path resolution errors
        print(f"Warning: Path resolution failed for {file_path}: {e}", file=sys.stderr)
        return file_path


def _create_file_operation_log_entry(
    tool_name: str, file_path_relative: str, tool_input: dict[str, object]
) -> dict[str, object]:
    """Create log entry for file operations."""
    # Create the log entry
    log_entry: dict[str, object] = {
        "operation": tool_name.lower(),  # "read" or "write"
        "file_path": file_path_relative,
    }

    # Add tool_input parameters (excluding file_path since we already have it)
    tool_input_filtered: dict[str, object] = {}
    if tool_name == "Read":
        if "limit" in tool_input:
            limit_val = tool_input["limit"]
            if isinstance(limit_val, int):
                tool_input_filtered["limit"] = limit_val
        if "offset" in tool_input:
            offset_val = tool_input["offset"]
            if isinstance(offset_val, int):
                tool_input_filtered["offset"] = offset_val
    elif tool_name == "Write":
        # For Write, track content length but not the content itself
        if "content" in tool_input:
            content_obj = tool_input.get("content", "")
            if isinstance(content_obj, str):
                tool_input_filtered["content_length"] = len(content_obj)

    # Only add tool_input if there are parameters to save
    if tool_input_filtered:
        log_entry["tool_input"] = tool_input_filtered

    return log_entry


def main() -> None:
    """Main entry point with argument parsing."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Context Bundle Builder")
    parser.add_argument(
        "--type",
        choices=["file_ops", "user_prompt"],
        default="file_ops",
        help="Type of operation to handle",
    )
    args = parser.parse_args()

    try:
        # Read hook input from stdin - json.load returns Any, cast immediately
        input_data_raw: object = cast(object, json.load(sys.stdin))
        if not isinstance(input_data_raw, dict):
            print("Error: Input is not a JSON object", file=sys.stderr)
            sys.exit(1)
        input_data = cast(dict[str, object], input_data_raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Route to appropriate handler
    operation_type: str = str(getattr(args, "type", "file_ops"))
    if operation_type == "file_ops":
        handle_file_operations(input_data)
    elif operation_type == "user_prompt":
        handle_user_prompt(input_data)

    # Success - exit silently
    sys.exit(0)


if __name__ == "__main__":
    main()
