# pyright: reportUnknownVariableType=false, reportAny=false
"""
Comprehensive Test Suite for Context Bundle Builder Hook
=========================================================

Tests all functionality of the context_bundle_builder.py hook including:
- File operation logging (Read/Write)
- User prompt logging
- Filename generation
- JSONL format
- Error handling
- Path conversion
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


# Path to the hook script (absolute path from project root)
HOOK_SCRIPT = (
    Path(__file__).parent.parent.parent.parent
    / ".claude"
    / "hooks"
    / "logging"
    / "context_bundle_builder.py"
)


class TestFileOperations:
    """Test Suite 1: File Operations (PostToolUse)"""

    def test_read_operation_logging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.1: Read operations are logged correctly."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("# test file")

        # Prepare input
        input_data = {
            "session_id": "test123",
            "tool_name": "Read",
            "tool_input": {"file_path": str(test_file), "limit": 100, "offset": 0},
            "tool_response": {"success": True},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        # Find the generated JSONL file
        bundle_dir = tmp_path / "agents" / "context_bundles"
        assert bundle_dir.exists(), "Bundle directory not created"

        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1, f"Expected 1 JSONL file, found {len(jsonl_files)}"

        # Parse JSONL
        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions
        assert entry["operation"] == "read"
        assert entry["file_path"] == "test.py"
        assert entry["tool_input"]["limit"] == 100
        assert entry["tool_input"]["offset"] == 0

    def test_write_operation_logging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.2: Write operations are logged correctly."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        test_file = tmp_path / "new_file.py"

        # Prepare input
        input_data = {
            "session_id": "test456",
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(test_file),
                "content": "print('hello world')",
            },
            "tool_response": {"success": True, "filePath": str(test_file)},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        # Find and parse JSONL
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions
        assert entry["operation"] == "write"
        assert entry["file_path"] == "new_file.py"
        assert entry["tool_input"]["content_length"] == len("print('hello world')")
        assert "content" not in entry["tool_input"], "Content should not be logged"

    def test_write_operation_failure_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.3: Failed Write operations are skipped."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Prepare input with failed write
        input_data = {
            "session_id": "test789",
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/test.py", "content": "test"},
            "tool_response": {"success": False},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code (should still be 0, just skipped)
        assert result.returncode == 0

        # Verify no JSONL file created
        bundle_dir = tmp_path / "agents" / "context_bundles"
        if bundle_dir.exists():
            jsonl_files = list(bundle_dir.glob("*.jsonl"))
            assert len(jsonl_files) == 0, "No log should be created for failed writes"

    def test_non_read_write_tool_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.4: Non-Read/Write tools are skipped."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Prepare input with Bash tool
        input_data = {
            "session_id": "test_bash",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
            "tool_response": {},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Verify no JSONL file created
        bundle_dir = tmp_path / "agents" / "context_bundles"
        if bundle_dir.exists():
            jsonl_files = list(bundle_dir.glob("*.jsonl"))
            assert len(jsonl_files) == 0, "No log should be created for Bash tool"

    def test_missing_file_path_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.5: Operations with missing file_path are skipped."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Prepare input without file_path
        input_data = {
            "session_id": "test_nopath",
            "tool_name": "Read",
            "tool_input": {},
            "tool_response": {},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Verify no JSONL file created
        bundle_dir = tmp_path / "agents" / "context_bundles"
        if bundle_dir.exists():
            jsonl_files = list(bundle_dir.glob("*.jsonl"))
            assert len(jsonl_files) == 0

    def test_path_outside_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.6: Files outside project keep absolute paths."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Use /tmp which is outside project
        external_file = "/tmp/external_file.py"

        # Prepare input
        input_data = {
            "session_id": "test_external",
            "tool_name": "Read",
            "tool_input": {"file_path": external_file},
            "tool_response": {"success": True},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Parse JSONL
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions - path should be absolute since it's outside project
        assert entry["file_path"] == external_file or entry["file_path"].startswith("/")

    def test_relative_path_conversion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 1.7: Paths inside project are converted to relative."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        # Create nested file
        nested_dir = tmp_path / "src" / "utils"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "helper.py"
        nested_file.write_text("# helper")

        # Prepare input with absolute path
        input_data = {
            "session_id": "test_relative",
            "tool_name": "Read",
            "tool_input": {"file_path": str(nested_file)},
            "tool_response": {"success": True},
            "hook_event_name": "PostToolUse",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Parse JSONL
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions - path should be relative
        assert entry["file_path"] == "src/utils/helper.py"


class TestUserPrompts:
    """Test Suite 2: User Prompts (UserPromptSubmit)"""

    def test_normal_prompt_logging(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 2.1: Normal prompts are logged correctly."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Prepare input
        input_data = {
            "session_id": "prompt123",
            "prompt": "Hello Claude, please help me",
            "hook_event_name": "UserPromptSubmit",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Parse JSONL
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions
        assert entry["operation"] == "prompt"
        assert entry["prompt"] == "Hello Claude, please help me"

    def test_long_prompt_truncation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 2.2: Long prompts are truncated to 500 characters."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Create a 1000-character prompt
        long_prompt = "A" * 1000

        # Prepare input
        input_data = {
            "session_id": "prompt_long",
            "prompt": long_prompt,
            "hook_event_name": "UserPromptSubmit",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Parse JSONL
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Assertions
        assert entry["operation"] == "prompt"
        assert len(entry["prompt"]) == 500
        assert entry["prompt"] == "A" * 500

    def test_empty_prompt_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 2.3: Empty prompts are skipped."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Prepare input with empty prompt
        input_data = {
            "session_id": "prompt_empty",
            "prompt": "",
            "hook_event_name": "UserPromptSubmit",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify exit code
        assert result.returncode == 0

        # Verify no JSONL file created
        bundle_dir = tmp_path / "agents" / "context_bundles"
        if bundle_dir.exists():
            jsonl_files = list(bundle_dir.glob("*.jsonl"))
            assert len(jsonl_files) == 0


class TestFilenameGeneration:
    """Test Suite 3: Filename Generation"""

    def test_correct_filename_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 3.1: Filename follows YYYY-MM-DD-DAY-HH-MM-SS-session_id.jsonl format."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Prepare input
        input_data = {
            "session_id": "format_test",
            "prompt": "Test prompt",
            "hook_event_name": "UserPromptSubmit",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0

        # Find JSONL file
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        filename = jsonl_files[0].name

        # Verify format using regex
        import re

        pattern = r"^\d{4}-\d{2}-\d{2}-[A-Z]{3}-\d{2}-\d{2}-\d{2}-format_test\.jsonl$"
        assert re.match(pattern, filename), f"Filename {filename} doesn't match pattern"

        # Verify components
        parts = filename.split("-")
        assert len(parts) == 8  # YYYY-MM-DD-DAY-HH-MM-SS-session.jsonl
        assert parts[3] in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    def test_day_abbreviation_uppercase(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 3.2: Day abbreviations are uppercase."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Prepare input
        input_data = {
            "session_id": "day_test",
            "prompt": "Test",
            "hook_event_name": "UserPromptSubmit",
        }

        # Execute hook
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0

        # Find JSONL file
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        filename = jsonl_files[0].name

        # Extract day part (4th component)
        day_part = filename.split("-")[3]
        assert day_part.isupper(), f"Day abbreviation {day_part} should be uppercase"
        assert len(day_part) == 3, f"Day abbreviation {day_part} should be 3 characters"

    def test_multiple_operations_same_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 3.3: Multiple operations with same session_id append to same file."""
        # Setup
        monkeypatch.chdir(tmp_path)

        session_id = "multi_ops"

        # Execute multiple operations
        for i in range(3):
            input_data = {
                "session_id": session_id,
                "prompt": f"Prompt {i}",
                "hook_event_name": "UserPromptSubmit",
            }

            result = subprocess.run(
                [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd=tmp_path,
            )
            assert result.returncode == 0

        # Verify single file with multiple entries
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1, "Should have single file for same session"

        # Count lines
        with open(jsonl_files[0]) as f:
            lines = f.readlines()
        assert len(lines) == 3, "Should have 3 entries"

    def test_different_sessions_different_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 3.4: Different sessions create separate files."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Execute operations with different sessions
        for i in range(3):
            input_data = {
                "session_id": f"session{i}",
                "prompt": f"Prompt {i}",
                "hook_event_name": "UserPromptSubmit",
            }

            result = subprocess.run(
                [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd=tmp_path,
            )
            assert result.returncode == 0

        # Verify multiple files
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 3, "Should have 3 separate files"


class TestJSONLFormat:
    """Test Suite 4: JSONL Format"""

    def test_valid_json_per_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 4.1: Each line is valid JSON."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Add multiple entries
        for i in range(5):
            input_data = {
                "session_id": "jsonl_test",
                "prompt": f"Prompt {i}",
                "hook_event_name": "UserPromptSubmit",
            }

            subprocess.run(
                [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd=tmp_path,
            )

        # Verify each line is valid JSON
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))

        with open(jsonl_files[0]) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    assert isinstance(entry, dict), f"Line {line_num} is not a dict"
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")

    def test_newline_separation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 4.2: Entries are separated by newlines."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Add entries
        for i in range(3):
            input_data = {
                "session_id": "newline_test",
                "prompt": f"Test {i}",
                "hook_event_name": "UserPromptSubmit",
            }

            subprocess.run(
                [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd=tmp_path,
            )

        # Verify newlines
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))

        with open(jsonl_files[0], "rb") as f:
            content = f.read()

        # File should end with newline
        assert content.endswith(b"\n"), "File should end with newline"

        # Count newlines matches entry count
        newline_count = content.count(b"\n")
        assert newline_count == 3, f"Expected 3 newlines, found {newline_count}"

    def test_no_nested_newlines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 4.3: Newlines in prompt text are escaped."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Prompt with newlines
        input_data = {
            "session_id": "escape_test",
            "prompt": "Line 1\nLine 2\nLine 3",
            "hook_event_name": "UserPromptSubmit",
        }

        subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Verify single line
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))

        with open(jsonl_files[0]) as f:
            lines = f.readlines()

        # Should be exactly 1 line (entry on single line with trailing newline)
        assert len(lines) == 1, "Entry with newlines should be on single line"

        # Parse and verify content
        entry = json.loads(lines[0])
        assert "\n" in entry["prompt"], "Newlines should be preserved in JSON string"


class TestErrorHandling:
    """Test Suite 5: Error Handling"""

    def test_invalid_json_input(self, tmp_path: Path) -> None:
        """Test 5.1: Invalid JSON returns error."""
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input="invalid json{",
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Should exit with error code 1
        assert result.returncode == 1
        assert "Error parsing JSON input" in result.stderr

    def test_missing_session_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 5.2: Missing session_id uses 'unknown'."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Input without session_id
        input_data = {"prompt": "Test", "hook_event_name": "UserPromptSubmit"}

        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Should succeed
        assert result.returncode == 0

        # Verify filename contains "unknown"
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        assert "unknown" in jsonl_files[0].name

    def test_directory_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 5.3: Directory is created automatically."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Verify directory doesn't exist
        bundle_dir = tmp_path / "agents" / "context_bundles"
        assert not bundle_dir.exists()

        # Execute hook
        input_data = {
            "session_id": "dir_test",
            "prompt": "Test",
            "hook_event_name": "UserPromptSubmit",
        }

        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0

        # Verify directory was created
        assert bundle_dir.exists()
        assert bundle_dir.is_dir()


class TestIntegration:
    """Test Suite 6: Integration Tests"""

    def test_full_session_workflow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 6.1: Full session with mixed operations."""
        # Setup
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        session_id = "full_workflow"

        # 1. User prompt
        subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "prompt": "Add a new feature",
                    "hook_event_name": "UserPromptSubmit",
                }
            ),
            capture_output=True,
            cwd=tmp_path,
        )

        # 2. Read operation
        test_file = tmp_path / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("# main")

        subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(test_file)},
                    "tool_response": {"success": True},
                    "hook_event_name": "PostToolUse",
                }
            ),
            capture_output=True,
            cwd=tmp_path,
        )

        # 3. Write operation
        new_file = tmp_path / "src" / "feature.py"
        subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(new_file), "content": "# feature"},
                    "tool_response": {"success": True},
                    "hook_event_name": "PostToolUse",
                }
            ),
            capture_output=True,
            cwd=tmp_path,
        )

        # 4. Another prompt
        subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt"],
            input=json.dumps(
                {
                    "session_id": session_id,
                    "prompt": "Run the tests",
                    "hook_event_name": "UserPromptSubmit",
                }
            ),
            capture_output=True,
            cwd=tmp_path,
        )

        # Verify all operations logged
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

        with open(jsonl_files[0]) as f:
            entries = [json.loads(line) for line in f]

        assert len(entries) == 4
        assert entries[0]["operation"] == "prompt"
        assert entries[1]["operation"] == "read"
        assert entries[2]["operation"] == "write"
        assert entries[3]["operation"] == "prompt"

    def test_argument_parsing(self, tmp_path: Path) -> None:
        """Test 6.2: Argument parsing works correctly."""
        # Test --type file_ops
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops", "--help"],
            capture_output=True,
            text=True,
        )
        assert "file_ops" in result.stdout or result.returncode == 0

        # Test --type user_prompt
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "user_prompt", "--help"],
            capture_output=True,
            text=True,
        )
        assert "user_prompt" in result.stdout or result.returncode == 0

    def test_claude_project_dir_env_variable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 6.3: CLAUDE_PROJECT_DIR environment variable is respected."""
        # Setup custom project dir
        custom_project = tmp_path / "custom_project"
        custom_project.mkdir()

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(custom_project))
        monkeypatch.chdir(tmp_path)

        # Create file inside custom project
        test_file = custom_project / "test.py"
        test_file.write_text("# test")

        # Execute hook
        input_data = {
            "session_id": "env_test",
            "tool_name": "Read",
            "tool_input": {"file_path": str(test_file)},
            "tool_response": {"success": True},
            "hook_event_name": "PostToolUse",
        }

        import os

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(custom_project)

        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT), "--type", "file_ops"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=env,
        )

        assert result.returncode == 0

        # Verify path is relative to custom project
        bundle_dir = tmp_path / "agents" / "context_bundles"
        jsonl_files = list(bundle_dir.glob("*.jsonl"))

        with open(jsonl_files[0]) as f:
            entry = json.loads(f.readline())

        # Path should be relative: just "test.py"
        assert entry["file_path"] == "test.py"
