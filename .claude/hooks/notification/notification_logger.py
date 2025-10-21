#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Notification Hook with JSONL Logging and Voice Alerts
======================================================
Logs notifications in JSONL format and triggers voice announcements.

Output JSON format:
- Success: {"continue": true, "suppressOutput": true}
- Failure: {"continue": false, "stopReason": "...", "systemMessage": "..."}

Note: Reads environment variables from system environment.
Use .env file loading via shell if needed.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict, cast


# Type definitions
class NotificationInput(TypedDict, total=False):
    """Input structure for notification hook."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    message: str


class HookOutput(TypedDict, total=False):
    """Output structure for hook response."""

    continue_: bool  # Use continue_ to avoid Python keyword conflict
    stopReason: str
    suppressOutput: bool
    systemMessage: str


class LogEntry(TypedDict):
    """Structure for JSONL log entry."""

    timestamp: str
    session_id: str
    message: str
    cwd: str
    triggered_voice: bool


def get_tts_script_path() -> Path | None:
    """
    Determine which TTS script to use.
    Priority: Kokoro > ElevenLabs > pyttsx3
    """
    script_dir = Path(__file__).parent.parent
    tts_dir = script_dir / "utils" / "tts"

    # Check for Kokoro (highest priority - local, fast, no API key needed)
    kokoro_script = tts_dir / "kokoro_tts.py"
    if kokoro_script.exists():
        return kokoro_script

    # Check for ElevenLabs (requires API key)
    if os.getenv("ELEVENLABS_API_KEY"):
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        if elevenlabs_script.exists():
            return elevenlabs_script

    # Fall back to pyttsx3 (no API key required)
    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return pyttsx3_script

    return None


def trigger_voice_notification(message: str) -> bool:
    """
    Trigger TTS voice notification.

    Args:
        message: Message to speak

    Returns:
        True if voice was triggered successfully, False otherwise
    """
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return False

        # Get engineer name if available
        engineer_name = os.getenv("ENGINEER_NAME", "").strip()

        # Create notification message with 30% chance to include name
        if engineer_name and random.random() < 0.3:
            notification_message = f"{engineer_name}, {message}"
        else:
            notification_message = message

        # Call the TTS script with timeout
        subprocess.run(
            ["uv", "run", str(tts_script), notification_message],
            capture_output=True,
            timeout=10,
            check=False,
        )

        return True

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues - non-blocking
        return False
    except Exception:
        # Fail silently for any other errors - non-blocking
        return False


def write_jsonl_log(log_entry: LogEntry, log_path: Path) -> None:
    """
    Write log entry to JSONL file (one JSON object per line).

    Args:
        log_entry: Log entry to write
        log_path: Path to JSONL log file

    Raises:
        OSError: If unable to write to log file
    """
    with open(log_path, "a", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False)
        f.write("\n")


def output_json(
    continue_execution: bool = True,
    stop_reason: str | None = None,
    suppress_output: bool = True,
    system_message: str | None = None,
) -> None:
    """
    Output JSON response and exit.

    Args:
        continue_execution: Whether Claude should continue
        stop_reason: Reason for stopping (when continue is False)
        suppress_output: Hide stdout from transcript mode
        system_message: Optional warning message for user
    """
    output: dict[str, bool | str] = {"continue": continue_execution}

    if not continue_execution and stop_reason:
        output["stopReason"] = stop_reason

    if suppress_output:
        output["suppressOutput"] = True

    if system_message:
        output["systemMessage"] = system_message

    print(json.dumps(output))
    sys.exit(0)


def main() -> None:
    """Main entry point for notification hook."""
    try:
        # Read JSON input from stdin
        input_text = sys.stdin.read()

        if not input_text:
            # No input - continue execution
            output_json(continue_execution=True)
            return

        # Parse JSON input
        try:
            input_data_raw = json.loads(input_text)  # type: ignore[reportAny]
        except json.JSONDecodeError:
            # Invalid JSON - continue gracefully
            output_json(continue_execution=True)
            return

        # Validate input structure
        if not isinstance(input_data_raw, dict):
            output_json(continue_execution=True)
            return

        # Cast to typed structure after validation
        input_data = cast(NotificationInput, input_data_raw)

        # Extract fields with proper typing
        session_id = input_data.get("session_id", "unknown")
        message = input_data.get("message", "")
        cwd = input_data.get("cwd", "")

        # Determine working directory
        if cwd:
            work_dir = Path(cwd)
        else:
            work_dir = Path.cwd()

        # Ensure log directory exists
        log_dir = work_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "notification.jsonl"

        # Trigger voice notification for important messages
        # Skip generic "waiting for input" message
        triggered_voice = False
        if message and message != "Claude is waiting for your input":
            triggered_voice = trigger_voice_notification(message)

        # Create log entry
        log_entry: LogEntry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "message": message,
            "cwd": str(work_dir),
            "triggered_voice": triggered_voice,
        }

        # Write to JSONL log
        try:
            write_jsonl_log(log_entry, log_path)
        except OSError as e:
            # Critical: log write failed
            output_json(
                continue_execution=False,
                stop_reason=f"Failed to write notification log: {e}",
                system_message="Notification logging is unavailable",
            )
            return

        # Success - continue execution with suppressed output
        output_json(continue_execution=True, suppress_output=True)

    except Exception as e:
        # Unexpected error - stop with message
        output_json(
            continue_execution=False,
            stop_reason=f"Notification hook error: {e}",
            system_message="Notification hook encountered an unexpected error",
        )


if __name__ == "__main__":
    main()
