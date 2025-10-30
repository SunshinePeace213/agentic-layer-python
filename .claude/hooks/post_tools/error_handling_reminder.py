#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Error Handling Reminder Hook for PostToolUse
=============================================

Educational awareness hook that gently reminds Claude to consider error
handling and logging when risky code patterns are detected.

This hook provides non-blocking feedback to help Claude improve error
handling practices without interfering with workflow.

Hook Event:
    PostToolUse

Tool Matchers:
    - Write: New files being created
    - Edit: Modified files
    - NotebookEdit: Notebook cells edited

Behavior:
    1. Validates file is Python (.py, .pyi)
    2. Parses file to AST
    3. Detects risky patterns (try/except, async, database, API)
    4. Calculates risk score
    5. Provides gentle reminder if score >= threshold
    6. Non-blocking (never blocks Claude)

Output:
    - High risk: Educational reminder with recommendations
    - Low risk: Silent exit (no output)
    - Errors: Silent exit (graceful degradation)

Security:
    - Validates file paths (no traversal)
    - Checks file is within project directory
    - No external commands
    - Graceful error handling

Configuration:
    Environment variables:
    - ERROR_HANDLING_REMINDER_ENABLED (default: "true")
    - ERROR_HANDLING_REMINDER_MIN_SCORE (default: "2")
    - ERROR_HANDLING_REMINDER_INCLUDE_TIPS (default: "true")
    - ERROR_HANDLING_REMINDER_DEBUG (default: "false")

Example Feedback:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📋 ERROR HANDLING SELF-CHECK
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ⚠️  Risky Patterns Detected in example.py

       ❓ Found 2 try-except blocks - Consider adding logging...
       ❓ Found 1 async function without error handling...

       💡 Error Handling Best Practices:
          - Add logging statements in exception handlers
          - Wrap await calls in try/except...
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version:
    1.0.0

Author:
    Claude Code Hook Expert
"""

import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Import shared utilities from post_tools/utils
try:
    from utils import (
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )
except ImportError:
    # Fallback for testing or direct execution
    sys.path.insert(0, str(Path(__file__).parent / "utils"))
    from utils import (  # type: ignore[reportMissingImports]
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Configuration ====================


@dataclass
class Config:
    """Configuration from environment variables."""

    enabled: bool = True
    min_score: int = 2
    include_tips: bool = True
    debug: bool = False

    @staticmethod
    def load() -> "Config":
        """Load configuration from environment variables."""
        return Config(
            enabled=os.getenv("ERROR_HANDLING_REMINDER_ENABLED", "true").lower()
            == "true",
            min_score=int(os.getenv("ERROR_HANDLING_REMINDER_MIN_SCORE", "2")),
            include_tips=os.getenv(
                "ERROR_HANDLING_REMINDER_INCLUDE_TIPS", "true"
            ).lower()
            == "true",
            debug=os.getenv("ERROR_HANDLING_REMINDER_DEBUG", "false").lower() == "true",
        )


# ==================== Risk Assessment ====================


@dataclass
class RiskAssessment:
    """Risk assessment result from pattern detection."""

    except_blocks_without_logging: int = 0
    async_functions_without_error_handling: int = 0
    db_operations_without_error_handling: int = 0
    endpoints_without_error_handling: int = 0

    @property
    def total_score(self) -> int:
        """Calculate total risk score."""
        return (
            self.except_blocks_without_logging
            + self.async_functions_without_error_handling
            + self.db_operations_without_error_handling
            + self.endpoints_without_error_handling
        )

    def exceeds_threshold(self, threshold: int) -> bool:
        """Check if risk score exceeds threshold."""
        return self.total_score >= threshold


# ==================== AST Pattern Detector ====================


class RiskyPatternDetector(ast.NodeVisitor):
    """AST visitor that detects risky code patterns."""

    def __init__(self) -> None:
        """Initialize pattern detector."""
        self.assessment = RiskAssessment()
        self.db_imports: set[str] = set()
        self.web_framework_imports: set[str] = set()
        self._try_contexts: list[ast.Try] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Detect database and web framework imports."""
        db_modules = {
            "sqlite3",
            "psycopg2",
            "pymongo",
            "mysql.connector",
            "sqlalchemy",
            "django.db",
            "peewee",
        }

        web_modules = {"flask", "fastapi", "django", "starlette", "aiohttp"}

        if node.module and any(node.module.startswith(mod) for mod in db_modules):
            self.db_imports.add(node.module)

        if node.module and any(node.module.startswith(mod) for mod in web_modules):
            self.web_framework_imports.add(node.module)

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Detect try/except blocks and check for logging."""
        self._try_contexts.append(node)

        for handler in node.handlers:
            has_logging = self._has_logging_in_block(handler.body)
            if not has_logging:
                self.assessment.except_blocks_without_logging += 1

        self.generic_visit(node)
        self._try_contexts.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Detect async functions without error handling."""
        has_try = any(isinstance(child, ast.Try) for child in ast.walk(node))
        if not has_try:
            self.assessment.async_functions_without_error_handling += 1

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Detect API endpoint functions via decorators."""
        if self._is_api_endpoint(node):
            has_try = any(isinstance(child, ast.Try) for child in ast.walk(node))
            if not has_try:
                self.assessment.endpoints_without_error_handling += 1

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect database operation calls."""
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            db_methods = {
                "execute",
                "executemany",
                "query",
                "filter",
                "get",
                "insert",
                "update",
                "delete",
                "commit",
                "rollback",
                "save",
                "create",
                "bulk_create",
            }

            if method_name in db_methods and self.db_imports:
                # Check if inside try block
                if not self._is_inside_try_block():
                    self.assessment.db_operations_without_error_handling += 1

        self.generic_visit(node)

    def _has_logging_in_block(self, block: list[ast.stmt]) -> bool:
        """Check if code block contains logging statements."""
        for node in ast.walk(ast.Module(body=block, type_ignores=[])):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Check for logging.info(), logger.error(), etc.
                    if node.func.attr in {
                        "debug",
                        "info",
                        "warning",
                        "error",
                        "critical",
                        "log",
                        "exception",
                    }:
                        return True
                elif isinstance(node.func, ast.Name):
                    # Check for print() (acceptable but not ideal)
                    if node.func.id == "print":
                        return True
        return False

    def _is_inside_try_block(self) -> bool:
        """Check if current context is inside a try block."""
        return len(self._try_contexts) > 0

    def _is_api_endpoint(self, node: ast.FunctionDef) -> bool:
        """Check if function is an API endpoint via decorators."""
        route_decorators = {
            "route",
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "api_view",
            "action",
        }

        for decorator in node.decorator_list:
            # Handle @app.route(...) or @router.get(...)
            if isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Attribute
            ):
                if decorator.func.attr in route_decorators:
                    return True
            # Handle @route or @get without call
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr in route_decorators:
                    return True
            # Handle @api_view([...]) for Django
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Name
            ):
                if decorator.func.id in route_decorators:
                    return True

        return False


# ==================== Message Generation ====================


def build_exception_recommendations(
    count: int, recommendations: list[str], tips: list[str]
) -> None:
    """Add exception handling recommendations and tips."""
    recommendations.append(
        f"   ❓ Found {count} try-except block{'s' if count != 1 else ''} - "
        "Consider adding logging in except blocks for debugging"
    )
    tips.extend(
        [
            "      - Add logging statements in exception handlers for debugging",
            "      - Use structured logging with context (e.g., user_id, request_id)",
            "      - Handle specific exceptions rather than bare except",
            "      - Log errors before re-raising or returning error responses",
        ]
    )


def build_async_recommendations(
    count: int, recommendations: list[str], tips: list[str]
) -> None:
    """Add async function recommendations and tips."""
    recommendations.append(
        f"   ❓ Found {count} async function{'s' if count != 1 else ''} without error handling - "
        "Add try/except to handle async errors"
    )
    tips.extend(
        [
            "      - Wrap await calls in try/except when dealing with external services",
            "      - Use finally blocks to ensure proper cleanup",
            "      - Consider timeout handling for long-running async operations",
        ]
    )


def build_database_recommendations(
    count: int, recommendations: list[str], tips: list[str]
) -> None:
    """Add database operation recommendations and tips."""
    recommendations.append(
        f"   ❓ Found {count} database operation{'s' if count != 1 else ''} - "
        "Ensure transactions have proper error handling and logging"
    )
    tips.extend(
        [
            "      - Use transactions with proper commit/rollback",
            "      - Log query errors with relevant context (table, operation)",
            "      - Handle connection errors gracefully with retries",
            "      - Use context managers (with statements) for automatic cleanup",
        ]
    )


def build_endpoint_recommendations(
    count: int, recommendations: list[str], tips: list[str]
) -> None:
    """Add API endpoint recommendations and tips."""
    recommendations.append(
        f"   ❓ Found {count} API endpoint{'s' if count != 1 else ''} - "
        "Consider adding error handling to return appropriate HTTP status codes"
    )
    tips.extend(
        [
            "      - Return appropriate HTTP status codes (400, 404, 500, etc.)",
            "      - Log errors with request context (endpoint, method, params)",
            "      - Avoid exposing internal error details to users",
            "      - Use middleware/decorators for consistent error handling",
        ]
    )


def deduplicate_tips(tips: list[str]) -> list[str]:
    """Remove duplicate tips while preserving order."""
    seen: set[str] = set()
    unique_tips: list[str] = []
    for tip in tips:
        if tip not in seen:
            seen.add(tip)
            unique_tips.append(tip)
    return unique_tips


def generate_feedback_message(
    file_path: str, assessment: RiskAssessment, config: Config
) -> str:
    """
    Generate educational feedback message.

    Args:
        file_path: Path to the file that was analyzed
        assessment: Risk assessment results
        config: Configuration settings

    Returns:
        Formatted feedback message for Claude
    """
    file_name = Path(file_path).name
    recommendations: list[str] = []
    tips: list[str] = []

    # Build recommendations based on detected patterns
    if assessment.except_blocks_without_logging > 0:
        build_exception_recommendations(
            assessment.except_blocks_without_logging, recommendations, tips
        )

    if assessment.async_functions_without_error_handling > 0:
        build_async_recommendations(
            assessment.async_functions_without_error_handling, recommendations, tips
        )

    if assessment.db_operations_without_error_handling > 0:
        build_database_recommendations(
            assessment.db_operations_without_error_handling, recommendations, tips
        )

    if assessment.endpoints_without_error_handling > 0:
        build_endpoint_recommendations(
            assessment.endpoints_without_error_handling, recommendations, tips
        )

    # Deduplicate tips while preserving order
    unique_tips = deduplicate_tips(tips)

    # Format message
    return format_message_output(file_name, recommendations, unique_tips, config)


def format_message_output(
    file_name: str, recommendations: list[str], tips: list[str], config: Config
) -> str:
    """
    Format the final feedback message.

    Args:
        file_name: Name of the file being analyzed
        recommendations: List of recommendation strings
        tips: List of best practice tip strings
        config: Configuration settings

    Returns:
        Formatted feedback message
    """
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📋 ERROR HANDLING SELF-CHECK",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"⚠️  Risky Patterns Detected in {file_name}",
        "",
    ]

    lines.extend(recommendations)

    if config.include_tips and tips:
        lines.extend(["", "   💡 Error Handling Best Practices:"])
        lines.extend(tips)

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


# ==================== Core Functions ====================


def main() -> None:
    """Main entry point for error handling reminder hook."""
    # Load configuration
    config = Config.load()

    # Check if hook is enabled
    if not config.enabled:
        output_feedback("", suppress_output=True)
        return

    # Parse input
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # Validate tool and file
    if not should_process(tool_name, tool_input, tool_response):
        output_feedback("", suppress_output=True)
        return

    file_path = get_file_path(tool_input)

    # Analyze file for risky patterns
    assessment = analyze_file(file_path)

    # Check if risk score exceeds threshold
    if not assessment.exceeds_threshold(config.min_score):
        output_feedback("", suppress_output=True)
        return

    # Generate and output feedback
    feedback = generate_feedback_message(file_path, assessment, config)
    output_feedback(feedback, suppress_output=True)


def is_file_size_acceptable(file_path: str, max_lines: int = 10000) -> bool:
    """
    Check if file size is within acceptable limits.

    Args:
        file_path: Path to file
        max_lines: Maximum number of lines allowed

    Returns:
        True if file size is acceptable, False otherwise
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            line_count = sum(1 for _ in f)
            return line_count <= max_lines
    except (OSError, UnicodeDecodeError):
        return False


def should_process(
    tool_name: str,
    tool_input: ToolInput,
    tool_response: dict[str, object],
) -> bool:
    """
    Determine if file should be processed.

    Args:
        tool_name: Name of the tool that was executed
        tool_input: Tool input parameters
        tool_response: Tool execution response

    Returns:
        True if file should be analyzed, False otherwise
    """
    # Check tool name
    if tool_name not in ["Write", "Edit", "NotebookEdit"]:
        return False

    # Check tool success
    if not was_tool_successful(tool_response):
        return False

    # Get and validate file path
    file_path = get_file_path(tool_input)
    if not file_path:
        return False

    # Check if Python file
    if not is_python_file(file_path):
        return False

    # Check if within project
    if not is_within_project(file_path):
        return False

    # Check if file exists
    if not Path(file_path).exists():
        return False

    # Check file size (skip files > 10,000 lines)
    if not is_file_size_acceptable(file_path):
        return False

    return True


def analyze_file(file_path: str) -> RiskAssessment:
    """
    Analyze file for risky code patterns using AST.

    Args:
        file_path: Absolute path to Python file

    Returns:
        RiskAssessment with pattern detection results

    Process:
        1. Read file contents
        2. Parse to AST
        3. Visit AST nodes to detect patterns
        4. Return risk assessment

    Error Handling:
        - Returns empty assessment on syntax errors
        - Returns empty assessment on encoding errors
        - Gracefully handles invalid Python
    """
    try:
        # Read file contents
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse to AST
        tree = ast.parse(content, filename=file_path)

        # Detect patterns
        detector = RiskyPatternDetector()
        detector.visit(tree)

        return detector.assessment

    except SyntaxError:
        # Invalid Python syntax, skip analysis
        return RiskAssessment()
    except (OSError, UnicodeDecodeError):
        # File access or encoding error, skip analysis
        return RiskAssessment()
    except Exception:
        # Unexpected error, skip analysis gracefully
        return RiskAssessment()


# ==================== Entry Point ====================


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log unexpected errors to stderr but don't block
        print(f"Error handling reminder hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
