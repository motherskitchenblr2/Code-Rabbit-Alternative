# =============================================================================
# Auto-rotation LLM router
# =============================================================================
# Picks the best configured provider/model for a task, tracks per-provider
# health (circuit-breaker style with cooldown), and transparently fails over
# to the next candidate when a provider errors or rate-limits. Providers are
# resolved from the admin settings store (backend/admin/store.py) with .env
# key fallbacks so the app is autonomous the moment an API key is added.
# =============================================================================

from __future__ import annotations

import os
import time
import json
import logging
import threading
from typing import Any, Dict, List, Optional

from .catalog import (
    TASK_TYPES,
    TASK_LABELS,
    PROVIDER_META,
    ENV_KEY_MAP,
    TASK_ROUTING_PREFERENCE,
    task_model_for,
    provider_name,
)

logger = logging.getLogger(__name__)

try:
    import requests
    HTTP_AVAILABLE = True
except ImportError:  # pragma: no cover - requests is a declared dependency
    requests = None
    HTTP_AVAILABLE = False

REQUEST_TIMEOUT = 60
MAX_RETRIES = 2          # attempts per provider before failing over
CIRCUIT_BREAK_FAILURES = 3
COOLDOWN_SECONDS = 60

# task -> candidate provider preference. Used as the ranked pool builder;
# custom providers are appended at the end.
DEFAULT_PREFERENCE: Dict[str, List[str]] = dict(TASK_ROUTING_PREFERENCE)


def _env_api_keys() -> Dict[str, str]:
    """Collect API keys for known providers from the environment."""
    out: Dict[str, str] = {}
    for pid, env_var in ENV_KEY_MAP.items():
        if env_var:
            val = os.environ.get(env_var, "").strip()
            if val:
                out[pid] = val
    return out


class ProviderHealth:
    """Per-provider circuit breaker state."""

    def __init__(self) -> None:
        self.failures = 0
        self.cooldown_until = 0.0
        self.last_error: Optional[str] = None

    def healthy(self) -> bool:
        if self.cooldown_until and time.time() < self.cooldown_until:
            return False
        return True

    def record_failure(self, error: str) -> None:
        self.failures += 1
        self.last_error = error
        if self.failures >= CIRCUIT_BREAK_FAILURES:
            self.cooldown_until = time.time() + COOLDOWN_SECONDS

    def record_success(self) -> None:
        self.failures = 0
        self.cooldown_until = 0.0
        self.last_error = None


class AutoRouter:
    """Task-aware router with automatic provider rotation / failover."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._health: Dict[str, ProviderHealth] = {}

    # ── provider resolution ────────────────────────────────────────────────
    def list_providers(self) -> List[Dict[str, Any]]:
        """Merge admin-store providers with .env fallbacks."""
        merged: Dict[str, Dict[str, Any]] = {}
        env_keys = _env_api_keys()

        try:
            from backend.admin.store import get_store
            stored = get_store().list_ai_providers()
        except Exception as exc:  # pragma: no cover - admin module may be missing
            logger.debug("Admin store unavailable: %s", exc)
            stored = []

        for item in stored:
            pid = str(item.get("id") or "").lower()
            if not pid:
                continue
            merged[pid] = {
                "id": pid,
                "name": item.get("name") or PROVIDER_META.get(pid, {}).get("name", pid),
                "base_url": (item.get("base_url") or "").strip() or PROVIDER_META.get(pid, {}).get("base_url", ""),
                "model": str(item.get("model") or "").strip(),
                "api_key": str(item.get("api_key") or "").strip(),
                "enabled": bool(item.get("enabled", True)),
                "multimodal": bool(item.get("multimodal", PROVIDER_META.get(pid, {}).get("multimodal", False))),
            }

        # .env keys fill gaps (highest-priority fallback when no store entry).
        for pid, key in env_keys.items():
            if pid not in merged:
                meta = PROVIDER_META.get(pid, {})
                merged[pid] = {
                    "id": pid,
                    "name": meta.get("name", pid),
                    "base_url": meta.get("base_url", ""),
                    "model": "",
                    "api_key": key,
                    "enabled": True,
                    "multimodal": bool(meta.get("multimodal", False)),
                }

        return list(merged.values())

    def _health_for(self, pid: str) -> ProviderHealth:
        with self._lock:
            return self._health.setdefault(pid, ProviderHealth())

    def _configured(self, provider: Dict[str, Any], task: str) -> bool:
        if not provider.get("enabled", True):
            return False
        if not provider.get("base_url"):
            return False
        meta = PROVIDER_META.get(provider.get("id", ""), {})
        if meta.get("auth") != "none" and not provider.get("api_key"):
            return False
        if task == "multimodal" and not provider.get("multimodal", False):
            return False
        return True

    # ── routing ────────────────────────────────────────────────────────────
    def rank_providers(self, task: str) -> List[Dict[str, Any]]:
        """Return candidates for a task ordered by routing preference."""
        preference = DEFAULT_PREFERENCE.get(task, DEFAULT_PREFERENCE.get("chat", []))
        providers = {p["id"]: p for p in self.list_providers()}

        ordered: List[Dict[str, Any]] = []
        seen = set()
        for pid in preference:
            p = providers.get(pid)
            if p and p["id"] not in seen:
                seen.add(p["id"])
                if self._configured(p, task):
                    ordered.append(p)
        # Custom providers (not in the catalog) always participate.
        for p in providers.values():
            if p["id"] not in seen and p["id"] not in PROVIDER_META:
                seen.add(p["id"])
                if self._configured(p, task):
                    ordered.append(p)
        return ordered

    def resolve_model(self, provider: Dict[str, Any], task: str) -> str:
        """Choose a model for a provider/task pair."""
        if provider.get("model"):
            return provider["model"]
        return task_model_for(provider["id"], task)

    def route(self, task: str) -> Optional[Dict[str, Any]]:
        """Pick the top healthy candidate for a task."""
        for p in self.rank_providers(task):
            if self._health_for(p["id"]).healthy():
                return {**p, "task": task, "model": self.resolve_model(p, task)}
        return None

    # ── chat completion ────────────────────────────────────────────────────
    def complete(
        self,
        messages: List[Dict[str, str]],
        task: str = "chat",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Send a chat request, auto-rotating across providers on failure.

        Returns a dict with ``ok``, ``provider``, ``model``, ``content``,
        ``attempts``, and (on total failure) ``error``.
        """
        if not HTTP_AVAILABLE:  # pragma: no cover - requests is required
            return {"ok": False, "error": "requests library unavailable", "attempts": 0}

        task = task if task in TASK_TYPES else "chat"
        candidates = self.rank_providers(task)
        attempts: List[Dict[str, Any]] = []
        errors: List[str] = []

        for provider in candidates:
            pid = provider["id"]
            candidate_model = (model or "").strip() or self.resolve_model(provider, task)
            if not candidate_model:
                continue

            attempts.append({"provider": pid, "model": candidate_model})
            try:
                content = self._chat_once(provider, candidate_model, messages, max_tokens, temperature)
            except Exception as exc:  # noqa: BLE001 - any transport/API error triggers failover
                error_msg = f"{exc.__class__.__name__}: {exc}"
                logger.warning("LLM %s/%s failed: %s", pid, candidate_model, error_msg)
                errors.append(f"{pid}: {error_msg}")
                self._health_for(pid).record_failure(error_msg)
                continue

            self._health_for(pid).record_success()
            return {
                "ok": True,
                "provider": pid,
                "provider_name": provider_name(pid),
                "model": candidate_model,
                "content": content,
                "attempts": attempts,
                "errors": errors,
            }

        return {
            "ok": False,
            "error": "No provider could complete the request",
            "attempts": attempts,
            "errors": errors,
        }

    # ── transport helpers ──────────────────────────────────────────────────
    def _chat_once(
        self,
        provider: Dict[str, Any],
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str:
        pid = provider["id"]
        base_url = (provider.get("base_url") or "").rstrip("/")
        api_key = provider.get("api_key") or ""
        meta = PROVIDER_META.get(pid, {})
        auth = meta.get("auth", "bearer")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        if auth == "x-goog":
            headers["x-goog-api-key"] = api_key
            url = f"{base_url}/models/{model}:generateContent"
            body = {
                "contents": [{"parts": [{"text": msg.get("content", "")}]} for msg in messages],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
            }
        elif auth == "x-api":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
            url = f"{base_url}/messages"
            # Convert OpenAI-style system message to Anthropic's system field.
            system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
            user_msgs = [m for m in messages if m.get("role") != "system"]
            body: Dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": user_msgs,
            }
            if system:
                body["system"] = system
        elif auth == "none":  # ollama
            url = f"{base_url}/api/chat"
            body = {
                "model": model,
                "messages": messages,
                "options": {"num_predict": max_tokens, "temperature": temperature},
                "stream": False,
            }
        else:  # OpenAI-compatible (nvidia, openrouter, openai, groq, ...)
            headers["Authorization"] = f"Bearer {api_key}"
            url = f"{base_url}/chat/completions"
            body = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        r = requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return self._extract_text(pid, r.json())

    @staticmethod
    def _extract_text(pid: str, payload: Dict[str, Any]) -> str:
        if pid == "anthropic":
            blocks = payload.get("content") or []
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if pid == "google":
            candidates = payload.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts") or []
                return "".join(p.get("text", "") for p in parts)
            return ""
        if pid == "ollama":
            return payload.get("message", {}).get("content", "")
        choices = payload.get("choices") or []
        if choices:
            return choices[0].get("message", {}).get("content", "") or choices[0].get("text", "")
        return ""

    # ── introspection ──────────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        providers = []
        for p in self.list_providers():
            health = self._health_for(p["id"])
            providers.append({
                "id": p["id"],
                "name": p.get("name") or p["id"],
                "enabled": bool(p.get("enabled", True)),
                "configured": bool(p.get("api_key") or PROVIDER_META.get(p["id"], {}).get("auth") == "none"),
                "multimodal": bool(p.get("multimodal", False)),
                "healthy": health.healthy(),
                "failures": health.failures,
                "last_error": health.last_error,
            })

        routing = {}
        for task in TASK_TYPES:
            candidates = []
            for p in self.rank_providers(task):
                top = self._health_for(p["id"]).healthy() and len(candidates) == 0
                candidates.append({
                    "provider": p["id"],
                    "model": self.resolve_model(p, task),
                    "status": "prima" if top else ("degraded" if not self._health_for(p["id"]).healthy() else "fallback"),
                })
            routing[task] = {"label": TASK_LABELS[task], "candidates": candidates}

        return {
            "providers": providers,
            "routing": routing,
            "catalog_providers": [{"id": k, "name": v.get("name", k)} for k, v in PROVIDER_META.items()],
        }


_router: Optional[AutoRouter] = None
_router_lock = threading.Lock()


def get_router() -> AutoRouter:
    global _router
    with _router_lock:
        if _router is None:
            _router = AutoRouter()
        return _router


def complete(
    messages: List[Dict[str, str]],
    task: str = "chat",
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    return get_router().complete(messages, task=task, model=model, max_tokens=max_tokens, temperature=temperature)


def status() -> Dict[str, Any]:
    return get_router().snapshot()