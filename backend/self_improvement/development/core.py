# =============================================================================
# Self-Development Engine
# =============================================================================
# Goal tracking, skill acquisition, capability assessment, auto-improvement.
# Defines "what the agent wants to get better at" and measures progress.
# =============================================================================

import os
import json
import time
import logging
import threading
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from backend.self_improvement.memory.core import MemorySystem, MemoryType

logger = logging.getLogger(__name__)


class GoalStatus(str, Enum):
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class SkillLevel(str, Enum):
    NOVICE = "novice"
    DEVELOPING = "developing"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"


@dataclass
class Skill:
    name: str
    level: SkillLevel
    experience_points: int
    last_practiced: float
    prerequisites: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)


@dataclass
class Goal:
    id: str
    name: str
    description: str
    status: GoalStatus
    progress: float  # 0-1
    target_skill: str
    milestones: List[str] = field(default_factory=list)
    achieved_milestones: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class DevelopmentEngine:
    """Tracks skills, goals, and generates improvement plans."""

    SKILL_TREE: Dict[str, List[str]] = {
        "error_recovery": ["detection", "classification", "reflex_building"],
        "pattern_recognition": ["tokenization", "clustering", "heuristics"],
        "code_analysis": ["ast_parsing", "vulnerability_patterns", "quality_scores"],
        "self_reflection": ["review_loop", "lesson_extraction", "consolidation"],
    }

    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self._lock = threading.Lock()
        self._skills: Dict[str, Skill] = {}
        self._goals: Dict[str, Goal] = {}
        self._load_state()

    # ----- Skills -------------------------------------------------------

    def train(self, skill_name: str, xp: int = 1,
              activity: Optional[str] = None) -> Skill:
        """Earn XP in a skill; auto-promote at thresholds."""
        with self._lock:
            s = self._skills.get(skill_name)
            if s is None:
                s = Skill(name=skill_name, level=SkillLevel.NOVICE,
                          experience_points=0, last_practiced=time.time(),
                          prerequisites=self.SKILL_TREE.get(skill_name, []))
                self._skills[skill_name] = s
            s.experience_points += xp
            s.last_practiced = time.time()

            old_level = s.level
            s.level = self._level_for(s.experience_points)
            if s.level != old_level:
                logger.info(f"SKILL ADVANCEMENT: {skill_name} "
                            f"{old_level.value} → {s.level.value}")

            self._persist_state()

            if activity:
                self.memory.remember_episode(
                    f"Practiced {skill_name} (+{xp}xp): {activity}",
                    {"skill": skill_name, "xp": xp, "level": s.level.value},
                    importance=1,
                )
            return s

    def assess(self) -> List[Dict[str, Any]]:
        return [
            {"name": s.name, "level": s.level.value,
             "xp": s.experience_points,
             "prereqs_met": all(p in self._skills for p in s.prerequisites)}
            for s in sorted(self._skills.values(), key=lambda x: -x.experience_points)
        ]

    # ----- Goals --------------------------------------------------------

    def add_goal(self, name: str, description: str, target_skill: str,
                 milestones: List[str], deadline: Optional[float] = None) -> Goal:
        goal = Goal(
            id=f"g{int(time.time())}",
            name=name, description=description,
            status=GoalStatus.IN_PROGRESS,
            progress=0.0, target_skill=target_skill,
            milestones=milestones, deadline=deadline,
        )
        with self._lock:
            self._goals[goal.id] = goal
            self._persist_state()
        return goal

    def mark_milestone(self, goal_id: str, milestone: str):
        with self._lock:
            g = self._goals.get(goal_id)
            if not g or milestone in g.achieved_milestones:
                return
            g.achieved_milestones.append(milestone)
            g.progress = len(g.achieved_milestones) / max(1, len(g.milestones))
            if g.progress >= 1.0:
                g.status = GoalStatus.ACHIEVED
                self.train(g.target_skill, xp=10, activity=f"Goal '{g.name}' achieved")
            self._persist_state()

    def get_goals(self) -> List[Dict[str, Any]]:
        return [{"id": g.id, "name": g.name, "status": g.status.value,
                 "progress": round(g.progress, 2),
                 "target_skill": g.target_skill,
                 "milestones": g.milestones,
                 "achieved": g.achieved_milestones,
                 "deadline": g.deadline}
                for g in self._goals.values()]

    # ----- Improvement plan ---------------------------------------------

    def improvement_plan(self) -> List[Dict[str, Any]]:
        """Generate auto-improvement actions based on current state."""
        plan = []
        weak = [s for s in self._skills.values()
                if s.experience_points < 5]
        for s in weak:
            plan.append({
                "action": f"practice:{s.name}",
                "reason": f"{s.name} has only {s.experience_points}xp "
                          f"(level {s.level.value})",
                "priority": "high",
            })

        for skill, prereqs in self.SKILL_TREE.items():
            if skill in self._skills:
                missing = [p for p in prereqs if p not in self._skills]
                if missing:
                    plan.append({
                        "action": f"learn:{','.join(missing)}",
                        "reason": f"{skill} requires prerequisites: {missing}",
                        "priority": "medium",
                    })

        rules = self.memory.recall(mtype=MemoryType.PROCEDURAL,
                                   tags=["lesson"], limit=50)
        low_conf = [r for r in rules if r.importance < 3]
        if low_conf:
            plan.append({
                "action": "strengthen_lessons",
                "reason": f"{len(low_conf)} lessons need more evidence before use",
                "priority": "low",
            })

        return sorted(plan, key=lambda x: {"high": 0, "medium": 1,
                                           "low": 2}[x["priority"]])

    # ----- Internals ---------------------------------------------------

    def _level_for(self, xp: int) -> SkillLevel:
        if xp >= 100: return SkillLevel.EXPERT
        if xp >= 50:  return SkillLevel.PROFICIENT
        if xp >= 25:  return SkillLevel.COMPETENT
        if xp >= 10:  return SkillLevel.DEVELOPING
        return SkillLevel.NOVICE

    def _state_path(self) -> str:
        return os.path.join(os.path.dirname(self.memory.db_path),
                            "development.json")

    def _persist_state(self):
        try:
            state = {
                "skills": [
                    {"name": s.name, "level": s.level.value,
                     "experience_points": s.experience_points,
                     "last_practiced": s.last_practiced,
                     "prerequisites": s.prerequisites, "related": s.related}
                    for s in self._skills.values()
                ],
                "goals": [
                    {"id": g.id, "name": g.name,
                     "description": g.description,
                     "status": g.status.value,
                     "progress": g.progress,
                     "target_skill": g.target_skill,
                     "milestones": g.milestones,
                     "achieved_milestones": g.achieved_milestones,
                     "created_at": g.created_at,
                     "deadline": g.deadline,
                     "metrics": g.metrics}
                    for g in self._goals.values()
                ],
            }
            os.makedirs(os.path.dirname(self._state_path()), exist_ok=True)
            with open(self._state_path(), "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist development state: {e}")

    def _load_state(self):
        path = self._state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                state = json.load(f)
            for s in state.get("skills", []):
                self._skills[s["name"]] = Skill(
                    name=s["name"],
                    level=SkillLevel(s.get("level", "novice")),
                    experience_points=s.get("experience_points", 0),
                    last_practiced=s.get("last_practiced", time.time()),
                    prerequisites=s.get("prerequisites", []),
                    related=s.get("related", []),
                )
            for g in state.get("goals", []):
                self._goals[g["id"]] = Goal(
                    id=g["id"], name=g["name"], description=g.get("description", ""),
                    status=GoalStatus(g.get("status", "in_progress")),
                    progress=g.get("progress", 0.0),
                    target_skill=g.get("target_skill", ""),
                    milestones=g.get("milestones", []),
                    achieved_milestones=g.get("achieved_milestones", []),
                    created_at=g.get("created_at", time.time()),
                    deadline=g.get("deadline"),
                    metrics=g.get("metrics", {}),
                )
        except Exception as e:
            logger.warning(f"Could not load development state: {e}")