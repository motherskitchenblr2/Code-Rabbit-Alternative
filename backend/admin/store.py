# =============================================================================
# Admin settings store (JSON-file backed, thread-safe)
# =============================================================================
# Manages admin-configured integrations: AI API providers, MCP servers, and
# access tokens (GitHub, GitLab, Bitbucket, Azure DevOps). Secrets are stored
# to a gitignored JSON file under ~/.gitfix/admin/settings.json and never
# echoed to the Admin UI in full -- only a masked tail is returned.
# =============================================================================

import os
import json
import threading
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = Path.home() / ".gitfix" / "admin" / "settings.json"
MASK_PLACEHOLDER = "••••••••••••"

_lock = threading.Lock()


class AdminSettings:
    """Thread-safe read/write access to the admin settings file.

    Each mutating call persists the whole document atomically (write temp +
    rename) so a crash mid-write never corrupts the file.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_SETTINGS_PATH
        self._doc: Dict[str, Any] = {}

    # ── load/save ──────────────────────────────────────────────────────────
    def load(self) -> Dict[str, Any]:
        with _lock:
            if not self.path.exists():
                self._doc = self._blank()
                return self._doc
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.error("Failed to read admin settings %s: %s", self.path, exc)
                self._doc = self._blank()
                return self._doc
            merged = self._blank()
            merged.update(raw or {})
            self._doc = merged
            return self._doc

    def save(self) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._doc, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)

    @staticmethod
    def _blank() -> Dict[str, Any]:
        return {
            "version": 1,
            "ai_providers": [],
            "mcp_servers": [],
            "access_tokens": [],
            "webhook_configs": [],
        }

    # ── generic list helpers ───────────────────────────────────────────────
    def _list(self, key: str) -> List[Dict[str, Any]]:
        self._doc.setdefault(key, [])
        return self._doc[key]

    def _get_item(self, key: str, item_id: str) -> Optional[Dict[str, Any]]:
        for it in self._list(key):
            if it.get("id") == item_id:
                return it
        return None

    def _upsert_item(self, key: str, item: Dict[str, Any]) -> Dict[str, Any]:
        items = self._list(key)
        for i, it in enumerate(items):
            if it.get("id") == item.get("id"):
                items[i] = item
                self.save()
                return item
        items.append(item)
        self.save()
        return item

    def _delete_item(self, key: str, item_id: str) -> bool:
        items = self._list(key)
        new = [it for it in items if it.get("id") != item_id]
        if len(new) == len(items):
            return False
        self._doc[key] = new
        self.save()
        return True

    # ── collections ────────────────────────────────────────────────────────
    def get_doc(self) -> Dict[str, Any]:
        return self.load()

    def list_ai_providers(self) -> List[Dict[str, Any]]:
        return self._list("ai_providers")

    def upsert_ai_provider(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert_item("ai_providers", provider)

    def delete_ai_provider(self, provider_id: str) -> bool:
        return self._delete_item("ai_providers", provider_id)

    def get_ai_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return self._get_item("ai_providers", provider_id)

    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        return self._list("mcp_servers")

    def upsert_mcp_server(self, server: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert_item("mcp_servers", server)

    def delete_mcp_server(self, server_id: str) -> bool:
        return self._delete_item("mcp_servers", server_id)

    def get_mcp_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        return self._get_item("mcp_servers", server_id)

    def list_access_tokens(self) -> List[Dict[str, Any]]:
        return self._list("access_tokens")

    def upsert_access_token(self, token: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert_item("access_tokens", token)

    def delete_access_token(self, token_id: str) -> bool:
        return self._delete_item("access_tokens", token_id)

    def get_access_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        return self._get_item("access_tokens", token_id)

    def list_webhook_configs(self) -> List[Dict[str, Any]]:
        return self._list("webhook_configs")

    def upsert_webhook_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return self._upsert_item("webhook_configs", config)

    def delete_webhook_config(self, config_id: str) -> bool:
        return self._delete_item("webhook_configs", config_id)

    def get_webhook_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        return self._get_item("webhook_configs", config_id)


_store: Optional[AdminSettings] = None


def get_store() -> AdminSettings:
    global _store
    if _store is None:
        _store = AdminSettings()
    return _store