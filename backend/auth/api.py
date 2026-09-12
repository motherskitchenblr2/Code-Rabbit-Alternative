# =============================================================================
# User auth & account API (Settings → Security tab)
# =============================================================================
# Routes under /api/v1/auth: password change, 2FA (TOTP) enrollment, user API
# keys for automation, and active-session management (list / revoke).
# =============================================================================

import hmac
import logging
import re
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from backend.security import require_admin, extract_token
from backend.auth.store import account_store, fingerprint

logger = logging.getLogger(__name__)

auth_bp = Blueprint("account", __name__, url_prefix="/api/v1/auth")


def _request_json() -> Dict[str, Any]:
    return request.get_json(force=True, silent=True) or {}


def _device_label(user_agent: str) -> str:
    ua = user_agent or ""
    browser = re.search(r"(Firefox|Chrome|Safari|Edge|OPR)[/\s]?[\d.]*", ua)
    browser = browser.group(1) if browser else "Browser"
    os_match = re.search(r"(Android|iOS|iPhone|Mac OS X|Windows|Linux|Ubuntu|CrOS)", ua)
    os_name = os_match.group(1).replace("Mac OS X", "macOS") if os_match else "Unknown OS"
    return f"{browser} on {os_name}"


def _public_session(s: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": s.get("id"),
        "device": _device_label(s.get("user_agent")),
        "created_at": s.get("created_at"),
        "last_active": s.get("last_active"),
        "expires_at": s.get("expires_at"),
        "revoked": bool(s.get("revoked")),
    }


# ── 2FA / TOTP ─────────────────────────────────────────────────────────────

@auth_bp.route("/2fa/status", methods=["GET"])
@require_admin
def totp_status():
    store = account_store()
    return jsonify({
        "enabled": store.totp_enabled(),
        "secret": None,
        "otpauth_uri": None,
        "digits": 6,
        "period": 30,
    })


@auth_bp.route("/2fa/setup", methods=["POST"])
@require_admin
def totp_setup():
    store = account_store()
    if store.totp_enabled():
        return jsonify({"error": "2FA is already enabled"}), 409
    secret = store.totp_secret()
    if not secret:
        from backend.auth import totp

        secret = totp.generate_secret()
        store.set_totp_secret(secret)
    return jsonify({
        "enabled": False,
        "secret": secret,
        "otpauth_uri": store.totp_uri(secret),
        "digits": 6,
        "period": 30,
    })


@auth_bp.route("/2fa/enable", methods=["POST"])
@require_admin
def totp_enable():
    data = _request_json()
    code = data.get("code")
    store = account_store()
    if store.totp_enabled():
        return jsonify({"error": "2FA is already enabled"}), 409
    secret = store.totp_secret()
    if not secret:
        return jsonify({"error": "Run setup first"}), 400
    if not store.verify_totp_enrollment(secret, code):
        return jsonify({"error": "Invalid authenticator code"}), 400
    store.enable_totp()
    return jsonify({"enabled": True})


@auth_bp.route("/2fa/disable", methods=["POST"])
@require_admin
def totp_disable():
    data = _request_json()
    store = account_store()
    if not store.totp_enabled():
        return jsonify({"error": "2FA is not enabled"}), 409
    if not store.verify_totp_code(data.get("code")):
        return jsonify({"error": "Invalid authenticator code"}), 400
    store.disable_totp()
    return jsonify({"enabled": False})


# ── password ────────────────────────────────────────────────────────────────

@auth_bp.route("/password", methods=["POST"])
@require_admin
def change_password():
    data = _request_json()
    current = str(data.get("current_password") or "")
    new = str(data.get("new_password") or "")
    if len(new) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400
    if len(new) > 128:
        return jsonify({"error": "New password is too long"}), 400
    store = account_store()
    if store.has_password():
        if not store.verify_password(current):
            return jsonify({"error": "Current password is incorrect"}), 400
    else:
        from backend.app import _get_admin_credentials  # circular-safe late import
        admin_user, admin_pass = _get_admin_credentials()
        username = str(data.get("username") or admin_user)
        if not (admin_pass and hmac.compare_digest(username, admin_user)
                and hmac.compare_digest(current, admin_pass)):
            return jsonify({"error": "Current password is incorrect"}), 400
    store.set_password(new)
    return jsonify({"ok": True})


# ── user API keys ───────────────────────────────────────────────────────────

@auth_bp.route("/api-keys", methods=["GET"])
@require_admin
def api_keys_list():
    return jsonify({"keys": account_store().list_api_keys()})


@auth_bp.route("/api-keys", methods=["POST"])
@require_admin
def api_keys_create():
    data = _request_json()
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    created = account_store().create_api_key(name)
    return jsonify(created), 201


@auth_bp.route("/api-keys/<key_id>", methods=["DELETE"])
@require_admin
def api_keys_delete(key_id: str):
    if not account_store().delete_api_key(key_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ── active sessions ─────────────────────────────────────────────────────────

@auth_bp.route("/sessions", methods=["GET"])
@require_admin
def sessions_list():
    store = account_store()
    current_fp = fingerprint(extract_token() or "")
    sessions = []
    for raw in store.list_sessions():
        item = _public_session(raw)
        item["current"] = current_fp in raw.get("fingerprints", [])
        sessions.append(item)
    return jsonify({"sessions": sorted(sessions, key=lambda s: s["created_at"] or 0, reverse=True)})


@auth_bp.route("/sessions/revoke", methods=["POST"])
@require_admin
def sessions_revoke():
    data = _request_json()
    session_id = str(data.get("id") or "")
    if not session_id:
        return jsonify({"error": "Session id is required"}), 400
    if not account_store().revoke_session(session_id):
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"ok": True})


@auth_bp.route("/sessions/revoke-all", methods=["POST"])
@require_admin
def sessions_revoke_all():
    current_fp = fingerprint(extract_token() or "")
    revoked = account_store().revoke_all_except(current_fp)
    return jsonify({"ok": True, "revoked": revoked})


def init_auth(app) -> None:
    app.register_blueprint(auth_bp)