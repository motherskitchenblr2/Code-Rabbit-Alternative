# =============================================================================
# Git-Fix Custom Policy Engine - DSL for Security Policies
# =============================================================================
# Domain-Specific Language for defining and enforcing security policies
# =============================================================================

import os
import re
import json
import logging
import ast
import operator
from typing import Optional, List, Dict, Any, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# =============================================================================
# Module-level pattern registry for access in lambdas
# =============================================================================

_PATTERNS = {
    'secret_pattern': r'(?i)(api[_-]?key|secret|password|token)[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})[\'"]?',
    'sql_injection': r'fmt\.Sprintf\s*\([^)]*%[^)]*\)|execute\s*\([^)]*\+[^)]*\)|query\s*\(\s*["\'].*\+',
    'command_injection': r'eval\s*\([^)]+\)|exec\s*\([^)]+\)|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
    'weak_crypto': r'(md5|sha1|des|rc4|ecb)[\s\.\(]',
    'xss_pattern': r'innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=',
    'path_traversal': r'\.\./|\.\.\\|%2e%2e|%252e%252e',
    'sql_concat': r'SELECT\s+.*\+.*FROM|INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+|UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+',
}

class PolicySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class PolicyAction(str, Enum):
    DENY = "deny"
    WARN = "warn"
    AUDIT = "audit"
    ALLOW = "allow"
    AUTO_FIX = "auto_fix"


class PolicyScope(str, Enum):
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    REPOSITORY = "repository"
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"


@dataclass
class PolicyRule:
    id: str
    name: str
    description: str
    severity: PolicySeverity
    action: PolicyAction
    scope: PolicyScope
    condition: str  # DSL expression
    message: str
    remediation: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyViolation:
    rule_id: str
    rule_name: str
    severity: PolicySeverity
    action: PolicyAction
    file_path: str
    line: int
    column: int
    message: str
    code_snippet: str
    suggested_fix: Optional[str] = None
    remediation: Optional[str] = None
    confidence: float = 1.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyEvaluationResult:
    violations: List[PolicyViolation]
    passed: bool
    evaluated_rules: int
    execution_time_ms: float


class PolicyParser:
    """Parse and compile policy DSL expressions"""

    # Supported operators
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
        'contains': lambda x, y: y in x if isinstance(x, str) else False,
        'startswith': lambda x, y: x.startswith(y) if isinstance(x, str) else False,
        'endswith': lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        'matches': lambda x, y: bool(re.match(y, x)) if isinstance(x, str) else False,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'not': lambda x: not x,
    }

    # Built-in functions - module level for access in lambdas
    FUNCTIONS = {
        'len': len,
        'count': lambda x: len(x) if hasattr(x, '__len__') else 0,
        'sum': sum,
        'max': max,
        'min': min,
        'any': any,
        'all': all,
        'contains': lambda seq, item: item in seq,
        'startswith': lambda s, prefix: s.startswith(prefix) if isinstance(s, str) else False,
        'endswith': lambda s, suffix: s.endswith(suffix) if isinstance(s, str) else False,
        'matches': lambda s, pattern: bool(re.match(pattern, s)) if isinstance(s, str) else False,
        'regex_match': lambda s, pattern: bool(re.search(_PATTERNS.get(pattern, pattern), s)) if isinstance(s, str) else False,
        'contains_any': lambda seq, items: any(item in seq for item in items),
        'contains_all': lambda seq, items: all(item in seq for item in items),
    }

    # Pattern registry - module level for access in lambdas
    PATTERNS = {
        'secret_pattern': r'(?i)(api[_-]?key|secret|password|token)[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})[\'"]?',
        'sql_injection': r'fmt\.Sprintf\s*\([^)]*%[^)]*\)|execute\s*\([^)]*\+[^)]*\)|query\s*\(\s*["\'].*\+',
        'command_injection': r'eval\s*\([^)]+\)|exec\s*\([^)]+\)|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
        'weak_crypto': r'(md5|sha1|des|rc4|ecb)[\s\.\(]',
        'xss_pattern': r'innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=',
        'path_traversal': r'\.\./|\.\.\\|%2e%2e|%252e%252e',
        'sql_concat': r'SELECT\s+.*\+.*FROM|INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+|UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+',
    }

    # Supported operators
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
        'contains': lambda x, y: y in x if isinstance(x, str) else False,
        'startswith': lambda x, y: x.startswith(y) if isinstance(x, str) else False,
        'endswith': lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        'matches': lambda x, y: bool(re.match(y, x)) if isinstance(x, str) else False,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'not': lambda x: not x,
    }

    # Built-in functions - module level for access in lambdas
    FUNCTIONS = {
        'len': len,
        'count': lambda x: len(x) if hasattr(x, '__len__') else 0,
        'sum': sum,
        'max': max,
        'min': min,
        'any': any,
        'all': all,
        'contains': lambda seq, item: item in seq,
        'startswith': lambda s, prefix: s.startswith(prefix) if isinstance(s, str) else False,
        'endswith': lambda s, suffix: s.endswith(suffix) if isinstance(s, str) else False,
        'matches': lambda s, pattern: bool(re.match(pattern, s)) if isinstance(s, str) else False,
        'regex_match': lambda s, pattern: bool(re.search(_PATTERNS.get(pattern, pattern), s)) if isinstance(s, str) else False,
        'contains_any': lambda seq, items: any(item in seq for item in items),
        'contains_all': lambda seq, items: all(item in seq for item in items),
    }

    # Pattern registry - module level for access in lambdas
    PATTERNS = {
        'secret_pattern': r'(?i)(api[_-]?key|secret|password|token)[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})[\'"]?',
        'sql_injection': r'fmt\.Sprintf\s*\([^)]*%[^)]*\)|execute\s*\([^)]*\+[^)]*\)|query\s*\(\s*["\'].*\+',
        'command_injection': r'eval\s*\([^)]+\)|exec\s*\([^)]+\)|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
        'weak_crypto': r'(md5|sha1|des|rc4|ecb)[\s\.\(]',
        'xss_pattern': r'innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=',
        'path_traversal': r'\.\./|\.\.\\|%2e%2e|%252e%252e',
        'sql_concat': r'SELECT\s+.*\+.*FROM|INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+|UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+',
    }

    # Supported operators
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
        'contains': lambda x, y: y in x if isinstance(x, str) else False,
        'startswith': lambda x, y: x.startswith(y) if isinstance(x, str) else False,
        'endswith': lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        'matches': lambda x, y: bool(re.match(y, x)) if isinstance(x, str) else False,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'not': lambda x: not x,
    }

    # Built-in functions - module level for access in lambdas
    FUNCTIONS = {
        'len': len,
        'count': lambda x: len(x) if hasattr(x, '__len__') else 0,
        'sum': sum,
        'max': max,
        'min': min,
        'any': any,
        'all': all,
        'contains': lambda seq, item: item in seq,
        'startswith': lambda s, prefix: s.startswith(prefix) if isinstance(s, str) else False,
        'endswith': lambda s, suffix: s.endswith(suffix) if isinstance(s, str) else False,
        'matches': lambda s, pattern: bool(re.match(pattern, s)) if isinstance(s, str) else False,
        'regex_match': lambda s, pattern: bool(re.search(_PATTERNS.get(pattern, pattern), s)) if isinstance(s, str) else False,
        'contains_any': lambda seq, items: any(item in seq for item in items),
        'contains_all': lambda seq, items: all(item in seq for item in items),
    }

    # Pattern registry - module level for access in lambdas
    PATTERNS = {
        'secret_pattern': r'(?i)(api[_-]?key|secret|password|token)[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})[\'"]?',
        'sql_injection': r'fmt\.Sprintf\s*\([^)]*%[^)]*\)|execute\s*\([^)]*\+[^)]*\)|query\s*\(\s*["\'].*\+',
        'command_injection': r'eval\s*\([^)]+\)|exec\s*\([^)]+\)|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
        'weak_crypto': r'(md5|sha1|des|rc4|ecb)[\s\.\(]',
        'xss_pattern': r'innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=',
        'path_traversal': r'\.\./|\.\.\\|%2e%2e|%252e%252e',
        'sql_concat': r'SELECT\s+.*\+.*FROM|INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+|UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+',
    }

    # Supported operators
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
        'contains': lambda x, y: y in x if isinstance(x, str) else False,
        'startswith': lambda x, y: x.startswith(y) if isinstance(x, str) else False,
        'endswith': lambda x, y: x.endswith(y) if isinstance(x, str) else False,
        'matches': lambda x, y: bool(re.match(y, x)) if isinstance(x, str) else False,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'not': lambda x: not x,
    }

    def __init__(self):
        self.variables: Dict[str, Any] = {}

    def parse(self, expression: str) -> ast.AST:
        """Parse DSL expression into AST"""
        try:
            return ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise PolicySyntaxError(f"Invalid policy syntax: {e}")

    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate DSL expression with context"""
        try:
            # Prepare safe evaluation environment
            # Functions and operators need to be in globals for eval to find them
            safe_globals = {
                "__builtins__": {},
                **self.FUNCTIONS,
                **self.OPERATORS,
            }
            # Context variables go in locals
            safe_locals = {**context}
            
            # Parse and compile
            tree = self.parse(expression)
            code = compile(tree, '<policy>', 'eval')
            
            # Evaluate safely with functions in globals
            result = eval(code, safe_globals, safe_locals)
            return result
        except Exception as e:
            logger.warning(f"Policy evaluation error: {e}")
            return False

    def validate(self, expression: str) -> Tuple[bool, Optional[str]]:
        """Validate DSL expression syntax"""
        try:
            self.parse(expression)
            return True, None
        except PolicySyntaxError as e:
            return False, str(e)


class PolicySyntaxError(Exception):
    """Policy syntax error"""
    pass


# Module-level pattern registry for access in lambdas
_PATTERNS = {
    'secret_pattern': r'(?i)(api[_-]?key|secret|password|token)[\'"]?\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})[\'"]?',
    'sql_injection': r'fmt\.Sprintf\s*\([^)]*%[^)]*\)|execute\s*\([^)]*\+[^)]*\)|query\s*\(\s*["\'].*\+',
    'command_injection': r'eval\s*\([^)]+\)|exec\s*\([^)]+\)|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True',
    'weak_crypto': r'(md5|sha1|des|rc4|ecb)[\s\.\(]',
    'xss_pattern': r'innerHTML\s*=|dangerouslySetInnerHTML|v-html\s*=',
    'path_traversal': r'\.\./|\.\.\\|%2e%2e|%252e%252e',
    'sql_concat': r'SELECT\s+.*\+.*FROM|INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+|UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+',
}