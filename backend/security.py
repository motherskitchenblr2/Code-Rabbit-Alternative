# =============================================================================
# Git-Fix Security Helpers
# =============================================================================
# Shared stdlib: rate limiting, HMAC session tokens, auth decorators.
# All enforcement is gated behind AUTH_ENABLED / RATE_LIMITER_AVAILABLE so the
# default deployment behaviour is byte-for-byte identical to before.
# =============================================================================

import hashlib
import os
import secrets
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

# Globally revoked token fingerprints (in-memory; persisted session revocations
# live in the account store). Kept here as a module-level set so the vanilla
# single-worker deploy and threaded test clients share revocations.
_REVOKED_TOKENS: set = set()


def fingerprint(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def revoke_token(token: str, reason: Optional[str] = None) -> None:
    """Hard-revoke an access/refresh token without touching the session store."""
    if token:
        _REVOKED_TOKENS.add(fingerprint(token))


def init_security(secret_key: Optional[str] = None, auth_enabled: Optional[bool] = None):
    global _security_secret, AUTH_ENABLED
    _security_secret = secret_key
    if auth_enabled is None:
        # Resolve at init time (after load_env) so .env / exported vars take effect.
        auth_enabled = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
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
    payload = {"sub": identity, "role": role, "jti": secrets.token_hex(6)}
    return serializer.dumps(payload)


def verify_token(token: str, max_age: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not token or not security_ready():
        return None
    if fingerprint(token) in _REVOKED_TOKENS:
        return None
    serializer = URLSafeTimedSerializer(_security_secret, salt=_SALT)
    try:
        payload = serializer.loads(token, max_age=max_age or _REFRESH_TTL)
    except (BadSignature, SignatureExpired, Exception):
        return None
    if _session_revoked(fingerprint(token)):
        return None
    return payload


def _session_revoked(fp: str) -> bool:
    try:
        from backend.auth.store import account_store

        return account_store().is_revoked(fp)
    except Exception:
        return False


def extract_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    header = request.headers.get("X-Auth-Token")
    if header:
        return header.strip()
    # Query-param fallback used by media download URLs (<img>/<audio> tags
    # cannot carry Authorization headers).
    return (request.args.get("token") or request.args.get("access_token") or "").strip() or None


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


def _touch_session(fp: str) -> None:
    try:
        from backend.auth.store import account_store

        account_store().touch_session(fp)
    except Exception as exc:
        logger.warning(f"Could not touch session: {exc}")


def _authenticate_api_key() -> Optional[Dict[str, Any]]:
    api_key = request.headers.get("X-API-Key") or request.args.get("api_key") or ""
    if not api_key:
        return None
    try:
        from backend.auth.store import account_store, AccountStore
    except Exception:
        return None
    record = account_store().get_api_key_record(AccountStore.hash_api_key(api_key))
    if not record:
        return None
    account_store().touch_api_key(record.get("id"))
    return {
        "sub": f"key:{record.get('name', 'api-key')}",
        "role": "admin",
        "auth_source": "api_key",
        "key_id": record.get("id"),
    }


def _authenticate() -> Optional[Dict[str, Any]]:
    token = extract_token()
    if token:
        payload = verify_token(token)
        if payload:
            g.auth_source = "token"
            _touch_session(fingerprint(token))
            return payload
    api_payload = _authenticate_api_key()
    if api_payload:
        g.auth_source = "api_key"
        return api_payload
    return None


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
    "revoke_token",
    "fingerprint",
]