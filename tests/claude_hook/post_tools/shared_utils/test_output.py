#!/usr/bin/env python3
"""
Unit Tests for PostToolUse Shared Utilities - Output Functions

Tests the output_feedback, output_block, and output_result functions.
"""

import json
import pytest

from utils import HookOutput, output_block, output_feedback, output_result


class TestOutputFeedback:
    """Tests for output_feedback function."""

    def test_output_feedback_with_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting feedback with context."""
        with pytest.raises(SystemExit) as exc_info:
            output_feedback("Test feedback message")

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"]  # type: ignore[index] == "PostToolUse"
        assert output["hookSpecificOutput"]["additionalContext"]  # type: ignore[index] == "Test feedback message"
        assert "decision" not in output
        assert "reason" not in output

    def test_output_feedback_with_suppress(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting feedback with suppressOutput flag."""
        with pytest.raises(SystemExit) as exc_info:
            output_feedback("Test message", suppress_output=True)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output["suppressOutput"] is True
        assert output["hookSpecificOutput"]["additionalContext"]  # type: ignore[index] == "Test message"

    def test_output_feedback_empty_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting feedback with empty context."""
        with pytest.raises(SystemExit) as exc_info:
            output_feedback("")

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        # Should still have hookSpecificOutput but no additionalContext
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"]  # type: ignore[index] == "PostToolUse"
        assert "additionalContext" not in output["hookSpecificOutput"]  # type: ignore[operator]

    def test_output_feedback_empty_with_suppress(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting empty feedback with suppress flag."""
        with pytest.raises(SystemExit) as exc_info:
            output_feedback("", suppress_output=True)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output["suppressOutput"] is True


class TestOutputBlock:
    """Tests for output_block function."""

    def test_output_block_with_reason(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting block decision with reason."""
        with pytest.raises(SystemExit) as exc_info:
            output_block("Critical error detected")

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        # decision and reason at TOP LEVEL (not in hookSpecificOutput)
        assert output["decision"]  # type: ignore[index] == "block"
        assert output["reason"]  # type: ignore[index] == "Critical error detected"
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"]  # type: ignore[index] == "PostToolUse"

    def test_output_block_with_additional_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting block with additional context."""
        with pytest.raises(SystemExit) as exc_info:
            output_block(
                reason="Type checking failed",
                additional_context="Run: basedpyright file.py"
            )

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output["decision"]  # type: ignore[index] == "block"
        assert output["reason"]  # type: ignore[index] == "Type checking failed"
        assert output["hookSpecificOutput"]["additionalContext"]  # type: ignore[index] == "Run: basedpyright file.py"

    def test_output_block_with_suppress(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting block with suppressOutput flag."""
        with pytest.raises(SystemExit) as exc_info:
            output_block(
                reason="Error",
                additional_context="Details",
                suppress_output=True
            )

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output["suppressOutput"] is True
        assert output["decision"]  # type: ignore[index] == "block"
        assert output["reason"]  # type: ignore[index] == "Error"

    def test_output_block_no_additional_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting block without additional context."""
        with pytest.raises(SystemExit) as exc_info:
            output_block(reason="Simple error")

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output["decision"]  # type: ignore[index] == "block"
        assert output["reason"]  # type: ignore[index] == "Simple error"
        assert "additionalContext" not in output["hookSpecificOutput"]  # type: ignore[operator]


class TestOutputResult:
    """Tests for output_result function."""

    def test_output_result_complete(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting complete HookOutput structure."""
        hook_output: HookOutput = {
            "decision": "block",
            "reason": "Test reason",
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Test context"
            },
            "suppressOutput": True
        }

        with pytest.raises(SystemExit) as exc_info:
            output_result(hook_output)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output == hook_output

    def test_output_result_minimal(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting minimal HookOutput structure."""
        hook_output: HookOutput = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse"
            }
        }

        with pytest.raises(SystemExit) as exc_info:
            output_result(hook_output)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"]  # type: ignore[index] == "PostToolUse"

    def test_output_result_empty_dict(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputting empty HookOutput dictionary."""
        hook_output: HookOutput = {}

        with pytest.raises(SystemExit) as exc_info:
            output_result(hook_output)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output: dict[str, object] = json.loads(captured.out)  # type: ignore[assignment]

        assert output == {}
