# Claude Code Hooks Reference Documentation

## Overview

Claude Code hooks enable automated execution of shell commands in response to specific events during development. Hooks receive JSON data via stdin and can control Claude's behavior through exit codes and structured output.

## Configuration Structure

Hooks are defined in settings files (`~/.claude/settings.json`, `.claude/settings.json`, or `.claude/settings.local.json`) organized by event type and matcher patterns:

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Key Configuration Elements

- **matcher**: Pattern for tool names (regex supported, case-sensitive)
- **hooks**: Array of command definitions to execute
- **type**: Currently only "command" is supported
- **timeout**: Optional execution limit in seconds (default 60)

## Hook Events

### PreToolUse
Executes after Claude creates tool parameters but before tool processing. Supports matchers for tools like `Bash`, `Write`, `Edit`, `Read`, `Glob`, `Grep`, and others.

### PostToolUse
Runs immediately after successful tool completion. Uses identical matcher patterns as PreToolUse.

### Notification
Triggers when Claude sends notifications, such as permission requests or input idle timeouts.

### UserPromptSubmit
Executes when users submit prompts, enabling validation, context injection, or prompt blocking.

### Stop
Runs when the main Claude Code agent finishes responding (excluding user interrupts).

### SubagentStop
Executes when a Claude Code subagent (Task tool) completes.

### PreCompact
Triggers before compact operations with matchers: `manual` or `auto`.

### SessionStart
Runs at session initialization with matchers: `startup`, `resume`, `clear`, or `compact`. Supports `CLAUDE_ENV_FILE` for persisting environment variables.

### SessionEnd
Executes at session termination. Cannot block termination but enables cleanup tasks.

## Hook Input Format

Hooks receive JSON via stdin containing session information:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/directory",
  "hook_event_name": "EventName"
}
```

Event-specific fields vary by hook type.

## Hook Output Methods

### Exit Code Approach

- **0**: Success; stdout shown in transcript (except UserPromptSubmit/SessionStart where stdout becomes context)
- **2**: Blocking error; stderr fed to Claude for processing
- **Other codes**: Non-blocking error; stderr shown to user

### JSON Output Approach

Hooks can return structured JSON for sophisticated control:

```json
{
  "continue": true,
  "stopReason": "message",
  "suppressOutput": true,
  "systemMessage": "warning"
}
```

Hook-specific decision fields control behavior:
- **PreToolUse**: `permissionDecision` ("allow", "deny", "ask")
- **PostToolUse**: `decision` ("block" or undefined)
- **UserPromptSubmit**: `decision` ("block" or undefined)
- **Stop/SubagentStop**: `decision` ("block" or undefined)
- **SessionStart**: `additionalContext` for context injection

## Working with MCP Tools

MCP tools follow the naming pattern: `mcp__<server>__<tool>`

Examples:
- `mcp__memory__create_entities`
- `mcp__filesystem__read_file`

Configure hooks using regex matchers:
```json
{
  "matcher": "mcp__memory__.*"
}
```

## Environment Variables

- `CLAUDE_PROJECT_DIR`: Absolute path to project root
- `CLAUDE_CODE_REMOTE`: "true" for web environments
- `CLAUDE_ENV_FILE`: (SessionStart only) Path for persisting environment variables

## Security Considerations

"USE AT YOUR OWN RISK": Hooks execute arbitrary shell commands automatically. Users are solely responsible for command safety. Hooks can access any files your user account can access. Malicious or poorly written hooks may cause data loss or system damage.

### Best Practices

1. Validate and sanitize all inputs
2. Always quote shell variables (`"$VAR"`)
3. Block path traversal attempts (check for `..`)
4. Use absolute paths for scripts
5. Avoid sensitive files (`.env`, `.git/`, keys)

## Hook Execution Details

- **Timeout**: 60-second default, configurable per command
- **Parallelization**: Matching hooks run in parallel
- **Deduplication**: Identical hook commands automatically deduplicated
- **Environment**: Runs in current directory with Claude Code's environment
- **Input**: JSON via stdin
- **Output**: Varies by hook type (transcript, debug log, or context)

## Debugging

Use `claude --debug` for detailed hook execution information. Check:

1. Hook registration via `/hooks` command
2. JSON settings validity
3. Command execution manually
4. Script permissions
5. Debug logs for detailed execution flow

Progress messages in transcript mode (Ctrl-R) display hook execution status, commands, and results.

---

**Note**: This documentation provides reference material for Claude Code hook implementation. For practical examples and quickstart guidance, consult the accompanying hooks guide.
