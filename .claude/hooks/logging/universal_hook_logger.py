#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Universal Hook Logger - Claude Code Hook (Type-Safe)
=====================================================

Logs all hook payloads to session-specific JSONL files with full type safety.

Purpose:
    Capture complete hook event data for debugging, analytics, and auditing.
    Works across ALL hook events (PreToolUse, PostToolUse, Stop, etc.).

Hook Events: ALL (universal matcher "*")
Monitored Tools: N/A (applies to all events)

Output:
    - Exit code 0 (always non-blocking)
    - No stdout/stderr unless error occurs
    - Logs written to agents/hook_logs/{session_id}/{HookEventName}.jsonl

Log Format:
    Each line is a JSON object:
    {
        "timestamp": "2025-10-31T10:30:45.123456",
        "payload": { ... complete hook input data ... }
    }

Dependencies:
    - Python 3.11+
    - Standard library only
    - Shared utilities from .claude/hooks/logging/utils

Author: Claude Code Hook Expert
Version: 2.0.0
Last Updated: 2025-10-31
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    create_log_entry,
    get_hook_event_name,
    parse_universal_input,
    write_log_entry,
)


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin (type-safe)
        2. Extract session ID and hook event name
        3. Create enriched log entry with timestamp
        4. Write to session-specific JSONL file

    Error Handling:
        All exceptions result in exit 0 (non-blocking fail-safe).
        Errors logged to stderr but don't interrupt Claude operations.
    """
    try:
        # Parse input with type safety
        hook_input = parse_universal_input()

        if hook_input is None:
            # Parse failed - fail-safe: exit silently
            sys.exit(0)

        # Extract metadata
        session_id = hook_input.get("session_id", "unknown")
        hook_event_name = get_hook_event_name(hook_input)

        # Get project directory
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Create and write log entry
        log_entry = create_log_entry(hook_input)
        write_log_entry(session_id, hook_event_name, log_entry, project_dir)

        # Success - exit silently (non-blocking)
        sys.exit(0)

    except Exception as e:
        # Log error but don't block hook execution
        print(f"Universal hook logger error: {e}", file=sys.stderr)
        sys.exit(0)  # Non-blocking error


if __name__ == "__main__":
    main()
