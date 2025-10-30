# Sensitive File Access Validator Hook Specification

## 1. Overview

### 1.1 Purpose

The Sensitive File Access Validator hook prevents Claude Code from reading and writing sensitive files and system locations during development. This hook serves as a critical security control to protect:

- **Credentials and Secrets**: Environment variables, API keys, tokens
- **Private Keys**: SSH keys, TLS certificates, GPG keys
- **Configuration Files**: User authentication configs, cloud provider credentials
- **System Locations**: Critical system directories and configuration

### 1.2 Problem Statement

During AI-assisted development, Claude Code may attempt to access sensitive files that could:

1. **Expose Secrets**: Reading `.env` files or credentials exposes sensitive data in session transcripts
2. **Create Credential Files**: Writing credential files directly bypasses secure credential management practices
3. **Modify System Files**: Accidental or intentional writes to system directories can compromise system integrity
4. **Leak Private Keys**: Accessing SSH keys or certificates creates security vulnerabilities
5. **Violate Security Policies**: Direct access to credential files violates organizational security practices

This hook prevents these scenarios by intercepting file operations before execution and providing educational feedback with secure alternatives.

### 1.3 Objectives

1. **Block Sensitive File Access**: Prevent reading and writing of credentials, keys, and secrets
2. **Protect System Directories**: Block writes to system locations (e.g., `/etc`, `/usr`, `/bin`)
3. **Enforce Template Usage**: Require use of `.sample` or `.example` files for sensitive file templates
4. **Provide Educational Feedback**: Explain why operations are blocked and suggest secure alternatives
5. **Support Bash Command Detection**: Parse bash commands to detect indirect file access attempts
6. **Maintain Performance**: Execute validation in < 100ms for typical operations
7. **Fail-Safe Operation**: Allow operations on errors to avoid disrupting development workflow

## 2. Hook Event Selection

### 2.1 Event: PreToolUse

**Rationale**: PreToolUse is the optimal event for this hook because:

1. **Preventive Control**: Intercepts operations before they execute, preventing exposure
2. **Multiple Tool Support**: Can monitor Read, Write, Edit, and Bash tools simultaneously
3. **Permission Control**: Supports deny/allow/ask permission decisions
4. **Error Injection**: Can provide detailed error messages that Claude processes
5. **Context Preservation**: Blocks operations without disrupting session state

**Alternative Events Considered**:
- **PostToolUse**: Too late - files already accessed, data already exposed
- **UserPromptSubmit**: Too early - cannot determine specific file operations

### 2.2 Tool Matchers

**Matcher Pattern**: `Read|Write|Edit|Bash`

**Tool-Specific Behaviors**:

| Tool | Detection Method | Validation Focus |
|------|------------------|------------------|
| **Read** | `tool_input.file_path` | Prevent reading sensitive files |
| **Write** | `tool_input.file_path` | Prevent creating credentials, writing to system dirs |
| **Edit** | `tool_input.file_path` | Prevent modifying sensitive files |
| **Bash** | `tool_input.command` parsing | Detect file operations in commands (cat, echo >, cp, mv) |

**Why These Tools**:
- **Read**: Direct file reading (most common exposure vector)
- **Write**: Creating new sensitive files
- **Edit**: Modifying existing sensitive files
- **Bash**: Indirect file operations (redirects, cat, cp, mv, etc.)

**Not Included**:
- **Glob**: Pattern matching only, no file access
- **Grep**: Content search, but already requires file access permissions
- **NotebookEdit**: Jupyter notebooks unlikely to contain raw credentials

## 3. Sensitive File Detection

### 3.1 Sensitive File Patterns

The hook detects the following categories of sensitive files:

#### Category 1: Environment Variables
```python
('.env', 'environment variables'),
('.env.local', 'local environment variables'),
('.env.production', 'production environment'),
('.env.development', 'development environment'),
('.env.test', 'test environment'),
('.env.staging', 'staging environment'),
```

**Detection**: Case-insensitive filename matching, path-agnostic
**Special Handling**: For `.env` files, suggest using `.env.sample` or `.env.example`

#### Category 2: SSH Private Keys
```python
('id_rsa', 'SSH private key'),
('id_dsa', 'SSH private key'),
('id_ecdsa', 'SSH private key'),
('id_ed25519', 'SSH private key'),
('id_ed25519_sk', 'SSH security key'),
```

**Detection**: Filename contains key identifier
**Location**: Typically in `~/.ssh/` but detected anywhere

#### Category 3: Certificates and Private Keys
```python
('.pem', 'certificate/key file'),
('.key', 'private key file'),
('.crt', 'certificate file'),
('.cer', 'certificate file'),
('.pfx', 'certificate archive'),
('.p12', 'certificate archive'),
('cert.pem', 'certificate file'),
('privkey.pem', 'private key file'),
('fullchain.pem', 'certificate chain'),
```

**Detection**: File extension or filename patterns
**Common Locations**: Let's Encrypt, TLS certs, code signing certs

#### Category 4: Cloud Provider Credentials
```python
('.aws/credentials', 'AWS credentials'),
('.aws/config', 'AWS configuration'),
('.azure/credentials', 'Azure credentials'),
('.config/gcloud/', 'Google Cloud credentials'),
('.docker/config.json', 'Docker registry credentials'),
('.kube/config', 'Kubernetes credentials'),
```

**Detection**: Directory path contains service name
**Risk**: Cloud provider credentials grant broad permissions

#### Category 5: Package Manager Credentials
```python
('.npmrc', 'npm credentials'),
('.pypirc', 'PyPI credentials'),
('.gem/credentials', 'RubyGems credentials'),
('.cargo/credentials', 'Cargo credentials'),
('.nuget/', 'NuGet credentials'),
```

**Detection**: Configuration file names
**Risk**: Package registry access, potential supply chain attacks

#### Category 6: VCS and Tool Credentials
```python
('.gitconfig', 'Git configuration'),
('.git-credentials', 'Git credentials'),
('.netrc', 'network credentials'),
('.hgrc', 'Mercurial configuration'),
```

**Detection**: Configuration file names
**Risk**: VCS credentials, private repository access

#### Category 7: Database Credentials
```python
('.pgpass', 'PostgreSQL password file'),
('.my.cnf', 'MySQL credentials'),
('database.yml', 'Rails database config'),
('credentials.json', 'generic credentials'),
('secrets.json', 'generic secrets'),
('secrets.yaml', 'generic secrets'),
```

**Detection**: Common database credential file patterns
**Risk**: Database access credentials

#### Category 8: API Keys and Tokens
```python
('secrets', 'secrets file'),
('credentials', 'credentials file'),
('token', 'token file'),
('api_key', 'API key file'),
('service-account', 'service account credentials'),
('client_secret', 'OAuth client secret'),
```

**Detection**: Filename contains credential-related keywords
**Risk**: API access, service authentication

### 3.2 Allowed Template Files

The hook ALLOWS access to template/example files:

```python
ALLOWED_PATTERNS = [
    '.sample',
    '.example',
    '.template',
    '.dist',
    '.default',
    'example.',
    'sample.',
]
```

**Example Allowed Files**:
- `.env.sample`
- `.env.example`
- `credentials.example`
- `example.env`
- `sample.config.json`

**Rationale**: Template files document required structure without exposing actual credentials.

### 3.3 System Directory Protection (Write Only)

Block writes to critical system directories:

```python
SYSTEM_DIRECTORIES = [
    '/etc',      # System configuration
    '/usr',      # User programs
    '/bin',      # System binaries
    '/sbin',     # System admin binaries
    '/boot',     # Boot loader
    '/sys',      # Kernel interface
    '/proc',     # Process info
    '/dev',      # Device files
    '/lib',      # System libraries
    '/lib64',    # 64-bit libraries
    '/root',     # Root home (Unix)
]
```

**Windows System Directories**:
```python
WINDOWS_SYSTEM_DIRECTORIES = [
    'C:\\Windows',
    'C:\\Program Files',
    'C:\\Program Files (x86)',
]
```

**Detection**: Path prefix matching with normalization

### 3.4 Protected Configuration Directories (Write Only)

Block writes to user configuration directories:

```python
PROTECTED_CONFIG_DIRS = [
    '/.ssh/',
    '/.gnupg/',
    '/.aws/',
    '/.azure/',
    '/.docker/',
    '/.kube/',
    '/.config/gcloud/',
    '/.config/gh/',  # GitHub CLI
]
```

**Rationale**: Prevent accidental creation of credentials in standard locations.

## 4. Bash Command Parsing

### 4.1 Command Detection Strategy

Parse bash commands to detect file operations on sensitive paths.

#### Read Operations
```python
READ_COMMANDS = [
    'cat',
    'less',
    'more',
    'head',
    'tail',
    'grep',
    'awk',
    'sed',
    'tac',
    'strings',
]
```

**Detection Pattern**:
```regex
\b(cat|less|more|...)\s+.*<sensitive_pattern>
```

**Example Blocked Commands**:
```bash
cat .env
less ~/.ssh/id_rsa
grep password credentials.json
head -n 20 .aws/credentials
```

#### Write Operations
```python
# Redirect operators
REDIRECT_PATTERNS = [
    r'>\s*',      # stdout redirect
    r'>>\s*',     # stdout append
    r'2>\s*',     # stderr redirect
    r'&>\s*',     # both redirect
    r'&>>\s*',    # both append
]
```

**Detection Pattern**:
```regex
(>|>>|2>|&>|&>>)\s*<sensitive_pattern>
```

**Example Blocked Commands**:
```bash
echo "SECRET=value" > .env
cat data >> ~/.ssh/id_rsa
echo "password" &> credentials.json
```

#### Copy/Move Operations
```python
COPY_MOVE_COMMANDS = [
    'cp',
    'mv',
    'rsync',
    'scp',
]
```

**Detection Pattern**:
```regex
\b(cp|mv|rsync|scp)\s+.*<sensitive_pattern>
```

**Example Blocked Commands**:
```bash
cp production.env .env
mv backup.key ~/.ssh/id_rsa
rsync keys/ ~/.ssh/
```

### 4.2 Command Parsing Algorithm

```python
def parse_bash_command(command: str) -> list[FileOperation]:
    """
    Parse bash command to extract file operations.

    Returns:
        List of (operation_type, file_path) tuples
    """
    operations = []

    # Split on command separators
    segments = split_command_chain(command)

    for segment in segments:
        # Check for read operations
        for read_cmd in READ_COMMANDS:
            if re.search(rf'\b{read_cmd}\b', segment):
                paths = extract_file_args(segment, read_cmd)
                operations.extend([('read', p) for p in paths])

        # Check for write operations (redirects)
        for redirect_pattern in REDIRECT_PATTERNS:
            matches = re.finditer(redirect_pattern + r'(\S+)', segment)
            operations.extend([('write', m.group(1)) for m in matches])

        # Check for copy/move operations
        for copy_cmd in COPY_MOVE_COMMANDS:
            if re.search(rf'\b{copy_cmd}\b', segment):
                paths = extract_file_args(segment, copy_cmd)
                operations.extend([('copy', p) for p in paths])

    return operations
```

### 4.3 Command Chain Handling

Handle complex bash command structures:

```python
COMMAND_SEPARATORS = [
    '&&',  # And operator
    '||',  # Or operator
    ';',   # Sequential
    '|',   # Pipe
]
```

**Example Complex Command**:
```bash
cd ~/.ssh && cat id_rsa | base64
# Detected: read operation on ~/.ssh/id_rsa
```

## 5. Input/Output Schemas

### 5.1 Input Schema (stdin)

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project/directory",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read|Write|Edit|Bash",
  "tool_input": {
    "file_path": "path/to/file",
    "content": "...",
    "command": "bash command"
  }
}
```

### 5.2 Output Schema (stdout) - Allow

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "File operation is safe"
  }
}
```

### 5.3 Output Schema (stdout) - Deny

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked reading environment variables file.\n\nPath: /project/.env\nFile Type: Environment variables containing secrets and configuration\n\nWhy this is blocked:\n  - Environment files contain sensitive credentials and API keys\n  - Reading .env exposes secrets in session transcripts and logs\n  - Security policy requires secrets to remain outside version control\n  - Exposing credentials creates security vulnerabilities\n\nSecure alternatives:\n  • Read template structure: Read('.env.sample')\n  • Check if file exists: Bash('test -f .env && echo exists')\n  • Document required variables in README\n  • Use environment variable documentation tools\n\nTo understand .env structure:\n  1. Create/read .env.sample with placeholder values\n  2. Document each variable's purpose and format\n  3. Never commit actual .env to version control\n\nThis protection prevents accidental credential exposure."
  },
  "suppressOutput": true
}
```

**Key Fields**:
- `permissionDecision`: Always "deny" for violations
- `permissionDecisionReason`: Detailed, educational error message
- `suppressOutput`: Always `true` to keep transcript clean

## 6. Error Message Format

### 6.1 Message Structure

All error messages follow this format:

```
🚫 Blocked <operation> <file_type> file.

Path: <file_path>
File Type: <description>

Why this is blocked:
  - <reason 1>
  - <reason 2>
  - <reason 3>

Secure alternatives:
  • <alternative 1>
  • <alternative 2>
  • <alternative 3>

<additional guidance>

This protection prevents <specific security risk>.
```

### 6.2 Example Error Messages

#### .env File Read Attempt
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

#### SSH Key Write Attempt
```
🚫 Blocked writing SSH private key file.

Path: ~/.ssh/id_rsa
File Type: SSH private key for authentication

Why this is blocked:
  - SSH private keys must be generated securely using ssh-keygen
  - Writing keys directly bypasses proper key generation practices
  - Compromised key generation creates security vulnerabilities
  - Keys should never be created from templates or copied

Secure alternatives:
  • Generate new key: Bash('ssh-keygen -t ed25519 -C "email"')
  • Document key setup: Write('SSH_SETUP.md', '...')
  • Create key generation script: Write('scripts/generate_ssh_key.sh', '...')

To set up SSH keys properly:
  1. Use ssh-keygen with strong key type (ed25519, RSA 4096+)
  2. Protect with strong passphrase
  3. Set correct permissions (600 for private, 644 for public)
  4. Add public key to authorized services

This protection prevents insecure key generation.
```

#### System Directory Write Attempt
```
⛔ Blocked writing to system directory.

Path: /etc/hosts
Directory: /etc (system configuration)

Why this is blocked:
  - System directories contain critical OS configuration
  - Modifying system files can break system functionality
  - Requires elevated permissions (root/sudo)
  - Unintended changes can make system unstable or unbootable

Secure alternatives:
  • Document required changes: Write('SYSTEM_CONFIG.md', '...')
  • Create configuration script: Write('scripts/setup_hosts.sh', '...')
  • Use user-level configuration when possible
  • Manually apply changes with sudo after review

To modify system files safely:
  1. Exit Claude Code
  2. Review required changes thoroughly
  3. Make backup: sudo cp /etc/hosts /etc/hosts.backup
  4. Apply changes manually with sudo
  5. Test system functionality

This protection prevents accidental system damage.
```

#### AWS Credentials Read Attempt
```
🚫 Blocked reading AWS credentials file.

Path: ~/.aws/credentials
File Type: AWS access keys and secrets

Why this is blocked:
  - AWS credentials provide broad cloud infrastructure access
  - Reading credentials exposes them in session logs
  - Credential exposure can lead to unauthorized AWS usage
  - Security best practices require keeping credentials secure

Secure alternatives:
  • Check AWS configuration: Bash('aws configure list')
  • Read AWS documentation: Read('AWS_SETUP.md')
  • Create example config: Write('.aws/credentials.example', '...')
  • Use AWS CLI to verify setup: Bash('aws sts get-caller-identity')

To work with AWS configuration:
  1. Use aws configure command for setup
  2. Document required permissions in README
  3. Use IAM roles when possible (no credentials needed)
  4. Create example files with placeholder values

This protection prevents credential exposure.
```

#### Bash Command with .env Write
```
🚫 Bash command attempts to write to environment variables file.

Command: echo "SECRET=abc123" > .env
File Type: Environment variables

Why this is blocked:
  - Direct credential writing bypasses secure credential management
  - Creates credentials in plaintext without proper protection
  - Environment files should be created manually with proper values

Secure alternatives:
  • Create template: Write('.env.sample', 'SECRET=your_secret_here')
  • Document setup: Write('ENV_SETUP.md', '...')
  • Instruct manual creation: Echo instructions to user

To set up environment variables:
  1. Create .env.sample with placeholder values
  2. Document where to obtain each secret value
  3. Users copy .env.sample to .env manually
  4. Users fill in actual secret values
  5. Ensure .env is in .gitignore

This protection prevents insecure credential creation.
```

### 6.3 Message Design Principles

1. **Clear Action Blocked**: State what was blocked upfront
2. **Context**: Show the file path and type
3. **Educational**: Explain why it's dangerous
4. **Actionable**: Provide specific alternatives
5. **Empowering**: Show how to accomplish the goal securely
6. **Concise**: Keep under 20 lines when possible

## 7. Validation Logic

### 7.1 Validation Flow

```python
def main() -> None:
    """Main validation workflow."""
    # 1. Parse input
    result = parse_hook_input()
    if result is None:
        output_decision("allow", "Failed to parse input")
        return

    tool_name, tool_input = result

    # 2. Check if tool requires validation
    if tool_name not in {"Read", "Write", "Edit", "Bash"}:
        output_decision("allow", "Not a file operation tool")
        return

    # 3. Perform validation
    violation = validate_file_operation(tool_name, tool_input)

    # 4. Output decision
    if violation:
        output_decision("deny", violation, suppress_output=True)
    else:
        output_decision("allow", "File operation is safe")
```

### 7.2 File Path Validation

```python
def validate_file_path(file_path: str, operation: str) -> str | None:
    """
    Validate a file path against sensitive file patterns.

    Args:
        file_path: Path to validate
        operation: 'read' or 'write'

    Returns:
        Error message if violation found, None otherwise
    """
    # 1. Normalize path
    try:
        path = Path(file_path).resolve()
        path_str = str(path).lower()
    except Exception:
        # Allow on normalization errors (fail-safe)
        return None

    # 2. Check if template file (allowed)
    if is_template_file(path_str):
        return None

    # 3. Check sensitive file patterns
    violation = check_sensitive_patterns(path_str, operation)
    if violation:
        return format_error_message(violation, file_path, operation)

    # 4. For writes, check system/config directories
    if operation == "write":
        violation = check_protected_directories(path)
        if violation:
            return format_error_message(violation, file_path, operation)

    return None
```

### 7.3 Bash Command Validation

```python
def validate_bash_command(command: str) -> str | None:
    """
    Validate bash command for sensitive file operations.

    Args:
        command: Bash command string

    Returns:
        Error message if violation found, None otherwise
    """
    # 1. Parse command to extract file operations
    operations = parse_bash_command(command)

    # 2. Validate each operation
    for operation_type, file_path in operations:
        violation = validate_file_path(file_path, operation_type)
        if violation:
            # Format error with command context
            return format_bash_error(violation, command, file_path)

    return None
```

## 8. Security Considerations

### 8.1 Path Normalization

**Challenge**: Prevent path traversal and canonicalization attacks

**Solution**:
```python
def normalize_path(file_path: str) -> Path:
    """Normalize path to prevent traversal attacks."""
    # Resolve symlinks and make absolute
    path = Path(file_path).resolve()
    return path
```

**Protected Against**:
- Path traversal: `../../.env`
- Symlinks: `/tmp/link -> ~/.ssh/id_rsa`
- Relative paths: `./subdir/../.env`
- Windows path variants: `C:\Users\..\Windows\System32`

### 8.2 Case-Insensitive Matching

**Challenge**: Detect sensitive files regardless of case

**Solution**:
```python
def is_sensitive_file(path: str) -> bool:
    """Case-insensitive sensitive file detection."""
    path_lower = path.lower()
    return any(pattern in path_lower for pattern, _ in SENSITIVE_PATTERNS)
```

**Protected Against**:
- `.ENV`
- `ID_RSA`
- `Credentials.json`
- `SECRET.key`

### 8.3 Fail-Safe Behavior

**Principle**: Never block operations due to hook errors

**Implementation**:
```python
def main() -> None:
    try:
        # Validation logic
        ...
    except Exception as e:
        # Log error but allow operation
        print(f"Hook error (allowing operation): {e}", file=sys.stderr)
        output_decision("allow", f"Hook error: {e}")
```

**Rationale**:
- Hook bugs should not disrupt development
- False positives are acceptable; false negatives in error cases are acceptable
- Users can always disable hook if needed

### 8.4 ReDoS Protection

**Challenge**: Prevent Regular Expression Denial of Service

**Solution**:
- Use simple, bounded regex patterns
- Avoid nested quantifiers: `(a+)+`
- Use string operations where possible
- Limit regex complexity

**Example Safe Patterns**:
```python
# Good: Simple, bounded
r'\bcat\b.*\.env'

# Bad: Nested quantifiers
r'(.*)+\.env'
```

### 8.5 Input Sanitization

**Challenge**: Handle malformed or malicious input

**Solution**:
```python
def parse_hook_input() -> tuple[str, ToolInput] | None:
    """Parse input with validation."""
    try:
        data = json.loads(sys.stdin.read())

        # Validate structure
        if not isinstance(data, dict):
            return None

        # Validate required fields
        if "tool_name" not in data or "tool_input" not in data:
            return None

        return (str(data["tool_name"]), data["tool_input"])
    except Exception:
        return None
```

### 8.6 Information Disclosure

**Concern**: Error messages might leak path information

**Mitigation**:
- Include full paths in error messages (useful for debugging)
- Users already have filesystem access
- Hook runs in user context, not privileged
- Error messages help users understand why operations blocked

## 9. Dependencies

### 9.1 Python Version

**Required**: Python 3.12+

**Rationale**:
- Type hints (PEP 604): `str | None` syntax
- Pattern matching (PEP 634): Not used but available
- Standard library improvements

### 9.2 External Dependencies

**None** - Uses Python standard library only:
- `sys`: stdin/stdout/stderr, exit codes
- `json`: Input/output parsing
- `re`: Pattern matching
- `pathlib`: Path operations
- `os`: Environment variables

### 9.3 Shared Utilities

**Location**: `.claude/hooks/pre_tools/utils/`

**Used Modules**:
```python
from utils import parse_hook_input, output_decision, get_file_path
from utils.data_types import ToolInput, PermissionDecision
```

**Functions**:
- `parse_hook_input()`: Parse and validate stdin JSON
- `output_decision()`: Format and output JSON decision
- `get_file_path()`: Extract file path from tool input

## 10. Error Handling

### 10.1 Error Categories

| Category | Handling | Example |
|----------|----------|---------|
| **Validation Errors** | Block with detailed message | Sensitive file detected |
| **Input Parsing Errors** | Allow operation (fail-safe) | Malformed JSON |
| **Path Resolution Errors** | Allow operation (fail-safe) | Invalid path format |
| **Hook Internal Errors** | Allow operation (fail-safe) | Unexpected exception |

### 10.2 Error Handling Strategy

```python
def main() -> None:
    """Main with comprehensive error handling."""
    try:
        # Normal validation flow
        result = parse_hook_input()
        if result is None:
            # Parse error - fail-safe
            output_decision("allow", "Failed to parse input")
            return

        tool_name, tool_input = result

        # Validation logic
        violation = validate_file_operation(tool_name, tool_input)

        if violation:
            output_decision("deny", violation, suppress_output=True)
        else:
            output_decision("allow", "File operation is safe")

    except Exception as e:
        # Unexpected error - fail-safe
        print(f"Hook error: {e}", file=sys.stderr)
        output_decision("allow", f"Hook error (allowing): {str(e)}")
```

### 10.3 Logging

**stderr Output**: Used for debugging
```python
print(f"Debug: Validating {tool_name} operation", file=sys.stderr)
```

**stdout Output**: JSON decision only
```python
print(json.dumps(decision_output))  # stdout
```

## 11. Testing Strategy

### 11.1 Test Framework

**Framework**: pytest with pytest-xdist

**Test Location**: `tests/claude-hook/pre_tools/test_sensitive_file_access_validator.py`

**Execution**:
```bash
uv run pytest -n auto tests/claude-hook/pre_tools/test_sensitive_file_access_validator.py
```

### 11.2 Test Categories

#### 11.2.1 Unit Tests

**Test Individual Functions**:
```python
def test_is_sensitive_file():
    """Test sensitive file detection."""
    assert is_sensitive_file("/path/.env") == True
    assert is_sensitive_file("/path/.env.sample") == False
    assert is_sensitive_file("/path/data.json") == False

def test_normalize_path():
    """Test path normalization."""
    assert normalize_path("../../.env").name == ".env"
    assert normalize_path("/tmp/../etc/passwd").parts[-2:] == ("etc", "passwd")
```

#### 11.2.2 Integration Tests

**Test Full Hook Flow**:
```python
def test_read_env_file_blocked():
    """Test .env read is blocked."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": ".env"}
    }
    result = run_hook(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert ".env" in result["hookSpecificOutput"]["permissionDecisionReason"]

def test_read_env_sample_allowed():
    """Test .env.sample read is allowed."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": ".env.sample"}
    }
    result = run_hook(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
```

#### 11.2.3 Bash Command Tests

**Test Command Parsing**:
```python
def test_bash_cat_env_blocked():
    """Test bash cat .env is blocked."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "cat .env"}
    }
    result = run_hook(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_bash_redirect_env_blocked():
    """Test bash redirect to .env is blocked."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo SECRET=value > .env"}
    }
    result = run_hook(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
```

#### 11.2.4 Edge Case Tests

```python
def test_empty_file_path():
    """Test empty file path."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": ""}
    }
    result = run_hook(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

def test_malformed_json():
    """Test malformed input."""
    result = run_hook_raw("{invalid json")
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "parse" in result["hookSpecificOutput"]["permissionDecisionReason"].lower()
```

### 11.3 Test Data

**Test Files**: Create temporary test files
```python
@pytest.fixture
def temp_sensitive_files(tmp_path):
    """Create temporary sensitive files for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=value")

    ssh_key = tmp_path / "id_rsa"
    ssh_key.write_text("-----BEGIN PRIVATE KEY-----")

    return tmp_path
```

### 11.4 Performance Tests

```python
def test_hook_performance():
    """Test hook executes quickly."""
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": ".env"}
    }

    start = time.time()
    result = run_hook(input_data)
    duration = time.time() - start

    assert duration < 0.1  # < 100ms
```

### 11.5 Coverage Goals

- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Critical Path Coverage**: 100%

## 12. Configuration

### 12.1 Hook Registration

**File**: `.claude/settings.json`

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

**Configuration Fields**:
- `matcher`: Tools to intercept (Read, Write, Edit, Bash)
- `command`: Path to hook script (uses `$CLAUDE_PROJECT_DIR`)
- `timeout`: Maximum execution time (60 seconds)

### 12.2 Disabling the Hook

**Option 1**: Comment in `.claude/settings.json`
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

**Option 2**: Local override in `.claude/settings.local.json`
```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

**Option 3**: Rename hook script
```bash
mv sensitive_file_access_validator.py sensitive_file_access_validator.py.disabled
```

### 12.3 Customization

**Environment Variables**: (Future Enhancement)
```bash
# Disable specific categories
export HOOK_SKIP_SSH_KEYS=true
export HOOK_SKIP_ENV_FILES=true

# Add custom patterns
export HOOK_SENSITIVE_PATTERNS=".secret,.token"
```

**Configuration File**: (Future Enhancement)
`.claude/hooks/pre_tools/sensitive_file_access_validator.config.json`
```json
{
  "enabled": true,
  "skip_categories": ["ssh_keys"],
  "custom_patterns": [
    {
      "pattern": ".secret",
      "description": "secret files",
      "applies_to": ["read", "write"]
    }
  ]
}
```

## 13. Performance Requirements

### 13.1 Execution Time

**Target**: < 100ms for typical operations
**Maximum**: < 500ms for complex bash commands

**Benchmarks**:
- Simple file path check: < 10ms
- Bash command parsing: < 50ms
- Complex command chain: < 100ms

### 13.2 Memory Usage

**Target**: < 10 MB peak memory
**Maximum**: < 50 MB for complex operations

### 13.3 Optimization Strategies

1. **Lazy Pattern Compilation**: Compile regex patterns once
2. **Early Exit**: Return on first violation found
3. **Minimal Allocations**: Reuse data structures
4. **Simple Algorithms**: Avoid complex parsing when possible

```python
# Pre-compile patterns at module level
SENSITIVE_PATTERNS_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), desc)
    for pattern, desc in SENSITIVE_PATTERNS
]

def is_sensitive_file(path: str) -> tuple[bool, str]:
    """Check if file is sensitive (with early exit)."""
    path_lower = path.lower()

    # Early exit on template files
    if any(t in path_lower for t in TEMPLATE_PATTERNS):
        return (False, "")

    # Check patterns with early exit
    for pattern, description in SENSITIVE_PATTERNS_COMPILED:
        if pattern.search(path):
            return (True, description)

    return (False, "")
```

## 14. Known Limitations

### 14.1 Evasion Techniques

The hook **cannot detect**:

1. **Base64 Encoding**:
   ```bash
   echo Y2F0IC5lbnY= | base64 -d | bash
   # Decodes to: cat .env
   ```

2. **Variable Indirection**:
   ```bash
   FILE=".env"
   cat $FILE
   ```

3. **Command Substitution**:
   ```bash
   cat $(echo .env)
   ```

4. **Hexadecimal Encoding**:
   ```bash
   cat "\x2e\x65\x6e\x76"  # .env in hex
   ```

5. **Script File Execution**:
   ```bash
   # Write malicious script
   Write("script.sh", "cat .env")
   # Execute it
   Bash("bash script.sh")
   ```

### 14.2 Design Rationale

**This is workflow guidance, not a security sandbox.**

**Goals**:
- ✅ Prevent accidental credential exposure
- ✅ Educate developers on secure practices
- ✅ Catch common mistakes
- ❌ Not designed to prevent determined malicious actors
- ❌ Not a security boundary

**Philosophy**:
> "Make the right thing easy and the wrong thing hard, but don't make the wrong thing impossible."

### 14.3 False Positives vs False Negatives

**Trade-off**: Prioritize preventing false negatives

- **False Positive**: Block a safe operation → Minor workflow interruption
- **False Negative**: Miss a dangerous operation → Potential credential exposure

**Decision**: Accept some false positives to ensure comprehensive protection.

**Mitigation**: Users can temporarily disable hook for legitimate use cases.

## 15. Implementation Checklist

### 15.1 Core Implementation

- [ ] Create hook script file: `sensitive_file_access_validator.py`
- [ ] Add UV script metadata (Python 3.12+, no dependencies)
- [ ] Implement main() entry point
- [ ] Add comprehensive module docstring
- [ ] Import shared utilities from utils/

### 15.2 Validation Logic

- [ ] Implement `validate_file_operation()`
- [ ] Implement `validate_file_path()`
- [ ] Implement `validate_bash_command()`
- [ ] Add path normalization
- [ ] Add case-insensitive matching
- [ ] Add template file detection

### 15.3 Pattern Detection

- [ ] Define all 8 categories of sensitive files
- [ ] Implement system directory detection
- [ ] Implement protected config directory detection
- [ ] Add bash read command detection
- [ ] Add bash write/redirect detection
- [ ] Add bash copy/move detection

### 15.4 Error Messages

- [ ] Create error message templates
- [ ] Add category-specific messages
- [ ] Implement message formatting function
- [ ] Add alternative suggestions
- [ ] Add educational content

### 15.5 Error Handling

- [ ] Add try-catch in main()
- [ ] Implement fail-safe behavior
- [ ] Add stderr logging
- [ ] Handle malformed input gracefully

### 15.6 Testing

- [ ] Create test file
- [ ] Add unit tests for sensitive file detection
- [ ] Add unit tests for path normalization
- [ ] Add integration tests for each tool
- [ ] Add bash command parsing tests
- [ ] Add edge case tests
- [ ] Add performance tests
- [ ] Achieve >90% code coverage

### 15.7 Documentation

- [ ] Update `.claude/hooks/pre_tools/README.md`
- [ ] Create hook-specific documentation section
- [ ] Add usage examples
- [ ] Add troubleshooting guide
- [ ] Document known limitations

### 15.8 Configuration

- [ ] Add hook to `.claude/settings.json`
- [ ] Test hook registration
- [ ] Verify timeout configuration
- [ ] Test disabling mechanisms

### 15.9 Performance

- [ ] Benchmark execution time
- [ ] Optimize pattern matching
- [ ] Add early exit optimizations
- [ ] Verify < 100ms target

## 16. Future Enhancements

### 16.1 Configuration File Support

**Proposal**: Add `.claude/hooks/pre_tools/sensitive_file_access_validator.config.json`

**Features**:
- Enable/disable specific categories
- Add custom sensitive patterns
- Configure error message verbosity
- Set allow-list patterns

### 16.2 Machine Learning Pattern Detection

**Proposal**: Use ML to detect credential-like content patterns

**Features**:
- Detect base64-encoded secrets
- Identify API key patterns
- Recognize credential formats

**Challenges**:
- Requires external dependencies
- Performance impact
- False positive rate

### 16.3 Integration with Secrets Management

**Proposal**: Integrate with secret management tools

**Features**:
- Validate against HashiCorp Vault
- Check AWS Secrets Manager
- Verify Azure Key Vault

**Challenges**:
- Requires network access
- Authentication complexity
- Latency impact

### 16.4 User-Specific Allow Lists

**Proposal**: Per-user customization of allowed files

**Features**:
- `.claude/hooks/pre_tools/allowed_files.json`
- User-specific exceptions
- Project-specific patterns

### 16.5 Audit Logging

**Proposal**: Log all blocked operations for security auditing

**Features**:
- Write to `agents/security_audit/<session_id>/blocked_operations.jsonl`
- Include timestamp, file path, operation type
- Support compliance requirements

## 17. Related Documentation

### 17.1 Internal Documentation

- [Claude Code Hooks Reference](../../../ai_docs/claude-code-hooks.md)
- [UV Scripts Guide](../../../ai_docs/uv-scripts-guide.md)
- [Claude Code Built-in Tools](../../../ai_docs/claude-built-in-tools.md)
- [PreToolUse Hooks README](../../../.claude/hooks/pre_tools/README.md)
- [Shared Utilities](../../../.claude/hooks/pre_tools/utils/)

### 17.2 External References

- [PEP 723 - Inline Script Metadata](https://peps.python.org/pep-0723/)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [CIS Security Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### 17.3 Similar Hooks

- [Destructive Command Blocker](destructive-command-blocker-spec.md) - Prevents destructive bash commands
- [UV Dependency Blocker](uv-dependency-blocker-spec.md) - Prevents direct dependency file edits
- [TMP Creation Blocker](tmp-creation-blocker-spec.md) - Prevents system temp directory usage

## 18. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-10-30 | Claude Code Hook Expert | Initial specification |

---

## Appendix A: Complete Sensitive File Patterns List

```python
SENSITIVE_FILE_PATTERNS = [
    # Environment Variables
    ('.env', 'environment variables'),
    ('.env.local', 'local environment variables'),
    ('.env.production', 'production environment'),
    ('.env.development', 'development environment'),
    ('.env.test', 'test environment'),
    ('.env.staging', 'staging environment'),

    # SSH Keys
    ('id_rsa', 'SSH private key'),
    ('id_dsa', 'SSH private key'),
    ('id_ecdsa', 'SSH private key'),
    ('id_ed25519', 'SSH private key'),
    ('id_ed25519_sk', 'SSH security key'),

    # Certificates and Keys
    ('.pem', 'certificate/key file'),
    ('.key', 'private key file'),
    ('.crt', 'certificate file'),
    ('.cer', 'certificate file'),
    ('.pfx', 'certificate archive'),
    ('.p12', 'certificate archive'),
    ('cert.pem', 'certificate file'),
    ('privkey.pem', 'private key file'),
    ('fullchain.pem', 'certificate chain'),

    # Cloud Provider Credentials
    ('.aws/credentials', 'AWS credentials'),
    ('.aws/config', 'AWS configuration'),
    ('.azure/credentials', 'Azure credentials'),
    ('.config/gcloud/', 'Google Cloud credentials'),
    ('.docker/config.json', 'Docker registry credentials'),
    ('.kube/config', 'Kubernetes credentials'),

    # Package Manager Credentials
    ('.npmrc', 'npm credentials'),
    ('.pypirc', 'PyPI credentials'),
    ('.gem/credentials', 'RubyGems credentials'),
    ('.cargo/credentials', 'Cargo credentials'),
    ('.nuget/', 'NuGet credentials'),

    # VCS and Tool Credentials
    ('.gitconfig', 'Git configuration'),
    ('.git-credentials', 'Git credentials'),
    ('.netrc', 'network credentials'),
    ('.hgrc', 'Mercurial configuration'),

    # Database Credentials
    ('.pgpass', 'PostgreSQL password file'),
    ('.my.cnf', 'MySQL credentials'),
    ('database.yml', 'Rails database config'),

    # Generic Credentials
    ('credentials.json', 'credentials file'),
    ('credentials.yaml', 'credentials file'),
    ('secrets.json', 'secrets file'),
    ('secrets.yaml', 'secrets file'),
    ('secrets.toml', 'secrets file'),
    ('token', 'token file'),
    ('api_key', 'API key file'),
    ('service-account', 'service account credentials'),
    ('client_secret', 'OAuth client secret'),
]
```

## Appendix B: Example Hook Output

### Successful Validation (Allow)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "File operation is safe"
  }
}
```

### Failed Validation (Deny)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "🚫 Blocked reading environment variables file.\n\nPath: /project/.env\nFile Type: Environment variables containing secrets and configuration\n\nWhy this is blocked:\n  - Environment files contain sensitive credentials and API keys\n  - Reading .env exposes secrets in session transcripts and logs\n  - Security policy requires secrets to remain outside version control\n  - Exposing credentials creates security vulnerabilities\n\nSecure alternatives:\n  • Read template structure: Read('.env.sample')\n  • Check if file exists: Bash('test -f .env && echo exists')\n  • Document required variables in README\n  • Use environment variable documentation tools\n\nTo understand .env structure:\n  1. Create/read .env.sample with placeholder values\n  2. Document each variable's purpose and format\n  3. Never commit actual .env to version control\n\nThis protection prevents accidental credential exposure."
  },
  "suppressOutput": true
}
```

---

**End of Specification**
