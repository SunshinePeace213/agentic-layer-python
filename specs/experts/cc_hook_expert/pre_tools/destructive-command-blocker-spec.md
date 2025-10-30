# Destructive Command Blocker Hook - Specification

## Metadata

- **Hook Name**: destructive_command_blocker.py
- **Hook Category**: PreToolUse
- **Version**: 1.0.0
- **Author**: Claude Code Hook Expert
- **Last Updated**: 2025-10-30

## 1. Purpose

Prevent execution of dangerous bash commands in Claude Code during development by validating bash commands before execution to protect against accidental system damage. This hook serves as a safety net against commands that could cause irreversible damage to the system, data loss, or system instability.

## 2. Problem Statement

During AI-assisted development, Claude Code may attempt to execute potentially destructive commands that could cause serious system damage:

1. **Destructive File Operations**: Commands like `rm -rf /` that can delete entire filesystems
2. **Disk Overwrite Operations**: Direct disk writes that can corrupt data
3. **Fork Bombs**: Malicious processes that exhaust system resources
4. **Dangerous Permission Changes**: Modifications that compromise system security
5. **System File Overwriting**: Corruption of critical system files
6. **Format Operations**: Disk formatting commands that erase data
7. **Critical Process Termination**: Killing essential system processes
8. **Network Attacks**: Commands that could be used for DoS or unauthorized access

These operations can:
- Cause permanent data loss
- Make the system unbootable
- Compromise system security
- Require complete system reinstallation
- Result in hours of recovery work

## 3. Objectives

1. **Comprehensive Protection**: Block all major categories of destructive commands
2. **Educational Feedback**: Provide clear explanations of why commands are dangerous
3. **Allow-list Support**: Enable safe variations of potentially dangerous commands
4. **Minimal False Positives**: Avoid blocking legitimate development operations
5. **Fail-safe Behavior**: Allow operations on errors to avoid workflow disruption
6. **Zero Dependencies**: Use only Python standard library for maximum portability
7. **Performance**: Execute validation in < 50ms
8. **Integration**: Leverage shared utilities for consistency

## 4. Hook Event Selection

### Selected Event: PreToolUse

**Rationale**:
- Executes **before** command execution, preventing damage before it occurs
- Receives complete command string for pattern analysis
- Can deny operations via `permissionDecision: "deny"`
- Provides opportunity for educational error messages
- Ideal for security validation and policy enforcement

**Alternative Events Considered**:
- **PostToolUse**: Too late - damage would already be done
- **UserPromptSubmit**: Too early - bash command not yet formed
- **SessionStart**: Not appropriate for per-command validation

## 5. Tool Matchers

### Monitored Tool: Bash

The hook exclusively monitors the **Bash** tool, as it's the only built-in Claude Code tool that can execute potentially destructive system commands.

**Matcher Configuration**:
```json
{
  "matcher": "Bash"
}
```

### Tools Explicitly Excluded

- **Write/Edit**: File operations are contained and reversible
- **Read**: Read-only operations cannot cause damage
- **Glob/Grep**: Search operations are safe
- **Other tools**: None pose system-level destruction risks

## 6. Input Schema

### Standard PreToolUse Input Structure

```typescript
{
  session_id: string,           // Unique session identifier
  transcript_path: string,      // Path to transcript JSONL
  cwd: string,                  // Current working directory
  hook_event_name: "PreToolUse",
  tool_name: "Bash",            // Only Bash commands monitored
  tool_input: {
    command: string,            // The bash command to validate
    description?: string,       // Optional command description
    timeout?: number,           // Optional timeout
    run_in_background?: boolean // Optional background flag
  }
}
```

### Command Extraction

```python
command = tool_input.get("command", "")
```

## 7. Output Schema

### JSON Output Format

```typescript
{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow" | "deny",
    permissionDecisionReason: string
  },
  suppressOutput?: boolean  // Optional: hide from transcript
}
```

### Decision Types

#### 7.1 Allow Decision

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Command is safe or uses allowed patterns"
  }
}
```

**Used when**:
- Command matches no dangerous patterns
- Command uses safe variations (e.g., `rm -i` with confirmation)
- Command is in explicit allow-list
- Error occurs (fail-safe behavior)

#### 7.2 Deny Decision

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "⚠️ BLOCKED: Extremely dangerous command detected\n\nCommand: rm -rf /\nCategory: Destructive File Operations\n\nWhy this is extremely dangerous:\n  - Attempts to recursively delete the entire filesystem\n  - Will destroy the operating system\n  - Results in permanent, irreversible data loss\n  - Makes the system completely unbootable\n  - No recovery possible without full reinstallation\n\nThis command should NEVER be executed under any circumstances.\n\nSafe alternatives:\n  - Delete specific files: rm file.txt\n  - Delete with confirmation: rm -i unwanted_files\n  - Delete project files only: rm -r ./old_project/\n  - Preview deletion: ls -R directory_to_delete/"
  },
  "suppressOutput": true
}
```

**Used when**:
- Dangerous pattern detected in command
- Provides category classification
- Explains specific risks
- Offers safe alternatives
- Uses `suppressOutput: true` for cleaner transcript

## 8. Dangerous Command Patterns

### 8.1 Destructive File Operations

**Category Description**: Commands that can delete large amounts of data or critical files.

**Patterns Detected**:

```python
DESTRUCTIVE_FILE_PATTERNS = [
    # Recursive deletion of root or system directories
    (r'\brm\s+.*-[rf]+.*\s+/', "rm -rf with root path"),
    (r'\brm\s+-[rf]+\s+/', "rm -rf of root"),
    (r'\brm\s+.*-[rf]+.*\s+/\s*$', "rm -rf ending with root"),
    (r'\brm\s+.*-[rf]+.*\s+/\w+', "rm -rf of system directory"),

    # Deletion of all files
    (r'\brm\s+.*-[rf]+.*\s+\*', "rm -rf with wildcard"),
    (r'\brm\s+-[rf]+\s+\.\*', "rm -rf of dot files"),

    # Critical system directories
    (r'\brm\s+.*-[rf]+.*/(?:bin|boot|dev|etc|lib|proc|root|sbin|sys|usr|var)\b', "rm -rf of system directory"),
]
```

**Examples Blocked**:
```bash
rm -rf /                    # Delete entire filesystem
rm -rf /*                   # Delete all root directories
rm -rf /usr                 # Delete system binaries
rm -rf /etc                 # Delete system configuration
rm -rf ~/*                  # Delete entire home directory
rm -rf .                    # Delete current directory
rm -rf *                    # Delete all files in current directory
```

**Examples Allowed**:
```bash
rm file.txt                 # Delete single file
rm -i unwanted.txt          # Delete with confirmation
rm -r ./old_project/        # Delete specific project directory
```

### 8.2 Disk Overwrite Operations

**Category Description**: Commands that directly write to disk devices, potentially corrupting filesystems.

**Patterns Detected**:

```python
DISK_OVERWRITE_PATTERNS = [
    # Direct disk writes
    (r'>\s*/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+|disk\d+)', "write to disk device"),
    (r'\bdd\s+.*of=/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+|disk\d+)', "dd to disk device"),

    # Random data overwrites
    (r'/dev/(?:zero|random|urandom)\s*>\s*/dev/(?:sd|hd|nvme|disk)', "overwrite disk with random"),

    # Disk device manipulation
    (r'\b(?:cat|tee)\s+.*>\s*/dev/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+)', "write to disk via cat/tee"),
]
```

**Examples Blocked**:
```bash
dd if=/dev/zero of=/dev/sda           # Wipe entire disk
cat /dev/urandom > /dev/sda           # Fill disk with random data
echo "data" > /dev/sda                # Write to disk device
dd if=image.iso of=/dev/disk0         # macOS disk overwrite
```

**Examples Allowed**:
```bash
dd if=/dev/zero of=./file.img         # Create file image
cat file.txt > output.txt             # Normal file operations
```

### 8.3 Fork Bombs

**Category Description**: Commands that spawn infinite processes, exhausting system resources.

**Patterns Detected**:

```python
FORK_BOMB_PATTERNS = [
    # Classic fork bombs
    (r':\(\)\{.*:\|:.*\}.*;:', "bash fork bomb"),
    (r'\(\)\s*\{\s*\(\)\s*\|\s*\(\)\s*&\s*\}', "function fork bomb"),

    # Perl/Python fork bombs
    (r'perl.*fork.*while', "perl fork bomb"),
    (r'python.*os\.fork.*while', "python fork bomb"),

    # Recursive process spawning
    (r'\$0\s*&\s*\$0', "recursive script execution"),
]
```

**Examples Blocked**:
```bash
:(){ :|:& };:                         # Classic bash fork bomb
perl -e "fork while fork"             # Perl fork bomb
python -c "import os; os.fork() while True"  # Python fork bomb
$0 & $0                               # Recursive script spawn
```

### 8.4 Dangerous Permission Changes

**Category Description**: Permission modifications that compromise system security.

**Patterns Detected**:

```python
PERMISSION_PATTERNS = [
    # World-writable sensitive directories
    (r'\bchmod\s+.*777\s+/(?:etc|bin|sbin|boot|usr)', "chmod 777 on system directory"),

    # Recursive permission changes on root
    (r'\bchmod\s+.*-R.*\s+/', "recursive chmod on root"),
    (r'\bchown\s+.*-R.*\s+/', "recursive chown on root"),

    # SUID/SGID on dangerous locations
    (r'\bchmod\s+.*[24][0-9]{3}\s+/', "SUID/SGID on system files"),
]
```

**Examples Blocked**:
```bash
chmod -R 777 /                        # Make everything world-writable
chmod 777 /etc/                       # Compromise system config security
chmod 4755 /bin/bash                  # SUID on shell (privilege escalation)
chown -R nobody /                     # Change ownership of root
```

**Examples Allowed**:
```bash
chmod 755 ./script.sh                 # Make script executable
chmod 644 ./config.txt                # Normal file permissions
chown user:group ./project/           # Change project ownership
```

### 8.5 System File Overwriting

**Category Description**: Commands that overwrite critical system files.

**Patterns Detected**:

```python
SYSTEM_FILE_PATTERNS = [
    # Critical system files
    (r'>\s*/(?:etc/(?:passwd|shadow|group|sudoers|fstab|hosts))', "overwrite system config"),
    (r'>\s*/boot/', "overwrite boot files"),

    # System binaries
    (r'>\s*/(?:bin|sbin|usr/bin|usr/sbin)/', "overwrite system binaries"),

    # Kernel/system files
    (r'>\s*/proc/', "write to proc filesystem"),
    (r'>\s*/sys/', "write to sys filesystem"),
]
```

**Examples Blocked**:
```bash
echo "hacker::0:0:::/bin/bash" > /etc/passwd    # Compromise user auth
cat malware > /bin/ls                            # Replace system command
echo "options" > /etc/fstab                      # Corrupt filesystem table
echo "data" > /boot/vmlinuz                      # Corrupt kernel
```

**Examples Allowed**:
```bash
echo "data" > ./etc/config.txt        # Write to project's etc directory
cat source.sh > ./bin/tool            # Write to project's bin directory
```

### 8.6 Format Operations

**Category Description**: Disk formatting and partition operations.

**Patterns Detected**:

```python
FORMAT_PATTERNS = [
    # Filesystem creation (formatting)
    (r'\bmkfs\.(?:ext[234]|xfs|btrfs|ntfs|fat32)', "format filesystem"),
    (r'\bmke2fs\b', "ext filesystem format"),

    # Partition manipulation
    (r'\b(?:fdisk|parted|gparted|diskutil)\b', "partition tool"),

    # Disk erasure
    (r'\bshred\s+.*--remove', "secure file deletion"),
    (r'\bwipe\s+', "secure wipe command"),
]
```

**Examples Blocked**:
```bash
mkfs.ext4 /dev/sda1                   # Format partition
fdisk /dev/sda                        # Partition manipulation
diskutil eraseDisk                    # macOS disk erase
shred -vfz -n 10 /dev/sda            # Secure wipe disk
parted /dev/sdb rm 1                  # Delete partition
```

**Examples Allowed**:
```bash
mkfs.ext4 ./disk.img                  # Format disk image file
```

### 8.7 Critical Process Termination

**Category Description**: Killing essential system processes.

**Patterns Detected**:

```python
PROCESS_KILL_PATTERNS = [
    # Kill all processes
    (r'\bkillall\s+-9', "killall with SIGKILL"),
    (r'\bkill\s+.*-9\s+1\b', "kill init/systemd"),

    # Kill critical services
    (r'\bkill(?:all)?\s+.*\b(?:systemd|init|launchd|sshd|networkd)\b', "kill critical service"),

    # pkill dangerous patterns
    (r'\bpkill\s+-9', "pkill with SIGKILL"),
]
```

**Examples Blocked**:
```bash
kill -9 1                             # Kill init/systemd (PID 1)
killall -9 systemd                    # Kill all systemd processes
pkill -9 sshd                         # Kill SSH daemon
kill -9 -1                            # Kill all user processes
```

**Examples Allowed**:
```bash
kill 12345                            # Kill specific process
killall myapp                         # Kill instances of user app
pkill -TERM python                    # Gracefully terminate Python
```

### 8.8 Additional Dangerous Commands

**Category Description**: Other commands that pose security or stability risks.

**Patterns Detected**:

```python
ADDITIONAL_DANGEROUS_PATTERNS = [
    # Kernel module manipulation
    (r'\b(?:rmmod|modprobe|insmod)\b', "kernel module manipulation"),

    # System shutdown/reboot
    (r'\b(?:shutdown|reboot|halt|poweroff|init\s+[06])\b', "system shutdown"),

    # Memory/system information exposure
    (r'/dev/mem', "direct memory access"),
    (r'/dev/kmem', "kernel memory access"),

    # Cryptocurrency miners (CPU exhaustion)
    (r'\b(?:xmrig|minerd|cpuminer|ethminer)\b', "cryptocurrency miner"),

    # Network flooding/attacks
    (r'\bhping3\b.*--flood', "network flood attack"),
    (r'\bnmap\b.*-sS.*-p-', "aggressive port scan"),

    # System configuration corruption
    (r'\bsysctl\s+.*kernel\.panic', "kernel panic trigger"),
]
```

**Examples Blocked**:
```bash
rmmod critical_driver                 # Remove kernel module
shutdown -h now                       # Shutdown system
dd if=/dev/mem                        # Read system memory
xmrig --donate-level=0                # Cryptocurrency miner
hping3 --flood target.com             # DoS attack
sysctl kernel.panic=1                 # Trigger kernel panic
```

## 9. Allow-list Patterns

### Safe Command Variations

Commands that appear dangerous but are actually safe:

```python
ALLOWED_PATTERNS = [
    # Safe rm with confirmation
    r'\brm\s+.*-i',  # Interactive mode (prompts for confirmation)

    # Help/version queries (read-only)
    r'\b(?:rm|dd|chmod|kill)\s+(?:--help|-h|--version|-V)\b',

    # Man pages (documentation)
    r'\bman\s+(?:rm|dd|chmod|kill)',

    # Dry-run/preview modes
    r'\b\w+\s+.*(?:--dry-run|--simulate|-n)\b',

    # Project-local operations only
    r'^\s*rm\s+.*\./[^/]',  # rm starting with ./
]
```

## 10. Validation Logic

### 10.1 Command Analysis Flow

```python
def validate_bash_command(command: str) -> Optional[str]:
    """
    Validate bash command for dangerous patterns.

    Returns:
        None if safe, error message string if dangerous
    """
    if not command:
        return None

    try:
        # Step 1: Check allow-list (early return for safe patterns)
        if is_allowed_command(command):
            return None

        # Step 2: Check each dangerous pattern category
        for category, patterns in DANGEROUS_PATTERNS.items():
            for pattern, description in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return format_deny_message(command, category, description)

        # Step 3: No dangerous patterns found
        return None

    except re.error:
        # Regex error: fail-safe, allow
        return None
    except Exception:
        # Any other error: fail-safe, allow
        return None
```

### 10.2 Pattern Matching Strategy

**Case Sensitivity**: Case-insensitive matching (`re.IGNORECASE`)
- Reason: `RM -RF /` is equally dangerous as `rm -rf /`

**Word Boundaries**: Use `\b` for command boundaries
- Prevents false positives: `farm` shouldn't match `rm` pattern

**Greedy Matching**: Minimal use to avoid ReDoS attacks
- All patterns tested for performance

**Priority Order**:
1. Check allow-list first (most permissive)
2. Check destructive operations (highest severity)
3. Check system modifications (medium severity)
4. Check resource exhaustion (medium severity)

## 11. Error Messages

### Message Structure

```python
def format_deny_message(command: str, category: str, description: str) -> str:
    """Format comprehensive denial message."""

    message = f"""⚠️ BLOCKED: Dangerous command detected

Command: {command}
Category: {category}
Pattern: {description}

Why this is dangerous:
{get_danger_explanation(category)}

Safe alternatives:
{get_safe_alternatives(category)}

If you absolutely must run this command:
  1. Exit Claude Code
  2. Run the command manually in a terminal
  3. Understand the risks fully before proceeding

This protection exists to prevent accidental system damage."""

    return message
```

### Category-Specific Messages

Each category includes:
1. **Danger Explanation**: 3-5 bullet points on specific risks
2. **Safe Alternatives**: 2-4 concrete alternative commands
3. **Context**: Why the command is blocked
4. **Manual Override**: Instructions if truly necessary

## 12. Error Handling Strategy

### Fail-Safe Principle

**All errors result in "allow" decision** to prevent workflow disruption:

```python
try:
    # Validation logic
    pass
except Exception as e:
    print(f"Destructive command blocker error: {e}", file=sys.stderr)
    output_decision("allow", f"Hook error (fail-safe): {e}")
```

### Error Scenarios

1. **Input Parsing Failure**:
   - Decision: Allow
   - Reason: "Failed to parse input (fail-safe)"

2. **Regex Compilation Error**:
   - Decision: Allow (exception caught)
   - Behavior: Skip that pattern, continue checking

3. **Pattern Matching Error**:
   - Decision: Allow
   - Continue with remaining patterns

## 13. Configuration

### 13.1 Hook Registration

**File**: `.claude/settings.json`

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

### 13.2 Hook Script Location

**Path**: `.claude/hooks/pre_tools/destructive_command_blocker.py`

**Execution**: `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/pre_tools/destructive_command_blocker.py`

### 13.3 Environment Variables

- **CLAUDE_PROJECT_DIR**: Absolute path to project root
  - Used for logging and safe path detection
  - Accessed via: `os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())`

## 14. Dependencies

### UV Script Metadata

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
```

### Python Version Requirement

- **Minimum**: Python 3.12
- **Rationale**: Modern type hints and pattern matching

### Standard Library Modules

```python
import re          # Regex pattern matching
import sys         # stdin/stdout/stderr, exit codes
from pathlib import Path  # Path operations
from typing import Optional  # Type hints
```

### Shared Utilities

```python
from utils import parse_hook_input, output_decision
```

## 15. Testing Strategy

### 15.1 Test Structure

**Location**: `tests/claude-hook/pre_tools/test_destructive_command_blocker.py`

**Framework**: pytest with distributed testing

**Execution**: `uv run pytest -n auto tests/claude-hook/pre_tools/test_destructive_command_blocker.py`

### 15.2 Test Categories

#### Pattern Detection Tests

```python
def test_destructive_file_operations():
    """Test detection of rm -rf patterns."""
    assert is_dangerous("rm -rf /")
    assert is_dangerous("rm -rf /*")
    assert is_dangerous("rm -rf /usr")
    assert not is_dangerous("rm file.txt")
    assert not is_dangerous("rm -i dangerous.txt")

def test_disk_overwrite_operations():
    """Test detection of disk write patterns."""
    assert is_dangerous("dd if=/dev/zero of=/dev/sda")
    assert is_dangerous("cat data > /dev/sda")
    assert not is_dangerous("dd if=/dev/zero of=file.img")

def test_fork_bombs():
    """Test detection of fork bomb patterns."""
    assert is_dangerous(":(){ :|:& };:")
    assert is_dangerous("perl -e 'fork while fork'")

def test_permission_changes():
    """Test detection of dangerous chmod/chown."""
    assert is_dangerous("chmod 777 /etc")
    assert is_dangerous("chmod -R 777 /")
    assert not is_dangerous("chmod 755 ./script.sh")

def test_system_file_overwriting():
    """Test detection of system file writes."""
    assert is_dangerous("echo hack > /etc/passwd")
    assert is_dangerous("cat malware > /bin/ls")
    assert not is_dangerous("echo data > ./etc/config")

def test_format_operations():
    """Test detection of format commands."""
    assert is_dangerous("mkfs.ext4 /dev/sda1")
    assert is_dangerous("fdisk /dev/sda")

def test_process_termination():
    """Test detection of critical process kills."""
    assert is_dangerous("kill -9 1")
    assert is_dangerous("killall -9 systemd")
    assert not is_dangerous("kill 12345")

def test_additional_dangerous_commands():
    """Test detection of other dangerous patterns."""
    assert is_dangerous("shutdown -h now")
    assert is_dangerous("rmmod critical_module")
```

#### Allow-list Tests

```python
def test_safe_rm_with_interactive():
    """Test rm -i is allowed."""
    assert not is_dangerous("rm -i file.txt")
    assert not is_dangerous("rm -ri ./directory/")

def test_help_commands_allowed():
    """Test help commands are allowed."""
    assert not is_dangerous("rm --help")
    assert not is_dangerous("dd --version")
```

#### Integration Tests

```python
def test_bash_tool_blocks_dangerous_command():
    """Test hook blocks dangerous bash commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"}
    }
    # Verify "deny" decision with appropriate message

def test_bash_tool_allows_safe_command():
    """Test hook allows safe bash commands."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"}
    }
    # Verify "allow" decision
```

#### Error Handling Tests

```python
def test_fail_safe_on_invalid_input():
    """Test hook allows on malformed input."""
    # Test with invalid JSON

def test_fail_safe_on_regex_error():
    """Test hook allows on regex compilation error."""
    # Test with pathological input
```

### 15.3 Test Coverage Goals

- **Line Coverage**: ≥ 95%
- **Branch Coverage**: ≥ 90%
- **Pattern Coverage**: All pattern categories tested
- **Edge Cases**: Complex commands, unicode, escaping

## 16. Security Considerations

### 16.1 Pattern Evasion

**Risk**: Attackers might try to evade pattern detection

**Mitigations**:
- Case-insensitive matching
- Whitespace normalization
- Detection of command substitution: `$(rm -rf /)`
- Detection of escaped characters
- Detection of environment variables: `$HOME` expansion

**Limitations**:
- Cannot detect all obfuscation techniques
- This is a **safety net**, not security sandbox
- Goal is to prevent **accidents**, not determined attacks

### 16.2 ReDoS Protection

**Risk**: Complex regex patterns could cause denial of service

**Mitigations**:
- Simple, non-backtracking patterns
- No nested quantifiers
- Timeout via hook configuration (60 seconds)
- Testing all patterns for performance

### 16.3 Input Validation

**Risk**: Malformed input could cause crashes

**Mitigations**:
- Use shared `parse_hook_input()` utility
- Validate types before processing
- Fail-safe on all errors

### 16.4 False Negatives vs False Positives

**Strategy**: Prioritize preventing false negatives (missing dangerous commands)

**Rationale**:
- False negative = potential system damage (high cost)
- False positive = workflow interruption (low cost)
- User can always disable hook temporarily if needed

## 17. Performance Considerations

### 17.1 Execution Time

**Target**: < 50ms per invocation

**Optimizations**:
- Early return on allow-list match
- Compiled regex patterns (compiled once at import)
- Simple string operations
- Minimal I/O (only stdin/stdout)

### 17.2 Memory Usage

**Target**: < 10 MB per invocation

**Considerations**:
- Fixed pattern lists
- No dynamic pattern generation
- Minimal string manipulation

## 18. Integration Considerations

### 18.1 Coexistence with Other Hooks

**Compatible Hooks**:
- universal_hook_logger.py - Logs all operations
- uv_workflow_enforcer.py - Enforces UV usage
- tmp_creation_blocker.py - Blocks temp file creation

**Behavior**:
- All PreToolUse hooks run in parallel
- Any "deny" decision blocks the operation
- This hook uses `suppressOutput: true`

### 18.2 User Experience

**Design Principles**:
1. **Clear Communication**: Explain exactly what was blocked
2. **Educational**: Help users understand the risk
3. **Actionable**: Provide safe alternatives
4. **Respectful**: Not punitive or condescending
5. **Escapable**: Explain how to override if truly necessary

## 19. Success Criteria

### 19.1 Functional Requirements

- ✅ Blocks all major categories of destructive commands
- ✅ Provides clear, educational error messages
- ✅ Allows safe command variations
- ✅ Uses shared utilities from pre_tools/utils
- ✅ Fail-safe behavior on errors

### 19.2 Non-Functional Requirements

- ✅ Execution time < 50ms
- ✅ Test coverage ≥ 95%
- ✅ Zero external dependencies
- ✅ Minimal false positives
- ✅ No workflow disruption on errors

### 19.3 Security Requirements

- ✅ Detects common evasion techniques
- ✅ Protected against ReDoS
- ✅ Robust input validation
- ✅ Clear documentation of limitations

## 20. Implementation Plan

### Phase 1: Core Implementation

1. ⏳ Create UV script with metadata
2. ⏳ Define all dangerous pattern categories
3. ⏳ Implement pattern matching logic
4. ⏳ Create comprehensive error messages
5. ⏳ Integrate with shared utilities
6. ⏳ Add allow-list patterns

### Phase 2: Configuration

1. ⏳ Add to .claude/settings.json
2. ⏳ Configure Bash tool matcher
3. ⏳ Set appropriate timeout
4. ⏳ Test hook registration

### Phase 3: Testing

1. ⏳ Write unit tests for each pattern category
2. ⏳ Write integration tests
3. ⏳ Write allow-list tests
4. ⏳ Write error handling tests
5. ⏳ Achieve ≥95% code coverage

### Phase 4: Documentation

1. ⏳ Complete inline documentation
2. ⏳ Write user guide
3. ⏳ Add to pre_tools/README.md
4. ⏳ Create troubleshooting guide

### Phase 5: Validation

1. ⏳ Manual testing with real Claude Code sessions
2. ⏳ Test pattern detection accuracy
3. ⏳ Validate error messages are helpful
4. ⏳ Performance testing

## 21. Future Enhancements

### 21.1 Pattern Customization

Allow users to customize dangerous patterns:

```json
{
  "destructiveCommandBlocker": {
    "customPatterns": [
      {"pattern": "mycorp-dangerous-cmd", "category": "Corporate Policy"}
    ],
    "disabledCategories": ["System Shutdown"]
  }
}
```

### 21.2 Severity Levels

Classify commands by severity:
- **Critical**: Blocks immediately (rm -rf /)
- **High**: Blocks with explanation (chmod 777 /etc)
- **Medium**: Asks for confirmation (killall)
- **Low**: Warns but allows (large file operations)

### 21.3 Learning Mode

Track blocked commands to identify patterns:
- Log all blocked attempts
- Analyze common false positives
- Suggest pattern refinements

### 21.4 Context-Aware Validation

Consider command context:
- Running in Docker container? (more permissive)
- In /tmp directory? (more permissive for rm)
- Root privileges available? (more restrictive)

## 22. Documentation Requirements

### 22.1 Inline Documentation

- Comprehensive module docstring
- Function docstrings with examples
- Pattern explanations with test cases
- Type hints on all functions

### 22.2 User Documentation

Create comprehensive guide covering:
1. What commands are blocked and why
2. How to safely accomplish common tasks
3. How to temporarily disable if needed
4. Understanding error messages
5. Reporting false positives

### 22.3 Developer Documentation

Document for future maintainers:
1. Pattern matching strategy
2. How to add new pattern categories
3. Testing procedures
4. Performance considerations
5. Security limitations

## 23. Known Limitations

### 23.1 Evasion Techniques

**Cannot detect**:
- Base64 encoded commands: `echo cm0gLXJmIC8= | base64 -d | bash`
- Command obfuscation: `r''m -rf /`
- Variable expansion: `CMD="rm -rf" && $CMD /`
- Script files: Writing dangerous command to file, then executing

**Rationale**: This is a **safety net** for accidents, not a security sandbox.

### 23.2 Context Limitations

**Cannot understand**:
- Whether operation is actually safe in current context
- User's true intentions
- Whether system is already compromised

**Example**: `rm -rf /mnt/external/*` might be safe if mounting an external disk

### 23.3 Performance Trade-offs

**Balancing**:
- More patterns = better protection but slower execution
- Complex patterns = better detection but ReDoS risk
- Current implementation prioritizes common dangerous patterns

## 24. Specification Change Log

| Version | Date       | Changes                                      | Author                   |
|---------|------------|----------------------------------------------|--------------------------|
| 1.0.0   | 2025-10-30 | Initial specification                        | Claude Code Hook Expert  |

---

**Specification Status**: ✅ Ready for Implementation

**Next Steps**:
1. Review specification with stakeholders
2. Proceed to build phase using `/experts:cc_hook_expert:cc_hook_expert_build`
3. Implement comprehensive test suite
4. Deploy and validate in real-world usage

**Related Documents**:
- `.claude/hooks/pre_tools/utils/data_types.py` - Shared type definitions
- `.claude/hooks/pre_tools/utils/utils.py` - Shared utility functions
- `ai_docs/claude-code-hooks.md` - Claude Code hooks reference
- `ai_docs/uv-scripts-guide.md` - UV script execution guide
