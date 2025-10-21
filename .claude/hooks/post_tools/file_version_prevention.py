#!/usr/bin/env python3
"""
File Version Prevention PostToolUse Hook
=========================================
Prevents creating versioned files and suggests updating the original instead.

This hook detects versioned file patterns like:
- file_v1.py, file_v2.py
- file_copy.py, file_backup.py
- file (1).py, file (2).py
- file_20240101.py
- file.py.bak, file.py~

Exit codes:
- 0: Success (JSON output controls permission)
- 1: Non-blocking error (invalid input, continues execution)
"""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
from pathlib import Path
from typing import TypedDict, cast


# Type definitions for JSON I/O
class ToolInput(TypedDict, total=False):
    """Tool input structure."""

    file_path: str
    path: str
    content: str


class ToolResponse(TypedDict):
    """Tool response structure."""

    filePath: str
    success: bool


class HookInput(TypedDict):
    """Complete hook input structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput
    tool_response: ToolResponse


class HookSpecificOutput(TypedDict):
    """Hook-specific output structure."""

    hookEventName: str
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """Output JSON structure for PostToolUse."""

    decision: str  # "block" or omit
    reason: str
    hookSpecificOutput: HookSpecificOutput


class FileVersionChecker:
    """Check and prevent file versioning."""

    def __init__(self, project_dir: str) -> None:
        self.project_dir: Path = Path(project_dir)

        # Version patterns (immutable tuples)
        self.version_patterns: tuple[tuple[str, str], ...] = (
            (r"(.+)_v\d+(\.\w+)$", r"\1\2"),  # file_v1.py -> file.py
            (r"(.+)_copy(\.\w+)$", r"\1\2"),  # file_copy.py -> file.py
            (r"(.+)_backup(\.\w+)$", r"\1\2"),  # file_backup.py -> file.py
            (r"(.+)_old(\.\w+)$", r"\1\2"),  # file_old.py -> file.py
            (r"(.+)_new(\.\w+)$", r"\1\2"),  # file_new.py -> file.py
            (r"(.+)\s+\(\d+\)(\.\w+)$", r"\1\2"),  # file (1).py -> file.py
            (r"(.+)_\d{8}(\.\w+)$", r"\1\2"),  # file_20240101.py -> file.py
            (r"(.+)\.bak$", r"\1"),  # file.py.bak -> file.py
            (r"(.+)~$", r"\1"),  # file.py~ -> file.py
        )

        # Patterns to ignore (immutable tuple)
        self.ignore_patterns: tuple[str, ...] = (
            r"test_.*",  # Test files can have versions
            r".*_test\..*",  # Test files
            r".*\.test\..*",  # Test files
            r"migration_.*",  # Migration files often need versions
            r"v\d+_.*",  # Files that start with version (e.g., v1_schema.sql)
        )

    def is_versioned_file(self, file_path: str) -> tuple[bool, Path | None]:
        """
        Check if this is a versioned file and return the original if it exists.

        Returns:
            (is_versioned, original_file_path)
        """
        file_path_obj = Path(file_path)
        file_name = file_path_obj.name

        # Check if this should be ignored

        for ignore_pattern in self.ignore_patterns:
            if re.match(ignore_pattern, file_name):
                return (False, None)

        # Check each version pattern
        for pattern, replacement in self.version_patterns:
            match = re.match(pattern, file_name)
            if match:
                # Get the original filename
                original_name = re.sub(pattern, replacement, file_name)
                original_path = file_path_obj.parent / original_name

                # Check if the original file exists
                if original_path.exists():
                    return (True, original_path)

                # Even if original doesn't exist, this is still a versioned filename
                return (True, None)

        return (False, None)

    def find_similar_files(self, file_path: str) -> list[Path]:
        """Find files with similar names that might be the 'original'."""

        file_path_obj = Path(file_path)
        file_name = file_path_obj.stem  # Get name without extension
        file_ext = file_path_obj.suffix

        similar_files: list[Path] = []

        # Clean the filename of common version indicators
        clean_name = file_name
        patterns_to_clean = (
            r"_v\d+",
            r"_copy",
            r"_backup",
            r"_old",
            r"_new",
            r"_\d{8}",
            r"\s+\(\d+\)",
        )
        for pattern in patterns_to_clean:
            clean_name = re.sub(pattern, "", clean_name)

        # Search in the same directory and parent directory
        search_dirs = [file_path_obj.parent]
        if file_path_obj.parent != self.project_dir:
            search_dirs.append(file_path_obj.parent.parent)

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for existing_file in search_dir.glob(f"*{file_ext}"):
                if existing_file == file_path_obj:
                    continue

                # Calculate similarity
                existing_stem = existing_file.stem
                similarity = difflib.SequenceMatcher(
                    None, clean_name, existing_stem
                ).ratio()

                if similarity > 0.7:  # 70% similarity threshold
                    similar_files.append(existing_file)

        # Sort by similarity
        similar_files.sort(
            key=lambda f: difflib.SequenceMatcher(None, clean_name, f.stem).ratio(),
            reverse=True,
        )

        return similar_files[:3]  # Return top 3 matches

    def suggest_merge_strategy(self, original_file: Path, new_content: str) -> str:
        """Suggest how to merge the new content with the original file."""
        suggestions: list[str] = []

        # Check if original file exists and is readable
        if original_file.exists():
            try:
                original_content = original_file.read_text(encoding="utf-8")

                # Calculate the difference
                differ = difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(original_file),
                    tofile="new_version",
                    n=1,
                )

                diff_lines = list(differ)

                # Analyze the differences
                additions = sum(
                    1
                    for line in diff_lines
                    if line.startswith("+") and not line.startswith("+++")
                )
                deletions = sum(
                    1
                    for line in diff_lines
                    if line.startswith("-") and not line.startswith("---")
                )

                if additions > deletions * 2:
                    suggestions.append(
                        "The new version adds significant functionality. Consider:"
                    )
                    suggestions.append(
                        "- Adding the new functions to the original file"
                    )
                    suggestions.append(
                        "- Creating a new module if the functionality is distinct"
                    )
                elif deletions > additions * 2:
                    suggestions.append(
                        "The new version removes functionality. Consider:"
                    )
                    suggestions.append("- Refactoring the original file instead")
                    suggestions.append("- Deprecating unused functions properly")
                else:
                    suggestions.append(
                        "The new version modifies existing functionality. Consider:"
                    )
                    suggestions.append("- Updating the original file directly")
                    suggestions.append(
                        "- Using feature flags if both versions are needed"
                    )

            except Exception as e:
                suggestions.append(f"Could not analyze original file: {e}")

        return (
            "\n".join(suggestions)
            if suggestions
            else "Consider updating the original file instead of creating a new version."
        )


def main() -> None:
    """Main entry point for PostToolUse hook."""
    try:
        # Read input from stdin
        input_text = sys.stdin.read()
        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)

        # Parse input
        try:
            input_data_raw: object = json.loads(input_text)  # type: ignore[reportUnknownVariableType]
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)

        # Type validation
        if not isinstance(input_data_raw, dict):
            print("Error: Input must be a JSON object", file=sys.stderr)
            sys.exit(1)

        input_dict = cast(dict[str, object], input_data_raw)

        # Extract tool_input
        tool_input_obj = input_dict.get("tool_input")
        if not isinstance(tool_input_obj, dict):
            # No tool_input - skip check
            sys.exit(0)

        tool_input_dict = cast(dict[str, object], tool_input_obj)

        # Extract file_path
        file_path_obj = tool_input_dict.get("file_path") or tool_input_dict.get("path")
        if not isinstance(file_path_obj, str):
            # No file path - skip check
            sys.exit(0)

        file_path = file_path_obj

        # Get project directory
        project_dir = input_dict.get("cwd", os.getcwd())
        if not isinstance(project_dir, str):
            project_dir = os.getcwd()

        # Initialize the checker
        checker = FileVersionChecker(project_dir)

        # Check if this is a versioned file
        is_versioned, original_file = checker.is_versioned_file(file_path)

        if is_versioned:
            feedback_lines: list[str] = ["⚠️  File Versioning Detected\n"]

            if original_file:
                feedback_lines.append("You're creating a version of an existing file:")
                feedback_lines.append(f"  • Original: {original_file.name}")
                feedback_lines.append(f"  • New version: {Path(file_path).name}\n")

                # Get merge suggestions
                content_obj = tool_input_dict.get("content", "")
                new_content = str(content_obj) if isinstance(content_obj, str) else ""

                if new_content:
                    merge_strategy = checker.suggest_merge_strategy(
                        original_file, new_content
                    )
                    feedback_lines.append(f"Suggested approach:\n{merge_strategy}\n")

                feedback_lines.append("Instead of creating a new version:")
                feedback_lines.append(
                    "  1. Update the original file directly using Edit tool"
                )
                feedback_lines.append("  2. Use git branches for experimental changes")
                feedback_lines.append(
                    "  3. Use feature flags for multiple implementations"
                )

            else:
                feedback_lines.append(
                    f"This appears to be a versioned filename: {Path(file_path).name}\n"
                )

                # Find similar files
                similar_files = checker.find_similar_files(file_path)
                if similar_files:
                    feedback_lines.append("Similar existing files found:")
                    for similar in similar_files:
                        feedback_lines.append(f"  • {similar.name}")
                    feedback_lines.append(
                        "\nConsider updating one of these files instead.\n"
                    )

                feedback_lines.append("Best practices:")
                feedback_lines.append("  • Avoid version suffixes (_v2, _copy, _new)")
                feedback_lines.append("  • Use descriptive names that indicate purpose")
                feedback_lines.append(
                    "  • Leverage version control instead of file versions"
                )

            # Create blocking response with JSON output
            output: HookOutput = {
                "decision": "block",
                "reason": "File versioning detected",
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n".join(feedback_lines),
                },
            }
            print(json.dumps(output))
            sys.exit(0)

        # File is not versioned - output success message
        file_name = Path(file_path).name
        success_output: HookOutput = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"✅ File version check passed for {file_name}",
            }
        }
        print(json.dumps(success_output))
        sys.exit(0)

    except Exception as e:
        # Unexpected error - non-blocking
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
