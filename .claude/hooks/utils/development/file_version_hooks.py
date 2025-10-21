#!/usr/bin/env python3
"""
File Version Prevention Hook
Prevents creating versioned files and suggests updating the original instead
"""

import json
import sys
import os
import re
from pathlib import Path
import difflib
from typing import Optional, Tuple, List

class FileVersionChecker:
    """Check and prevent file versioning"""
    
    VERSION_PATTERNS = [
        (r'(.+)_v\d+(\.\w+)$', r'\1\2'),  # file_v1.py -> file.py
        (r'(.+)_copy(\.\w+)$', r'\1\2'),  # file_copy.py -> file.py
        (r'(.+)_backup(\.\w+)$', r'\1\2'),  # file_backup.py -> file.py
        (r'(.+)_old(\.\w+)$', r'\1\2'),  # file_old.py -> file.py
        (r'(.+)_new(\.\w+)$', r'\1\2'),  # file_new.py -> file.py
        (r'(.+)\s+\(\d+\)(\.\w+)$', r'\1\2'),  # file (1).py -> file.py
        (r'(.+)_\d{8}(\.\w+)$', r'\1\2'),  # file_20240101.py -> file.py
        (r'(.+)\.bak$', r'\1'),  # file.py.bak -> file.py
        (r'(.+)~$', r'\1'),  # file.py~ -> file.py
    ]
    
    IGNORE_PATTERNS = [
        r'test_.*',  # Test files can have versions
        r'.*_test\..*',  # Test files
        r'.*\.test\..*',  # Test files
        r'migration_.*',  # Migration files often need versions
        r'v\d+_.*',  # Files that start with version (e.g., v1_schema.sql)
    ]
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
    
    def is_versioned_file(self, file_path: str) -> Tuple[bool, Optional[Path]]:
        """
        Check if this is a versioned file and return the original if it exists
        
        Returns:
            (is_versioned, original_file_path)
        """
        file_path = Path(file_path)
        file_name = file_path.name
        
        # Check if this should be ignored
        for ignore_pattern in self.IGNORE_PATTERNS:
            if re.match(ignore_pattern, file_name):
                return (False, None)
        
        # Check each version pattern
        for pattern, replacement in self.VERSION_PATTERNS:
            match = re.match(pattern, file_name)
            if match:
                # Get the original filename
                original_name = re.sub(pattern, replacement, file_name)
                original_path = file_path.parent / original_name
                
                # Check if the original file exists
                if original_path.exists():
                    return (True, original_path)
                
                # Even if original doesn't exist, this is still a versioned filename
                return (True, None)
        
        return (False, None)
    
    def find_similar_files(self, file_path: str) -> List[Path]:
        """Find files with similar names that might be the 'original'"""
        file_path = Path(file_path)
        file_name = file_path.stem  # Get name without extension
        file_ext = file_path.suffix
        
        similar_files = []
        
        # Clean the filename of common version indicators
        clean_name = file_name
        for pattern in ['_v\\d+', '_copy', '_backup', '_old', '_new', '_\\d{8}', '\\s+\\(\\d+\\)']:
            clean_name = re.sub(pattern, '', clean_name)
        
        # Search in the same directory and parent directory
        search_dirs = [file_path.parent]
        if file_path.parent != self.project_dir:
            search_dirs.append(file_path.parent.parent)
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for existing_file in search_dir.glob(f"*{file_ext}"):
                if existing_file == file_path:
                    continue
                
                # Calculate similarity
                existing_stem = existing_file.stem
                similarity = difflib.SequenceMatcher(None, clean_name, existing_stem).ratio()
                
                if similarity > 0.7:  # 70% similarity threshold
                    similar_files.append(existing_file)
        
        # Sort by similarity
        similar_files.sort(key=lambda f: difflib.SequenceMatcher(None, clean_name, f.stem).ratio(), reverse=True)
        
        return similar_files[:3]  # Return top 3 matches
    
    def suggest_merge_strategy(self, original_file: Path, new_content: str) -> str:
        """Suggest how to merge the new content with the original file"""
        
        suggestions = []
        
        # Check if original file exists and is readable
        if original_file.exists():
            try:
                with open(original_file, 'r') as f:
                    original_content = f.read()
                
                # Calculate the difference
                differ = difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(original_file),
                    tofile='new_version',
                    n=1
                )
                
                diff_lines = list(differ)
                
                # Analyze the differences
                additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
                
                if additions > deletions * 2:
                    suggestions.append("The new version adds significant functionality. Consider:")
                    suggestions.append("- Adding the new functions to the original file")
                    suggestions.append("- Creating a new module if the functionality is distinct")
                elif deletions > additions * 2:
                    suggestions.append("The new version removes functionality. Consider:")
                    suggestions.append("- Refactoring the original file instead")
                    suggestions.append("- Deprecating unused functions properly")
                else:
                    suggestions.append("The new version modifies existing functionality. Consider:")
                    suggestions.append("- Updating the original file directly")
                    suggestions.append("- Using feature flags if both versions are needed")
                
            except Exception as e:
                suggestions.append(f"Could not analyze original file: {e}")
        
        return "\n".join(suggestions) if suggestions else "Consider updating the original file instead of creating a new version."

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
        
        # Get the file path
        file_path = tool_input.get('file_path') or tool_input.get('path')
        if not file_path:
            sys.exit(0)
        
        # Get project directory
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # Initialize the checker
        checker = FileVersionChecker(project_dir)
        
        # Check if this is a versioned file
        is_versioned, original_file = checker.is_versioned_file(file_path)
        
        if is_versioned:
            feedback = "### ⚠️ File Versioning Detected\n\n"
            
            if original_file:
                feedback += f"**You're creating a version of an existing file:**\n"
                feedback += f"- Original: `{original_file}`\n"
                feedback += f"- New version: `{file_path}`\n\n"
                
                # Get merge suggestions
                new_content = tool_input.get('content', '')
                if new_content:
                    merge_strategy = checker.suggest_merge_strategy(original_file, new_content)
                    feedback += f"**Suggested approach:**\n{merge_strategy}\n\n"
                
                feedback += "**Instead of creating a new version:**\n"
                feedback += "1. Update the original file directly using Edit tool\n"
                feedback += "2. Use git branches for experimental changes\n"
                feedback += "3. Use feature flags for multiple implementations\n\n"
                
            else:
                feedback += f"**This appears to be a versioned filename:** `{file_path}`\n\n"
                
                # Find similar files
                similar_files = checker.find_similar_files(file_path)
                if similar_files:
                    feedback += "**Similar existing files found:**\n"
                    for similar in similar_files:
                        feedback += f"- `{similar}`\n"
                    feedback += "\nConsider updating one of these files instead.\n\n"
                
                feedback += "**Best practices:**\n"
                feedback += "- Avoid version suffixes (_v2, _copy, _new)\n"
                feedback += "- Use descriptive names that indicate purpose\n"
                feedback += "- Leverage version control instead of file versions\n"
            
            # Print feedback to stderr
            print(feedback, file=sys.stderr)
            
            # Block the file creation
            sys.exit(2)
        
        # File is not versioned, allow creation
        sys.exit(0)
        
    except Exception as e:
        # Log error but don't block on errors
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
