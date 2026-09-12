# =============================================================================
# Admin settings store (JSON-file backed, thread-safe)
# =============================================================================
# Manages admin-configured integrations: AI API providers, MCP servers, and
# access tokens (GitHub, GitLab, Bitbucket, Azure DevOps). Secrets are stored
# to a gitignored JSON file under ~/.gitfix/admin/settings.json and never
# echoed to the Admin UI in full -- only a masked tail is returned.
# When the optional `cryptography` package is available and SECRET_KEY is set,
# secret fields are encrypted at rest (Fernet); the file stays plaintext-only
# otherwise so a missing dependency never blocks the app.
# =============================================================================

import os
import json
import base64
import hashlib
import threading
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTO = True
except Exception:  # optional dependency -- degrade to plaintext storage
    Fernet = None  # type: ignore[assignment]
    InvalidToken = ValueError
    _HAS_CRYPTO = False

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = Path.home() / ".gitfix" / "admin" / "settings.json"
MASK_PLACEHOLDER = "••••••••••••"

# Record fields that hold secrets and must never sit on disk in plaintext.
_SECRET_FIELDS = {
    "access_tokens": ("token",),
    "ai_providers": ("api_key",),
    "mcp_servers": ("env",),
    "webhook_configs": ("secret", "url"),
}
_ENC_PREFIX = "enc:"


def _fernet() -> Any:
    """Fernet cipher bound to SECRET_KEY, or None when encryption is unavailable."""
    if not _HAS_CRYPTO:
        return None
    key_hex = os.environ.get("SECRET_KEY", "")
    if not key_hex:
        return None
    digest = base64.urlsafe_b64encode(hashlib.sha256(key_hex.encode("utf-8")).digest())
    return Fernet(digest)


def _encrypt_record(record: Dict[str, Any], fields: tuple) -> Dict[str, Any]:
    f = _fernet()
    if f is None:
        return record
    rec = dict(record)
    for field in fields:
        val = rec.get(field)
        if val in (None, "", [], {}):
            continue
        serialized = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
        if serialized.startswith(_ENC_PREFIX):
            continue
        rec[field] = _ENC_PREFIX + f.encrypt(serialized.encode("utf-8")).decode("ascii")
    return rec


def _decrypt_record(record: Dict[str, Any], fields: tuple) -> Dict[str, Any]:
    f = _fernet()
    rec = dict(record)
    for field in fields:
        val = rec.get(field)
        if not isinstance(val, str) or not val.startswith(_ENC_PREFIX):
            continue
        try:
            if f is None:
                raise InvalidToken("crypto unavailable")
            raw = f.decrypt(val[len(_ENC_PREFIX):].encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            # Key rotated or dependency missing: keep the blob, never leak it.
            continue
        try:
            rec[field] = json.loads(raw)
        except ValueError:
            rec[field] = raw
    return rec


def _encrypt_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Non-mutating copy of the doc with secret fields encrypted for disk."""
    if not _HAS_CRYPTO or not _fernet():
        return doc
    out: Dict[str, Any] = {}
    for key, val in doc.items():
        if key in _SECRET_FIELDS and isinstance(val, list):
            out[key] = [_encrypt_record(item, _SECRET_FIELDS[key]) for item in val]
        elif isinstance(val, dict):
            out[key] = _encrypt_doc(val)
        else:
            out[key] = val
    return out


def _decrypt_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Non-mutating copy of a disk doc with secret fields decrypted in memory."""
    out: Dict[str, Any] = {}
    for key, val in doc.items():
        if key in _SECRET_FIELDS and isinstance(val, list):
            out[key] = [_decrypt_record(item, _SECRET_FIELDS[key]) for item in val]
        elif isinstance(val, dict):
            out[key] = _decrypt_doc(val)
        else:
            out[key] = val
    return out

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
            self._doc = _decrypt_doc(merged)
            return self._doc

    def save(self) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(_encrypt_doc(self._doc), indent=2, ensure_ascii=False),
                           encoding="utf-8")
            os.chmod(tmp, 0o600)
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
        _store.load()
    return _store