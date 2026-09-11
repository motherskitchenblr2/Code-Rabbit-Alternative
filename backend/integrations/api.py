# =============================================================================
# Integrations API blueprint -- notification webhook channels (Slack/Discord)
# =============================================================================
# Complements backend/admin/api.py, which owns platform access tokens (GitHub,
# GitLab, Bitbucket, Azure DevOps). This blueprint manages outbound notification
# webhooks so the Settings -> Integrations UI can persist real channel endpoints
# and verify them with a live ping. All routes are admin-gated; URLs are masked
# on read so webhook secrets never leak through the UI.
# =============================================================================

import time
import uuid
import logging
from typing import Any, Dict, Optional

from flask import Blueprint, request, jsonify
try:
    import requests as http_client
except ImportError:  # pragma: no cover - requests is a declared dependency
    http_client = None

from backend.security import require_admin
from backend.admin.store import get_store, MASK_PLACEHOLDER

logger = logging.getLogger(__name__)

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")

PING_TIMEOUT = 8  # seconds; keep ping tests snappy

_KNOWN_KINDS: Dict[str, str] = {
    "slack": "Slack",
    "discord": "Discord",
    "custom": "Custom Webhook",
}


def _mask_url(url: Optional[str]) -> str:
    if not url:
        return ""
    if len(url) <= 8:
        return MASK_PLACEHOLDER
    return f"{MASK_PLACEHOLDER}{url[-8:]}"


def _public_webhook(item: Dict[str, Any]) -> Dict[str, Any]:
    kind = item.get("kind", "custom")
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": kind,
        "channel": _KNOWN_KINDS.get(kind, kind),
        "url_set": bool(item.get("url")),
        "url_tail": _mask_url(item.get("url")),
        "enabled": bool(item.get("enabled", True)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


# ── Webhook configs ─────────────────────────────────────────────────────────

@integrations_bp.route("/webhooks", methods=["GET"])
@require_admin
def list_webhooks():
    return jsonify({"webhooks": [_public_webhook(w) for w in get_store().list_webhook_configs()]})


@integrations_bp.route("/webhooks", methods=["POST"])
@require_admin
def upsert_webhook():
    data = request.get_json(force=True, silent=True) or {}
    kind = str(data.get("kind") or "").strip().lower()
    if kind not in _KNOWN_KINDS:
        return jsonify({"error": f"unsupported kind: {kind}"}), 400
    name = str(data.get("name") or "").strip() or _KNOWN_KINDS[kind]

    existing = None
    wid = data.get("id")
    if wid:
        existing = get_store().get_webhook_config(wid)
    if existing is None:
        wid = str(wid or "").strip() or uuid.uuid4().hex[:12]

    url = str(data.get("url") or "").strip()
    # If the client is echoing the masked tail only, keep the stored URL.
    if existing and existing.get("url") and _mask_url(url) == url:
        url = existing.get("url")
    if not url:
        return jsonify({"error": "url is required"}), 400
    if not (url.startswith("https://") or url.startswith("http://")):
        return jsonify({"error": "url must be an http(s) endpoint"}), 400

    now = time.time()
    cfg = {
        "id": wid,
        "name": name,
        "kind": kind,
        "url": url,
        "enabled": bool(data.get("enabled", True)) if "enabled" in data else (existing.get("enabled", True) if existing else True),
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    saved = get_store().upsert_webhook_config(cfg)

    # Auto-ping whenever a webhook is (re)configured so the modal shows live status.
    response = _public_webhook(saved)
    response["probe"] = _ping_webhook(saved)
    return jsonify(response), 200


@integrations_bp.route("/webhooks/<webhook_id>", methods=["DELETE"])
@require_admin
def delete_webhook(webhook_id: str):
    if get_store().delete_webhook_config(webhook_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


@integrations_bp.route("/webhooks/<webhook_id>/test", methods=["POST"])
@require_admin
def test_webhook(webhook_id: str):
    cfg = get_store().get_webhook_config(webhook_id)
    if cfg is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"result": _ping_webhook(cfg)})


def _ping_webhook(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort connectivity ping that posts a formatted test message."""
    if http_client is None:
        return {"ok": False, "status": None, "detail": "requests library unavailable"}
    url = cfg.get("url", "")
    if not url:
        return {"ok": False, "status": None, "detail": "No webhook URL saved yet"}

    kind = cfg.get("kind", "custom")
    payload: Dict[str, str] = {"text": "Git-Fix: webhook connected"}
    if kind == "discord":
        payload = {"content": "Git-Fix: webhook connected"}
    elif kind == "custom":
        payload = {"message": "Git-Fix: webhook connected"}

    try:
        r = http_client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=PING_TIMEOUT)
    except Exception as exc:
        return {"ok": False, "status": None, "detail": f"Connection failed: {exc.__class__.__name__}"}
    if 200 <= r.status_code < 300:
        return {"ok": True, "status": r.status_code, "detail": "Webhook ping delivered"}
    if r.status_code in (401, 403):
        return {"ok": False, "status": r.status_code, "detail": "Webhook URL rejected (bad permissions)"}
    if r.status_code == 404:
        return {"ok": False, "status": r.status_code, "detail": "Webhook URL not found (verify endpoint)"}
    return {"ok": False, "status": r.status_code, "detail": f"Unexpected HTTP {r.status_code}"}


def init_integrations(app) -> None:
    """Register the integrations blueprint."""
    app.register_blueprint(integrations_bp)
    logger.info("Integrations API mounted at /api/v1/integrations")