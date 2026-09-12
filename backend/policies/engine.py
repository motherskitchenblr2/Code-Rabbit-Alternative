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

    # Node types permitted in policy AST evaluation (no imports, no assignments,
    # no comprehensions, no attribute dunder access).
    _SAFE_AST_TYPES = frozenset({
        ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
        ast.Compare, ast.Call, ast.Name, ast.Constant, ast.Load,
        ast.Attribute, ast.Subscript, ast.Slice, ast.Tuple, ast.List,
        ast.Dict, ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt,
        ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Add, ast.Sub,
        ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    })

    # Method names permitted on values inside policy expressions. Anything else
    # (including every dunder, __class__, __getattribute__, __subclasses__, ...)
    # is rejected before evaluation.
    _SAFE_METHODS = frozenset({
        'startswith', 'endswith', 'contains', 'matches', 'regex_match',
        'count', 'lower', 'upper', 'strip', 'lstrip', 'rstrip', 'split',
        'rsplit', 'join', 'replace', 'format', 'find', 'index', 'isdigit',
        'isalpha', 'isalnum', 'isupper', 'islower',
    })

    def _validate_ast(self, node: ast.AST) -> None:
        """Walk the AST and reject any node type or name not in the allowlist."""
        if type(node) not in self._SAFE_AST_TYPES:
            raise PolicySyntaxError(
                f"Unsupported expression node: {type(node).__name__}"
            )
        if isinstance(node, ast.Name):
            if node.id.startswith('__'):
                raise PolicySyntaxError(f"Reserved name: {node.id}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('__'):
                raise PolicySyntaxError(f"Reserved attribute: {node.attr}")
            if node.attr not in self._SAFE_METHODS:
                raise PolicySyntaxError(
                    f"Disallowed method: {node.attr}"
                )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in self.FUNCTIONS:
                    raise PolicySyntaxError(f"Unknown function: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith('__'):
                    raise PolicySyntaxError(
                        f"Reserved method: {node.func.attr}"
                    )
                if node.func.attr not in self._SAFE_METHODS:
                    raise PolicySyntaxError(
                        f"Disallowed method: {node.func.attr}"
                    )
            else:
                raise PolicySyntaxError(
                    "Only direct function/method calls are allowed"
                )
        for child in ast.iter_child_nodes(node):
            self._validate_ast(child)

    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate DSL expression with context (AST-validated, no eval/compile)."""
        try:
            tree = self.parse(expression)
            self._validate_ast(tree)

            safe_globals = {
                **self.FUNCTIONS,
                **self.OPERATORS,
            }
            safe_locals = {**context}
            return self._eval_node(tree, safe_globals, safe_locals)
        except PolicySyntaxError:
            raise
        except Exception as e:
            logger.warning(f"Policy evaluation error: {e}")
            return False

    def _eval_node(self, node: ast.AST,
                   globals_: Dict[str, Any], locals_: Dict[str, Any]) -> Any:
        """Recursively interpret the allowlisted parse tree without compiling strings."""
        t = type(node)
        if t is ast.Expression:
            return self._eval_node(node.body, globals_, locals_)
        if t is ast.Constant:
            return node.value
        if t is ast.Name:
            if node.id in locals_:
                return locals_[node.id]
            if node.id in globals_:
                return globals_[node.id]
            raise PolicySyntaxError(f"Unknown name: {node.id}")
        if t is ast.Attribute:
            value = self._eval_node(node.value, globals_, locals_)
            return getattr(value, node.attr)
        if t is ast.Subscript:
            value = self._eval_node(node.value, globals_, locals_)
            key = self._eval_node(node.slice, globals_, locals_)
            return value[key]
        if t is ast.Slice:
            lower = self._eval_node(node.lower, globals_, locals_) if node.lower is not None else None
            upper = self._eval_node(node.upper, globals_, locals_) if node.upper is not None else None
            step = self._eval_node(node.step, globals_, locals_) if node.step is not None else None
            return slice(lower, upper, step)
        if t is ast.Tuple:
            return tuple(self._eval_node(e, globals_, locals_) for e in node.elts)
        if t is ast.List:
            return [self._eval_node(e, globals_, locals_) for e in node.elts]
        if t is ast.Dict:
            keys = node.keys
            return {
                (self._eval_node(k, globals_, locals_) if k is not None else None):
                self._eval_node(v, globals_, locals_)
                for k, v in zip(keys, node.values)
            }
        if t is ast.BoolOp:
            result: Any = None
            for v in node.values:
                result = self._eval_node(v, globals_, locals_)
                if isinstance(node.op, ast.And) and not result:
                    break
                if isinstance(node.op, ast.Or) and result:
                    break
            return result
        if t is ast.BinOp:
            left = self._eval_node(node.left, globals_, locals_)
            right = self._eval_node(node.right, globals_, locals_)
            op = {
                ast.Add: operator.add, ast.Sub: operator.sub,
                ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Mod: operator.mod, ast.Pow: operator.pow,
            }.get(type(node.op))
            if op is None:
                raise PolicySyntaxError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        if t is ast.UnaryOp:
            operand = self._eval_node(node.operand, globals_, locals_)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.Not):
                return not operand
            raise PolicySyntaxError(f"Unsupported unary op: {type(node.op).__name__}")
        if t is ast.Compare:
            left = self._eval_node(node.left, globals_, locals_)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, globals_, locals_)
                cmp_op = {
                    ast.Eq: operator.eq, ast.NotEq: operator.ne,
                    ast.Lt: operator.lt, ast.LtE: operator.le,
                    ast.Gt: operator.gt, ast.GtE: operator.ge,
                    ast.In: lambda a, b: a in b,
                    ast.NotIn: lambda a, b: a not in b,
                }.get(type(op))
                if cmp_op is None:
                    raise PolicySyntaxError(f"Unsupported comparison: {type(op).__name__}")
                if not cmp_op(left, right):
                    return False
                left = right
            return True
        if t is ast.IfExp:
            test = self._eval_node(node.test, globals_, locals_)
            return self._eval_node(node.body if test else node.orelse, globals_, locals_)
        if t is ast.Call:
            args = [self._eval_node(a, globals_, locals_) for a in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value, globals_, locals_)
                      for kw in node.keywords if kw.arg}
            if isinstance(node.func, ast.Name):
                fn = locals_.get(node.func.id) if node.func.id in locals_ else globals_.get(node.func.id)
                if fn is None:
                    raise PolicySyntaxError(f"Unknown function: {node.func.id}")
                return fn(*args, **kwargs)
            value = self._eval_node(node.func.value, globals_, locals_)
            return getattr(value, node.func.attr)(*args, **kwargs)
        raise PolicySyntaxError(f"Unsupported expression node: {t.__name__}")

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