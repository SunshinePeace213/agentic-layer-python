#!/usr/bin/env python3
"""
Logging Hook Utilities - Helper Functions
==========================================

Common utility functions for universal hook logging.

Usage:
    from logging.utils import parse_universal_input, create_log_entry, write_log_entry

Dependencies:
    - Python 3.11+ (for typing)
    - No external packages required
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from .data_types import LogEntry, UniversalHookInput


def parse_universal_input() -> UniversalHookInput | None:
    """
    Parse hook input from stdin as a universal hook input.

    Returns:
        Parsed hook input if successful, None if parsing fails

    Type Safety:
        Returns UniversalHookInput which is a Union of all hook event types.
        Runtime validation ensures the structure is valid.
    """
    try:
        input_text = sys.stdin.read()
        # json.loads returns Any, but we know it's a dict at runtime
        parsed_json = cast(dict[str, object], json.loads(input_text))

        # Basic validation: ensure required fields exist
        required_fields = ["session_id", "hook_event_name"]
        if not all(field in parsed_json for field in required_fields):
            return None

        # Cast to UniversalHookInput (runtime trust after validation)
        return cast(UniversalHookInput, parsed_json)

    except (json.JSONDecodeError, ValueError):
        return None


def get_hook_event_name(hook_input: UniversalHookInput) -> str:
    """
    Extract hook event name from input data.

    Args:
        hook_input: Parsed hook input

    Returns:
        Hook event name (e.g., "PreToolUse", "Stop")
    """
    return hook_input.get("hook_event_name", "Unknown")


def create_log_entry(hook_input: UniversalHookInput) -> LogEntry:
    """
    Create enriched log entry with timestamp and full payload.

    Args:
        hook_input: Parsed hook input

    Returns:
        Log entry ready to be written to JSONL
    """
    return LogEntry(timestamp=datetime.now().isoformat(), payload=hook_input)


def write_log_entry(
    session_id: str, hook_event_name: str, log_entry: LogEntry, project_dir: str
) -> None:
    """
    Write log entry to appropriate JSONL file.

    Args:
        session_id: Session identifier
        hook_event_name: Name of hook event (for file naming)
        log_entry: Log entry to write
        project_dir: Project root directory

    File Structure:
        {project_dir}/agents/hook_logs/{session_id}/{HookEventName}.jsonl

    Behavior:
        - Creates directory structure if it doesn't exist
        - Appends to existing file (creates if new)
        - Each entry is a single JSON line
    """
    # Create directory structure
    log_dir = Path(project_dir) / "agents" / "hook_logs" / session_id
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create hook-specific log file
    log_file = log_dir / f"{hook_event_name}.jsonl"

    # Append to JSONL file (atomic write)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
