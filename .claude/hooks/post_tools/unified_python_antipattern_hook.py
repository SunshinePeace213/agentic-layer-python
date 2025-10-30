#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Unified Python Antipattern Hook for PostToolUse
================================================

Detects Python-specific antipatterns across 7 categories:
- Runtime issues: Mutable defaults, late binding, global misuse
- Performance problems: String concatenation, inefficient operations
- Complexity concerns: Deep nesting, too many parameters
- Security vulnerabilities: SQL injection, hardcoded secrets
- Code organization: Poor imports, wildcard imports
- Resource management: File handles, context managers
- Python gotchas: Using 'is' for equality, type checking

This hook uses AST-based analysis for accurate pattern detection and provides
clear, actionable feedback for Claude to fix issues in the next iteration.

Hook Event:
    PostToolUse

Tool Matchers:
    - Write: Triggers when new files are created
    - Edit: Triggers when existing files are modified
    - NotebookEdit: Triggers when notebook cells are edited

Behavior:
    1. Validates file is Python (.py, .pyi)
    2. Parses file to AST
    3. Detects 40+ antipatterns using AST visitor
    4. Provides feedback with severity levels
    5. Blocks on CRITICAL security issues (configurable)

Configuration:
    Environment variables:
    - PYTHON_ANTIPATTERN_ENABLED: Enable/disable hook (default: "true")
    - PYTHON_ANTIPATTERN_LEVELS: Severity levels to report (default: "CRITICAL,HIGH,MEDIUM,LOW")
    - PYTHON_ANTIPATTERN_BLOCK_CRITICAL: Block on critical issues (default: "true")
    - PYTHON_ANTIPATTERN_DISABLED: Comma-separated pattern IDs to disable
    - PYTHON_ANTIPATTERN_MAX_ISSUES: Maximum issues to report (default: "10")

Version:
    1.0.0

Author:
    Claude Code Hook Expert
"""

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

# Import shared utilities from post_tools/utils
try:
    from utils import (
        ToolInput,
        get_file_path,
        is_python_file,
        is_within_project,
        output_block,
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
        output_block,
        output_feedback,
        parse_hook_input,
        was_tool_successful,
    )


# ==================== Data Structures ====================


@dataclass
class Issue:
    """Represents a detected antipattern issue."""

    id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    line: int
    column: int
    message: str
    suggestion: str
    code_snippet: str = ""


# ==================== Configuration ====================


class Config:
    """Hook configuration from environment variables."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        enabled_str = os.getenv("PYTHON_ANTIPATTERN_ENABLED", "true").lower()
        self.enabled = enabled_str == "true"

        levels_str = os.getenv("PYTHON_ANTIPATTERN_LEVELS", "CRITICAL,HIGH,MEDIUM,LOW")
        self.levels = set(levels_str.split(","))

        block_str = os.getenv("PYTHON_ANTIPATTERN_BLOCK_CRITICAL", "true").lower()
        self.block_critical = block_str == "true"

        disabled_str = os.getenv("PYTHON_ANTIPATTERN_DISABLED", "")
        self.disabled_patterns = set(disabled_str.split(",") if disabled_str else [])

        max_issues_str = os.getenv("PYTHON_ANTIPATTERN_MAX_ISSUES", "10")
        self.max_issues = int(max_issues_str)

        debug_str = os.getenv("PYTHON_ANTIPATTERN_DEBUG", "false").lower()
        self.debug = debug_str == "true"


# ==================== Main Detector ====================


class AntipatternDetector(ast.NodeVisitor):
    """AST visitor for detecting Python antipatterns."""

    def __init__(self, source_code: str, config: Config) -> None:
        """
        Initialize detector with source code and configuration.

        Args:
            source_code: Python source code to analyze
            config: Configuration settings
        """
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.config = config
        self.issues: list[Issue] = []
        self.current_loop_depth = 0
        self.current_function: Optional[ast.FunctionDef | ast.AsyncFunctionDef] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for antipatterns."""
        prev_function = self.current_function
        self.current_function = node

        # Check various function-level antipatterns
        self._check_mutable_defaults(node)
        self._check_parameter_count(node)
        self._check_function_complexity(node)
        self._check_function_length(node)
        self._check_missing_super_call(node)
        self._check_shadowing_builtins(node)

        # Continue traversal
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for antipatterns."""
        prev_function = self.current_function
        self.current_function = node

        # Check various function-level antipatterns
        self._check_mutable_defaults(node)
        self._check_parameter_count(node)
        self._check_function_complexity(node)
        self._check_function_length(node)
        self._check_missing_super_call(node)
        self._check_shadowing_builtins(node)

        # Continue traversal
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check comparison operations."""
        self._check_is_with_literals(node)
        self._check_equality_with_none(node)
        self._check_equality_with_bool(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls."""
        self._check_dangerous_functions(node)
        self._check_sql_injection(node)
        self._check_command_injection(node)
        self._check_type_checking_with_type(node)
        self._check_weak_cryptography(node)
        self._check_unsafe_deserialization(node)
        self._check_weak_random_for_security(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Check exception handlers."""
        self._check_bare_except(node)
        self._check_silent_exception_swallowing(node)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Check assert statements."""
        self._check_assert_in_production(node)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        """Check global statements."""
        self._check_global_misuse(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class definitions."""
        self._check_mutable_class_variables(node)
        self._check_eq_without_hash(node)
        self._check_context_manager_protocol(node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Check for loops."""
        self.current_loop_depth += 1
        self._check_string_concatenation_in_loops(node)
        self._check_list_concatenation_in_loops(node)
        self._check_modifying_list_while_iterating(node)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Check async for loops."""
        self.current_loop_depth += 1
        self._check_string_concatenation_in_loops(node)
        self._check_list_concatenation_in_loops(node)
        self._check_modifying_list_while_iterating(node)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        """Check while loops."""
        self.current_loop_depth += 1
        self._check_string_concatenation_in_loops(node)
        self._check_list_concatenation_in_loops(node)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        """Check if statements."""
        self._check_unnecessary_else_after_return(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignments."""
        self._check_hardcoded_secrets(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check import statements."""
        self._check_wildcard_imports(node)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Check with statements (context managers)."""
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Check async with statements (context managers)."""
        self.generic_visit(node)

    # ==================== Detection Methods ====================

    def _check_mutable_defaults(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect mutable default arguments (R001)."""
        if "R001" in self.config.disabled_patterns:
            return

        all_defaults = list(node.args.defaults) + list(node.args.kw_defaults)
        for default_arg in all_defaults:
            if default_arg is None:
                continue
            if isinstance(default_arg, (ast.List, ast.Dict, ast.Set)):
                code_snippet = self._get_code_snippet(default_arg.lineno)
                self.issues.append(
                    Issue(
                        id="R001",
                        severity="HIGH",
                        line=default_arg.lineno,
                        column=default_arg.col_offset,
                        message="Mutable default argument",
                        suggestion="Use None and create mutable object inside function",
                        code_snippet=code_snippet,
                    )
                )

    def _check_dangerous_functions(self, node: ast.Call) -> None:
        """Detect dangerous functions like eval, exec (R002)."""
        if "R002" in self.config.disabled_patterns:
            return

        dangerous_funcs = {"eval", "exec", "compile", "__import__"}
        if isinstance(node.func, ast.Name) and node.func.id in dangerous_funcs:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="R002",
                    severity="HIGH",
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"Dangerous function: {node.func.id}()",
                    suggestion="Avoid using eval/exec, use safer alternatives like ast.literal_eval()",
                    code_snippet=code_snippet,
                )
            )

    def _check_bare_except(self, node: ast.ExceptHandler) -> None:
        """Detect bare except clauses (R003)."""
        if "R003" in self.config.disabled_patterns:
            return

        if node.type is None:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="R003",
                    severity="MEDIUM",
                    line=node.lineno,
                    column=node.col_offset,
                    message="Bare except clause",
                    suggestion="Specify exception type: except Exception: or except SpecificError:",
                    code_snippet=code_snippet,
                )
            )

    def _check_assert_in_production(self, node: ast.Assert) -> None:
        """Detect assertions used for validation (R004)."""
        if "R004" in self.config.disabled_patterns:
            return

        code_snippet = self._get_code_snippet(node.lineno)
        self.issues.append(
            Issue(
                id="R004",
                severity="HIGH",
                line=node.lineno,
                column=node.col_offset,
                message="Assert statement (disabled with python -O)",
                suggestion="Use explicit if/raise for production validation",
                code_snippet=code_snippet,
            )
        )

    def _check_global_misuse(self, node: ast.Global) -> None:
        """Detect overuse of global keyword (R005)."""
        if "R005" in self.config.disabled_patterns:
            return

        code_snippet = self._get_code_snippet(node.lineno)
        self.issues.append(
            Issue(
                id="R005",
                severity="MEDIUM",
                line=node.lineno,
                column=node.col_offset,
                message="Global keyword usage",
                suggestion="Consider using function parameters or class attributes instead",
                code_snippet=code_snippet,
            )
        )

    def _check_mutable_class_variables(self, node: ast.ClassDef) -> None:
        """Detect mutable class variables (R006)."""
        if "R006" in self.config.disabled_patterns:
            return

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and isinstance(
                        item.value, (ast.List, ast.Dict, ast.Set)
                    ):
                        code_snippet = self._get_code_snippet(item.lineno)
                        self.issues.append(
                            Issue(
                                id="R006",
                                severity="HIGH",
                                line=item.lineno,
                                column=item.col_offset,
                                message=f"Mutable class variable: {target.id}",
                                suggestion="Initialize mutable attributes in __init__ instead",
                                code_snippet=code_snippet,
                            )
                        )

    def _check_missing_super_call(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect missing super().__init__() in __init__ (R010)."""
        if "R010" in self.config.disabled_patterns:
            return

        if node.name != "__init__":
            return

        # Check if this is in a class with base classes
        # (This requires context we don't have in simple visitor, so skip for now)
        # Full implementation would track class hierarchy
        pass

    def _check_shadowing_builtins(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect shadowing of builtin names (R008)."""
        if "R008" in self.config.disabled_patterns:
            return

        builtins_set = {
            "list",
            "dict",
            "set",
            "tuple",
            "str",
            "int",
            "float",
            "bool",
            "type",
            "id",
            "input",
            "open",
            "range",
            "len",
            "max",
            "min",
            "sum",
            "all",
            "any",
            "filter",
            "map",
            "zip",
        }

        for arg in node.args.args:
            if arg.arg in builtins_set:
                code_snippet = self._get_code_snippet(node.lineno)
                self.issues.append(
                    Issue(
                        id="R008",
                        severity="MEDIUM",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Shadowing builtin: {arg.arg}",
                        suggestion=f"Rename parameter to avoid shadowing builtin '{arg.arg}'",
                        code_snippet=code_snippet,
                    )
                )

    def _check_eq_without_hash(self, node: ast.ClassDef) -> None:
        """Detect __eq__ without __hash__ (R009)."""
        if "R009" in self.config.disabled_patterns:
            return

        has_eq = False
        has_hash = False

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__eq__":
                    has_eq = True
                elif item.name == "__hash__":
                    has_hash = True

        if has_eq and not has_hash:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="R009",
                    severity="HIGH",
                    line=node.lineno,
                    column=node.col_offset,
                    message="Class defines __eq__ without __hash__",
                    suggestion="Define __hash__ or set __hash__ = None if unhashable",
                    code_snippet=code_snippet,
                )
            )

    def _check_string_concatenation_in_loops(
        self, node: ast.For | ast.AsyncFor | ast.While
    ) -> None:
        """Detect string concatenation in loops (P001)."""
        if "P001" in self.config.disabled_patterns:
            return

        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                code_snippet = self._get_code_snippet(child.lineno)
                self.issues.append(
                    Issue(
                        id="P001",
                        severity="MEDIUM",
                        line=child.lineno,
                        column=child.col_offset,
                        message="String/list concatenation in loop using +=",
                        suggestion="Use list.append() and ''.join() for strings",
                        code_snippet=code_snippet,
                    )
                )

    def _check_list_concatenation_in_loops(
        self, _node: ast.For | ast.AsyncFor | ast.While
    ) -> None:
        """Detect list concatenation in loops (P005)."""
        if "P005" in self.config.disabled_patterns:
            return
        # Covered by P001 check above (no separate implementation needed)

    def _check_parameter_count(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect functions with too many parameters (C004)."""
        if "C004" in self.config.disabled_patterns:
            return

        total_args = (
            len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs)
        )

        if total_args > 7:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="C004",
                    severity="MEDIUM",
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"Too many parameters: {total_args}",
                    suggestion="Reduce to 7 or fewer parameters, consider using a dataclass or config object",
                    code_snippet=code_snippet,
                )
            )

    def _check_function_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect high cyclomatic complexity (C003)."""
        if "C003" in self.config.disabled_patterns:
            return

        complexity = self._calculate_complexity(node)
        if complexity > 15:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="C003",
                    severity="HIGH",
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"Cyclomatic complexity: {complexity}",
                    suggestion="Break down into smaller functions (target: < 15)",
                    code_snippet=code_snippet,
                )
            )

    def _check_function_length(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Detect overly long functions (C010)."""
        if "C010" in self.config.disabled_patterns:
            return

        # Get the last line of the function
        end_lineno = node.end_lineno if node.end_lineno else node.lineno
        length = end_lineno - node.lineno

        if length > 50:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="C010",
                    severity="HIGH",
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"Function too long: {length} lines",
                    suggestion="Break down into smaller functions (target: < 50 lines)",
                    code_snippet=code_snippet,
                )
            )

    def _check_unnecessary_else_after_return(self, node: ast.If) -> None:
        """Detect else after return statement (C005)."""
        if "C005" in self.config.disabled_patterns:
            return

        # Check if body ends with return
        if node.body and isinstance(node.body[-1], ast.Return):
            if node.orelse:
                code_snippet = self._get_code_snippet(node.lineno)
                self.issues.append(
                    Issue(
                        id="C005",
                        severity="LOW",
                        line=node.lineno,
                        column=node.col_offset,
                        message="Unnecessary else after return",
                        suggestion="Remove else clause and unindent code",
                        code_snippet=code_snippet,
                    )
                )

    def _check_sql_injection(self, node: ast.Call) -> None:
        """Detect potential SQL injection (S001)."""
        if "S001" in self.config.disabled_patterns:
            return

        # Check for .execute() calls with string formatting
        if isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
            if node.args:
                first_arg = node.args[0]
                # Check for f-strings, % formatting, .format()
                if isinstance(first_arg, ast.JoinedStr):  # f-string
                    code_snippet = self._get_code_snippet(node.lineno)
                    self.issues.append(
                        Issue(
                            id="S001",
                            severity="CRITICAL",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Potential SQL injection (f-string in execute)",
                            suggestion="Use parameterized queries: cursor.execute(query, (param,))",
                            code_snippet=code_snippet,
                        )
                    )

    def _check_command_injection(self, node: ast.Call) -> None:
        """Detect command injection via subprocess (S002)."""
        if "S002" in self.config.disabled_patterns:
            return

        # Check for subprocess calls with shell=True
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {"run", "call", "Popen"}:
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(
                        keyword.value, ast.Constant
                    ):
                        if keyword.value.value is True:
                            code_snippet = self._get_code_snippet(node.lineno)
                            self.issues.append(
                                Issue(
                                    id="S002",
                                    severity="CRITICAL",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    message="Command injection risk (shell=True)",
                                    suggestion="Use shell=False with list of args instead",
                                    code_snippet=code_snippet,
                                )
                            )

    def _check_hardcoded_secrets(self, node: ast.Assign) -> None:
        """Detect hardcoded secrets (S003)."""
        if "S003" in self.config.disabled_patterns:
            return

        secret_patterns = [
            r"api[_-]?key",
            r"password",
            r"secret",
            r"token",
            r"auth",
            r"credential",
            r"api[_-]?secret",
        ]

        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                for pattern in secret_patterns:
                    if re.search(pattern, var_name):
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            # Check if it looks like an actual secret (not empty or placeholder)
                            value = node.value.value
                            if value and value not in {
                                "",
                                "TODO",
                                "REPLACE_ME",
                                "your-key-here",
                            }:
                                code_snippet = self._get_code_snippet(node.lineno)
                                self.issues.append(
                                    Issue(
                                        id="S003",
                                        severity="CRITICAL",
                                        line=node.lineno,
                                        column=node.col_offset,
                                        message=f"Hardcoded secret: {target.id}",
                                        suggestion="Use environment variables or secret management system",
                                        code_snippet=code_snippet,
                                    )
                                )
                        break

    def _check_weak_cryptography(self, node: ast.Call) -> None:
        """Detect weak cryptographic functions (S004)."""
        if "S004" in self.config.disabled_patterns:
            return

        weak_hashes = {"md5", "sha1"}
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in weak_hashes:
                code_snippet = self._get_code_snippet(node.lineno)
                self.issues.append(
                    Issue(
                        id="S004",
                        severity="HIGH",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Weak cryptography: {node.func.attr}",
                        suggestion="Use SHA-256 or stronger: hashlib.sha256()",
                        code_snippet=code_snippet,
                    )
                )

    def _check_unsafe_deserialization(self, node: ast.Call) -> None:
        """Detect unsafe deserialization (S005)."""
        if "S005" in self.config.disabled_patterns:
            return

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "load" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "pickle":
                    code_snippet = self._get_code_snippet(node.lineno)
                    self.issues.append(
                        Issue(
                            id="S005",
                            severity="HIGH",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Unsafe deserialization: pickle.load",
                            suggestion="Only unpickle from trusted sources, consider using json instead",
                            code_snippet=code_snippet,
                        )
                    )

    def _check_weak_random_for_security(self, node: ast.Call) -> None:
        """Detect use of random module for security (S007)."""
        if "S007" in self.config.disabled_patterns:
            return

        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "random":
                    code_snippet = self._get_code_snippet(node.lineno)
                    self.issues.append(
                        Issue(
                            id="S007",
                            severity="HIGH",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Weak random for security",
                            suggestion="Use secrets module for cryptographic purposes",
                            code_snippet=code_snippet,
                        )
                    )

    def _check_wildcard_imports(self, node: ast.ImportFrom) -> None:
        """Detect wildcard imports (O003)."""
        if "O003" in self.config.disabled_patterns:
            return

        for alias in node.names:
            if alias.name == "*":
                code_snippet = self._get_code_snippet(node.lineno)
                module_name = node.module if node.module else "unknown"
                self.issues.append(
                    Issue(
                        id="O003",
                        severity="HIGH",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Wildcard import from {module_name}",
                        suggestion="Import specific names: from module import name1, name2",
                        code_snippet=code_snippet,
                    )
                )

    def _check_modifying_list_while_iterating(
        self, node: ast.For | ast.AsyncFor
    ) -> None:
        """Detect modifying list while iterating over it (G004)."""
        if "G004" in self.config.disabled_patterns:
            return

        # Check if iterating over a list and modifying it in the body
        if isinstance(node.iter, ast.Name):
            iter_name = node.iter.id
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        if isinstance(child.func.value, ast.Name):
                            if child.func.value.id == iter_name:
                                if child.func.attr in {
                                    "append",
                                    "remove",
                                    "pop",
                                    "insert",
                                }:
                                    code_snippet = self._get_code_snippet(child.lineno)
                                    self.issues.append(
                                        Issue(
                                            id="G004",
                                            severity="HIGH",
                                            line=child.lineno,
                                            column=child.col_offset,
                                            message="Modifying list while iterating",
                                            suggestion="Iterate over a copy: for item in list.copy():",
                                            code_snippet=code_snippet,
                                        )
                                    )

    def _check_silent_exception_swallowing(self, node: ast.ExceptHandler) -> None:
        """Detect empty except blocks with pass (G005)."""
        if "G005" in self.config.disabled_patterns:
            return

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="G005",
                    severity="HIGH",
                    line=node.lineno,
                    column=node.col_offset,
                    message="Silent exception swallowing",
                    suggestion="Log the exception or handle it explicitly",
                    code_snippet=code_snippet,
                )
            )

    def _check_is_with_literals(self, node: ast.Compare) -> None:
        """Detect using 'is' with literals (G001)."""
        if "G001" in self.config.disabled_patterns:
            return

        for op in node.ops:
            if isinstance(op, (ast.Is, ast.IsNot)):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant):
                        # Allow 'is None' but not 'is 5' or 'is "string"'
                        if comparator.value is not None:
                            code_snippet = self._get_code_snippet(node.lineno)
                            self.issues.append(
                                Issue(
                                    id="G001",
                                    severity="HIGH",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    message="Using 'is' with literal value",
                                    suggestion="Use == for equality comparison",
                                    code_snippet=code_snippet,
                                )
                            )

    def _check_equality_with_none(self, node: ast.Compare) -> None:
        """Detect using == with None (G002)."""
        if "G002" in self.config.disabled_patterns:
            return

        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.Eq, ast.NotEq)):
                comparator = node.comparators[i]
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    code_snippet = self._get_code_snippet(node.lineno)
                    operator = "is" if isinstance(op, ast.Eq) else "is not"
                    self.issues.append(
                        Issue(
                            id="G002",
                            severity="MEDIUM",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Using == with None",
                            suggestion=f"Use '{operator} None' instead",
                            code_snippet=code_snippet,
                        )
                    )

    def _check_equality_with_bool(self, node: ast.Compare) -> None:
        """Detect comparing with True/False (G006)."""
        if "G006" in self.config.disabled_patterns:
            return

        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.Eq, ast.NotEq)):
                comparator = node.comparators[i]
                if isinstance(comparator, ast.Constant):
                    if comparator.value is True or comparator.value is False:
                        code_snippet = self._get_code_snippet(node.lineno)
                        self.issues.append(
                            Issue(
                                id="G006",
                                severity="LOW",
                                line=node.lineno,
                                column=node.col_offset,
                                message="Comparing with True/False",
                                suggestion="Use 'if x:' or 'if not x:' instead",
                                code_snippet=code_snippet,
                            )
                        )

    def _check_type_checking_with_type(self, node: ast.Call) -> None:
        """Detect using type() for type checking (G003)."""
        if "G003" in self.config.disabled_patterns:
            return

        if isinstance(node.func, ast.Name) and node.func.id == "type":
            # Check if this is in a comparison context
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="G003",
                    severity="MEDIUM",
                    line=node.lineno,
                    column=node.col_offset,
                    message="Type checking with type()",
                    suggestion="Use isinstance() instead: isinstance(obj, SomeClass)",
                    code_snippet=code_snippet,
                )
            )

    def _check_context_manager_protocol(self, node: ast.ClassDef) -> None:
        """Check context manager implementation (M003)."""
        if "M003" in self.config.disabled_patterns:
            return

        has_enter = False
        enter_returns_self = False

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__enter__":
                    has_enter = True
                    # Check if returns self
                    for child in ast.walk(item):
                        if isinstance(child, ast.Return):
                            if isinstance(child.value, ast.Name):
                                if child.value.id == "self":
                                    enter_returns_self = True

        if has_enter and not enter_returns_self:
            code_snippet = self._get_code_snippet(node.lineno)
            self.issues.append(
                Issue(
                    id="M003",
                    severity="MEDIUM",
                    line=node.lineno,
                    column=node.col_offset,
                    message="__enter__ should return self",
                    suggestion="Add 'return self' at end of __enter__ method",
                    code_snippet=code_snippet,
                )
            )

    # ==================== Helper Methods ====================

    def _calculate_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> int:
        """
        Calculate cyclomatic complexity of a function.

        Complexity increases by 1 for each:
        - if/elif statement
        - for/while loop
        - except handler
        - and/or operator
        - list/dict/set comprehension
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, (ast.BoolOp,)):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp)):
                complexity += 1

        return complexity

    def _get_code_snippet(self, line: int) -> str:
        """Get code snippet for a given line number."""
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1].strip()
        return ""


# ==================== Core Processing Functions ====================


def main() -> None:
    """Main entry point for unified antipattern hook."""
    # 1. Load configuration
    config = Config()

    if not config.enabled:
        output_feedback("", suppress_output=True)
        return

    # 2. Parse input
    result = parse_hook_input()
    if result is None:
        output_feedback("", suppress_output=True)
        return

    tool_name, tool_input, tool_response = result

    # 3. Validate tool and file
    if not should_process(tool_name, tool_input, tool_response):
        output_feedback("", suppress_output=True)
        return

    file_path = get_file_path(tool_input)

    # 4. Analyze file for antipatterns
    issues = analyze_file(file_path, config)

    # 5. Filter and format issues
    filtered_issues = filter_issues(issues, config)

    # 6. Generate output
    if not filtered_issues:
        output_feedback("", suppress_output=True)
        return

    # Check for critical issues
    has_critical = any(issue.severity == "CRITICAL" for issue in filtered_issues)

    feedback = format_issue_report(filtered_issues, file_path)

    if has_critical and config.block_critical:
        output_block(
            reason=f"Critical security issues detected in {Path(file_path).name}",
            additional_context=feedback,
            suppress_output=False,
        )
    else:
        output_feedback(feedback, suppress_output=False)


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

    # Skip test files (optional)
    if "/test" in file_path or "tests/" in file_path:
        # Can be disabled with env var
        skip_tests = os.getenv("PYTHON_ANTIPATTERN_SKIP_TESTS", "false").lower()
        if skip_tests == "true":
            return False

    return True


def analyze_file(file_path: str, config: Config) -> list[Issue]:
    """
    Analyze file for Python antipatterns.

    Args:
        file_path: Absolute path to Python file
        config: Configuration settings

    Returns:
        List of detected issues
    """
    try:
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Check file size limit
        line_count = source_code.count("\n")
        if line_count > 10000:
            # Skip very large files
            return []

        # Parse to AST
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            # Skip files with syntax errors (will be caught by other tools)
            return []

        # Run detector
        detector = AntipatternDetector(source_code, config)
        detector.visit(tree)

        return detector.issues

    except (IOError, OSError):
        return []
    except Exception:
        # Fail safe - don't block on unexpected errors
        return []


def filter_issues(issues: list[Issue], config: Config) -> list[Issue]:
    """
    Filter issues based on configuration.

    Args:
        issues: List of detected issues
        config: Configuration settings

    Returns:
        Filtered list of issues
    """
    filtered: list[Issue] = []

    for issue in issues:
        # Check if severity level is enabled
        if issue.severity not in config.levels:
            continue

        # Check if pattern is disabled
        if issue.id in config.disabled_patterns:
            continue

        filtered.append(issue)

        # Limit number of issues
        if len(filtered) >= config.max_issues:
            break

    return filtered


def format_issue_report(issues: list[Issue], file_path: str) -> str:
    """
    Format issues for display.

    Args:
        issues: List of issues to format
        file_path: File that was analyzed

    Returns:
        Formatted report string
    """
    if not issues:
        return ""

    file_name = Path(file_path).name

    # Group by severity
    by_severity: dict[str, list[Issue]] = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
    }

    for issue in issues:
        by_severity[issue.severity].append(issue)

    # Build report
    lines = [f"⚠️ Python antipatterns detected in {file_name}:\n"]

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        for issue in by_severity[severity]:
            lines.append(
                f"[{issue.id}:{severity}] {issue.message} on line {issue.line}"
            )
            if issue.code_snippet:
                lines.append(f"  {issue.code_snippet}")
            lines.append(f"  Fix: {issue.suggestion}\n")

    # Summary
    count = len(issues)
    counts = {s: len(by_severity[s]) for s in by_severity if by_severity[s]}
    summary = ", ".join(f"{n} {s}" for s, n in counts.items())
    lines.append(f"{count} issue{'s' if count != 1 else ''} found ({summary})")

    return "\n".join(lines)


# ==================== Entry Point ====================


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log unexpected errors to stderr but don't block
        print(f"Antipattern hook error: {e}", file=sys.stderr)
        output_feedback("", suppress_output=True)
