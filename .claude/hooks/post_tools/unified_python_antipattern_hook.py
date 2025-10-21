#!/usr/bin/env python3
"""
Unified Python Post-Tools Checker
==================================
Detects Python-specific antipatterns not covered by type checkers or dead code detectors.
Focuses on runtime issues, security vulnerabilities, and code quality problems.

Exit codes:
- 0: All checks passed or only warnings (outputs JSON)
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, TypedDict, cast

# Constants for thresholds
MAX_ATTRIBUTE_ACCESS_IN_LOOP = 3
MIN_LIST_SIZE_FOR_SET_RECOMMENDATION = 5
MAX_NESTED_COMPREHENSIONS = 2
MAX_COMPREHENSION_CONDITIONS = 2
MAX_FUNCTION_NESTING_DEPTH = 3
MAX_FUNCTION_ARGUMENTS = 5
MAX_FUNCTION_COMPLEXITY = 15
MAX_FILE_LINES = 1000
MAX_IMPORT_SPREAD = 20


# Type definitions for JSON input/output
class ToolInput(TypedDict):
    """Type definition for tool input parameters."""

    file_path: str


class HookSpecificOutput(TypedDict):
    """Hook-specific output structure."""

    hookEventName: Literal["PostToolUse"]
    additionalContext: str


class HookOutput(TypedDict, total=False):
    """Output JSON structure for PostToolUse."""

    decision: Literal["block"]
    reason: str
    hookSpecificOutput: HookSpecificOutput


class Severity(Enum):
    """Issue severity levels."""

    BLOCK = "BLOCKED"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    """Represents a code quality issue."""

    severity: Severity
    category: str
    message: str
    line: int | None = None
    details: str = ""


@dataclass
class CheckResult:
    """Results from all checks."""

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


class PythonAntipatternChecker:
    """
    Detects Python antipatterns that are NOT caught by:
    - Type checkers (basedpyright/mypy)
    - Dead code detectors (vulture)

    Focuses on:
    - Runtime bugs (mutable defaults, dangerous functions)
    - Security vulnerabilities (SQL injection, hardcoded secrets)
    - Performance antipatterns (string concatenation in loops)
    - Code complexity issues
    - Resource management issues
    - Python-specific gotchas
    """

    def __init__(self, tool_input: ToolInput) -> None:
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
        self.file_path: Path = Path(file_path)
        self.content: str = ""
        self.tree: ast.AST | None = None
        self.results: CheckResult = CheckResult()

    def run_all_checks(self) -> CheckResult:
        """Run all antipattern checks."""
        # Validate file exists and is Python
        if not self._validate_file():
            return self.results

        # Parse the file
        if not self._parse_file():
            return self.results

        # === RUNTIME ANTIPATTERNS (not caught by type checkers) ===
        self._check_mutable_defaults()
        self._check_dangerous_functions()
        self._check_bare_except()
        self._check_assert_usage()
        self._check_global_usage()
        self._check_class_variable_defaults()
        self._check_late_binding_closures()

        # === PERFORMANCE ANTIPATTERNS ===
        self._check_string_concatenation_in_loops()
        self._check_repeated_attribute_access()
        self._check_inefficient_containment_checks()
        self._check_unnecessary_lambda()
        self._check_list_concatenation()

        # === COMPLEXITY ANTIPATTERNS ===
        self._check_list_comprehension_complexity()
        self._check_nested_functions_complexity()
        self._check_function_complexity()
        self._check_too_many_arguments()
        self._check_unnecessary_else_after_return()

        # === SECURITY ANTIPATTERNS ===
        self._run_security_patterns_check()
        self._check_tempfile_usage()
        self._check_random_usage_for_security()

        # === CODE ORGANIZATION ===
        self._check_file_length()
        self._check_import_organization()
        self._check_wildcard_imports()

        # === RESOURCE MANAGEMENT ===
        self._check_file_resource_management()

        # === PYTHON GOTCHAS ===
        self._check_is_for_equality()
        self._check_type_checking_antipattern()
        self._check_modifying_list_while_iterating()
        self._check_silent_exception_swallowing()

        return self.results

    def _validate_file(self) -> bool:
        """Validate the file exists and is a Python file."""
        # If no file path provided or it's just ".", skip validation (not a file operation)
        if not self.file_path or str(self.file_path) in {"", ".", "./"}:
            return False

        if not self.file_path.exists():
            self.results.add_issue(
                Issue(
                    severity=Severity.BLOCK,
                    category="File Error",
                    message=f"File not found: {self.file_path}",
                )
            )
            return False

        if self.file_path.suffix not in {".py", ".pyi"}:
            # Not a Python file, but don't block - just skip the check
            return False

        return True

    def _parse_file(self) -> bool:
        """Parse the Python file into an AST."""
        try:
            self.content = self.file_path.read_text(encoding="utf-8")
            self.tree = ast.parse(self.content)
            return True
        except SyntaxError as e:
            self.results.add_issue(
                Issue(
                    severity=Severity.BLOCK,
                    category="Syntax Error",
                    message=f"Python syntax error at line {e.lineno}: {e.msg}",
                    line=e.lineno,
                )
            )
            return False
        except Exception as e:
            self.results.add_issue(
                Issue(
                    severity=Severity.BLOCK,
                    category="Parse Error",
                    message=f"Failed to parse file: {str(e)}",
                )
            )
            return False

    def _check_mutable_defaults(self) -> None:
        """Check for mutable default arguments (critical runtime bug)."""
        if not self.tree:
            return

        class MutableDefaultVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._check_function(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._check_function(node)
                self.generic_visit(node)

            def _check_function(
                self, node: ast.FunctionDef | ast.AsyncFunctionDef
            ) -> None:
                defaults = node.args.defaults
                args = node.args.args
                for i, default in enumerate(defaults):
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        # Cache args access
                        param_idx = len(args) - len(defaults) + i
                        if 0 <= param_idx < len(args):
                            param_name = args[param_idx].arg
                        else:
                            param_name = "unknown"

                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.BLOCK,
                                category="Mutable Default",
                                message=f"Function '{node.name}' has mutable default for '{param_name}'",
                                line=node.lineno,
                                details="Use None and initialize inside function to avoid shared state bugs",
                            )
                        )

        visitor = MutableDefaultVisitor(self)
        visitor.visit(self.tree)

    def _check_class_variable_defaults(self) -> None:
        """Check for mutable class variables (shared between instances)."""
        if not self.tree:
            return

        class ClassVariableVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                for item in node.body:
                    if isinstance(item, (ast.AnnAssign, ast.Assign)):
                        # Check if it's a class variable (not in __init__)
                        value = (
                            item.value
                            if isinstance(item, ast.AnnAssign)
                            else item.value
                        )
                        if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.WARNING,
                                    category="Mutable Class Variable",
                                    message=f"Class '{node.name}' has mutable class variable",
                                    line=item.lineno,
                                    details="Mutable class variables are shared between instances. Initialize in __init__",
                                )
                            )
                self.generic_visit(node)

        visitor = ClassVariableVisitor(self)
        visitor.visit(self.tree)

    def _check_dangerous_functions(self) -> None:
        """Check for dangerous function usage like eval, exec."""
        if not self.tree:
            return

        dangerous_funcs = {
            "eval": Severity.BLOCK,
            "exec": Severity.BLOCK,
            "compile": Severity.WARNING,
            "__import__": Severity.WARNING,
            "globals": Severity.WARNING,
            "locals": Severity.WARNING,
        }

        class DangerousFuncVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in dangerous_funcs:
                        severity = dangerous_funcs[func_name]
                        self.checker.results.add_issue(
                            Issue(
                                severity=severity,
                                category="Dangerous Function",
                                message=f"Use of '{func_name}()' is dangerous",
                                line=node.lineno,
                                details="Can lead to code injection vulnerabilities",
                            )
                        )
                self.generic_visit(node)

        visitor = DangerousFuncVisitor(self)
        visitor.visit(self.tree)

    def _check_bare_except(self) -> None:
        """Check for bare except clauses."""
        if not self.tree:
            return

        class BareExceptVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.type is None:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Bare Except",
                            message="Bare 'except:' clause catches all exceptions",
                            line=node.lineno,
                            details="Use 'except Exception:' or specific exception types",
                        )
                    )
                self.generic_visit(node)

        visitor = BareExceptVisitor(self)
        visitor.visit(self.tree)

    def _check_silent_exception_swallowing(self) -> None:
        """Check for silent exception swallowing (except: pass)."""
        if not self.tree:
            return

        class SilentExceptVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                # Check if body is just pass or ...
                if len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Pass):
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.BLOCK,
                                category="Silent Exception",
                                message="Silent exception swallowing with 'pass'",
                                line=node.lineno,
                                details="At least log the exception or add a comment explaining why it's ignored",
                            )
                        )
                    elif isinstance(stmt, ast.Expr) and isinstance(
                        stmt.value, ast.Constant
                    ):
                        if stmt.value.value == ...:
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.BLOCK,
                                    category="Silent Exception",
                                    message="Silent exception swallowing with '...'",
                                    line=node.lineno,
                                    details="At least log the exception or add a comment",
                                )
                            )
                self.generic_visit(node)

        visitor = SilentExceptVisitor(self)
        visitor.visit(self.tree)

    def _check_wildcard_imports(self) -> None:
        """Check for wildcard imports (from module import *)."""
        if not self.tree:
            return

        class WildcardImportVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                for alias in node.names:
                    if alias.name == "*":
                        module_name = node.module or "module"
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.WARNING,
                                category="Wildcard Import",
                                message=f"Wildcard import from '{module_name}'",
                                line=node.lineno,
                                details="Explicitly import what you need to avoid namespace pollution",
                            )
                        )
                self.generic_visit(node)

        visitor = WildcardImportVisitor(self)
        visitor.visit(self.tree)

    def _check_is_for_equality(self) -> None:
        """Check for using 'is' for value comparison instead of '=='."""
        if not self.tree:
            return

        class IsComparisonVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Compare(self, node: ast.Compare) -> None:
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Is, ast.IsNot)):
                        # Check if comparing to literals other than None
                        if isinstance(comparator, ast.Constant):
                            if comparator.value not in (None, True, False):
                                self.checker.results.add_issue(
                                    Issue(
                                        severity=Severity.BLOCK,
                                        category="Is Comparison",
                                        message=f"Using 'is' to compare with literal value {repr(comparator.value)}",
                                        line=node.lineno,
                                        details="Use '==' for value comparison, 'is' for identity comparison",
                                    )
                                )
                self.generic_visit(node)

        visitor = IsComparisonVisitor(self)
        visitor.visit(self.tree)

    def _check_type_checking_antipattern(self) -> None:
        """Check for using type() instead of isinstance()."""
        if not self.tree:
            return

        class TypeCheckVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Compare(self, node: ast.Compare) -> None:
                # Look for patterns like: type(x) == int
                if isinstance(node.left, ast.Call):
                    if (
                        isinstance(node.left.func, ast.Name)
                        and node.left.func.id == "type"
                    ):
                        for op in node.ops:
                            if isinstance(op, (ast.Eq, ast.NotEq)):
                                self.checker.results.add_issue(
                                    Issue(
                                        severity=Severity.WARNING,
                                        category="Type Check",
                                        message="Using type() for type checking",
                                        line=node.lineno,
                                        details="Use isinstance() for better inheritance support",
                                    )
                                )
                                break
                self.generic_visit(node)

        visitor = TypeCheckVisitor(self)
        visitor.visit(self.tree)

    def _check_modifying_list_while_iterating(self) -> None:
        """Check for modifying a list while iterating over it."""
        if not self.tree:
            return

        class ListModificationVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.loop_targets: list[str] = []

            def visit_For(self, node: ast.For) -> None:
                # Track what we're iterating over
                target_name = None
                if isinstance(node.iter, ast.Name):
                    target_name = node.iter.id

                if target_name:
                    self.loop_targets.append(target_name)

                    # Check for modifications in loop body
                    for stmt in ast.walk(node):
                        if isinstance(stmt, ast.Call):
                            func = stmt.func
                            if isinstance(func, ast.Attribute):
                                if isinstance(func.value, ast.Name):
                                    if func.value.id == target_name:
                                        if func.attr in (
                                            "append",
                                            "remove",
                                            "pop",
                                            "clear",
                                            "extend",
                                        ):
                                            self.checker.results.add_issue(
                                                Issue(
                                                    severity=Severity.BLOCK,
                                                    category="List Modification",
                                                    message=f"Modifying list '{target_name}' while iterating over it",
                                                    line=node.lineno,
                                                    details="Create a copy of the list or use list comprehension",
                                                )
                                            )
                                            break

                    self.loop_targets.pop()

                self.generic_visit(node)

        visitor = ListModificationVisitor(self)
        visitor.visit(self.tree)

    def _check_file_resource_management(self) -> None:
        """Check for files opened without context managers."""
        if not self.tree:
            return

        class FileResourceVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.in_with: bool = False

            def visit_With(self, node: ast.With) -> None:
                old_in_with = self.in_with
                self.in_with = True
                self.generic_visit(node)
                self.in_with = old_in_with

            def visit_Call(self, node: ast.Call) -> None:
                if not self.in_with:
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id

                    if func_name == "open":
                        # Check if it's assigned to a variable (not used directly)
                        parent = getattr(node, "parent", None)
                        if not isinstance(parent, ast.With):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.WARNING,
                                    category="Resource Management",
                                    message="File opened without context manager",
                                    line=node.lineno,
                                    details="Use 'with open(...) as f:' to ensure proper file closure",
                                )
                            )
                self.generic_visit(node)

        visitor = FileResourceVisitor(self)
        visitor.visit(self.tree)

    def _check_late_binding_closures(self) -> None:
        """Check for late binding closure issues in loops."""
        if not self.tree:
            return

        class LateBindingVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_For(self, node: ast.For) -> None:
                # Look for lambda or function definitions in loops
                for stmt in ast.walk(node):
                    if isinstance(stmt, (ast.Lambda, ast.FunctionDef)):
                        # Check if it references the loop variable
                        loop_var = None
                        if isinstance(node.target, ast.Name):
                            loop_var = node.target.id

                        if loop_var:
                            # Simple check: look for the loop variable in the lambda/function
                            for subnode in ast.walk(stmt):
                                if (
                                    isinstance(subnode, ast.Name)
                                    and subnode.id == loop_var
                                ):
                                    self.checker.results.add_issue(
                                        Issue(
                                            severity=Severity.WARNING,
                                            category="Late Binding",
                                            message=f"Potential late binding closure issue with '{loop_var}'",
                                            line=stmt.lineno,
                                            details="Use default argument or functools.partial to capture loop variable",
                                        )
                                    )
                                    break

                self.generic_visit(node)

        visitor = LateBindingVisitor(self)
        visitor.visit(self.tree)

    def _check_unnecessary_else_after_return(self) -> None:
        """Check for unnecessary else after return/break/continue."""
        if not self.tree:
            return

        class UnnecessaryElseVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_If(self, node: ast.If) -> None:
                # Check if the if-branch ends with return/break/continue
                if node.orelse and node.body:
                    last_stmt = node.body[-1]
                    if isinstance(last_stmt, (ast.Return, ast.Break, ast.Continue)):
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.WARNING,
                                category="Code Style",
                                message="Unnecessary 'else' after return/break/continue",
                                line=node.lineno,
                                details="Remove 'else' and dedent the code for better readability",
                            )
                        )
                self.generic_visit(node)

        visitor = UnnecessaryElseVisitor(self)
        visitor.visit(self.tree)

    def _check_unnecessary_lambda(self) -> None:
        """Check for unnecessary lambda functions."""
        if not self.tree:
            return

        class UnnecessaryLambdaVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Lambda(self, node: ast.Lambda) -> None:
                # Check for lambda x: func(x) pattern
                if isinstance(node.body, ast.Call):
                    # Check if lambda args match call args exactly
                    lambda_args = [arg.arg for arg in node.args.args]
                    call_args: list[str] = []

                    for arg in node.body.args:
                        if isinstance(arg, ast.Name):
                            call_args.append(arg.id)
                        else:
                            break

                    if lambda_args == call_args and len(lambda_args) > 0:
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.WARNING,
                                category="Code Style",
                                message="Unnecessary lambda wrapper",
                                line=node.lineno,
                                details="Use the function directly without lambda",
                            )
                        )
                self.generic_visit(node)

        visitor = UnnecessaryLambdaVisitor(self)
        visitor.visit(self.tree)

    def _check_list_concatenation(self) -> None:
        """Check for using += with lists instead of extend()."""
        if not self.tree:
            return

        class ListConcatVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_AugAssign(self, node: ast.AugAssign) -> None:
                if isinstance(node.op, ast.Add):
                    # Check if right side is a list and left is likely a list
                    if isinstance(node.value, ast.List):
                        if isinstance(node.target, ast.Name):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.WARNING,
                                    category="Performance",
                                    message="Using += for list concatenation",
                                    line=node.lineno,
                                    details="Use list.extend() for better performance",
                                )
                            )
                self.generic_visit(node)

        visitor = ListConcatVisitor(self)
        visitor.visit(self.tree)

    def _check_assert_usage(self) -> None:
        """Check for assertions used for validation."""
        if not self.tree:
            return

        class AssertVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.in_test: bool = False

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                # Don't warn for test functions
                old_in_test = self.in_test
                if node.name.startswith("test_") or node.name.startswith("Test"):
                    self.in_test = True
                self.generic_visit(node)
                self.in_test = old_in_test

            def visit_Assert(self, node: ast.Assert) -> None:
                if not self.in_test:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Assert for Validation",
                            message="Assert used outside test code",
                            line=node.lineno,
                            details="Assertions can be disabled with -O flag, use explicit validation",
                        )
                    )
                self.generic_visit(node)

        visitor = AssertVisitor(self)
        visitor.visit(self.tree)

    def _check_global_usage(self) -> None:
        """Check for global variable usage."""
        if not self.tree:
            return

        class GlobalVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Global(self, node: ast.Global) -> None:
                for name in node.names:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Global Variable",
                            message=f"Use of global variable '{name}'",
                            line=node.lineno,
                            details="Consider using function parameters or class attributes",
                        )
                    )
                self.generic_visit(node)

        visitor = GlobalVisitor(self)
        visitor.visit(self.tree)

    def _check_string_concatenation_in_loops(self) -> None:
        """Check for string concatenation in loops (performance antipattern)."""
        if not self.tree:
            return

        class StringConcatVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.in_loop: bool = False

            def visit_For(self, node: ast.For) -> None:
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop

            def visit_While(self, node: ast.While) -> None:
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop

            def visit_AugAssign(self, node: ast.AugAssign) -> None:
                if self.in_loop and isinstance(node.op, ast.Add):
                    # Check if target is likely a string
                    if isinstance(node.target, ast.Name):
                        # Simple heuristic: variable names containing 'str', 'text', 'msg'
                        var_name = node.target.id.lower()
                        if any(
                            s in var_name
                            for s in ["str", "text", "msg", "result", "output"]
                        ):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.WARNING,
                                    category="Performance",
                                    message="String concatenation in loop with '+='",
                                    line=node.lineno,
                                    details="Use list.append() and ''.join() for better performance",
                                )
                            )
                self.generic_visit(node)

        visitor = StringConcatVisitor(self)
        visitor.visit(self.tree)

    def _check_list_comprehension_complexity(self) -> None:
        """Check for overly complex list comprehensions."""
        if not self.tree:
            return

        class ComprehensionVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_ListComp(self, node: ast.ListComp) -> None:
                # Count nested comprehensions and conditions
                nested_count = len(node.generators)
                condition_count = sum(len(g.ifs) for g in node.generators)

                if nested_count > MAX_NESTED_COMPREHENSIONS:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Complexity",
                            message=f"List comprehension with {nested_count} nested loops",
                            line=node.lineno,
                            details="Consider using regular loops for readability",
                        )
                    )
                elif condition_count > MAX_COMPREHENSION_CONDITIONS:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Complexity",
                            message=f"List comprehension with {condition_count} conditions",
                            line=node.lineno,
                            details="Consider using filter() or regular loops",
                        )
                    )
                self.generic_visit(node)

        visitor = ComprehensionVisitor(self)
        visitor.visit(self.tree)

    def _check_nested_functions_complexity(self) -> None:
        """Check for deeply nested functions."""
        if not self.tree:
            return

        class NestingVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.depth: int = 0

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.depth += 1
                if self.depth > MAX_FUNCTION_NESTING_DEPTH:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Complexity",
                            message=f"Function '{node.name}' is nested {self.depth} levels deep",
                            line=node.lineno,
                            details=f"Maximum recommended nesting is {MAX_FUNCTION_NESTING_DEPTH}",
                        )
                    )
                self.generic_visit(node)
                self.depth -= 1

        visitor = NestingVisitor(self)
        visitor.visit(self.tree)

    def _check_repeated_attribute_access(self) -> None:
        """Check for repeated attribute access in loops (performance issue)."""
        if not self.tree:
            return

        class AttributeAccessVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.in_loop: bool = False
                self.attribute_counts: dict[str, int] = {}

            def visit_For(self, node: ast.For) -> None:
                old_in_loop = self.in_loop
                old_counts = self.attribute_counts.copy()
                self.in_loop = True
                self.attribute_counts = {}

                self.generic_visit(node)

                # Check if any attribute was accessed more than threshold
                for attr_chain, count in self.attribute_counts.items():
                    if count > MAX_ATTRIBUTE_ACCESS_IN_LOOP:
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.WARNING,
                                category="Performance",
                                message=f"Attribute '{attr_chain}' accessed {count} times in loop",
                                line=node.lineno,
                                details="Cache the attribute value before the loop",
                            )
                        )

                self.in_loop = old_in_loop
                self.attribute_counts = old_counts

            def visit_Attribute(self, node: ast.Attribute) -> None:
                if self.in_loop:
                    # Build the attribute chain (e.g., "self.config.value")
                    chain = self._get_attribute_chain(node)
                    if chain and "." in chain:  # Only track chained attributes
                        self.attribute_counts[chain] = (
                            self.attribute_counts.get(chain, 0) + 1
                        )
                self.generic_visit(node)

            def _get_attribute_chain(self, node: ast.expr) -> str | None:
                """Build string representation of attribute chain."""
                if isinstance(node, ast.Name):
                    return node.id
                if isinstance(node, ast.Attribute):
                    base = self._get_attribute_chain(node.value)
                    if base:
                        return f"{base}.{node.attr}"
                return None

        visitor = AttributeAccessVisitor(self)
        visitor.visit(self.tree)

    def _check_inefficient_containment_checks(self) -> None:
        """Check for inefficient 'in' checks on lists in conditions."""
        if not self.tree:
            return

        class ContainmentVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_Compare(self, node: ast.Compare) -> None:
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, ast.In):
                        # Check if it's a list literal with many elements
                        if (
                            isinstance(comparator, ast.List)
                            and len(comparator.elts)
                            > MIN_LIST_SIZE_FOR_SET_RECOMMENDATION
                        ):
                            self.checker.results.add_issue(
                                Issue(
                                    severity=Severity.WARNING,
                                    category="Performance",
                                    message=f"Using 'in' with list literal of {len(comparator.elts)} elements",
                                    line=node.lineno,
                                    details="Use a set for O(1) lookup instead of O(n) list search",
                                )
                            )
                self.generic_visit(node)

        visitor = ContainmentVisitor(self)
        visitor.visit(self.tree)

    def _check_too_many_arguments(self) -> None:
        """Check for functions with too many arguments."""
        if not self.tree:
            return

        class ArgumentCountVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                # Don't count self/cls
                args = node.args.args
                if args and args[0].arg in ("self", "cls"):
                    args = args[1:]

                if len(args) > MAX_FUNCTION_ARGUMENTS:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Complexity",
                            message=f"Function '{node.name}' has {len(args)} arguments (max recommended: {MAX_FUNCTION_ARGUMENTS})",
                            line=node.lineno,
                            details="Consider using a configuration object or keyword arguments",
                        )
                    )
                self.generic_visit(node)

        visitor = ArgumentCountVisitor(self)
        visitor.visit(self.tree)

    def _check_tempfile_usage(self) -> None:
        """Check for insecure temporary file usage."""
        if not self.tree:
            return

        class TempfileVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker
                self.has_tempfile_import: bool = False

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    if alias.name == "tempfile":
                        self.has_tempfile_import = True
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module == "tempfile":
                    self.has_tempfile_import = True
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                if self.has_tempfile_import:
                    func_name = None
                    if isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id

                    # Check for insecure functions
                    if func_name and func_name in ("mktemp", "mkstemp"):
                        msg = f"Using potentially insecure '{func_name}' for temporary files"
                        self.checker.results.add_issue(
                            Issue(
                                severity=Severity.WARNING,
                                category="Security",
                                message=msg,
                                line=node.lineno,
                                details="Use NamedTemporaryFile or TemporaryDirectory for better security",
                            )
                        )
                self.generic_visit(node)

        visitor = TempfileVisitor(self)
        visitor.visit(self.tree)

    def _check_random_usage_for_security(self) -> None:
        """Check for using random module for security purposes."""
        if not self.content:
            return

        # Look for patterns suggesting security usage of random
        security_contexts = [
            (
                r"random\.[\w]+\([^)]*\).*(?:password|token|secret|key|salt|nonce)",
                "Using 'random' module for security-sensitive values",
            ),
            (
                r"(?:password|token|secret|key|salt|nonce).*=.*random\.[\w]+\([^)]*\)",
                "Using 'random' module for cryptographic purposes",
            ),
        ]

        for pattern, description in security_contexts:
            if match := re.search(pattern, self.content, re.IGNORECASE):
                line_no = self.content[: match.start()].count("\n") + 1
                self.results.add_issue(
                    Issue(
                        severity=Severity.BLOCK,
                        category="Security",
                        message=description,
                        line=line_no,
                        details="Use 'secrets' module for cryptographically secure randomness",
                    )
                )

    def _run_security_patterns_check(self) -> None:
        """Check for common security antipatterns."""
        if not self.content:
            return

        # Skip pattern checks if this is a pattern definition file
        # (check for regex pattern definitions or security checker code)
        if "sql_patterns" in self.content.lower() or "re.search" in self.content:
            # Likely a security checker or pattern definition file, skip regex pattern checks
            return

        # SQL injection patterns
        sql_patterns = [
            (r'".*SELECT.*FROM.*WHERE.*\+', "SQL query with string concatenation"),
            (r'".*SELECT.*FROM.*WHERE.*%\s', "SQL query with % formatting"),
            (r'f".*SELECT.*FROM.*WHERE.*\{', "SQL query with f-string"),
            (r"\.format\(.*SELECT.*FROM.*WHERE", "SQL query with .format()"),
        ]

        for pattern, description in sql_patterns:
            if re.search(pattern, self.content, re.IGNORECASE | re.DOTALL):
                self.results.add_issue(
                    Issue(
                        severity=Severity.BLOCK,
                        category="SQL Injection",
                        message=f"Potential SQL injection: {description}",
                        details="Use parameterized queries with placeholders",
                    )
                )

        # Hardcoded secrets patterns
        secret_patterns = [
            (
                r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']',
                "Hardcoded password",
            ),
            (
                r'(?:api_key|apikey|api_secret)\s*=\s*["\'][^"\']{16,}["\']',
                "Hardcoded API key",
            ),
            (
                r'(?:token|secret|private_key)\s*=\s*["\'][^"\']{20,}["\']',
                "Hardcoded secret/token",
            ),
            (
                r'(?:AWS|AZURE|GCP|GITHUB)_[A-Z_]*(?:KEY|SECRET|TOKEN)\s*=\s*["\'][^"\']+["\']',
                "Hardcoded cloud credential",
            ),
        ]

        for pattern, description in secret_patterns:
            if match := re.search(pattern, self.content, re.IGNORECASE):
                line_no = self.content[: match.start()].count("\n") + 1
                self.results.add_issue(
                    Issue(
                        severity=Severity.BLOCK,
                        category="Security",
                        message=description,
                        line=line_no,
                        details="Use environment variables or secure vaults for secrets",
                    )
                )

        # Command injection patterns
        cmd_patterns = [
            (r"os\.system\s*\([^)]*\+[^)]*\)", "os.system with string concatenation"),
            (
                r"subprocess\.[\w]+\s*\([^)]*shell\s*=\s*True[^)]*\+",
                "subprocess with shell=True and concatenation",
            ),
            (r"eval\s*\([^)]*(?:input|request|user)", "eval with user input"),
            (r"exec\s*\([^)]*(?:input|request|user)", "exec with user input"),
        ]

        for pattern, description in cmd_patterns:
            if re.search(pattern, self.content, re.IGNORECASE):
                self.results.add_issue(
                    Issue(
                        severity=Severity.BLOCK,
                        category="Command Injection",
                        message=f"Potential command injection: {description}",
                        details="Use subprocess with list arguments, avoid shell=True",
                    )
                )

        # Unsafe deserialization - skip if it's in import or documentation
        if "pickle.loads" in self.content or "pickle.load" in self.content:
            # Check it's not just an import statement or comment
            if not re.search(
                r"(?:from|import)\s+pickle|#.*pickle", self.content, re.IGNORECASE
            ):
                if any(
                    word in self.content.lower()
                    for word in ["request", "user", "input", "client", "untrusted"]
                ):
                    self.results.add_issue(
                        Issue(
                            severity=Severity.BLOCK,
                            category="Unsafe Deserialization",
                            message="Pickle usage with potentially untrusted data",
                            details="Pickle can execute arbitrary code. Use JSON or other safe formats",
                        )
                    )

        # YAML safe loading
        if "yaml.load" in self.content and "yaml.safe_load" not in self.content:
            self.results.add_issue(
                Issue(
                    severity=Severity.BLOCK,
                    category="Security",
                    message="Using yaml.load instead of yaml.safe_load",
                    details="yaml.load can execute arbitrary code. Use yaml.safe_load",
                )
            )

    def _check_function_complexity(self) -> None:
        """Check cyclomatic complexity of functions."""
        if not self.tree:
            return

        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self, checker: PythonAntipatternChecker) -> None:
                self.checker: PythonAntipatternChecker = checker

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                complexity = self._calculate_complexity(node)
                if complexity > MAX_FUNCTION_COMPLEXITY:
                    self.checker.results.add_issue(
                        Issue(
                            severity=Severity.WARNING,
                            category="Complexity",
                            message=f"Function '{node.name}' has high complexity ({complexity})",
                            line=node.lineno,
                            details="Consider breaking into smaller functions",
                        )
                    )
                self.generic_visit(node)

            def _calculate_complexity(self, node: ast.FunctionDef) -> int:
                """Simple complexity calculation."""
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(
                        child, (ast.If, ast.While, ast.For, ast.ExceptHandler)
                    ):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                return complexity

        visitor = ComplexityVisitor(self)
        visitor.visit(self.tree)

    def _check_file_length(self) -> None:
        """Check if file is too long."""
        if self.content:
            lines = self.content.split("\n")
            if len(lines) > MAX_FILE_LINES:
                self.results.add_issue(
                    Issue(
                        severity=Severity.WARNING,
                        category="File Size",
                        message=f"File has {len(lines)} lines (exceeds {MAX_FILE_LINES})",
                        details="Consider splitting into multiple modules",
                    )
                )

    def _check_import_organization(self) -> None:
        """Check if imports are properly organized."""
        if not self.tree:
            return

        import_lines: list[int] = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_lines.append(node.lineno)

        if import_lines and max(import_lines) - min(import_lines) > MAX_IMPORT_SPREAD:
            self.results.add_issue(
                Issue(
                    severity=Severity.WARNING,
                    category="Import Organization",
                    message="Imports are scattered throughout the file",
                    details="Group all imports at the top of the file",
                )
            )


def main() -> None:
    """
    Main entry point for unified Python post-tools checking.

    Reads file path from stdin JSON and runs comprehensive checks.
    Outputs JSON result for PostToolUse hook.
    """

    try:
        # Read input from stdin
        input_text = sys.stdin.read()

        if not input_text:
            # No input provided - non-blocking error
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)

        try:
            # Parse JSON input
            input_data_raw: object = json.loads(input_text)  # type: ignore[reportUnknownVariableType]
        except json.JSONDecodeError as e:
            # Invalid JSON - non-blocking error
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)

        # Type-safe extraction with validation
        if not isinstance(input_data_raw, dict):
            print("Error: Input must be a JSON object", file=sys.stderr)
            sys.exit(1)

        # Cast to dict[str, object] after validation
        input_dict = cast(dict[str, object], input_data_raw)

        # Extract tool_input
        tool_input_obj = input_dict.get("tool_input", {})

        if not isinstance(tool_input_obj, dict):
            # Invalid tool_input - skip check (not an error, just not applicable)
            output_success()
            return

        # Cast tool_input to dict after validation
        tool_input_dict = cast(dict[str, object], tool_input_obj)

        # Extract file_path
        file_path_val = tool_input_dict.get("file_path")

        # Create typed tool input
        typed_tool_input: ToolInput = {
            "file_path": file_path_val if isinstance(file_path_val, str) else ""
        }

        # Run all checks
        checker = PythonAntipatternChecker(tool_input=typed_tool_input)
        results = checker.run_all_checks()

        # Output results based on findings
        if results.has_blocks():
            output_blocked(results)
        elif results.warnings:
            output_warnings(results)
        else:
            # Get filename for success message
            file_name = Path(typed_tool_input["file_path"]).name
            output_success(file_name)

    except Exception as e:
        # Unexpected error - non-blocking error
        print(f"Error: Unexpected error in hook: {e}", file=sys.stderr)
        sys.exit(1)


def output_success(file_name: str = "") -> None:
    """Output success result with optional filename."""
    context = ""
    if file_name:
        context = f"✅ Python antipattern check passed for {file_name}"

    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def output_warnings(results: CheckResult) -> None:
    """Output warning results."""
    separator_line = "=" * 60
    warning_lines = [f"⚠️  Python Quality Warnings ({len(results.warnings)} found):"]
    warning_lines.append(str(separator_line))

    for issue in results.warnings:
        line_info = f" (line {issue.line})" if issue.line else ""
        msg = f"  • [{issue.category}] {issue.message}{line_info}"
        warning_lines.append(msg)
        if issue.details:
            warning_lines.append(f"    → {issue.details}")

    warning_lines.append(str(separator_line))
    warning_lines.append(
        "💡 Consider addressing these warnings to improve code quality"
    )

    output: HookOutput = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(warning_lines),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def output_blocked(results: CheckResult) -> None:
    """Output blocking results."""
    separator_line = "=" * 60
    issue_lines = [f"❌ Python Quality Issues ({len(results.blocks)} blocking):"]
    issue_lines.append(str(separator_line))

    for issue in results.blocks:
        line_info = f" (line {issue.line})" if issue.line else ""
        msg = f"  • [{issue.category}] {issue.message}{line_info}"
        issue_lines.append(msg)
        if issue.details:
            issue_lines.append(f"    → {issue.details}")

    issue_lines.append(str(separator_line))
    issue_lines.append("🔧 Fix these issues before proceeding")

    reason = f"{len(results.blocks)} critical Python antipattern(s) detected"

    output: HookOutput = {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(issue_lines),
        },
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
