# =============================================================================
# Self-Improvement Flask API Blueprint
# =============================================================================
# REST endpoints for memory, error handling, learning, development.
# Mount in app.py via:
#   from backend.self_improvement.api import self_improvement_bp, init_self_improvement
#   init_self_improvement(app)
# =============================================================================

import os
import json
import time
import logging
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import asdict
from functools import wraps

from flask import Blueprint, request, jsonify, g

from backend.security import rate_limit, require_admin
from backend.config import memory_db_path
from .orchestrator import SelfImprovementEngine
from .error_handling.core import ErrorHandler, ErrorSeverity, RecoveryStrategy, ReflexRule
from .learning.core import FeedbackSignal
from .development.core import GoalStatus

try:
    from pydantic import BaseModel, Field, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)

self_improvement_bp = Blueprint(
    "self_improvement", __name__,
    url_prefix="/api/self-improvement",
)

_engine: Optional[SelfImprovementEngine] = None


if PYDANTIC_AVAILABLE:
    class MemoryStoreRequest(BaseModel):
        key: str = Field(..., min_length=1, max_length=500)
        content: str = Field(..., min_length=1, max_length=50000)
        type: str = Field("episodic", max_length=50)
        metadata: Optional[Dict[str, Any]] = None
        importance: int = Field(2, ge=0, le=10)
        tags: Optional[List[str]] = Field(None, max_length=50)

    class FeedbackRequest(BaseModel):
        event: str = Field(..., min_length=1, max_length=500)
        outcome: str = Field("pass", max_length=100)
        context: Dict[str, Any] = {}
        source: str = Field("api", max_length=100)

    class SkillsTrainRequest(BaseModel):
        skill: str = Field(..., min_length=1, max_length=200)
        xp: int = Field(1, ge=0, le=1000)
        activity: str = Field("", max_length=500)

    class GoalsCreateRequest(BaseModel):
        name: str = Field(..., min_length=1, max_length=500)
        description: str = Field(..., max_length=5000)
        target_skill: str = Field(..., max_length=200)
        milestones: List[str] = Field(..., min_length=1, max_length=50)
        deadline: Optional[str] = Field(None, max_length=100)

    class MilestoneRequest(BaseModel):
        milestone: str = Field(..., min_length=1, max_length=500)

    class ErrorsHandleRequest(BaseModel):
        source: str = Field("api", max_length=200)
        error_type: str = Field("RuntimeError", max_length=100)
        message: str = Field("simulated error", max_length=5000)
        context: Dict[str, Any] = {}

    class ReflexRegisterRequest(BaseModel):
        error_type: str = Field(..., min_length=1, max_length=100)
        strategy: str = Field(..., max_length=50)
        source_pattern: str = Field("*", max_length=500)
        max_attempts: int = Field(3, ge=1, le=50)
        backoff_seconds: float = Field(0.3, ge=0.0, le=3600.0)
        message: str = Field("", max_length=1000)


def _payload(data, model_class):
    """Validate via Pydantic when available, else return raw data."""
    if PYDANTIC_AVAILABLE:
        try:
            return model_class(**data), None
        except ValidationError as e:
            return None, {"error": "Invalid request", "details": e.errors()}
    return data, None


def get_engine() -> SelfImprovementEngine:
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine(db_path=memory_db_path())
    return _engine


def init_self_improvement(app, db_path: Optional[str] = None):
    """Initialize the engine and register the blueprint."""
    global _engine
    if db_path is None:
        db_path = memory_db_path()
    _engine = SelfImprovementEngine(db_path=db_path)

    # Share the single engine instance with the pipeline integration hooks so
    # all subsystems write to the same in-memory state.
    from . import pipeline_integration as _pi
    _pi._engine = _engine

    app.register_blueprint(self_improvement_bp)
    logger.info("Self-improvement API mounted at /api/self-improvement")


# ---------------------------------------------------------------------------
# Status & introspection
# ---------------------------------------------------------------------------

@self_improvement_bp.route("/status", methods=["GET"])
def status():
    engine = get_engine()
    return jsonify(engine.status())


@self_improvement_bp.route("/snapshot", methods=["GET"])
def snapshot():
    engine = get_engine()
    return jsonify(engine.snapshot())


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def _safe_limit(args_key: str = "limit", default: int = 50) -> int:
    try:
        return max(1, min(int(request.args.get(args_key, default)), 500))
    except (TypeError, ValueError):
        return default


@self_improvement_bp.route("/memory", methods=["GET"])
def memory_list():
    engine = get_engine()
    mtype  = request.args.get("type")
    tags   = request.args.getlist("tag")
    query  = request.args.get("q")
    limit  = _safe_limit("limit", 50)

    kwargs: Dict[str, Any] = {"limit": limit}
    if query:
        results = engine.memory.search(query, limit=limit)
    else:
        results = engine.memory.recall(
            mtype=mtype, tags=tags or None, limit=limit,
        )
    return jsonify({"memories": [m.to_dict() for m in results]})


@self_improvement_bp.route("/memory", methods=["POST"])
@rate_limit(60, 60)
@require_admin
def memory_store():
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, MemoryStoreRequest)
    if err:
        return jsonify(err), 400
    if not data or "key" not in data or "content" not in data:
        return jsonify({"error": "key and content are required"}), 400

    mid = engine.memory.store(
        mtype=data.get("type", "episodic"),
        key=data["key"],
        content=data["content"],
        metadata=data.get("metadata"),
        importance=data.get("importance", 2),
        tags=data.get("tags"),
    )
    return jsonify({"id": mid}), 201


@self_improvement_bp.route("/memory/<int:memory_id>", methods=["GET"])
def memory_get(memory_id):
    engine = get_engine()
    m = engine.memory.get(memory_id)
    if not m:
        return jsonify({"error": "not found"}), 404
    return jsonify(m.to_dict())


@self_improvement_bp.route("/memory/<int:memory_id>", methods=["DELETE"])
@rate_limit(30, 60)
@require_admin
def memory_delete(memory_id):
    engine = get_engine()
    n = engine.memory.forget(memory_id=memory_id)
    return jsonify({"deleted": n})


@self_improvement_bp.route("/memory/stats", methods=["GET"])
def memory_stats():
    return jsonify(get_engine().memory.stats())


@self_improvement_bp.route("/memory/consolidate", methods=["POST"])
@rate_limit(10, 60)
@require_admin
def memory_consolidate():
    engine = get_engine()
    return jsonify(engine.consolidate())


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------

@self_improvement_bp.route("/learning/feedback", methods=["POST"])
@rate_limit(30, 60)
@require_admin
def learning_feedback():
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, FeedbackRequest)
    if err:
        return jsonify(err), 400
    if not data or "event" not in data:
        return jsonify({"error": "event is required"}), 400

    engine.learning.record_feedback(FeedbackSignal(
        event=data["event"],
        outcome=data.get("outcome", "pass"),
        context=data.get("context", {}),
        source=data.get("source", "api"),
        timestamp=time.time(),
    ))
    engine.practice("learning", 1, f"feedback for {data['event'][:40]}")
    return jsonify({"ok": True})


@self_improvement_bp.route("/learning/lessons", methods=["GET"])
def learning_lessons():
    engine  = get_engine()
    subject = request.args.get("subject")
    try:
        min_conf = float(request.args.get("min_confidence", 0.0))
    except (TypeError, ValueError):
        min_conf = 0.0
    lessons = engine.learning.get_lessons(subject=subject,
                                          min_confidence=min_conf)
    return jsonify({"lessons": [
        {"id": l.id, "subject": l.subject, "rule": l.rule,
         "confidence": l.confidence, "source": l.source,
         "applications": l.applications}
        for l in lessons
    ]})


# ---------------------------------------------------------------------------
# Development / skills / goals
# ---------------------------------------------------------------------------

@self_improvement_bp.route("/skills", methods=["GET"])
def skills_list():
    return jsonify({"skills": get_engine().development.assess()})


@self_improvement_bp.route("/skills/train", methods=["POST"])
@rate_limit(30, 60)
@require_admin
def skills_train():
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, SkillsTrainRequest)
    if err:
        return jsonify(err), 400
    skill  = data.get("skill")
    if not skill:
        return jsonify({"error": "skill is required"}), 400

    s = engine.practice(skill, data.get("xp", 1), data.get("activity", ""))
    return jsonify({"skill": s.name, "level": s.level.value,
                     "experience_points": s.experience_points})


@self_improvement_bp.route("/goals", methods=["GET"])
def goals_list():
    return jsonify({"goals": get_engine().development.get_goals()})


@self_improvement_bp.route("/goals", methods=["POST"])
@rate_limit(20, 60)
@require_admin
def goals_create():
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, GoalsCreateRequest)
    if err:
        return jsonify(err), 400
    required = ["name", "description", "target_skill", "milestones"]
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"missing: {missing}"}), 400

    goal = engine.propose_goal(
        name=data["name"],
        description=data["description"],
        target_skill=data["target_skill"],
        milestones=data["milestones"],
        deadline=data.get("deadline"),
    )
    return jsonify({"id": goal.id, "name": goal.name,
                     "status": goal.status.value}), 201


@self_improvement_bp.route("/goals/<goal_id>/milestone", methods=["POST"])
@rate_limit(20, 60)
@require_admin
def goals_mark_milestone(goal_id):
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, MilestoneRequest)
    if err:
        return jsonify(err), 400
    milestone = data.get("milestone")
    if not milestone:
        return jsonify({"error": "milestone is required"}), 400
    engine.development.mark_milestone(goal_id, milestone)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@self_improvement_bp.route("/errors/handle", methods=["POST"])
@rate_limit(30, 60)
@require_admin
def errors_handle():
    """Simulate/replay an error through the engine for learning."""
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, ErrorsHandleRequest)
    if err:
        return jsonify(err), 400
    source = data.get("source", "api")
    error_type = data.get("error_type", "RuntimeError")
    message    = data.get("message", "simulated error")

    # Security: never resolve exception types from __builtins__ — an attacker
    # could pass "eval"/"exec"/"open" and achieve arbitrary code execution.
    # Only a fixed allowlist of stdlib exception classes may be instantiated.
    _ALLOWED_ERROR_TYPES = {
        "RuntimeError": RuntimeError,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "AttributeError": AttributeError,
        "IndexError": IndexError,
        "StopIteration": StopIteration,
        "TimeoutError": TimeoutError,
        "ConnectionError": ConnectionError,
        "FileNotFoundError": FileNotFoundError,
        "PermissionError": PermissionError,
        "ZeroDivisionError": ZeroDivisionError,
        "ArithmeticError": ArithmeticError,
        "OverflowError": OverflowError,
    }

    ErrorCls = _ALLOWED_ERROR_TYPES.get(error_type, RuntimeError)
    error = ErrorCls(message)
    recovered, detail = engine.handle_error(source, error, data.get("context", {}))
    return jsonify({"recovered": recovered, **detail})


@self_improvement_bp.route("/errors/reflexes", methods=["GET"])
def errors_reflexes():
    return jsonify({"reflexes": get_engine().errors.get_reflexes()})


@self_improvement_bp.route("/errors/reflexes", methods=["POST"])
@rate_limit(10, 60)
@require_admin
def errors_register_reflex():
    engine = get_engine()
    data   = request.get_json(force=True)
    validated, err = _payload(data, ReflexRegisterRequest)
    if err:
        return jsonify(err), 400
    if not data.get("error_type") or not data.get("strategy"):
        return jsonify({"error": "error_type and strategy are required"}), 400

    try:
        recovery_strategy = RecoveryStrategy(data["strategy"])
    except ValueError:
        return jsonify({"error": f"invalid strategy: {data['strategy']}"}), 400

    engine.errors.register_reflex(ReflexRule(
        error_type=data["error_type"],
        source_pattern=data.get("source_pattern", "*"),
        recovery_strategy=recovery_strategy,
        max_attempts=data.get("max_attempts", 3),
        backoff_seconds=data.get("backoff_seconds", 0.3),
        message=data.get("message", ""),
    ))
    return jsonify({"ok": True}), 201


@self_improvement_bp.route("/errors/recent", methods=["GET"])
def errors_recent():
    limit = _safe_limit("limit", 20)
    return jsonify({"errors": get_engine().errors.get_recent_events(limit)})


# ---------------------------------------------------------------------------
# Dashboard export
# ---------------------------------------------------------------------------

@self_improvement_bp.route("/dashboard", methods=["GET"])
def dashboard_html():
    from .report import generate_html_dashboard
    engine = get_engine()
    return generate_html_dashboard(engine), 200, {"Content-Type": "text/html"}