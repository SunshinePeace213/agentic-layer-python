#!/usr/bin/env python3
"""
Unit Tests for Unified Python Antipattern Hook
===============================================

Tests the detection of 40+ Python antipatterns across 7 categories:
- Runtime issues
- Performance problems
- Complexity concerns
- Security vulnerabilities
- Code organization
- Resource management
- Python gotchas

Test Strategy:
- Each antipattern has at least one test case
- Tests use synthetic code snippets that trigger specific patterns
- Tests verify correct issue ID, severity, and message
- Integration tests verify end-to-end functionality
"""

import ast
import sys
from pathlib import Path

import pytest

# Add hook directory to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent.parent / ".claude" / "hooks" / "post_tools"
    ),
)

from unified_python_antipattern_hook import (  # type: ignore[reportMissingImports]
    AntipatternDetector,
    Config,
    Issue,
    filter_issues,
    format_issue_report,
)


# ==================== Test Helpers ====================


def detect_antipatterns(code: str, config: Config | None = None) -> list[Issue]:
    """Helper function to detect antipatterns in code snippet."""
    if config is None:
        config = Config()
    detector = AntipatternDetector(code, config)
    try:
        tree = ast.parse(code)
        detector.visit(tree)
        return detector.issues
    except SyntaxError:
        return []


def has_issue(issues: list[Issue], issue_id: str) -> bool:
    """Check if issues list contains an issue with given ID."""
    return any(issue.id == issue_id for issue in issues)


def get_issue(issues: list[Issue], issue_id: str) -> Issue | None:
    """Get first issue with given ID."""
    for issue in issues:
        if issue.id == issue_id:
            return issue
    return None


# ==================== Runtime Antipattern Tests ====================


def test_detect_mutable_default_list() -> None:
    """Test detection of mutable default arguments with list."""
    code = """
def process(items=[]):
    items.append(1)
    return items
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R001")
    issue = get_issue(issues, "R001")
    assert issue is not None
    assert issue.severity == "HIGH"


def test_detect_mutable_default_dict() -> None:
    """Test detection of mutable default arguments with dict."""
    code = """
def process(config={}):
    config['key'] = 'value'
    return config
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R001")


def test_detect_mutable_default_set() -> None:
    """Test detection of mutable default arguments with set literal."""
    code = """
def process(items={1, 2, 3}):
    items.add(4)
    return items
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R001")


def test_no_issue_with_none_default() -> None:
    """Test that None defaults don't trigger mutable default warning."""
    code = """
def process(items=None):
    if items is None:
        items = []
    return items
"""
    issues = detect_antipatterns(code)
    assert not has_issue(issues, "R001")


def test_detect_dangerous_eval() -> None:
    """Test detection of eval() usage."""
    code = """
user_input = "1 + 1"
result = eval(user_input)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R002")
    issue = get_issue(issues, "R002")
    assert issue is not None
    assert issue.severity == "HIGH"


def test_detect_dangerous_exec() -> None:
    """Test detection of exec() usage."""
    code = """
code = "print('hello')"
exec(code)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R002")


def test_detect_bare_except() -> None:
    """Test detection of bare except clauses."""
    code = """
try:
    risky_operation()
except:
    pass
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R003")
    issue = get_issue(issues, "R003")
    assert issue is not None
    assert issue.severity == "MEDIUM"


def test_detect_assert_in_production() -> None:
    """Test detection of assert statements."""
    code = """
def validate(value):
    assert value > 0
    return value
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R004")
    issue = get_issue(issues, "R004")
    assert issue is not None
    assert issue.severity == "HIGH"


def test_detect_global_misuse() -> None:
    """Test detection of global keyword usage."""
    code = """
counter = 0

def increment():
    global counter
    counter += 1
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R005")


def test_detect_mutable_class_variable() -> None:
    """Test detection of mutable class variables."""
    code = """
class MyClass:
    shared_list = []

    def add_item(self, item):
        self.shared_list.append(item)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R006")


def test_detect_shadowing_builtins() -> None:
    """Test detection of shadowing builtin names."""
    code = """
def process(list, dict, id):
    return list + dict + id
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R008")


def test_detect_eq_without_hash() -> None:
    """Test detection of __eq__ without __hash__."""
    code = """
class Person:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R009")


# ==================== Performance Antipattern Tests ====================


def test_detect_string_concatenation_in_loop() -> None:
    """Test detection of string concatenation in loops."""
    code = """
result = ""
for item in items:
    result += str(item)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "P001")


# ==================== Complexity Antipattern Tests ====================


def test_detect_too_many_parameters() -> None:
    """Test detection of functions with too many parameters."""
    code = """
def complex_function(a, b, c, d, e, f, g, h):
    return a + b + c + d + e + f + g + h
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "C004")


def test_detect_high_cyclomatic_complexity() -> None:
    """Test detection of high cyclomatic complexity."""
    code = """
def complex_logic(x):
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                if x % 3 == 0:
                    if x % 5 == 0:
                        if x % 7 == 0:
                            if x > 1:
                                if x < 9:
                                    if x != 6:
                                        if x != 4:
                                            if x != 8:
                                                if x == 2:
                                                    if x > 0:
                                                        if x < 3:
                                                            if x == 2:
                                                                return True
    return False
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "C003")


def test_detect_long_function() -> None:
    """Test detection of overly long functions."""
    code = "def long_function():\n" + "    pass\n" * 60
    issues = detect_antipatterns(code)
    assert has_issue(issues, "C010")


def test_detect_unnecessary_else_after_return() -> None:
    """Test detection of else after return."""
    code = """
def check_value(x):
    if x > 0:
        return True
    else:
        return False
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "C005")


# ==================== Security Antipattern Tests ====================


def test_detect_sql_injection() -> None:
    """Test detection of SQL injection with f-string."""
    code = """
user_id = request.GET['id']
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S001")
    issue = get_issue(issues, "S001")
    assert issue is not None
    assert issue.severity == "CRITICAL"


def test_detect_command_injection() -> None:
    """Test detection of command injection with shell=True."""
    code = """
import subprocess
user_input = input("Enter filename: ")
subprocess.run(f"cat {user_input}", shell=True)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S002")
    issue = get_issue(issues, "S002")
    assert issue is not None
    assert issue.severity == "CRITICAL"


def test_detect_hardcoded_password() -> None:
    """Test detection of hardcoded passwords."""
    code = """
PASSWORD = "super_secret_password"
API_KEY = "sk_live_abc123xyz789"
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S003")


def test_no_issue_with_placeholder_password() -> None:
    """Test that placeholder passwords don't trigger warning."""
    code = """
PASSWORD = "TODO"
API_KEY = "your-key-here"
"""
    issues = detect_antipatterns(code)
    assert not has_issue(issues, "S003")


def test_detect_weak_cryptography() -> None:
    """Test detection of weak cryptographic functions."""
    code = """
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S004")


def test_detect_unsafe_deserialization() -> None:
    """Test detection of unsafe pickle.load."""
    code = """
import pickle
with open('data.pkl', 'rb') as f:
    data = pickle.load(f)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S005")


def test_detect_weak_random_for_security() -> None:
    """Test detection of random module for security."""
    code = """
import random
token = random.randint(1000, 9999)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "S007")


# ==================== Code Organization Tests ====================


def test_detect_wildcard_import() -> None:
    """Test detection of wildcard imports."""
    code = """
from os import *
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "O003")
    issue = get_issue(issues, "O003")
    assert issue is not None
    assert issue.severity == "HIGH"


# ==================== Python Gotchas Tests ====================


def test_detect_is_with_literal() -> None:
    """Test detection of 'is' with literal values."""
    code = """
x = 5
if x is 5:
    print("yes")
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G001")


def test_allow_is_none() -> None:
    """Test that 'is None' is allowed."""
    code = """
x = None
if x is None:
    print("none")
"""
    issues = detect_antipatterns(code)
    assert not has_issue(issues, "G001")


def test_detect_equality_with_none() -> None:
    """Test detection of == with None."""
    code = """
if value == None:
    print("none")
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G002")


def test_detect_equality_with_bool() -> None:
    """Test detection of comparison with True/False."""
    code = """
if flag == True:
    do_something()
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G006")


def test_detect_type_checking_with_type() -> None:
    """Test detection of type() for type checking."""
    code = """
if type(x) == int:
    process(x)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G003")


def test_detect_modifying_list_while_iterating() -> None:
    """Test detection of modifying list during iteration."""
    code = """
items = [1, 2, 3]
for item in items:
    items.remove(item)
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G004")


def test_detect_silent_exception_swallowing() -> None:
    """Test detection of empty except with pass."""
    code = """
try:
    risky_operation()
except Exception:
    pass
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "G005")


# ==================== Context Manager Tests ====================


def test_detect_context_manager_not_returning_self() -> None:
    """Test detection of __enter__ not returning self."""
    code = """
class MyContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "M003")


# ==================== Configuration Tests ====================


def test_config_disabled_patterns() -> None:
    """Test that disabled patterns are not reported."""
    config = Config()
    config.disabled_patterns = {"R001", "P001"}

    code = """
def process(items=[]):
    result = ""
    for item in items:
        result += item
    return result
"""
    issues = detect_antipatterns(code, config)
    assert not has_issue(issues, "R001")
    assert not has_issue(issues, "P001")


def test_config_severity_filtering() -> None:
    """Test that severity level filtering works."""
    config = Config()
    config.levels = {"CRITICAL", "HIGH"}

    code = """
def process(items=[]):  # HIGH
    if value == None:  # MEDIUM
        pass
"""
    issues = detect_antipatterns(code, config)
    filtered = filter_issues(issues, config)

    # Should have R001 (HIGH) but not G002 (MEDIUM)
    assert any(issue.id == "R001" for issue in filtered)
    assert not any(issue.id == "G002" for issue in filtered)


def test_config_max_issues() -> None:
    """Test that max issues limit works."""
    config = Config()
    config.max_issues = 2

    code = """
def bad_function(list, dict, id, a, b, c, d, e):  # Multiple issues
    global x
    assert True
    x = 5
    if x is 5:
        pass
"""
    issues = detect_antipatterns(code, config)
    filtered = filter_issues(issues, config)

    assert len(filtered) <= 2


# ==================== Integration Tests ====================


def test_format_issue_report_single_issue() -> None:
    """Test formatting of single issue report."""
    issues = [
        Issue(
            id="R001",
            severity="HIGH",
            line=1,
            column=0,
            message="Mutable default argument",
            suggestion="Use None and create inside function",
            code_snippet="def process(items=[]):",
        )
    ]

    report = format_issue_report(issues, "/path/to/file.py")

    assert "⚠️" in report
    assert "R001:HIGH" in report
    assert "Mutable default argument" in report
    assert "file.py" in report


def test_format_issue_report_multiple_issues() -> None:
    """Test formatting of multiple issues with different severities."""
    issues = [
        Issue(
            id="S001",
            severity="CRITICAL",
            line=5,
            column=0,
            message="SQL injection",
            suggestion="Use parameterized queries",
            code_snippet="cursor.execute(f'...')",
        ),
        Issue(
            id="R001",
            severity="HIGH",
            line=10,
            column=0,
            message="Mutable default",
            suggestion="Use None",
            code_snippet="def foo(x=[]):",
        ),
        Issue(
            id="G002",
            severity="MEDIUM",
            line=15,
            column=0,
            message="Equality with None",
            suggestion="Use 'is None'",
            code_snippet="if x == None:",
        ),
    ]

    report = format_issue_report(issues, "/path/to/file.py")

    assert "3 issues found" in report
    assert "1 CRITICAL" in report
    assert "1 HIGH" in report
    assert "1 MEDIUM" in report


def test_format_issue_report_empty() -> None:
    """Test formatting of empty issue list."""
    issues: list[Issue] = []
    report = format_issue_report(issues, "/path/to/file.py")
    assert report == ""


# ==================== Async Function Tests ====================


def test_detect_async_function_issues() -> None:
    """Test that async functions are analyzed properly."""
    code = """
async def process(items=[]):
    result = ""
    async for item in items:
        result += item
    return result
"""
    issues = detect_antipatterns(code)
    assert has_issue(issues, "R001")  # Mutable default
    assert has_issue(issues, "P001")  # String concatenation


# ==================== Edge Cases ====================


def test_empty_file() -> None:
    """Test that empty files don't cause errors."""
    code = ""
    issues = detect_antipatterns(code)
    assert len(issues) == 0


def test_syntax_error_file() -> None:
    """Test that syntax errors are handled gracefully."""
    code = "def broken(\n    # Missing closing paren"
    issues = detect_antipatterns(code)
    assert len(issues) == 0


def test_very_simple_file() -> None:
    """Test that simple valid code produces no issues."""
    code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
    issues = detect_antipatterns(code)
    # May have some low-priority issues but should be mostly clean
    assert len(issues) <= 1


# ==================== Run Tests ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
