#!/usr/bin/env python3
"""
Check Naming Convention Violations - PreToolUse Hook
=====================================================
Prevents creation of files with poor naming conventions and enforces Python standards.

This hook enforces:
- No .backup, .bak files (use git stash/commits instead)
- No v2, v3, _fixed, _update, _final suffixes (use git branches/tags)
- Python naming conventions for .py files (snake_case, CamelCase, etc.)

Usage:
    python naming_convention_violations.py

Exit codes:
    0: Success (JSON output controls permission)
    1: Non-blocking error (invalid input, continues execution)
"""

import json
import re
import sys
from pathlib import Path
from typing import TypedDict, Literal


class ToolInput(TypedDict, total=False):
    """Type definition for tool input parameters."""
    file_path: str
    path: str
    command: str
    content: str


class HookSpecificOutput(TypedDict):
    """Type definition for hook-specific output."""
    hookEventName: Literal["PreToolUse"]
    permissionDecision: Literal["allow", "deny", "ask"]
    permissionDecisionReason: str


class HookOutput(TypedDict, total=False):
    """Type definition for complete hook output."""
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


def main() -> None:
    """
    Main entry point for the naming convention violations checker.
    
    Reads hook data from stdin and outputs JSON decision.
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
        
        if not isinstance(tool_name_obj, str):
            # Missing tool_name - allow operation
            output_decision("allow", "Missing or invalid tool_name")
            return
        
        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - allow operation
            output_decision("allow", "Invalid tool_input format")
            return
        
        tool_name: str = tool_name_obj
        
        # Create typed tool input
        typed_tool_input = ToolInput()
        
        # Extract relevant fields
        file_path_val = tool_input_obj.get("file_path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(file_path_val, str):
            typed_tool_input["file_path"] = file_path_val
        
        path_val = tool_input_obj.get("path")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(path_val, str):
            typed_tool_input["path"] = path_val
        
        command_val = tool_input_obj.get("command")  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(command_val, str):
            typed_tool_input["command"] = command_val
        
        # Check for naming violations
        violation = check_naming_violations(tool_name, typed_tool_input)
        
        if violation:
            # Deny operation with detailed reason
            output_decision("deny", violation, suppress_output=True)
        else:
            # Allow operation
            output_decision("allow", "Naming conventions are correct")
            
    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def output_decision(
    decision: Literal["allow", "deny", "ask"],
    reason: str,
    suppress_output: bool = False
) -> None:
    """
    Output a properly formatted JSON decision.
    
    Args:
        decision: Permission decision
        reason: Reason for the decision
        suppress_output: Whether to suppress output in transcript mode
    """
    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason
        }
    }
    
    # Only add suppressOutput if it's True
    if suppress_output:
        output["suppressOutput"] = True
    
    try:
        print(json.dumps(output))
        sys.exit(0)  # Success - JSON output controls permission
    except (TypeError, ValueError) as e:
        # Failed to serialize JSON - non-blocking error
        print(f"Error: Failed to serialize output JSON: {e}", file=sys.stderr)
        sys.exit(1)


def check_naming_violations(tool_name: str, tool_input: ToolInput) -> str | None:
    """
    Check for naming convention violations.
    
    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        
    Returns:
        Violation message if found, None otherwise
    """
    # File-based tools
    file_tools = {"Write", "Edit", "MultiEdit"}
    
    if tool_name in file_tools:
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        if file_path:
            # Check for bad version control patterns
            bad_pattern_violation = check_bad_version_patterns(file_path)
            if bad_pattern_violation:
                return bad_pattern_violation
            
            # Check Python naming conventions for .py files
            if file_path.endswith('.py'):
                python_violation = check_python_naming(file_path)
                if python_violation:
                    return python_violation
    
    # Bash/shell commands
    elif tool_name in {"bash", "shell", "bash_tool", "shell_tool"}:
        command = tool_input.get("command", "")
        if command:
            violation = check_command_naming_violations(command)
            if violation:
                return violation
    
    return None


def check_bad_version_patterns(file_path: str) -> str | None:
    """
    Check for bad version control patterns in file names.
    
    Args:
        file_path: Path to check
        
    Returns:
        Violation message if found, None otherwise
    """
    path = Path(file_path)
    name = path.name
    name_lower = name.lower()
    
    # Bad patterns to detect
    bad_patterns = [
        # Backup files
        (r'\.backup$', '.backup', 'backup file'),
        (r'\.bak$', '.bak', 'backup file'),
        (r'\.backup\.', '.backup.', 'backup file'),
        (r'\.bak\.', '.bak.', 'backup file'),
        (r'_backup\.', '_backup.', 'backup file'),
        (r'_bak\.', '_bak.', 'backup file'),
        
        # Version suffixes
        (r'_v\d+(\.|_|$)', 'v2, v3', 'version suffix'),
        (r'_version\d+(\.|_|$)', 'version2', 'version suffix'),
        (r'\.v\d+\.', '.v2.', 'version suffix'),
        
        # Status suffixes
        (r'_fixed(\.|_|$)', '_fixed', 'status suffix'),
        (r'_update(\.|_|$)', '_update', 'status suffix'),
        (r'_updated(\.|_|$)', '_updated', 'status suffix'),
        (r'_final(\.|_|$)', '_final', 'status suffix'),
        (r'_old(\.|_|$)', '_old', 'status suffix'),
        (r'_new(\.|_|$)', '_new', 'status suffix'),
        (r'_temp(\.|_|$)', '_temp', 'temporary file'),
        (r'_tmp(\.|_|$)', '_tmp', 'temporary file'),
        
        # Copy patterns
        (r'_copy(\.|_|$)', '_copy', 'copy suffix'),
        (r' copy(\.|$)', ' copy', 'copy suffix'),
        (r'\(copy\)', '(copy)', 'copy suffix'),
        (r'\(\d+\)', '(1), (2)', 'duplicate number'),
    ]
    
    for pattern, example, description in bad_patterns:
        if re.search(pattern, name_lower):
            return (
                f"📁 Bad naming pattern detected: {description}. \n"
                f"File: {name}. \n"
                f"Pattern like '{example}' violates version control best practices. \n"
                f"Alternative: Use git branches for versions (git checkout -b feature/new-version). \n"
                f"Use git tags for releases (git tag v1.0.0). \n"
                f"Use git stash or commits for temporary saves. \n"
                f"This keeps the working directory clean and history trackable."
            )
    
    return None


def check_python_naming(file_path: str) -> str | None:
    """
    Check Python file naming conventions.
    
    Args:
        file_path: Path to a Python file
        
    Returns:
        Violation message if found, None otherwise
    """
    path = Path(file_path)
    name_without_ext = path.stem
    
    # Skip __init__.py and other dunder files
    if name_without_ext.startswith('__') and name_without_ext.endswith('__'):
        return None
    
    # Check for valid Python module name
    # Should be lowercase with underscores (snake_case)
    # Can start with underscore for private modules
    
    # Check for uppercase letters (except for classes, but file names should be lowercase)
    if any(c.isupper() for c in name_without_ext):
        # Convert CamelCase to snake_case
        example_fix = re.sub(r'(?<!^)(?=[A-Z])', '_', name_without_ext).lower()
        
        return (
            f"🐍 Python file naming violation: Use snake_case for module names. \n"
            f"File: {name_without_ext}.py. \n"
            f"Python modules should use lowercase with underscores. \n"
            f"Suggested: {example_fix}.py. \n"
            f"PEP 8 style: Modules use short, all-lowercase names. \n"
            f"If multiple words needed, separate with underscores."
        )
    
    # Check for hyphens (not allowed in Python module names)
    if '-' in name_without_ext:
        fixed_name = name_without_ext.replace('-', '_')
        return (
            f"🐍 Python file naming violation: Hyphens not allowed in module names. \n"
            f"File: {name_without_ext}.py. \n"
            f"Python module names cannot contain hyphens (breaks imports). \n"
            f"Suggested: {fixed_name}.py. \n"
            f"Use underscores instead of hyphens for word separation."
        )
    
    # Check for spaces (should never happen but just in case)
    if ' ' in name_without_ext:
        fixed_name = name_without_ext.replace(' ', '_').lower()
        return (
            f"🐍 Python file naming violation: Spaces not allowed in module names. \n"
            f"File: {name_without_ext}.py. \n"
            f"Python module names cannot contain spaces. \n"
            f"Suggested: {fixed_name}.py. \n"
            f"Use underscores for word separation."
        )
    
    # Check if starts with a number
    if name_without_ext and name_without_ext[0].isdigit():
        return (
            f"🐍 Python file naming violation: Module names cannot start with a number. \n"
            f"File: {name_without_ext}.py. \n"
            f"Python identifiers must start with a letter or underscore. \n"
            f"Suggested: Add a descriptive prefix like 'module_{name_without_ext}.py'."
        )
    
    return None


def check_command_naming_violations(command: str) -> str | None:
    """
    Check for naming violations in bash commands.
    
    Args:
        command: Bash command to check
        
    Returns:
        Violation message if found, None otherwise
    """
    # Common file creation/manipulation commands
    file_operations = [
        (r'touch\s+([^\s]+)', 'touch'),
        (r'>\s*([^\s]+)', 'redirect'),
        (r'>>\s*([^\s]+)', 'append'),
        (r'cp\s+[^\s]+\s+([^\s]+)', 'copy to'),
        (r'mv\s+[^\s]+\s+([^\s]+)', 'move to'),
        (r'echo\s+.*>\s*([^\s]+)', 'echo to'),
        (r'cat\s+.*>\s*([^\s]+)', 'cat to'),
    ]
    
    for pattern, operation in file_operations:
        match = re.search(pattern, command)
        if match:
            file_path = match.group(1)
            
            # Check for bad patterns
            bad_pattern_violation = check_bad_version_patterns(file_path)
            if bad_pattern_violation:
                # Customize message for bash commands
                display_cmd = command if len(command) <= 60 else command[:57] + "..."
                return (
                    f"📁 Command creates file with bad naming pattern. \n"
                    f"Command: {display_cmd}. \n"
                    f"File: {file_path}. \n"
                    f"Alternative: Use proper git workflow instead. \n"
                    f"Example: git add . \n&& git commit -m 'Save work in progress'. \n"
                    f"Or use: git stash push -m 'Temporary changes'."
                )
            
            # Check Python naming for .py files
            if file_path.endswith('.py'):
                python_violation = check_python_naming(file_path)
                if python_violation:
                    return python_violation
    
    return None


if __name__ == "__main__":
    main()