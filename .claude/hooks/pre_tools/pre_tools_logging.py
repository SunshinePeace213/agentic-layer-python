#!/usr/bin/env python3
"""
PreToolUse Logging Hook
========================
Logs all attempted tool operations before execution for audit and compliance.

Tracks what operations are attempted, when, and by which session,
regardless of whether they are ultimately approved or denied.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, cast


# Type definitions for JSON I/O
class ToolInput(TypedDict, total=False):
    """Tool input structure."""
    file_path: str
    content: str
    old_str: str
    new_str: str


class InputData(TypedDict):
    """Complete input data structure."""
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput


class PreToolLogEntry(TypedDict):
    """Structure for a PreToolUse log entry."""
    timestamp: str
    session_id: str
    tool_name: str
    file_path: str | None
    operation_type: str
    cwd: str


def main() -> None:
    """Main entry point for PreToolUse logging hook."""
    try:
        # Read JSON input from stdin
        input_text = sys.stdin.read()
        if not input_text:
            sys.exit(0)

        # Parse input
        try:
            input_data_raw: object = json.loads(input_text)  # type: ignore[no-any-expr]
        except json.JSONDecodeError:
            # Invalid JSON, exit cleanly
            sys.exit(0)
        
        # Type validation
        if not isinstance(input_data_raw, dict):
            sys.exit(0)

        input_dict = cast(dict[str, object], input_data_raw)
        
        # Extract required fields
        session_id = str(input_dict.get("session_id", "unknown"))
        tool_name = str(input_dict.get("tool_name", "unknown"))
        cwd = str(input_dict.get("cwd", ""))
        
        # Extract file_path from tool_input
        file_path: str | None = None
        tool_input_obj = input_dict.get("tool_input")
        if isinstance(tool_input_obj, dict):
            tool_input_dict = cast(dict[str, object], tool_input_obj)
            file_path_obj = tool_input_dict.get("file_path")
            if isinstance(file_path_obj, str):
                file_path = file_path_obj
        
        # Determine operation type based on tool_name and input
        operation_type = tool_name
        if tool_name == "Write" and tool_input_obj and isinstance(tool_input_obj, dict):
            # Check if file exists to distinguish between create and overwrite
            if file_path and Path(file_path).exists():
                operation_type = "Write (overwrite)"
            else:
                operation_type = "Write (create)"
        
        # Create log entry
        log_entry: PreToolLogEntry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "tool_name": tool_name,
            "file_path": file_path,
            "operation_type": operation_type,
            "cwd": cwd
        }
        
        # Ensure log directory exists
        if cwd:
            log_dir = Path(cwd) / "logs"
        else:
            log_dir = Path.cwd() / "logs"
            
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "pre_tool_use_logging.jsonl"
        
        # Append to JSONL file
        with open(log_path, "a", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write("\n")
        
        # Exit cleanly - don't output anything to avoid interfering with permission flow
        # The actual permission decision will be handled by other hooks or default behavior
        sys.exit(0)
        
    except Exception:
        # Exit cleanly on any error to avoid disrupting operations
        sys.exit(0)


if __name__ == "__main__":
    main()