#!/usr/bin/env python3
"""
Compliance Logging PostToolUse Hook
====================================
Logs all tool operations for compliance and audit tracking.

Maintains a JSON log file with timestamp, tool operations, 
file paths, and session information for compliance purposes.
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


class ToolResponse(TypedDict):
    """Tool response structure."""
    filePath: str
    success: bool


class InputData(TypedDict):
    """Complete input data structure."""
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput
    tool_response: ToolResponse


class LogEntry(TypedDict):
    """Structure for a log entry."""
    timestamp: str
    session_id: str
    tool_name: str
    file_path: str | None
    success: bool
    cwd: str


def main() -> None:
    """Main entry point for compliance logging hook."""
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
        
        # Extract tool_input for file_path
        file_path: str | None = None
        tool_input_obj = input_dict.get("tool_input")
        if isinstance(tool_input_obj, dict):
            tool_input_dict = cast(dict[str, object], tool_input_obj)
            file_path_obj = tool_input_dict.get("file_path")
            if isinstance(file_path_obj, str):
                file_path = file_path_obj
        
        # Extract success status from tool_response
        success = False
        tool_response_obj = input_dict.get("tool_response")
        if isinstance(tool_response_obj, dict):
            tool_response_dict = cast(dict[str, object], tool_response_obj)
            success_obj = tool_response_dict.get("success")
            if isinstance(success_obj, bool):
                success = success_obj
        
        # Create log entry
        log_entry: LogEntry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "tool_name": tool_name,
            "file_path": file_path,
            "success": success,
            "cwd": cwd
        }
        
        # Ensure log directory exists
        if cwd:
            log_dir = Path(cwd) / "logs"
        else:
            log_dir = Path.cwd() / "logs"
            
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "post_tools_use_logging.json"
        
        # Append to JSONL file (one JSON object per line)
        # Using JSONL format for better handling of large logs
        with open(log_path, "a", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write("\n")
        
        # Success - no output needed
        sys.exit(0)
        
    except Exception:
        # Exit cleanly on any error to avoid disrupting operations
        sys.exit(0)


if __name__ == "__main__":
    main()