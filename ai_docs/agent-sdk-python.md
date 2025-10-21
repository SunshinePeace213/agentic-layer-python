# Agent SDK Reference - Python

## Installation

```bash
pip install claude-agent-sdk
```

## Core Functions

### query()

Creates a new session for each interaction. Returns an async iterator yielding messages.

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None
) -> AsyncIterator[Message]
```

**Key feature:** Each call starts fresh with no memory of previous interactions.

### ClaudeSDKClient

Maintains conversation sessions across multiple exchanges, enabling context retention.

```python
async with ClaudeSDKClient() as client:
    await client.query("Your prompt")
    async for message in client.receive_response():
        print(message)
```

**Key feature:** Claude remembers previous messages within the session.

## Quick Comparison Table

| Feature | query() | ClaudeSDKClient |
|---------|---------|-----------------|
| Session | New each time | Reuses same |
| Conversation | Single exchange | Multiple exchanges |
| Streaming Input | ✅ | ✅ |
| Interrupts | ❌ | ✅ |
| Hooks | ❌ | ✅ |
| Custom Tools | ❌ | ✅ |

## Decorators and Tools

### @tool()

Decorator for defining MCP tools with type safety.

```python
@tool("greet", "Greet a user", {"name": str})
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{
            "type": "text",
            "text": f"Hello, {args['name']}!"
        }]
    }
```

### create_sdk_mcp_server()

Creates in-process MCP server within Python applications.

```python
calculator = create_sdk_mcp_server(
    name="calculator",
    version="2.0.0",
    tools=[add, multiply]
)
```

## Key Configuration: ClaudeAgentOptions

Main dataclass for configuring Claude Code queries:

- `allowed_tools`: List of permitted tool names
- `system_prompt`: Custom or preset system prompt
- `mcp_servers`: MCP server configurations
- `permission_mode`: Control tool execution permissions
- `continue_conversation`: Resume previous conversation
- `max_turns`: Limit conversation turns
- `cwd`: Working directory
- `setting_sources`: Control filesystem settings loading

**Important:** When `setting_sources` is omitted, no filesystem settings load, providing SDK isolation.

## SettingSource Values

- `"user"`: Global settings (~/.claude/settings.json)
- `"project"`: Shared project settings (.claude/settings.json)
- `"local"`: Local project settings (.claude/settings.local.json)

Load all sources: `setting_sources=["user", "project", "local"]`

Load only project: `setting_sources=["project"]`

## Message Types

- **UserMessage**: User input with string or content blocks
- **AssistantMessage**: Claude response with content blocks
- **SystemMessage**: System message with metadata
- **ResultMessage**: Final result with cost and usage info

## Content Blocks

- **TextBlock**: Text content (`text: str`)
- **ThinkingBlock**: Model thinking (`thinking: str`, `signature: str`)
- **ToolUseBlock**: Tool requests (`name: str`, `input: dict`)
- **ToolResultBlock**: Tool results (`tool_use_id: str`, `content`, `is_error`)

## Permission Modes

- `"default"`: Standard behavior
- `"acceptEdits"`: Auto-accept file edits
- `"plan"`: Planning mode without execution
- `"bypassPermissions"`: Bypass all checks (use cautiously)

## Hook Events

Supported for intercepting behavior:

- `PreToolUse`: Before tool execution
- `PostToolUse`: After tool execution
- `UserPromptSubmit`: When user submits prompt
- `Stop`: When stopping execution
- `SubagentStop`: When subagent stops
- `PreCompact`: Before message compaction

## Error Types

- **ClaudeSDKError**: Base exception class
- **CLINotFoundError**: Claude Code CLI not found
- **CLIConnectionError**: Connection failure
- **ProcessError**: Process failure with exit code
- **CLIJSONDecodeError**: JSON parsing failure

## Built-in Tool Input/Output Schemas

**Bash**: Execute commands with timeout and background support

**Read**: Read files (text with line numbers or base64 images)

**Write**: Write file content

**Edit**: Replace text in files

**Glob**: Match files against patterns

**Grep**: Search with regex support

**WebFetch**: Fetch and analyze web content

**WebSearch**: Search the web with domain filtering

**Task**: Delegate to subagents

**NotebookEdit**: Modify Jupyter notebooks

**TodoWrite**: Manage todo lists

## Advanced Features

### Using Hooks for Behavior Control

```python
async def validate_bash_command(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    if "rm -rf /" in input_data.get('command', ''):
        return {'decision': 'block'}
    return {}
```

### Continuous Conversation Pattern

```python
async with ClaudeSDKClient() as client:
    await client.query("Create a file")
    async for msg in client.receive_response():
        process(msg)

    await client.query("What's in that file?")
    async for msg in client.receive_response():
        process(msg)  # Claude remembers!
```

### Streaming Input

```python
async def message_stream():
    yield {"type": "text", "text": "Part 1"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "Part 2"}

await client.query(message_stream())
```

## SystemPromptPreset Configuration

Use Claude Code's preset with optional extensions:

```python
{
    "type": "preset",
    "preset": "claude_code",
    "append": "Additional instructions here"
}
```

## AgentDefinition for Subagents

```python
@dataclass
class AgentDefinition:
    description: str       # When to use this agent
    prompt: str           # System prompt
    tools: list[str] | None  # Allowed tools
    model: str | None     # Model override
```

## MCP Server Configuration

**SDK Server**: `{"type": "sdk", "name": str, "instance": Any}`

**Stdio Server**: `{"command": str, "args": list, "env": dict}`

**SSE Server**: `{"type": "sse", "url": str, "headers": dict}`

**HTTP Server**: `{"type": "http", "url": str, "headers": dict}`

## Key Patterns

**Use query() for:** One-off tasks, independent operations, simple automation

**Use ClaudeSDKClient for:** Continuing conversations, interactive interfaces, response-driven logic

**Avoid breaking early:** Don't use `break` when iterating; let iterations complete naturally to prevent asyncio cleanup issues.
