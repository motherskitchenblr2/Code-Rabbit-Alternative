# =============================================================================
# Self Error Handling & Recovery System
# =============================================================================
# Detects, classifies, recovers from, and learns from errors.
# Tracks failure patterns and builds reflex responses over time.
# =============================================================================

import os
import json
import time
import uuid
import logging
import traceback
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from backend.self_improvement.memory.core import MemorySystem, MemoryType

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRANSIENT = "transient"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    SKIP = "skip"
    ESCALATE = "escalate"


@dataclass
class ErrorEvent:
    id: str
    occurred_at: float
    source: str
    error_type: str
    message: str
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    traceback: str
    context: Dict[str, Any]
    recovered: bool
    recovery_attempts: int


@dataclass
class ReflexRule:
    error_type: str
    source_pattern: str
    recovery_strategy: RecoveryStrategy
    max_attempts: int
    backoff_seconds: float
    message: str
    hits: int = 0
    successes: int = 0

    @property
    def success_rate(self) -> float:
        return (self.successes / self.hits) if self.hits else 1.0


class ErrorHandler:
    """Self error handling with reflex learning."""

    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self._lock = threading.Lock()
        self._reflexes: Dict[str, ReflexRule] = {}
        self._events: List[ErrorEvent] = []
        self._max_events = 100
        self._load_reflexes()

    # ----- Public API ----------------------------------------------------

    def handle(self, source: str, error: BaseException,
               context: Optional[Dict[str, Any]] = None,
               strategy: Optional[RecoveryStrategy] = None) -> Tuple[bool, Dict[str, Any]]:
        """Process an error: classify, recover, learn, escalate on failure.

        Returns (recovered, detail).
        """
        context = context or {}
        event = self._build_event(source, error, context, strategy)
        self._record(event)

        # Try reflex + retry loop
        recovered = self._attempt_recovery(event, context)

        if recovered:
            self._learn_success(event)
            return True, {"event": event.id, "recovered": True,
                           "strategy": event.recovery_strategy.value,
                           "attempts": event.recovery_attempts}
        else:
            self._learn_failure(event)
            return False, {"event": event.id, "recovered": False,
                            "strategy": event.recovery_strategy.value,
                            "attempts": event.recovery_attempts,
                            "escalate": True}

    def register_reflex(self, rule: ReflexRule):
        key = f"{rule.error_type}:{rule.source_pattern}"
        with self._lock:
            self._reflexes[key] = rule

    def get_reflexes(self) -> List[Dict[str, Any]]:
        return [{"error_type": r.error_type,
                 "source_pattern": r.source_pattern,
                 "strategy": r.recovery_strategy.value,
                 "max_attempts": r.max_attempts,
                 "hit_rate": f"{r.success_rate:.0%}",
                 "hits": r.hits,
                 "successes": r.successes}
                for r in self._reflexes.values()]

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {"id": e.id, "source": e.source, "error_type": e.error_type,
             "message": e.message, "severity": e.severity.value,
             "recovered": e.recovered, "attempts": e.recovery_attempts}
            for e in self._events[-limit:]
        ]

    # ----- Core ----------------------------------------------------------

    def _build_event(self, source, error, context, strategy) -> ErrorEvent:
        error_type = type(error).__name__
        # Choose strategy: preferred > reflex > degrade/retry by severity
        chosen = strategy
        if chosen is None:
            existing = self._find_matching_reflex(error_type, source)
            if existing:
                chosen = existing.recovery_strategy
            else:
                chosen = RecoveryStrategy.RETRY

        sev = self._severity_for(error_type, chosen)
        return ErrorEvent(
            id=uuid.uuid4().hex[:12],
            occurred_at=time.time(),
            source=source,
            error_type=error_type,
            message=str(error)[:500],
            severity=sev,
            recovery_strategy=chosen,
            traceback=traceback.format_exc(),
            context=context,
            recovered=False,
            recovery_attempts=0,
        )

    def _find_matching_reflex(self, error_type: str, source: str) -> Optional[ReflexRule]:
        for rule in self._reflexes.values():
            if rule.error_type == error_type and (
                rule.source_pattern in source or rule.source_pattern == "*"
            ):
                return rule
        return None

    def _attempt_recovery(self, event: ErrorEvent, context: dict) -> bool:
        context = context if isinstance(context, dict) else {}
        attempts_allowed = self._max_for(event)
        backoff = self._backoff_for(event)

        for attempt in range(1, attempts_allowed + 1):
            event.recovery_attempts = attempt
            handler = getattr(self, f"_recover_{event.recovery_strategy.value}", None)
            if handler is None:
                handler = self._recover_retry

            try:
                handled = handler(event, context)
                if handled:
                    event.recovered = True
                    return True
            except Exception as e:
                logger.error(f"Recovery handler for {event.error_type} failed: {e}")

            time.sleep(backoff * attempt)

        return False

    def _max_for(self, event: ErrorEvent) -> int:
        rule = self._find_matching_reflex(event.error_type, event.source)
        if rule:
            return rule.max_attempts
        return 1 if event.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH) else 3

    def _backoff_for(self, event: ErrorEvent) -> float:
        rule = self._find_matching_reflex(event.error_type, event.source)
        return rule.backoff_seconds if rule else 0.3

    # ----- Recovery strategies ------------------------------------------

    def _recover_retry(self, event: ErrorEvent, context: dict) -> bool:
        # Re-attempt: caller supplies the operation via context.
        fn = context.get("retry_fn")
        if callable(fn):
            fn()
            return True
        return False

    def _recover_fallback(self, event: ErrorEvent, context: dict) -> bool:
        fb = context.get("fallback")
        if fb is not None:
            context.get("on_fallback", lambda s: None)(fb)
            return True
        return False

    def _recover_degrade(self, event: ErrorEvent, context: dict) -> bool:
        # Disable the failing subsystem, keep the rest running.
        target = context.get("subsystem")
        logger.warning(f"Degrading subsystem: {target} after {event.error_type}")
        return True

    def _recover_skip(self, event: ErrorEvent, context: dict) -> bool:
        logger.info(f"Skipping {event.source} after {event.error_type} (non-fatal)")
        return True

    def _recover_escalate(self, event: ErrorEvent, context: dict) -> bool:
        logger.error(f"ESCALATED: {event.source} — {event.message}")
        return False

    # ----- Learning ------------------------------------------------------

    def _learn_success(self, event: ErrorEvent):
        """Strengthen or create the reflex that worked."""
        key = f"{event.error_type}:{event.source}"
        with self._lock:
            if key in self._reflexes:
                rule = self._reflexes[key]
                rule.hits += 1
                rule.successes += 1
            else:
                rule = ReflexRule(
                    error_type=event.error_type,
                    source_pattern=event.source,
                    recovery_strategy=event.recovery_strategy,
                    max_attempts=self._max_for(event),
                    backoff_seconds=0.3,
                    message=event.message,
                    hits=1, successes=1,
                )
                self._reflexes[key] = rule
            self._persist_reflex(rule)

        self.memory.remember_episode(
            f"Recovered {event.error_type} in {event.source} via "
            f"{event.recovery_strategy.value}",
            {"event_id": event.id, "strategy": event.recovery_strategy.value,
             "attempts": event.recovery_attempts},
            importance=2,
        )

    def _learn_failure(self, event: ErrorEvent):
        """Record failure + create a corrective procedure."""
        with self._lock:
            key = f"{event.error_type}:{event.source}"
            if key in self._reflexes:
                self._reflexes[key].hits += 1
                self._persist_reflex(self._reflexes[key])

        self.memory.remember_episode(
            f"Failed to recover {event.error_type} in {event.source}",
            {"event_id": event.id, "message": event.message,
             "traceback": event.traceback[:800]},
            importance=3,
        )
        self.memory.remember_procedure(
            f"avoid:{event.error_type}",
            ["Detect precondition matching error type",
             "Apply corrective action before it can occur",
             "Verify fix did not introduce new failure"],
            success_rate=0.5,
            metadata={"source": event.source, "message": event.message[:200]},
            importance=2,
        )

    # ----- Helpers -------------------------------------------------------

    def _record(self, event: ErrorEvent):
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        logger.info(
            f"ErrorEvent [{event.id}] {event.error_type} @ {event.source} "
            f"sev={event.severity.value} strategy={event.recovery_strategy.value}"
        )

    def _severity_for(self, error_type: str, strategy: RecoveryStrategy) -> ErrorSeverity:
        if error_type in ("PermissionError", "AuthenticationError", "SecurityError"):
            return ErrorSeverity.CRITICAL
        if strategy is RecoveryStrategy.ESCALATE:
            return ErrorSeverity.HIGH
        if error_type in ("TimeoutError", "ConnectionError", "BrokenPipeError"):
            return ErrorSeverity.TRANSIENT
        return ErrorSeverity.MEDIUM

    def _persist_reflex(self, rule: ReflexRule):
        # Reflexes survive restarts via a JSON sidecar file.
        path = os.path.join(os.path.dirname(self.memory.db_path), "reflexes.json")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            state = {}
            if os.path.exists(path):
                with open(path) as f:
                    state = json.load(f)
            state[f"{rule.error_type}:{rule.source_pattern}"] = {
                "error_type": rule.error_type,
                "source_pattern": rule.source_pattern,
                "strategy": rule.recovery_strategy.value,
                "max_attempts": rule.max_attempts,
                "backoff_seconds": rule.backoff_seconds,
                "message": rule.message,
                "hits": rule.hits,
                "successes": rule.successes,
            }
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist reflexes: {e}")

    def _load_reflexes(self):
        path = os.path.join(os.path.dirname(self.memory.db_path), "reflexes.json")
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                state = json.load(f)
            for key, data in state.items():
                self._reflexes[key] = ReflexRule(
                    error_type=data["error_type"],
                    source_pattern=data["source_pattern"],
                    recovery_strategy=RecoveryStrategy(data["strategy"]),
                    max_attempts=data.get("max_attempts", 3),
                    backoff_seconds=data.get("backoff_seconds", 0.3),
                    message=data.get("message", ""),
                    hits=data.get("hits", 0),
                    successes=data.get("successes", 0),
                )
        except Exception as e:
            logger.warning(f"Could not load reflexes: {e}")