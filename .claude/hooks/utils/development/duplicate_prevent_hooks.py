#!/usr/bin/env python3
"""
Enhanced Claude Code Hook for Preventing Code Duplication
Monitors all file modifications and suggests reusing existing functionality
"""

import json
import sys
import os
import subprocess
import ast
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import difflib
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/claude_hook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DuplicationAnalysis:
    """Results from duplication analysis"""
    is_duplicate: bool
    similar_files: List[str]
    suggestions: List[str]
    confidence: float
    analysis_type: str  # 'query', 'function', 'class', 'file'

class CodeDuplicationDetector:
    """Detects potential code duplication across the project"""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.cache_dir = self.project_dir / '.claude' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.function_index = self._build_function_index()
        
    def _build_function_index(self) -> Dict[str, List[Tuple[str, str]]]:
        """Build an index of all functions and classes in the project"""
        index = {
            'functions': [],
            'classes': [],
            'queries': [],
            'imports': []
        }
        
        # Define directories to scan
        scan_dirs = ['src', 'lib', 'app', 'queries', 'components', 'utils', 'services']
        
        for dir_name in scan_dirs:
            dir_path = self.project_dir / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob('*.py'):
                    if '__pycache__' in str(file_path):
                        continue
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            tree = ast.parse(content)
                            
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    # Extract function signature and docstring
                                    func_sig = self._get_function_signature(node)
                                    index['functions'].append((str(file_path), func_sig))
                                    
                                    # Check if it's a query function
                                    if 'query' in node.name.lower() or 'get_' in node.name or 'fetch_' in node.name:
                                        index['queries'].append((str(file_path), func_sig))
                                        
                                elif isinstance(node, ast.ClassDef):
                                    class_sig = f"class {node.name}"
                                    index['classes'].append((str(file_path), class_sig))
                                    
                                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                                    import_stmt = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                                    index['imports'].append((str(file_path), import_stmt))
                                    
                    except Exception as e:
                        logger.warning(f"Failed to parse {file_path}: {e}")
                        
        return index
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature with parameters"""
        args = []
        if node.args.args:
            args = [arg.arg for arg in node.args.args]
        return f"def {node.name}({', '.join(args)})"
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two code snippets"""
        # Remove whitespace and comments for comparison
        content1_clean = re.sub(r'#.*?\n', '', content1).strip()
        content2_clean = re.sub(r'#.*?\n', '', content2).strip()
        
        # Use difflib to calculate similarity
        seq_matcher = difflib.SequenceMatcher(None, content1_clean, content2_clean)
        return seq_matcher.ratio()
    
    def check_for_duplicates(self, file_path: str, new_content: str) -> DuplicationAnalysis:
        """Check if the new content duplicates existing functionality"""
        
        # Parse the new content
        try:
            tree = ast.parse(new_content)
        except SyntaxError:
            # If not Python, do basic text analysis
            return self._check_non_python_duplicates(file_path, new_content)
        
        # Extract functions and classes from new content
        new_functions = []
        new_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                new_functions.append(self._get_function_signature(node))
            elif isinstance(node, ast.ClassDef):
                new_classes.append(f"class {node.name}")
        
        # Check for similar functions
        similar_files = set()
        suggestions = []
        
        for new_func in new_functions:
            func_name = new_func.split('(')[0].replace('def ', '')
            
            # Check exact matches
            for existing_file, existing_func in self.function_index['functions']:
                existing_name = existing_func.split('(')[0].replace('def ', '')
                
                # Check for exact name matches
                if func_name == existing_name and existing_file != file_path:
                    similar_files.add(existing_file)
                    suggestions.append(f"Function '{func_name}' already exists in {existing_file}")
                
                # Check for similar names (edit distance)
                elif self._is_similar_name(func_name, existing_name) and existing_file != file_path:
                    similar_files.add(existing_file)
                    suggestions.append(f"Similar function '{existing_name}' found in {existing_file}")
        
        # Check if this is creating a versioned file
        if self._is_versioned_file(file_path):
            original_file = self._get_original_file(file_path)
            if original_file and original_file.exists():
                suggestions.append(f"This appears to be creating a version of {original_file}. Consider updating the original file instead.")
                return DuplicationAnalysis(
                    is_duplicate=True,
                    similar_files=[str(original_file)],
                    suggestions=suggestions,
                    confidence=0.95,
                    analysis_type='file'
                )
        
        # Determine if this is a duplicate
        is_duplicate = len(suggestions) > 0
        confidence = min(1.0, len(suggestions) * 0.3) if suggestions else 0.0
        
        return DuplicationAnalysis(
            is_duplicate=is_duplicate,
            similar_files=list(similar_files),
            suggestions=suggestions,
            confidence=confidence,
            analysis_type='function'
        )
    
    def _check_non_python_duplicates(self, file_path: str, content: str) -> DuplicationAnalysis:
        """Check for duplicates in non-Python files"""
        suggestions = []
        similar_files = []
        
        # Check for SQL queries
        if '.sql' in file_path or 'query' in file_path.lower():
            sql_patterns = re.findall(r'(SELECT|INSERT|UPDATE|DELETE).*?(?:;|\Z)', content, re.IGNORECASE | re.DOTALL)
            
            for pattern in sql_patterns:
                # Search for similar queries in existing files
                query_files = self.project_dir.rglob('*.sql')
                for qf in query_files:
                    if str(qf) != file_path:
                        try:
                            with open(qf, 'r') as f:
                                existing_content = f.read()
                                similarity = self._calculate_similarity(pattern, existing_content)
                                if similarity > 0.7:
                                    similar_files.append(str(qf))
                                    suggestions.append(f"Similar query found in {qf}")
                        except:
                            pass
        
        return DuplicationAnalysis(
            is_duplicate=len(suggestions) > 0,
            similar_files=similar_files,
            suggestions=suggestions,
            confidence=0.5 if suggestions else 0.0,
            analysis_type='query'
        )
    
    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """Check if two function names are similar"""
        # Convert to lowercase and remove common prefixes
        name1 = name1.lower().replace('get_', '').replace('fetch_', '').replace('create_', '')
        name2 = name2.lower().replace('get_', '').replace('fetch_', '').replace('create_', '')
        
        # Check Levenshtein distance
        return difflib.SequenceMatcher(None, name1, name2).ratio() > 0.8
    
    def _is_versioned_file(self, file_path: str) -> bool:
        """Check if this is a versioned file (e.g., file_v2.py, file_copy.py)"""
        patterns = [
            r'_v\d+\.',  # _v1, _v2, etc.
            r'_copy\.',  # _copy
            r'_backup\.',  # _backup
            r'_old\.',  # _old
            r'_new\.',  # _new
            r'\(\d+\)\.',  # (1), (2), etc.
        ]
        
        for pattern in patterns:
            if re.search(pattern, file_path):
                return True
        return False
    
    def _get_original_file(self, versioned_path: str) -> Optional[Path]:
        """Get the original file from a versioned file path"""
        # Remove version indicators
        original = versioned_path
        original = re.sub(r'_v\d+\.', '.', original)
        original = re.sub(r'_copy\.', '.', original)
        original = re.sub(r'_backup\.', '.', original)
        original = re.sub(r'_old\.', '.', original)
        original = re.sub(r'_new\.', '.', original)
        original = re.sub(r'\(\d+\)\.', '.', original)
        
        return Path(original) if original != versioned_path else None

class ClaudeCodeReviewer:
    """Launches a separate Claude instance to review changes"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
    
    def review_changes(self, file_path: str, new_content: str, analysis: DuplicationAnalysis) -> str:
        """Use Claude API to review the changes and provide detailed feedback"""
        
        prompt = f"""You are reviewing a proposed change to a file in a development project.
Your task is to analyze if the new or modified functionality could be accomplished by reusing or modifying existing code.

File: {file_path}

Duplication Analysis:
- Potential duplicate: {analysis.is_duplicate}
- Similar files: {', '.join(analysis.similar_files) if analysis.similar_files else 'None'}
- Initial suggestions: {json.dumps(analysis.suggestions, indent=2)}

New content:
<new_content>
{new_content[:3000]}  # Truncate for API limits
</new_content>

Please provide specific, actionable feedback on:
1. Whether this duplicates existing functionality
2. Which existing functions/files could be reused instead
3. If modification is needed, what specific changes to suggest

Be concise and specific. If no duplication is found, just say "Changes look appropriate."
"""
        
        # Here you would call the Claude API
        # For now, we'll return a formatted response based on the analysis
        
        if not analysis.is_duplicate:
            return "Changes look appropriate."
        
        feedback = "### Code Duplication Detected\n\n"
        feedback += f"**Confidence:** {analysis.confidence * 100:.1f}%\n\n"
        
        if analysis.suggestions:
            feedback += "**Issues found:**\n"
            for suggestion in analysis.suggestions:
                feedback += f"- {suggestion}\n"
        
        if analysis.similar_files:
            feedback += f"\n**Consider reusing code from:**\n"
            for file in analysis.similar_files:
                feedback += f"- `{file}`\n"
        
        feedback += "\n**Recommendation:** Review the existing implementations and consider:\n"
        feedback += "1. Importing and using the existing function\n"
        feedback += "2. Extending the existing functionality with additional parameters\n"
        feedback += "3. Creating a shared utility if the logic needs to be slightly different\n"
        
        return feedback

def main():
    """Main hook entry point"""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data:
            logger.error("No input data received")
            sys.exit(0)
        
        # Parse the hook data
        hook_data = json.loads(input_data)
        tool_input = hook_data.get('tool_input', {})
        
        # Extract file path and content
        file_path = tool_input.get('file_path') or tool_input.get('path')
        new_content = tool_input.get('content') or tool_input.get('contents', '')
        
        if not file_path:
            logger.info("No file path found in tool input")
            sys.exit(0)
        
        # Get project directory
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # Initialize the duplication detector
        detector = CodeDuplicationDetector(project_dir)
        
        # Check for duplicates
        logger.info(f"Analyzing file: {file_path}")
        analysis = detector.check_for_duplicates(file_path, new_content)
        
        # If no duplicates found, allow the operation
        if not analysis.is_duplicate:
            logger.info(f"No duplication detected for {file_path}")
            sys.exit(0)
        
        # If duplicates found with high confidence, get detailed review
        if analysis.confidence > 0.6:
            reviewer = ClaudeCodeReviewer()
            detailed_feedback = reviewer.review_changes(file_path, new_content, analysis)
            
            # Output feedback to stderr (will be shown to Claude)
            print(detailed_feedback, file=sys.stderr)
            
            # Block the operation
            sys.exit(2)
        
        # For low confidence, just warn
        if analysis.suggestions:
            warning = f"⚠️ Potential duplication detected (confidence: {analysis.confidence * 100:.1f}%)\n"
            warning += "\n".join(analysis.suggestions)
            print(warning, file=sys.stderr)
        
        # Allow the operation but with warning
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Hook error: {e}", exc_info=True)
        # Don't block on errors
        sys.exit(0)

if __name__ == "__main__":
    main()
