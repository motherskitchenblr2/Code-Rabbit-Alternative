# =============================================================================
# Git-Fix Security Helpers
# =============================================================================
# Shared stdlib: rate limiting, HMAC session tokens, auth decorators.
# All enforcement is gated behind AUTH_ENABLED / RATE_LIMITER_AVAILABLE so the
# default deployment behaviour is byte-for-byte identical to before.
# =============================================================================

import os
import time
import threading
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable

from flask import request, jsonify, g

logger = logging.getLogger(__name__)

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

try:
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    ITS_DANGEROUS_AVAILABLE = True
except ImportError:
    ITS_DANGEROUS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Runtime configuration (set once from app.py)
# ---------------------------------------------------------------------------
_security_secret: Optional[str] = None
AUTH_ENABLED: bool = os.environ.get("AUTH_ENABLED", "false").lower() == "true"


def init_security(secret_key: Optional[str] = None, auth_enabled: Optional[bool] = None):
    global _security_secret, AUTH_ENABLED
    _security_secret = secret_key
    if auth_enabled is not None:
        AUTH_ENABLED = bool(auth_enabled)


def security_ready() -> bool:
    return bool(_security_secret) and ITS_DANGEROUS_AVAILABLE


# ---------------------------------------------------------------------------
# Stdlib rate limiting (sliding window, thread-safe, in-memory)
# ---------------------------------------------------------------------------
_ratelimit_lock = threading.Lock()
_ratelimit_buckets: Dict[tuple, list] = {}


def _client_key() -> tuple:
    return (request.remote_addr or "unknown", request.path)


def rate_limit(limit: int, period: int = 60) -> Callable:
    """In-memory sliding-window rate limiter.

    No-op when flask_limiter is installed so deployments that already use the
    full limiter keep exactly the same behaviour; on minimal setups it still
    provides real protection.
    """
    def _passthrough(f):
        return f

    if RATE_LIMITER_AVAILABLE:
        return _passthrough

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = _client_key()
            now = time.monotonic()
            with _ratelimit_lock:
                hits = _ratelimit_buckets.setdefault(key, [])
                window_start = now - period
                hits[:] = [t for t in hits if t > window_start]
                if len(hits) >= limit:
                    return jsonify({
                        "error": "Rate Limit Exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": period,
                        "request_id": getattr(g, "request_id", None),
                    }), 429
                hits.append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# HMAC session tokens (itsdangerous)
# ---------------------------------------------------------------------------
_SALT = "gitfix-auth"
_ACCESS_TTL = 3600
_REFRESH_TTL = 7 * 24 * 3600


def create_token(identity: str, role: str = "admin", ttl: Optional[int] = None) -> str:
    if not security_ready():
        raise RuntimeError("Security not initialized")
    serializer = URLSafeTimedSerializer(_security_secret, salt=_SALT)
    return serializer.dumps({"sub": identity, "role": role})


def verify_token(token: str, max_age: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not token or not security_ready():
        return None
    serializer = URLSafeTimedSerializer(_security_secret, salt=_SALT)
    try:
        return serializer.loads(token, max_age=max_age or _REFRESH_TTL)
    except (BadSignature, SignatureExpired, Exception):
        return None


def extract_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return request.headers.get("X-Auth-Token")


# ---------------------------------------------------------------------------
# Auth decorators (no-op unless AUTH_ENABLED=true)
# ---------------------------------------------------------------------------
def _unauthorized(msg: str = "Authentication required") -> "_Response":
    return jsonify({
        "error": "Unauthorized",
        "message": msg,
        "request_id": getattr(g, "request_id", None),
    }), 401


def _forbidden(msg: str = "Insufficient permissions") -> "_Response":
    return jsonify({
        "error": "Forbidden",
        "message": msg,
        "request_id": getattr(g, "request_id", None),
    }), 403


def _authenticate() -> Optional[Dict[str, Any]]:
    token = extract_token()
    if not token:
        return None
    return verify_token(token)


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        payload = _authenticate()
        if not payload:
            return _unauthorized()
        g.auth_user = payload
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        payload = _authenticate()
        if not payload:
            return _unauthorized()
        if payload.get("role") != "admin":
            return _forbidden()
        g.auth_user = payload
        return f(*args, **kwargs)
    return wrapper


__all__ = [
    "RATE_LIMITER_AVAILABLE",
    "ITS_DANGEROUS_AVAILABLE",
    "AUTH_ENABLED",
    "init_security",
    "security_ready",
    "rate_limit",
    "create_token",
    "verify_token",
    "extract_token",
    "require_auth",
    "require_admin",
]