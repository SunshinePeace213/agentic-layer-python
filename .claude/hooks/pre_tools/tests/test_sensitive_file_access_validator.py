#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pytest>=7.0.0",
# ]
# ///

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_types import ToolInput
from sensitive_file_access_validator import validate_file_operation


class TestValidateFileOperation:
    """Test file operation validation."""

    def test_blocks_env_file_read(self):
        """Should block reading .env files."""
        tool_input: ToolInput = {"file_path": "/project/.env"}
        violation = validate_file_operation("Read", tool_input)
        assert violation is not None
        assert "environment variables" in violation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
