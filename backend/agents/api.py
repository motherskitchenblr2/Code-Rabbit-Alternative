# =============================================================================
# AI Agent Team API blueprint
# =============================================================================
#   POST   /api/v1/agents/sessions          -> start a team working session
#   GET    /api/v1/agents/sessions          -> list recent sessions
#   GET    /api/v1/agents/sessions/<id>     -> live snapshot (status/transcript)
#   POST   /api/v1/agents/sessions/<id>/message   -> user replies to the team
#   POST   /api/v1/agents/sessions/<id>/stop     -> abort the current round
#   GET    /api/v1/agents/sessions/<id>/attachments/<filename> -> download
#
# The create/message endpoints accept JSON ({"request"|"message": ...}) or
# multipart/form-data (fields "request"|"message" plus one or more files under
# any field name) so the chat UI can attach files, images, and voice notes.
# =============================================================================

import logging
import os
import uuid
from typing import Any, Dict

from flask import Blueprint, request, jsonify, send_file

from backend.security import require_auth
from . import team as team_mod
from .team import (
    AGENTS,
    start_session,
    get_session,
    list_sessions,
    reply_to_session,
    save_attachments,
    find_attachment_meta,
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


def _uploaded_files():
    """All FileStorage objects from a multipart request."""
    return [f for key in request.files.keys() for f in request.files.getlist(key)]


def _request_text(field: str) -> str:
    """Extract the single text field from JSON or multipart payloads."""
    if request.files:
        return str(request.form.get(field, "") or "").strip()
    data = request.get_json(force=True, silent=True) or {}
    return str(data.get(field) or "").strip()


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
    has_files = bool(request.files)
    request_text = _request_text("request")
    if not request_text and not has_files:
        return jsonify({"error": "request is required"}), 400
    if len(request_text) > 4000:
        return jsonify({"error": "request too long (max 4000 chars)"}), 400

    sid = uuid.uuid4().hex[:12]
    try:
        attachments = save_attachments(sid, _uploaded_files()) if has_files else []
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    session = start_session(
        request_text or "Shared attachments",
        attachments=attachments,
        session_id=sid,
    )
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
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "not found"}), 404

    has_files = bool(request.files)
    content = _request_text("message")
    try:
        attachments = save_attachments(session_id, _uploaded_files()) if has_files else []
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not content and not attachments:
        return jsonify({"error": "message is required"}), 400
    if len(content) > 4000:
        return jsonify({"error": "message too long (max 4000 chars)"}), 400

    updated = reply_to_session(session_id, content, attachments=attachments)
    if updated is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"session": updated.snapshot()}), 200


@agents_bp.route("/sessions/<session_id>/attachments/<path:filename>", methods=["GET"])
@require_auth
def session_attachment(session_id: str, filename: str):
    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "not found"}), 404
    safe = os.path.basename(filename or "")
    if not safe:
        return jsonify({"error": "not found"}), 404
    path = team_mod.UPLOADS_PATH / session_id / safe
    if not path.is_file():
        return jsonify({"error": "not found"}), 404

    meta = find_attachment_meta(session, safe) or {}
    mime = str(meta.get("mime") or "application/octet-stream")
    if meta.get("kind") in ("image", "audio"):
        # Inline so <img> and <audio> render directly; dangerous types are
        # classified as "file" (download-only) server-side.
        return send_file(path, mimetype=mime, conditional=True)
    return send_file(
        path,
        mimetype=mime,
        as_attachment=True,
        download_name=str(meta.get("name") or safe),
    )


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