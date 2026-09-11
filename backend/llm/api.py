# =============================================================================
# LLM Router API blueprint
# =============================================================================
# /api/v1/llm/* — task-aware auto-rotation completions, provider health, and
# an endpoint the Agent Builder can drive directly ("Auto API Call system").
# =============================================================================

import logging
from typing import Any, Dict, List

from flask import Blueprint, request, jsonify

from backend.security import require_auth
from .router import get_router, TASK_TYPES, TASK_LABELS

logger = logging.getLogger(__name__)

llm_bp = Blueprint("llm", __name__, url_prefix="/api/v1/llm")

_MAX_MESSAGES = 200
_SYS_PROMPT_MAX = 200_000


def _clean_messages(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for item in raw[: _MAX_MESSAGES]:
        if isinstance(item, dict):
            role = str(item.get("role") or "user")
            content = item.get("content")
            if content is None:
                continue
            text = content if isinstance(content, str) else json_dumps(content)
            # Strip binary / non-text content blocks for multimodal-safe chat.
            out.append({"role": role if role in ("system", "user", "assistant") else "user", "content": text})
    return out


def json_dumps(value: Any) -> str:
    import json
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


@llm_bp.route("/status", methods=["GET"])
@require_auth
def llm_status():
    """Provider health + per-task routing table (no secrets)."""
    return jsonify(get_router().snapshot())


@llm_bp.route("/tasks", methods=["GET"])
def llm_tasks():
    """List supported router task types (public — the Agent Builder uses this)."""
    return jsonify({"tasks": [{"id": t, "label": TASK_LABELS[t]} for t in TASK_TYPES]})


@llm_bp.route("/complete", methods=["POST"])
@require_auth
def llm_complete():
    """One auto-rotating chat completion.

    Body: {task?, model?, messages, max_tokens?, temperature?}
    Task is optional; when omitted the router introspects the request and
    picks a sensible default (chat).
    """
    data = request.get_json(force=True, silent=True) or {}
    messages = _clean_messages(data.get("messages"))
    if not messages:
        return jsonify({"error": "messages[].content is required"}), 400

    task = str(data.get("task") or "chat")
    if task not in TASK_TYPES:
        task = "chat"

    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    if len(system) > _SYS_PROMPT_MAX:
        messages = [m for m in messages if m.get("role") != "system"] + [
            {"role": "system", "content": system[:_SYS_PROMPT_MAX]}
        ]

    result = get_router().complete(
        messages,
        task=task,
        model=str(data.get("model") or "").strip() or None,
        max_tokens=int(data.get("max_tokens") or 1024),
        temperature=float(data.get("temperature") or 0.3),
    )
    status_code = 200 if result.get("ok") else 502
    return jsonify(result), status_code


# /api/v1/llm/models
@llm_bp.route("/models", methods=["GET"])
@require_auth
def llm_models():
    """All models a configured provider can serve, grouped by provider."""
    snapshot = get_router().snapshot()
    from .catalog import PROVIDER_META, task_model_for

    models: Dict[str, Any] = {}
    for pid in PROVIDER_META:
        meta = PROVIDER_META[pid]
        models[pid] = {
            "name": meta["name"],
            "tasks": {t: task_model_for(pid, t) for t in TASK_TYPES},
        }
    return jsonify({"providers": models, "routing": snapshot.get("routing", {})})


def init_llm(app) -> None:
    app.register_blueprint(llm_bp)
    logger.info("LLM router API mounted at /api/v1/llm")