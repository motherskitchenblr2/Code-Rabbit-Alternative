# =============================================================================
# Background task queue fallback (Phase 2)
# =============================================================================
# When Celery/Redis is not installed or configured, transparently falls back to
# an in-process ThreadPoolExecutor so webhook processing (and other async work)
# never blocks the request thread. Real Celery can be wired later; the public
# API surface here stays identical.
#
# Usage:
#   from backend.queue import submit
#   submit(record_webhook, repo, pr_number, action)
# =============================================================================

import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

logger = logging.getLogger(__name__)

_pool: ThreadPoolExecutor | None = None
_pool_lock = threading.Lock()
DEFAULT_WORKERS = 4


def get_pool() -> ThreadPoolExecutor:
    """Return the module-level executor, creating it lazily (thread-safe)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                workers = int(os.environ.get("GITFIX_BG_WORKERS", DEFAULT_WORKERS))
                _pool = ThreadPoolExecutor(
                    max_workers=max(1, workers),
                    thread_name_prefix="gitfix-bg",
                )
    return _pool


def submit(fn: Callable, *args: Any, **kwargs: Any):
    """Dispatch a function to the background pool.

    If a real message broker is expected in the future, this is the single
    choke point to swap for a Celery `.delay()`/`.apply_async()` call. Never
    blocks the caller; failures logged, never raised to the request.
    """
    def _wrapped(*a, **k):
        try:
            fn(*a, **k)
        except Exception:
            logger.exception("Background task %s failed", getattr(fn, "__name__", fn))
    try:
        get_pool().submit(_wrapped, *args, **kwargs)
    except RuntimeError:
        # Pool already shut down (e.g. interpreter exiting). Run inline rather
        # than silently dropping the work.
        logger.warning("Background pool unavailable; running %s inline",
                       getattr(fn, "__name__", fn))
        _wrapped(*args, **kwargs)


def shutdown(wait: bool = True) -> None:
    """Gracefully stop the background pool (safe to call more than once)."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            pool = _pool
            _pool = None
            pool.shutdown(wait=wait, cancel_futures=False)