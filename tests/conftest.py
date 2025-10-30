"""
Pytest configuration for Claude Code hook tests.

Sets up import paths to allow tests to import from .claude/hooks directories.
"""

import sys
from pathlib import Path

# Add .claude/hooks/ paths to Python path for importing shared utilities
project_root = Path(__file__).parent.parent.resolve()
pre_tools_path = project_root / ".claude" / "hooks" / "pre_tools"
post_tools_path = project_root / ".claude" / "hooks" / "post_tools"

if str(pre_tools_path) not in sys.path:
    sys.path.insert(0, str(pre_tools_path))

if str(post_tools_path) not in sys.path:
    sys.path.insert(0, str(post_tools_path))