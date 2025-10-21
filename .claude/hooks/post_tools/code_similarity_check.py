#!/usr/bin/env python3
"""
Duplicate Detection PostToolUse Hook
====================================
Prevents duplicate code/queries by checking for similar functionality
before allowing file modifications in monitored directories.

This hook monitors directories like ./queries, ./utils, ./components and
checks if similar functionality already exists before allowing modifications.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast


# Type definitions for JSON I/O
class ToolInput(TypedDict, total=False):
    """Tool input structure for Write/Edit operations."""

    file_path: str
    content: str  # For Write
    old_str: str  # For Edit
    new_str: str  # For Edit
    edits: list[dict[str, str]]  # For MultiEdit


class InputData(TypedDict):
    """Complete input data structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput


class HookSpecificOutput(TypedDict):
    """Hook-specific output structure."""

    hookEventName: str
    additionalContext: str


class OutputData(TypedDict, total=False):
    """Output JSON structure for PostToolUse."""

    permissionDecision: str  # "approve", "deny", or "prompt"
    reason: str
    hookSpecificOutput: HookSpecificOutput
    suppressOutput: bool


@dataclass
class FunctionSignature:
    """Represents a function or query signature for comparison."""

    name: str
    file_path: str
    line_number: int
    params: list[str]
    return_type: str | None
    docstring: str | None
    body_hash: str | None


class DuplicateDetector:
    """Detects duplicate or similar functions/queries in a codebase."""

    def __init__(self, base_dir: str, monitored_dirs: list[str]) -> None:
        self.base_dir = Path(base_dir)
        self.monitored_dirs = [self.base_dir / d for d in monitored_dirs]
        self.existing_functions: list[FunctionSignature] = []

    def scan_existing_code(self) -> None:
        """Scan monitored directories for existing functions/queries."""
        for dir_path in self.monitored_dirs:
            if not dir_path.exists():
                continue

            for file_path in dir_path.rglob("*.py"):
                self._extract_functions_from_file(file_path)

            for file_path in dir_path.rglob("*.ts"):
                self._extract_typescript_functions(file_path)

            for file_path in dir_path.rglob("*.sql"):
                self._extract_sql_queries(file_path)

    def _extract_functions_from_file(self, file_path: Path) -> None:
        """Extract Python function signatures from a file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    signature = self._create_function_signature(node, file_path)
                    self.existing_functions.append(signature)
        except Exception:
            # Skip files that can't be parsed
            pass

    def _extract_typescript_functions(self, file_path: Path) -> None:
        """Extract TypeScript function signatures using regex patterns."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Pattern for TypeScript functions
            patterns = [
                r"export\s+(?:async\s+)?function\s+(\w+)\s*\([^)]*\)",
                r"const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::|=>)",
                r"(?:public|private|protected)\s+(?:async\s+)?(\w+)\s*\([^)]*\)",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    func_name = match.group(1)
                    line_num = content[: match.start()].count("\n") + 1

                    signature = FunctionSignature(
                        name=func_name,
                        file_path=str(file_path),
                        line_number=line_num,
                        params=[],
                        return_type=None,
                        docstring=None,
                        body_hash=None,
                    )
                    self.existing_functions.append(signature)
        except Exception:
            pass

    def _extract_sql_queries(self, file_path: Path) -> None:
        """Extract SQL query names from files."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Pattern for common SQL query function patterns
            patterns = [
                r"(?:CREATE|REPLACE)\s+FUNCTION\s+(\w+)",
                r"(?:const|let|var)\s+(\w+Query)\s*=",
                r"def\s+(\w+_query)\s*\(",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    query_name = match.group(1)
                    line_num = content[: match.start()].count("\n") + 1

                    signature = FunctionSignature(
                        name=query_name,
                        file_path=str(file_path),
                        line_number=line_num,
                        params=[],
                        return_type=None,
                        docstring=None,
                        body_hash=None,
                    )
                    self.existing_functions.append(signature)
        except Exception:
            pass

    def _create_function_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path
    ) -> FunctionSignature:
        """Create a function signature from an AST node."""
        # Extract parameters
        params: list[str] = []
        for arg in node.args.args:
            params.append(arg.arg)

        # Extract return type if available
        return_type = None
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except Exception:
                return_type = None

        # Extract docstring
        docstring = ast.get_docstring(node)

        return FunctionSignature(
            name=node.name,
            file_path=str(file_path),
            line_number=node.lineno,
            params=params,
            return_type=return_type,
            docstring=docstring,
            body_hash=None,
        )

    def find_similar_functions(
        self, new_content: str, file_path: str
    ) -> list[FunctionSignature]:
        """Find functions similar to those in the new content."""
        similar_functions: list[FunctionSignature] = []

        # Extract function names from new content
        new_func_names = self._extract_function_names_from_content(new_content)

        # Check for similar names in existing functions
        for new_name in new_func_names:
            for existing in self.existing_functions:
                if self._are_names_similar(new_name, existing.name):
                    # Don't flag if it's in the same file (likely an update)
                    if not file_path.endswith(Path(existing.file_path).name):
                        similar_functions.append(existing)

        return similar_functions

    def _extract_function_names_from_content(self, content: str) -> list[str]:
        """Extract function names from content string."""
        names: list[str] = []

        # Try Python parsing first
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.append(node.name)
        except Exception:
            # If not Python, try regex patterns
            patterns = [
                r"(?:function|def|const|let|var)\s+(\w+)",
                r"(\w+)\s*(?:=|:)\s*(?:async\s+)?\([^)]*\)\s*(?:=>|{)",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    names.append(match.group(1))

        return names

    def _are_names_similar(self, name1: str, name2: str) -> bool:
        """Check if two function names are similar."""
        # Exact match
        if name1.lower() == name2.lower():
            return True

        # Check if one contains the other (with some minimum length)
        if len(name1) > 5 and len(name2) > 5:
            if name1.lower() in name2.lower() or name2.lower() in name1.lower():
                return True

        # Check for common patterns (e.g., getPendingOrders vs fetchPendingOrders)
        common_prefixes = ["get", "fetch", "load", "find", "search", "query"]
        for prefix in common_prefixes:
            if name1.lower().startswith(prefix) and name2.lower().startswith(prefix):
                # Compare the rest of the name
                rest1 = name1[len(prefix) :].lower()
                rest2 = name2[len(prefix) :].lower()
                if rest1 == rest2:
                    return True

        return False


def check_for_duplicates(
    tool_name: str, tool_input: ToolInput, cwd: str, monitored_dirs: list[str]
) -> OutputData | None:
    """Check if the file modification would create duplicate functionality."""

    # Only check for Write/Edit/MultiEdit operations
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        return None

    # Extract file path
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None

    # Check if file is in a monitored directory
    file_path_obj = Path(file_path)
    is_monitored = False

    for monitored_dir in monitored_dirs:
        monitored_path = Path(cwd) / monitored_dir
        try:
            file_path_obj.resolve().relative_to(monitored_path.resolve())
            is_monitored = True
            break
        except (ValueError, OSError):
            continue

    if not is_monitored:
        return None

    # Extract content to be written
    new_content = ""
    if tool_name == "Write":
        new_content = tool_input.get("content", "")
    elif tool_name == "Edit":
        new_content = tool_input.get("new_str", "")
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        new_content = "\n".join(edit.get("new_str", "") for edit in edits)

    if not new_content:
        return None

    # Initialize duplicate detector
    detector = DuplicateDetector(cwd, monitored_dirs)
    detector.scan_existing_code()

    # Find similar functions
    similar_functions = detector.find_similar_functions(new_content, file_path)

    if similar_functions:
        # Format the feedback
        feedback_lines: list[str] = ["🔍 Potential duplicate functionality detected!\n"]
        feedback_lines.append("The following similar functions already exist:\n")

        for func in similar_functions[:5]:  # Limit to 5 suggestions
            feedback_lines.append(
                f"  • {func.name}() in {Path(func.file_path).name} (line {func.line_number})"
            )
            if func.docstring:
                # Add first line of docstring
                first_line = func.docstring.split("\n")[0][:60]
                feedback_lines.append(f"    → {first_line}")

        feedback_lines.append("\n💡 Suggestions:")
        feedback_lines.append("  1. Review if you can reuse the existing function")
        feedback_lines.append(
            "  2. If this is an intentional replacement, consider removing the old one"
        )
        feedback_lines.append(
            "  3. If they serve different purposes, consider more distinct naming"
        )

        return {
            "permissionDecision": "prompt",
            "reason": "Potential duplicate functionality detected",
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(feedback_lines),
            },
        }

    return None


def main() -> None:
    """Main entry point for PostToolUse hook."""
    # Configuration - customize these for your project
    MONITORED_DIRS = [
        "queries",
        "src/queries",
        "lib/queries",
        "utils",
        "src/utils",
        "lib/utils",
        "components",
        "src/components",
    ]

    try:
        # Read JSON input from stdin
        input_text = sys.stdin.read()
        if not input_text:
            sys.exit(0)

        # Parse input
        try:
            input_data_raw: object = json.loads(input_text)  # type: ignore[no-any-expr]
        except json.JSONDecodeError:
            sys.exit(0)

        # Type validation
        if not isinstance(input_data_raw, dict):
            sys.exit(0)

        input_dict = cast(dict[str, object], input_data_raw)

        # Extract tool_name
        tool_name_obj = input_dict.get("tool_name", "")
        tool_name = str(tool_name_obj) if isinstance(tool_name_obj, str) else ""

        # Extract tool_input
        tool_input_obj = input_dict.get("tool_input")
        if not isinstance(tool_input_obj, dict):
            sys.exit(0)

        tool_input_dict = cast(dict[str, object], tool_input_obj)

        # Extract cwd
        cwd_obj = input_dict.get("cwd", "")
        cwd = str(cwd_obj) if isinstance(cwd_obj, str) else os.getcwd()

        # Convert tool_input to proper type
        tool_input = cast(ToolInput, tool_input_dict)

        # Check for duplicates
        result = check_for_duplicates(tool_name, tool_input, cwd, MONITORED_DIRS)

        if result:
            print(json.dumps(result))
            sys.exit(0)

        # No duplicates found - output success message
        file_path = tool_input.get("file_path", "")
        if file_path:
            file_name = Path(file_path).name
            success_output: OutputData = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"✅ Code similarity check passed for {file_name}",
                }
            }
            print(json.dumps(success_output))

        sys.exit(0)

    except Exception:
        # On any error, don't block the operation
        sys.exit(0)


if __name__ == "__main__":
    main()
