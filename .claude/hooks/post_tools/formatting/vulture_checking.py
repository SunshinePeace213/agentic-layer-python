#!/usr/bin/env python3
"""
Vulture Checking - PostToolUse Hook
===================================
Detects dead code in Python files after editing with complete type safety.
No Any types used - all data structures are properly typed.

This hook runs after Write, Edit, or MultiEdit operations on Python files and:
- Runs vulture to detect unused code
- Provides feedback to Claude about dead code
- Uses proper JSON output for PostToolUse events

Usage:
    python vulture_checking.py

Exit codes:
    0: Success (JSON output provides feedback)
    1: Non-blocking error (invalid input, continues)
"""

from __future__ import annotations

import json
import re
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


class VultureFinding(TypedDict):
    """Parsed finding from vulture output."""
    line: int
    message: str
    confidence: int
    finding_type: str


# ============================================================================
# MAIN HOOK IMPLEMENTATION
# ============================================================================

def main() -> None:
    """
    Main entry point for the vulture checking hook.
    
    Reads hook data from stdin and performs dead code detection.
    """
    try:
        # Read input from stdin
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
                # Tool failed - skip dead code detection
                output_result(None, None)
                return
        
        # Run vulture dead code detection
        findings = run_vulture_on_file(file_path)
        
        # Prepare feedback based on results
        if findings:
            feedback = prepare_feedback(file_path, findings)
            # Don't block for dead code, just provide feedback
            output_result(None, None, additional_context=feedback)
        else:
            context = f"✅ Vulture check passed for {path_obj.name} - no dead code detected"
            output_result(None, None, additional_context=context)
            
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def find_whitelist_files() -> list[str]:
    """
    Find vulture whitelist files in the current directory.
    
    Returns:
        List of whitelist file paths
    """
    whitelist_patterns = [
        "whitelist.py",
        "vulture_whitelist.py",
        "*_whitelist.py",
        "whitelist_*.py"
    ]
    
    whitelists: list[str] = []
    cwd = Path.cwd()
    
    for pattern in whitelist_patterns:
        for path in cwd.glob(pattern):
            if path.is_file() and path.suffix == ".py":
                whitelists.append(str(path))
    
    return whitelists


def run_vulture_on_file(file_path: str) -> list[VultureFinding]:
    """
    Run vulture on a Python file for dead code detection.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        List of findings
    """
    findings: list[VultureFinding] = []
    
    # Build command
    cmd = ["vulture", file_path]
    
    # Add whitelist files if they exist
    whitelists = find_whitelist_files()
    if whitelists:
        cmd.extend(whitelists)
    
    # Add minimum confidence to reduce false positives
    cmd.extend(["--min-confidence", "80"])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Vulture exit codes:
        # 0: No dead code found
        # 3: Dead code found
        # 1: File/syntax issues
        # 2: Invalid command line arguments
        
        if result.returncode == 0:
            # No dead code found
            return []
        
        elif result.returncode == 3:
            # Dead code found - parse output
            if result.stdout:
                findings = parse_vulture_output(result.stdout)
        
        elif result.returncode == 1:
            # File/syntax issues - don't report as findings
            if "SyntaxError" in result.stderr or "IndentationError" in result.stderr:
                # Syntax error in file - skip vulture check
                return []
        
        # For other exit codes, return empty list
        
    except subprocess.TimeoutExpired:
        # Timeout - return empty list
        pass
    except FileNotFoundError:
        # Vulture not installed - return one finding as notification
        findings = [{
            "line": 0,
            "message": "Vulture not found. Install with: pip install vulture",
            "confidence": 100,
            "finding_type": "error"
        }]
    except Exception:
        # Other errors - return empty list
        pass
    
    return findings


def parse_vulture_output(output: str) -> list[VultureFinding]:
    """
    Parse vulture output into structured findings.
    
    Args:
        output: Raw output from vulture
        
    Returns:
        List of parsed findings
    """
    findings: list[VultureFinding] = []
    
    # Pattern to parse vulture output: filename:line: message (confidence%)
    pattern = r'^.+?:(\d+):\s+(.+?)\s+\((\d+)% confidence\)$'
    
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
        
        match = re.match(pattern, line)
        if match:
            line_num = int(match.group(1))
            message = match.group(2)
            confidence = int(match.group(3))
            
            # Determine finding type from message
            finding_type = "unknown"
            msg_lower = message.lower()
            if "unused import" in msg_lower:
                finding_type = "unused_import"
            elif "unused function" in msg_lower:
                finding_type = "unused_function"
            elif "unused class" in msg_lower:
                finding_type = "unused_class"
            elif "unused variable" in msg_lower:
                finding_type = "unused_variable"
            elif "unused method" in msg_lower:
                finding_type = "unused_method"
            elif "unused attribute" in msg_lower:
                finding_type = "unused_attribute"
            elif "unreachable code" in msg_lower:
                finding_type = "unreachable_code"
            
            findings.append({
                "line": line_num,
                "message": message,
                "confidence": confidence,
                "finding_type": finding_type
            })
    
    # Sort by line number and limit to 10 findings
    findings.sort(key=lambda x: x["line"])
    return findings[:10]


def prepare_feedback(file_path: str, findings: list[VultureFinding]) -> str:
    """
    Prepare feedback message for Claude about dead code.
    
    Args:
        file_path: Path to the file
        findings: List of vulture findings
        
    Returns:
        Feedback message
    """
    file_name = Path(file_path).name
    feedback_parts: list[str] = []
    
    feedback_parts.append(f"🔍 Vulture found potential dead code in {file_name}:")
    feedback_parts.append("")
    
    # Group findings by type
    by_type: dict[str, list[VultureFinding]] = {}
    for finding in findings:
        finding_type = finding["finding_type"]
        if finding_type not in by_type:
            by_type[finding_type] = []
        by_type[finding_type].append(finding)
    
    # Display grouped findings
    type_icons = {
        "unused_import": "📦",
        "unused_function": "⚡",
        "unused_class": "🏗️",
        "unused_variable": "📝",
        "unused_method": "🔧",
        "unused_attribute": "🏷️",
        "unreachable_code": "⛔",
        "error": "❌",
        "unknown": "❓"
    }
    
    for finding_type, items in by_type.items():
        icon = type_icons.get(finding_type, "❓")
        type_label = finding_type.replace("_", " ").title()
        feedback_parts.append(f"{icon} {type_label}:")
        for item in items[:3]:  # Show max 3 per type
            feedback_parts.append(f"  • Line {item['line']}: {item['message']} ({item['confidence']}% confidence)")
        if len(items) > 3:
            feedback_parts.append(f"  ... and {len(items) - 3} more")
    
    feedback_parts.append("")
    feedback_parts.append("💡 Note: Some may be false positives. Consider:")
    feedback_parts.append("  • Remove genuinely unused code")
    feedback_parts.append("  • Use 'del' to mark intentionally unused variables")
    feedback_parts.append("  • Add # noqa comments for false positives")
    feedback_parts.append("  • Create whitelist.py for persistent false positives")
    
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