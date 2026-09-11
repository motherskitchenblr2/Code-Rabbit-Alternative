# =============================================================================
# Core configuration helpers (Phase 2)
# =============================================================================
# Loads a local .env when present (never overriding real env vars), provides a
# central memory-store path resolver that understands sqlite:// DATABASE_URLs,
# and exposes structured-logging configuration. All accesses are defensive so
# the app never breaks when a dependency is missing.
# =============================================================================

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv as _dotenv_load
except ImportError:
    _dotenv_load = None


def load_env(path=None):
    """Best-effort .env loader. Never overrides variables already in os.environ.

    Searches the current directory, then the repository root (two levels up
    from this file) when no explicit path is given. Any failure is swallowed --
    the app falls back to plain environment variables. Set GITFIX_SKIP_DOTENV=1
    to disable .env loading entirely (e.g. fail-loud boot tests).
    """
    if os.environ.get("GITFIX_SKIP_DOTENV") == "1":
        return
    if _dotenv_load is None:
        return
    candidates = []
    if path:
        candidates.append(path)
    else:
        cwd = os.path.abspath(os.getcwd())
        candidates.append(os.path.join(cwd, ".env"))
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates.append(os.path.join(repo_root, ".env"))
    for candidate in candidates:
        try:
            _dotenv_load(candidate, override=False, verbose=False)
        except Exception as exc:  # pragma: no cover - defensive only
            logger.debug("Failed to load env file %s: %s", candidate, exc)


def memory_db_path():
    """Resolve the memory-store SQLite file path.

    Precedence:
      1. GITFIX_MEMORY_PATH (explicit override, current behavior)
      2. DATABASE_URL when it uses a sqlite:// or sqlite:/// scheme
      3. ~/.gitfix/memory/memory.db (default)

    A postgresql:// DATABASE_URL keeps the SQLite fallback (the memory store is
    sqlite3-backed) and logs an informational line rather than failing.
    """
    explicit = os.environ.get("GITFIX_MEMORY_PATH")
    if explicit:
        return explicit

    url = os.environ.get("DATABASE_URL") or ""
    if url.startswith("sqlite:///"):
        candidate = url[len("sqlite:///"):]
        if candidate and not candidate.startswith(":"):
            return candidate

    default = os.path.join(Path.home(), ".gitfix", "memory", "memory.db")
    if url.startswith("postgres"):
        logger.info(
            "DATABASE_URL uses PostgreSQL; memory store keeps SQLite fallback (%s). "
            "Full SQLAlchemy/Postgres migration is a follow-up change.",
            default,
        )
    return default


def log_level():
    """Parse LOG_LEVEL env into a logging level (default INFO)."""
    raw = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def log_format():
    """Backwards-compatible stub returning the text default format.

    ``LOG_FORMAT`` is fully handled by :func:`formatter`; this helper is kept
    for parity with earlier imports of ``log_format()``.
    """
    return "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    """Attach a default request_id so %(request_id)s never fails."""

    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    """Single-line JSON logs (LOG_FORMAT=json). Safe with any record."""

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def formatter():
    """Return the Formatter for the LOG_FORMAT env value.

    ``json`` selects JSON output; any other value is used as a %-style format
    string when valid, otherwise the default text format is used so a
    misconfigured value never crashes boot.
    """
    raw = (os.environ.get("LOG_FORMAT") or "").strip().lower()
    if raw == "json":
        return JsonFormatter()
    if raw:
        try:
            logging.Formatter(raw)
            return logging.Formatter(raw)
        except ValueError:
            logger.warning("Ignoring invalid LOG_FORMAT=%r (not %% style)", raw)
    return logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
    )