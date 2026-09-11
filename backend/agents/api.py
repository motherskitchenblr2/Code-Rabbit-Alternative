# =============================================================================
# AI Agent Team API blueprint
# =============================================================================
#   POST   /api/v1/agents/sessions          -> start a team working session
#   GET    /api/v1/agents/sessions          -> list recent sessions
#   GET    /api/v1/agents/sessions/<id>     -> live snapshot (status/transcript)
#   POST   /api/v1/agents/sessions/<id>/message   -> user replies to the team
#   POST   /api/v1/agents/sessions/<id>/stop     -> abort the current round
# =============================================================================

import logging
from typing import Any, Dict

from flask import Blueprint, request, jsonify

from backend.security import require_auth
from .team import (
    AGENTS,
    start_session,
    get_session,
    list_sessions,
    reply_to_session,
)

logger = logging.getLogger(__name__)

agents_bp = Blueprint("agents", __name__, url_prefix="/api/v1/agents")


def _roster_public() -> Dict[str, Any]:
    return {
        "agents": [
            {
                "id": a["id"],
                "name": a["name"],
                "title": a["title"],
                "tagline": a["tagline"],
            }
            for a in AGENTS
        ]
    }


@agents_bp.route("/roster", methods=["GET"])
@require_auth
def roster():
    return jsonify(_roster_public())


@agents_bp.route("/sessions", methods=["GET"])
@require_auth
def sessions_list():
    return jsonify({"sessions": list_sessions(limit=15)})


@agents_bp.route("/sessions", methods=["POST"])
@require_auth
def sessions_create():
    data = request.get_json(force=True, silent=True) or {}
    request_text = str(data.get("request") or "").strip()
    if not request_text:
        return jsonify({"error": "request is required"}), 400
    if len(request_text) > 4000:
        return jsonify({"error": "request too long (max 4000 chars)"}), 400

    session = start_session(request_text)
    return jsonify({"session": session.snapshot()}), 201


@agents_bp.route("/sessions/<session_id>", methods=["GET"])
@require_auth
def session_get(session_id: str):
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"session": session.snapshot()})


@agents_bp.route("/sessions/<session_id>/message", methods=["POST"])
@require_auth
def session_message(session_id: str):
    data = request.get_json(force=True, silent=True) or {}
    content = str(data.get("message") or "").strip()
    if not content:
        return jsonify({"error": "message is required"}), 400

    session = reply_to_session(session_id, content)
    if session is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"session": session.snapshot()}), 200


@agents_bp.route("/sessions/<session_id>/stop", methods=["POST"])
@require_auth
def session_stop(session_id: str):
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "not found"}), 404
    session.stop()
    return jsonify({"session": session.snapshot()}), 200


def init_agents(app) -> None:
    """Register the agents blueprint."""
    app.register_blueprint(agents_bp)
    # Warm-restore any persisted sessions at boot (never blocks HTTP).
    try:
        from .team import list_sessions
        list_sessions(limit=1)
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("Agent registry warm-up skipped: %s", exc)
    logger.info("AI Agent Team API mounted at /api/v1/agents")