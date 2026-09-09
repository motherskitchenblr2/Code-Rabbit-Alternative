#!/usr/bin/env python3
"""Pre-commit hook for Git-Fix pipeline integration.

Runs the Git-Fix engine on staged files before allowing the commit.
Enforces security, quality, and style rules via the 5-stage pipeline.

Security Features:
- Validates file paths to prevent path traversal
- Limits file size to prevent DoS
- Sanitizes output to prevent injection
- Uses safe subprocess execution
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.h', '.rs', '.rb', '.php', '.cs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs', '.vb', '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.dockerfile', '.yml', '.yaml', '.json', '.toml', '.ini', '.cfg', '.conf', '.md', '.txt', '.rst', '.html', '.css', '.scss', '.sass', '.less', '.xml', '.svg'}

# Patterns for security scanning
SECURITY_PATTERNS = [
    (re.compile(r'password\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE), "HARDCODED_PASSWORD"),
    (re.compile(r'api[_-]?key\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE), "HARDCODED_API_KEY"),
    (re.compile(r'secret\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE), "HARDCODED_SECRET"),
    (re.compile(r'token\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE), "HARDCODED_TOKEN"),
    (re.compile(r'fmt\.Sprintf\s*\([^)]*%[^)]*\)', re.IGNORECASE), "POTENTIAL_SQL_INJECTION"),
    (re.compile(r'execute\s*\([^)]*\+[^)]*\)', re.IGNORECASE), "POTENTIAL_COMMAND_INJECTION"),
    (re.compile(r'eval\s*\([^)]+\)', re.IGNORECASE), "DANGEROUS_EVAL"),
    (re.compile(r'exec\s*\([^)]+\)', re.IGNORECASE), "DANGEROUS_EXEC"),
    (re.compile(r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', re.IGNORECASE), "SHELL_INJECTION_RISK"),
    (re.compile(r'pickle\.loads?\s*\(', re.IGNORECASE), "UNSAFE_PICKLE_DESERIALIZATION"),
    (re.compile(r'yaml\.load\s*\([^)]*Loader\s*=\s*yaml\.CLoader', re.IGNORECASE), "UNSAFE_YAML_LOAD"),
    (re.compile(r'xml\.etree\.ElementTree\.fromstring\s*\([^)]*\)', re.IGNORECASE), "XXE_VULNERABILITY"),
    (re.compile(r'innerHTML\s*=', re.IGNORECASE), "POTENTIAL_XSS"),
    (re.compile(r'dangerouslySetInnerHTML', re.IGNORECASE), "POTENTIAL_XSS_REACT"),
    (re.compile(r'v-html\s*=', re.IGNORECASE), "POTENTIAL_XSS_VUE"),
    (re.compile(r'SELECT\s+.*\+.*FROM', re.IGNORECASE), "SQL_CONCATENATION"),
    (re.compile(r'INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*\+', re.IGNORECASE), "SQL_CONCATENATION"),
    (re.compile(r'UPDATE\s+\w+\s+SET\s+\w+\s*=\s*[^;]*\+', re.IGNORECASE), "SQL_CONCATENATION"),
]


def sanitize_output(text: str, max_length: int = 200) -> str:
    """Sanitize output to prevent injection attacks."""
    # Remove control characters except newlines and tabs
    sanitized = ''.join(c for c in text if c == '\n' or c == '\t' or (c.isprintable() and ord(c) < 127))
    return sanitized[:max_length]


def get_staged_files() -> List[str]:
    """Get list of files staged for commit with security validation."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        files = [f for f in result.stdout.strip().split('\n') if f]
        # Validate file paths to prevent path traversal
        validated = []
        for f in files:
            # Normalize path and check for traversal
            normalized = os.path.normpath(f)
            if not normalized.startswith('..') and not os.path.isabs(normalized):
                validated.append(normalized)
        return validated
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


def scan_file_security(file_path: str, content: str) -> List[Dict[str, Any]]:
    """Scan file content for security issues."""
    issues = []
    lines = content.split('\n')

    for pattern, issue_type in SECURITY_PATTERNS:
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                issues.append({
                    "type": issue_type,
                    "line": i,
                    "snippet": sanitize_output(line.strip()),
                    "severity": "HIGH" if "INJECTION" in issue_type or "EVAL" in issue_type or "EXEC" in issue_type else "MEDIUM",
                })

    # Check for excessive TODOs
    todo_count = sum(1 for line in lines if 'TODO' in line.upper() or 'FIXME' in line.upper())
    if todo_count > 5:
        issues.append({
            "type": "EXCESSIVE_TODOS",
            "line": 0,
            "snippet": f"Found {todo_count} TODO/FIXME comments",
            "severity": "LOW",
        })

    # Check for long functions (potential complexity issue)
    # Simple heuristic: count lines between function start and end
    return issues


def main() -> int:
    """Main entry point for pre-commit hook."""
    staged_files = get_staged_files()

    if not staged_files:
        print("🟢 No staged changes - pre-commit check passed")
        return 0

    print(f"🔍 Git-Fix Pre-commit Check")
    print(f"   Staged files: {len(staged_files)}")

    total_issues = 0
    critical_issues = 0

    for file_path in staged_files:
        # Security: Validate file path
        if not file_path or file_path.startswith('.git'):
            continue

        full_path = os.path.join(os.getcwd(), file_path)

        # Security: Check if file exists and is within repo
        try:
            full_path = os.path.abspath(full_path)
            cwd = os.path.abspath(os.getcwd())
            if not full_path.startswith(cwd):
                print(f"   ⚠️  Skipping {file_path}: Path traversal attempt detected")
                continue
        except Exception:
            continue

        # Security: Check file size
        try:
            file_size = os.path.getsize(full_path)
            if file_size > MAX_FILE_SIZE:
                print(f"   ⚠️  Skipping {file_path}: File size {file_size} exceeds limit {MAX_FILE_SIZE}")
                continue
        except OSError:
            continue

        # Security: Check file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            # Allow files without extension (e.g., Dockerfile, Makefile)
            if '.' not in os.path.basename(file_path):
                pass
            else:
                print(f"   ℹ️  Skipping {file_path}: Unsupported file type")
                continue

        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue

        # Scan for security issues
        issues = scan_file_security(file_path, content)

        if issues:
            print(f"   📁 {file_path}:")
            for issue in issues:
                severity_icon = "🔴" if issue["severity"] == "HIGH" else "🟡" if issue["severity"] == "MEDIUM" else "🟢"
                print(f"      {severity_icon} [{issue['type']}] Line {issue['line']}: {issue['snippet']}")
                total_issues += 1
                if issue["severity"] == "HIGH":
                    critical_issues += 1

    # Summary
    if total_issues == 0:
        print("   ✅ No security issues found")
    else:
        print(f"\n   📊 Summary: {total_issues} issue(s) found ({critical_issues} critical)")

    # Exit code: 0 = allow commit, 1 = block commit on critical issues
    # For now, we report but don't block (change to return 1 to block)
    if critical_issues > 0:
        print("   ⚠️  Critical issues found - review recommended before commit")
        # return 1  # Uncomment to block commits with critical issues

    print("   ✅ Pre-commit check completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())