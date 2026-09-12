# =============================================================================
# User account store: password, 2FA, API keys, active sessions
# =============================================================================
# Single JSON-file backed store (atomic writes, thread-safe, gitignored) for
# everything the Settings → Security tab manages. The whole document lives in
# memory once loaded, so per-request token verification is O(1) lookups and
# only mutations touch disk. Secrets are never stored in plaintext: passwords
# use PBKDF2-HMAC-SHA256 and API keys are stored as SHA-256 hashes.
# =============================================================================

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.auth import totp

logger = logging.getLogger(__name__)

ACCOUNT_FILE = Path(os.environ.get("GITFIX_AUTH_FILE") or (Path.home() / ".gitfix" / "auth" / "account.json"))

API_KEY_PREFIX = "gfk_"
_REFRESH_TTL = 7 * 24 * 3600
_PBKDF2_ROUNDS = 200_000


def _now() -> int:
    return int(time.time())


def fingerprint(token: str) -> str:
    """Opaque token fingerprint — safe to store and use for revocation."""
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _blank() -> Dict[str, Any]:
    return {
        "version": 1,
        "password_hash": None,
        "totp_secret": None,
        "totp_enabled": False,
        "api_keys": [],
        "sessions": [],
    }


class AccountStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or ACCOUNT_FILE
        # RLock: persist() is called from inside other locked mutations.
        self._lock = threading.RLock()
        self._doc: Dict[str, Any] = _blank()
        self.load()

    # ── load / persist ─────────────────────────────────────────────────────
    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._doc = _blank()
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.error("Failed to read account store %s: %s", self.path, exc)
                self._doc = _blank()
                return
            merged = _blank()
            merged.update(raw or {})
            merged.setdefault("api_keys", [])
            merged.setdefault("sessions", [])
            self._doc = merged

    def persist(self) -> None:
        with self._lock:
            self.path = Path(self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._doc, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)

    # ── password ───────────────────────────────────────────────────────────
    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
        return "pbkdf2:sha256:%d:%s$%s" % (
            _PBKDF2_ROUNDS,
            salt.hex(),
            digest.hex(),
        )

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            _, _, rounds, rest = encoded.split(":", 3)
            salt_hex, hash_hex = rest.split("$")
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
            )
            return hmac.compare_digest(digest.hex(), hash_hex)
        except (ValueError, TypeError):
            return False

    def has_password(self) -> bool:
        return bool(self._doc.get("password_hash"))

    def set_password(self, password: str) -> None:
        with self._lock:
            self._doc["password_hash"] = self._hash_password(password) if password else ""
            self.persist()

    def verify_password(self, password: str) -> bool:
        encoded = self._doc.get("password_hash")
        return bool(encoded) and self._verify_password(password, encoded)

    # ── 2FA / TOTP ─────────────────────────────────────────────────────────
    def totp_enabled(self) -> bool:
        return bool(self._doc.get("totp_enabled"))

    def totp_secret(self) -> Optional[str]:
        return self._doc.get("totp_secret")

    def set_totp_secret(self, secret: str) -> None:
        with self._lock:
            self._doc["totp_secret"] = secret
            self.persist()

    def enable_totp(self) -> None:
        with self._lock:
            self._doc["totp_enabled"] = True
            self.persist()

    def disable_totp(self) -> None:
        with self._lock:
            self._doc["totp_enabled"] = False
            self._doc["totp_secret"] = None
            self.persist()

    def verify_totp_code(self, code: object) -> bool:
        secret = self._doc.get("totp_secret")
        if not secret or not self._doc.get("totp_enabled"):
            return False
        return totp.verify_code(secret, code)

    def verify_totp_enrollment(self, secret: str, code: object) -> bool:
        return bool(secret) and totp.verify_code(secret, code)

    @staticmethod
    def totp_uri(secret: str) -> str:
        return totp.otpauth_uri(secret)

    # ── user API keys ──────────────────────────────────────────────────────
    @staticmethod
    def hash_api_key(key: str) -> str:
        return hashlib.sha256((key or "").encode("utf-8")).hexdigest()

    def create_api_key(self, name: str) -> Dict[str, Any]:
        raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
        record = {
            "id": uuid4(),
            "name": (name or "API key").strip()[:80],
            "key_hash": self.hash_api_key(raw),
            "tail": raw[-8:],
            "created_at": _now(),
            "last_used_at": None,
        }
        with self._lock:
            self._doc.setdefault("api_keys", []).append(record)
            self.persist()
        public = dict(record)
        public.pop("key_hash", None)
        return {"record": public, "key": raw}

    def list_api_keys(self) -> List[Dict[str, Any]]:
        with self._lock:
            out = []
            for rec in self._doc.get("api_keys", []):
                out.append({k: v for k, v in rec.items() if k != "key_hash"})
            return out

    def get_api_key_record(self, hashed: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for rec in self._doc.get("api_keys", []):
                if rec.get("key_hash") == hashed:
                    return dict(rec)
            return None

    def touch_api_key(self, key_id: str) -> None:
        with self._lock:
            for rec in self._doc.get("api_keys", []):
                if rec.get("id") == key_id:
                    rec["last_used_at"] = _now()
                    self.persist()
                    return

    def delete_api_key(self, key_id: str) -> bool:
        with self._lock:
            keys = self._doc.get("api_keys", [])
            new = [r for r in keys if r.get("id") != key_id]
            if len(new) == len(keys):
                return False
            self._doc["api_keys"] = new
            self.persist()
            return True

    # ── active sessions ────────────────────────────────────────────────────
    def register_login(self, user_agent: str, access: str, refresh: str) -> Dict[str, Any]:
        now = _now()
        session = {
            "id": uuid4(),
            "fingerprints": [fingerprint(access), fingerprint(refresh)],
            "user_agent": (user_agent or "")[:300],
            "created_at": now,
            "last_active": now,
            "expires_at": now + _REFRESH_TTL,
            "revoked": False,
        }
        with self._lock:
            self._doc.setdefault("sessions", []).append(session)
            self.persist()
        return session

    def rotate_session(self, old_refresh: str, access: str, refresh: str) -> None:
        """Rebind an existing device session after a token refresh."""
        old_fp = fingerprint(old_refresh)
        with self._lock:
            for s in self._doc.get("sessions", []):
                if not s.get("revoked") and old_fp in s.get("fingerprints", []):
                    s["fingerprints"] = [fingerprint(access), fingerprint(refresh)]
                    s["last_active"] = _now()
                    s["expires_at"] = _now() + _REFRESH_TTL
                    self.persist()
                    return

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(s) for s in self._doc.get("sessions", [])]

    def is_revoked(self, fp: str) -> bool:
        with self._lock:
            for s in self._doc.get("sessions", []):
                if fp in s.get("fingerprints", []):
                    return bool(s.get("revoked"))
            return False

    def touch_session(self, fp: str) -> None:
        with self._lock:
            for s in self._doc.get("sessions", []):
                if fp in s.get("fingerprints", []):
                    s["last_active"] = _now()
                    return

    def revoke_session(self, session_id: str) -> bool:
        with self._lock:
            for s in self._doc.get("sessions", []):
                if s.get("id") == session_id:
                    s["revoked"] = True
                    self.persist()
                    return True
            return False

    def revoke_all_except(self, fp: str) -> int:
        with self._lock:
            revoked = 0
            for s in self._doc.get("sessions", []):
                if not s.get("revoked") and fp not in s.get("fingerprints", []):
                    s["revoked"] = True
                    revoked += 1
            if revoked:
                self.persist()
            return revoked


def uuid4() -> str:
    return secrets.token_hex(6)


# ── module factory ─────────────────────────────────────────────────────────

_current: Optional[AccountStore] = None


def account_store() -> AccountStore:
    global _current
    if _current is None or Path(_current.path) != Path(ACCOUNT_FILE):
        _current = AccountStore(ACCOUNT_FILE)
    return _current


def reset() -> None:
    global _current
    _current = None