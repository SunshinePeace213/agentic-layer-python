#!/usr/bin/env python3
"""
Code Index Updater Hook
Updates the code index after successful file modifications
Runs in background to not block Claude's workflow
"""

import json
import sys
import os
import ast
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib
from typing import Dict, List, Optional
import threading
import time

class CodeIndexer:
    """Maintains an SQLite database of code structure for fast duplicate detection"""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.db_path = self.project_dir / '.claude' / 'code_index.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                function_name TEXT NOT NULL,
                signature TEXT NOT NULL,
                docstring TEXT,
                line_start INTEGER,
                line_end INTEGER,
                hash TEXT UNIQUE,
                last_modified TIMESTAMP,
                complexity INTEGER,
                imports TEXT,
                calls_functions TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                class_name TEXT NOT NULL,
                bases TEXT,
                docstring TEXT,
                line_start INTEGER,
                line_end INTEGER,
                hash TEXT UNIQUE,
                last_modified TIMESTAMP,
                methods TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                query_name TEXT NOT NULL,
                query_type TEXT,
                tables_used TEXT,
                query_text TEXT,
                hash TEXT UNIQUE,
                last_modified TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                last_indexed TIMESTAMP,
                file_type TEXT,
                size INTEGER,
                imports TEXT,
                exports TEXT
            )
        """)
        
        # Create indexes for faster searching
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_func_name ON functions(function_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_class_name ON classes(class_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON files(file_path)")
        
        conn.commit()
        conn.close()
    
    def update_file_index(self, file_path: str, content: str):
        """Update the index for a specific file"""
        file_path = Path(file_path)
        
        # Determine file type and process accordingly
        if file_path.suffix == '.py':
            self._index_python_file(file_path, content)
        elif file_path.suffix in ['.sql', '.query']:
            self._index_sql_file(file_path, content)
        elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            self._index_javascript_file(file_path, content)
        else:
            self._index_generic_file(file_path, content)
    
    def _index_python_file(self, file_path: Path, content: str):
        """Index a Python file"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Clear existing entries for this file
        cursor.execute("DELETE FROM functions WHERE file_path = ?", (str(file_path),))
        cursor.execute("DELETE FROM classes WHERE file_path = ?", (str(file_path),))
        
        # Index functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._index_function(cursor, file_path, node, content)
            elif isinstance(node, ast.ClassDef):
                self._index_class(cursor, file_path, node, content)
        
        # Update file record
        file_hash = hashlib.md5(content.encode()).hexdigest()
        imports = self._extract_imports(tree)
        
        cursor.execute("""
            INSERT OR REPLACE INTO files (file_path, file_hash, last_indexed, file_type, size, imports)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(file_path), file_hash, datetime.now(), 'python', len(content), json.dumps(imports)))
        
        conn.commit()
        conn.close()
    
    def _index_function(self, cursor, file_path: Path, node: ast.FunctionDef, content: str):
        """Index a function node"""
        # Extract function signature
        args = []
        if node.args.args:
            args = [arg.arg for arg in node.args.args]
        signature = f"def {node.name}({', '.join(args)})"
        
        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        
        # Calculate complexity (simplified McCabe complexity)
        complexity = self._calculate_complexity(node)
        
        # Extract function calls
        calls = self._extract_function_calls(node)
        
        # Generate unique hash
        func_hash = hashlib.md5(f"{file_path}:{node.name}:{signature}".encode()).hexdigest()
        
        cursor.execute("""
            INSERT OR REPLACE INTO functions 
            (file_path, function_name, signature, docstring, line_start, line_end, hash, last_modified, complexity, calls_functions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(file_path), node.name, signature, docstring,
            node.lineno, node.end_lineno, func_hash, datetime.now(),
            complexity, json.dumps(calls)
        ))
    
    def _index_class(self, cursor, file_path: Path, node: ast.ClassDef, content: str):
        """Index a class node"""
        # Extract base classes
        bases = [ast.unparse(base) if hasattr(ast, 'unparse') else str(base) for base in node.bases]
        
        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        
        # Extract methods
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        
        # Generate unique hash
        class_hash = hashlib.md5(f"{file_path}:{node.name}".encode()).hexdigest()
        
        cursor.execute("""
            INSERT OR REPLACE INTO classes
            (file_path, class_name, bases, docstring, line_start, line_end, hash, last_modified, methods)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(file_path), node.name, json.dumps(bases), docstring,
            node.lineno, node.end_lineno, class_hash, datetime.now(),
            json.dumps(methods)
        ))
    
    def _index_sql_file(self, file_path: Path, content: str):
        """Index SQL queries from a file"""
        import re
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Clear existing entries
        cursor.execute("DELETE FROM queries WHERE file_path = ?", (str(file_path),))
        
        # Simple regex patterns for SQL queries
        patterns = {
            'SELECT': r'SELECT\s+.*?\s+FROM\s+(\w+)',
            'INSERT': r'INSERT\s+INTO\s+(\w+)',
            'UPDATE': r'UPDATE\s+(\w+)',
            'DELETE': r'DELETE\s+FROM\s+(\w+)'
        }
        
        # Find all queries
        for query_type, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for i, match in enumerate(matches):
                table_name = match.group(1)
                query_name = f"{query_type.lower()}_{table_name}_{i}"
                query_text = match.group(0)[:500]  # Truncate long queries
                
                query_hash = hashlib.md5(f"{file_path}:{query_name}".encode()).hexdigest()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO queries
                    (file_path, query_name, query_type, tables_used, query_text, hash, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(file_path), query_name, query_type, table_name,
                    query_text, query_hash, datetime.now()
                ))
        
        conn.commit()
        conn.close()
    
    def _index_javascript_file(self, file_path: Path, content: str):
        """Index JavaScript/TypeScript files (simplified)"""
        import re
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Extract function declarations and arrow functions
        func_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=])\s*=>)'
        matches = re.finditer(func_pattern, content)
        
        for match in matches:
            func_name = match.group(1) or match.group(2)
            if func_name:
                func_hash = hashlib.md5(f"{file_path}:{func_name}".encode()).hexdigest()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO functions
                    (file_path, function_name, signature, docstring, line_start, line_end, hash, last_modified, complexity, calls_functions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(file_path), func_name, f"function {func_name}()", "",
                    0, 0, func_hash, datetime.now(), 0, "[]"
                ))
        
        # Update file record
        file_hash = hashlib.md5(content.encode()).hexdigest()
        cursor.execute("""
            INSERT OR REPLACE INTO files (file_path, file_hash, last_indexed, file_type, size)
            VALUES (?, ?, ?, ?, ?)
        """, (str(file_path), file_hash, datetime.now(), 'javascript', len(content)))
        
        conn.commit()
        conn.close()
    
    def _index_generic_file(self, file_path: Path, content: str):
        """Index a generic file (just track its existence and hash)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        file_hash = hashlib.md5(content.encode()).hexdigest()
        
        cursor.execute("""
            INSERT OR REPLACE INTO files (file_path, file_hash, last_indexed, file_type, size)
            VALUES (?, ?, ?, ?, ?)
        """, (str(file_path), file_hash, datetime.now(), file_path.suffix[1:], len(content)))
        
        conn.commit()
        conn.close()
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate simplified McCabe complexity"""
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity
    
    def _extract_function_calls(self, node: ast.FunctionDef) -> List[str]:
        """Extract function calls from a function"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))
    
    def _extract_imports(self, tree: ast.Module) -> List[str]:
        """Extract all imports from a module"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

def index_in_background(file_path: str, content: str, project_dir: str):
    """Run indexing in background thread"""
    def _index():
        try:
            indexer = CodeIndexer(project_dir)
            indexer.update_file_index(file_path, content)
        except Exception as e:
            # Log error to file
            log_path = Path(project_dir) / '.claude' / 'index_errors.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(f"{datetime.now()}: Error indexing {file_path}: {e}\n")
    
    # Start background thread
    thread = threading.Thread(target=_index, daemon=True)
    thread.start()

def main():
    """Main hook entry point"""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)
        
        # Parse the hook data
        hook_data = json.loads(input_data)
        tool_input = hook_data.get('tool_input', {})
        tool_name = hook_data.get('tool_name', '')
        
        # Only process successful edits/writes
        if tool_name not in ['Edit', 'MultiEdit', 'Write']:
            sys.exit(0)
        
        # Extract file path and content
        file_path = tool_input.get('file_path') or tool_input.get('path')
        content = tool_input.get('content') or tool_input.get('contents', '')
        
        if not file_path or not content:
            sys.exit(0)
        
        # Get project directory
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # Index in background to not block Claude
        index_in_background(file_path, content, project_dir)
        
        # Always exit successfully for PostToolUse
        sys.exit(0)
        
    except Exception:
        # Never block on errors in PostToolUse
        sys.exit(0)

if __name__ == "__main__":
    main()