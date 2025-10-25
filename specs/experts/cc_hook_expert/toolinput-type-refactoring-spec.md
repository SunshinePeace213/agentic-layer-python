# ToolInput Type Refactoring Specification

## Overview

**Purpose**: Refactor the shared `ToolInput` TypedDict in `utils/data_types.py` to only include fields that are universally required across all PreToolUse hooks, removing optional fields that are tool-specific.

**Rationale**: The current `ToolInput` TypedDict includes four fields (`command`, `file_path`, `path`, `content`), but analysis shows that:
- The shared utility function `parse_hook_input()` only populates `file_path` and `content`
- Most hooks parse input directly and use `dict[str, str]` for raw tool_input data
- Including tool-specific fields in the shared type creates confusion about what is truly required

**Objectives**:
1. Simplify the shared `ToolInput` type to only contain universally required fields
2. Maintain backward compatibility for hooks that access fields via `.get()`
3. Update tests to reflect the new type definition
4. Document the pattern for hooks that need additional fields

---

## Current State Analysis

### Current ToolInput Definition
Located in `.claude/hooks/pre_tools/utils/data_types.py:25-48`:

```python
class ToolInput(TypedDict, total=False):
    """
    Type definition for tool input parameters from Claude Code.

    Uses total=False to allow partial dictionaries since different
    tools provide different sets of parameters.

    Attributes:
        command: Shell command string (for Bash tool)
        file_path: File path (for Read/Write/Edit/MultiEdit tools)
        path: Alternative path field (for some tools like Glob)
        content: File content string (for Write tool)
    """
    command: str
    file_path: str
    path: str
    content: str
```

### Current parse_hook_input() Implementation
Located in `.claude/hooks/pre_tools/utils/utils.py:18-32`:

```python
def parse_hook_input() -> Optional[Tuple[str, ToolInput]]:
    """Parse and validate hook input from stdin."""
    input_text = sys.stdin.read()
    parsed_json: dict[str, Any] = json.loads(input_text)

    tool_name: str = parsed_json.get("tool_name", "")
    tool_input_obj: dict[str, Any] = parsed_json.get("tool_input", {})

    typed_tool_input = ToolInput()
    if "file_path" in tool_input_obj:
        typed_tool_input["file_path"] = tool_input_obj["file_path"]
    if "content" in tool_input_obj:
        typed_tool_input["content"] = tool_input_obj["content"]

    return (tool_name, typed_tool_input)
```

**Note**: Only `file_path` and `content` are populated.

### Field Usage Analysis

**Files using `command` field** (9 occurrences):
- `.claude/hooks/pre_tools/sensitive_file_access_validator.py:93`
- `.claude/hooks/pre_tools/uv_dependency_blocker.py:109, 179`
- `.claude/hooks/pre_tools/file_naming_enforcer.py:107, 189`
- `.claude/hooks/pre_tools/tmp_creation_blocker.py:106, 190`
- `.claude/hooks/pre_tools/destructive_command_blocker.py:30-34` (defines own ToolInput)
- `.claude/hooks/pre_tools/tests/test_data_types.py:36`

**Files using `path` field** (11 occurrences):
- `.claude/hooks/pre_tools/uv_dependency_blocker.py:105, 188`
- `.claude/hooks/pre_tools/file_naming_enforcer.py:103, 174`
- `.claude/hooks/pre_tools/tmp_creation_blocker.py:102, 172`
- `.claude/hooks/post_tools/unified_python_antipattern_hook.py:114`
- `.claude/hooks/post_tools/formatting/basedpyright_checking.py:158`
- `.claude/hooks/post_tools/formatting/vulture_checking.py:129`
- `.claude/hooks/pre_tools/tests/test_data_types.py:38`

**Pattern observed**: Hooks typically use fallback pattern:
```python
file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
```

This suggests they work with the raw `dict[str, str]` from `tool_input_obj`, not the typed `ToolInput`.

---

## Proposed Changes

### 1. Update ToolInput TypedDict

**File**: `.claude/hooks/pre_tools/utils/data_types.py:25-48`

**Change**:
```python
class ToolInput(TypedDict, total=False):
    """
    Type definition for tool input parameters from Claude Code.

    This represents the SHARED fields used by the parse_hook_input() utility.
    Individual hooks may access additional fields directly from tool_input_obj.

    Uses total=False to allow partial dictionaries since different
    tools provide different sets of parameters.

    Attributes:
        file_path: File path (for Read/Write/Edit/MultiEdit tools)
        content: File content string (for Write tool)

    Note:
        Hooks that need additional fields (e.g., 'command' for Bash validation,
        'path' for Glob operations) should access them directly from the raw
        tool_input dict using .get(), or define their own extended TypedDict.

    Example:
        >>> tool_input: ToolInput = {
        ...     "file_path": "/path/to/file.py",
        ...     "content": "print('hello')"
        ... }
    """
    file_path: str
    content: str
```

**Rationale**:
- Only includes fields populated by `parse_hook_input()`
- Clarifies that hooks needing other fields should use raw dict access
- Maintains `total=False` for partial dictionaries

### 2. Update Test File

**File**: `.claude/hooks/pre_tools/tests/test_data_types.py`

**Changes**:

1. Remove test for `command` and `path` fields (lines 28-39):
```python
def test_tool_input_accepts_required_fields():
    """Test that ToolInput accepts required fields."""
    tool_input: ToolInput = {
        "file_path": "/path/to/file",
        "content": "file content"
    }
    assert tool_input["file_path"] == "/path/to/file"
    assert tool_input["content"] == "file content"
```

2. Add test for extended usage pattern:
```python
def test_tool_input_extended_usage():
    """Test that hooks can extend ToolInput with additional fields via dict."""
    # Raw tool_input_obj from Claude Code can have any fields
    raw_tool_input: dict[str, str] = {
        "command": "ls -la",
        "file_path": "/path/to/file",
        "path": "/alternative/path",
        "content": "file content"
    }

    # Hooks access additional fields via .get()
    assert raw_tool_input.get("command") == "ls -la"
    assert raw_tool_input.get("path") == "/alternative/path"

    # Shared ToolInput only includes core fields
    typed_input: ToolInput = {
        "file_path": raw_tool_input["file_path"],
        "content": raw_tool_input["content"]
    }
    assert typed_input["file_path"] == "/path/to/file"
```

3. Keep existing `test_tool_input_partial_dictionary` test (lines 42-46) but update assertions:
```python
def test_tool_input_partial_dictionary():
    """Test that ToolInput allows partial dictionaries (total=False)."""
    tool_input: ToolInput = {"file_path": "/path/to/file"}
    assert "file_path" in tool_input
    assert "content" not in tool_input
```

### 3. No Changes Required for Hooks

**Rationale**: All hooks that currently access `command` or `path` do so via:
```python
command = tool_input.get("command", "")
path = tool_input.get("path", "")
```

Since they use `.get()` on the raw dictionary, removing these fields from the TypedDict won't break functionality. The hooks work with `dict[str, str]` at runtime, and TypedDict is only for static type checking.

### 4. Optional: Update Hooks with Local TypedDict (Future Enhancement)

Hooks that frequently use `command` field could define their own extended type:

**Example** (`.claude/hooks/pre_tools/destructive_command_blocker.py` already does this):
```python
class ExtendedToolInput(TypedDict, total=False):
    """Extended tool input with command field for Bash validation."""
    command: str
    file_path: str
    content: str
```

**Not required for this refactoring** but could improve type safety in the future.

---

## Implementation Steps

### Step 1: Update ToolInput in data_types.py
- Remove `command` and `path` fields
- Update docstring to clarify shared vs. hook-specific fields
- Add note about extending via raw dict access

### Step 2: Update Test File
- Remove test assertions for `command` and `path`
- Add test for extended usage pattern
- Update existing test to match new field set
- Run tests to verify: `uv run pytest .claude/hooks/pre_tools/tests/test_data_types.py -v`

### Step 3: Verification
- Run all hook tests to ensure no breakage
- Verify hooks still function correctly with Claude Code
- Check type checking passes: `uv run pyright .claude/hooks/pre_tools/`

### Step 4: Documentation Update
- Update any hook documentation mentioning ToolInput structure
- Add comment in hooks that use extended fields explaining the pattern

---

## Testing Strategy

### Unit Tests

1. **Test ToolInput structure** (test_data_types.py)
   - Verify only `file_path` and `content` are in type
   - Test partial dictionaries work correctly
   - Test extended usage pattern with raw dicts

2. **Test parse_hook_input()** (test_utils.py)
   - Verify only `file_path` and `content` are parsed
   - Test with input containing `command` and `path` (should be ignored)
   - Verify output type matches new ToolInput definition

### Integration Tests

1. **Test hooks with command field**
   - `sensitive_file_access_validator.py` - Test Bash command validation
   - `destructive_command_blocker.py` - Test dangerous command blocking
   - Verify they still access `command` via `.get()` successfully

2. **Test hooks with path field**
   - `uv_dependency_blocker.py` - Test fallback pattern
   - Verify `file_path` or `path` resolution still works

### Test Commands

```bash
# Run unit tests
uv run pytest .claude/hooks/pre_tools/tests/test_data_types.py -v
uv run pytest .claude/hooks/pre_tools/tests/test_utils.py -v

# Run type checking
uv run pyright .claude/hooks/pre_tools/

# Run all hook tests
uv run pytest .claude/hooks/pre_tools/tests/ -v
uv run pytest .claude/hooks/post_tools/tests/ -v  # If exists
```

---

## Security Considerations

### No Security Impact

This refactoring has **zero security impact** because:

1. **Runtime behavior unchanged**: Hooks access fields via `.get()` on raw dicts, which is unaffected by TypedDict changes
2. **No data flow changes**: Input parsing, validation, and output remain identical
3. **No permission changes**: Hook permission decisions are based on runtime values, not types
4. **Type safety improvement**: Removing unused fields from shared type reduces confusion

### Validation Still Works

All security validations remain intact:
- Sensitive file blocking
- Destructive command prevention
- Path traversal checks
- System directory protection

---

## Error Handling

### Potential Issues and Mitigations

1. **Type checker errors in hooks**
   - **Issue**: Static type checkers might flag access to `command` or `path` on ToolInput
   - **Mitigation**: Hooks already use raw `dict[str, str]` for tool_input_obj, not ToolInput
   - **Verification**: Run pyright on all hooks after change

2. **Test failures**
   - **Issue**: Existing tests assert on removed fields
   - **Mitigation**: Update tests to match new structure (Step 2)
   - **Verification**: Run pytest on all test files

3. **Hook breakage**
   - **Issue**: Hook might depend on ToolInput having all fields
   - **Mitigation**: Analysis shows no hooks construct ToolInput with these fields
   - **Verification**: Test hooks in Claude Code environment

### Rollback Strategy

If issues arise:
1. Revert `utils/data_types.py` to previous version
2. Revert `tests/test_data_types.py` to previous version
3. All hooks will continue working as before

Git rollback command:
```bash
git checkout HEAD -- .claude/hooks/pre_tools/utils/data_types.py
git checkout HEAD -- .claude/hooks/pre_tools/tests/test_data_types.py
```

---

## Files to Modify

### Required Changes

1. `.claude/hooks/pre_tools/utils/data_types.py` - Update ToolInput TypedDict
2. `.claude/hooks/pre_tools/tests/test_data_types.py` - Update tests

### No Changes Required

The following files reference ToolInput but require **no changes**:

**Pre-Tools Hooks**:
- `sensitive_file_access_validator.py` - Uses `.get("command")` on raw dict
- `uv_dependency_blocker.py` - Uses `.get("command")` and `.get("path")` on raw dict
- `file_naming_enforcer.py` - Uses `.get("command")` and `.get("path")` on raw dict
- `tmp_creation_blocker.py` - Uses `.get("command")` and `.get("path")` on raw dict
- `destructive_command_blocker.py` - Defines own ToolInput type
- `utils/utils.py` - Already only populates `file_path` and `content`

**Post-Tools Hooks**:
- `unified_python_antipattern_hook.py` - Uses `.get("path")` on raw dict
- `formatting/basedpyright_checking.py` - Uses `.get("path")` on raw dict
- `formatting/vulture_checking.py` - Uses `.get("path")` on raw dict

**Rationale**: All these hooks work with `dict[str, str]` from `tool_input_obj`, not the typed `ToolInput`. Runtime behavior is unaffected.

---

## Success Criteria

### Refactoring Completed Successfully When:

1. ✅ `ToolInput` TypedDict only contains `file_path` and `content`
2. ✅ All tests in `test_data_types.py` pass
3. ✅ All hook tests pass (if they exist)
4. ✅ Type checking passes with pyright
5. ✅ Hooks function correctly in Claude Code environment
6. ✅ No breaking changes to hook behavior
7. ✅ Documentation updated to explain shared vs. extended pattern

### Validation Checklist

- [ ] Updated `ToolInput` definition in data_types.py
- [ ] Updated tests in test_data_types.py
- [ ] Ran pytest on data_types tests - all pass
- [ ] Ran pytest on utils tests - all pass
- [ ] Ran pyright on pre_tools directory - no errors
- [ ] Tested hooks manually in Claude Code - all work
- [ ] Reviewed all hooks accessing command/path - no issues
- [ ] Updated hook documentation if needed

---

## Impact Summary

### Low-Risk Refactoring

**Why this is low-risk**:
- Changes only type definitions, not runtime behavior
- Hooks use raw dicts with `.get()`, unaffected by TypedDict changes
- parse_hook_input() already only populates these two fields
- Comprehensive test coverage will catch any issues

**Benefits**:
- Clearer shared type definition
- Less confusion about required vs. optional fields
- Better separation between shared utilities and hook-specific logic
- Improved maintainability

**No Impact On**:
- Hook execution flow
- Security validations
- Error handling
- Performance
- User-visible behavior

---

## Future Enhancements

### Optional Follow-up Tasks

1. **Create extended ToolInput types**
   - Define `BashToolInput` with `command` field
   - Define `PathToolInput` with `path` field
   - Use in hooks for better type safety

2. **Consolidate path handling**
   - Create utility function for `file_path or path` fallback
   - Standardize path extraction across hooks

3. **Improve parse_hook_input()**
   - Add option to parse additional fields
   - Support generic parsing for hook-specific needs

4. **Add hook testing framework**
   - Create test utilities for simulating hook inputs
   - Add integration tests with actual Claude Code events

---

## References

### Documentation
- Claude Code Hooks: `ai_docs/claude-code-hooks.md`
- UV Scripts Guide: `ai_docs/uv-scripts-guide.md`
- Hook Settings: `.claude/settings.json`

### Related Files
- Data types: `.claude/hooks/pre_tools/utils/data_types.py`
- Utilities: `.claude/hooks/pre_tools/utils/utils.py`
- Tests: `.claude/hooks/pre_tools/tests/test_data_types.py`

### Code Patterns
```python
# Pattern 1: Raw dict access (most hooks use this)
tool_input_obj: dict[str, str] = parsed_json.get("tool_input", {})
command = tool_input_obj.get("command", "")

# Pattern 2: Typed input via parse_hook_input()
tool_name, tool_input = parse_hook_input()
file_path = get_file_path(tool_input)

# Pattern 3: Local extended type
class MyToolInput(TypedDict, total=False):
    command: str
    file_path: str
```

---

**Specification Version**: 1.0
**Created**: 2025-10-26
**Status**: Ready for Implementation
