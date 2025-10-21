#!/usr/bin/env python3
"""
BasedPyright Checking - PostToolUse Hook
========================================
Type-checks Python files after editing with complete type safety.
No Any types used - all data structures are properly typed.

This hook runs after Write, Edit, or MultiEdit operations on Python files and:
- Runs basedpyright with --level error for type checking
- Provides feedback to Claude about type violations
- Uses proper JSON output for PostToolUse events

Usage:
    python basedpyright_checking.py

Exit codes:
    0: Success (JSON output provides feedback)
    1: Non-blocking error (invalid input, continues)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, TypedDict, cast


# ============================================================================
# TYPE DEFINITIONS - No Any types!
# ============================================================================

class ToolInput(TypedDict, total=False):
    """Input parameters for tool operations."""
    file_path: str
    path: str
    content: str


class ToolResponse(TypedDict, total=False):
    """Response from tool execution."""
    filePath: str
    success: bool


class HookInput(TypedDict, total=False):
    """Complete input structure for PostToolUse hook."""
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput
    tool_response: ToolResponse


class HookSpecificOutput(TypedDict):
    """Hook-specific output for PostToolUse."""
    hookEventName: Literal["PostToolUse"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """Complete output structure for PostToolUse hook."""
    decision: Literal["block"] | None
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


class DiagnosticPosition(TypedDict):
    """Position in a file (line and character)."""
    line: int
    character: int


class DiagnosticRange(TypedDict):
    """Range in a file with start and end positions."""
    start: DiagnosticPosition
    end: DiagnosticPosition


class Diagnostic(TypedDict, total=False):
    """Diagnostic information from basedpyright."""
    file: str
    severity: Literal["error", "warning", "information", "hint"]
    message: str
    rule: str
    range: DiagnosticRange


class BasedPyrightSummary(TypedDict):
    """Summary information from basedpyright."""
    filesAnalyzed: int
    errorCount: int
    warningCount: int
    informationCount: int
    timeInSec: float


class BasedPyrightResults(TypedDict):
    """Complete results from basedpyright JSON output."""
    version: str
    time: str
    generalDiagnostics: list[Diagnostic]
    summary: BasedPyrightSummary


# ============================================================================
# MAIN HOOK IMPLEMENTATION
# ============================================================================

def main() -> None:
    """
    Main entry point for the basedpyright checking hook.
    
    Reads hook data from stdin and performs type checking.
    """
    try:
        # Read input from stdin with proper typing
        stdin_text = sys.stdin.read()
        
        if not stdin_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)
        
        # Parse JSON with proper typing
        try:
            # json.loads returns Any, we need to suppress and validate
            json_data = json.loads(stdin_text)  # type: ignore[reportAny]
            if not isinstance(json_data, dict):
                print("Error: Input must be a JSON object", file=sys.stderr)
                sys.exit(1)
            # Cast to properly typed dict
            parsed_json = cast(dict[str, object], json_data)
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Cast the validated dict to HookInput
        hook_data = cast(HookInput, parsed_json)
        
        # Extract fields
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        tool_response = hook_data.get("tool_response", {})
        
        # Only process file modification tools
        if tool_name not in {"Write", "Edit", "MultiEdit"}:
            # Not a file modification - skip
            output_result(None, None)
            return
        
        # Extract file path
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        
        if not file_path:
            # No file path - skip
            output_result(None, None)
            return
        
        # Only process Python files
        path_obj = Path(file_path)
        if path_obj.suffix not in {".py", ".pyi"}:
            # Not a Python file - skip
            output_result(None, None)
            return
        
        # Check if file exists
        if not path_obj.exists():
            # File doesn't exist - skip
            output_result(None, None)
            return
        
        # Check tool response for success
        if tool_response:
            success = tool_response.get("success", True)
            if not success:
                # Tool failed - skip type checking
                output_result(None, None)
                return
        
        # Run basedpyright type checking
        issues = run_basedpyright_on_file(file_path)
        
        # Prepare feedback based on results
        if issues:
            feedback = prepare_feedback(file_path, issues)
            output_result("block", feedback)
        else:
            context = f"✅ BasedPyright type check passed for {path_obj.name}"
            output_result(None, None, additional_context=context)
            
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def find_config_file() -> str | None:
    """
    Find the appropriate basedpyright configuration file.
    
    Returns:
        Path to config file if found, None otherwise
    """
    # Check for pyrightconfig.json first
    if Path("pyrightconfig.json").exists():
        return "pyrightconfig.json"
    
    # Check for pyproject.toml with basedpyright section
    if Path("pyproject.toml").exists():
        try:
            with open("pyproject.toml", "r", encoding="utf-8") as f:
                content = f.read()
                if "[tool.basedpyright]" in content or "[tool.pyright]" in content:
                    return "pyproject.toml"
        except Exception:
            pass
    
    return None


def run_basedpyright_on_file(file_path: str) -> list[str]:
    """
    Run basedpyright on a Python file for type checking.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of issues found
    """
    issues: list[str] = []
    
    # Find config file
    config_file = find_config_file()
    
    # Build command - always use --level error as per requirements
    cmd = ["basedpyright", "--level", "error", "--outputjson"]
    
    # Add config file if found
    if config_file:
        if config_file.endswith(".json"):
            cmd.extend(["--project", config_file])
        # For pyproject.toml, basedpyright should detect it automatically
    
    cmd.append(file_path)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Exit codes:
        # 0: Success, no errors
        # 1: Type errors found
        # 2+: Configuration or other errors
        
        if result.returncode == 0:
            # No issues found
            return []
        
        elif result.returncode == 1:
            # Type errors found - parse JSON output
            if result.stdout:
                try:
                    results = cast(BasedPyrightResults, json.loads(result.stdout))
                    issues = parse_diagnostics(results)
                except json.JSONDecodeError:
                    # Fallback to parsing plain output
                    if result.stdout:
                        issues = parse_plain_output(result.stdout)
                    elif result.stderr:
                        issues = [result.stderr.strip()]
        
        else:
            # Configuration or other error
            error_msg = result.stderr or result.stdout or f"BasedPyright failed with code {result.returncode}"
            issues = [f"Configuration error: {error_msg.strip()}"]
            
    except subprocess.TimeoutExpired:
        issues = ["BasedPyright timed out after 30 seconds"]
    except FileNotFoundError:
        issues = ["BasedPyright not found. Please install: pip install basedpyright"]
    except Exception as e:
        issues = [f"Error running basedpyright: {str(e)}"]
    
    return issues


def parse_diagnostics(results: BasedPyrightResults) -> list[str]:
    """
    Parse diagnostics from basedpyright JSON output.
    
    Args:
        results: BasedPyright JSON results
        
    Returns:
        List of formatted issue strings
    """
    issues: list[str] = []
    diagnostics = results.get("generalDiagnostics", [])
    
    # Focus on errors only (as we use --level error)
    for diag in diagnostics:
        severity = diag.get("severity", "").lower()
        if severity != "error":
            continue
        
        message = diag.get("message", "Unknown error")
        rule = diag.get("rule", "")
        
        # Get location
        range_info = diag.get("range", {})
        start = range_info.get("start", {})
        line = start.get("line", 0) + 1
        col = start.get("character", 0) + 1
        
        # Format issue
        if rule:
            issues.append(f"Line {line}:{col} - {message} ({rule})")
        else:
            issues.append(f"Line {line}:{col} - {message}")
    
    # Limit to 10 issues to avoid overwhelming
    return issues[:10]


def parse_plain_output(output: str) -> list[str]:
    """
    Parse plain text basedpyright output.
    
    Args:
        output: Plain text output from basedpyright
        
    Returns:
        List of formatted issue strings
    """
    issues: list[str] = []
    lines = output.strip().split("\n")
    
    for line in lines:
        if not line.strip():
            continue
        
        # Look for error lines
        if " - error:" in line.lower():
            # Extract the error message
            parts = line.split(" - error:", 1)
            if len(parts) == 2:
                location = parts[0].strip()
                message = parts[1].strip()
                # Simplify the location
                if ":" in location:
                    location = location.split("/")[-1]  # Get just filename:line:col
                issues.append(f"{location} - {message}")
            else:
                issues.append(line.strip())
        elif line.strip().startswith("error:"):
            issues.append(line.strip())
    
    # Limit to 10 issues
    return issues[:10]


def prepare_feedback(file_path: str, issues: list[str]) -> str:
    """
    Prepare feedback message for Claude about type checking issues.
    
    Args:
        file_path: Path to the file
        issues: List of issues found
        
    Returns:
        Feedback message
    """
    file_name = Path(file_path).name
    feedback_parts: list[str] = []
    
    feedback_parts.append(f"🔍 BasedPyright found type errors in {file_name}:")
    feedback_parts.append("")
    
    # Add issues
    feedback_parts.append("⚠️ Type Errors:")
    for issue in issues[:5]:  # Show first 5 issues
        feedback_parts.append(f"  • {issue}")
    
    if len(issues) > 5:
        feedback_parts.append(f"  ... and {len(issues) - 5} more")
    
    feedback_parts.append("")
    feedback_parts.append("💡 Suggestions:")
    feedback_parts.append("  • Add type annotations to clarify types")
    feedback_parts.append("  • Check for None before accessing optional values")
    feedback_parts.append("  • Ensure types match in assignments and function calls")
    feedback_parts.append("  • Use cast() for necessary type conversions")
    
    return "\n".join(feedback_parts)


def output_result(
    decision: Literal["block"] | None,
    reason: str | None,
    additional_context: str | None = None
) -> None:
    """
    Output a properly formatted JSON result for PostToolUse.
    
    Args:
        decision: Optional "block" decision
        reason: Reason for blocking (required if decision is "block")
        additional_context: Optional context to add for Claude
    """
    # Build output following the schema
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context or ""
        }
    }
    
    # Add decision and reason if blocking
    if decision == "block" and reason:
        output["decision"] = decision
        output["reason"] = reason
    
    try:
        # Output JSON and exit successfully
        print(json.dumps(output))
        sys.exit(0)
    except (TypeError, ValueError) as e:
        # Failed to serialize JSON - non-blocking error
        print(f"Error: Failed to serialize output JSON: {e}", file=sys.stderr)
        sys.exit(1)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()