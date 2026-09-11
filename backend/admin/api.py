# =============================================================================
# Admin API blueprint -- manage AI providers, MCP servers, and access tokens
# =============================================================================
# All routes are admin-gated (require_admin). Secret fields are accepted on
# write but masked on read so credentials never leak through the Admin UI.
# "Test connection" probes are best-effort (short timeout) and never block.
# =============================================================================

import os
import time
import uuid
import logging
import shutil
from typing import Any, Dict, Optional

from flask import Blueprint, request, jsonify
try:
    import requests as http_client
except ImportError:  # pragma: no cover - requests is a declared dependency
    http_client = None

from backend.security import require_admin
from .store import get_store, MASK_PLACEHOLDER

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")

PROBE_TIMEOUT = 6  # seconds; keep connection tests snappy
_KNOWN_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "multimodal": True,
        "models": True,
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "multimodal": True,
        "models": False,  # no public models list; token -> POST /messages required
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "multimodal": True,
        "models": True,
        "auth_key": "x-goog-api-key",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "multimodal": False,
        "models": True,
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "multimodal": True,
        "models": True,
    },
    "huggingface": {
        "name": "Hugging Face",
        "base_url": "https://api-inference.huggingface.co",
        "multimodal": True,
        "models": False,
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "multimodal": False,
        "models": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "multimodal": False,
        "models": False,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434",
        "multimodal": True,
        "models": True,
        "auth": None,
    },
    "nvidia": {
        "name": "NVIDIA",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "multimodal": False,
        "models": True,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "multimodal": True,
        "models": True,
    },

    "perplexity": {
        "name": "Perplexity",
        "base_url": "https://api.perplexity.ai",
        "multimodal": False,
        "models": False,
    },
}


def _mask(secret: Optional[str]) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return MASK_PLACEHOLDER
    return f"{MASK_PLACEHOLDER}{secret[-4:]}"


def _public_provider(item: Dict[str, Any]) -> Dict[str, Any]:
    known = _KNOWN_PROVIDERS.get(item.get("id", ""), {})
    return {
        "id": item.get("id"),
        "name": item.get("name") or known.get("name") or item.get("id"),
        "base_url": item.get("base_url") or known.get("base_url", ""),
        "multimodal": bool(item.get("multimodal", known.get("multimodal", False))),
        "enabled": bool(item.get("enabled", True)),
        "model": item.get("model", ""),
        "api_key_set": bool(item.get("api_key")),
        "api_key_tail": _mask(item.get("api_key")),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def _public_server(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "transport": item.get("transport", "stdio"),
        "command": item.get("command"),
        "args": item.get("args", []),
        "url": item.get("url"),
        "env_set": bool(item.get("env")),
        "enabled": bool(item.get("enabled", True)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def _public_token(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "platform": item.get("platform"),
        "scopes": item.get("scopes", []),
        "enabled": bool(item.get("enabled", True)),
        "token_set": bool(item.get("token")),
        "token_tail": _mask(item.get("token")),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


# ── Overview ────────────────────────────────────────────────────────────────

@admin_bp.route("/overview", methods=["GET"])
@require_admin
def admin_overview():
    store = get_store()
    document = store.get_doc()
    providers = document.get("ai_providers", [])
    servers = document.get("mcp_servers", [])
    tokens = document.get("access_tokens", [])
    return jsonify({
        "ai_providers": {
            "total": len(providers),
            "enabled": sum(1 for p in providers if p.get("enabled", True)),
            "configured": sum(1 for p in providers if p.get("api_key")),
        },
        "mcp_servers": {
            "total": len(servers),
            "enabled": sum(1 for s in servers if s.get("enabled", True)),
        },
        "access_tokens": {
            "total": len(tokens),
            "enabled": sum(1 for t in tokens if t.get("enabled", True)),
            "configured": sum(1 for t in tokens if t.get("token")),
        },
        "auth_enabled": os.environ.get("AUTH_ENABLED", "false").lower() == "true",
    })


# ── AI Providers ────────────────────────────────────────────────────────────

@admin_bp.route("/providers", methods=["GET"])
@require_admin
def list_providers():
    store = get_store()
    return jsonify({"providers": [_public_provider(p) for p in store.list_ai_providers()]})


@admin_bp.route("/providers", methods=["POST"])
@require_admin
def create_provider():
    data = request.get_json(force=True, silent=True) or {}
    pid = str(data.get("id") or "").strip().lower()
    if not pid:
        return jsonify({"error": "id is required"}), 400
    if not re_valid_id(pid):
        return jsonify({"error": "id may only contain letters, numbers, '_' and '-'"}), 400

    known = _KNOWN_PROVIDERS.get(pid, {})
    now = time.time()
    api_key = data.get("api_key")
    existing = get_store().get_ai_provider(pid)
    # If the client is echoing the masked tail only, keep the stored key.
    if existing and existing.get("api_key") and (not api_key or _mask(api_key) == api_key):
        api_key = existing.get("api_key")

    provider = {
        "id": pid,
        "name": data.get("name") or known.get("name") or pid,
        "base_url": (data.get("base_url") or known.get("base_url") or "").strip(),
        "model": (data.get("model") or "").strip(),
        "multimodal": data.get("multimodal", known.get("multimodal", False)),
        "enabled": bool(data.get("enabled", True)),
        "api_key": api_key or "",
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    saved = get_store().upsert_ai_provider(provider)

    # Auto API Call: whenever a key is (re)provided, immediately validate the
    # connection so the modal shows live status without a manual "Test" click.
    # Also notify the LLM router so it picks up the new provider instantly.
    probe = None
    if provider.get("api_key") or pid == "ollama":
        probe = _probe_provider(saved)
        saved["last_probe"] = probe
    response = _public_provider(saved)
    if probe is not None:
        response["probe"] = probe
    return jsonify(response), 200


@admin_bp.route("/providers/<provider_id>", methods=["DELETE"])
@require_admin
def delete_provider(provider_id: str):
    if get_store().delete_ai_provider(provider_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


@admin_bp.route("/providers/<provider_id>/test", methods=["POST"])
@require_admin
def test_provider(provider_id: str):
    store = get_store()
    provider = store.get_ai_provider(provider_id)
    if provider is None:
        provider = {
            "id": provider_id,
            "name": _KNOWN_PROVIDERS.get(provider_id, {}).get("name", provider_id),
            "base_url": _KNOWN_PROVIDERS.get(provider_id, {}).get("base_url", ""),
        }
    return jsonify({"result": _probe_provider(provider)})


def _headers_for(provider: Dict[str, Any]) -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = provider.get("api_key", "")
    pid = provider.get("id", "")
    if not api_key:
        return headers
    if _KNOWN_PROVIDERS.get(pid, {}).get("auth_key") == "x-goog-api-key":
        headers["x-goog-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _probe_provider(provider: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort connectivity probe against the provider's models endpoint."""
    if http_client is None:
        return {"ok": False, "status": None, "detail": "requests library unavailable"}
    if not provider.get("api_key") and provider.get("id") != "ollama":
        return {"ok": False, "status": None, "detail": "No API key saved yet"}

    base_url = (provider.get("base_url") or "").rstrip("/") or _KNOWN_PROVIDERS.get(provider.get("id", ""), {}).get("base_url", "")
    pid = provider.get("id", "")
    # Key-based probe endpoints per provider
    url = f"{base_url}/models"
    if pid == "anthropic":
        url = base_url  # POST /messages is the cheapest auth route
        try:
            r = http_client.post(
                url.rstrip("/") + "/messages",
                headers=_headers_for(provider),
                json={"model": "claude-3-haiku-4-20250219", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                timeout=PROBE_TIMEOUT,
            )
        except Exception as exc:
            return {"ok": False, "status": None, "detail": f"Connection failed: {exc.__class__.__name__}"}
    elif pid == "ollama":
        url = f"{base_url}/api/tags"
        try:
            r = http_client.get(url, timeout=PROBE_TIMEOUT)
        except Exception as exc:
            return {"ok": False, "status": None, "detail": f"Connection failed: {exc.__class__.__name__}"}
    else:
        try:
            r = http_client.get(url, headers=_headers_for(provider), timeout=PROBE_TIMEOUT)
        except Exception as exc:
            return {"ok": False, "status": None, "detail": f"Connection failed: {exc.__class__.__name__}"}

    if r.status_code == 200:
        return {"ok": True, "status": 200, "detail": "Connection OK"}
    if r.status_code == 401 or r.status_code == 403:
        return {"ok": False, "status": r.status_code, "detail": "Invalid API key"}
    return {"ok": False, "status": r.status_code, "detail": f"Unexpected HTTP {r.status_code}"}


# ── MCP Servers ─────────────────────────────────────────────────────────────

@admin_bp.route("/mcp/servers", methods=["GET"])
@require_admin
def list_mcp_servers():
    return jsonify({"servers": [_public_server(s) for s in get_store().list_mcp_servers()]})


@admin_bp.route("/mcp/servers", methods=["POST"])
@require_admin
def create_mcp_server():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    existing = None
    sid = data.get("id")
    if sid:
        existing = get_store().get_mcp_server(sid)
    if existing is None:
        sid = str(sid or "").strip() or uuid.uuid4().hex[:12]

    env = data.get("env") or {}
    now = time.time()
    server = {
        "id": sid,
        "name": name,
        "transport": data.get("transport") or (existing.get("transport") if existing else "stdio"),
        "command": (data.get("command") if data.get("command") is not None else (existing.get("command") if existing else "")),
        "args": data.get("args") if data.get("args") is not None else (existing.get("args", []) if existing else []),
        "url": (data.get("url") if data.get("url") is not None else (existing.get("url") if existing else "")),
        "enabled": bool(data.get("enabled", existing.get("enabled", True)) if existing else data.get("enabled", True)),
        "env": env if env else (existing.get("env", {}) if existing else {}),
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    return jsonify(_public_server(get_store().upsert_mcp_server(server))), 200


@admin_bp.route("/mcp/servers/<server_id>", methods=["DELETE"])
@require_admin
def delete_mcp_server(server_id: str):
    if get_store().delete_mcp_server(server_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


@admin_bp.route("/mcp/servers/<server_id>/test", methods=["POST"])
@require_admin
def test_mcp_server(server_id: str):
    server = get_store().get_mcp_server(server_id)
    if server is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"result": _probe_server(server)})


def _probe_server(server: Dict[str, Any]) -> Dict[str, Any]:
    transport = server.get("transport", "stdio")
    if transport == "stdio":
        command = (server.get("command") or "").strip()
        if not command:
            return {"ok": False, "detail": "No command configured for stdio transport"}
        resolved = shutil.which(command.split()[0]) if command else None
        if resolved:
            return {"ok": True, "detail": f"Command found: {resolved}"}
        return {"ok": False, "detail": f"Command not found on PATH: {command.split()[0]}"}

    # HTTP/SSE transport: probe the URL
    base_url = (server.get("url") or "").strip().rstrip("/")
    if not base_url:
        return {"ok": False, "detail": "No URL configured for HTTP transport"}
    if http_client is None:
        return {"ok": False, "detail": "requests library unavailable"}
    try:
        r = http_client.get(f"{base_url}/", timeout=PROBE_TIMEOUT)
    except Exception as exc:
        return {"ok": False, "detail": f"Connection failed: {exc.__class__.__name__}"}
    if r.status_code < 500:
        return {"ok": True, "status": r.status_code, "detail": f"HTTP server reachable ({r.status_code})"}
    return {"ok": False, "status": r.status_code, "detail": f"HTTP error {r.status_code}"}


# ── Access Tokens (GitHub, GitLab, Bitbucket, Azure DevOps) ────────────────

_PLATFORMS = {
    "github": {
        "name": "GitHub",
        "type_guess": "github_personal_access_token",
        # README token format descriptions (fine-grained or classic PATs)
        "hint": "Fine-grained PAT (prefix ghp_) or classic PAT — scopes: repo, read:org",
    },
    "gitlab": {
        "name": "GitLab",
        "type_guess": "gitlab_personal_access_token",
        "hint": "Personal access token (glpat-) scoped to api",
    },
    "bitbucket": {
        "name": "Bitbucket",
        "type_guess": "bitbucket_app_password",
        "hint": "App password (username:password) with repo read access",
    },
    "azure_devops": {
        "name": "Azure DevOps",
        "type_guess": "azure_devops_personal_access_token",
        "hint": "PAT with Code Read scope",
    },
}


@admin_bp.route("/tokens", methods=["GET"])
@require_admin
def list_tokens():
    return jsonify({
        "tokens": [_public_token(t) for t in get_store().list_access_tokens()],
        "platforms": _PLATFORMS,
    })


@admin_bp.route("/tokens", methods=["POST"])
@require_admin
def create_token_record():
    data = request.get_json(force=True, silent=True) or {}
    name = str(data.get("name") or "").strip()
    platform = str(data.get("platform") or "").strip()
    if not name or not platform:
        return jsonify({"error": "name and platform are required"}), 400
    if platform not in _PLATFORMS:
        return jsonify({"error": f"unsupported platform: {platform}"}), 400

    existing = None
    tid = data.get("id")
    if tid:
        existing = get_store().get_access_token(tid)
    if existing is None:
        tid = str(tid or "").strip() or uuid.uuid4().hex[:12]

    token = data.get("token")
    if existing and existing.get("token") and (not token or _mask(token) == token):
        token = existing.get("token")

    now = time.time()
    record = {
        "id": tid,
        "name": name,
        "platform": platform,
        "enabled": bool(data.get("enabled", True)) if "enabled" in data else (existing.get("enabled", True) if existing else True),
        "token": token or "",
        "scopes": data.get("scopes") or (existing.get("scopes", []) if existing else []),
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    return jsonify(_public_token(get_store().upsert_access_token(record))), 200


@admin_bp.route("/tokens/<token_id>", methods=["DELETE"])
@require_admin
def delete_token_record(token_id: str):
    if get_store().delete_access_token(token_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


@admin_bp.route("/tokens/<token_id>/test", methods=["POST"])
@require_admin
def test_token_record(token_id: str):
    record = get_store().get_access_token(token_id)
    if record is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"result": _probe_token(record)})


def _probe_token(record: Dict[str, Any]) -> Dict[str, Any]:
    if http_client is None:
        return {"ok": False, "detail": "requests library unavailable"}
    token = record.get("token", "")
    if not token:
        return {"ok": False, "detail": "No token saved yet"}
    platform = record.get("platform", "")
    headers = {"Accept": "application/json"}

    if platform == "github":
        headers["Authorization"] = f"Bearer {token}"
        url = "https://api.github.com/user"
    elif platform == "gitlab":
        headers["PRIVATE-TOKEN"] = token
        url = "https://gitlab.com/api/v4/user"
    elif platform == "bitbucket":
        # token stored as "username:app_password"
        parts = token.split(":", 1)
        if len(parts) == 2:
            headers["Authorization"] = None
            # use basic auth
            import base64
            b64 = base64.b64encode(token.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {b64}"
        url = "https://api.bitbucket.org/2.0/user"
    elif platform == "azure_devops":
        import base64
        b64 = base64.b64encode(f":{token}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {b64}"
        url = "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1"
    else:
        return {"ok": False, "detail": f"Unsupported platform {platform}"}

    try:
        r = http_client.get(url, headers=headers, timeout=PROBE_TIMEOUT)
    except Exception as exc:
        return {"ok": False, "detail": f"Connection failed: {exc.__class__.__name__}"}
    if r.status_code == 200:
        return {"ok": True, "status": 200, "detail": "Token validated"}
    if r.status_code in (401, 403):
        return {"ok": False, "status": r.status_code, "detail": "Invalid token / insufficient scope"}
    return {"ok": False, "status": r.status_code, "detail": f"Unexpected HTTP {r.status_code}"}


# ── helpers ─────────────────────────────────────────────────────────────────

def re_valid_id(value: str) -> bool:
    return all(c.isalnum() or c in ("_", "-") for c in value)


def init_admin(app) -> None:
    """Register the admin blueprint."""
    app.register_blueprint(admin_bp)
    logger.info("Admin API mounted at /api/v1/admin")