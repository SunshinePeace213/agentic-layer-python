# PostToolUse Shared Utilities Specification

## Overview

**Feature Name:** PostToolUse Shared Utilities
**Location:** `.claude/hooks/post_tools/utils/`
**Version:** 1.0.0
**Author:** Claude Code Hook Expert
**Created:** 2025-10-30

## Purpose

Provide a standardized, reusable utility library for all PostToolUse hooks in the `post_tools/` category. This mirrors the architecture established for PreToolUse hooks, enabling consistent input parsing, type-safe data handling, and standardized output formatting across all post-tool validation and feedback hooks.

## Problem Statement

### Current Challenges

1. **Code Duplication**: Each PostToolUse hook implements its own input parsing and output formatting
2. **Inconsistent Patterns**: Different hooks use different approaches for handling hook I/O
3. **Type Safety**: No centralized type definitions for PostToolUse input/output schemas
4. **Maintenance Burden**: Changes to hook patterns require updates across multiple files
5. **Learning Curve**: New hooks require developers to understand hook I/O from scratch
6. **Error Handling**: Inconsistent error handling patterns across different hooks

### Impact

- Increased development time for new PostToolUse hooks
- Higher risk of bugs in input parsing and output formatting
- Difficult to maintain consistency across hook implementations
- Harder to evolve hook patterns without breaking existing hooks

## Objectives

### Primary Goals

1. **Centralized Type Definitions**: Provide TypedDict definitions for PostToolUse input/output schemas
2. **Reusable Utilities**: Create shared functions for common operations (parsing, output, validation)
3. **Type Safety**: Enable static type checking with basedpyright/mypy
4. **Consistency**: Ensure all PostToolUse hooks follow the same patterns
5. **Maintainability**: Single source of truth for hook I/O patterns

### Success Criteria

- All PostToolUse hooks use shared utilities (100% adoption)
- Zero code duplication for input parsing and output formatting
- Full type safety with basedpyright --strict
- Clear, documented API for hook developers
- Easy to extend with new utilities as needed

## Architecture Design

### File Structure

```
.claude/hooks/post_tools/
├── utils/
│   ├── __init__.py           # Public API exports
│   ├── data_types.py         # TypedDict definitions
│   └── utils.py              # Shared utility functions
└── <hook_name>.py            # Individual hook implementations
```

### Module Organization

#### `__init__.py` - Public API

**Purpose:** Export all public utilities and types for use by post_tools hooks

**Exports:**
- Type definitions (ToolInput, HookOutput, HookSpecificOutput, etc.)
- Utility functions (parse_hook_input, output_result, output_feedback, etc.)

**Usage Pattern:**
```python
from utils import parse_hook_input, output_feedback, ToolInput
```

#### `data_types.py` - Type Definitions

**Purpose:** Centralized TypedDict definitions for PostToolUse hook schemas

**Type Categories:**
1. **Input Types**: Hook input data from Claude Code
2. **Output Types**: Hook output data to Claude Code
3. **Type Aliases**: Common type aliases for convenience

#### `utils.py` - Utility Functions

**Purpose:** Shared utility functions for common hook operations

**Function Categories:**
1. **Input Parsing**: Parse and validate hook input from stdin
2. **Output Formatting**: Format and output hook responses
3. **Data Extraction**: Extract common fields (file_path, tool_response, etc.)
4. **Validation Helpers**: Common validation patterns

## Data Type Specifications

### Input Data Types

#### `ToolInput` TypedDict

**Purpose:** Type definition for tool input parameters from Claude Code

**Attributes:**
```python
class ToolInput(TypedDict, total=False):
    """Tool-specific input parameters (partial dictionary)."""
    file_path: str          # File path (Read/Write/Edit/MultiEdit tools)
    content: str            # File content (Write tool)
    command: str            # Shell command (Bash tool)
    old_string: str         # String to replace (Edit tool)
    new_string: str         # Replacement string (Edit tool)
    replace_all: bool       # Replace all occurrences (Edit tool)
    pattern: str            # Glob pattern (Glob tool)
    path: str               # Search path (Glob/Grep tools)
```

**Notes:**
- Uses `total=False` to allow partial dictionaries
- Different tools provide different parameter sets
- Hooks can access additional fields directly from raw dict

#### `ToolResponse` TypedDict

**Purpose:** Type definition for tool response from tool execution

**Attributes:**
```python
class ToolResponse(TypedDict, total=False):
    """Tool execution response (varies by tool)."""
    filePath: str           # File path (Write/Edit tools)
    success: bool          # Success status (Write/Edit tools)
    # Note: Different tools return different response structures
    # Use dict[str, Any] for flexibility when parsing
```

**Notes:**
- Structure varies by tool type
- Write tool returns: `{"filePath": "...", "success": true}`
- Read tool may return different structure
- Always check for expected fields with `.get()`

#### `HookInputData` TypedDict

**Purpose:** Complete input data structure received by PostToolUse hooks

**Attributes:**
```python
class HookInputData(TypedDict):
    """Complete hook input from Claude Code via stdin."""
    session_id: str                    # Unique session identifier
    transcript_path: str               # Path to session transcript JSONL
    cwd: str                          # Current working directory
    hook_event_name: Literal["PostToolUse"]  # Hook event name
    tool_name: str                    # Tool that was executed (e.g., "Write", "Bash")
    tool_input: dict[str, Any]        # Tool input parameters (parse into ToolInput)
    tool_response: dict[str, Any]     # Tool execution response (parse into ToolResponse)
```

**Key Differences from PreToolUse:**
- Includes `tool_response`: Result of tool execution (not `tool_output`/`tool_error`)
- Hook runs AFTER tool completes (not before)
- tool_response structure varies by tool type

**Important:** The official schema uses `tool_response` (not `tool_output` or `tool_error`). The tool_response contains the execution result, including success status and any relevant data returned by the tool.

### Output Data Types

#### `HookSpecificOutput` TypedDict

**Purpose:** PostToolUse-specific output structure (nested inside HookOutput)

**Attributes:**
```python
class HookSpecificOutput(TypedDict, total=False):
    """PostToolUse hook-specific output fields."""
    hookEventName: Literal["PostToolUse"]  # Required
    additionalContext: str                 # Optional: Additional info for Claude
```

**Additional Context:**
- Injected into Claude's context for awareness
- Used for feedback, warnings, or informational messages
- Should be concise and actionable

#### `HookOutput` TypedDict

**Purpose:** Complete output structure for PostToolUse hooks

**Attributes:**
```python
class HookOutput(TypedDict, total=False):
    """Complete hook output to Claude Code."""
    decision: Literal["block"]             # Optional: Block Claude's flow
    reason: str                            # Optional: Explanation for decision
    hookSpecificOutput: HookSpecificOutput  # Optional: Event-specific data
    suppressOutput: bool                    # Optional: Hide from transcript
```

**Key Differences from PreToolUse:**
- `decision` is at TOP LEVEL (not inside hookSpecificOutput)
- `reason` is at TOP LEVEL (not permissionDecisionReason inside hookSpecificOutput)
- hookSpecificOutput only contains hookEventName and additionalContext
- All fields except hookEventName are optional

**Decision Field Semantics:**
- **Omitted/undefined**: Non-blocking (default)
- **"block"**: Block Claude's continuation (rare, for critical issues)

**Reason Field:**
- Explanation for the decision (especially important when blocking)
- Displayed to Claude and potentially to the user
- Should be clear and actionable

**Notes:**
- Uses `total=False` because all top-level fields are optional
- suppressOutput hides output in transcript mode (Ctrl-R)

**Important:** The official PostToolUse schema differs from PreToolUse:
- PreToolUse: Everything nested in hookSpecificOutput with permissionDecision
- PostToolUse: decision and reason at top level, simpler hookSpecificOutput

### Type Aliases

```python
# Decision type for PostToolUse hooks
PostToolDecision = Literal["block"] | None

# Validation result (None = passed, str = error message)
ValidationResult = str | None

# Tool response type (flexible for different tools)
ToolResponseType = dict[str, Any]
```

## Utility Function Specifications

### Input Parsing Functions

#### `parse_hook_input()` → `Optional[Tuple[str, ToolInput, dict[str, Any]]]`

**Purpose:** Parse and validate hook input from stdin

**Returns:**
- Tuple of (tool_name, tool_input, tool_response)
- None if parsing fails

**Example:**
```python
result = parse_hook_input()
if result is None:
    output_feedback("")
    return

tool_name, tool_input, tool_response = result
file_path = tool_input.get("file_path", "")
success = tool_response.get("success", True)
```

**Error Handling:**
- Returns None for invalid JSON
- Returns None for missing required fields
- Logs warnings to stderr for debugging

**Note:** tool_response is always a dict (even if empty). Check for expected fields using `.get()` with defaults.

#### `parse_hook_input_minimal()` → `Optional[dict[str, Any]]`

**Purpose:** Parse raw hook input without validation (for advanced usage)

**Returns:**
- Raw dictionary from stdin JSON
- None if JSON parsing fails

**Use Case:**
- Hooks that need access to custom/additional fields
- Debugging and logging hooks

### Output Functions

#### `output_feedback(context: str, suppress_output: bool = False)` → `None`

**Purpose:** Output feedback to Claude without blocking

**Parameters:**
- `context`: Feedback message to inject into Claude's context
- `suppress_output`: Hide from transcript mode

**Behavior:**
- Outputs JSON with additionalContext in hookSpecificOutput
- Does not include decision field (non-blocking)
- Exit code 0

**Output Structure:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "feedback message"
  },
  "suppressOutput": true  // if suppress_output=True
}
```

**Example:**
```python
output_feedback(
    "✅ Ruff formatted file.py: Fixed 3 lint violations",
    suppress_output=True
)
```

#### `output_block(reason: str, additional_context: str = "", suppress_output: bool = False)` → `None`

**Purpose:** Block Claude's continuation with error message

**Parameters:**
- `reason`: Explanation for blocking (goes to top-level reason field)
- `additional_context`: Optional additional info for hookSpecificOutput
- `suppress_output`: Hide from transcript mode

**Behavior:**
- Outputs JSON with decision="block" and reason at TOP LEVEL
- Optionally includes additionalContext in hookSpecificOutput
- Blocks Claude's flow until issue resolved
- Exit code 0

**Output Structure:**
```json
{
  "decision": "block",
  "reason": "explanation for blocking",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "optional additional context"
  },
  "suppressOutput": true  // if suppress_output=True
}
```

**Example:**
```python
output_block(
    reason="❌ Type checking failed with 5 errors. Please fix before continuing.",
    additional_context="Run: basedpyright file.py",
    suppress_output=True
)
```

**Use Case:** Critical validation failures that require user intervention

**Important:** In PostToolUse, decision and reason are at TOP LEVEL, not inside hookSpecificOutput!

#### `output_result(hook_output: HookOutput)` → `None`

**Purpose:** Output raw HookOutput structure (advanced usage)

**Parameters:**
- `hook_output`: Complete HookOutput dictionary

**Example:**
```python
output: HookOutput = {
    "decision": "block",
    "reason": "Critical error detected",
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "Additional info"
    },
    "suppressOutput": True
}
output_result(output)
```

**Note:** Most hooks should use output_feedback() or output_block() instead. This function is for advanced cases requiring full control over the output structure.

### Data Extraction Functions

#### `get_file_path(tool_input: ToolInput)` → `str`

**Purpose:** Extract file path from tool input

**Returns:** File path string (empty if not present)

**Example:**
```python
file_path = get_file_path(tool_input)
if file_path.endswith(".py"):
    validate_python_file(file_path)
```

#### `get_command(tool_input: ToolInput)` → `str`

**Purpose:** Extract command from Bash tool input

**Returns:** Command string (empty if not present)

**Example:**
```python
command = get_command(tool_input)
if "rm -rf" in command:
    output_block("Destructive command blocked")
```

#### `was_tool_successful(tool_response: dict[str, Any])` → `bool`

**Purpose:** Check if tool execution succeeded

**Parameters:**
- `tool_response`: Tool response dictionary

**Returns:** True if success, False otherwise

**Logic:**
- Checks for `success` field in tool_response
- Returns `tool_response.get("success", True)` (default True if not present)

**Example:**
```python
if not was_tool_successful(tool_response):
    # Tool failed, skip validation
    output_feedback("")
    return
```

#### `get_tool_response_field(tool_response: dict[str, Any], field: str, default: Any = None)` → `Any`

**Purpose:** Safely extract a field from tool_response

**Parameters:**
- `tool_response`: Tool response dictionary
- `field`: Field name to extract
- `default`: Default value if field not present

**Returns:** Field value or default

**Example:**
```python
file_path = get_tool_response_field(tool_response, "filePath", "")
success = get_tool_response_field(tool_response, "success", True)
```

### Validation Helper Functions

#### `is_python_file(file_path: str)` → `bool`

**Purpose:** Check if file is a Python file

**Returns:** True if .py or .pyi extension

**Example:**
```python
if is_python_file(file_path):
    run_python_validators(file_path)
```

#### `is_within_project(file_path: str)` → `bool`

**Purpose:** Check if file is within project directory

**Returns:** True if file is within CLAUDE_PROJECT_DIR

**Security:** Prevents path traversal attacks

**Example:**
```python
if not is_within_project(file_path):
    output_feedback("Skipped: File outside project", suppress_output=True)
    return
```

#### `get_project_dir()` → `Path`

**Purpose:** Get absolute path to project directory

**Returns:** Path object for CLAUDE_PROJECT_DIR

**Example:**
```python
project_dir = get_project_dir()
config_file = project_dir / "pyproject.toml"
```

## Implementation Guidelines

### Python Coding Standards

Follow the established patterns from pre_tools/utils:

1. **Module Structure**:
   ```python
   """Module docstring"""

   # Standard library imports
   import json
   import sys

   # Third-party imports (if any)

   # Local imports
   try:
       from .data_types import ToolInput
   except ImportError:
       from data_types import ToolInput
   ```

2. **Type Hints**: Use type annotations for all public functions

3. **Docstrings**: Document all public functions with:
   - Purpose
   - Parameters
   - Returns
   - Examples
   - Error handling

4. **Error Handling**: Fail-safe approach (always exit 0)

5. **Imports**: Support both relative and absolute imports for flexibility

### Type Safety

**Requirements:**
- All code must pass basedpyright --strict
- Use TypedDict for structured data
- Use Literal types for enums
- Use Optional for nullable values
- Use Union (|) for multiple types

**Example:**
```python
def parse_hook_input() -> Optional[Tuple[str, ToolInput, ToolOutput, Optional[str]]]:
    """Parse hook input with full type safety."""
    ...
```

### Security Considerations

1. **Path Validation**:
   - Always validate file paths are within project directory
   - Use `os.path.realpath()` to resolve symlinks
   - Check for `..` in paths

2. **Input Sanitization**:
   - Validate all fields from stdin
   - Type-check before using values
   - Handle malformed JSON gracefully

3. **Command Execution**:
   - Never use shell=True in subprocess
   - Use list arguments for subprocess.run()
   - Validate command paths

4. **Sensitive Files**:
   - Provide helper to check for sensitive file patterns
   - Skip operations on .env, secrets/, etc.

## Testing Strategy

### Unit Tests Location

**Path:** `tests/claude_hook/post_tools/shared_utils/`

**Structure:**
```
tests/claude_hook/post_tools/shared_utils/
├── test_data_types.py      # Type checking tests
├── test_parsing.py         # Input parsing tests
├── test_output.py          # Output formatting tests
└── test_extraction.py      # Data extraction tests
```

### Test Cases

#### Input Parsing Tests

1. **test_parse_valid_input**: Parse complete, valid hook input
2. **test_parse_minimal_input**: Parse minimal valid input
3. **test_parse_invalid_json**: Handle malformed JSON gracefully
4. **test_parse_missing_fields**: Handle missing required fields
5. **test_parse_with_tool_response**: Parse input with various tool_response structures
6. **test_parse_empty_tool_response**: Parse input with empty tool_response dict

#### Output Tests

1. **test_output_feedback**: Verify feedback output format
2. **test_output_block**: Verify blocking output format
3. **test_output_with_suppress**: Verify suppressOutput flag
4. **test_output_json_format**: Verify JSON structure matches schema

#### Data Extraction Tests

1. **test_get_file_path**: Extract file_path from various tool inputs
2. **test_get_command**: Extract command from Bash tool input
3. **test_was_tool_successful**: Check tool success status from tool_response
4. **test_get_tool_response_field**: Extract fields from tool_response safely

#### Validation Helper Tests

1. **test_is_python_file**: Identify Python files correctly
2. **test_is_within_project**: Validate project boundary checks
3. **test_get_project_dir**: Get project directory correctly

### Test Execution

```bash
# Run all util tests
uv run pytest tests/claude_hook/post_tools/shared_utils/ -v

# Run with coverage
uv run pytest tests/claude_hook/post_tools/shared_utils/ --cov=.claude/hooks/post_tools/utils

# Run type checking
uv run basedpyright .claude/hooks/post_tools/utils/
```

## Dependencies

### UV Script Metadata

All hooks using these utilities should declare:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

**Rationale:**
- Python 3.12+ for improved typing features
- No external dependencies (stdlib only)
- Maximum portability and minimal setup

### Required Python Modules

**Standard Library:**
- `json`: Parse stdin and format stdout
- `sys`: stdin/stdout/stderr, exit codes
- `os`: Environment variables, file operations
- `pathlib`: Path manipulation
- `typing`: Type annotations (TypedDict, Literal, Optional)

## Usage Examples

### Example 1: Simple Feedback Hook

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_hook_input, output_feedback, is_python_file, was_tool_successful

def main() -> None:
    result = parse_hook_input()
    if result is None:
        output_feedback("")
        return

    tool_name, tool_input, tool_response = result

    # Skip if tool failed
    if not was_tool_successful(tool_response):
        output_feedback("")
        return

    file_path = tool_input.get("file_path", "")

    # Only process Python files
    if not is_python_file(file_path):
        output_feedback("")
        return

    # Do validation
    message = perform_validation(file_path)

    # Output feedback
    output_feedback(message, suppress_output=True)

if __name__ == "__main__":
    main()
```

### Example 2: Blocking Validation Hook

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_hook_input, output_block, output_feedback, get_file_path

def main() -> None:
    result = parse_hook_input()
    if result is None:
        output_feedback("")
        return

    tool_name, tool_input, tool_response = result

    file_path = get_file_path(tool_input)

    # Run critical validation
    errors = run_critical_validation(file_path)

    if errors:
        # Block Claude's flow with reason at top level
        error_msg = format_error_message(errors)
        output_block(
            reason=error_msg,
            additional_context="Fix these errors before continuing",
            suppress_output=True
        )
    else:
        # Allow continuation with success message
        output_feedback("✅ Validation passed", suppress_output=True)

if __name__ == "__main__":
    main()
```

### Example 3: Tool Response Processing

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    parse_hook_input,
    output_feedback,
    was_tool_successful,
    get_tool_response_field
)

def main() -> None:
    result = parse_hook_input()
    if result is None:
        output_feedback("")
        return

    tool_name, tool_input, tool_response = result

    # Check if tool succeeded
    if not was_tool_successful(tool_response):
        output_feedback("⚠️  Tool execution failed")
        return

    # Process tool response fields
    file_path = get_tool_response_field(tool_response, "filePath", "")
    success = get_tool_response_field(tool_response, "success", True)

    # Analyze based on tool response
    analysis = analyze_tool_response(tool_response, file_path)

    # Provide feedback based on analysis
    output_feedback(analysis, suppress_output=True)

if __name__ == "__main__":
    main()
```

## Integration with Existing Hooks

### Migration Path

Existing PostToolUse hooks should be migrated to use shared utilities:

1. **Phase 1: Create Utils** (Week 1)
   - Implement data_types.py
   - Implement utils.py
   - Implement __init__.py
   - Write unit tests

2. **Phase 2: Migrate Existing Hooks** (Week 2)
   - Update context_bundle_builder.py
   - Migrate any other PostToolUse hooks
   - Test compatibility

3. **Phase 3: New Hooks** (Ongoing)
   - All new hooks use shared utilities
   - Document patterns and examples

### Backward Compatibility

**Guarantee:** Shared utilities will maintain stable API

**Versioning:**
- Semantic versioning for utils module
- Breaking changes require major version bump
- Deprecation warnings for changes

**Testing:** All existing hooks tested after utils changes

## File Structure Details

### `__init__.py` Implementation

```python
#!/usr/bin/env python3
"""
Public API for PostToolUse Shared Utilities
============================================

This module exports the shared utilities and data types used by all
PostToolUse hooks in this category.

Exports:
    - ToolInput: TypedDict for tool input parameters
    - ToolResponse: TypedDict for tool response data
    - HookOutput: TypedDict for hook output structure
    - HookSpecificOutput: TypedDict for PostToolUse output data
    - HookInputData: TypedDict for complete hook input
    - PostToolDecision: Type alias for decision field
    - ValidationResult: Type alias for validation results
    - ToolResponseType: Type alias for tool response
    - parse_hook_input: Parse and validate hook input from stdin
    - parse_hook_input_minimal: Parse raw input without validation
    - output_feedback: Output feedback without blocking
    - output_block: Output blocking decision with reason
    - output_result: Output raw HookOutput
    - get_file_path: Extract file path from tool input
    - get_command: Extract command from tool input
    - was_tool_successful: Check if tool succeeded
    - get_tool_response_field: Extract field from tool response
    - is_python_file: Check if file is Python
    - is_within_project: Check if file is within project
    - get_project_dir: Get project directory path

Usage:
    from utils import parse_hook_input, output_feedback, ToolInput
"""

from .data_types import (
    ToolInput,
    ToolResponse,
    HookOutput,
    HookSpecificOutput,
    HookInputData,
    PostToolDecision,
    ValidationResult,
    ToolResponseType,
)
from .utils import (
    parse_hook_input,
    parse_hook_input_minimal,
    output_feedback,
    output_block,
    output_result,
    get_file_path,
    get_command,
    was_tool_successful,
    get_tool_response_field,
    is_python_file,
    is_within_project,
    get_project_dir,
)

__all__ = [
    # Type definitions
    "ToolInput",
    "ToolResponse",
    "HookOutput",
    "HookSpecificOutput",
    "HookInputData",
    "PostToolDecision",
    "ValidationResult",
    "ToolResponseType",
    # Input parsing
    "parse_hook_input",
    "parse_hook_input_minimal",
    # Output functions
    "output_feedback",
    "output_block",
    "output_result",
    # Data extraction
    "get_file_path",
    "get_command",
    "was_tool_successful",
    "get_tool_response_field",
    # Validation helpers
    "is_python_file",
    "is_within_project",
    "get_project_dir",
]

__version__ = "1.0.0"
```

### `data_types.py` Implementation Outline

```python
#!/usr/bin/env python3
"""
Shared Data Types for PostToolUse Hooks
========================================

Centralized TypedDict definitions used across all PostToolUse hooks.
Ensures consistent input/output formats and type safety.
"""

from typing import TypedDict, Literal, Any

# Input Data Types
class ToolInput(TypedDict, total=False):
    """Tool input parameters (partial dict)."""
    file_path: str
    content: str
    command: str
    old_string: str
    new_string: str
    replace_all: bool
    pattern: str
    path: str

class ToolResponse(TypedDict, total=False):
    """Tool execution response (varies by tool)."""
    filePath: str      # File path (Write/Edit tools)
    success: bool      # Success status (Write/Edit tools)
    # Note: Different tools return different structures

class HookInputData(TypedDict):
    """Complete hook input from stdin."""
    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: dict[str, Any]  # Tool execution response

# Output Data Types
class HookSpecificOutput(TypedDict, total=False):
    """PostToolUse hook-specific output."""
    hookEventName: Literal["PostToolUse"]  # Required
    additionalContext: str                 # Optional

class HookOutput(TypedDict, total=False):
    """Complete hook output."""
    decision: Literal["block"]             # Optional: at TOP LEVEL
    reason: str                            # Optional: at TOP LEVEL
    hookSpecificOutput: HookSpecificOutput  # Optional
    suppressOutput: bool                    # Optional

# Type Aliases
PostToolDecision = Literal["block"] | None
ValidationResult = str | None
ToolResponseType = dict[str, Any]
```

### `utils.py` Implementation Outline

```python
#!/usr/bin/env python3
"""
Shared Utilities for PostToolUse Hooks
=======================================

Common utility functions for PostToolUse hooks.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple, cast

try:
    from .data_types import ToolInput, HookOutput, HookSpecificOutput, ToolResponseType
except ImportError:
    from data_types import ToolInput, HookOutput, HookSpecificOutput, ToolResponseType

# Input parsing functions
def parse_hook_input() -> Optional[Tuple[str, ToolInput, dict[str, Any]]]:
    """Parse and validate hook input from stdin.

    Returns:
        Tuple of (tool_name, tool_input, tool_response) or None
    """
    # Implementation

def parse_hook_input_minimal() -> Optional[dict[str, Any]]:
    """Parse raw hook input without validation."""
    # Implementation

# Output functions
def output_feedback(context: str, suppress_output: bool = False) -> None:
    """Output feedback without blocking.

    Creates hookSpecificOutput with additionalContext.
    """
    # Implementation

def output_block(reason: str, additional_context: str = "", suppress_output: bool = False) -> None:
    """Output blocking decision with reason at top level.

    decision and reason go at TOP LEVEL, not in hookSpecificOutput.
    """
    # Implementation

def output_result(hook_output: HookOutput) -> None:
    """Output raw HookOutput structure."""
    # Implementation

# Data extraction functions
def get_file_path(tool_input: ToolInput) -> str:
    """Extract file path from tool input."""
    # Implementation

def get_command(tool_input: ToolInput) -> str:
    """Extract command from tool input."""
    # Implementation

def was_tool_successful(tool_response: dict[str, Any]) -> bool:
    """Check if tool execution succeeded.

    Returns tool_response.get("success", True).
    """
    # Implementation

def get_tool_response_field(tool_response: dict[str, Any], field: str, default: Any = None) -> Any:
    """Safely extract a field from tool_response."""
    # Implementation

# Validation helper functions
def is_python_file(file_path: str) -> bool:
    """Check if file is a Python file."""
    # Implementation

def is_within_project(file_path: str) -> bool:
    """Check if file is within project directory."""
    # Implementation

def get_project_dir() -> Path:
    """Get project directory path."""
    # Implementation
```

## Success Metrics

### Quantitative Metrics

- **Adoption Rate**: 100% of PostToolUse hooks use shared utilities
- **Code Reduction**: 50%+ reduction in boilerplate code per hook
- **Type Safety**: 100% type checking coverage with basedpyright
- **Test Coverage**: 95%+ code coverage for utils module
- **Performance**: < 50ms overhead for parsing and output

### Qualitative Metrics

- **Developer Experience**: Faster development of new hooks
- **Code Quality**: Consistent patterns across all hooks
- **Maintainability**: Easier to evolve hook patterns
- **Documentation**: Clear examples and API documentation

## Rollout Plan

### Week 1: Implementation
- Day 1-2: Implement data_types.py
- Day 3-4: Implement utils.py
- Day 5: Implement __init__.py and tests

### Week 2: Testing & Documentation
- Day 1-2: Write comprehensive unit tests
- Day 3: Test with example hooks
- Day 4-5: Write documentation and examples

### Week 3: Integration
- Day 1-2: Migrate context_bundle_builder.py
- Day 3-4: Update existing PostToolUse hooks
- Day 5: Integration testing

### Week 4: Deployment
- Day 1-2: Create PR and code review
- Day 3: Merge to main branch
- Day 4-5: Monitor and gather feedback

## Related Specifications

- **Pre-Tools Shared Utils**: `.claude/hooks/pre_tools/utils/` (reference architecture)
- **Ruff Checking Hook**: First PostToolUse hook to use shared utils
- **Context Bundle Builder**: Existing PostToolUse hook to migrate

## References

- [Claude Code Hooks Documentation](https://docs.claude.com/en/docs/claude-code/hooks)
- [UV Scripts Guide](https://docs.astral.sh/uv/guides/scripts/)
- [Python TypedDict Documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)
- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/)

## Version History

- **1.0.0** (2025-10-30): Initial specification
  - Complete architecture design
  - Type definitions for PostToolUse hooks
  - Utility functions for parsing and output
  - Testing strategy and examples
  - Migration plan for existing hooks

## Appendix A: Comparison with PreToolUse Utils

| Aspect | PreToolUse Utils | PostToolUse Utils |
|--------|------------------|-------------------|
| **Input Fields** | tool_name, tool_input | tool_name, tool_input, tool_response |
| **Output Decision Location** | Inside hookSpecificOutput | At top level |
| **Output Decision Field** | permissionDecision ("allow", "deny", "ask") | decision ("block" or omitted) |
| **Output Reason Field** | permissionDecisionReason (inside hookSpecificOutput) | reason (at top level) |
| **Feedback Mechanism** | permissionDecisionReason | additionalContext (inside hookSpecificOutput) |
| **Primary Use Case** | Validate BEFORE tool execution | Feedback AFTER tool execution |
| **Blocking Behavior** | deny = block tool execution | block = pause Claude's flow |
| **Common Pattern** | Validation and blocking | Feedback and post-processing |

**Key Difference:** PostToolUse places `decision` and `reason` at the TOP LEVEL, while PreToolUse nests everything inside `hookSpecificOutput`.

## Appendix B: PostToolUse vs PreToolUse Decision Matrix

| Scenario | PreToolUse | PostToolUse |
|----------|------------|-------------|
| **Validate file naming** | ✅ Deny before write | ❌ Too late |
| **Check code formatting** | ❌ File doesn't exist yet | ✅ Format after write |
| **Block destructive commands** | ✅ Deny before execution | ❌ Too late |
| **Report type errors** | ❌ File doesn't exist yet | ✅ Check after write |
| **Inject context from tool response** | ❌ No response yet | ✅ Use tool_response |
| **Prevent UV violations** | ✅ Deny before write | ❌ Too late |

## Appendix C: Common Patterns

### Pattern 1: Skip Hook Silently

```python
# Skip without any output (silent success)
if not should_process(file_path):
    output_feedback("")
    return
```

### Pattern 2: Provide Non-Blocking Feedback

```python
# Inform Claude of results without blocking
results = analyze_file(file_path)
message = format_results(results)
output_feedback(message, suppress_output=True)
```

### Pattern 3: Block for Critical Issues

```python
# Block Claude's flow for critical issues (decision and reason at top level)
if has_critical_errors(file_path):
    error_msg = "❌ Critical errors found. Please fix before continuing."
    output_block(reason=error_msg, suppress_output=True)
```

### Pattern 4: Process Tool Response

```python
# Use tool response for context
if was_tool_successful(tool_response):
    file_path = get_tool_response_field(tool_response, "filePath", "")
    analysis = analyze_file(file_path)
    output_feedback(analysis, suppress_output=True)
```
