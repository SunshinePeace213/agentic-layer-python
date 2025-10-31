# pyright: reportUnknownVariableType=false, reportMissingImports=false, reportAny=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false
"""
Test Suite for UserPromptSubmit Data Types
===========================================

Tests the TypedDict definitions for UserPromptSubmit hooks.
"""

import sys
from pathlib import Path
from typing import get_type_hints

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent.parent.parent.parent / ".claude" / "hooks"
sys.path.insert(0, str(hooks_dir))


def test_import_data_types() -> None:
    """Test that data types can be imported successfully."""
    from user_prompt_submit.utils.data_types import (
        HookOutput,
        HookSpecificOutput,
        UserPromptSubmitInput,
    )

    assert UserPromptSubmitInput is not None
    assert HookOutput is not None
    assert HookSpecificOutput is not None


def test_user_prompt_submit_input_structure() -> None:
    """Test UserPromptSubmitInput TypedDict structure."""
    from user_prompt_submit.utils.data_types import UserPromptSubmitInput

    # Verify it's a TypedDict by checking annotations
    annotations = get_type_hints(UserPromptSubmitInput)

    assert "session_id" in annotations
    assert "transcript_path" in annotations
    assert "cwd" in annotations
    assert "hook_event_name" in annotations
    assert "prompt" in annotations


def test_hook_specific_output_structure() -> None:
    """Test HookSpecificOutput TypedDict structure."""
    from user_prompt_submit.utils.data_types import HookSpecificOutput

    annotations = get_type_hints(HookSpecificOutput)

    assert "hookEventName" in annotations
    assert "additionalContext" in annotations


def test_hook_output_structure() -> None:
    """Test HookOutput TypedDict structure."""
    from user_prompt_submit.utils.data_types import HookOutput

    annotations = get_type_hints(HookOutput)

    assert "decision" in annotations
    assert "reason" in annotations
    assert "hookSpecificOutput" in annotations
    assert "suppressOutput" in annotations


def test_public_api_exports() -> None:
    """Test that public API exports all necessary types."""
    from user_prompt_submit.utils import (  # type: ignore[import]
        HookOutput,
        HookSpecificOutput,
        UserPromptSubmitInput,
    )

    # Verify all types are accessible
    assert UserPromptSubmitInput is not None
    assert HookOutput is not None
    assert HookSpecificOutput is not None


def test_user_prompt_submit_input_example() -> None:
    """Test creating a valid UserPromptSubmitInput instance."""
    from user_prompt_submit.utils.data_types import UserPromptSubmitInput

    # Create a valid instance
    input_data: UserPromptSubmitInput = {
        "session_id": "test123",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/project/root",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Test prompt",
    }

    assert input_data["session_id"] == "test123"
    assert input_data["hook_event_name"] == "UserPromptSubmit"
    assert input_data["prompt"] == "Test prompt"


def test_hook_output_non_blocking_example() -> None:
    """Test creating a non-blocking HookOutput."""
    from user_prompt_submit.utils.data_types import HookOutput, HookSpecificOutput

    # Non-blocking output (no decision field)
    hook_specific: HookSpecificOutput = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "Prompt validated successfully",
    }

    output: HookOutput = {
        "hookSpecificOutput": hook_specific,
        "suppressOutput": True,
    }

    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert output["suppressOutput"] is True
    assert "decision" not in output


def test_hook_output_blocking_example() -> None:
    """Test creating a blocking HookOutput."""
    from user_prompt_submit.utils.data_types import HookOutput, HookSpecificOutput

    # Blocking output
    hook_specific: HookSpecificOutput = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "Remove API keys before submitting",
    }

    output: HookOutput = {
        "decision": "block",
        "reason": "Prompt contains sensitive information",
        "hookSpecificOutput": hook_specific,
        "suppressOutput": False,
    }

    assert output["decision"] == "block"
    assert output["reason"] == "Prompt contains sensitive information"
    assert output["suppressOutput"] is False
