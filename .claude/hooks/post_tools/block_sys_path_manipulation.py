#!/usr/bin/env python3
"""
sys.path Manipulation PostToolUse Hook
=======================================
Detects and blocks manipulations of sys.path in Python code.

This hook integrates with Claude Code to prevent sys.path manipulations,
encouraging proper module execution instead:
    - uv run -m src.module_name.script
    - python -m package.module
    - Proper package structure with __init__.py
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TypedDict, cast


# Type definitions for JSON I/O
class ToolInput(TypedDict):
    """Tool input structure."""

    file_path: str
    content: str


class ToolResponse(TypedDict):
    """Tool response structure."""

    filePath: str
    success: bool


class InputData(TypedDict):
    """Complete input data structure."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    tool_name: str
    tool_input: ToolInput
    tool_response: ToolResponse


class HookSpecificOutput(TypedDict):
    """Hook-specific output structure."""

    hookEventName: str
    additionalContext: str


class OutputData(TypedDict, total=False):
    """Output JSON structure for PostToolUse."""

    decision: str  # "block" or omit
    reason: str
    hookSpecificOutput: HookSpecificOutput


class Severity(Enum):
    """Issue severity levels."""

    BLOCK = "BLOCKED"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    """Represents a sys.path manipulation issue."""

    severity: Severity
    category: str
    message: str
    line: int | None = None
    column: int | None = None
    details: str = ""
    suggestion: str = ""


@dataclass
class CheckResult:
    """Results from sys.path manipulation checks."""

    blocks: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    info: list[Issue] = field(default_factory=list)

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the appropriate list."""
        if issue.severity == Severity.BLOCK:
            self.blocks.append(issue)
        elif issue.severity == Severity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    def has_blocks(self) -> bool:
        """Check if there are any blocking issues."""
        return len(self.blocks) > 0


class SysPathManipulationChecker:
    """
    Detects manipulations of sys.path in Python code.

    Flags as BLOCKED:
    - sys.path.append()
    - sys.path.insert()
    - sys.path.extend()
    - sys.path += [...]
    - sys.path[x] = ...
    - Direct assignment to sys.path
    """

    def __init__(self, file_path: str) -> None:
        self.file_path: Path = Path(file_path)
        self.content: str = ""
        self.tree: ast.AST | None = None
        self.results: CheckResult = CheckResult()

        # Track imports related to sys.path
        self.sys_imports: dict[str, str] = {}  # alias -> what it refers to
        self.path_aliases: set[str] = set()  # Variables that refer to sys.path
        self.has_sys: bool = False
        self.has_sys_path: bool = False

    def check_manipulations(self) -> CheckResult:
        """Run sys.path manipulation checks."""
        # Validate file exists and is Python
        if not self._validate_file():
            return self.results

        # Parse the file
        if not self._parse_file():
            return self.results

        # Analyze imports to understand what refers to sys/sys.path
        self._analyze_imports()

        # Check for sys.path manipulations
        if self.has_sys or self.has_sys_path:
            self._check_path_manipulations()

        return self.results

    def _validate_file(self) -> bool:
        """Validate the file exists and is a Python file."""
        if not self.file_path.exists():
            # File doesn't exist yet (might be a new file), skip checks
            return False

        if self.file_path.suffix not in {".py", ".pyi"}:
            # Not a Python file, skip checks
            return False

        return True

    def _parse_file(self) -> bool:
        """Parse the Python file into an AST."""
        try:
            self.content = self.file_path.read_text(encoding="utf-8")
            self.tree = ast.parse(self.content)
            return True
        except SyntaxError:
            # Syntax error - can't check for sys.path manipulations
            # Don't block on syntax errors, let other tools handle that
            return False
        except Exception:
            # Can't read/parse file, skip checks
            return False

    def _analyze_imports(self) -> None:
        """Analyze imports to detect sys and sys.path usage."""
        if not self.tree:
            return

        class ImportAnalyzer(ast.NodeVisitor):
            def __init__(self, checker: SysPathManipulationChecker) -> None:
                self.checker: SysPathManipulationChecker = checker

            def visit_Import(self, node: ast.Import) -> None:
                """Handle 'import sys' style imports."""
                for alias in node.names:
                    if alias.name == "sys":
                        asname = alias.asname or "sys"
                        self.checker.sys_imports[asname] = "sys"
                        self.checker.has_sys = True
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                """Handle 'from sys import path' style imports."""
                if node.module == "sys":
                    for alias in node.names:
                        if alias.name == "path":
                            asname = alias.asname or "path"
                            self.checker.path_aliases.add(asname)
                            self.checker.has_sys_path = True
                        elif alias.name == "*":
                            # from sys import *
                            self.checker.path_aliases.add("path")
                            self.checker.has_sys_path = True
                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                """Detect assignments like: path_var = sys.path"""
                # Check if the value is sys.path
                if self._is_sys_path(node.value):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.checker.path_aliases.add(target.id)
                            self.checker.has_sys_path = True
                self.generic_visit(node)

            def _is_sys_path(self, node: ast.expr) -> bool:
                """Check if a node refers to sys.path."""
                if isinstance(node, ast.Attribute):
                    if node.attr == "path" and isinstance(node.value, ast.Name):
                        return node.value.id in self.checker.sys_imports
                return False

        analyzer = ImportAnalyzer(self)
        analyzer.visit(self.tree)

    def _check_path_manipulations(self) -> None:
        """Check for sys.path manipulations throughout the code."""
        if not self.tree:
            return

        class ManipulationDetector(ast.NodeVisitor):
            def __init__(self, checker: SysPathManipulationChecker) -> None:
                self.checker: SysPathManipulationChecker = checker
                self.in_function: bool = False
                self.function_name: str | None = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                """Track when we're inside a function."""
                old_in_function = self.in_function
                old_function_name = self.function_name
                self.in_function = True
                self.function_name = node.name
                self.generic_visit(node)
                self.in_function = old_in_function
                self.function_name = old_function_name

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                """Track when we're inside an async function."""
                old_in_function = self.in_function
                old_function_name = self.function_name
                self.in_function = True
                self.function_name = node.name
                self.generic_visit(node)
                self.in_function = old_in_function
                self.function_name = old_function_name

            def visit_Call(self, node: ast.Call) -> None:
                """Detect method calls on sys.path."""
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr

                    # Check if it's a method call on sys.path or a path alias
                    if self._is_path_manipulation(node.func.value, method_name):
                        self._report_method_manipulation(node, method_name)

                self.generic_visit(node)

            def visit_AugAssign(self, node: ast.AugAssign) -> None:
                """Detect += operations on sys.path."""
                if self._is_sys_path_reference(node.target):
                    location = "module level"
                    if self.in_function:
                        location = f"function '{self.function_name}'"

                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.BLOCK,
                            category="sys.path Manipulation",
                            message=f"sys.path augmented assignment (+=) at {location}",
                            line=node.lineno,
                            column=node.col_offset,
                            details="Augmented assignment to sys.path makes module loading dependent on execution context",
                            suggestion="Use proper module structure with 'uv run -m module.name' or 'python -m module.name'",
                        )
                    )

                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                """Detect direct assignment to sys.path."""
                for target in node.targets:
                    if self._is_sys_path_reference(target):
                        location = "module level"
                        if self.in_function:
                            location = f"function '{self.function_name}'"

                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.BLOCK,
                                category="sys.path Manipulation",
                                message=f"Direct assignment to sys.path at {location}",
                                line=node.lineno,
                                column=node.col_offset,
                                details="Replacing sys.path entirely is dangerous and breaks module loading",
                                suggestion="Structure your project properly and use PYTHONPATH or virtual environments",
                            )
                        )

                    # Also check for item assignment like sys.path[0] = ...
                    if isinstance(target, ast.Subscript):
                        if self._is_sys_path_reference(target.value):
                            location = "module level"
                            if self.in_function:
                                location = f"function '{self.function_name}'"

                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.BLOCK,
                                    category="sys.path Manipulation",
                                    message=f"sys.path item assignment at {location}",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    details="Modifying individual sys.path entries is fragile and context-dependent",
                                    suggestion="Use proper package structure and module imports",
                                )
                            )

                self.generic_visit(node)

            def visit_Delete(self, node: ast.Delete) -> None:
                """Detect deletion from sys.path."""
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if self._is_sys_path_reference(target.value):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.BLOCK,
                                    category="sys.path Manipulation",
                                    message="Deleting from sys.path",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    details="Removing paths from sys.path can break imports",
                                    suggestion="Fix import issues at the source rather than manipulating sys.path",
                                )
                            )

                self.generic_visit(node)

            def _is_path_manipulation(self, obj: ast.expr, method: str) -> bool:
                """Check if this is a manipulation method on sys.path."""
                manipulation_methods = {
                    "append",
                    "insert",
                    "extend",
                    "remove",
                    "pop",
                    "clear",
                    "reverse",
                    "sort",
                }

                if method not in manipulation_methods:
                    return False

                return self._is_sys_path_reference(obj)

            def _is_sys_path_reference(self, node: ast.expr) -> bool:
                """Check if a node refers to sys.path or an alias."""
                if isinstance(node, ast.Attribute):
                    if node.attr == "path" and isinstance(node.value, ast.Name):
                        return node.value.id in self.checker.sys_imports
                elif isinstance(node, ast.Name):
                    return node.id in self.checker.path_aliases
                return False

            def _report_method_manipulation(self, node: ast.Call, method: str) -> None:
                """Report a method-based manipulation of sys.path."""
                location = "module level"
                if self.in_function:
                    location = f"function '{self.function_name}'"

                severity = Severity.BLOCK

                # Customize message based on method
                if method == "append":
                    details = "sys.path.append() is a common antipattern that makes code execution directory-dependent"
                    suggestion = "Structure as a proper package and use 'uv run -m package.module' or add to PYTHONPATH"
                elif method == "insert":
                    details = "sys.path.insert() is even worse than append, as it changes import priority"
                    suggestion = "Use proper package structure with __init__.py files and relative imports"
                elif method == "extend":
                    details = "sys.path.extend() adds multiple paths, making debugging difficult"
                    suggestion = "Use virtual environments or PYTHONPATH for managing multiple package locations"
                elif method in ["remove", "pop", "clear"]:
                    details = f"sys.path.{method}() can break standard library imports"
                    suggestion = (
                        "Never remove paths from sys.path; fix the root cause instead"
                    )
                else:
                    details = f"sys.path.{method}() modifies the module search path"
                    suggestion = (
                        "Avoid sys.path manipulation; use proper module organization"
                    )

                self.checker.results.add_issue(
                    Issue(
                        severity=severity,
                        category="sys.path Manipulation",
                        message=f"sys.path.{method}() called at {location}",
                        line=node.lineno,
                        column=node.col_offset,
                        details=details,
                        suggestion=suggestion,
                    )
                )

        detector = ManipulationDetector(self)
        detector.visit(self.tree)


def main() -> None:
    """Main entry point for PostToolUse hook."""
    try:
        # Read JSON input from stdin
        input_text = sys.stdin.read()
        if not input_text:
            # No input, nothing to check
            sys.exit(0)

        # Parse input - json.loads returns Any, we suppress only this line
        try:
            input_data_raw: object = json.loads(input_text)  # type: ignore[no-any-expr]
        except json.JSONDecodeError:
            # Invalid JSON input, skip
            sys.exit(0)

        # Type validation and extraction with proper type narrowing
        if not isinstance(input_data_raw, dict):
            # Invalid input structure, skip
            sys.exit(0)

        # Cast to dict[str, object] after validation
        # We know keys are strings from JSON spec
        input_dict = cast(dict[str, object], input_data_raw)

        # Extract tool_name - only check Write operations
        tool_name_obj = input_dict.get("tool_name", "")
        if not isinstance(tool_name_obj, str):
            tool_name = ""
        else:
            tool_name = tool_name_obj

        if tool_name != "Write":
            # Not a write operation, skip checks
            sys.exit(0)

        # Extract tool_input
        tool_input_obj = input_dict.get("tool_input")
        if not isinstance(tool_input_obj, dict):
            # No tool_input or wrong type - nothing to check
            sys.exit(0)

        # Cast to dict[str, object] after validation
        tool_input_dict = cast(dict[str, object], tool_input_obj)

        # Extract file_path from tool_input
        file_path_obj = tool_input_dict.get("file_path")
        if not isinstance(file_path_obj, str):
            # No file path - nothing to check
            sys.exit(0)

        file_path = file_path_obj

        # Check if it's a Python file
        if not file_path.endswith((".py", ".pyi")):
            # Not a Python file, skip checks
            sys.exit(0)

        # Run sys.path manipulation checks
        checker = SysPathManipulationChecker(file_path)
        results = checker.check_manipulations()

        # Handle results
        if results.has_blocks():
            # Format blocking issues for output
            issue_list: list[str] = []
            for issue in results.blocks:
                # Build message parts
                line_info = f" (line {issue.line}" if issue.line else ""
                if line_info and issue.column is not None:
                    line_info = f"{line_info}, col {issue.column})"
                elif line_info:
                    line_info = f"{line_info})"

                details_info = f"\n  → {issue.details}" if issue.details else ""
                suggestion_info = (
                    f"\n  ✅ {issue.suggestion}" if issue.suggestion else ""
                )

                msg = f"• {issue.message}{line_info}{details_info}{suggestion_info}"
                issue_list.append(msg)

            # Create blocking response
            output: OutputData = {
                "decision": "block",
                "reason": "sys.path manipulation detected",
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"❌ sys.path manipulation detected:\n\n"
                        f"{chr(10).join(issue_list)}\n\n"
                        f"📝 To fix these issues:\n"
                        f"  1. Structure your code as proper Python packages\n"
                        f"  2. Use 'uv run -m package.module' to run scripts\n"
                        f"  3. Or use 'python -m package.module' with proper PYTHONPATH\n"
                        f"  4. Consider using a justfile for consistent execution"
                    ),
                },
            }
            print(json.dumps(output))
            sys.exit(0)

        # No blocking issues - output success message
        file_name = Path(file_path).name
        success_output: OutputData = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"✅ System Path Manipulation check passed for {file_name}",
            }
        }
        print(json.dumps(success_output))
        sys.exit(0)

    except Exception:
        # Unexpected error, skip checks to avoid blocking normal operation
        sys.exit(0)


if __name__ == "__main__":
    main()
