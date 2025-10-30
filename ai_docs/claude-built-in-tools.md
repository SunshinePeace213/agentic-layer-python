# Claude Code Built-in Tools

This document lists all core, built-in non-MCP development tools available to Claude Code.

## Agent & Task Management

### Task
```typescript
Task(
  description: string,
  prompt: string,
  subagent_type: string,
  model?: "sonnet" | "opus" | "haiku",
  resume?: string
)
```
Launch specialized agents for complex tasks. Available agent types:
- `general-purpose` - General research and multi-step tasks
- `Explore` - Fast codebase exploration specialist
- `Plan` - Planning specialist
- `docs-scraper` - Documentation scraping specialist
- `meta-agent` - Generates new Claude Code sub-agent configurations
- `statusline-setup` - Configure status line settings
- `output-style-setup` - Create output styles

## Shell & Command Execution

### Bash
```typescript
Bash(
  command: string,
  description?: string,
  timeout?: number,
  run_in_background?: boolean,
  dangerouslyDisableSandbox?: boolean
)
```
Execute shell commands in a persistent session with optional timeout and background execution.

### BashOutput
```typescript
BashOutput(
  bash_id: string,
  filter?: string
)
```
Retrieve output from running or completed background bash shells.

### KillShell
```typescript
KillShell(
  shell_id: string
)
```
Terminate a running background bash shell by its ID.

## File Operations

### Read
```typescript
Read(
  file_path: string,
  offset?: number,
  limit?: number
)
```
Read files from the filesystem. Supports:
- Text files
- Images (PNG, JPG, etc.)
- PDF files
- Jupyter notebooks (.ipynb)

### Write
```typescript
Write(
  file_path: string,
  content: string
)
```
Write or overwrite files on the filesystem.

### Edit
```typescript
Edit(
  file_path: string,
  old_string: string,
  new_string: string,
  replace_all?: boolean
)
```
Perform exact string replacements in files.

### NotebookEdit
```typescript
NotebookEdit(
  notebook_path: string,
  new_source: string,
  cell_id?: string,
  cell_type?: "code" | "markdown",
  edit_mode?: "replace" | "insert" | "delete"
)
```
Edit Jupyter notebook cells with support for insert, replace, and delete operations.

## File Search & Pattern Matching

### Glob
```typescript
Glob(
  pattern: string,
  path?: string
)
```
Fast file pattern matching with glob patterns. Examples:
- `**/*.js` - All JavaScript files
- `src/**/*.ts` - All TypeScript files in src directory

### Grep
```typescript
Grep(
  pattern: string,
  path?: string,
  glob?: string,
  type?: string,
  output_mode?: "content" | "files_with_matches" | "count",
  "-i"?: boolean,
  "-n"?: boolean,
  "-A"?: number,
  "-B"?: number,
  "-C"?: number,
  head_limit?: number,
  multiline?: boolean
)
```
Search file contents using regex patterns (powered by ripgrep). Supports:
- Full regex syntax
- File filtering by glob or type
- Context lines (before/after)
- Multiple output modes
- Case-insensitive search
- Multiline matching

## Web & Network

### WebFetch
```typescript
WebFetch(
  url: string,
  prompt: string
)
```
Fetch and analyze web content with AI processing. Converts HTML to markdown and processes with specified prompt.

### WebSearch
```typescript
WebSearch(
  query: string,
  allowed_domains?: string[],
  blocked_domains?: string[]
)
```
Search the web for current information with optional domain filtering.

## User Interaction

### AskUserQuestion
```typescript
AskUserQuestion(
  questions: Array<{
    question: string,
    header: string,
    options: Array<{
      label: string,
      description: string
    }>,
    multiSelect: boolean
  }>,
  answers?: object
)
```
Ask user questions with multiple choice options (1-4 questions, 2-4 options each).

### TodoWrite
```typescript
TodoWrite(
  todos: Array<{
    content: string,
    status: "pending" | "in_progress" | "completed",
    activeForm: string
  }>
)
```
Create and manage structured task lists for tracking progress.

## Planning & Commands

### ExitPlanMode
```typescript
ExitPlanMode(
  plan: string
)
```
Exit planning mode and present implementation plan to user for approval.

### SlashCommand
```typescript
SlashCommand(
  command: string
)
```
Execute custom slash commands from `.claude/commands` directory.

### Skill
```typescript
Skill(
  command: string
)
```
Execute specialized skills within the main conversation.
