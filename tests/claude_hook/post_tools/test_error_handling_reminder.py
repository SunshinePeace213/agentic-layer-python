#!/usr/bin/env python3
# type: ignore
# pyright: basic
"""
Unit Tests for Error Handling Reminder Hook
=============================================

Tests for the error_handling_reminder.py PostToolUse hook.

Test Coverage:
    - Configuration loading
    - File validation
    - AST pattern detection (try/except, async, database, API)
    - Risk scoring
    - Message generation
    - Integration tests

Test Structure:
    - Fixtures for sample Python code
    - Unit tests for individual functions
    - Integration tests for complete workflow

Run Tests:
    pytest -n auto tests/claude_hook/post_tools/test_error_handling_reminder.py
    pytest --cov=.claude/hooks/post_tools/error_handling_reminder tests/claude_hook/post_tools/test_error_handling_reminder.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ==================== Fixtures ====================


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    return tmp_path


@pytest.fixture
def hook_script() -> Path:
    """Get path to error_handling_reminder.py hook script."""
    return (
        Path(__file__).parent.parent.parent.parent
        / ".claude"
        / "hooks"
        / "post_tools"
        / "error_handling_reminder.py"
    )


@pytest.fixture
def sample_code_safe() -> str:
    """Sample Python code with proper error handling."""
    return """
import logging

logger = logging.getLogger(__name__)

async def fetch_user(user_id):
    try:
        response = await http_client.get(f"/users/{user_id}")
        logger.info(f"Fetched user {user_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        raise
"""


@pytest.fixture
def sample_code_risky_try_except() -> str:
    """Sample code with try/except without logging."""
    return """
def process_user_data(user_id):
    try:
        data = fetch_from_database(user_id)
        return process(data)
    except Exception:
        return None
"""


@pytest.fixture
def sample_code_risky_async() -> str:
    """Sample code with async function without error handling."""
    return """
async def fetch_user_profile(user_id):
    response = await http_client.get(f"/users/{user_id}")
    return response.json()
"""


@pytest.fixture
def sample_code_risky_database() -> str:
    """Sample code with database operations without error handling."""
    return """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()
"""


@pytest.fixture
def sample_code_risky_api_endpoint() -> str:
    """Sample code with API endpoint without error handling."""
    return """
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/users/<user_id>")
def get_user(user_id):
    user = database.query(User).filter_by(id=user_id).first()
    return jsonify(user.to_dict())
"""


@pytest.fixture
def sample_code_multiple_issues() -> str:
    """Sample code with multiple risky patterns."""
    return """
from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route("/users/<user_id>")
async def get_user(user_id):
    conn = sqlite3.connect("database.db")
    result = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(result)
"""


# ==================== Helper Functions ====================


def create_test_file(project_dir: Path, filename: str, content: str) -> Path:
    """Create a test Python file with content."""
    file_path = project_dir / filename
    file_path.write_text(content)
    return file_path


def create_hook_input(
    file_path: str, tool_name: str = "Write", success: bool = True
) -> dict[str, object]:
    """Create hook input JSON for testing."""
    return {
        "session_id": "test_session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": str(Path(file_path).parent),
        "hook_event_name": "PostToolUse",
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path, "content": "test content"},
        "tool_response": {"filePath": file_path, "success": success},
    }


def run_hook(
    hook_script: Path, hook_input: dict[str, object], env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """
    Run the hook script with input.

    Args:
        hook_script: Path to hook script
        hook_input: Input data for hook
        env: Environment variables

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    env_dict = os.environ.copy()
    if env:
        env_dict.update(env)

    result = subprocess.run(
        ["uv", "run", str(hook_script)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env=env_dict,
        timeout=30,
    )

    return result.returncode, result.stdout, result.stderr


# ==================== Configuration Tests ====================


def test_config_defaults() -> None:
    """Test default configuration loading."""
    sys.path.insert(
        0,
        str(
            Path(__file__).parent.parent.parent.parent
            / ".claude"
            / "hooks"
            / "post_tools"
        ),
    )
    from error_handling_reminder import Config

    config = Config.load()
    assert config.enabled is True
    assert config.min_score == 2
    assert config.include_tips is True
    assert config.debug is False


def test_config_from_env() -> None:
    """Test configuration loading from environment variables."""
    sys.path.insert(
        0,
        str(
            Path(__file__).parent.parent.parent.parent
            / ".claude"
            / "hooks"
            / "post_tools"
        ),
    )
    from error_handling_reminder import Config

    os.environ["ERROR_HANDLING_REMINDER_ENABLED"] = "false"
    os.environ["ERROR_HANDLING_REMINDER_MIN_SCORE"] = "5"
    os.environ["ERROR_HANDLING_REMINDER_INCLUDE_TIPS"] = "false"
    os.environ["ERROR_HANDLING_REMINDER_DEBUG"] = "true"

    config = Config.load()
    assert config.enabled is False
    assert config.min_score == 5
    assert config.include_tips is False
    assert config.debug is True

    # Cleanup
    del os.environ["ERROR_HANDLING_REMINDER_ENABLED"]
    del os.environ["ERROR_HANDLING_REMINDER_MIN_SCORE"]
    del os.environ["ERROR_HANDLING_REMINDER_INCLUDE_TIPS"]
    del os.environ["ERROR_HANDLING_REMINDER_DEBUG"]


# ==================== Pattern Detection Tests ====================


def test_detect_try_except_without_logging(
    project_dir: Path, hook_script: Path, sample_code_risky_try_except: str
) -> None:
    """Test detection of try/except without logging."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_try_except)
    hook_input = create_hook_input(str(file_path))

    # Set min score to 1 so single issue triggers feedback
    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    assert "additionalContext" in hook_output
    context = hook_output["additionalContext"]
    assert isinstance(context, str)
    assert "try-except block" in context


def test_detect_async_without_error_handling(
    project_dir: Path, hook_script: Path, sample_code_risky_async: str
) -> None:
    """Test detection of async functions without error handling."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_async)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    assert "async function" in output["hookSpecificOutput"]["additionalContext"]


def test_detect_database_operations(
    project_dir: Path, hook_script: Path, sample_code_risky_database: str
) -> None:
    """Test detection of database operations without error handling."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_database)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    assert "database operation" in output["hookSpecificOutput"]["additionalContext"]


def test_detect_api_endpoints(
    project_dir: Path, hook_script: Path, sample_code_risky_api_endpoint: str
) -> None:
    """Test detection of API endpoints without error handling."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_api_endpoint)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    assert "API endpoint" in output["hookSpecificOutput"]["additionalContext"]


def test_ignore_safe_code(
    project_dir: Path, hook_script: Path, sample_code_safe: str
) -> None:
    """Test that properly handled code is not flagged."""
    file_path = create_test_file(project_dir, "test.py", sample_code_safe)
    hook_input = create_hook_input(str(file_path))

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    # Should suppress output for safe code
    assert output.get("suppressOutput") is True
    # Should not have feedback for safe code
    if "hookSpecificOutput" in output:
        assert (
            "additionalContext" not in output["hookSpecificOutput"]
            or output["hookSpecificOutput"]["additionalContext"] == ""
        )


# ==================== Risk Scoring Tests ====================


def test_risk_score_calculation(
    project_dir: Path, hook_script: Path, sample_code_multiple_issues: str
) -> None:
    """Test that multiple patterns increase risk score."""
    file_path = create_test_file(project_dir, "test.py", sample_code_multiple_issues)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]

    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    context = hook_output["additionalContext"]
    assert isinstance(context, str)
    # Should contain multiple recommendations
    assert context.count("❓") >= 2


def test_threshold_filtering(
    project_dir: Path, hook_script: Path, sample_code_risky_async: str
) -> None:
    """Test that low scores don't trigger reminder."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_async)
    hook_input = create_hook_input(str(file_path))

    # Set high threshold
    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "10",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    # Should suppress output when below threshold
    assert output.get("suppressOutput") is True


# ==================== Message Generation Tests ====================


def test_message_format(
    project_dir: Path, hook_script: Path, sample_code_risky_try_except: str
) -> None:
    """Test output message formatting."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_try_except)
    hook_input = create_hook_input(str(file_path))

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    context = hook_output["additionalContext"]
    assert isinstance(context, str)

    # Check message structure
    assert "ERROR HANDLING SELF-CHECK" in context
    assert "Risky Patterns Detected" in context
    assert "❓" in context


def test_tips_section_configurable(
    project_dir: Path, hook_script: Path, sample_code_risky_try_except: str
) -> None:
    """Test that tips can be disabled via env var."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_try_except)
    hook_input = create_hook_input(str(file_path))

    # Disable tips
    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_INCLUDE_TIPS": "false",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    context = hook_output["additionalContext"]
    assert isinstance(context, str)

    # Should not contain best practices section
    assert "Best Practices" not in context


# ==================== Validation Tests ====================


def test_skip_non_python_files(project_dir: Path, hook_script: Path) -> None:
    """Test that non-Python files are skipped."""
    file_path = create_test_file(project_dir, "test.txt", "some text")
    hook_input = create_hook_input(str(file_path))

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert output.get("suppressOutput") is True


def test_skip_when_tool_fails(
    project_dir: Path, hook_script: Path, sample_code_safe: str
) -> None:
    """Test that failed tool operations are skipped."""
    file_path = create_test_file(project_dir, "test.py", sample_code_safe)
    hook_input = create_hook_input(str(file_path), success=False)

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert output.get("suppressOutput") is True


def test_disabled_via_env(
    project_dir: Path, hook_script: Path, sample_code_risky_try_except: str
) -> None:
    """Test that hook can be disabled via environment variable."""
    file_path = create_test_file(project_dir, "test.py", sample_code_risky_try_except)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_ENABLED": "false",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert output.get("suppressOutput") is True


# ==================== Error Handling Tests ====================


def test_error_handling_doesnt_block(project_dir: Path, hook_script: Path) -> None:
    """Test that errors result in silent exit."""
    # Create invalid hook input
    hook_input = {"invalid": "input"}

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    # Should exit cleanly even with invalid input
    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert output.get("suppressOutput") is True


def test_syntax_error_handling(project_dir: Path, hook_script: Path) -> None:
    """Test graceful handling of files with syntax errors."""
    invalid_python = """
def broken_function(
    # Missing closing paren and colon
"""
    file_path = create_test_file(project_dir, "test.py", invalid_python)
    hook_input = create_hook_input(str(file_path))

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    # Should exit cleanly
    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)
    assert output.get("suppressOutput") is True


# ==================== Integration Tests ====================


def test_full_workflow_with_risky_code(
    project_dir: Path, hook_script: Path, sample_code_multiple_issues: str
) -> None:
    """Test complete hook flow with risky code."""
    file_path = create_test_file(project_dir, "test.py", sample_code_multiple_issues)
    hook_input = create_hook_input(str(file_path))

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "ERROR_HANDLING_REMINDER_MIN_SCORE": "1",
    }
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)

    # Should have hook-specific output
    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "additionalContext" in output["hookSpecificOutput"]

    hook_output = output["hookSpecificOutput"]
    assert isinstance(hook_output, dict)
    context = hook_output["additionalContext"]
    assert isinstance(context, str)
    # Should contain feedback
    assert "ERROR HANDLING SELF-CHECK" in context
    assert "Risky Patterns" in context

    # Should suppress output in transcript
    assert output.get("suppressOutput") is True


def test_full_workflow_with_safe_code(
    project_dir: Path, hook_script: Path, sample_code_safe: str
) -> None:
    """Test complete hook flow with safe code."""
    file_path = create_test_file(project_dir, "test.py", sample_code_safe)
    hook_input = create_hook_input(str(file_path))

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}
    exit_code, stdout, stderr = run_hook(hook_script, hook_input, env)

    assert exit_code == 0
    output: dict[str, object] = json.loads(stdout)

    # Should have minimal output for safe code
    assert output.get("suppressOutput") is True
