# Error Handling Reminder Hook Specification

## Overview

**Hook Name:** `error_handling_reminder.py`
**Hook Type:** PostToolUse
**Version:** 1.0.0
**Purpose:** Educational awareness hook that gently reminds Claude to consider error handling and logging when risky code patterns are detected

## Problem Statement

Claude Code often writes Python code involving exception handling, async operations, database calls, and API endpoints. While Claude understands error handling conceptually, it may not always include sufficient logging or error handling in every scenario. This hook provides a gentle, educational reminder when risky patterns are detected without adequate logging, helping Claude self-assess and improve error handling practices.

## Objectives

1. **Detection:** Identify risky code patterns that commonly need error handling:
   - Exception handling blocks (try/except)
   - Async operations (async/await)
   - Database operations (SQL queries, ORM calls)
   - API controllers/endpoints (Flask, FastAPI, Django routes)

2. **Assessment:** Evaluate whether detected patterns have adequate logging:
   - Logging statements in exception handlers
   - Logging around database operations
   - Logging in async functions
   - Logging in API endpoints

3. **Education:** Provide gentle, non-blocking reminders with:
   - Pattern summary (what was detected)
   - Specific recommendations based on detected patterns
   - Best practice tips for error handling and logging

4. **Non-Interference:** Never block Claude's workflow:
   - Always exit with code 0
   - No decision="block" in output
   - Purely informational/educational

## Hook Event Selection

**Selected Event:** `PostToolUse`

**Rationale:**
- Runs after Write/Edit/NotebookEdit operations complete
- Allows analysis of the final file state
- Provides feedback Claude can act on in next iteration
- Non-intrusive timing (after tool succeeds)

**Tool Matchers:** `Write|Edit|NotebookEdit`

**Why These Tools:**
- Write: New files being created may need error handling
- Edit: Modified files may have new risky patterns added
- NotebookEdit: Notebook cells can contain risky code

## Input Schema

The hook receives standard PostToolUse input via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/root",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/project/src/example.py",
    "content": "..."
  },
  "tool_response": {
    "filePath": "/project/src/example.py",
    "success": true
  }
}
```

**Required Fields for Processing:**
- `tool_name`: Must be "Write", "Edit", or "NotebookEdit"
- `tool_input.file_path`: Path to the edited file
- `tool_response.success`: Must be true (only process successful operations)

## Output Schema

### Non-Blocking Feedback (Default)

When risky patterns are detected:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "📋 ERROR HANDLING SELF-CHECK\n\n⚠️ Risky Patterns Detected..."
  },
  "suppressOutput": true
}
```

### Silent Exit (No Issues)

When no risky patterns detected or logging is adequate:

```json
{
  "suppressOutput": true
}
```

**Exit Code:** Always `0` (never blocks)

## Detection Algorithm

### Phase 1: File Validation

1. Check tool name matches Write|Edit|NotebookEdit
2. Verify tool execution succeeded (tool_response.success)
3. Extract file_path from tool_input
4. Validate file is Python (.py, .pyi)
5. Verify file is within project directory (security)
6. Check file exists on disk

### Phase 2: AST-Based Pattern Detection

Parse file to AST and detect:

#### 1. Exception Handling Patterns

**Detection:**
- `ast.Try` nodes (try/except blocks)
- Count total try/except blocks
- Analyze except handlers for logging statements

**Logging Check:**
- Look for `logging.*` or `logger.*` calls in except body
- Look for `print()` calls (with note that logging is preferred)
- Flag try/except blocks without any logging as risky

**Risk Scoring:**
```python
risk_score += (except_blocks_without_logging * 1)
```

#### 2. Async Operation Patterns

**Detection:**
- `ast.AsyncFunctionDef` nodes (async def functions)
- `ast.Await` expressions (await calls)
- Count async functions without try/except

**Logging Check:**
- Check if async function body contains Try nodes
- Check for logging statements in async function

**Risk Scoring:**
```python
risk_score += (async_functions_without_error_handling * 1)
```

#### 3. Database Operation Patterns

**Detection:**
- Import statements from DB libraries:
  - `sqlite3`, `psycopg2`, `pymongo`, `mysql.connector`
  - `sqlalchemy`, `django.db`, `peewee`
- Method calls containing DB keywords:
  - `execute`, `executemany`, `query`, `filter`, `get`
  - `insert`, `update`, `delete`, `commit`, `rollback`
  - `save`, `create`, `bulk_create`

**Logging Check:**
- Check if DB operations are within Try nodes
- Check for logging around DB operations

**Risk Scoring:**
```python
risk_score += (db_operations_without_error_handling * 1)
```

#### 4. API Controller/Endpoint Patterns

**Detection:**
- Function decorators indicating routes:
  - Flask: `@app.route`, `@blueprint.route`
  - FastAPI: `@app.get`, `@app.post`, `@router.get`
  - Django: Functions in views.py or decorated with `@api_view`
- Import statements from web frameworks

**Logging Check:**
- Check if endpoint functions have Try nodes
- Check for logging statements in endpoint body

**Risk Scoring:**
```python
risk_score += (endpoints_without_error_handling * 1)
```

### Phase 3: Risk Assessment

**Risk Score Calculation:**
```python
total_risk_score = (
    except_blocks_without_logging +
    async_functions_without_error_handling +
    db_operations_without_error_handling +
    endpoints_without_error_handling
)
```

**Threshold:**
- Default: 2 (trigger reminder if score >= 2)
- Configurable via: `ERROR_HANDLING_REMINDER_MIN_SCORE`

**Decision:**
- If `total_risk_score >= threshold`: Generate reminder message
- If `total_risk_score < threshold`: Silent exit (no output)

### Phase 4: Message Generation

Generate structured feedback message:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ERROR HANDLING SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Risky Patterns Detected in [filename]

   [Recommendations section - specific to detected patterns]

   💡 Error Handling Best Practices:
      [Tips section - based on detected patterns]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Recommendation Templates:**

| Pattern | Recommendation |
|---------|----------------|
| Try/except without logging | ❓ Found X try-except block(s) - Consider adding logging in except blocks for debugging |
| Async without error handling | ❓ Found X async function(s) without error handling - Add try/except to handle async errors |
| Database operations | ❓ Found X database operation(s) - Ensure transactions have proper error handling and logging |
| API endpoints | ❓ Found X API endpoint(s) - Consider adding error handling to return appropriate HTTP status codes |

**Best Practice Tips:**

For exception handling:
- Add logging statements in exception handlers for debugging
- Use structured logging with context (e.g., user_id, request_id)
- Handle specific exceptions rather than bare except
- Log errors before re-raising or returning error responses

For async operations:
- Wrap await calls in try/except when dealing with external services
- Use finally blocks to ensure proper cleanup
- Consider timeout handling for long-running async operations

For database operations:
- Use transactions with proper commit/rollback
- Log query errors with relevant context (table, operation)
- Handle connection errors gracefully with retries
- Use context managers (with statements) for automatic cleanup

For API endpoints:
- Return appropriate HTTP status codes (400, 404, 500, etc.)
- Log errors with request context (endpoint, method, params)
- Avoid exposing internal error details to users
- Use middleware/decorators for consistent error handling

## Configuration

### Environment Variables

```python
ERROR_HANDLING_REMINDER_ENABLED = os.getenv("ERROR_HANDLING_REMINDER_ENABLED", "true")
# Enable/disable the hook entirely
# Values: "true" | "false"

ERROR_HANDLING_REMINDER_MIN_SCORE = int(os.getenv("ERROR_HANDLING_REMINDER_MIN_SCORE", "2"))
# Minimum risk score to trigger reminder
# Values: integer >= 1 (default: 2)

ERROR_HANDLING_REMINDER_INCLUDE_TIPS = os.getenv("ERROR_HANDLING_REMINDER_INCLUDE_TIPS", "true")
# Include best practice tips section in output
# Values: "true" | "false"

ERROR_HANDLING_REMINDER_DEBUG = os.getenv("ERROR_HANDLING_REMINDER_DEBUG", "false")
# Enable debug logging to stderr
# Values: "true" | "false"
```

### Settings.json Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/error_handling_reminder.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Timeout:** 15 seconds (adequate for AST parsing of typical files)

## Dependencies

### Python Version
- `requires-python = ">=3.12"`

### External Packages
None - uses Python standard library only:
- `ast`: AST parsing and analysis
- `json`: Input/output parsing
- `os`: Environment variables
- `sys`: stdin/stdout/stderr
- `pathlib`: Path manipulation
- `re`: Pattern matching (if needed)

### UV Script Metadata

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

## Security Considerations

### Path Validation

1. **No Path Traversal:**
   - Validate file_path is within CLAUDE_PROJECT_DIR
   - Use `Path.resolve()` and `Path.relative_to()` for security
   - Reject files outside project directory

2. **File Existence:**
   - Check file exists before reading
   - Handle missing files gracefully (silent exit)

### Safe File Reading

1. **File Size Limits:**
   - Skip files > 10,000 lines (performance protection)
   - Prevent memory exhaustion on large files

2. **Encoding Handling:**
   - Use UTF-8 encoding with error handling
   - Skip files with encoding errors (silent exit)

3. **Syntax Errors:**
   - Catch `SyntaxError` during AST parsing
   - Silent exit if file has syntax errors (other hooks will catch)

### Process Safety

1. **No External Commands:**
   - Pure Python implementation
   - No subprocess calls
   - No shell execution

2. **Timeout Protection:**
   - Hook-level timeout: 15 seconds (in settings.json)
   - Ensures hook doesn't hang indefinitely

### Error Handling

```python
try:
    main()
except Exception as e:
    # Log to stderr but don't block Claude
    print(f"Error handling reminder hook error: {e}", file=sys.stderr)
    output_feedback("", suppress_output=True)
```

**Principle:** Never block Claude due to hook errors

## Error Handling Strategy

### Hook-Level Errors

All errors result in silent exit (exit 0):

```python
output_feedback("", suppress_output=True)
sys.exit(0)
```

**Error Categories:**

1. **Input Parsing Errors:**
   - Invalid JSON → Silent exit
   - Missing required fields → Silent exit

2. **File Access Errors:**
   - File not found → Silent exit
   - Permission denied → Silent exit
   - File outside project → Silent exit

3. **AST Parsing Errors:**
   - Syntax errors → Silent exit (other hooks handle syntax)
   - Invalid Python → Silent exit

4. **Unexpected Exceptions:**
   - Log to stderr for debugging
   - Silent exit (never block)

### Non-Blocking Guarantee

**Critical Requirement:** This hook MUST NEVER block Claude

- Always exit with code 0
- Never use `decision="block"` in output
- All errors result in silent exit
- No exceptions propagate to Claude Code

## Testing Strategy

### Unit Tests Location

```
tests/claude_hook/post_tools/test_error_handling_reminder.py
```

### Test Cases

#### 1. File Validation Tests

```python
def test_skip_non_python_files():
    """Test that .js, .txt, etc. are skipped"""

def test_skip_files_outside_project():
    """Test path traversal protection"""

def test_skip_when_tool_fails():
    """Test that failed tool operations are skipped"""

def test_skip_missing_files():
    """Test graceful handling of missing files"""
```

#### 2. Pattern Detection Tests

```python
def test_detect_try_except_without_logging():
    """Test detection of try/except without logging"""

def test_detect_async_without_error_handling():
    """Test detection of async functions without try/except"""

def test_detect_database_operations():
    """Test detection of DB calls"""

def test_detect_api_endpoints():
    """Test detection of Flask/FastAPI routes"""

def test_ignore_try_except_with_logging():
    """Test that properly logged exceptions are not flagged"""
```

#### 3. Risk Scoring Tests

```python
def test_risk_score_calculation():
    """Test risk score accumulation"""

def test_threshold_filtering():
    """Test that low scores don't trigger reminder"""

def test_multiple_patterns_increase_score():
    """Test that multiple risky patterns increase score"""
```

#### 4. Message Generation Tests

```python
def test_message_format():
    """Test output message formatting"""

def test_recommendations_match_patterns():
    """Test that recommendations match detected patterns"""

def test_tips_section_configurable():
    """Test that tips can be disabled via env var"""
```

#### 5. Integration Tests

```python
def test_full_workflow_with_risky_code():
    """Test complete hook flow with risky code"""

def test_full_workflow_with_safe_code():
    """Test complete hook flow with safe code"""

def test_error_handling_doesnt_block():
    """Test that errors result in silent exit"""
```

### Test Execution

```bash
# Run tests with distributed testing
uv run pytest -n auto tests/claude_hook/post_tools/test_error_handling_reminder.py

# Run with coverage
uv run pytest --cov=.claude/hooks/post_tools/error_handling_reminder tests/claude_hook/post_tools/test_error_handling_reminder.py
```

## Implementation Checklist

### Phase 1: Core Structure

- [ ] Create `error_handling_reminder.py` in `.claude/hooks/post_tools/`
- [ ] Add UV script metadata (Python 3.12+, no dependencies)
- [ ] Import shared utilities from `utils/`
- [ ] Implement `main()` entry point
- [ ] Add exception handling wrapper

### Phase 2: Input Processing

- [ ] Implement `should_process()` validation function
- [ ] Check tool name (Write|Edit|NotebookEdit)
- [ ] Validate tool success
- [ ] Extract and validate file path
- [ ] Check Python file extension
- [ ] Verify file within project directory

### Phase 3: Pattern Detection

- [ ] Create `RiskyPatternDetector` AST visitor class
- [ ] Implement exception handling detection (`visit_Try`)
- [ ] Implement async operation detection (`visit_AsyncFunctionDef`, `visit_Await`)
- [ ] Implement database operation detection (`visit_ImportFrom`, `visit_Call`)
- [ ] Implement API endpoint detection (decorator analysis)
- [ ] Implement logging statement detection helper

### Phase 4: Risk Assessment

- [ ] Create `RiskAssessment` data class
- [ ] Implement risk score calculation logic
- [ ] Implement threshold comparison
- [ ] Create recommendation generator
- [ ] Create best practice tip selector

### Phase 5: Output Generation

- [ ] Implement message formatter
- [ ] Create ASCII art header/footer
- [ ] Format recommendations list
- [ ] Format best practices list
- [ ] Test message formatting with various scenarios

### Phase 6: Configuration

- [ ] Add environment variable loading
- [ ] Implement configuration validation
- [ ] Add debug logging support
- [ ] Document configuration options

### Phase 7: Testing

- [ ] Create test file structure
- [ ] Write unit tests for pattern detection
- [ ] Write unit tests for risk scoring
- [ ] Write integration tests
- [ ] Add test fixtures (sample Python files)

### Phase 8: Documentation

- [ ] Add comprehensive docstrings
- [ ] Document configuration options
- [ ] Create usage examples
- [ ] Add inline code comments

### Phase 9: Integration

- [ ] Add hook to `.claude/settings.json`
- [ ] Test with real Claude Code sessions
- [ ] Verify non-blocking behavior
- [ ] Validate message formatting in transcript

## Rollback Strategy

If issues arise with the hook:

### Immediate Disable

Disable via environment variable (no code changes):

```bash
export ERROR_HANDLING_REMINDER_ENABLED=false
```

### Settings Disable

Remove or comment out hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          // {
          //   "type": "command",
          //   "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/error_handling_reminder.py",
          //   "timeout": 15
          // }
        ]
      }
    ]
  }
}
```

### Complete Removal

Delete the hook file:

```bash
rm .claude/hooks/post_tools/error_handling_reminder.py
```

### Fallback Behavior

The hook is designed to fail safely:
- All errors result in silent exit (no impact to Claude)
- No blocking behavior even during failures
- Claude continues normal operation if hook removed

## Success Metrics

### Quantitative Metrics

1. **Detection Accuracy:**
   - True positives: Risky code correctly identified
   - False positives: Safe code incorrectly flagged (target: < 10%)
   - False negatives: Risky code missed (target: < 5%)

2. **Performance:**
   - Execution time: < 1 second for typical files
   - Memory usage: < 50MB for typical files
   - No timeouts (15-second limit)

3. **Reliability:**
   - Zero blocking incidents (critical)
   - Zero crashes/exceptions that escape to user
   - 100% graceful degradation on errors

### Qualitative Metrics

1. **Educational Value:**
   - Claude adds logging after seeing reminders
   - Improved error handling in subsequent iterations
   - Better awareness of logging best practices

2. **User Experience:**
   - Non-intrusive (suppressOutput=true)
   - Helpful recommendations
   - Clear, actionable advice

3. **Code Quality Impact:**
   - More consistent error handling across codebase
   - Better debugging capabilities through logging
   - Fewer production errors due to missing error handling

## Future Enhancements

### Potential Additions (v2.0)

1. **Pattern Library Expansion:**
   - Network requests (requests, httpx, aiohttp)
   - File I/O operations (open, with statements)
   - External service calls (API clients)
   - Resource management (threading, multiprocessing)

2. **Logging Quality Analysis:**
   - Check if logging includes context variables
   - Validate logging levels (debug vs error)
   - Detect empty log messages
   - Suggest structured logging improvements

3. **Project-Specific Configuration:**
   - `.errorhandling.toml` for project rules
   - Custom pattern definitions
   - Framework-specific templates
   - Team-specific best practices

4. **Integration with Other Hooks:**
   - Share data with antipattern hook
   - Coordinate with type checking hooks
   - Aggregate feedback across hooks

5. **Machine Learning Enhancements:**
   - Learn project-specific patterns over time
   - Adapt recommendations based on codebase style
   - Reduce false positives through context learning

## Appendix A: Example Scenarios

### Scenario 1: Try/Except Without Logging

**Input Code:**
```python
def process_user_data(user_id):
    try:
        data = fetch_from_database(user_id)
        return process(data)
    except Exception:
        return None
```

**Detection:**
- 1 try/except block detected
- 0 logging statements in except block
- Risk score: 1

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ERROR HANDLING SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Risky Patterns Detected in example.py

   ❓ Found 1 try-except block - Consider adding logging in except blocks for debugging

   💡 Error Handling Best Practices:
      - Add logging statements in exception handlers for debugging
      - Use structured logging with context (e.g., user_id, request_id)
      - Handle specific exceptions rather than bare except
      - Log errors before re-raising or returning error responses
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario 2: Async Function Without Error Handling

**Input Code:**
```python
async def fetch_user_profile(user_id):
    response = await http_client.get(f"/users/{user_id}")
    return response.json()
```

**Detection:**
- 1 async function detected
- 0 try/except blocks in function body
- Risk score: 1

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ERROR HANDLING SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Risky Patterns Detected in async_service.py

   ❓ Found 1 async function without error handling - Add try/except to handle async errors

   💡 Error Handling Best Practices:
      - Wrap await calls in try/except when dealing with external services
      - Use finally blocks to ensure proper cleanup
      - Consider timeout handling for long-running async operations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario 3: Multiple Risky Patterns

**Input Code:**
```python
@app.route("/users/<user_id>")
async def get_user(user_id):
    result = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(result)
```

**Detection:**
- 1 API endpoint detected (Flask route)
- 1 async function detected
- 1 database operation detected (execute)
- 0 try/except blocks
- Risk score: 3

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ERROR HANDLING SELF-CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Risky Patterns Detected in api.py

   ❓ Found 1 async function without error handling - Add try/except to handle async errors
   ❓ Found 1 database operation - Ensure transactions have proper error handling and logging
   ❓ Found 1 API endpoint - Consider adding error handling to return appropriate HTTP status codes

   💡 Error Handling Best Practices:
      - Wrap await calls in try/except when dealing with external services
      - Use transactions with proper commit/rollback
      - Return appropriate HTTP status codes (400, 404, 500, etc.)
      - Log errors with request context (endpoint, method, params)
      - Add logging statements in exception handlers for debugging
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario 4: Properly Handled Code (No Output)

**Input Code:**
```python
import logging

logger = logging.getLogger(__name__)

async def fetch_user_profile(user_id):
    try:
        response = await http_client.get(f"/users/{user_id}")
        logger.info(f"Fetched profile for user {user_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        raise
```

**Detection:**
- 1 async function detected
- 1 try/except block with logging
- Risk score: 0

**Output:**
```json
{
  "suppressOutput": true
}
```

(Silent exit - no feedback to Claude)

## Appendix B: AST Detection Patterns

### Exception Handling Detection

```python
def visit_Try(self, node: ast.Try) -> None:
    """Detect try/except blocks and check for logging."""
    for handler in node.handlers:
        has_logging = self._has_logging_in_block(handler.body)
        if not has_logging:
            self.except_blocks_without_logging += 1
            self.issues.append({
                "type": "exception_handling",
                "line": node.lineno,
                "message": "Try/except block without logging"
            })
    self.generic_visit(node)
```

### Async Function Detection

```python
def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
    """Detect async functions and check for error handling."""
    has_try = any(isinstance(child, ast.Try) for child in ast.walk(node))
    if not has_try:
        self.async_functions_without_error_handling += 1
        self.issues.append({
            "type": "async_operation",
            "line": node.lineno,
            "message": f"Async function '{node.name}' without error handling"
        })
    self.generic_visit(node)
```

### Database Operation Detection

```python
def visit_Call(self, node: ast.Call) -> None:
    """Detect database operation calls."""
    if isinstance(node.func, ast.Attribute):
        method_name = node.func.attr
        db_methods = {
            "execute", "executemany", "query", "filter", "get",
            "insert", "update", "delete", "commit", "rollback",
            "save", "create", "bulk_create"
        }
        if method_name in db_methods:
            # Check if inside try block
            if not self._is_inside_try_block(node):
                self.db_operations_without_error_handling += 1
                self.issues.append({
                    "type": "database_operation",
                    "line": node.lineno,
                    "message": f"Database operation '{method_name}' without error handling"
                })
    self.generic_visit(node)
```

### API Endpoint Detection

```python
def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
    """Detect API endpoint functions via decorators."""
    route_decorators = {
        "route", "get", "post", "put", "patch", "delete",
        "api_view", "action"
    }

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in route_decorators:
                    # Found an API endpoint
                    has_try = any(isinstance(child, ast.Try) for child in ast.walk(node))
                    if not has_try:
                        self.endpoints_without_error_handling += 1
                        self.issues.append({
                            "type": "api_endpoint",
                            "line": node.lineno,
                            "message": f"API endpoint '{node.name}' without error handling"
                        })
    self.generic_visit(node)
```

### Logging Statement Detection

```python
def _has_logging_in_block(self, block: list[ast.stmt]) -> bool:
    """Check if code block contains logging statements."""
    for node in ast.walk(ast.Module(body=block)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Check for logging.info(), logger.error(), etc.
                if node.func.attr in {
                    "debug", "info", "warning", "error", "critical",
                    "log", "exception"
                }:
                    return True
            elif isinstance(node.func, ast.Name):
                # Check for print() (acceptable but not ideal)
                if node.func.id == "print":
                    return True
    return False
```

## Appendix C: Configuration Examples

### Minimal Configuration

Only trigger for high-risk scenarios:

```bash
export ERROR_HANDLING_REMINDER_MIN_SCORE=3
```

### Verbose Configuration

Show tips and enable debugging:

```bash
export ERROR_HANDLING_REMINDER_ENABLED=true
export ERROR_HANDLING_REMINDER_MIN_SCORE=1
export ERROR_HANDLING_REMINDER_INCLUDE_TIPS=true
export ERROR_HANDLING_REMINDER_DEBUG=true
```

### Strict Configuration

Trigger on any risky pattern:

```bash
export ERROR_HANDLING_REMINDER_MIN_SCORE=1
```

### Disabled Configuration

Completely disable the hook:

```bash
export ERROR_HANDLING_REMINDER_ENABLED=false
```

## Appendix D: Integration with Existing Hooks

### Execution Order in PostToolUse

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/unified_python_antipattern_hook.py",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/ruff_checking.py",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/basedpyright_checking.py",
            "timeout": 15
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/vulture_checking.py",
            "timeout": 15
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post_tools/error_handling_reminder.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Note:** Hooks run in parallel, so execution order doesn't matter for non-blocking hooks.

### Coordination with Other Hooks

This hook complements existing hooks:

- **unified_python_antipattern_hook.py**: Detects code antipatterns (bare except, etc.)
- **ruff_checking.py**: Formats and lints code
- **basedpyright_checking.py**: Type checking
- **vulture_checking.py**: Dead code detection
- **error_handling_reminder.py**: Error handling and logging awareness ← NEW

Each hook has a distinct, non-overlapping purpose.

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-10-31 | Claude Code Hook Expert | Initial specification |

---

**End of Specification**
