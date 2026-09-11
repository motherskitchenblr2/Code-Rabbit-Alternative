# =============================================================================
# Self-Learning Pipeline
# =============================================================================
# Extracts patterns from experiences, builds feedback loops, records lessons.
# Turns raw events into knowledge the agent actually reuses.
# =============================================================================

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict

from backend.self_improvement.memory.core import MemorySystem, MemoryType

logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    id: str
    subject: str
    rule: str
    evidence: str
    confidence: float
    source: str
    created_at: float
    applications: int = 0


@dataclass
class FeedbackSignal:
    event: str
    outcome: str  # pass | fail | bypass | retry
    context: Dict[str, Any]
    source: str
    timestamp: float = field(default_factory=time.time)


class LearningEngine:
    """Extracts reusable lessons from raw feedback signals."""

    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self._lessons: List[Lesson] = []
        self._signals: List[FeedbackSignal] = []
        self._pattern_counts: Counter = Counter()
        self._load_lessons()

    # ----- Public API ----------------------------------------------------

    def record_feedback(self, signal: FeedbackSignal):
        """Feed an outcome signal into the learning pipeline."""
        self._signals.append(signal)
        self._update_pattern_counts(signal)
        self._extract_lesson(signal)

    def get_lessons(self, subject: Optional[str] = None,
                    min_confidence: float = 0.0) -> List[Lesson]:
        out = [l for l in self._lessons
               if (subject is None or subject in l.subject)
               and l.confidence >= min_confidence]
        out.sort(key=lambda l: -l.confidence)
        return out

    def count_lesson(self, lesson_id: str):
        for l in self._lessons:
            if l.id == lesson_id:
                l.applications += 1
                break

    def suggest_improvements(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Surface the highest-confidence, under-applied lessons."""
        lessons = sorted(self._lessons, key=lambda l: -l.confidence)
        return [
            {"id": l.id, "subject": l.subject, "rule": l.rule,
             "confidence": l.confidence, "applications": l.applications}
            for l in lessons[:limit]
        ]

    # ----- Internals ----------------------------------------------------

    def _update_pattern_counts(self, signal: FeedbackSignal):
        for token in self._tokenize(signal.event):
            self._pattern_counts[token] += 1
        for token in self._tokenize(f"{signal.outcome} {signal.source}"):
            self._pattern_counts[token] += 1

    def _extract_lesson(self, signal: FeedbackSignal):
        """Derive a lesson from a single signal via lightweight heuristics."""
        if signal.outcome == "fail":
            # Problem -> avoid-pattern lesson
            subject = self._subject_of(signal)
            rule = f"Avoid repeating {subject}: {self._shorten(signal.event)}"
            lesson = Lesson(
                id=hashlib_short(f"fail:{subject}"),
                subject=subject,
                rule=rule,
                evidence=f"{signal.context}",
                confidence=0.6,
                source=signal.source,
                created_at=signal.timestamp,
            )
            self._upsert_lesson(lesson, boost=0.15)

        elif signal.outcome == "pass":
            subject = self._subject_of(signal)
            lesson = Lesson(
                id=hashlib_short(f"pass:{subject}"),
                subject=subject,
                rule=f"Repeat successful approach for {subject}: "
                     f"{self._shorten(signal.event)}",
                evidence=f"{signal.context}",
                confidence=0.5,
                source=signal.source,
                created_at=signal.timestamp,
            )
            self._upsert_lesson(lesson, boost=0.1)

        elif signal.outcome == "retry":
            subject = self._subject_of(signal)
            existing = [l for l in self._lessons if subject in l.subject]
            for l in existing:
                l.confidence = min(1.0, l.confidence - 0.05)
                l.applications += 1

        self._memory_store(signal)

    def _upsert_lesson(self, lesson: Lesson, boost: float = 0.0):
        for existing in self._lessons:
            if existing.id == lesson.id:
                existing.confidence = min(1.0, existing.confidence + boost)
                existing.evidence = lesson.evidence
                return
        # Chemical-grade guard: only keep lessons above a quality floor
        if len(lesson.rule) >= 15:
            self._lessons.append(lesson)
            self._persist_lesson(lesson)

    def _subject_of(self, signal: FeedbackSignal) -> str:
        tokens = self._tokenize(signal.event)
        # First meaningful noun-ish token cluster wins
        stops = {"the", "to", "of", "a", "an", "in", "for", "on", "with", "and", "or"}
        meaningful = [t for t in tokens if t not in stops and len(t) > 2]
        return " ".join(meaningful[:3]) if meaningful else signal.source

    def _tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{1,}", text)]

    def _shorten(self, text: str, maxlen: int = 80) -> str:
        text = " ".join(text.split())
        return text[:maxlen] + ("…" if len(text) > maxlen else "")

    def _memory_store(self, signal: FeedbackSignal):
        self.memory.store(
            MemoryType.EPISODIC,
            f"signal:{hashlib_short(signal.event)}",
            signal.event,
            {"outcome": signal.outcome, "source": signal.source,
             "context": signal.context},
            importance=2,
            tags=["feedback", signal.outcome],
        )

    # ----- Persistence ---------------------------------------------------

    def _persist_lesson(self, lesson: Lesson):
        self.memory.store(
            MemoryType.PROCEDURAL,
            f"lesson:{lesson.id}",
            lesson.rule,
            {"subject": lesson.subject, "evidence": lesson.evidence,
             "confidence": lesson.confidence, "source": lesson.source},
            importance=int(2 + lesson.confidence * 2),
            tags=["lesson", lesson.subject[:20]],
        )

    def _load_lessons(self):
        for mem in self.memory.recall(mtype=MemoryType.PROCEDURAL,
                                      tags=["lesson"], limit=100):
            try:
                md = mem.metadata
                self._lessons.append(Lesson(
                    id=md.get("subject", "unknown").replace(" ", ":"),
                    subject=md.get("subject", "unknown"),
                    rule=mem.content,
                    evidence=md.get("evidence", ""),
                    confidence=md.get("confidence", 0.5),
                    source=md.get("source", ""),
                    created_at=mem.created_at,
                    applications=0,
                ))
            except Exception as e:
                logger.debug(f"Skip malformed lesson memory: {e}")


def hashlib_short(text: str) -> str:
    import hashlib
    return hashlib.sha1(text.encode()).hexdigest()[:10]