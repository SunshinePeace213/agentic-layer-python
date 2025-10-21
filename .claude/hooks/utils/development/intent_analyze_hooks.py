#!/usr/bin/env python3
"""
Intent Analyzer Hook
Analyzes user prompts to understand intent and provide context to Claude
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sqlite3

class IntentAnalyzer:
    """Analyzes user intent from prompts to provide better context"""
    
    # Keywords that suggest different intents
    INTENT_PATTERNS = {
        'duplicate_function': [
            r'create\s+(?:a\s+)?(?:new\s+)?function',
            r'add\s+(?:a\s+)?(?:new\s+)?method',
            r'write\s+(?:a\s+)?function\s+(?:that|to)',
            r'implement\s+(?:a\s+)?(?:new\s+)?',
        ],
        'create_version': [
            r'make\s+(?:a\s+)?copy',
            r'create\s+(?:a\s+)?version',
            r'duplicate\s+(?:the\s+)?file',
            r'save\s+as\s+new',
            r'create\s+.*?_v\d+',
        ],
        'refactor': [
            r'refactor',
            r'clean\s+up',
            r'improve\s+(?:the\s+)?code',
            r'optimize',
            r'reorganize',
        ],
        'fix_bug': [
            r'fix\s+(?:the\s+)?(?:bug|issue|problem|error)',
            r'debug',
            r'resolve\s+(?:the\s+)?(?:issue|error)',
            r'(?:doesn\'t|does\s+not)\s+work',
        ],
        'add_feature': [
            r'add\s+(?:a\s+)?(?:new\s+)?feature',
            r'implement\s+(?:a\s+)?(?:new\s+)?feature',
            r'extend\s+(?:the\s+)?functionality',
            r'enhance',
        ],
        'query_database': [
            r'query\s+(?:the\s+)?(?:database|db)',
            r'fetch\s+(?:data|records)',
            r'get\s+(?:all\s+)?(?:records|data|rows)',
            r'select\s+from',
            r'retrieve\s+(?:from\s+)?(?:database|db)',
        ]
    }
    
    # Patterns that suggest the user wants to reuse existing code
    REUSE_PATTERNS = [
        r'similar\s+to',
        r'like\s+(?:the\s+)?(?:existing|previous)',
        r'same\s+as',
        r'based\s+on',
        r'copy\s+from',
        r'use\s+(?:the\s+)?(?:existing|same)',
    ]
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.context_db = self.project_dir / '.claude' / 'context.db'
        self.context_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize context database"""
        conn = sqlite3.connect(str(self.context_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                prompt TEXT,
                intent TEXT,
                timestamp TIMESTAMP,
                suggestions TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                key TEXT,
                value TEXT,
                timestamp TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def analyze_intent(self, prompt: str) -> Tuple[str, List[str]]:
        """
        Analyze the user's intent from their prompt
        
        Returns:
            (primary_intent, suggestions)
        """
        prompt_lower = prompt.lower()
        
        # Check for each intent pattern
        intent_scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, prompt_lower))
            if score > 0:
                intent_scores[intent] = score
        
        # Get primary intent
        primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else 'general'
        
        # Generate suggestions based on intent
        suggestions = self._generate_suggestions(primary_intent, prompt)
        
        return primary_intent, suggestions
    
    def _generate_suggestions(self, intent: str, prompt: str) -> List[str]:
        """Generate contextual suggestions based on intent"""
        suggestions = []
        
        # Check if user wants to reuse existing code
        prompt_lower = prompt.lower()
        wants_reuse = any(re.search(pattern, prompt_lower) for pattern in self.REUSE_PATTERNS)
        
        if intent == 'duplicate_function' or wants_reuse:
            suggestions.append("Check existing functions before creating new ones")
            suggestions.append("Consider extending existing functions with parameters")
            suggestions.append("Look for similar functionality in utils/ or helpers/")
        
        elif intent == 'create_version':
            suggestions.append("Avoid creating file versions (_v2, _copy)")
            suggestions.append("Update the original file instead")
            suggestions.append("Use git branches for experimental changes")
        
        elif intent == 'query_database':
            suggestions.append("Check existing query functions in src/queries/")
            suggestions.append("Reuse existing database connections")
            suggestions.append("Consider using query builders or ORMs")
        
        elif intent == 'add_feature':
            suggestions.append("Check if similar features exist")
            suggestions.append("Follow existing architectural patterns")
            suggestions.append("Update documentation and tests")
        
        elif intent == 'refactor':
            suggestions.append("Preserve existing functionality")
            suggestions.append("Update tests after refactoring")
            suggestions.append("Consider backward compatibility")
        
        return suggestions
    
    def add_context_hints(self, prompt: str, session_id: str) -> Optional[str]:
        """
        Add context hints to help Claude make better decisions
        
        Returns enhanced prompt with context
        """
        intent, suggestions = self.analyze_intent(prompt)
        
        # Store in database
        conn = sqlite3.connect(str(self.context_db))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prompts (session_id, prompt, intent, timestamp, suggestions)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt, intent, datetime.now(), json.dumps(suggestions)))
        conn.commit()
        
        # Check for specific patterns that need context
        context_additions = []
        
        # Check if creating something that might already exist
        if re.search(r'create|add|write|implement', prompt.lower()):
            context_additions.append(
                "\n[Context: Check existing implementations before creating new code. "
                "Use 'search' or 'grep' to find similar functionality.]"
            )
        
        # Check if working with queries
        if re.search(r'query|database|sql|fetch.*data', prompt.lower()):
            context_additions.append(
                "\n[Context: Query functions are in src/queries/. "
                "Reuse existing queries when possible.]"
            )
        
        # Check if creating a "new" version of something
        if re.search(r'new\s+version|copy\s+of|_v\d+|duplicate', prompt.lower()):
            context_additions.append(
                "\n[Context: Instead of creating versions, update existing files directly. "
                "Use git for version control.]"
            )
        
        # Add recent context from this session
        cursor.execute("""
            SELECT key, value FROM context 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (session_id,))
        
        recent_context = cursor.fetchall()
        if recent_context:
            context_additions.append("\n[Recent context:")
            for key, value in recent_context:
                context_additions.append(f"  - {key}: {value}")
            context_additions.append("]")
        
        conn.close()
        
        # Return enhanced prompt if we have context to add
        if context_additions:
            return prompt + "\n" + "".join(context_additions)
        
        return None
    
    def log_activity(self, session_id: str, key: str, value: str):
        """Log activity for context tracking"""
        conn = sqlite3.connect(str(self.context_db))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO context (session_id, key, value, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, key, value, datetime.now()))
        conn.commit()
        conn.close()

def main():
    """Main hook entry point"""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)
        
        # Parse the hook data
        hook_data = json.loads(input_data)
        
        # Extract prompt and session ID
        prompt = hook_data.get('prompt', '')
        session_id = hook_data.get('session_id', 'default')
        
        if not prompt:
            sys.exit(0)
        
        # Get project directory
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # Check for --log-only flag
        log_only = '--log-only' in sys.argv
        
        # Initialize analyzer
        analyzer = IntentAnalyzer(project_dir)
        
        # Analyze intent
        intent, suggestions = analyzer.analyze_intent(prompt)
        
        # Log to file for debugging
        log_path = Path(project_dir) / '.claude' / 'intent.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a') as f:
            f.write(f"{datetime.now()}: Session {session_id}\n")
            f.write(f"  Intent: {intent}\n")
            f.write(f"  Prompt: {prompt[:100]}...\n")
            if suggestions:
                f.write(f"  Suggestions: {', '.join(suggestions)}\n")
            f.write("\n")
        
        # If not log-only, we could modify the prompt
        if not log_only:
            enhanced_prompt = analyzer.add_context_hints(prompt, session_id)
            if enhanced_prompt:
                # Output the enhanced prompt (this would be passed to Claude)
                # Note: This requires proper integration with Claude Code's prompt handling
                print(json.dumps({
                    'enhanced_prompt': enhanced_prompt,
                    'intent': intent,
                    'suggestions': suggestions
                }))
        
        sys.exit(0)
        
    except Exception as e:
        # Log error but don't block
        print(f"Intent analyzer error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()