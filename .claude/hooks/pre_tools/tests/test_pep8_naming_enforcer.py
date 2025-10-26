#!/usr/bin/env python3
"""
Unit Tests for PEP 8 Naming Enforcer Hook
==========================================

Test suite for validating PEP 8 naming conventions.

Usage:
    uv run pytest .claude/hooks/pre_tools/tests/test_pep8_naming_enforcer.py -v
"""

import pytest


# ==================== Class Name Validation Tests ====================

class TestClassNameValidation:
    """Test class name validation against PEP 8 PascalCase rules."""

    def test_valid_simple_class_name(self):
        """Test that simple PascalCase class names are valid."""
        from ..pep8_naming_enforcer import validate_class_name

        assert validate_class_name("MyClass", 1) is None

    def test_invalid_lowercase_class_name(self):
        """Test that lowercase class names are invalid."""
        from ..pep8_naming_enforcer import validate_class_name

        result = validate_class_name("myclass", 1)
        assert result is not None
        assert "myclass" in result
        assert "PascalCase" in result

    def test_valid_magic_class_name(self):
        """Test that magic class names are valid."""
        from ..pep8_naming_enforcer import validate_class_name

        assert validate_class_name("__MagicClass__", 1) is None


# ==================== Function Name Validation Tests ====================

class TestFunctionNameValidation:
    """Test function name validation against PEP 8 snake_case rules."""

    def test_valid_snake_case_function_name(self):
        """Test that snake_case function names are valid."""
        from ..pep8_naming_enforcer import validate_function_name

        assert validate_function_name("my_function", 1) is None

    def test_invalid_camelcase_function_name(self):
        """Test that camelCase function names are invalid."""
        from ..pep8_naming_enforcer import validate_function_name

        result = validate_function_name("myFunction", 1)
        assert result is not None
        assert "myFunction" in result
        assert "snake_case" in result

    def test_valid_magic_method_names(self):
        """Test that magic method names are valid."""
        from ..pep8_naming_enforcer import validate_function_name

        assert validate_function_name("__init__", 1) is None
        assert validate_function_name("__str__", 1) is None


# ==================== Variable Name Validation Tests ====================

class TestVariableNameValidation:
    """Test variable name validation against PEP 8 snake_case rules."""

    def test_valid_snake_case_variable_name(self):
        """Test that snake_case variable names are valid."""
        from ..pep8_naming_enforcer import validate_variable_name

        assert validate_variable_name("my_variable", 1) is None

    def test_invalid_camelcase_variable_name(self):
        """Test that camelCase variable names are invalid."""
        from ..pep8_naming_enforcer import validate_variable_name

        result = validate_variable_name("myVariable", 1)
        assert result is not None
        assert "myVariable" in result
        assert "snake_case" in result


# ==================== Constant Name Validation Tests ====================

class TestConstantNameValidation:
    """Test constant name validation against PEP 8 UPPER_CASE rules."""

    def test_valid_upper_case_constant_name(self):
        """Test that UPPER_CASE constant names are valid."""
        from ..pep8_naming_enforcer import validate_constant_name

        assert validate_constant_name("MAX_SIZE", 1) is None

    def test_invalid_lowercase_constant_name(self):
        """Test that lowercase constant names are invalid."""
        from ..pep8_naming_enforcer import validate_constant_name

        result = validate_constant_name("max_size", 1)
        assert result is not None
        assert "max_size" in result
        assert "UPPER_CASE" in result


# ==================== Forbidden Pattern Tests ====================

class TestForbiddenPatterns:
    """Test detection of forbidden naming patterns."""

    def test_builtin_shadowing_detected(self):
        """Test that shadowing Python builtins is detected."""
        from ..pep8_naming_enforcer import check_forbidden_patterns

        result = check_forbidden_patterns("list", 1)
        assert result is not None
        assert "list" in result
        assert "builtin" in result.lower()


# ==================== File Type Detection Tests ====================

class TestFileTypeDetection:
    """Test file type detection functions."""

    def test_python_file_detected(self):
        """Test that .py files are detected as Python files."""
        from ..pep8_naming_enforcer import is_python_file

        assert is_python_file("/path/to/file.py") is True
        assert is_python_file("/path/to/file.txt") is False


# ==================== Code Validation Integration Tests ====================

class TestCodeValidation:
    """Test full code validation with AST analysis."""

    def test_valid_code_passes(self):
        """Test that PEP 8 compliant code passes validation."""
        from ..pep8_naming_enforcer import validate_python_code

        code = """
class MyClass:
    def my_method(self):
        my_variable = 10
        return my_variable
"""
        result = validate_python_code(code, "test.py")
        assert result is None

    def test_invalid_code_detected(self):
        """Test that PEP 8 violations are detected in code."""
        from ..pep8_naming_enforcer import validate_python_code

        code = """
class myClass:
    def MyMethod(self):
        pass
"""
        result = validate_python_code(code, "test.py")
        assert result is not None
        assert "myClass" in result
        assert "MyMethod" in result

    def test_detects_violations_in_different_code(self):
        """Test that different violations are detected (requires real AST)."""
        from ..pep8_naming_enforcer import validate_python_code

        code = """
class GoodClass:
    def badMethod(self):
        BadVariable = 10
"""
        result = validate_python_code(code, "test.py")
        assert result is not None
        assert "badMethod" in result
        assert "BadVariable" in result

    def test_does_not_detect_in_strings(self):
        """Test that violations in strings are not flagged (requires AST)."""
        from ..pep8_naming_enforcer import validate_python_code

        code = '''
class MyClass:
    def my_method(self):
        text = "This mentions badMethod but it's in a string"
        return text
'''
        result = validate_python_code(code, "test.py")
        # Should be None because badMethod is only in a string, not actual code
        assert result is None


# ==================== Main Hook Entry Point Tests ====================

class TestMainHook:
    """Test main() hook entry point and integration."""

    def test_main_allows_non_python_files(self):
        """Test that main() allows non-Python files without validation."""
        import json
        from io import StringIO
        from unittest.mock import patch
        from ..pep8_naming_enforcer import main

        hook_input = json.dumps({
            "session_id": "test123",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/file.txt",
                "content": "class myClass: pass"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.exit') as mock_exit:
                    main()
                    output = json.loads(mock_stdout.getvalue())
                    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_main_denies_violations_in_python_files(self):
        """Test that main() denies Python files with PEP 8 violations."""
        import json
        from io import StringIO
        from unittest.mock import patch
        from ..pep8_naming_enforcer import main

        hook_input = json.dumps({
            "session_id": "test123",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/file.py",
                "content": "class badClass:\n    def BadMethod(self): pass"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.exit') as mock_exit:
                    main()
                    output = json.loads(mock_stdout.getvalue())
                    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
                    assert "badClass" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_main_allows_valid_python_code(self):
        """Test that main() allows Python files with valid PEP 8 naming."""
        import json
        from io import StringIO
        from unittest.mock import patch
        from ..pep8_naming_enforcer import main

        hook_input = json.dumps({
            "session_id": "test123",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/file.py",
                "content": "class MyClass:\n    def my_method(self):\n        my_var = 10"
            }
        })

        with patch('sys.stdin', StringIO(hook_input)):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.exit') as mock_exit:
                    main()
                    output = json.loads(mock_stdout.getvalue())
                    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
