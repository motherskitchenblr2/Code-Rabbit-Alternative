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
        "endpoint_set": bool(item.get("endpoint")),
        "endpoint_tail": _mask(item.get("endpoint")),
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


# ── Access Tokens & connection credentials ──────────────────────────────────
# Each platform carries a `probe` spec that drives _probe_token():
#   api      — validate a token against a GET endpoint (auth strategy in `auth`)
#   graphql  — validate against a GraphQL POST endpoint
#   tcp      — connection-string service (Redis/PostgreSQL): TCP reachability only
#   http     — the stored value IS a base URL; GET value + `path`
# `endpoint_optional` platforms may store a per-record base-URL override, which
# is persisted masked like a token (it can embed credentials, e.g. a DSN).

_PLATFORMS: Dict[str, Dict[str, Any]] = {
    "github": {
        "name": "GitHub",
        "type_guess": "github_personal_access_token",
        "hint": "Fine-grained PAT (prefix ghp_) or classic PAT — scopes: repo, read:org",
        "probe": {"type": "api", "url": "https://api.github.com/user", "auth": "bearer"},
    },
    "gitlab": {
        "name": "GitLab",
        "type_guess": "gitlab_personal_access_token",
        "hint": "Personal access token (glpat-) scoped to api",
        "probe": {"type": "api", "url": "https://gitlab.com/api/v4/user", "auth": "private_token"},
    },
    "bitbucket": {
        "name": "Bitbucket",
        "type_guess": "bitbucket_app_password",
        "hint": "Store as username:app-password with repo read access",
        "probe": {"type": "api", "url": "https://api.bitbucket.org/2.0/user", "auth": "basic_colon"},
    },
    "azure_devops": {
        "name": "Azure DevOps",
        "type_guess": "azure_devops_personal_access_token",
        "hint": "PAT with Code Read scope",
        "probe": {"type": "api", "url": "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1", "auth": "basic_colon_prefix"},
    },
    "vercel": {
        "name": "Vercel",
        "type_guess": "vercel_api_token",
        "credential_label": "API Token",
        "hint": "API token from vercel.com/account/tokens (read scope)",
        "probe": {"type": "api", "url": "https://api.vercel.com/v2/user", "auth": "bearer"},
    },
    "netlify": {
        "name": "Netlify",
        "type_guess": "netlify_personal_access_token",
        "credential_label": "Personal Access Token",
        "hint": "Personal access token from app.netlify.com/user/applications",
        "probe": {"type": "api", "url": "https://api.netlify.com/api/v1/user", "auth": "bearer"},
    },
    "cloudflare": {
        "name": "Cloudflare",
        "type_guess": "cloudflare_api_token",
        "credential_label": "API Token",
        "hint": "API token from dash.cloudflare.com/profile/api-tokens",
        "probe": {"type": "api", "url": "https://api.cloudflare.com/client/v4/user/tokens/verify", "auth": "bearer", "invalid_statuses": [400, 401, 403]},
    },
    "huggingface": {
        "name": "Hugging Face",
        "type_guess": "huggingface_access_token",
        "hint": "Access token from huggingface.co/settings/tokens",
        "probe": {"type": "api", "url": "https://huggingface.co/api/whoami-v2", "auth": "bearer"},
    },
    "codeberg": {
        "name": "Codeberg",
        "type_guess": "codeberg_project_token",
        "hint": "Token from codeberg.org/user/settings/applications",
        "probe": {"type": "api", "url": "https://codeberg.org/api/v1/user", "auth": "token"},
    },
    "jira": {
        "name": "Jira",
        "type_guess": "jira_api_token",
        "credential_label": "Email:API token",
        "hint": "Store as email:your-api-token (Atlassian API token); set your site URL in Endpoint",
        "endpoint_optional": True,
        "endpoint_hint": "Atlassian site URL, e.g. https://your-domain.atlassian.net",
        "probe": {"type": "api", "url": "https://your-domain.atlassian.net", "path": "/rest/api/2/myself", "auth": "basic_colon", "require_endpoint": True},
    },
    "linear": {
        "name": "Linear",
        "type_guess": "linear_api_token",
        "credential_label": "API Key",
        "hint": "Personal API key from linear.app/settings/api",
        "probe": {"type": "graphql", "url": "https://api.linear.app/graphql", "auth": "linear"},
    },
    "datadog": {
        "name": "Datadog",
        "type_guess": "datadog_api_key",
        "credential_label": "API Key",
        "hint": "Datadog API key; override Endpoint for a regional site (https://api.eu.datadoghq.com etc.)",
        "endpoint_optional": True,
        "endpoint_hint": "Regional API endpoint, e.g. https://api.us3.datadoghq.com",
        "probe": {"type": "api", "url": "https://api.datadoghq.com", "path": "/api/v1/validate", "auth": "dd_api_key"},
    },
    "sentry": {
        "name": "Sentry",
        "type_guess": "sentry_auth_token",
        "credential_label": "Auth Token",
        "hint": "Auth token from sentry.io/settings/auth-tokens (or your self-hosted Sentry)",
        "endpoint_optional": True,
        "endpoint_hint": "Sentry base URL, e.g. https://sentry.io or https://sentry.example.com",
        "probe": {"type": "api", "url": "https://sentry.io", "path": "/api/0/", "auth": "bearer"},
    },
    "postgresql": {
        "name": "PostgreSQL",
        "type_guess": "postgresql_connection_string",
        "credential_label": "Connection string",
        "hint": "postgresql://user:password@host:5432/dbname — reachability only, credentials are not checked",
        "probe": {"type": "tcp", "default_port": 5432},
    },
    "redis": {
        "name": "Redis",
        "type_guess": "redis_connection_string",
        "credential_label": "Connection string",
        "hint": "redis://:password@host:6379 — reachability only, credentials are not checked",
        "probe": {"type": "tcp", "default_port": 6379},
    },
    "qdrant": {
        "name": "Qdrant",
        "type_guess": "qdrant_endpoint_url",
        "credential_label": "Endpoint URL",
        "hint": "Full Qdrant base URL, e.g. http://localhost:6333",
        "probe": {"type": "http", "path": "/collections", "label": "Endpoint reachable"},
    },
    "prometheus": {
        "name": "Prometheus",
        "type_guess": "prometheus_endpoint_url",
        "credential_label": "Endpoint URL",
        "hint": "Prometheus base URL, e.g. http://localhost:9090",
        "probe": {"type": "http", "path": "/api/v1/status/buildinfo", "label": "Endpoint reachable"},
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

    endpoint = data.get("endpoint")
    if existing and existing.get("endpoint") and (not endpoint or _mask(str(endpoint)) == str(endpoint)):
        endpoint = existing.get("endpoint")

    now = time.time()
    record = {
        "id": tid,
        "name": name,
        "platform": platform,
        "enabled": bool(data.get("enabled", True)) if "enabled" in data else (existing.get("enabled", True) if existing else True),
        "token": token or "",
        "endpoint": str(endpoint or "").strip(),
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


def _b64(secret: str) -> str:
    import base64
    return base64.b64encode(secret.encode("utf-8")).decode("ascii")


def _parse_host_port(value: str, default_port: int):
    from urllib.parse import urlparse
    value = (value or "").strip()
    if not value:
        return None, None
    parsed = urlparse(value if "://" in value else f"//{value}")
    host = parsed.hostname
    if not host:
        return None, None
    return host, parsed.port or default_port


def _tcp_reachable(host: str, port: int, timeout: float = PROBE_TIMEOUT) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _token_headers(record: Dict[str, Any], probe: Dict[str, Any]) -> Dict[str, str]:
    token = record.get("token", "")
    auth = probe.get("auth", "bearer")
    headers = {"Accept": "application/json"}
    if auth == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    elif auth == "token":
        headers["Authorization"] = f"token {token}"
    elif auth == "private_token":
        headers["PRIVATE-TOKEN"] = token
    elif auth == "basic_colon":
        headers["Authorization"] = f"Basic {_b64(token)}"
    elif auth == "basic_colon_prefix":
        headers["Authorization"] = f"Basic {_b64(':' + token)}"
    elif auth == "dd_api_key":
        headers["DD-API-KEY"] = token
    elif auth == "linear":
        headers["Authorization"] = f"Linear {token}"
    return headers


def _token_http_get(url: str, headers: Dict[str, str], ok_text: str, invalid_statuses=()) -> Dict[str, Any]:
    try:
        r = http_client.get(url, headers=headers, timeout=PROBE_TIMEOUT)
    except Exception as exc:
        return {"ok": False, "detail": f"Connection failed: {exc.__class__.__name__}"}
    if r.status_code == 200:
        return {"ok": True, "status": 200, "detail": ok_text}
    if r.status_code in (401, 403) + tuple(invalid_statuses):
        return {"ok": False, "status": r.status_code, "detail": "Invalid token / insufficient scope"}
    return {"ok": False, "status": r.status_code, "detail": f"Unexpected HTTP {r.status_code}"}


def _probe_token(record: Dict[str, Any]) -> Dict[str, Any]:
    if http_client is None:
        return {"ok": False, "detail": "requests library unavailable"}
    token = (record.get("token") or "").strip()
    if not token:
        return {"ok": False, "detail": "No credential saved yet"}
    platform = record.get("platform", "")
    spec = _PLATFORMS.get(platform, {})
    if not spec:
        return {"ok": False, "detail": f"Unsupported platform {platform}"}
    probe = spec.get("probe", {}) or {}
    ptype = probe.get("type", "api")

    # TCP reachability (Redis / PostgreSQL connection strings)
    if ptype == "tcp":
        host, port = _parse_host_port(token, probe.get("default_port", 443))
        if not host:
            return {"ok": False, "detail": "Could not parse host from connection string"}
        if _tcp_reachable(host, port, PROBE_TIMEOUT):
            return {"ok": True, "detail": f"TCP reachable on {host}:{port}"}
        return {"ok": False, "detail": f"Connection failed on {host}:{port}"}

    # URL-based HTTP services (Qdrant, Prometheus) where the stored value IS the URL
    if ptype == "http":
        url = f"{token.rstrip('/')}{probe.get('path', '/')}"
        return _token_http_get(url, {"Accept": "application/json"}, probe.get("label", "Connection OK"))

    # API / GraphQL token probes
    endpoint = (record.get("endpoint") or "").strip()
    base = endpoint.rstrip("/") or probe.get("url", "").rstrip("/")
    if probe.get("require_endpoint") and not endpoint:
        return {"ok": False, "detail": "Set your site URL (e.g. https://your-domain.atlassian.net) when connecting"}
    url = base + (probe.get("path", "") or "")
    headers = _token_headers(record, probe)

    if ptype == "graphql":
        try:
            r = http_client.post(url, headers=headers, json={"query": "{ viewer { id } }"}, timeout=PROBE_TIMEOUT)
        except Exception as exc:
            return {"ok": False, "detail": f"Connection failed: {exc.__class__.__name__}"}
        if r.status_code == 200:
            return {"ok": True, "status": 200, "detail": "Token validated"}
        if r.status_code in (401, 403):
            return {"ok": False, "status": r.status_code, "detail": "Invalid token / insufficient scope"}
        return {"ok": False, "status": r.status_code, "detail": f"Unexpected HTTP {r.status_code}"}

    return _token_http_get(url, headers, "Token validated", probe.get("invalid_statuses", ()))


# ── helpers ─────────────────────────────────────────────────────────────────

def re_valid_id(value: str) -> bool:
    return all(c.isalnum() or c in ("_", "-") for c in value)


def init_admin(app) -> None:
    """Register the admin blueprint."""
    app.register_blueprint(admin_bp)
    logger.info("Admin API mounted at /api/v1/admin")