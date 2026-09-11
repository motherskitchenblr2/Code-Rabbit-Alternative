from flask import Flask, request, jsonify, g
from flask_cors import CORS
import json
import hashlib
import hmac
import base64
import time
import os
import logging
import secrets
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any

from backend.security import (
    init_security,
    security_ready,
    rate_limit,
    create_token,
    verify_token,
    extract_token,
    require_admin,
)
import backend.security as security_mod
from backend.config import load_env, log_level, formatter, RequestIdFilter
import atexit
from backend.queue import submit, shutdown as shutdown_bg_pool

# Load local .env (never overrides real env) before any config is read.
load_env()

# Ensure background worker threads drain on exit.
atexit.register(shutdown_bg_pool)

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

try:
    from flask_talisman import Talisman
    TALISMAN_AVAILABLE = True
except ImportError:
    TALISMAN_AVAILABLE = False

try:
    from pydantic import BaseModel, Field, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

app = Flask(__name__)

# Security Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    MAX_CONTENT_LENGTH=int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)),  # 16MB
    JSON_SORT_KEYS=False,
)

# Shared security helpers (rate limiting + token auth)
init_security(app.config['SECRET_KEY'])

# CORS Configuration - Restrict to specific origins in production
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
CORS(app, origins=CORS_ORIGINS, supports_credentials=True, allow_headers=['Content-Type', 'Authorization'])

# Security Headers with Talisman
if TALISMAN_AVAILABLE:
    Talisman(
        app,
        force_https=os.environ.get('FORCE_HTTPS', 'false').lower() == 'true',
        strict_transport_security=True,
        session_cookie_secure=True,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
            'font-src': "'self' https://fonts.gstatic.com",
            'img-src': "'self' data: https:",
            'connect-src': "'self' ws: wss:",
        },
        force_https_permanent=True,
    )

# Rate Limiter
if RATE_LIMITER_AVAILABLE:
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.environ.get('REDIS_URL', 'memory://'),
    )
else:
    limiter = None

# Structured Logging. basicConfig ensures a handler exists; the actual
# formatter (text or JSON per LOG_FORMAT) is applied below.
logging.basicConfig(
    level=log_level(),
    format="%(message)s",
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(RequestIdFilter())
    _handler.setFormatter(formatter())
logger = logging.getLogger(__name__)

# Pipeline state management (use Redis in production)
pipeline_state = {
    "current_stage": 0,
    "events_processed": 0,
    "comments_dispatched": 0,
    "reviews_created": 0,
}

# Security: Secret from environment only. Fail loud in non-development.
GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')
WEBHOOK_SECRET_IS_FALLBACK = False
if not GITHUB_WEBHOOK_SECRET:
    GITHUB_WEBHOOK_SECRET = secrets.token_hex(32)
    WEBHOOK_SECRET_IS_FALLBACK = True
    if os.environ.get('APP_ENV', 'development') != 'development':
        logger.error("GITHUB_WEBHOOK_SECRET must be set in non-development environments")
        raise RuntimeError("GITHUB_WEBHOOK_SECRET not set")
    logger.warning("GITHUB_WEBHOOK_SECRET not set! Using random fallback for development only.")

# Request ID middleware for tracing
@app.before_request
def before_request():
    g.request_id = request.headers.get('X-Request-ID', secrets.token_hex(8))
    g.start_time = time.time()
    logger.info(
        f"Request started",
        extra={
            'request_id': g.request_id,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
        }
    )

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time if hasattr(g, 'start_time') else 0
    logger.info(
        f"Request completed",
        extra={
            'request_id': g.request_id,
            'status': response.status_code,
            'duration_ms': round(duration * 1000, 2),
        }
    )
    # Add security headers
    response.headers['X-Request-ID'] = g.request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Error handlers
@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        "error": "Bad Request",
        "message": str(e.description) if hasattr(e, 'description') else "Invalid request",
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        "error": "Unauthorized",
        "message": "Authentication required",
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({
        "error": "Forbidden",
        "message": "Insufficient permissions",
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 403

@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({
        "error": "Payload Too Large",
        "message": f"Maximum payload size is {app.config['MAX_CONTENT_LENGTH']} bytes",
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 413

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({
        "error": "Rate Limit Exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": e.retry_after if hasattr(e, 'retry_after') else 60,
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}", exc_info=True)

    # Self-improvement: route the crash through the self error-handler with an
    # immediate escalate (no retry sleeps on the error path). It records the
    # error as memory and learns a reflex for next time.
    try:
        if 'get_engine' in globals() and 'RecoveryStrategy' in globals() and RecoveryStrategy is not None:
            _si_engine = get_engine()
            _si_engine.errors.handle(
                f"flask:{request.path}",
                e if isinstance(e, BaseException) else RuntimeError(str(e)),
                {"request_id": getattr(g, 'request_id', None)},
                RecoveryStrategy.ESCALATE,
            )
    except Exception as learning_err:
        logging.debug(f"Error-learning hook skipped: {learning_err}")

    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "request_id": g.request_id if hasattr(g, 'request_id') else None
    }), 500


# ── Pydantic Models for Input Validation ──────────────────────────────────────

if PYDANTIC_AVAILABLE:
    class WebhookPayload(BaseModel):
        event: str = Field(..., pattern=r"^pull_request$")
        action: str = Field(..., pattern=r"^(opened|synchronize|reopened|closed)$")
        repository: Dict[str, Any]
        pull_request: Dict[str, Any]
        installation: Dict[str, Any]

    class ASTSliceRequest(BaseModel):
        diff: str = Field(..., min_length=1, max_length=100000)

    class RAGRequest(BaseModel):
        scope: Dict[str, Any]

    class CritiqueRequest(BaseModel):
        findings: list = Field(..., min_items=1)

    class GitHubReviewRequest(BaseModel):
        pr_number: int = Field(..., gt=0)
        findings: list = Field(..., min_items=1)

    class ChatReplyRequest(BaseModel):
        comment_id: str = Field(..., min_length=1)

    class YAMLConfigRequest(BaseModel):
        config: str = Field(..., min_length=1)


# ── Helper Functions ──────────────────────────────────────────────────────────

def validate_signature(payload: bytes, signature: str) -> bool:
    """Validate X-Hub-Signature-256 HMAC-SHA256 with constant-time comparison."""
    if not signature or not signature.startswith('sha256='):
        return False
    mac = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature)


def is_bot_author(payload: dict) -> bool:
    """Check if the PR author is an automated bot."""
    user = payload.get("pull_request", {}).get("user", {})
    return user.get("type") == "Bot"


def extract_diff_metadata(payload: dict) -> dict:
    """Extract structured diff metadata from the webhook payload."""
    pr = payload.get("pull_request", {})
    return {
        "number": pr.get("number"),
        "base_sha": pr.get("base", {}).get("sha"),
        "head_sha": pr.get("head", {}).get("sha"),
        "diff_url": pr.get("diff_url"),
        "title": pr.get("title"),
    }


def generate_idempotency_key(payload: dict) -> str:
    """Generate cryptographically secure idempotency key."""
    repo_id = payload.get("repository", {}).get("id", 0)
    pr_number = payload.get("pull_request", {}).get("number", 0)
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "")
    # Add random component to prevent prediction
    return f"{repo_id}:{pr_number}:{head_sha}:{secrets.token_hex(8)}"


# ── Stage 1: Webhook Ingestion ──────────────────────────────────────────────

@app.route("/api/v1/webhook", methods=["POST"])
@limiter.limit("100 per minute") if limiter else lambda f: f
@rate_limit(100, 60)
def webhook():
    """Receive and validate GitHub pull_request webhooks."""
    # Validate content type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    # Get raw payload for HMAC validation
    payload_bytes = request.get_data()
    payload = request.get_json()

    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # HMAC signature validation
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature or not validate_signature(payload_bytes, signature):
        logger.warning(f"Invalid webhook signature", extra={'request_id': g.request_id})
        return jsonify({"error": "Invalid signature"}), 401

    # Validate payload structure
    if PYDANTIC_AVAILABLE:
        try:
            WebhookPayload(**payload)
        except ValidationError as e:
            return jsonify({"error": "Invalid payload structure", "details": e.errors()}), 400

    # Discard bot author events to prevent feedback loops
    if is_bot_author(payload):
        return jsonify({"status": "ignored", "reason": "bot_author"}), 202

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(payload)

    # Enqueue for processing (simulate Redis-backed queue)
    pipeline_state["events_processed"] += 1

    # Self-improvement: record the event + earn pattern-recognition XP.
    # Run off the request thread via the background pool (falls back to
    # synchronous execution if the pool is unavailable).
    try:
        if 'record_webhook' in globals():
            submit(record_webhook,
                   payload.get("repository", {}).get("full_name"),
                   payload.get("pull_request", {}).get("number"),
                   payload.get("action"))
    except Exception as e:
        logging.debug(f"Learning hook skipped: {e}")

    logger.info(f"Webhook accepted", extra={
        'request_id': g.request_id,
        'event_id': idempotency_key,
        'repo': payload.get("repository", {}).get("full_name"),
        'pr_number': payload.get("pull_request", {}).get("number"),
    })

    return jsonify({
        "status": "accepted",
        "event_id": idempotency_key,
        "diff_metadata": extract_diff_metadata(payload),
    }), 202


# ── Stage 2: Tree-sitter AST Diff Slicing ───────────────────────────────────

@app.route("/api/v1/ast-slice", methods=["POST"])
@limiter.limit("50 per minute") if limiter else lambda f: f
@rate_limit(50, 60)
def ast_slice():
    """Parse unified diff into Tree-sitter AST scopes."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if PYDANTIC_AVAILABLE:
        try:
            validated = ASTSliceRequest(**data)
            unified_diff = validated.diff
        except ValidationError as e:
            return jsonify({"error": "Invalid request", "details": e.errors()}), 400
    else:
        unified_diff = data.get("diff")
        if not unified_diff:
            return jsonify({"error": "Missing 'diff' field"}), 400

    slices = simulate_ast_parsing(unified_diff)

    return jsonify({
        "status": "success",
        "slices": slices,
        "total_modified_lines": sum(len(s["modified_lines"]) for s in slices),
    })


def simulate_ast_parsing(unified_diff: str) -> list:
    """Simulate Tree-sitter-based AST scope extraction from unified diff."""
    lines = unified_diff.split("\n")
    hunks = []
    current_hunk = None

    for line in lines:
        if line.startswith("@@"):
            parts = line.split(" ")
            if len(parts) >= 3:
                try:
                    old_info = parts[1].lstrip("-").split(",")
                    new_info = parts[2].lstrip("+").split(",")
                    old_start = int(old_info[0])
                    old_count = int(old_info[1]) if len(old_info) > 1 else 1
                    current_hunk = {
                        "old_start": old_start,
                        "old_count": old_count,
                        "modified_lines": [],
                    }
                    hunks.append(current_hunk)
                except (ValueError, IndexError):
                    continue
        elif current_hunk and line.startswith("+"):
            line_num = current_hunk["old_start"] + len(current_hunk["modified_lines"])
            current_hunk["modified_lines"].append(line_num)

    scopes = []
    for hunk in hunks:
        if hunk["modified_lines"]:
            scopes.append({
                "file_path": "unknown",
                "scope_type": "function_definition",
                "name": "unknown_function",
                "start_line": hunk["old_start"],
                "end_line": hunk["old_start"] + hunk["old_count"],
                "modified_lines": hunk["modified_lines"],
            })

    return scopes


# ── Stage 3: Contextual RAG & Caller Graphs ─────────────────────────────────

@app.route("/api/v1/rag", methods=["POST"])
@limiter.limit("30 per minute") if limiter else lambda f: f
@rate_limit(30, 60)
def rag():
    """Inject contextual codebase information into LLM prompts."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if PYDANTIC_AVAILABLE:
        try:
            validated = RAGRequest(**data)
            scope = validated.scope
        except ValidationError as e:
            return jsonify({"error": "Invalid request", "details": e.errors()}), 400
    else:
        scope = data.get("scope")
        if not scope:
            return jsonify({"error": "Missing 'scope' field"}), 400

    context = generate_contextual_knowledge(scope)

    return jsonify({
        "status": "success",
        "context": context,
        "callers": context.get("callers", []),
        "associated_tests": context.get("associated_tests", []),
        "repo_rules": context.get("repo_rules", {}),
    })


def generate_contextual_knowledge(scope: dict) -> dict:
    """Generate contextual knowledge for an AST scope."""
    file_path = scope.get("file_path", "unknown")
    name = scope.get("name", "unknown_function")
    modified_lines = scope.get("modified_lines", [])

    # Simulated vector DB lookup and caller resolution
    callers = []
    if "auth" in file_path.lower() or "jwt" in name.lower():
        callers = [
            {"file": "api/v1/routes.py", "line": 104, "sample": "verify_session_token(token)"}
        ]

    associated_tests = []
    if "test" in file_path.lower():
        associated_tests = [f"tests/test_{name.lower()}.py:test_{name.lower()}_changed"]

    repo_rules = {}
    try:
        with open(".coderabbit.yaml", "r") as f:
            import yaml
            config = yaml.safe_load(f)
            repo_rules = config.get("rules", {}) if config else {}
    except Exception:
        pass

    return {
        "target_symbol": name,
        "callers": callers,
        "associated_tests": associated_tests,
        "repo_rules": repo_rules,
        "dependency_graph": {
            "imports": ["import jwt", "from redis import Redis"],
            "dependents": ["api/v1/middleware.py:15"],
        },
    }


# ── Stage 4: Multi-Agent Critic Ensemble ────────────────────────────────────

@app.route("/api/v1/critique", methods=["POST"])
@limiter.limit("20 per minute") if limiter else lambda f: f
@rate_limit(20, 60)
def critique():
    """Run multi-agent LLM review on diff context."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if PYDANTIC_AVAILABLE:
        try:
            validated = CritiqueRequest(**data)
            findings = validated.findings
        except ValidationError as e:
            return jsonify({"error": "Invalid request", "details": e.errors()}), 400
    else:
        findings = data.get("findings")
        if not findings:
            return jsonify({"error": "Missing 'findings' field"}), 400

    structured_findings = simulate_critique_ensemble(findings)

    # Self-improvement: teach the model which categories to watch for
    try:
        if 'practice_on_request' in globals():
            practice_on_request("critique")
    except Exception as e:
        logging.debug(f"Critique learning hook skipped: {e}")

    return jsonify({
        "status": "success",
        "findings": structured_findings,
        "confidence_filtered": [f for f in structured_findings if f.get("confidence", 0) >= 0.85],
    })


def simulate_critique_ensemble(initial_findings: list) -> list:
    """Simulate specialized LLM critics: Security, Logic, Test Oracle."""
    findings = []

    for f in initial_findings:
        category = f.get("category", "")

        # Security critic
        if "security" in category.lower() or "inject" in category.lower():
            findings.append({
                "category": "security_vulnerability",
                "severity": "CRITICAL" if "critical" in category.lower() else "HIGH",
                "cwe": "CWE-89" if "sql" in category.lower() else "CWE-79",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": f.get("summary", "Security issue detected"),
                "confidence": 0.95,
                "code_patch": generate_patch_for_line(f.get("start_line", 0), "parameterize_input"),
            })

        # Logic critic
        elif "logic" in category.lower() or "edge" in category.lower() or "nil" in category.lower():
            findings.append({
                "category": "logic_bug",
                "severity": "HIGH",
                "cwe": "CWE-697",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "Logic edge case or nil pointer risk",
                "confidence": 0.88,
                "code_patch": generate_patch_for_line(f.get("start_line", 0), "add_null_check"),
            })

        # Test oracle
        elif "test" in category.lower() or "coverage" in category.lower():
            findings.append({
                "category": "test_coverage",
                "severity": "MEDIUM",
                "cwe": "N/A",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "May require new or modified unit tests",
                "confidence": 0.82,
                "code_patch": None,
            })

        # General code-style
        else:
            findings.append({
                "category": "code_style",
                "severity": "LOW",
                "cwe": "N/A",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "Code style suggestion (handled by linter)",
                "confidence": 0.65,
                "code_patch": None,
            })

    return findings


def generate_patch_for_line(line_num: int, patch_type: str) -> str:
    """Generate a code patch suggestion for a given line number."""
    patches = {
        "parameterize_input": 'row := db.QueryRow("SELECT id, name FROM users WHERE email = $1", params)',
        "add_null_check": "if x != nil { return x.method() }",
    }
    return patches.get(patch_type, "// TODO: apply appropriate fix")


# ── Stage 5: GitHub API Post & Conversational Bot ───────────────────────────

@app.route("/api/v1/github/review", methods=["POST"])
@limiter.limit("10 per minute") if limiter else lambda f: f
@rate_limit(10, 60)
@require_admin
def github_review():
    """Dispatch consolidated review comments to GitHub PR."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if PYDANTIC_AVAILABLE:
        try:
            validated = GitHubReviewRequest(**data)
            pr_number = validated.pr_number
            findings = validated.findings
        except ValidationError as e:
            return jsonify({"error": "Invalid request", "details": e.errors()}), 400
    else:
        if "findings" not in data or "pr_number" not in data:
            return jsonify({"error": "Missing required fields"}), 400
        pr_number = data["pr_number"]
        findings = data["findings"]

    # Filter to high-confidence findings only
    high_confidence = [f for f in findings if f.get("confidence", 0) >= 0.85]

    # Build GitHub Review API payload
    comments = []
    for finding in high_confidence:
        comment = {
            "path": finding.get("file_path", "modified_file.go"),
            "line": finding.get("start_line", 0),
            "body": f"**{finding['category'].replace('_', ' ').title()}**: {finding['summary']}",
            "side": "RIGHT",
            "body_html": f"<strong>{finding['category'].replace('_', ' ').title()}</strong>: {finding['summary']}",
        }
        comments.append(comment)

    review_payload = {
        "event": "COMMENT",
        "body": f"## Git-Fix Walkthrough\n\nIdentified {len(comments)} finding(s) in this PR.",
        "comments": comments,
    }

    pipeline_state["reviews_created"] += 1
    pipeline_state["comments_dispatched"] += len(comments)

    # Self-improvement: strongest learning signal — every dispatched review
    # teaches the engine what categories to watch for next time.
    try:
        if 'record_review_dispatched' in globals():
            record_review_dispatched(
                data.get("repo_full_name"),
                pr_number,
                findings,
                len(comments),
            )
    except Exception as e:
        logging.debug(f"Review learning hook skipped: {e}")

    logger.info(f"GitHub review dispatched", extra={
        'request_id': g.request_id,
        'pr_number': pr_number,
        'findings_count': len(comments),
    })

    return jsonify({
        "status": "review_dispatched",
        "pr_number": pr_number,
        "total_findings": len(findings),
        "high_confidence": len(high_confidence),
        "comments_posted": len(comments),
        "review_payload": review_payload,
    })


# ── Conversational reply handler ────────────────────────────────────────────

@app.route("/api/v1/chat/reply", methods=["POST"])
@limiter.limit("30 per minute") if limiter else lambda f: f
@rate_limit(30, 60)
@require_admin
def chat_reply():
    """Handle conversational follow-ups when developers reply to bot comments."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if PYDANTIC_AVAILABLE:
        try:
            validated = ChatReplyRequest(**data)
            comment_id = validated.comment_id
        except ValidationError as e:
            return jsonify({"error": "Invalid request", "details": e.errors()}), 400
    else:
        comment_id = data.get("comment_id")
        if not comment_id:
            return jsonify({"error": "Missing 'comment_id' field"}), 400

    return jsonify({
        "status": "reply_queued",
        "comment_id": comment_id,
        "response": "I can help regenerate that suggestion or answer follow-up questions about the change.",
    })


# ── Authentication ──────────────────────────────────────────────────────────

def _get_admin_credentials() -> tuple:
    username = os.environ.get("GITFIX_ADMIN_USERNAME", "admin")
    password = os.environ.get("GITFIX_ADMIN_PASSWORD", "")
    return username, password


def _authed_user_payload(payload: dict) -> dict:
    return {
        "id": payload.get("sub"),
        "username": payload.get("sub"),
        "email": "",
        "role": payload.get("role", "viewer"),
    }


@app.route("/api/v1/auth/login", methods=["POST"])
@rate_limit(10, 60)
def auth_login():
    if not security_ready():
        return jsonify({"error": "Auth not configured", "message": "Missing itsdangerous dependency"}), 503
    data = request.get_json(force=True, silent=True) or {}
    username = str(data.get("username") or data.get("email") or "")
    password = str(data.get("password") or "")
    admin_user, admin_pass = _get_admin_credentials()
    if not admin_pass:
        return jsonify({"error": "Auth not configured", "message": "Set GITFIX_ADMIN_PASSWORD"}), 503
    if not (hmac.compare_digest(username, admin_user) and hmac.compare_digest(password, admin_pass)):
        return jsonify({"error": "Unauthorized", "message": "Invalid credentials"}), 401
    access = create_token(admin_user, role="admin")
    refresh = create_token(admin_user, role="admin", ttl=604800)
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": admin_user, "username": admin_user, "email": "", "role": "admin"},
    })


@app.route("/api/v1/auth/refresh", methods=["POST"])
@rate_limit(10, 60)
def auth_refresh():
    if not security_ready():
        return jsonify({"error": "Auth not configured", "message": "Missing itsdangerous dependency"}), 503
    data = request.get_json(force=True, silent=True) or {}
    refresh_token = data.get("refresh_token")
    payload = verify_token(refresh_token)
    if not payload:
        return jsonify({"error": "Unauthorized", "message": "Invalid or expired token"}), 401
    access = create_token(payload.get("sub", "admin"), role=payload.get("role", "admin"))
    refresh = create_token(payload.get("sub", "admin"), role=payload.get("role", "admin"), ttl=604800)
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": _authed_user_payload(payload),
    })


@app.route("/api/v1/auth/me", methods=["GET"])
def auth_me():
    token = extract_token()
    payload = verify_token(token) if token else None
    if payload:
        return jsonify(_authed_user_payload(payload))
    if security_mod.AUTH_ENABLED:
        return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
    return jsonify({"id": None, "username": "anonymous", "email": "", "role": "viewer"})


# ── Health & status endpoints ───────────────────────────────────────────────

@app.route("/api/v1/health", methods=["GET"])
def health():
    """Health check endpoint with dependency checks."""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {
            "webhook_secret": "configured" if not WEBHOOK_SECRET_IS_FALLBACK else "using_fallback",
            "rate_limiter": "enabled" if limiter else "enabled",
            "security_headers": "enabled" if TALISMAN_AVAILABLE else "disabled",
            "input_validation": "enabled" if PYDANTIC_AVAILABLE else "disabled",
            "auth": "enabled" if security_mod.AUTH_ENABLED else "disabled",
        }
    }
    return jsonify(checks)


@app.route("/api/v1/status", methods=["GET"])
def status():
    return jsonify(pipeline_state)


@app.route("/api/v1/metrics", methods=["GET"])
def metrics():
    """Prometheus-style metrics endpoint."""
    return jsonify({
        "pipeline_events_processed": pipeline_state["events_processed"],
        "pipeline_comments_dispatched": pipeline_state["comments_dispatched"],
        "pipeline_reviews_created": pipeline_state["reviews_created"],
        "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else 0,
    })


# ── Self-Improvement API ──────────────────────────────────────────────────

try:
    from backend.self_improvement.api import self_improvement_bp, init_self_improvement
    from backend.self_improvement.pipeline_integration import (
        get_engine,
        record_webhook,
        record_review_dispatched,
        practice_on_request,
        maybe_consolidate,
        start_consolidator,
    )
    from backend.self_improvement.error_handling.core import RecoveryStrategy
    init_self_improvement(app)
    # Start the background memory consolidator daemon.
    start_consolidator()
except ImportError as e:
    logging.warning(f"Self-improvement module not available: {e}")


# ── Admin API ──────────────────────────────────────────────────────────────

try:
    from backend.admin.api import init_admin
    init_admin(app)
except ImportError as e:
    logging.warning(f"Admin API not available: {e}")


# ── Integrations API (notification webhook channels) ─────────────────────────

try:
    from backend.integrations.api import init_integrations
    init_integrations(app)
except ImportError as e:
    logging.warning(f"Integrations API not available: {e}")


# ── LLM Router API (auto-rotation AI provider gateway) ──────────────────────

try:
    from backend.llm.api import init_llm
    init_llm(app)
except ImportError as e:
    logging.warning(f"LLM router API not available: {e}")


# ── AI Agent Team API (collaborative agent panel) ───────────────────────────

try:
    from backend.agents.api import init_agents
    init_agents(app)
except ImportError as e:
    logging.warning(f"AI Agent Team API not available: {e}")


# ── Run the app ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.start_time = time.time()
    # Only enable debug in development
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)