#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///
"""
Unit tests for utils package __init__.py

Tests that the utils package properly exports all public APIs.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_utils_package_imports_data_types():
    """Test that utils package exports data types."""
    from utils import ToolInput, HookOutput, HookSpecificOutput
    from utils import PermissionDecision, ValidationResult

    # Verify they are accessible
    assert ToolInput is not None
    assert HookOutput is not None
    assert HookSpecificOutput is not None
    assert PermissionDecision is not None
    assert ValidationResult is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
