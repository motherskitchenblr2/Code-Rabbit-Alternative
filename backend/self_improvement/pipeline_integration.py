# =============================================================================
# Pipeline Integration for the Self-Improvement Engine
# =============================================================================
# Hooks the learning/memory/error-handling engine into the live review
# pipeline so Git-Fix "gets better at reviewing code" with every PR.
#
# Usage from app.py (already wired):
#   from backend.self_improvement.pipeline_integration import (
#       record_webhook, record_review_dispatched, learn_from_webhook_error,
#       practice_on_request, get_engine, maybe_consolidate,
#   )
# =============================================================================

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .orchestrator import SelfImprovementEngine
from .learning.core import FeedbackSignal
from .error_handling.core import ErrorSeverity

logger = logging.getLogger(__name__)

_engine: Optional[SelfImprovementEngine] = None
_engine_lock = threading.Lock()
_last_consolidation: Optional[float] = None
_consolidate_every_seconds = int(os.environ.get("GITFIX_CONSOLIDATE_SECONDS", 8 * 3600))


def get_engine() -> SelfImprovementEngine:
    """Lazily create the shared engine (thread-safe)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                db_path = os.environ.get(
                    "GITFIX_MEMORY_PATH",
                    os.path.join(os.path.expanduser("~"), ".gitfix", "memory", "memory.db"),
                )
                _engine = SelfImprovementEngine(db_path=db_path)
    return _engine


# ---------------------------------------------------------------------------
# Stage hooks
# ---------------------------------------------------------------------------

def record_webhook(repo: Optional[str], pr_number: Optional[int],
                   action: Optional[str], ok: bool = True):
    """Webhook received → episodic memory + skill practice."""
    engine = get_engine()
    engine.track_event(
        "webhook received for pull request",
        {"repo": repo, "pr_number": pr_number, "action": action,
         "outcome": "pass" if ok else "fail", "source": "webhook"},
    )
    engine.practice("pattern_recognition", xp=1,
                    activity=f"parsed webhook for {repo}#{pr_number}")


def record_review_dispatched(repo: Optional[str], pr_number: Optional[int],
                             findings: List[Dict[str, Any]], comment_count: int):
    """A review was dispatched → strongest self-learning signal.

    Each finding category teaches the model what to watch for next time;
    the dispatch itself earns code_analysis XP.
    """
    engine = get_engine()
    categories = [f.get("category", "unknown") for f in findings]
    severities = [f.get("severity", "UNKNOWN") for f in findings]

    engine.track_event(
        "code review dispatched to pull request",
        {"repo": repo, "pr_number": pr_number,
         "findings": len(findings), "comments": comment_count,
         "categories": categories[:10], "severities": severities[:10],
         "outcome": "pass", "source": "review"},  # review completed successfully
    )
    engine.practice("code_analysis", xp=len(findings),
                    activity=f"analyzed {repo}#{pr_number} ({len(findings)} findings)")

    # Feed each finding category into the learning loop as a lesson signal.
    # Fail on a category = "remember to check this pattern again".
    for cat in categories:
        if cat:
            engine.learning.record_feedback(FeedbackSignal(
                event=f"finding-category:{cat}",
                outcome="fail",
                context={"repo": repo, "pr_number": pr_number},
                source="review",
            ))
    maybe_consolidate()


def learn_from_webhook_error(repo: Optional[str], pr_number: Optional[int],
                             error: BaseException):
    """Route a pipeline exception through the self error-handler."""
    engine = get_engine()
    recovered, detail = engine.handle_error(
        f"webhook:{repo}#{pr_number}", error,
        {"repo": repo, "pr_number": pr_number},
    )
    logger.info(
        f"Self-healing {'recovered' if recovered else 'escalated'} "
        f"{type(error).__name__}: {detail['strategy']} ({detail['attempts']} tries)"
    )


def practice_on_request(endpoint: str, outcome: str = "pass"):
    """General-purpose practice hook for any handled request."""
    engine = get_engine()
    engine.practice("self_reflection", xp=1, activity=f"served {endpoint}")
    if outcome in ("fail", "error"):
        engine.learning.record_feedback(FeedbackSignal(
            event=f"pipeline-endpoint:{endpoint}",
            outcome=outcome,
            context={"endpoint": endpoint},
            source="flask",
        ))


# ---------------------------------------------------------------------------
# Consolidation (memory hygiene) & lifecycle
# ---------------------------------------------------------------------------

def maybe_consolidate(force: bool = False) -> bool:
    """Run memory consolidation on a schedule (default every 8h)."""
    global _last_consolidation
    now = time.time()
    if not force and _last_consolidation and \
            (now - _last_consolidation) < _consolidate_every_seconds:
        return False
    try:
        result = get_engine().consolidate()
        _last_consolidation = now
        logger.info(f"Memory consolidation complete: {result}")
        return True
    except Exception as e:
        logger.warning(f"Consolidation failed: {e}")
        return False


def start_consolidator(interval_seconds: Optional[int] = None):
    """Start a daemon consolidator thread (safe to call from app init)."""
    global _consolidate_every_seconds
    if interval_seconds:
        _consolidate_every_seconds = interval_seconds
    t = threading.Thread(target=_consolidator_loop, daemon=True,
                         name="gitfix-consolidator")
    t.start()
    logger.info("Memory consolidator thread started "
                f"(every {_consolidate_every_seconds}s)")
    return t


def _consolidator_loop():
    while True:
        maybe_consolidate(force=True)
        time.sleep(_consolidate_every_seconds)