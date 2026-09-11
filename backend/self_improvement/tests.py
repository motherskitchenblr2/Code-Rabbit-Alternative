#!/usr/bin/env python3
# =============================================================================
# Tests for the Self-Improvement subsystem
# =============================================================================
# Runs in the project root with:
#   python -m backend.self_improvement.tests
# =============================================================================

import os
import sys
import time
import json
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from backend.self_improvement.memory.core import MemorySystem, MemoryType
from backend.self_improvement.error_handling.core import (
    ErrorHandler, ErrorSeverity, RecoveryStrategy, ReflexRule,
)
from backend.self_improvement.learning.core import LearningEngine, FeedbackSignal
from backend.self_improvement.development.core import (
    DevelopmentEngine, SkillLevel, GoalStatus,
)
from backend.self_improvement.orchestrator import SelfImprovementEngine

TEST_DB = os.path.join(os.path.dirname(__file__), "_test_memory.db")
TEST_DEV = os.path.join(os.path.dirname(__file__), "_test_dev.json")


class _ResetMixin:
    def setUp(self):
        for p in [TEST_DB, TEST_DEV,
                  os.path.join(os.path.dirname(TEST_DB), "reflexes.json"),
                  os.path.join(os.path.dirname(TEST_DB), "heartbeat.json")]:
            if os.path.exists(p):
                os.remove(p)
        os.makedirs(os.path.dirname(TEST_DB), exist_ok=True)


class _SecurityError(Exception):
    pass


class TestMemory(_ResetMixin, unittest.TestCase):

    def test_store_and_get(self):
        ms = MemorySystem(TEST_DB)
        mid = ms.store(MemoryType.SEMANTIC, "fact:python", "Python is great",
                       importance=3, tags=["lang"])
        m = ms.get(mid)
        self.assertIsNotNone(m)
        self.assertEqual(m.key, "fact:python")
        self.assertIn("great", m.content)

    def test_recall_type_filter(self):
        ms = MemorySystem(TEST_DB)
        ms.store(MemoryType.SEMANTIC, "k1", "v1", tags=["t1"])
        ms.store(MemoryType.EPISODIC, "k2", "v2", tags=["t2"])
        s = ms.recall(mtype=MemoryType.SEMANTIC)
        e = ms.recall(mtype=MemoryType.EPISODIC)
        self.assertTrue(len(s) >= 1)
        self.assertTrue(len(e) >= 1)
        self.assertTrue(all(m.type == MemoryType.SEMANTIC for m in s))
        self.assertTrue(all(m.type == MemoryType.EPISODIC for m in e))

    def test_search_keyword(self):
        ms = MemorySystem(TEST_DB)
        ms.store(MemoryType.SEMANTIC, "secret:api", "API key found in config",
                 tags=["secret"])
        ms.store(MemoryType.SEMANTIC, "fact:go", "Go compiles fast",
                 tags=["lang"])
        results = ms.search("API key")
        self.assertTrue(any("api" in m.key.lower() for m in results))

    def test_deduplication_on_key(self):
        ms = MemorySystem(TEST_DB)
        ms.store(MemoryType.SEMANTIC, "x", "first", importance=1)
        ms.store(MemoryType.SEMANTIC, "x", "second", importance=2)
        m = ms.get(1)
        self.assertEqual(m.content, "second")
        self.assertEqual(m.importance, 2)

    def test_delete(self):
        ms = MemorySystem(TEST_DB)
        mid = ms.store(MemoryType.EPISODIC, "to_delete", "temp")
        n = ms.forget(memory_id=mid)
        self.assertEqual(n, 1)
        self.assertIsNone(ms.get(mid))

    def test_stats(self):
        ms = MemorySystem(TEST_DB)
        ms.store(MemoryType.SEMANTIC, "s1", "x")
        ms.store(MemoryType.EPISODIC, "e1", "y")
        stats = ms.stats()
        self.assertEqual(stats["total_memories"], 2)
        self.assertIn("semantic", stats["by_type"])
        self.assertIn("episodic", stats["by_type"])

    def test_consolidate(self):
        ms = MemorySystem(TEST_DB)
        ms.store(MemoryType.SEMANTIC, "important", "very", importance=4)
        ms.store(MemoryType.SEMANTIC, "unimportant", "meh", importance=1)
        result = ms.consolidate()
        self.assertIn("rehearsed", result)
        self.assertGreaterEqual(result["rehearsed"], 1)


class TestErrorHandling(_ResetMixin, unittest.TestCase):

    def test_handle_with_fallback(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        received = {}
        recovered, detail = eh.handle(
            "test-worker", ValueError("bad input"),
            {"fallback": "cached-result", "on_fallback": lambda v: received.update(v=v)},
            RecoveryStrategy.FALLBACK,
        )
        self.assertTrue(recovered)
        self.assertEqual(received.get("v"), "cached-result")

    def test_handle_with_skip(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        recovered, _ = eh.handle("test", RuntimeError("boom"),
                                 {}, strategy=RecoveryStrategy.SKIP)
        self.assertTrue(recovered)

    def test_handle_unrecoverable_returns_escalate(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        recovered, detail = eh.handle("test", _SecurityError("forbidden"),
                                      {}, strategy=RecoveryStrategy.ESCALATE)
        self.assertFalse(recovered)

    def test_reflex_registration(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        rule = ReflexRule(
            error_type="TimeoutError",
            source_pattern="api-service",
            recovery_strategy=RecoveryStrategy.RETRY,
            max_attempts=5,
            backoff_seconds=0.2,
            message="custom timeout reflex",
        )
        eh.register_reflex(rule)
        reflexes = eh.get_reflexes()
        api_reflexes = [r for r in reflexes if r["source_pattern"] == "api-service"]
        self.assertEqual(len(api_reflexes), 1)
        self.assertEqual(api_reflexes[0]["strategy"], "retry")

    def test_severity_classification(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        sev = eh._severity_for("PermissionError", RecoveryStrategy.SKIP)
        self.assertEqual(sev, ErrorSeverity.CRITICAL)
        sev = eh._severity_for("TimeoutError", RecoveryStrategy.RETRY)
        self.assertEqual(sev, ErrorSeverity.TRANSIENT)

    def test_recent_events_recorded(self):
        ms = MemorySystem(TEST_DB)
        eh = ErrorHandler(ms)
        eh.handle("w1", OSError("disk"), {}, strategy=RecoveryStrategy.DEGRADE)
        events = eh.get_recent_events()
        self.assertTrue(any(e["error_type"] == "OSError" for e in events))


class TestLearning(_ResetMixin, unittest.TestCase):

    def test_feedback_creates_lesson(self):
        ms = MemorySystem(TEST_DB)
        le = LearningEngine(ms)
        le.record_feedback(FeedbackSignal(
            event="build-failure type=timeout",
            outcome="fail",
            context={"file": "server.py"},
            source="ci",
        ))
        lessons = le.get_lessons()
        self.assertTrue(len(lessons) >= 1)

    def test_pass_feedback_strengthens(self):
        ms = MemorySystem(TEST_DB)
        le = LearningEngine(ms)
        for _ in range(3):
            le.record_feedback(FeedbackSignal(
                event="api-call-happy-path",
                outcome="pass",
                context={},
                source="test",
            ))
        lessons = le.get_lessons(subject="api call happy")
        if lessons:
            self.assertGreater(lessons[0].confidence, 0.5)

    def test_retry_feedback_reduces_confidence(self):
        ms = MemorySystem(TEST_DB)
        le = LearningEngine(ms)
        le.record_feedback(FeedbackSignal("flaky-test", "fail", {}, "ci"))
        before = le.get_lessons(subject="flaky test")
        if before:
            old_conf = before[0].confidence
            le.record_feedback(FeedbackSignal("flaky-test", "retry", {}, "ci"))
            after = le.get_lessons(subject="flaky test")
            # Confidence should be lower or equal after a retry
            self.assertLessEqual(after[0].confidence, old_conf)


class TestDevelopment(_ResetMixin, unittest.TestCase):

    def _make_engine(self):
        ms = MemorySystem(TEST_DB)
        # Override the dev state path for isolation
        import backend.self_improvement.development.core as dc
        orig = dc.DevelopmentEngine._state_path
        dc.DevelopmentEngine._state_path = lambda self: TEST_DEV
        de = DevelopmentEngine(ms)
        dc.DevelopmentEngine._state_path = orig
        return ms, de

    def test_skill_training(self):
        ms, de = self._make_engine()
        s = de.train("testing", xp=30, activity="built test suite")
        self.assertEqual(s.level, SkillLevel.COMPETENT)
        self.assertEqual(s.experience_points, 30)

    def test_goal_milestones(self):
        ms, de = self._make_engine()
        g = de.add_goal("Deploy v1", "ship it", "devops", ["ci-cd", "staging", "prod"])
        self.assertEqual(g.status, GoalStatus.IN_PROGRESS)
        de.mark_milestone(g.id, "ci-cd")
        de.mark_milestone(g.id, "staging")
        goals = de.get_goals()
        matching = [x for x in goals if x["id"] == g.id][0]
        self.assertAlmostEqual(matching["progress"], 2/3, places=2)

    def test_improvement_plan(self):
        ms, de = self._make_engine()
        de.train("test-skill", xp=3)
        plan = de.improvement_plan()
        self.assertIsInstance(plan, list)
        self.assertTrue(any("test-skill" in p["action"] for p in plan))

    def test_level_promotion(self):
        ms, de = self._make_engine()
        s1 = de.train("code_review", xp=10)
        self.assertEqual(s1.level, SkillLevel.DEVELOPING)
        s2 = de.train("code_review", xp=15)
        self.assertEqual(s2.level, SkillLevel.COMPETENT)


class TestOrchestrator(_ResetMixin, unittest.TestCase):

    def test_full_cycle(self):
        engine = SelfImprovementEngine(db_path=TEST_DB)

        engine.track_event("test-event", {"outcome": "pass", "source": "unittest"})
        engine.practice("error_recovery", 5, "unit test recovery")

        goal = engine.propose_goal("Test goal", "desc", "error_recovery",
                                   ["m1", "m2"])
        engine.development.mark_milestone(goal.id, "m1")

        recovered, _ = engine.handle_error("worker", TimeoutError("slow"),
                                           {"retry_fn": lambda: None})
        self.assertTrue(recovered)

        status = engine.status()
        self.assertEqual(status["status"], "idle")
        self.assertGreater(status["memory"]["total_memories"], 0)
        self.assertGreater(len(status["reflexes"]), 0)
        self.assertGreater(len(status["skills"]), 0)

    def test_snapshot_contains_all(self):
        engine = SelfImprovementEngine(db_path=TEST_DB)
        engine.track_event("a", {"outcome": "pass", "source": "s"})
        snap = engine.snapshot()
        self.assertIn("status", snap)
        self.assertIn("goals", snap)
        self.assertIn("lessons", snap)
        self.assertIn("all_memories", snap)


if __name__ == "__main__":
    unittest.main(verbosity=2)