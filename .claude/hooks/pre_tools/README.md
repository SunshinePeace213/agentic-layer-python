# PreToolUse Hooks

This directory contains Claude Code hooks that execute before tools are used.

## Available Hooks

### destructive_command_blocker.py

**Purpose**: Prevents execution of dangerous bash commands in Claude Code during development by validating bash commands before execution to protect against accidental system damage.

**Hook Event**: PreToolUse
**Monitored Tool**: Bash
**Version**: 1.0.0

#### Why Use This Hook?

During AI-assisted development, Claude Code may attempt to execute potentially destructive commands that could cause serious system damage:

- **Permanent Data Loss**: Commands like `rm -rf /` can delete entire filesystems
- **System Instability**: Fork bombs and process termination can make systems unresponsive
- **Security Compromises**: Dangerous permission changes and system file overwrites
- **Irreversible Damage**: Disk formatting and partition operations
- **Resource Exhaustion**: Network attacks and cryptocurrency miners

This hook serves as a safety net against commands that could cause irreversible damage, providing educational feedback and safe alternatives.

#### How It Works

The hook intercepts Bash tool operations and validates commands before execution:

1. **Check Allow-List**: Safe variations (e.g., `rm -i`, `--help`) are immediately allowed
2. **Pattern Analysis**: Scans command against 8 categories of dangerous patterns
3. **Educational Blocking**: Provides clear explanations and safe alternatives when blocking
4. **Fail-Safe Behavior**: Allows operations on errors to avoid workflow disruption

#### Dangerous Command Categories

**1. Destructive File Operations**
- `rm -rf /`, `rm -rf /*`, `rm -rf /usr`, `rm -rf ~/`, `rm -rf *`
- Deletes large portions of filesystem
- Results in permanent, irreversible data loss

**2. Disk Overwrite Operations**
- `dd if=/dev/zero of=/dev/sda`, `echo data > /dev/sda`
- Directly writes to disk devices, corrupting filesystems
- Makes systems completely unbootable

**3. Fork Bombs**
- `:(){ :|:& };:`, `perl -e "fork while fork"`
- Creates exponentially growing processes
- Exhausts system resources, requires hard reboot

**4. Dangerous Permission Changes**
- `chmod 777 /etc`, `chmod -R 777 /`
- Compromises system security
- Enables privilege escalation attacks

**5. System File Overwriting**
- `echo hack > /etc/passwd`, `cat malware > /bin/ls`
- Corrupts critical system configuration
- May render system unbootable

**6. Format Operations**
- `mkfs.ext4 /dev/sda1`, `fdisk /dev/sda`
- Formats disks and partitions
- All data permanently lost

**7. Critical Process Termination**
- `kill -9 1`, `killall -9 systemd`
- Kills essential system processes
- Causes system instability

**8. Additional Dangerous Commands**
- System shutdown, kernel module manipulation, network attacks
- Various system stability and security risks

#### Examples

**Blocked Operations**:
```bash
# Destructive file deletion
rm -rf /
# ❌ Blocked: Will destroy the entire operating system

# Disk overwrite
dd if=/dev/zero of=/dev/sda
# ❌ Blocked: Will erase all data on disk

# Fork bomb
:(){ :|:& };:
# ❌ Blocked: Will exhaust all system resources

# System file corruption
echo "hacker::0:0:::/bin/bash" > /etc/passwd
# ❌ Blocked: Compromises system authentication

# Disk formatting
mkfs.ext4 /dev/sda1
# ❌ Blocked: Will format partition and erase all data
```

**Allowed Operations**:
```bash
# Safe file deletion
rm file.txt
# ✅ Allowed: Specific file deletion

# Interactive deletion
rm -i unwanted.txt
# ✅ Allowed: Prompts for confirmation

# Project-relative deletion
rm -r ./old_project/
# ✅ Allowed: Project directory only

# Help commands
rm --help
# ✅ Allowed: Documentation queries

# Normal operations
ls -la
git status
npm install
# ✅ Allowed: Regular development commands
```

#### Error Messages

When a dangerous command is detected, you'll see a comprehensive error message:

```
⚠️ BLOCKED: Dangerous command detected

Command: rm -rf /
Category: Destructive File Operations
Pattern: rm -rf with root path

Why this is dangerous:
  - Attempts to recursively delete the entire filesystem
  - Will destroy the operating system
  - Results in permanent, irreversible data loss
  - Makes the system completely unbootable
  - No recovery possible without full reinstallation

Safe alternatives:
  - Delete specific files: rm file.txt
  - Delete with confirmation: rm -i unwanted_files
  - Delete project files only: rm -r ./old_project/
  - Preview deletion: ls -R directory_to_delete/

If you absolutely must run this command:
  1. Exit Claude Code
  2. Run the command manually in a terminal
  3. Understand the risks fully before proceeding

This protection exists to prevent accidental system damage.
```

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/destructive_command_blocker.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Bash",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the comprehensive test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_destructive_command_blocker.py
```

Manual testing:
```bash
# Test dangerous command (blocked)
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | \
  uv run .claude/hooks/pre_tools/destructive_command_blocker.py

# Test safe command (allowed)
echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' | \
  uv run .claude/hooks/pre_tools/destructive_command_blocker.py

# Test interactive deletion (allowed)
echo '{"tool_name":"Bash","tool_input":{"command":"rm -i file.txt"}}' | \
  uv run .claude/hooks/pre_tools/destructive_command_blocker.py
```

#### Performance

- **Execution Time**: < 50ms per invocation
- **Memory Usage**: < 10 MB
- **Pattern Coverage**: 8 major categories, 40+ specific patterns
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Comprehensive Pattern Detection**: Covers all major categories of destructive commands
- **Case-Insensitive Matching**: Catches `RM -RF /` equally as `rm -rf /`
- **Fail-Safe Behavior**: Allows operations on errors to avoid disrupting development
- **ReDoS Protection**: Simple, non-backtracking regex patterns
- **Educational Feedback**: Clear explanations help developers understand risks

#### Known Limitations

The hook cannot detect all evasion techniques:

- **Base64 Encoding**: `echo cm0gLXJmIC8= | base64 -d | bash`
- **Command Obfuscation**: `r''m -rf /` with quotes
- **Variable Expansion**: `CMD="rm -rf" && $CMD /`
- **Script Files**: Writing dangerous commands to files, then executing them

**Important**: This is a **safety net for accidents**, not a security sandbox. The goal is to catch unintentional dangerous commands and provide education, not to prevent determined malicious actors.

#### False Positives

The hook prioritizes preventing false negatives (missing dangerous commands) over false positives:

- **Rationale**: Missing a dangerous command = potential system damage (high cost)
- **Trade-off**: Blocking a safe command = workflow interruption (low cost)
- **Solution**: Users can temporarily disable the hook if needed for legitimate use cases

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/destructive_command_blocker.py`
4. Enable debug mode: `claude --debug`

**Command incorrectly blocked**:
- Review the error message to understand why it was blocked
- Consider if there's a safer alternative approach
- Temporarily disable the hook if the command is truly safe in your context

**Command not detected**:
- The hook uses regex patterns with word boundaries
- Check the test suite for examples of detected patterns
- Consider submitting an issue if you find a dangerous pattern that should be blocked

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/destructive-command-blocker-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Test Suite](../../../tests/claude-hook/pre_tools/test_destructive_command_blocker.py)

---

### uv_workflow_enforcer.py

**Purpose**: Enforces UV-based Python workflow by preventing direct execution of `pip`, `python`, and `python3` commands.

**Hook Event**: PreToolUse
**Monitored Tools**: Bash
**Version**: 2.0.0

#### Why Use This Hook?

Direct usage of `pip`, `python`, and `python3` commands bypasses UV's modern Python project management workflow and creates several critical issues:

- **Environment Fragmentation**: Direct `python` usage doesn't leverage UV's automatic environment management
- **Dependency Drift**: Using `pip install` without UV breaks lock file consistency and reproducibility
- **Performance Loss**: Missing UV's parallel installation and caching optimizations
- **Version Inconsistency**: Direct `python` may use wrong Python version vs. project requirements
- **Workflow Confusion**: Mixing UV and traditional tools creates unclear dependency management practices
- **Missing Isolation**: Direct installations pollute global or system environments
- **Broken Reproducibility**: Changes not tracked in UV's lock file can't be reproduced by team members

This hook ensures all Python operations use UV commands, maintaining consistency and leveraging UV's benefits.

#### How It Works

The hook intercepts Bash tool operations and validates commands:

1. **Parse Command**: Splits command into segments to handle chains, pipes, and compound commands
2. **Check Allow-List**: Commands using UV (e.g., `uv run python`) are immediately allowed
3. **Detect Blocked Patterns**: Searches for direct `pip`, `python`, or `python3` usage
4. **Provide Alternatives**: Returns specific UV command alternatives when blocking

#### Detected Command Patterns

**Blocked pip Commands**:
- `pip install requests`
- `pip3 install numpy`
- `pip uninstall flask`
- `python -m pip install pandas`
- `python3 -m pip install scipy`

**Blocked python Commands**:
- `python script.py`
- `python3 app.py --arg value`
- `python -m pytest tests/`
- `python3 -m http.server 8000`
- `python -c "print('hello')"`
- `python` (REPL)

**Allowed Commands**:
- `uv run python script.py`
- `uv pip install requests`
- `uv add numpy`
- `uv tool run ruff`
- `python --help`
- `git status` (non-Python commands)

#### Examples

**Blocked Operations**:
```bash
# Direct pip usage
pip install requests
# ❌ Blocked: Use 'uv add requests' or 'uv pip install requests'

# Direct python script
python main.py
# ❌ Blocked: Use 'uv run main.py'

# Python module execution
python -m pytest tests/
# ❌ Blocked: Use 'uv run -m pytest tests/'
```

**Allowed Operations**:
```bash
# UV-managed Python
uv run python script.py
# ✅ Allowed

# UV pip interface
uv pip install requests
# ✅ Allowed

# UV project dependencies
uv add numpy
# ✅ Allowed

# Non-Python commands
git status
# ✅ Allowed
```

#### Error Messages

When a blocked operation is detected, you'll see a helpful error message like:

```
🚫 Blocked: Direct pip usage bypasses UV dependency management

Command: pip install requests

Why this is blocked:
  - Bypasses UV's lock file (uv.lock)
  - Breaks reproducibility for your team
  - Misses UV's parallel installation optimizations
  - Installs into wrong environment
  - Creates dependency drift over time

Use UV instead:

  For project dependencies:
    uv add requests              # Add to project + update lock file
    uv add --dev pytest          # Add dev dependency
    uv add 'requests>=2.28'      # Add with version constraint

  For one-off installations:
    uv pip install requests      # Use UV's pip interface
    uv tool install ruff         # Install CLI tools

  To sync environment:
    uv sync                      # Install from lock file
    uv sync --all-extras         # Include all optional dependencies

Learn more: https://docs.astral.sh/uv/concepts/dependencies/
```

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_workflow_enforcer.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Bash",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_uv_workflow_enforcer.py
```

Manual testing:
```bash
# Test blocked pip command
echo '{"tool_name":"Bash","tool_input":{"command":"pip install requests"}}' | \
  uv run .claude/hooks/pre_tools/uv_workflow_enforcer.py

# Test blocked python command
echo '{"tool_name":"Bash","tool_input":{"command":"python script.py"}}' | \
  uv run .claude/hooks/pre_tools/uv_workflow_enforcer.py

# Test allowed UV command
echo '{"tool_name":"Bash","tool_input":{"command":"uv run python script.py"}}' | \
  uv run .claude/hooks/pre_tools/uv_workflow_enforcer.py
```

#### Performance

- **Execution Time**: < 50ms per invocation
- **Memory Usage**: < 5 MB
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Read-Only Operation**: Hook analyzes commands but never executes them
- **Regex Safety**: Uses simple, bounded patterns to avoid ReDoS attacks
- **Fail-Safe Behavior**: Allows operations on errors to avoid disrupting development
- **Input Validation**: Validates all inputs before processing

#### Known Limitations

The hook cannot detect:
- **Shell aliases**: `alias py=python` then `py script.py`
- **Environment manipulation**: Custom PATH settings
- **Complex shell syntax**: Obscure shell constructs
- **Indirect execution**: Writing a script with python commands, then executing it

This is **workflow enforcement**, not security. The goal is to catch **accidental** usage and help developers learn UV workflows.

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/uv_workflow_enforcer.py`
4. Enable debug mode: `claude --debug`

**False positives**:
- If you need to run direct python/pip commands for a specific reason, temporarily disable the hook

**Command not detected**:
- The hook uses regex patterns with word boundaries - ensure the command matches expected patterns
- Check test suite for examples of detected patterns

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/uv-workflow-enforcer-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [UV CLI Documentation](https://docs.astral.sh/uv/)
- [UV Dependencies Guide](https://docs.astral.sh/uv/concepts/dependencies/)

---

### tmp_creation_blocker.py

**Purpose**: Prevents file creation in system temporary directories during Claude Code development operations.

**Hook Event**: PreToolUse
**Monitored Tools**: Write, Edit, Bash
**Version**: 2.1.0

#### Why Use This Hook?

System temporary directories (e.g., `/tmp/`, `C:\Temp\`, `$TMPDIR`) present several challenges in development:

- **Lack of Observability**: Files scattered in system temp directories are not visible in your project workspace
- **Version Control Issues**: Cannot track or commit temporary artifacts that may be needed for debugging
- **Auto-deletion Risk**: System cleanup processes may delete important development artifacts
- **Poor Organization**: Files spread across system locations are harder to manage and locate
- **Cross-platform Issues**: Different platforms have different temp directory conventions

This hook encourages the use of project-local directories instead, ensuring better observability, version control integration, and workflow management.

#### How It Works

The hook intercepts Write, Edit, and Bash tool operations and validates file paths:

1. **For Write/Edit tools**: Checks the `file_path` parameter
2. **For Bash commands**: Parses commands to extract file creation paths from:
   - Redirect operators: `>`, `>>`, `2>`, `&>`
   - `touch` command
   - `tee` command

If a path is detected in a system temporary directory, the operation is blocked with a helpful error message.

#### Examples

**Blocked Operations**:
```bash
# Write tool
Write("/tmp/data.json", content='{"test": true}')
# ❌ Blocked: /tmp/data.json

# Bash redirect
echo "output" > /tmp/result.txt
# ❌ Blocked: /tmp/result.txt

# Touch command
touch /tmp/marker.txt
# ❌ Blocked: /tmp/marker.txt
```

**Allowed Operations**:
```bash
# Project-relative paths
Write("./tmp/data.json", content='{"test": true}')
# ✅ Allowed: ./tmp/data.json

# Bash redirect to project directory
echo "output" > ./tmp/result.txt
# ✅ Allowed: ./tmp/result.txt

# Touch in project directory
touch ./workspace/marker.txt
# ✅ Allowed: ./workspace/marker.txt
```

#### Error Messages

When a blocked operation is detected, you'll see a helpful error message like:

```
📂 Blocked: File creation in system temporary directory

Path: /tmp/data.json

Why this is blocked:
  - Files in system temp directories are not visible in your project workspace
  - Cannot be tracked by git for version control
  - May be automatically deleted by the system
  - Scattered outside your project directory structure
  - Harder to manage and locate during development

Recommended alternatives:
  - Create in project: ./tmp/data.json
  - Use project subdirectory: ./output/data.json
  - Use workspace directory: ./workspace/data.json

To create the directory: mkdir -p ./tmp

This keeps all development artifacts organized and trackable.
```

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/tmp_creation_blocker.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Write|Edit|Bash",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_tmp_creation_blocker.py
```

Manual testing:
```bash
# Test blocked path
echo '{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.txt"}}' | \
  uv run .claude/hooks/pre_tools/tmp_creation_blocker.py

# Test allowed path
echo '{"tool_name":"Write","tool_input":{"file_path":"./tmp/test.txt"}}' | \
  uv run .claude/hooks/pre_tools/tmp_creation_blocker.py
```

#### Cross-Platform Support

The hook detects temporary directories on:

- **Unix/Linux**: `/tmp`, `/var/tmp`
- **macOS**: `/tmp`, `/var/tmp`, `/private/tmp`, `/private/var/tmp`
- **Windows**: `C:\Temp`, `C:\Windows\Temp`
- **Environment Variables**: `TMPDIR`, `TEMP`, `TMP`

#### Performance

- **Execution Time**: < 100ms per invocation
- **Memory Usage**: < 10 MB
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Path Normalization**: Prevents path traversal attacks
- **Symlink Resolution**: Ensures accurate path comparison on systems with symlinks
- **Fail-Safe Behavior**: Allows operations on errors to avoid disrupting development
- **Input Validation**: Validates all inputs before processing

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/tmp_creation_blocker.py`
4. Enable debug mode: `claude --debug`

**False positives**:
- The hook may block legitimate use cases. Use project-local directories instead, or temporarily disable the hook.

**Path not detected**:
- Check if the path is in a system temp directory: `uv run python -c "from tmp_creation_blocker import get_all_temp_directories; print(get_all_temp_directories())"`

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/tmp-creation-blocker-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)

---

### uv_dependency_blocker.py

**Purpose**: Prevents direct editing of Python dependency files to enforce the use of UV commands for dependency management during development.

**Hook Event**: PreToolUse
**Monitored Tools**: Write, Edit
**Version**: 1.0.0

#### Why Use This Hook?

Direct manual editing of Python dependency files bypasses UV's dependency management workflow and creates several critical issues:

- **Lock File Inconsistency**: Manual edits to `requirements.txt` or `pyproject.toml` don't update `uv.lock`, breaking reproducibility
- **Dependency Resolution Bypass**: UV's sophisticated dependency resolver won't validate compatibility when files are edited directly
- **Version Conflicts**: Manual version specifications may conflict with other dependencies without validation
- **Missing Transitive Dependencies**: Adding packages manually doesn't include their required dependencies
- **Platform-Specific Issues**: Direct edits miss UV's platform-specific dependency handling
- **Workflow Fragmentation**: Mixing manual edits with UV commands creates confusion about the source of truth
- **Team Synchronization**: Manual changes harder to track, review, and replicate across team members

This hook ensures all dependency operations use UV commands, maintaining consistency and leveraging UV's advanced dependency resolution.

#### How It Works

The hook intercepts Write and Edit tool operations and validates file paths:

1. **Parse Input**: Extracts tool name and file path from hook input
2. **Check File Type**: Determines if the file is a dependency file (case-insensitive)
3. **Provide Alternatives**: Returns specific UV command alternatives when blocking

#### Detected Dependency Files

**Blocked Files**:
- `uv.lock` - UV lock file (automatically generated, never edit manually)
- `pyproject.toml` - PEP 621 project metadata and dependencies
- `requirements.txt` - Standard pip requirements
- `requirements-*.txt` - Requirements variants (dev, test, prod, etc.)
- `Pipfile` - Pipenv dependency specification
- `Pipfile.lock` - Pipenv lock file

**Detection Features**:
- **Case-insensitive**: Matches `UV.LOCK`, `PyProject.Toml`, `REQUIREMENTS.TXT`
- **Path-agnostic**: Detects files in any directory (project root, subdirectories, etc.)
- **Requirements variants**: Catches all `requirements*.txt` patterns

#### Examples

**Blocked Operations**:
```bash
# Write tool - uv.lock
Write("uv.lock", content="# Modified lock file")
# ❌ Blocked: UV lock files should never be edited manually

# Edit tool - pyproject.toml
Edit("./pyproject.toml", old_string="old_dep", new_string="new_dep")
# ❌ Blocked: Use UV commands for dependency management

# Write tool - requirements.txt
Write("requirements-dev.txt", content="pytest==7.0.0")
# ❌ Blocked: Use 'uv add --dev pytest==7.0.0'
```

**Allowed Operations**:
```bash
# Write tool - regular Python file
Write("src/main.py", content="print('hello')")
# ✅ Allowed: Regular Python files

# Edit tool - non-dependency file
Edit("setup.py", old_string="old", new_string="new")
# ✅ Allowed: Not a dependency file

# Read tool - dependency files
Read("pyproject.toml")
# ✅ Allowed: Reading is permitted
```

#### Error Messages

When a blocked operation is detected, you'll see a helpful error message like:

```
📦 Blocked: Direct editing of pyproject.toml

File: pyproject.toml

Direct edits bypass UV's dependency management. Use UV commands for consistency.

Common operations:
  uv add <package>           # Add dependency
  uv add --dev <package>     # Add dev dependency
  uv add --optional <group> <package>  # Add to optional group
  uv remove <package>        # Remove dependency
  uv lock                    # Update lock file after changes

For non-dependency edits (metadata, tool config):
  - Temporarily disable this hook if needed
  - Use uv init for initial project setup

Learn more: https://docs.astral.sh/uv/concepts/dependencies/
```

Each file type has specific error messages with relevant UV command alternatives.

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/uv_dependency_blocker.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook (e.g., to edit pyproject.toml metadata):

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Write|Edit",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_uv_dependency_blocker.py
```

Manual testing:
```bash
# Test blocked uv.lock edit
echo '{"tool_name":"Write","tool_input":{"file_path":"uv.lock","content":"test"}}' | \
  uv run .claude/hooks/pre_tools/uv_dependency_blocker.py

# Test blocked pyproject.toml edit
echo '{"tool_name":"Edit","tool_input":{"file_path":"./pyproject.toml","old_string":"old","new_string":"new"}}' | \
  uv run .claude/hooks/pre_tools/uv_dependency_blocker.py

# Test allowed regular file
echo '{"tool_name":"Write","tool_input":{"file_path":"main.py","content":"print()"}}' | \
  uv run .claude/hooks/pre_tools/uv_dependency_blocker.py
```

#### Performance

- **Execution Time**: < 50ms per invocation
- **Memory Usage**: < 5 MB
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Read-Only Operation**: Hook analyzes file paths but never modifies files
- **Fail-Safe Behavior**: Allows operations on errors to avoid disrupting development
- **Input Validation**: Validates all inputs before processing
- **No Path Execution**: Only examines basenames, never executes paths

#### Known Limitations

The hook cannot detect:
- **Bash commands**: `echo "dep" >> requirements.txt` bypasses Write/Edit tools
- **MultiEdit tool**: Not currently monitored (could be added if needed)
- **Indirect edits**: Writing to a file that later becomes a dependency file

This is **workflow enforcement**, not security. The goal is to catch **accidental** edits and help developers learn UV workflows.

#### pyproject.toml Special Case

**Note**: The hook blocks ALL `pyproject.toml` edits, including non-dependency sections (metadata, tool configurations).

**Rationale**:
- Most pyproject.toml edits in UV projects are dependency-related
- Content-aware parsing would be complex and slow
- Non-dependency metadata can be added via `uv init` or by temporarily disabling the hook

**For non-dependency edits**:
1. Temporarily disable this hook
2. Make your metadata/tool configuration changes
3. Re-enable the hook

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/uv_dependency_blocker.py`
4. Enable debug mode: `claude --debug`

**Need to edit pyproject.toml for metadata**:
- Temporarily disable the hook using one of the methods above
- Make your changes
- Re-enable the hook

**File not detected**:
- The hook uses case-insensitive basename matching
- Check if the filename exactly matches expected patterns
- Subdirectory locations are supported

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/uv-dependency-blocker-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [UV Dependencies Guide](https://docs.astral.sh/uv/concepts/dependencies/)
- [UV pip Interface](https://docs.astral.sh/uv/pip/)

---

### pep8_naming_enforcer.py

**Purpose**: Enforces PEP 8 naming conventions for Python code before files are written, ensuring consistent and Pythonic code style across the project.

**Hook Event**: PreToolUse
**Monitored Tools**: Write, Edit
**Version**: 1.0.0

#### Why Use This Hook?

Inconsistent naming conventions can significantly reduce code readability and maintainability in Python projects:

- **Inconsistent Naming**: Developers may use inconsistent naming conventions (camelCase, PascalCase, snake_case) inappropriately
- **Style Drift**: Without automated enforcement, code style can drift from PEP 8 standards over time
- **Code Review Burden**: Manual code review must catch naming violations, slowing development
- **Learning Curve**: New Python developers may not be familiar with PEP 8 conventions
- **Mixed Conventions**: Teams migrating from other languages may bring non-Pythonic naming patterns

This hook automatically validates all Python identifiers against PEP 8 standards before files are written, providing immediate educational feedback.

#### How It Works

The hook intercepts Write and Edit tool operations for Python files:

1. **Parse Python Code**: Uses Python's AST (Abstract Syntax Tree) to parse the code
2. **Extract Identifiers**: Collects all classes, functions, variables, constants, and arguments
3. **Validate Against PEP 8**: Checks each identifier against PEP 8 naming rules
4. **Provide Feedback**: Returns detailed error messages with concrete suggestions for fixes

#### PEP 8 Rules Enforced

**Classes**: CapWords (CamelCase)
- ✅ Valid: `MyClass`, `HTTPServer`, `UserProfile`, `_PrivateClass`
- ❌ Invalid: `myClass`, `my_class`, `MYCLASS`, `My_Class`

**Functions/Methods**: lowercase_with_underscores (snake_case)
- ✅ Valid: `get_user_data`, `calculate_total`, `_private_func`, `__init__`
- ❌ Invalid: `GetUserData`, `getUserData`, `GET_USER_DATA`

**Variables**: lowercase_with_underscores (snake_case)
- ✅ Valid: `user_count`, `total_price`, `_private_var`, `class_`
- ❌ Invalid: `userName`, `UserName`, `USER_COUNT`

**Constants**: UPPER_CASE_WITH_UNDERSCORES
- ✅ Valid: `MAX_SIZE`, `API_KEY`, `DEFAULT_TIMEOUT`
- ❌ Invalid: `maxSize`, `Max_Size`, `max_size` (at module level)

**Special Cases**:
- Magic methods allowed: `__init__`, `__str__`, `__repr__`
- Private names allowed: `_internal`, `__private`
- Keyword conflicts allowed: `class_`, `type_`, `id_`
- Single-char loop vars allowed: `i`, `j`, `k`, `x`, `y`, `z`, `n`, `m`
- Reserved names blocked: `l`, `O`, `I` (look like numbers)

#### Examples

**Blocked Operations**:
```python
# Write tool with invalid class name
Write("user.py", content='''
class userProfile:  # ❌ Should be UserProfile
    def GetData(self):  # ❌ Should be get_data
        userName = "test"  # ❌ Should be user_name
        return userName
''')
# Blocked with detailed error message
```

**Allowed Operations**:
```python
# Write tool with valid Python code
Write("user.py", content='''
class UserProfile:  # ✅ CapWords
    def __init__(self):
        self.user_name = ""  # ✅ snake_case

    def get_user_name(self):  # ✅ snake_case
        return self.user_name
''')
# Allowed
```

#### Error Messages

When naming violations are detected, you'll see a comprehensive error message like:

```
🐍 Blocked: PEP 8 naming convention violations

File: user.py

❌ Violations found:

1. Class 'userProfile' (line 1)
   Issue: Class names must use CapWords (CamelCase)
   Suggestion: Rename to 'UserProfile'
   Rule: PEP 8 requires class names to start with uppercase and use CapWords

2. Function 'GetData' (line 2)
   Issue: Function names must use lowercase_with_underscores
   Suggestion: Rename to 'get_data'
   Rule: PEP 8 requires function names to be lowercase with underscores

3. Variable 'userName' (line 3)
   Issue: Variable names must use lowercase_with_underscores
   Suggestion: Rename to 'user_name'
   Rule: PEP 8 requires variable names to be lowercase with underscores

Total violations: 3

PEP 8 Naming Quick Reference:
  • Classes: CapWords (MyClass, HTTPServer)
  • Functions: lowercase_with_underscores (get_user, calculate_total)
  • Variables: lowercase_with_underscores (user_count, is_valid)
  • Constants: UPPER_CASE_WITH_UNDERSCORES (MAX_SIZE, API_KEY)
  • Private: _leading_underscore (_internal_method, _private_var)

Learn more: https://peps.python.org/pep-0008/#naming-conventions
```

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/pep8_naming_enforcer.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Write|Edit",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py
```

Manual testing:
```bash
# Test valid Python code (allowed)
cat > ./tmp/test_valid.json << 'EOF'
{"tool_name":"Write","tool_input":{"file_path":"test.py","content":"class MyClass:\n    def get_value(self):\n        return 42"}}
EOF
cat ./tmp/test_valid.json | uv run ./.claude/hooks/pre_tools/pep8_naming_enforcer.py

# Test invalid Python naming (blocked)
cat > ./tmp/test_invalid.json << 'EOF'
{"tool_name":"Write","tool_input":{"file_path":"test.py","content":"class myClass:\n    def GetValue(self):\n        userName = \"test\"\n        return userName"}}
EOF
cat ./tmp/test_invalid.json | uv run ./.claude/hooks/pre_tools/pep8_naming_enforcer.py

# Test non-Python file (skipped)
cat > ./tmp/test_nonpython.json << 'EOF'
{"tool_name":"Write","tool_input":{"file_path":"test.json","content":"{\"key\": \"value\"}"}}
EOF
cat ./tmp/test_nonpython.json | uv run ./.claude/hooks/pre_tools/pep8_naming_enforcer.py
```

#### Performance

- **Execution Time**: < 200ms for typical Python files (< 500 lines)
- **Memory Usage**: < 50 MB for typical files
- **File Size Limit**: Skips validation for files > 10 MB (fail-safe)
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Static Analysis Only**: Uses AST parsing, never executes code
- **Fail-Safe Behavior**: Allows operations on syntax errors (Python will catch them)
- **Input Validation**: Validates all inputs before processing
- **Resource Limits**: Maximum file size limit prevents DoS attacks
- **No Network Calls**: All validation happens locally

#### Edge Cases Handled

The hook correctly handles:

- **Magic Methods**: `__init__`, `__str__`, `__repr__` (always allowed)
- **Private Names**: `_internal`, `__private` (allowed)
- **Keyword Conflicts**: `class_`, `type_`, `id_` (allowed)
- **Single-Char Variables**: `i`, `j`, `k` (common loop vars allowed)
- **Reserved Names**: `l`, `O`, `I` (blocked as they look like numbers)
- **Type Variables**: `T`, `AnyStr`, `T_co` (allowed)
- **Async Functions**: Same rules as regular functions
- **Empty Files**: Allowed (no validation needed)
- **Syntax Errors**: Allowed (fail-safe, Python will error later)
- **Non-Python Files**: Skipped (only .py files validated)

#### Known Limitations

The hook cannot detect:

- **Dynamic Attribute Creation**: `setattr(obj, "badName", value)`
- **String-Based Access**: `obj.__dict__["badName"]`
- **Generated Code**: May need to skip auto-generated files
- **Third-Party Conventions**: Some libraries require non-PEP-8 names (e.g., Django's `setUp`)

**Solution**: Temporarily disable the hook when working with such cases, or use thin adapter layers.

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/pep8_naming_enforcer.py`
4. Enable debug mode: `claude --debug`

**False positives**:
- Review the error message to understand the violation
- Check if your code actually violates PEP 8
- Consult PEP 8 documentation: https://peps.python.org/pep-0008/

**Command incorrectly allowed**:
- The hook only validates naming conventions, not other PEP 8 rules
- Consider using additional linters like `ruff` for comprehensive validation

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/pep8-naming-enforcer-spec.md)
- [PEP 8 Naming Conventions](https://peps.python.org/pep-0008/#naming-conventions)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Test Suite](../../../tests/claude-hook/pre_tools/test_pep8_naming_enforcer.py)

---

### sensitive_file_access_validator.py

**Purpose**: Prevents Claude Code from reading and writing sensitive files and system locations during development. This hook serves as a critical security control to protect credentials, secrets, private keys, and system files.

**Hook Event**: PreToolUse
**Monitored Tools**: Read, Write, Edit, Bash
**Version**: 1.0.0

#### Why Use This Hook?

During AI-assisted development, Claude Code may attempt to access sensitive files that could:

- **Expose Secrets**: Reading `.env` files or credentials exposes sensitive data in session transcripts
- **Create Credential Files**: Writing credential files directly bypasses secure credential management practices
- **Modify System Files**: Accidental or intentional writes to system directories can compromise system integrity
- **Leak Private Keys**: Accessing SSH keys or certificates creates security vulnerabilities
- **Violate Security Policies**: Direct access to credential files violates organizational security practices

This hook prevents these scenarios by intercepting file operations before execution and providing educational feedback with secure alternatives.

#### How It Works

The hook intercepts file operations and validates paths before execution:

1. **For Read/Write/Edit tools**: Checks the `file_path` parameter against sensitive file patterns
2. **For Bash commands**: Parses commands to detect file operations (`cat`, `echo >`, `cp`, etc.)
3. **Path Normalization**: Resolves symlinks and expands paths to prevent evasion
4. **Educational Blocking**: Provides clear explanations and secure alternatives when blocking

#### Protected File Categories

**1. Environment Variables**
- `.env`, `.env.local`, `.env.production`, `.env.development`, `.env.test`, `.env.staging`
- Contains sensitive credentials and API keys
- Exposes secrets in session transcripts and logs

**2. SSH Private Keys**
- `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`, `id_ed25519_sk`
- Provides authentication credentials
- Compromised keys create security vulnerabilities

**3. Certificates and Private Keys**
- `.pem`, `.key`, `.crt`, `.cer`, `.pfx`, `.p12`
- `cert.pem`, `privkey.pem`, `fullchain.pem`
- TLS certificates and code signing certificates

**4. Cloud Provider Credentials**
- `.aws/credentials`, `.aws/config`
- `.azure/credentials`
- `.config/gcloud/`
- `.docker/config.json`, `.kube/config`
- Grant broad cloud infrastructure access

**5. Package Manager Credentials**
- `.npmrc`, `.pypirc`, `.gem/credentials`, `.cargo/credentials`, `.nuget/`
- Package registry access tokens
- Potential supply chain attack vectors

**6. VCS and Tool Credentials**
- `.gitconfig`, `.git-credentials`, `.netrc`, `.hgrc`
- Version control system credentials
- Private repository access

**7. Database Credentials**
- `.pgpass`, `.my.cnf`, `database.yml`
- Database access credentials

**8. Generic Credentials**
- `credentials.json`, `credentials.yaml`
- `secrets.json`, `secrets.yaml`, `secrets.toml`
- `token`, `api_key`, `service-account`, `client_secret`
- Generic sensitive data files

#### System Directory Protection

**Unix/Linux System Directories** (write-only):
- `/etc`, `/usr`, `/bin`, `/sbin`, `/boot`, `/sys`, `/proc`, `/dev`, `/lib`, `/lib64`, `/root`

**Windows System Directories** (write-only):
- `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`

**Protected Configuration Directories** (write-only):
- `/.ssh/`, `/.gnupg/`, `/.aws/`, `/.azure/`, `/.docker/`, `/.kube/`, `/.config/gcloud/`, `/.config/gh/`

#### Allowed Template Files

The hook ALLOWS access to template/example files:
- `.env.sample`, `.env.example`, `.env.template`
- `example.env`, `sample.config`
- `credentials.example`, `config.template`

**Rationale**: Template files document required structure without exposing actual credentials.

#### Examples

**Blocked Operations**:
```bash
# Read environment variables
Read(".env")
# ❌ Blocked: Environment variables containing secrets

# Write SSH key
Write("~/.ssh/id_rsa", "-----BEGIN PRIVATE KEY-----")
# ❌ Blocked: SSH private key for authentication

# Edit credentials
Edit("credentials.json", old="old_key", new="new_key")
# ❌ Blocked: Credentials file

# Bash read operation
Bash("cat .env")
# ❌ Blocked: Bash command attempts to read sensitive file

# Bash write operation
Bash("echo SECRET=value > .env")
# ❌ Blocked: Bash command attempts to write to sensitive file

# Write to system directory
Write("/etc/hosts", "127.0.0.1 localhost")
# ❌ Blocked: Writing to system directory
```

**Allowed Operations**:
```bash
# Read template files
Read(".env.sample")
# ✅ Allowed: Template file with placeholder values

# Write normal files
Write("config.json", '{"setting": "value"}')
# ✅ Allowed: Regular configuration file

# Check file existence
Bash("test -f .env && echo exists")
# ✅ Allowed: Existence check without reading contents

# Write to project directory
Write("./data/output.json", '{"result": 42}')
# ✅ Allowed: Project-local file
```

#### Error Messages

When a sensitive file operation is detected, you'll see a comprehensive error message:

```
🚫 Blocked reading environment variables file.

Path: /project/.env
File Type: Environment variables containing secrets and configuration

Why this is blocked:
  - Environment files contain sensitive credentials and API keys
  - Reading .env exposes secrets in session transcripts and logs
  - Security policy requires secrets to remain outside version control
  - Exposing credentials creates security vulnerabilities

Secure alternatives:
  • Read template structure: Read('.env.sample')
  • Check if file exists: Bash('test -f .env && echo exists')
  • Document required variables in README
  • Use environment variable documentation tools

To understand .env structure:
  1. Create/read .env.sample with placeholder values
  2. Document each variable's purpose and format
  3. Never commit actual .env to version control

This protection prevents accidental credential exposure.
```

Each file type has specific error messages with relevant secure alternatives.

#### Bash Command Detection

The hook parses bash commands to detect file operations:

**Read Commands Detected**:
- `cat`, `less`, `more`, `head`, `tail`
- `grep`, `awk`, `sed`, `tac`, `strings`

**Write Commands Detected**:
- Redirects: `>`, `>>`, `2>`, `&>`, `&>>`
- Copy/move: `cp`, `mv`, `rsync`, `scp`

**Example Detected Commands**:
```bash
cat .env                  # Read operation
less ~/.ssh/id_rsa       # Read operation
echo SECRET > .env       # Write operation
cp prod.env .env         # Copy operation
```

#### Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/sensitive_file_access_validator.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### Disabling the Hook

If you need to temporarily disable this hook:

**Option 1**: Comment out in `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      // {
      //   "matcher": "Read|Write|Edit|Bash",
      //   "hooks": [...]
      // }
    ]
  }
}
```

**Option 2**: Create `.claude/settings.local.json` (gitignored)
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Delete or rename the hook script

#### Testing

Run the comprehensive test suite:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_sensitive_file_access_validator.py
```

Manual testing:
```bash
# Test .env read (blocked)
echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' | \
  uv run .claude/hooks/pre_tools/sensitive_file_access_validator.py

# Test .env.sample read (allowed)
echo '{"tool_name":"Read","tool_input":{"file_path":".env.sample"}}' | \
  uv run .claude/hooks/pre_tools/sensitive_file_access_validator.py

# Test SSH key write (blocked)
echo '{"tool_name":"Write","tool_input":{"file_path":"~/.ssh/id_rsa","content":"key"}}' | \
  uv run .claude/hooks/pre_tools/sensitive_file_access_validator.py

# Test bash cat .env (blocked)
echo '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' | \
  uv run .claude/hooks/pre_tools/sensitive_file_access_validator.py
```

#### Performance

- **Execution Time**: < 100ms for typical operations
- **Memory Usage**: < 10 MB
- **Pattern Coverage**: 8 major categories, 70+ specific patterns
- **Dependencies**: Zero external dependencies (Python 3.12+ standard library only)

#### Security

The hook implements several security measures:

- **Path Normalization**: Prevents path traversal attacks (e.g., `../../.env`)
- **Symlink Resolution**: Detects files even through symlinks
- **Case-Insensitive Matching**: Catches `.ENV`, `Credentials.json`
- **Fail-Safe Behavior**: Allows operations on errors to avoid disrupting development
- **No Code Execution**: Only analyzes paths, never executes commands

#### Known Limitations

The hook cannot detect all evasion techniques:

- **Base64 Encoding**: `echo Y2F0IC5lbnY= | base64 -d | bash` (decodes to `cat .env`)
- **Variable Indirection**: `FILE=".env" && cat $FILE`
- **Command Substitution**: `cat $(echo .env)`
- **Hexadecimal Encoding**: `cat "\x2e\x65\x6e\x76"` (`.env` in hex)
- **Script File Execution**: Writing a script with `cat .env`, then executing it

**Important**: This is **workflow guidance**, not a security sandbox. The goal is to:
- ✅ Prevent accidental credential exposure
- ✅ Educate developers on secure practices
- ✅ Catch common mistakes
- ❌ Not designed to prevent determined malicious actors
- ❌ Not a security boundary

**Philosophy**:
> "Make the right thing easy and the wrong thing hard, but don't make the wrong thing impossible."

#### False Positives vs False Negatives

**Trade-off**: Prioritize preventing false negatives (missing dangerous operations)

- **False Positive**: Block a safe operation → Minor workflow interruption (low cost)
- **False Negative**: Miss a dangerous operation → Potential credential exposure (high cost)

**Decision**: Accept some false positives to ensure comprehensive protection.

**Mitigation**: Users can temporarily disable hook for legitimate use cases.

#### Cross-Platform Support

The hook works on:
- **Unix/Linux**: Full support for all file patterns and system directories
- **macOS**: Full support including symlink resolution (`/etc` → `/private/etc`)
- **Windows**: Full support including Windows-specific system directories

#### Troubleshooting

**Hook not executing**:
1. Check hook is registered: `/hooks` command in Claude Code
2. Verify settings.json is valid JSON
3. Ensure script is executable: `chmod +x .claude/hooks/pre_tools/sensitive_file_access_validator.py`
4. Enable debug mode: `claude --debug`

**Operation incorrectly blocked**:
- Review the error message to understand why it was blocked
- Check if you're accessing a template file (`.env.sample`) instead
- Consider if there's a safer alternative approach
- Temporarily disable the hook if the operation is truly safe in your context

**Sensitive file not detected**:
- The hook uses substring matching on normalized paths
- Check if the file matches expected patterns (case-insensitive)
- Consider submitting an issue if you find a sensitive pattern that should be blocked

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/sensitive-file-access-validator-spec.md)
- [Claude Code Hooks Guide](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Test Suite](../../../tests/claude-hook/pre_tools/test_sensitive_file_access_validator.py)
- [PEP 723 - Inline Script Metadata](https://peps.python.org/pep-0723/)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)

---

### code_similarity_checking.py

**Purpose**: Prevents creation of duplicate or versioned files by detecting similar functionality before allowing Write operations, encouraging Claude to use Edit tool and Git version control instead.

**Hook Event**: PreToolUse
**Monitored Tool**: Write
**Version**: 1.0.0

#### Why Use This Hook?

During AI-assisted development, Claude Code may create multiple versions of the same file instead of updating existing files:

- **Version Proliferation**: Files like `parser_v2.py`, `parser_v3.py`, `parser_final.py` accumulate
- **Backup Clutter**: Unnecessary copies like `utils_copy.py`, `utils_backup.py` created
- **Git Misuse**: Using filename versioning instead of proper Git commits
- **Code Duplication**: Similar functionality spread across multiple files
- **Maintenance Burden**: Bug fixes must be applied to multiple versions
- **Confusion**: Developers unsure which version is current
- **Technical Debt**: Versioned files become permanent clutter

This hook detects when Claude attempts to create a file that appears to be a duplicate or version of an existing file, blocking the operation and encouraging proper practices.

#### How It Works

The hook intercepts Write operations and performs similarity analysis:

1. **Pattern Detection**: Checks filename for versioning patterns (_v2, _copy, (1), etc.)
2. **Directory Monitoring**: Only checks files in configured directories
3. **Base File Search**: Finds potential source file (e.g., `parser.py` for `parser_v2.py`)
4. **Content Similarity**: Compares file contents using difflib (if base file exists)
5. **Threshold Comparison**: Applies configurable similarity thresholds
6. **Educational Blocking**: Provides clear guidance on using Edit tool instead
7. **Git Encouragement**: Reminds Claude to use Git for version control

#### Detected Patterns

**Version Suffix Patterns**:
```python
# Version numbers
parser_v2.py, parser_v3.py        # Blocked if similar
parser_version2.py                # Blocked if similar
parser-v2.py, parser-2.py         # Blocked if similar

# Numbered suffixes
file_2.py, file-3.py              # Blocked if similar
file (1).py, file (2).py          # Blocked if similar

# Date suffixes
utils_20240101.py                 # Blocked if similar
config_2024_10_31.py              # Blocked if similar

# Copy/backup suffixes
parser_copy.py                    # Blocked if similar
parser_backup.py                  # Blocked if similar
parser_old.py                     # Blocked if similar
parser_new.py                     # Blocked if similar
parser_final.py                   # Blocked if similar
```

**Backup Extensions** (always checked):
```python
file.py.bak                       # Blocked if parser.py exists and similar
file.py.old                       # Blocked if parser.py exists and similar
file.py.orig                      # Blocked if parser.py exists and similar
file.py~                          # Blocked if parser.py exists and similar
```

**Allowed Patterns** (never blocked):
```python
file.backup                       # Allowed (explicit .backup extension)
file.py                          # Allowed (no version pattern)
parser_utils.py                  # Allowed (not a version suffix)
```

#### Similarity Thresholds

**High Similarity (>= 0.85)**: **DENY**
```
❌ BLOCKED: Code similarity detected!

You are attempting to create: utils/parser_v2.py
Similar file already exists: utils/parser.py
Content similarity: 92%

Instead of creating a new version:
1. Use Edit tool to modify existing file directly
2. Or use Git to manage versions:
   git add utils/parser.py
   git commit -m "Update parser logic"

This promotes cleaner codebase and proper version control.
```

**Moderate Similarity (0.60-0.85)**: **ALLOW with WARNING**
```
⚠️ Warning: Moderate similarity detected (75%) with utils/parser.py
Consider using Edit tool instead of creating new file.
```

**Low Similarity (< 0.60)**: **ALLOW** (silent)

#### Examples

**Blocked: High Similarity**:
```python
# Scenario: Claude tries to create parser_v2.py
# parser.py already exists with 90% similar content

# Hook Output:
{
  "permissionDecision": "deny",
  "permissionReason": "Code similarity detected...",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionReason": "❌ BLOCKED: Code similarity detected!..."
  }
}

# Result: Write operation blocked, Claude uses Edit instead
```

**Allowed: Different Content**:
```python
# Scenario: Claude creates parser_utils.py (helper module)
# parser.py exists but content is completely different

# Hook Output:
{
  "permissionDecision": "allow",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}

# Result: Write operation allowed
```

**Allowed: Monitored Directory**:
```python
# Scenario: Claude creates script_v2.py in ./scripts/
# Not in monitored directories list

# Result: Hook skips checking, Write operation allowed
```

#### Configuration

Hook registration in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/code_similarity_checking.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Environment Variables**:
```bash
# Enable/disable the hook
CODE_SIMILARITY_ENABLED=true  # default: true

# Similarity threshold for denial (0.0-1.0)
CODE_SIMILARITY_DENY_THRESHOLD=0.85  # default: 0.85

# Similarity threshold for warning (0.0-1.0)
CODE_SIMILARITY_WARN_THRESHOLD=0.60  # default: 0.60

# Monitored directories (colon-separated)
CODE_SIMILARITY_DIRS="./src:./lib:./utils:./components"
```

**Default Monitored Directories**:
```python
./queries
./utils
./components
./src
./lib
./services
./models
./handlers
./.claude/hooks
./tests
```

**Example Configurations**:

Strict mode (block more aggressively):
```bash
export CODE_SIMILARITY_DENY_THRESHOLD=0.70
export CODE_SIMILARITY_WARN_THRESHOLD=0.50
```

Lenient mode (only block very similar files):
```bash
export CODE_SIMILARITY_DENY_THRESHOLD=0.95
export CODE_SIMILARITY_WARN_THRESHOLD=0.85
```

Monitor all directories:
```bash
export CODE_SIMILARITY_DIRS="."
```

#### Behavior Details

**When Hook Triggers**:
- Write tool attempts to create new file → Similarity check performed
- File has version pattern → Search for base file
- File in monitored directory → Content comparison
- Similarity above threshold → Block with educational message

**What Gets Checked**:
- Files with version suffixes (_v2, _copy, etc.)
- Files with backup extensions (.bak, .old, .orig, ~)
- Files in monitored directories only
- Files under 1 MB size (performance optimization)

**What Gets Skipped**:
- Files without version patterns (normal file creation)
- Files with `.backup` extension (explicitly allowed)
- Files outside monitored directories
- Files over 1 MB (too large for quick checking)
- Files when base file doesn't exist
- Files when hook is disabled

**Performance Optimizations**:
1. **Quick Pre-Check**: Detects obviously different files by size
2. **File Size Limit**: Skips files over 1 MB
3. **Directory Filtering**: Only checks configured directories
4. **Pattern Matching**: Fast regex-based version detection
5. **Early Exit**: Returns immediately for non-versioned files

#### Testing

Run comprehensive test suite:
```bash
# Run all tests
uv run pytest tests/claude_hook/pre_tools/test_code_similarity_checking.py -v

# Run with coverage
uv run pytest --cov=.claude/hooks/pre_tools/code_similarity_checking \
  tests/claude_hook/pre_tools/test_code_similarity_checking.py

# Run specific test
uv run pytest tests/claude_hook/pre_tools/test_code_similarity_checking.py::test_blocks_high_similarity -v
```

Manual testing with hook input:
```bash
# Test blocking scenario
echo '{
  "session_id": "test",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "'$(pwd)'/utils/parser_v2.py",
    "content": "def parse():\n    return data"
  },
  "cwd": "'$(pwd)'"
}' | uv run .claude/hooks/pre_tools/code_similarity_checking.py
```

#### Performance

- **Execution Time**: < 500ms for typical files (< 1000 lines)
- **Memory Usage**: < 30 MB for typical comparisons
- **File Size Limit**: 1 MB maximum for similarity checking
- **Algorithm**: difflib.SequenceMatcher (optimized for text)
- **Dependencies**: Zero external dependencies (stdlib only)

**Optimization Strategies**:
- Quick size-based pre-check before full comparison
- Only checks monitored directories (not entire filesystem)
- Caches directory listings (within single execution)
- Early exit for files without version patterns
- File size limit prevents memory issues

#### Security

- **Path Validation**: Uses pathlib for safe path operations
- **Project Boundary**: Respects `$CLAUDE_PROJECT_DIR`
- **Resource Limits**: 1 MB file size limit prevents DoS
- **No Code Execution**: Only reads and compares file contents
- **Error Isolation**: Exceptions don't crash Claude (fail-safe)
- **Read-Only**: Never modifies existing files

#### Integration with Other Tools

**Complementary Hooks**:
- **file_naming_enforcer**: Ensures proper file naming conventions
- **pep8_naming_enforcer**: Validates Python naming in content
- **tmp_creation_blocker**: Prevents temporary file creation

**Git Workflow Integration**:
```bash
# Hook encourages this workflow:
1. Edit existing file directly
2. Commit changes to Git
3. Use Git for version history

# Instead of:
1. Create parser_v2.py
2. Create parser_v3.py
3. Create parser_final.py
```

#### Known Limitations

**False Positives** (similar files that should be separate):
- Files with similar boilerplate (templates, configs)
- Test files with similar setup code
- Legitimately different implementations with same structure
- Files that happen to match version pattern but aren't versions

**Mitigation**:
- Adjust thresholds: Lower DENY_THRESHOLD to be more lenient
- Remove directory from monitoring: Update CODE_SIMILARITY_DIRS
- Use allowed extensions: Name file with `.backup` extension
- Temporarily disable: `export CODE_SIMILARITY_ENABLED=false`

**False Negatives** (duplicate files not caught):
- Files with different naming patterns (no version suffix)
- Files in unmonitored directories
- Files over 1 MB (skipped for performance)
- Files with low textual similarity but same functionality

**Cannot Detect**:
- Semantic similarity (same logic, different code)
- Refactored code (same behavior, different structure)
- Cross-language duplicates (Python vs JavaScript)
- Duplicates in external dependencies

#### Troubleshooting

**Hook blocking legitimate file creation**:
- Check similarity score in error message
- If false positive, adjust threshold: `export CODE_SIMILARITY_DENY_THRESHOLD=0.95`
- Or remove directory from monitoring
- Or use different filename (avoid version patterns)

**Hook not blocking obvious duplicates**:
- Verify file is in monitored directory: `echo $CODE_SIMILARITY_DIRS`
- Check file has version pattern (must match regex)
- Verify similarity is above threshold (>= 0.85 by default)
- Enable hook if disabled: `export CODE_SIMILARITY_ENABLED=true`

**Performance issues with large files**:
- Hook automatically skips files > 1 MB
- For smaller files, increase timeout in settings.json
- Or exclude slow directories from monitoring

**Hook always allows everything**:
- Check CODE_SIMILARITY_ENABLED is not "false"
- Verify monitored directories are configured correctly
- Check filename matches version pattern
- Ensure base file actually exists

#### Use Cases

**When This Hook Helps**:
1. **Preventing Clutter**: Stops accumulation of versioned files
2. **Enforcing Git**: Encourages proper version control usage
3. **Code Review**: Catches unintentional duplicate creation
4. **Onboarding**: Teaches new developers proper practices
5. **Codebase Hygiene**: Maintains clean project structure

**When to Disable**:
1. **Legacy Migration**: When consolidating old versioned files
2. **Rapid Prototyping**: When experimenting with variations
3. **Template Generation**: When creating similar boilerplate
4. **Backup Creation**: When intentionally making safety copies
5. **Testing**: When testing the Write tool behavior

#### Educational Value

The hook teaches important software engineering practices:

**Git Version Control**:
```bash
# ❌ Bad Practice (blocked by hook):
- Create parser_v2.py with changes
- Create parser_v3.py with more changes
- Create parser_final.py

# ✅ Good Practice (encouraged by hook):
- Edit parser.py directly
- git commit -m "Refactor parsing logic"
- git commit -m "Add error handling"
```

**Direct File Updates**:
```bash
# ❌ Bad Practice:
Write("utils/helper_copy.py", "modified code")

# ✅ Good Practice:
Edit("utils/helper.py", old="old code", new="modified code")
```

**Clean Codebase**:
```
# ❌ Before (cluttered):
/utils/
  parser.py
  parser_v2.py
  parser_v3.py
  parser_copy.py
  parser_backup.py
  parser_final.py

# ✅ After (clean):
/utils/
  parser.py

# All versions tracked in Git:
git log utils/parser.py
```

#### Related Documentation

- [Specification](../../../specs/experts/cc_hook_expert/pre_tools/code_similarity_checking-spec.md)
- [Test Suite](../../../tests/claude_hook/pre_tools/test_code_similarity_checking.py)
- [Git Best Practices](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository)
- [difflib Documentation](https://docs.python.org/3/library/difflib.html)

---

## Shared Utilities

All PreToolUse hooks share common utilities from the `utils/` directory:

### data_types.py
- TypedDict definitions for type safety
- `ToolInput`, `HookOutput`, `HookSpecificOutput`
- `PermissionDecision`, `ValidationResult`

**Supported Tool Parameters**:
- `file_path`: File path (Read, Write, Edit tools)
- `content`: File content (Write tool)
- `command`: Shell command (Bash tool)
- `old_string`: String to replace (Edit tool)
- `new_string`: Replacement string (Edit tool)
- `replace_all`: Replace all occurrences flag (Edit tool)

### utils.py
- `parse_hook_input()`: Parse JSON from stdin with full Edit tool support
- `output_decision()`: Format and output JSON decisions
- `get_file_path()`: Extract file path from tool input

### Usage Example

```python
from utils import parse_hook_input, output_decision

def main():
    result = parse_hook_input()
    if result is None:
        output_decision("allow", "Failed to parse input")
        return

    tool_name, tool_input = result

    # Validation logic here
    if is_valid(tool_input):
        output_decision("allow", "Validation passed")
    else:
        output_decision("deny", "Validation failed", suppress_output=True)

if __name__ == "__main__":
    main()
```
