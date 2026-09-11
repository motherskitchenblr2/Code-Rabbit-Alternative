# =============================================================================
# Git-Fix Auto-Fix PR System
# =============================================================================
# One-click fix application for GitHub/GitLab/Bitbucket/Azure DevOps PRs
# =============================================================================

import os
import json
import logging
import asyncio
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import difflib
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class FixStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    CONFLICT = "conflict"


class FixType(str, Enum):
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE_BLOCK = "replace_block"
    MOVE = "move"


@dataclass
class FixAction:
    id: str
    type: FixType
    file_path: str
    line_start: int
    line_end: int
    original_code: str
    fixed_code: str
    description: str
    rule_id: str
    confidence: float = 1.0
    requires_review: bool = False


@dataclass
class FixPlan:
    id: str
    finding_ids: List[str]
    actions: List[FixAction]
    status: FixStatus = FixStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None
    git_branch: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None


@dataclass
class FixResult:
    action_id: str
    status: FixStatus
    message: str
    diff: Optional[str] = None
    applied_at: Optional[datetime] = None
    error: Optional[str] = None


class FixGenerator:
    """Generate fix actions from findings"""

    def __init__(self):
        self.fix_strategies = {
            'hardcoded_secret': self._fix_hardcoded_secret,
            'sql_injection': self._fix_sql_injection,
            'command_injection': self._fix_command_injection,
            'hardcoded_credential': self._fix_hardcoded_credential,
            'insecure_deserialization': self._fix_insecure_deserialization,
            'path_traversal': self._fix_path_traversal,
            'xss_vulnerability': self._fix_xss_vulnerability,
            'weak_cryptography': self._fix_weak_cryptography,
            'missing_input_validation': self._fix_missing_validation,
            'sensitive_data_exposure': self._fix_sensitive_data_exposure,
        }

    def generate_fix_actions(
        self,
        findings: List[Dict[str, Any]],
        code: str,
        file_path: str,
        language: str,
    ) -> List[FixAction]:
        """Generate fix actions for findings"""
        actions = []

        for finding in findings:
            fix_type = finding.get('category', '').lower()
            if fix_type in self.fix_strategies:
                try:
                    actions.extend(
                        self.fix_strategies[fix_type](
                            finding, code, file_path
                        ))
                except Exception as e:
                    logger.warning(f"Failed to generate fix for {finding.get('id')}: {e}")

        return actions

    def _fix_hardcoded_secret(
        self, finding: Dict, code: str, file_path: str
    ) -> List[FixAction]:
        """Fix hardcoded secret by replacing with env var"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        # Find secret pattern
        patterns = [
            r'(?i)(api[_-]?key|secret|password|token|secret_key)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9\-_]{20,})[\"']?',
            r'(?i)(api[_-]?key|secret|password|token|secret_key)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9\-_]{20,})[\"']?',
        ]

        for pattern in ['password', 'secret', 'token', 'key', 'api_key']:
            if pattern in finding.get('message', '').lower():
                # Find the variable name
                var_match = re.search(r'(\w+)\s*[:=]\s*[\"\']([^\"']+)', lines[line])
                if var_match:
                    var_name = var_match.group(1)
                    secret_value = var_match.group(2)
                    env_var = f"{var_name.upper()}" if not var_name.isupper() else var_name.upper()

                    # Generate fix
                    original = lines[line]
                    fixed = re.sub(
                        rf'(?i)({re.escape(pattern)})\s*[:=]\s*[\"\']?([^\"' + "'\s]{8,})[\"']?",
                        rf'\1: os.environ.get("{env_var}")',
                        lines[line]
                    )

                    return [FixAction(
                        id=f"fix_{secrets.token_hex(8)}",
                        type=FixType.REPLACE,
                        file_path=finding.get('file_path', ''),
                        line_start=finding.get('line_start', 1),
                        line_end=finding.get('line_end', finding.get('line_start', 1)),
                        original_code=lines[line],
                        fixed_code=fixed,
                        description=f"Replace hardcoded secret with environment variable {env_var}",
                        rule_id="SEC-001",
                        confidence=0.9,
                    )]
        return []

    def _fix_sql_injection(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix SQL injection by using parameterized queries"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Pattern: f"SELECT * FROM users WHERE id = {user_id}"
        f_string_pattern = r'f["\']([^"\']*\{[^}]*\}[^"\']*)["\']'
        format_pattern = r'\.format\([^)]*\)'
        percent_pattern = r'%[sf]'

        for pattern, replacement_type in [
            (f_string_pattern, 'parameterized'),
            (format_pattern, 'parameterized'),
            (percent_pattern, 'parameterized'),
        ]:
            if re.search(pattern, lines[line]):
                # Generate parameterized query fix
                original = lines[line]
                # Simplified fix - in production, use AST parsing
                fixed = re.sub(
                    r'(execute|execute_query|query)\s*\(\s*f?["\']([^"\']*)\{([^}]+)\}([^"\']*)["\']\s*\)',
                    r'\1(" \2 ? \3 \4 ", (\3,))',
                    lines[line]
                )
                fixed = re.sub(
                    r'\.format\(([^)]+)\)',
                    r', \1',
                    fixed
                )
                fixed = re.sub(
                    r'%\s*\(([^)]+)\)',
                    r', \1',
                    fixed
                )

                actions.append(FixAction(
                    id=f"fix_{secrets.token_hex(8)}",
                    type=FixType.REPLACE,
                    file_path=finding.get('file_path', ''),
                    line_start=finding.get('line_start', 1),
                    line_end=finding.get('line_end', finding.get('line_start', 1)),
                    original_code=lines[line],
                    fixed_code=fixed,
                    description="Convert to parameterized query to prevent SQL injection",
                    rule_id="SEC-002",
                    confidence=0.85,
                ))

        return actions

    def _fix_command_injection(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix command injection by using shell=False"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Fix subprocess with shell=True
        if 'shell=True' in lines[line]:
            original = lines[line]
            fixed = lines[line].replace('shell=True', 'shell=False')
            
            # Also fix command construction
            if 'subprocess.run(' in lines[line] or 'subprocess.call(' in lines[line] or 'subprocess.Popen(' in lines[line]:
                # Convert string command to list
                fixed = re.sub(
                    r'subprocess\.(run|call|Popen)\(\s*(["\'])([^"\']+)\2\s*,\s*shell=True',
                    r'subprocess.\1(\3.split(), shell=False',
                    fixed
                )

            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Fix command injection by using shell=False and list arguments",
                rule_id="SEC-003",
                confidence=0.9,
            )]
        return []

    def _fix_hardcoded_credential(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix hardcoded credential by using environment variable"""
        return self._fix_hardcoded_secret(finding, code, file_path)

    def _fix_insecure_deserialization(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix insecure deserialization by using safe methods"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Fix pickle.load -> json.load
        if 'pickle.load' in lines[line] or 'pickle.loads' in lines[line]:
            original = lines[line]
            fixed = lines[line].replace('pickle.loads', 'json.loads').replace('pickle.load', 'json.load')
            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Replace unsafe pickle with json for safe deserialization",
                rule_id="SEC-005",
                confidence=0.9,
            )]

        # Fix yaml.load -> yaml.safe_load
        if 'yaml.load(' in lines[line]:
            original = lines[line]
            fixed = lines[line].replace('yaml.load(', 'yaml.safe_load(')
            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Use yaml.safe_load instead of unsafe yaml.load",
                rule_id="SEC-005",
                confidence=0.95,
            )]

        return actions

    def _fix_path_traversal(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix path traversal by using safe path resolution"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Fix path traversal
        if 'os.path.join' in lines[line] and ('../' in lines[line] or '..\\' in lines[line]):
            original = lines[line]
            fixed = re.sub(
                r'os\.path\.join\(([^,]+),\s*["\']([^"\']*\.\./[^"\']*)["\']',
                r'os.path.join(\1, os.path.normpath(os.path.join(base_dir, \2)))',
                lines[line]
            )
            # Add import for base_dir if needed
            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Fix path traversal by using safe path resolution",
                rule_id="SEC-006",
                confidence=0.85,
            )]
        return actions

    def _fix_xss_vulnerability(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix XSS by using safe rendering"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Fix dangerouslySetInnerHTML
        if 'dangerouslySetInnerHTML' in lines[line]:
            original = lines[line]
            fixed = lines[line].replace(
                'dangerouslySetInnerHTML={{__html:',
                'dangerouslySetInnerHTML={{__html: DOMPurify.sanitize('
            )
            # Add import
            if 'import DOMPurify' not in code:
                # Add import at top
                pass
            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Sanitize HTML with DOMPurify to prevent XSS",
                rule_id="SEC-007",
                confidence=0.9,
            )]

        # Fix v-html in Vue
        if 'v-html=' in lines[line]:
            original = lines[line]
            fixed = lines[line].replace('v-html=', 'v-html="sanitize(')
            return [FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.REPLACE,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Sanitize v-html content to prevent XSS",
                rule_id="SEC-007",
                confidence=0.9,
            )]

        return actions

    def _fix_weak_cryptography(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix weak cryptography by using strong algorithms"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        replacements = {
            'md5': 'hashlib.sha256',
            'sha1': 'hashlib.sha256',
            'DES': 'AES',
            'DES3': 'AES',
            'RC4': 'ChaCha20',
            'ECB': 'AES.MODE_GCM',
        }

        for weak, strong in replacements.items():
            if weak in lines[line]:
                original = lines[line]
                fixed = lines[line].replace(weak, strong)
                actions.append(FixAction(
                    id=f"fix_{secrets.token_hex(8)}",
                    type=FixType.REPLACE,
                    file_path=finding.get('file_path', ''),
                    line_start=finding.get('line_start', 1),
                    line_end=finding.get('line_end', finding.get('line_start', 1)),
                    original_code=lines[line],
                    fixed_code=fixed,
                    description=f"Replace weak {weak} with strong {strong} algorithm",
                    rule_id="SEC-008",
                    confidence=0.9,
                ))

        return actions

    def _fix_missing_validation(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Add input validation"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Add validation wrapper
        if 'request.' in lines[line] and 'validate' not in lines[line]:
            original = lines[line]
            # Add validation call
            indent = len(line_content) - len(line_content.lstrip())
            fixed = f"{' ' * indent}# Added validation\n{' ' * indent}validate_input({line_content.strip()})\n{' ' * indent}{line_content.lstrip()}"
            
            actions.append(FixAction(
                id=f"fix_{secrets.token_hex(8)}",
                type=FixType.INSERT,
                file_path=finding.get('file_path', ''),
                line_start=finding.get('line_start', 1),
                line_end=finding.get('line_end', finding.get('line_start', 1)),
                original_code=lines[line],
                fixed_code=fixed,
                description="Add input validation",
                rule_id="SEC-009",
                confidence=0.7,
            ))

        return actions

    def _fix_sensitive_data_exposure(self, finding: Dict, code: str, file_path: str) -> List[FixAction]:
        """Fix sensitive data exposure in logs"""
        line = finding.get('line_start', 1) - 1
        lines = code.split('\n')
        if line >= len(lines):
            return []

        line_content = lines[line]
        actions = []

        # Mask sensitive data in logs
        sensitive_patterns = ['password', 'secret', 'token', 'key', 'ssn', 'credit_card', 'api_key']
        for pattern in sensitive_patterns:
            if pattern in lines[line].lower():
                original = lines[line]
                fixed = re.sub(
                    rf'(?i)({pattern}\s*[:=]\s*)([^"\'\\s,)]+)',
                    r'\1***REDACTED***',
                    lines[line]
                )
                actions.append(FixAction(
                    id=f"fix_{secrets.token_hex(8)}",
                    type=FixType.REPLACE,
                    file_path=finding.get('file_path', ''),
                    line_start=finding.get('line_start', 1),
                    line_end=finding.get('line_end', finding.get('line_start', 1)),
                    original_code=lines[line],
                    fixed_code=fixed,
                    description="Redact sensitive data in logs",
                    rule_id="SEC-010",
                    confidence=0.8,
                ))

        return actions


class AutoFixPRManager:
    """Manage auto-fix PR creation and application"""

    def __init__(
        self,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        base_branch: str = "main",
    ):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_branch = base_branch
        self.fix_generator = FixGenerator()
        self.fix_plans: Dict[str, FixPlan] = {}
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    async def create_fix_plan(
        self,
        findings: List[Dict[str, Any]],
        repository_files: Dict[str, str],
    ) -> FixPlan:
        """Create a fix plan from findings"""
        all_actions = []

        for finding in findings:
            file_path = finding.get('file_path', '')
            code = repository_files.get(file_path, '')
            language = self._detect_language(finding.get('file_path', ''))

            actions = FixGenerator().generate_fix_actions(
                [finding],
                repository_files.get(finding.get('file_path', ''), ''),
                finding.get('file_path', ''),
                self._detect_language(finding.get('file_path', '')),
            )
            all_actions.extend(actions)

        fix_plan = FixPlan(
            id=f"fixplan_{secrets.token_hex(8)}",
            finding_ids=[f.get('id', '') for f in findings],
            actions=[a for a in all_actions if a.confidence >= 0.7],
        )

        return fix_plan

    def _detect_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cs': 'csharp',
        }
        return ext_map.get(Path(file_path).suffix.lower(), 'text')

    async def apply_fix_plan(
        self,
        fix_plan: FixPlan,
        create_pr: bool = True,
        auto_merge: bool = False,
    ) -> FixPlan:
        """Apply fix plan by creating a branch and PR"""
        import git

        repo = git.Repo('.')
        fix_plan.git_branch = f"gitfix/auto-fix-{fix_plan.id[:8]}"

        # Create branch
        repo.git.checkout('-b', fix_plan.git_branch)

        # Apply fixes
        results = []
        for action in fix_plan.actions:
            result = await self._apply_fix_action(action)
            results.append(result)

        # Check for conflicts
        failed = [r for r in results if r.status == FixStatus.FAILED or r.status == FixStatus.CONFLICT]
        if failed:
            fix_plan.status = FixStatus.FAILED
            fix_plan.error_message = f"{len(failed)} fixes failed"
            return fix_plan

        # Commit changes
        repo.git.add('.')
        repo.index.commit(f"Git-Fix: Auto-fix {len(fix_plan.actions)} issues\n\nFix Plan: {fix_plan.id}")

        # Push branch
        origin = repo.remote(name='origin')
        origin.push(refspec=f'{fix_plan.git_branch}:{fix_plan.git_branch}')

        fix_plan.status = FixStatus.APPLIED
        fix_plan.applied_at = datetime.utcnow()

        if create_pr:
            # Create PR
            pr = await self._create_pull_request(fix_plan)
            fix_plan.pr_number = pr.number
            fix_plan.pr_url = pr.html_url

            if auto_merge:
                # Enable auto-merge
                pass

        return fix_plan

    async def _apply_fix_action(self, action: FixAction) -> FixResult:
        """Apply a single fix action"""
        try:
            file_path = action.file_path
            if not os.path.exists(file_path):
                return FixResult(
                    action_id=action.id,
                    status=FixStatus.FAILED,
                    message=f"File not found: {file_path}",
                    error="File not found",
                )

            # Read file
            with open(file_path, 'r') as f:
                content = f.read()

            # Apply fix
            if action.type == FixType.REPLACE:
                lines = action.original_code.split('\n')
                fixed_lines = action.fixed_code.split('\n')
                
                # Read full file
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Replace
                if action.original_code in content:
                    new_content = content.replace(action.original_code, action.fixed_code, 1)
                else:
                    # Try line-based replacement
                    lines = content.split('\n')
                    start = action.line_start - 1
                    end = action.line_end
                    if 0 <= start < len(lines):
                        lines[start:end] = action.fixed_code.split('\n')
                        new_content = '\n'.join(lines)
                    else:
                        return FixResult(
                            action_id=action.id,
                            status=FixStatus.FAILED,
                            message="Invalid line range",
                            error="Invalid line range",
                        )
                
                # Write back
                with open(file_path, 'w') as f:
                    f.write(new_content)

                # Generate diff
                diff = '\n'.join(difflib.unified_diff(
                    action.original_code.split('\n'),
                    action.fixed_code.split('\n'),
                    fromfile='original',
                    tofile='fixed',
                    lineterm=''
                ))

                return FixResult(
                    action_id=action.id,
                    status=FixStatus.APPLIED,
                    message="Fix applied successfully",
                    diff=diff,
                    applied_at=datetime.utcnow(),
                )

            elif action.type == FixType.INSERT:
                # Insert at line
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                lines.insert(action.line_start, action.fixed_code + '\n')
                
                with open(file_path, 'w') as f:
                    f.writelines(lines)

                return FixResult(
                    action_id=action.id,
                    status=FixStatus.APPLIED,
                    message="Code inserted",
                    applied_at=datetime.utcnow(),
                )

            elif action.type == FixType.DELETE:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                del lines[action.line_start - 1:action.line_end]
                
                with open(file_path, 'w') as f:
                    f.writelines(lines)

                return FixResult(
                    action_id=action.id,
                    status=FixStatus.APPLIED,
                    message="Code deleted",
                    applied_at=datetime.utcnow(),
                )

            return FixResult(
                action_id=action.id,
                status=FixStatus.FAILED,
                message=f"Unknown fix type: {action.type}",
                error="Unknown fix type",
            )

        except Exception as e:
            logger.error(f"Failed to apply fix {action.id}: {e}")
            return FixResult(
                action_id=action.id,
                status=FixStatus.FAILED,
                message=str(e),
                error=str(e),
            )

    async def _create_pull_request(self, fix_plan: FixPlan):
        """Create pull request on GitHub"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await httpx.post(
                f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls",
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={
                    "title": f"Git-Fix: Auto-fix {len(fix_plan.actions)} issues",
                    "body": self._generate_pr_body(fix_plan),
                    "head": fix_plan.git_branch,
                    "base": self.base_branch,
                },
            )
            response.raise_for_status()
            return response.json()

    def _generate_pr_body(self, fix_plan: FixPlan) -> str:
        body = f"""## Git-Fix Auto-Fix PR

This PR was automatically generated by Git-Fix to fix {len(fix_plan.actions)} issues.

### Fixes Applied
"""
        for action in fix_plan.actions:
            body += f"- **{action.rule_id}**: {action.description} in `{action.file_path}:{action.line_start}`\n"

        body += f"""
### Changes
- Files modified: {len(set(a.file_path for a in fix_plan.actions))}
- Total fixes: {len(fix_plan.actions)}
- Fix Plan ID: {fix_plan.id}

---
*Auto-generated by Git-Fix*
"""
        return body


class OneClickFixAPI:
    """REST API for one-click fix operations"""

    def __init__(self, app: Any = None):
        self.app = app
        self.fix_manager = None

    def init_app(self, app: Any, github_token: str, repo_owner: str, repo_name: str):
        self.app = app
        self.fix_manager = AutoFixPRManager(
            github_token=github_token,
            repo_owner=repo_owner,
            repo_name=repo_name,
        )

        # Register routes
        self._register_routes()

    def _register_routes(self):
        from flask import Blueprint, request, jsonify

        bp = Blueprint('autofix', __name__, url_prefix='/api/autofix')

        @bp.route('/scan', methods=['POST'])
        def scan_and_fix():
            data = request.get_json()
            findings = data.get('findings', [])
            files = data.get('files', {})

            fix_plan = self.fix_manager.create_fix_plan(findings, files)
            return jsonify({
                'fix_plan_id': fix_plan.id,
                'actions_count': len(fix_plan.actions),
                'estimated_time': len(fix_plan.actions) * 2,
            })

        @bp.route('/apply/<fix_plan_id>', methods=['POST'])
        async def apply_fix(fix_plan_id: str):
            # Get fix plan from storage
            # fix_plan = await storage.get(fix_plan_id)
            # result = await fix_manager.apply_fix_plan(fix_plan)
            return jsonify({'status': 'started', 'fix_plan_id': fix_plan_id})

        @bp.route('/plan/<fix_plan_id>', methods=['GET'])
        def get_plan(fix_plan_id: str):
            # Retrieve plan from storage
            return jsonify({'fix_plan_id': fix_plan_id, 'status': 'pending'})

        @bp.route('/plan/<fix_plan_id>/preview', methods=['GET'])
        def preview_fix(fix_plan_id: str):
            # Return diff preview
            return jsonify({'diff': '...', 'files_changed': 0})

        self.app.register_blueprint(bp)


def create_autofix_manager(
    github_token: str,
    repo_owner: str,
    repo_name: str,
    base_branch: str = "main",
) -> AutoFixPRManager:
    return AutoFixPRManager(github_token, repo_owner, repo_name, base_branch)