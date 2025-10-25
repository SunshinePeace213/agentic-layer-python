#!/usr/bin/env python3
"""
Test Suite for UV Dependency Blocker Hook
==========================================

Comprehensive tests for the uv_dependency_blocker.py hook.
Tests all protected file patterns, path resolution, and special cases.

Run with:
    uv run pytest .claude/hooks/pre_tools/tests/test_uv_dependency_blocker.py -v
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, TypedDict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.data_types import ToolInput
except ImportError:
    from ..utils.data_types import ToolInput


# Import the functions to test (will be implemented)
from uv_dependency_blocker import validate_dependency_file_edit


# Type definitions for hook output
class HookSpecificOutputType(TypedDict):
    """Type for hook-specific output."""
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutputType(TypedDict):
    """Type for complete hook output."""
    hookSpecificOutput: HookSpecificOutputType


class TestTemplateFilesAllowed:
    """Test that template/example files are allowed."""

    def test_allows_requirements_sample(self) -> None:
        """Test that requirements.txt.sample is allowed."""
        tool_input: ToolInput = {"file_path": "requirements.txt.sample"}
        result = validate_dependency_file_edit(tool_input)
        assert result is None


class TestRequirementsVariants:
    """Test that requirements file variants are blocked."""

    def test_blocks_requirements_dev_txt(self) -> None:
        """Test that requirements-dev.txt is blocked."""
        tool_input: ToolInput = {"file_path": "requirements-dev.txt"}
        result = validate_dependency_file_edit(tool_input)
        assert result is not None


class TestProtectedFileDetection:
    """Test detection of protected dependency files."""

    def test_blocks_requirements_txt_edit(self) -> None:
        """Test that editing requirements.txt is blocked."""
        tool_input: ToolInput = {"file_path": "requirements.txt"}
        result = validate_dependency_file_edit(tool_input)
        assert result is not None
        assert "requirements.txt" in result.lower()
        assert "uv add" in result.lower()

    def test_blocks_pyproject_toml_edit(self) -> None:
        """Test that editing pyproject.toml is blocked."""
        tool_input: ToolInput = {"file_path": "pyproject.toml"}
        result = validate_dependency_file_edit(tool_input)
        assert result is not None
        assert "pyproject.toml" in result.lower()

    def test_blocks_uv_lock_edit(self) -> None:
        """Test that editing uv.lock is blocked."""
        tool_input: ToolInput = {"file_path": "uv.lock"}
        result = validate_dependency_file_edit(tool_input)
        assert result is not None
        assert "auto-generated" in result.lower()

    def test_blocks_pipfile_edit(self) -> None:
        """Test that editing Pipfile is blocked."""
        tool_input: ToolInput = {"file_path": "Pipfile"}
        result = validate_dependency_file_edit(tool_input)
        assert result is not None


class TestIntegration:
    """Integration tests with actual hook execution."""

    def test_hook_integration_blocks_requirements_txt(self) -> None:
        """Integration test: Hook should block requirements.txt edits."""
        hook_input = {
            "session_id": "test123",
            "transcript_path": "/tmp/transcript.jsonl",
            "cwd": "/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "requirements.txt"},
        }

        result = subprocess.run(
            ["uv", "run", ".claude/hooks/pre_tools/uv_dependency_blocker.py"],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output: HookOutputType = json.loads(result.stdout)  # type: ignore[assignment]
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
