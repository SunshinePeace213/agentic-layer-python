#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Code Similarity Checking Hook
==============================

Prevents duplicate file creation by checking for similar functionality
before allowing Write operations. Encourages Claude to update existing
files directly rather than creating new versioned files.

Purpose:
    Prevent creation of duplicate files with versioned/backup naming patterns
    by detecting similar content before allowing Write operations. Promotes
    Git usage and maintains clean project structure.

Hook Event: PreToolUse
Monitored Tools: Write

Output:
    - JSON with permissionDecision ("allow" or "deny")
    - Educational error messages with Edit tool alternatives
    - Zero external dependencies (uses difflib from stdlib)

Dependencies:
    - Python 3.12+
    - Standard library only (json, sys, os, pathlib, re, difflib)
    - Shared utilities from .claude/hooks/pre_tools/utils

Blocked Patterns:
    - Version suffixes: _v2, _v3, file_v2.py (with high similarity)
    - Copy/backup suffixes: _copy, _backup
    - Number suffixes: file (1).py, file (2).py
    - Date suffixes: file_20240101.py
    - Backup extensions: .bak, .old, .orig (but allows .backup)

Similarity Thresholds:
    - >= 0.85: Very similar (DENY with error message)
    - 0.60-0.85: Moderately similar (ALLOW with warning)
    - < 0.60: Different enough (ALLOW)

Configuration:
    Environment variables:
        - CODE_SIMILARITY_DIRS: Colon-separated monitored directories
        - CODE_SIMILARITY_DENY_THRESHOLD: Threshold for denial (default 0.85)
        - CODE_SIMILARITY_WARN_THRESHOLD: Threshold for warning (default 0.60)
        - CODE_SIMILARITY_ENABLED: Enable/disable hook (default true)

Author: Claude Code Hook Expert
Version: 1.0.0
Last Updated: 2025-10-31
"""

import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import parse_hook_input, output_decision


# ==================== Configuration ====================

# Default similarity thresholds
SIMILARITY_THRESHOLD_DENY = float(
    os.environ.get("CODE_SIMILARITY_DENY_THRESHOLD", "0.85")
)
SIMILARITY_THRESHOLD_WARN = float(
    os.environ.get("CODE_SIMILARITY_WARN_THRESHOLD", "0.60")
)

# Default monitored directories
DEFAULT_MONITORED_DIRS = [
    "./queries",
    "./utils",
    "./components",
    "./src",
    "./lib",
    "./services",
    "./models",
    "./handlers",
    "./.claude/hooks",
    "./tests",
]


# Get monitored directories from environment or use defaults
def get_monitored_dirs() -> list[str]:
    """Get monitored directories from environment or use defaults."""
    dirs_str = os.environ.get("CODE_SIMILARITY_DIRS", "")
    if dirs_str:
        return [d.strip() for d in dirs_str.split(":")]
    return DEFAULT_MONITORED_DIRS


MONITORED_DIRS = get_monitored_dirs()

# Hook enabled/disabled
HOOK_ENABLED = os.environ.get("CODE_SIMILARITY_ENABLED", "true").lower() == "true"

# Version suffix patterns
VERSION_PATTERNS = [
    r"[_-]?v(ersion)?[_-]?\d+$",  # file_v2, file_version2
    r"[_-]\d+$",  # file_2, file-3
    r"\s*\(\d+\)$",  # file (2), file (3)
    r"[_-]\d{8}$",  # file_20240101 (date)
    r"[_-](copy|backup|old|new|final)$",  # file_copy, file_backup
]

# Backup extensions (always block if similar file exists)
BACKUP_EXTENSIONS = [".bak", ".old", ".orig", "~"]

# Allowed extensions (never block, user-requested)
ALLOWED_EXTENSIONS = [".backup"]

# Max file size for similarity checking (1MB)
MAX_FILE_SIZE = 1_048_576


# ==================== Pattern Detection Functions ====================


def detect_versioned_pattern(file_path: str) -> Optional[str]:
    """
    Detect if file name matches versioning/backup pattern.

    Args:
        file_path: Path to the file being checked

    Returns:
        Base file name without version suffix, or None if no pattern detected

    Examples:
        >>> detect_versioned_pattern("utils/parser_v2.py")
        'utils/parser.py'
        >>> detect_versioned_pattern("utils/parser.py")
        None
    """
    path = Path(file_path)
    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    # Check for backup extensions first
    for backup_ext in BACKUP_EXTENSIONS:
        if str(path).endswith(backup_ext):
            # Remove backup extension
            base = str(path).rstrip(backup_ext)
            return base

    # Check for version patterns in stem
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, stem)
        if match:
            # Remove matched version suffix
            base_stem = stem[: match.start()]
            if not base_stem:
                # Avoid empty base names
                return None
            return str(parent / f"{base_stem}{suffix}")

    return None


def is_allowed_extension(file_path: str) -> bool:
    """
    Check if file has an allowed extension (user-requested backups).

    Args:
        file_path: Path to the file being checked

    Returns:
        True if extension is allowed (should skip similarity checking)
    """
    return any(file_path.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def is_in_monitored_directory(file_path: str) -> bool:
    """
    Check if file is in a monitored directory.

    Args:
        file_path: Path to the file being checked

    Returns:
        True if file is in a monitored directory
    """
    # Convert to absolute path relative to project root
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    abs_path = Path(file_path).resolve()

    try:
        # Get relative path to project
        rel_path = abs_path.relative_to(project_dir)
        rel_path_str = f"./{rel_path}"
    except ValueError:
        # File is outside project directory
        return False

    # Check if starts with any monitored directory
    for monitored_dir in MONITORED_DIRS:
        # Normalize monitored_dir path
        if rel_path_str.startswith(monitored_dir) or monitored_dir == ".":
            return True

    return False


# ==================== File Search Functions ====================


def find_similar_files(base_path: str, directory: str) -> list[str]:
    """
    Find existing files with similar base names.

    Args:
        base_path: Base file path without version suffix
        directory: Directory to search in

    Returns:
        List of file paths that might be duplicates

    Examples:
        >>> find_similar_files("utils/parser.py", "utils")
        ['utils/parser.py', 'utils/parser_old.py']
    """
    similar_files: list[str] = []

    base_name = Path(base_path).stem
    base_suffix = Path(base_path).suffix
    dir_path = Path(directory)

    if not dir_path.exists():
        return similar_files

    # Search for files with similar base names
    pattern = f"{base_name}*{base_suffix}"

    try:
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                similar_files.append(str(file_path))
    except (OSError, PermissionError):
        # Ignore errors accessing directories
        pass

    return similar_files


# ==================== Similarity Calculation Functions ====================


def calculate_similarity(content1: str, content2: str) -> float:
    """
    Calculate content similarity ratio (0.0 to 1.0).

    Uses Python's difflib.SequenceMatcher for reliable string comparison.

    Args:
        content1: First file content
        content2: Second file content

    Returns:
        Similarity ratio (0.0 = completely different, 1.0 = identical)

    Examples:
        >>> calculate_similarity("hello world", "hello world")
        1.0
        >>> calculate_similarity("hello", "goodbye")
        < 0.3
    """
    matcher = SequenceMatcher(None, content1, content2)
    return matcher.ratio()


def quick_similarity_check(content1: str, content2: str) -> Optional[float]:
    """
    Quick pre-check before full similarity calculation.

    Optimizes performance by detecting obviously different or identical files
    without running full SequenceMatcher.

    Args:
        content1: First file content
        content2: Second file content

    Returns:
        Similarity score if can be determined quickly, None if needs full check

    Examples:
        >>> quick_similarity_check("x" * 1000, "y" * 100)  # Very different size
        0.0
        >>> quick_similarity_check("same", "same")  # Identical
        1.0
    """
    # Quick check: identical content
    if content1 == content2:
        return 1.0

    # Quick check: very different lengths
    len1 = len(content1)
    len2 = len(content2)

    if len1 == 0 or len2 == 0:
        return 0.0

    # If length difference > 30%, likely very different
    length_ratio = abs(len1 - len2) / max(len1, len2)
    if length_ratio > 0.3:
        return 0.0

    # Check first/last 100 characters for quick identical detection
    sample_size = min(100, len1, len2)
    if (
        content1[:sample_size] == content2[:sample_size]
        and content1[-sample_size:] == content2[-sample_size:]
    ):
        # Likely identical, run full check
        return None

    # Needs full check
    return None


def get_file_content(file_path: str) -> Optional[str]:
    """
    Read file content safely with size limit.

    Args:
        file_path: Path to file to read

    Returns:
        File content as string, or None if cannot read/too large
    """
    try:
        path = Path(file_path)

        # Check file size
        if path.stat().st_size > MAX_FILE_SIZE:
            return None

        # Read content
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return None


# ==================== Main Validation Logic ====================


def validate_write_operation(file_path: str, content: str) -> Optional[str]:
    """
    Validate Write operation against similarity rules.

    Args:
        file_path: Path where file will be created
        content: Content to be written

    Returns:
        None if allowed, error message string if denied

    Process:
        1. Check if hook is enabled
        2. Check if file is in monitored directory
        3. Check if file has allowed extension
        4. Detect versioned pattern
        5. Find similar files
        6. Calculate similarity
        7. Return denial message if too similar
    """
    # Check if hook is enabled
    if not HOOK_ENABLED:
        return None

    # Check if file is in monitored directory
    if not is_in_monitored_directory(file_path):
        return None

    # Check if file has allowed extension (user-requested backup)
    if is_allowed_extension(file_path):
        return None

    # Detect versioned pattern
    base_path = detect_versioned_pattern(file_path)
    if not base_path:
        # No versioned pattern detected, allow
        return None

    # Find similar files in same directory
    directory = str(Path(file_path).parent)
    similar_files = find_similar_files(base_path, directory)

    # Check similarity with each similar file
    for similar_file in similar_files:
        # Skip checking against self
        if Path(similar_file).resolve() == Path(file_path).resolve():
            continue

        # Get existing file content
        existing_content = get_file_content(similar_file)
        if existing_content is None:
            continue

        # Quick similarity check first
        quick_sim = quick_similarity_check(content, existing_content)
        if quick_sim is not None:
            similarity = quick_sim
        else:
            # Full similarity calculation
            similarity = calculate_similarity(content, existing_content)

        # Check if too similar
        if similarity >= SIMILARITY_THRESHOLD_DENY:
            # Create educational error message
            return create_similarity_error_message(file_path, similar_file, similarity)

    # All checks passed, allow
    return None


# ==================== Error Messages ====================


def create_similarity_error_message(
    new_file: str, existing_file: str, similarity: float
) -> str:
    """
    Create detailed error message for duplicate file detection.

    Args:
        new_file: Path to new file being created
        existing_file: Path to existing similar file
        similarity: Similarity ratio (0.0 to 1.0)

    Returns:
        Formatted error message with recommendations
    """
    similarity_pct = int(similarity * 100)

    return f"""🔍 Duplicate File Detected

Attempted to create: {new_file}
Similar file exists: {existing_file} ({similarity_pct}% similar)

Why this is blocked:
  • Creates confusion about which file is current
  • Duplicates code instead of improving existing implementation
  • Bypasses version control best practices
  • Makes codebase harder to maintain

✅ Recommended action:
  Update the existing file instead:

  Edit(
    file_path='{existing_file}',
    old_string='<existing implementation>',
    new_string='<improved implementation>'
  )

📚 Alternative approaches:
  • Use git branches: git checkout -b feature/improvements
  • Use git commits: git commit -m "refactor: improve implementation"
  • If truly different functionality, use descriptive name (not versioning)

Learn more: https://git-scm.com/docs/git-branch"""


# ==================== Main Entry Point ====================


def main() -> None:
    """
    Main hook execution logic.

    Process:
        1. Parse input from stdin
        2. Extract tool name and parameters
        3. Validate Write operation for similarity
        4. Output decision (allow or deny)

    Error Handling:
        All exceptions result in "allow" decision (fail-safe)
    """
    try:
        # Parse input from stdin
        result = parse_hook_input()
        if result is None:
            # Parse failed, fail-safe: allow
            output_decision("allow", "Failed to parse input (fail-safe)")
            return

        tool_name, tool_input = result

        # Only validate Write operations
        if tool_name != "Write":
            output_decision(
                "allow",
                "Not a Write operation (skip similarity check)",
                suppress_output=True,
            )
            return

        # Extract file path and content
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")

        if not file_path or not content:
            # Missing required fields, fail-safe: allow
            output_decision(
                "allow",
                "Missing file_path or content (fail-safe)",
                suppress_output=True,
            )
            return

        # Validate write operation
        error_message = validate_write_operation(file_path, content)

        # Output decision
        if error_message:
            # Validation failed: deny with educational message
            output_decision("deny", error_message, suppress_output=False)
        else:
            # Validation passed: allow
            output_decision(
                "allow",
                "No similar files found or content is sufficiently different",
                suppress_output=True,
            )

    except Exception as e:
        # Unexpected error: fail-safe, allow operation
        print(f"Code similarity checking error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (fail-safe): {e}", suppress_output=True)


if __name__ == "__main__":
    main()
