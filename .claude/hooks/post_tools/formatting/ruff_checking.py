#!/usr/bin/env python3
"""
Ruff Checking - PostToolUse Hook
=================================
Automatically formats and checks Python files after editing.

This hook runs after Write, Edit, or MultiEdit operations on Python files and:
- Runs ruff format for consistent code style
- Runs ruff check with auto-fix for lint violations
- Provides feedback to Claude about any issues found

Usage:
    python ruff_checking.py

Exit codes:
    0: Success (JSON output provides feedback)
    1: Non-blocking error (invalid input, continues)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    file_path: str
    path: str


class ToolResponse(TypedDict, total=False):
    """Type definition for tool response."""
    filePath: str
    success: bool


class HookSpecificOutput(TypedDict):
    """Type definition for hook-specific output."""
    hookEventName: Literal["PostToolUse"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """Type definition for complete hook output."""
    decision: Literal["block"] | None
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


def main() -> None:
    """
    Main entry point for the ruff checking hook.
    
    Reads hook data from stdin and performs linting/formatting.
    """
    try:
        # Read input from stdin
        input_text = sys.stdin.read()
        
        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)
        
        # Parse JSON
        try:
            parsed_json = json.loads(input_text)  # type: ignore[reportAny]
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Validate input structure
        if not isinstance(parsed_json, dict):
            # Invalid format - non-blocking error
            print("Error: Input must be a JSON object", file=sys.stderr)
            sys.exit(1)
        
        # Extract fields with type checking
        tool_name_obj = parsed_json.get("tool_name", "")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        tool_input_obj = parsed_json.get("tool_input", {})  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        tool_response_obj = parsed_json.get("tool_response", {})  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        
        if not isinstance(tool_name_obj, str):
            # Missing tool_name - skip
            output_result(None, None)
            return
        
        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - skip
            output_result(None, None)
            return
        
        tool_name: str = tool_name_obj
        
        # Only process file modification tools
        if tool_name not in {"Write", "Edit", "MultiEdit"}:
            # Not a file modification - skip
            output_result(None, None)
            return
        
        # Extract file path
        file_path_val = tool_input_obj.get("file_path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not file_path_val:
            file_path_val = tool_input_obj.get("path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        
        if not isinstance(file_path_val, str):
            # No file path - skip
            output_result(None, None)
            return
        
        file_path = file_path_val
        
        # Only process Python files
        if not file_path.endswith(('.py', '.pyi')):
            # Not a Python file - skip
            output_result(None, None)
            return
        
        # Check if file exists (might be newly created)
        if not Path(file_path).exists():
            # File doesn't exist - skip
            output_result(None, None)
            return
        
        # Check tool response for success
        if isinstance(tool_response_obj, dict):
            success = tool_response_obj.get("success")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
            if isinstance(success, bool) and not success:
                # Tool failed - skip linting
                output_result(None, None)
                return
        
        # Run ruff format and check
        format_issues, check_issues = run_ruff_on_file(file_path)
        
        # Prepare feedback based on results
        if format_issues or check_issues:
            feedback = prepare_feedback(file_path, format_issues, check_issues)
            output_result("block", feedback)
        else:
            context = f"✅ Ruff successfully formatted and checked {Path(file_path).name}"
            output_result(None, None, additional_context=context)
            
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def find_config_file() -> str | None:
    """
    Find the appropriate ruff configuration file.
    
    Returns:
        Path to config file if found, None otherwise
    """
    config_files = ["pyproject.toml", "ruff.toml", ".ruff.toml"]
    
    for config in config_files:
        if Path(config).exists():
            return config
    
    return None


def run_ruff_on_file(file_path: str) -> tuple[list[str], list[str]]:
    """
    Run ruff format and check on a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Tuple of (format_issues, check_issues)
    """
    format_issues: list[str] = []
    check_issues: list[str] = []
    
    # Find config file
    config_file = find_config_file()
    
    # Run ruff format
    format_cmd = ["ruff", "format"]
    if config_file:
        format_cmd.extend(["--config", config_file])
    format_cmd.append(file_path)
    
    try:
        format_result = subprocess.run(
            format_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Ruff format exit codes:
        # 0: Success, file formatted
        # 1: Format would change the file (shouldn't happen as we're formatting)
        # 2: Error
        if format_result.returncode == 2:
            if format_result.stderr:
                format_issues.append(f"Format error: {format_result.stderr.strip()}")
        elif format_result.stdout and "formatted" in format_result.stdout.lower():
            # File was formatted
            pass  # Success message handled elsewhere
            
    except subprocess.TimeoutExpired:
        format_issues.append("Ruff format timed out")
    except FileNotFoundError:
        format_issues.append("Ruff not found. Please install: pip install ruff")
        return format_issues, check_issues
    except Exception as e:
        format_issues.append(f"Format error: {str(e)}")
    
    # Run ruff check with auto-fix
    check_cmd = ["ruff", "check", "--fix"]
    if config_file:
        check_cmd.extend(["--config", config_file])
    # Select common rule sets
    check_cmd.extend(["--select", "F,E,W,I"])  # Pyflakes, pycodestyle, import sorting
    check_cmd.append(file_path)
    
    try:
        check_result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Ruff check exit codes:
        # 0: Success, no violations
        # 1: Violations found (even after fixing what it could)
        # 2: Error
        if check_result.returncode == 1:
            # Some violations remain after auto-fix
            if check_result.stdout:
                # Parse violations from stdout
                lines = check_result.stdout.strip().split('\n')
                for line in lines:
                    if line and not line.startswith('Found') and not line.startswith('No fixes'):
                        check_issues.append(line.strip())
        elif check_result.returncode == 2:
            if check_result.stderr:
                check_issues.append(f"Check error: {check_result.stderr.strip()}")
                
    except subprocess.TimeoutExpired:
        check_issues.append("Ruff check timed out")
    except Exception as e:
        check_issues.append(f"Check error: {str(e)}")
    
    return format_issues, check_issues


def prepare_feedback(file_path: str, format_issues: list[str], check_issues: list[str]) -> str:
    """
    Prepare feedback message for Claude about linting issues.
    
    Args:
        file_path: Path to the file
        format_issues: List of format issues
        check_issues: List of check issues
        
    Returns:
        Feedback message
    """
    file_name = Path(file_path).name
    feedback_parts: list[str] = []
    
    feedback_parts.append(f"🔍 Ruff found issues in {file_name}:")
    
    if format_issues:
        feedback_parts.append("\n📝 Format Issues:")
        for issue in format_issues[:3]:  # Limit to 3 issues
            feedback_parts.append(f"  - {issue}")
        if len(format_issues) > 3:
            feedback_parts.append(f"  ... and {len(format_issues) - 3} more")
    
    if check_issues:
        feedback_parts.append("\n⚠️ Lint Violations (couldn't auto-fix):")
        for issue in check_issues[:5]:  # Limit to 5 issues
            feedback_parts.append(f"  - {issue}")
        if len(check_issues) > 5:
            feedback_parts.append(f"  ... and {len(check_issues) - 5} more")
    
    feedback_parts.append("\n💡 Suggestion: Review and fix the remaining issues manually.")
    feedback_parts.append("Ruff has auto-fixed what it could, but some issues need manual attention.")
    
    return "\n".join(feedback_parts)


def output_result(
    decision: Literal["block"] | None,
    reason: str | None,
    additional_context: str | None = None,
    suppress_output: bool = False
) -> None:
    """
    Output a properly formatted JSON result for PostToolUse.
    
    Args:
        decision: Optional "block" decision
        reason: Reason for blocking (required if decision is "block")
        additional_context: Optional context to add for Claude
        suppress_output: Whether to suppress output in transcript mode
    """
    output: HookOutput = {}
    
    # Add decision and reason if blocking
    if decision == "block" and reason:
        output["decision"] = decision
        output["reason"] = reason
    
    # Always add hookSpecificOutput for PostToolUse
    hook_output: HookSpecificOutput = {
        "hookEventName": "PostToolUse",
        "additionalContext": additional_context or ""
    }
    output["hookSpecificOutput"] = hook_output
    
    # Add suppressOutput if True
    if suppress_output:
        output["suppressOutput"] = True
    
    try:
        # Output JSON and exit successfully
        print(json.dumps(output))
        sys.exit(0)
    except (TypeError, ValueError) as e:
        # Failed to serialize JSON - non-blocking error
        print(f"Error: Failed to serialize output JSON: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
