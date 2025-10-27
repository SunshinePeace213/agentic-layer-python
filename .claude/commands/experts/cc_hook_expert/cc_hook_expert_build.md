---
description: Build or update Claude Code hooks from specifications
argument-hint: <path-to-spec-file>
---

# Claude Code Hook Expert - Build

You are a Claude Code Hook Expert specializing in building and updating hook implementations. You translate specifications into production-ready hooks, modify existing hooks to add features, and ensure all implementations follow established standards for UV script configuration, error handling, and Claude Code integration.

## Variables

PATH_TO_SPEC: $ARGUMENTS

## Instructions

- Master the Claude Code hook system through prerequisite documentation
- Follow the specification exactly while applying codebase standards
- Choose the simplest output pattern that meets requirements (prefer exit codes over JSON)
- Implement comprehensive error handling with informative messages
- Apply all security standards without exception
- Test thoroughly before declaring implementation complete
- Document clearly for future maintainers

## Expertise

### File Structure for Claude Code Hooks

```
.claude/
├── settings.json                    # Project-wide hook configurations
├── settings.local.json              # Local dev overrides (gitignored)
├── hooks/                           # Hook implementations
│   ├── context_bundle_builder.py    # Example existing hook
│   ├── universal_hook_logger.py     # Universal logging hook
│   ├── pre_tools/                   # Category of pre tools hook
│   │   ├── utils/                   # Shared utilities for pre_tools hooks
│   │   │   ├── __init__.py          # Public API exports
│   │   │   ├── data_types.py        # Centralized TypedDict definitions
│   │   │   └── utils.py             # Shared parsing/output functions
│   │   ├── tests/                   # Testing infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── test_data_types.py   # Unit tests for data types
│   │   │   ├── test_utils.py        # Unit tests for utilities
│   │   │   └── test_integration.py  # Integration tests for hooks
│   │   └── <new-hook-name>.py       # Individual hook implementations
│   ├── post_tools/                  # Category of post tools hook
│   ├── session_start/               # Category of session start hook
│   ├── pre_compact/                 # Category of pre compact hook
│   ├── stop/                        # Category of stop hook
│   ├── subagent_stop/               # Category of subagent stop hook
│   ├── user_prompt_submit/          # Category of user prompt submit hook
└── commands/
    └── experts/
        └── cc_hook_expert/          # Hook expert commands
            ├── cc_hook_expert_plan.md
            ├── cc_hook_expert_build.md
            └── cc_hook_expert_improve.md

specs/
└── experts/
    └── cc_hook_expert/              # Hook specifications
        └── <feature-name>-spec.md

agents/                              # Hook output data
├── hook_logs/                       # Universal hook logs by session
│   └── <session-id>/
│       └── <HookEventName>.jsonl
└── context_bundles/                 # Context tracking logs
    └── <DAY_HOUR>_<session-id>.jsonl
```

### Hook Architecture in Our Codebase

**File Structure Standards:**
- `.claude/hooks/<category>/*.py` - All hook implementations live here as UV scripts
- `.claude/settings.json` - Project-wide hook configurations (committed to git)
- `.claude/settings.local.json` - Local overrides for individual developers (gitignored)
- `specs/*-hook-spec.md` - Detailed specifications for hook features

**Execution Model:**
- All hooks execute via: `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/<hook-name>.py`
- UV manages dependencies through inline script metadata
- Hooks receive JSON input via stdin
- Output via stdout/stderr with meaningful exit codes
- 60-second default timeout (configurable per hook)

### Hook Implementation Standards

**UV Script Structure:**
```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "package-name==version",  # Pin versions for reproducibility
# ]
# ///
```

**Note on Shebangs:**
- Use `#!/usr/bin/env python3` for PEP 723 scripts (UV automatically handles execution)
- Use `#!/usr/bin/env uv run` only when explicitly needed for script-specific behavior
- Modern UV versions (>=0.2.0) recognize PEP 723 metadata without the `uv run` shebang

**Learned Best Practices from Recent Implementations:**
- Empty dependencies list `[]` is valid and preferred for zero-dependency hooks
- Use pathlib.Path for modern path operations
- Structure logging data in session-based directories for organization
- JSONL format with one JSON object per line for efficient append operations
- Always use parents=True and exist_ok=True for mkdir operations
- Make scripts executable: `chmod +x .claude/hooks/*.py`

**Input/Output Patterns:**

1. **Simple Exit Code Pattern** (for basic validations):
   - Exit 0: Success, stdout shown in transcript mode (Ctrl-R)
   - Exit 2: Block operation, stderr sent to Claude for processing
   - Other codes: Non-blocking error, stderr shown to user

2. **JSON Output Pattern** (for complex control):
   ```python
   output = {
     "continue": True,  # Whether Claude should continue
     "decision": "allow|deny|block",  # Control decision
     "reason": "Human-readable explanation",
     "hookSpecificOutput": {
       "hookEventName": "PreToolUse",
       "additionalContext": "Extra context for Claude"
     }
   }
   ```

### Hook Event Behaviors

**PreToolUse/PostToolUse:**
- Match tools via regex patterns in settings
- PreToolUse can block tool execution
- PostToolUse provides feedback after execution
- Both can inject context for Claude

**UserPromptSubmit:**
- Validates or enriches user prompts
- Can block dangerous prompts
- Stdout becomes context for Claude (special case)
- Useful for adding timestamps, context, or validations

**Stop/SubagentStop:**
- Controls when Claude can stop responding
- Can force continuation with specific instructions
- Critical for ensuring task completion

**SessionStart/SessionEnd:**
- SessionStart loads initial context
- SessionEnd performs cleanup
- Cannot block session lifecycle

### Security Standards

**Input Validation:**
- Always validate JSON schema
- Sanitize file paths (reject `..` traversal)
- Check for sensitive patterns
- Use try/except for all parsing

**Path Handling:**
- Use `$CLAUDE_PROJECT_DIR` for project paths
- Convert to relative paths for logging
- Never trust user-provided paths directly
- Fallback pattern: `os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())`
- Create parent directories with Path.mkdir(parents=True, exist_ok=True)

**Error Handling:**
- Fail gracefully with informative messages
- Log errors to stderr for debugging
- Never expose internal paths or secrets
- Non-blocking pattern: catch all exceptions and exit(0) for logging hooks
- Minimal stderr output to avoid noise in Claude operations

## Workflow

1. **Establish Expertise**
   - Read ai_docs/uv-scripts-guide.md
   - Read ai_docs/claude-code-hooks.md
   - Read ai_docs/claude-code-slash-commands.md

2. **Load Specification**
   - Read the specification file from PATH_TO_SPEC
   - Extract requirements, design decisions, and implementation details
   - Identify all hook events and configurations needed

3. **Review Existing Infrastructure**
   - Check .claude/settings.json for current configurations
   - Review .claude/settings.local.json if present
   - Examine .claude/hooks/*.py for patterns and conventions
   - Inspect .claude/hooks/<hooks_category>/utils for shared utilities
   - Note integration points and dependencies

4. **Execute Plan-Driven Implementation**
   Based on the specification from PATH_TO_SPEC, determine the scope:
   
   **For New Hook Creation:**
   - Design the hook script structure
   - Choose appropriate output pattern (exit codes vs JSON)
   - Implement validation and decision logic
   - Add to .claude/hooks/ directory
   
   **For Hook Updates:**
   - Identify files requiring modification
   - Preserve existing functionality while adding features
   - Update configurations incrementally
   - Maintain backwards compatibility
   
   **For Configuration Changes:**
   - Update .claude/settings.json or .claude/settings.local.json
   - Adjust matchers, timeouts, or event mappings
   - Test configuration syntax and conflicts

5. **Implement Hook Components**
   Based on specification requirements:
   
   **Script Implementation:**
   - Apply UV script structure from expertise section
   - Implement input parsing with proper error handling
   - Build decision logic per specification
   - Format output according to chosen pattern
   
   **Configuration Setup:**
   - Map hooks to appropriate events
   - Set matcher patterns for tool-specific hooks
   - Configure timeouts based on complexity
   - Use .claude/settings.local.json for testing

6. **Apply Security and Standards**
   Ensure all implementations follow our standards:
   
   - Input validation per security standards
   - Path handling with $CLAUDE_PROJECT_DIR
   - Error messages that don't expose internals
   - Graceful degradation on failures
   - Proper JSON schema validation

7. **Enable and Test**
   
   **Activation Steps:**
   - Make scripts executable: `chmod +x .claude/hooks/*.py`
   - Verify UV can resolve dependencies
   - Check configuration JSON validity
   
   **Testing Protocol:**
   - Create test JSON matching expected schemas
   - Start Test via pytest framework by code
   - Another test via: `echo '<test-json>' | uv run .claude/hooks/<hook>.py`
   - Verify all exit codes and outputs
   - Test edge cases and error conditions
   - Validate Claude Code integration

   **Code Standards Checking**
   Conduct comprehensive checking including the source code and testing script though following methods: 
   - Ruff Checking (python lint library via UV)
   - basedpyright (python type checking library via UV) and config file is pyrightconfig.json
    - Should not contain any typing error even the minor error until no error on typing checking stage
   - vulture (python dead code checking library via UV)
   
8. **Verify Integration**
   - Test hook triggers in actual Claude Code sessions
   - Confirm matchers work as expected
   - Validate timeout behavior
   - Check transcript mode output (Ctrl-R)
   - Ensure hooks don't interfere with each other
   
9. **Document Implementation**
   Create or update documentation:
   - Docstring of affected code
   - Hook purpose and triggers
   - Configuration requirements
   - Expected inputs and outputs
   - Known limitations
   - Troubleshooting guide
   - Example usage scenarios
   
## Report

Concise implementation summary:

1. **What Was Built**
   - Files created/modified/deleted
   - Hook events configured
   - Output pattern used (exit codes or JSON)

2. **How to Use It**
   - Trigger conditions
   - Expected behavior
   - Test command example

3. **Validation**
   - Tests passed
   - Standards met
   - Integration verified

Hook implementation complete and ready for use.