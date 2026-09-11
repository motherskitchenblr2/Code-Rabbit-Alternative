#!/usr/bin/env python3
# =============================================================================
# Git-Fix Self-Improvement CLI
# =============================================================================
# Interactive terminal for the self-improvement engine.
# Example:
#   python -m backend.self_improvement.cli status
#   python -m backend.self_improvement.cli demo
#   python -m backend.self_improvement.cli plan
# =============================================================================

import os
import sys
import json
import time
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.self_improvement.orchestrator import SelfImprovementEngine
from backend.self_improvement.report import (
    generate_status_report, generate_html_dashboard,
)


def cmd_status(engine: SelfImprovementEngine):
    report = generate_status_report(engine)
    print(report)


def cmd_demo(engine: SelfImprovementEngine):
    """Run a short demo exercising memory, error handling, learning, and skills."""
    engine.practice("pattern_recognition", xp=3, activity="demo: analyzed a PR")
    engine.practice("code_analysis", xp=2, activity="demo: reviewed a diff")

    engine.track_event("webhook received from github/pr", 
                       {"outcome": "pass", "source": "demo"})

    for label, exc in [
        ("api-call-out", TimeoutError("upstream took too long")),
        ("db-read", ConnectionError("db socket closed")),
        ("cache-write", OSError("disk full")),
    ]:
        recovered, detail = engine.handle_error(label, exc,
            context={"retry_fn": lambda: None})
        print(f"  {'[RECOVERED]' if recovered else '[ESCALATE]':12s} "
              f"{label:14s} → {exc.__class__.__name__} ({detail['attempts']} tries)")

    goal = engine.propose_goal(
        name="Reduce error recovery time",
        description="Handle common transient errors without manual intervention.",
        target_skill="error_recovery",
        milestones=["Classify error types", "Build 3+ reflexes",
                    "Achieve 90% auto-recovery rate"],
        deadline=time.time() + 7 * 86400,
    )
    engine.development.mark_milestone(goal.id, "Classify error types")

    engine.track_event("phishing-like pattern in commit message",
                       {"outcome": "fail", "source": "demo"})

    engine.consolidate()
    print()
    print(generate_status_report(engine))


def cmd_plan(engine: SelfImprovementEngine):
    plan = engine.get_plan()
    print("IMPROVEMENT PLAN")
    for p in plan:
        print(f"  [{p['priority']}] {p['action']}")
        print(f"        {p['reason']}")


def cmd_memory(engine: SelfImprovementEngine):
    stats = engine.memory.stats()
    print(json.dumps(stats, indent=2))
    for m in engine.memory.recall(limit=20):
        print(f"  [{m.type.value:9s}] {m.key:36s} imp={m.importance} :: {m.content[:60]}")


def cmd_reset(engine: SelfImprovementEngine):
    if input("Are you sure? This wipes ALL memories and state. (yes/no) ") == "yes":
        n = engine.memory.forget()
        print(f"Forgot {n} memories. Re-initializing seeds...")
        engine = SelfImprovementEngine()
        print("Reset complete.")


def main():
    parser = argparse.ArgumentParser(description="Git-Fix Self-Improvement CLI")
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "demo", "plan", "memory",
                                 "reset", "dashboard"])
    parser.add_argument("--mem-path", help="path to memory db",
                        default=None)
    args = parser.parse_args()

    engine = SelfImprovementEngine(db_path=args.mem_path)

    if args.command == "demo":
        cmd_demo(engine)
    elif args.command == "plan":
        cmd_plan(engine)
    elif args.command == "memory":
        cmd_memory(engine)
    elif args.command == "reset":
        cmd_reset(engine)
    elif args.command == "dashboard":
        from backend.self_improvement.report import export_snapshot
        path = export_snapshot(engine)
        print(f"Dashboard written to {path}")
    else:
        cmd_status(engine)


if __name__ == "__main__":
    main()