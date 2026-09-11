# =============================================================================
# Self-Improvement Orchestrator
# =============================================================================
# Ties together memory, error handling, learning, and development into one
# self-aware engine that compounds its own knowledge over time.
# =============================================================================

import os
import json
import time
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from .memory.core import MemorySystem, MemoryType
from .error_handling.core import ErrorHandler, ReflexRule, RecoveryStrategy, ErrorSeverity
from .learning.core import LearningEngine, FeedbackSignal
from .development.core import DevelopmentEngine

logger = logging.getLogger(__name__)

SEED_REFLEXES = [
    ReflexRule(
        error_type="TimeoutError",
        source_pattern="*",
        recovery_strategy=RecoveryStrategy.RETRY,
        max_attempts=3,
        backoff_seconds=0.5,
        message="Network/host timeout — retry with backoff",
    ),
    ReflexRule(
        error_type="ConnectionError",
        source_pattern="*",
        recovery_strategy=RecoveryStrategy.RETRY,
        max_attempts=3,
        backoff_seconds=0.4,
        message="Connection dropped — reconnect and retry",
    ),
    ReflexRule(
        error_type="OSError",
        source_pattern="*",
        recovery_strategy=RecoveryStrategy.DEGRADE,
        max_attempts=2,
        backoff_seconds=0.2,
        message="File/system error — degrade subsystem gracefully",
    ),
    ReflexRule(
        error_type="PermissionError",
        source_pattern="*",
        recovery_strategy=RecoveryStrategy.SKIP,
        max_attempts=1,
        backoff_seconds=0.0,
        message="Permission denied — skip, log, continue",
    ),
]


class SelfImprovementEngine:
    """Unified self-improvement engine."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(Path.home(), ".gitfix", "memory", "memory.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.memory = MemorySystem(db_path)
        self.errors = ErrorHandler(self.memory)
        self.learning = LearningEngine(self.memory)
        self.development = DevelopmentEngine(self.memory)
        self._status = "idle"
        self._uptime = time.time()

        for reflex in SEED_REFLEXES:
            self.errors.register_reflex(reflex)

        self._archive_stats()

    # ----- High-level API -----------------------------------------------

    def track_event(self, event_name: str, context: Optional[dict] = None):
        """Record an event and feed it into the learning loop."""
        context = context or {}
        self.memory.remember_episode(event_name, context, importance=1)

        if context.get("outcome"):
            self.learning.record_feedback(FeedbackSignal(
                event=event_name,
                outcome=context.pop("outcome", "pass"),
                context=context,
                source=context.pop("source", "track_event"),
            ))

    def handle_error(self, source: str, error: BaseException,
                     context: Optional[dict] = None) -> Tuple[bool, dict]:
        """Self-healing error handling with reflex + retry."""
        result = self.errors.handle(source, error, context)
        recovered, detail = result
        return recovered, detail

    def practice(self, skill: str, xp: int = 1, activity: str = ""):
        """Log deliberate practice toward a skill; returns updated skill."""
        return self.development.train(skill, xp, activity)

    def propose_goal(self, name: str, description: str, target_skill: str,
                     milestones: List[str], deadline: Optional[float] = None):
        """Set a development goal."""
        return self.development.add_goal(name, description, target_skill,
                                         milestones, deadline)

    def get_plan(self) -> List[Dict[str, Any]]:
        """Auto-generated improvement plan."""
        self.practice("self_reflection", 2, "generated improvement plan")
        return self.development.improvement_plan()

    # ----- Introspection API --------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "uptime_seconds": int(time.time() - self._uptime),
            "memory": self.memory.stats(),
            "skills": self.development.assess(),
            "reflexes": self.errors.get_reflexes(),
            "recent_errors": self.errors.get_recent_events(limit=10),
            "improvement_plan": self.get_plan()[:5],
        }

    def consolidate(self):
        """Evening-like consolidation: strengthen important memories."""
        result = self.memory.consolidate()
        self.practice("consolidation", 1, "consolidated memories")
        return result

    def snapshot(self) -> Dict[str, Any]:
        """Export full state for backup / inspection."""
        return {
            "status": self.status(),
            "goals": self.development.get_goals(),
            "lessons": [l.__dict__ for l in self.learning.get_lessons()],
            "all_memories": [
                m.to_dict() for m in self.memory.recall(limit=1000)
            ],
        }

    def _archive_stats(self):
        """Persist a lightweight stats heartbeat."""
        try:
            path = os.path.join(os.path.dirname(self.memory.db_path), "heartbeat.json")
            stats = self.memory.stats()
            stats["created_at"] = time.time()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(stats, f)
        except Exception as e:
            logger.warning(f"Could not archive stats: {e}")