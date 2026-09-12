# =============================================================================
# AI Agent Team -- orchestrator, roster, and live session engine
# =============================================================================
# A group of specialist AI agents (CEO, Orchestrator, Planner, Project Lead,
# Coder, Project Engineer, Designer, Developer Admin, SEO, Q&A Experience) that
# work a user request together. The CEO critiques the idea up front (verdict: safe /
# risk / break) before any work starts; the team then talks it out turn by
# turn using the auto-rotation LLM router. Every agent sees what the others
# said, so they react, challenge, and refine each other's work.
#
# Runs each session in a background daemon thread so the HTTP API returns
# immediately and the frontend polls a live working-status snapshot.
# Falls back to hand-written templated responses (marked `synth: true`) when
# no LLM provider is configured, so the panel stays usable pre-key.
# =============================================================================

from __future__ import annotations

import os
import re
import time
import json
import uuid
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from backend.llm.router import complete as llm_complete
except Exception:  # pragma: no cover - llm module may be unavailable
    llm_complete = None

# ── Agent roster ─────────────────────────────────────────────────────────────

# Each entry: id, name, title (role), tagline, personality used to build the
# system prompt, and the router task class this agent's turn belongs to.
AGENTS: List[Dict[str, Any]] = [
    {
        "id": "ceo",
        "name": "Git-Fix CEO",
        "title": "CEO Git-Fix Agent",
        "tagline": "I lead the team, critique ideas, and make the final call.",
        "personality": (
            "You are the CEO Git-Fix Agent — decisive, deeply technical, and commercially aware. "
            "Before any work starts you critically evaluate whether an idea is SAFE, RISKY, or "
            "will BREAK the codebase. You weigh business value against regressions, security "
            "implications, and operational cost. You open by issuing a clear VERDICT and close "
            "by synthesising team output into an actionable summary. You reject scope creep, "
            "demand explicit definitions of done, and will not sign off on changes that are "
            "unclear, untested, or that compromise existing behaviour. Be blunt, honest, "
            "constructive, and opinionated when the team needs a final call."
        ),
        "task": "code_review",
    },
    {
        "id": "orchestrator",
        "name": "Orchestrator",
        "title": "Orchestrator",
        "tagline": "I assign work, sequence the team, and keep everyone aligned.",
        "personality": (
            "You are the Orchestrator agent — the team's conductor and sequencing engine. "
            "You break work into ordered, dependency-aware steps and hand each step to the "
            "specialist who owns it. You detect conflicts, parallelizable tasks, and blocked "
            "paths early, and you keep every agent aligned on the shared goal. You are "
            "intolerant of ambiguous handoffs: every assignment names the owner, the deliverable, "
            "and the next agent it flows to. Keep your briefs short, scannable, and actionable."
        ),
        "task": "chat",
    },
    {
        "id": "planner",
        "name": "Planner",
        "title": "Planner",
        "tagline": "I turn the request into a concrete, ordered plan.",
        "personality": (
            "You are the Planner agent — a rigorous systems thinker who converts a vague request "
            "into a concrete, ordered, executable plan. You define milestones with measurable "
            "deliverables, estimate effort honestly, flag unknowns and risks explicitly, and "
            "surface dependencies between steps. Every plan you produce states what is being "
            "built, in what order, what must be protected, and how success is verified. You will "
            "not pad estimates, hide uncertainties, or over-promise — if you cannot see the path, "
            "you say so and ask."
        ),
        "task": "chat",
    },
    {
        "id": "lead",
        "name": "Project Lead",
        "title": "Project Lead",
        "tagline": "I own delivery, scope, and the definition of done.",
        "personality": (
            "You are the Project Lead agent — delivery-obsessed and scope-disciplined. You own "
            "the definition of done, keep the plan realistic, sequence the team's execution, and "
            "escalate blockers to the CEO without hesitation. You measure progress in shippable "
            "increments, not activity. You will not let the team gold-plate, balloon scope, or "
            "declare victory on untested work. You are pragmatic, calm under pressure, and "
            "ruthless about priorities."
        ),
        "task": "chat",
    },
    {
        "id": "coder",
        "name": "Coder",
        "title": "Coder",
        "tagline": "I write the code. I live for clean, working implementations.",
        "personality": (
            "You are the Coder agent — a senior software engineer who writes clean, working, "
            "maintainable code. You speak in exact file and function references, note edge cases, "
            "and design your changes to be isolated and reversible. You will not introduce "
            "speculative abstractions, dead code, or silent behaviour changes. If a proposed "
            "feature would break existing code, the public contract, or tests, you say so bluntly "
            "and propose the minimal safe path. You defend correctness, readability, and "
            "regression-free merges above cleverness."
        ),
        "task": "code_fix",
    },
    {
        "id": "engineer",
        "name": "Project Engineer",
        "title": "Project Engineer",
        "tagline": "I sweat architecture, performance, and maintainability.",
        "personality": (
            "You are the Project Engineer agent — an architect who sweats maintainability, "
            "scalability, performance, coupling, and data-model integrity. You pressure-test "
            "every suggestion: what does this do to module boundaries, dependencies, horizontal "
            "scaling, and technical debt? You surface design problems early rather than after "
            "they become expensive. You are suspicious of hardcoded values, duplication, N+1 "
            "patterns, and premature optimization. When something architectural cannot survive "
            "the plan, you reject it and explain the trade-offs."
        ),
        "task": "code_review",
    },
    {
        "id": "devadmin",
        "name": "Developer Admin",
        "title": "Developer Admin",
        "tagline": "I own tooling, environment, and developer experience.",
        "personality": (
            "You are the Developer Admin agent — guardian of the developer environment and "
            "reproducibility. You inspect tooling, dependency graphs, CI pipelines, environment "
            "configuration, and build health with an eye for breakage. You flag any change that "
            "would break builds, add needless runtime dependencies, destabilise local development, "
            "or introduce environment drift. You champion locked dependencies, documented setup, "
            "and CI that fails loudly. Your approval criterion is simple: it must build cleanly "
            "and run the same way everywhere."
        ),
        "task": "chat",
    },
    {
        "id": "seo",
        "name": "SEO Agent",
        "title": "SEO Agent",
        "tagline": "I make sure product changes help — not hurt — discoverability.",
        "personality": (
            "You are the SEO Agent — a growth and search-visibility strategist who reads every "
            "product change for its impact on discoverability. You review metadata, URL structure, "
            "routing, crawlability, Core Web Vitals, content hierarchy, and user experience as "
            "ranking signals. You flag changes that would hurt indexing, damage long-tail keywords, "
            "or degrade performance budgets. You will not accept 'it works' as a reason to ignore "
            "canonical URLs, redirects, or structured data. You advocate for users and search "
            "engines simultaneously."
        ),
        "task": "chat",
    },
    {
        "id": "qa",
        "name": "Q&A Experience",
        "title": "Q&A Experience Expert",
        "tagline": "I hunt edge cases, define test plans, and protect the user experience.",
        "personality": (
            "You are the Q&A Experience Expert — a relentless defender of the user experience. "
            "You design comprehensive test plans, hunt edge cases, and think adversarially about "
            "what could go wrong before anything ships. You challenge the team on error handling, "
            "empty states, invalid input, race conditions, and accessibility (WCAG). Nothing is "
            "done until it has been probed with hostile inputs and verified by real scenarios. "
            "You are rigorous, evidence-driven, and never satisfied by a passing smoke test alone."
        ),
        "task": "code_review",
    },
    {
        "id": "designer",
        "name": "Designer",
        "title": "UI/UX Designer",
        "tagline": "I design the complete architecture look and feel — layout, motion, accessibility.",
        "personality": (
            "You are the Designer agent — a senior UI/UX and visual-design architect who owns the "
            "complete look and feel of the product. You design with intent: a cohesive visual "
            "language built on a design-token system (color, typography, spacing, radius, shadow), "
            "clear hierarchy, and a defined aesthetic direction that avoids generic AI templates. "
            "You design mobile-first, responsive layouts that survive 320px screens without "
            "horizontal scroll, and you enforce WCAG 2.2 AA contrast, keyboard operability, and "
            "visible focus states. Motion follows meaning: 150–300ms, respects "
            "prefers-reduced-motion, and never animates for decoration alone. You challenge the "
            "team on layout architecture, component consistency, perceived performance, and any "
            "experience that feels disjointed across routes or devices."
        ),
        "task": "code_review",
    },
]

AGENT_BY_ID: Dict[str, Dict[str, Any]] = {a["id"]: a for a in AGENTS}

# Turn order for a full round after a user request (or reply).
FULL_TURN_ORDER = [
    "ceo",           # critique the idea first: safe / risk / break
    "planner",       # concrete plan
    "orchestrator",  # assign + sequence
    "lead",          # delivery + definition of done
    "designer",      # architecture look and feel
    "coder",         # code impact
    "engineer",      # architecture pressure-test
    "devadmin",      # tooling / build safety
    "seo",           # growth / UX angle
    "qa",            # test plan + edge cases
    "ceo",           # final summary + question to the user
]

# Bounded continuation for user replies: react, tighten, wrap.
REPLY_TURN_ORDER = ["ceo", "orchestrator", "coder", "designer", "qa", "ceo"]

LLM_MAX_TOKENS = 420
LLM_MAX_CONTEXT_MESSAGES = 12
TURN_PAUSE_SECONDS = 0.45   # so the live panel visibly steps through agents
VERDICT_RE = re.compile(r"\bVERDICT[:\s]+(SAFE|RISK|BREAK)\b", re.IGNORECASE)

_ENV_FALLBACK_VERDICT = "review"  # when the LLM call fails

# ── Templates for the no-provider fallback (marked synth=True) ───────────────

_FALLBACK_TEXT: Dict[str, str] = {
    "ceo": (
        "Reviewing this now — I'm weighing whether this is safe to build straight away or "
        "whether it risks breaking existing behaviour. "
        "VERDICT: RISK — I want the team's input before I sign off."
    ),
    "planner": (
        "@orchestrator I'd sequence this as: 1) scope the change, 2) protect the existing "
        "contract, 3) implement behind a flag, 4) test and ship. Estimate: small-to-medium."
    ),
    "orchestrator": (
        "@planner +1. Handing the build to @lead and @coder, @engineer on architecture, "
        "@devadmin on tooling, @qa on the test pass."
    ),
    "lead": (
        "@orchestrator defined. Definition of done: feature behind a flag, existing tests "
        "green, no regressions, docs updated."
    ),
    "coder": (
        "@engineer I'd keep this isolated to avoid touching the hot path; I'll flag any "
        "public API change before merging."
    ),
    "engineer": (
        "@coder agreed — keep it isolated and preserve the existing contract. No "
        "architectural red flags if we gate it behind a flag."
    ),
    "devadmin": (
        "@lead confirmed: no new runtime deps, CI stays green, local dev unaffected."
    ),
    "qa": (
        "Test plan: happy path, flag on/off, old-caller regression check, and a11y "
        "smoke test. I'll own the edge-case pass."
    ),
    "designer": (
        "@lead I'll draft the look and feel: a coherent visual language, design tokens, "
        "mobile-first responsive layout, WCAG AA contrast, and motion that respects "
        "reduced-motion preferences. Reviewing the plan before the build starts."
    ),
    "seo": (
        "@engineer careful: route/structure changes can affect indexing. I'll review the "
        "URL/redirect impact before we merge."
    ),
}


def _fallback_text(agent_id: str, kind: str = "open") -> str:
    return _FALLBACK_TEXT.get(agent_id, f"{agent_id}: proceeding.")


# ── Session model ────────────────────────────────────────────────────────────

class TeamSession:
    """One live agent-team working session (thread-safe)."""

    def __init__(self, request: str, session_id: Optional[str] = None) -> None:
        self.id = session_id or uuid.uuid4().hex[:12]
        self.request = request
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.status = "running"          # running | awaiting_user | done | error
        self.phase = "starting"          # starting | planning | working | summarizing | responding
        self.statuses: Dict[str, Dict[str, Any]] = {
            a["id"]: {"status": "idle", "turns": 0, "last_at": None, "note": None}
            for a in AGENTS
        }
        self.transcript: List[Dict[str, Any]] = []
        self.plan: List[Dict[str, Any]] = []
        self.verdict: Dict[str, Any] = {
            "level": _ENV_FALLBACK_VERDICT,
            "summary": "",
            "advice": "",
        }
        self.error: Optional[str] = None
        self._lock = threading.RLock()
        self._stop = threading.Event()

    # ── state helpers ────────────────────────────────────────────────────────
    def _touch(self) -> None:
        self.updated_at = time.time()

    def add_user_message(
        self,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            msg = self._message(
                "user", "You", "User", content or "Shared attachments",
                agent_id="user", attachments=attachments,
            )
            self.transcript.append(msg)
            self._touch()
            return msg

    def _message(
        self,
        kind: str,
        name: str,
        title: str,
        content: str,
        agent_id: str = "",
        synth: bool = False,
        mentions: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return {
            "id": uuid.uuid4().hex[:12],
            "kind": kind,                 # user | agent | system
            "agent_id": agent_id,
            "name": name,
            "title": title,
            "content": content,
            "at": time.time(),
            "synth": synth,
            "mentions": mentions or [],
            "attachments": attachments or [],
        }

    # ── orchestration ────────────────────────────────────────────────────────
    def _set_agent(self, agent_id: str, status: str, note: Optional[str] = None) -> None:
        with self._lock:
            st = self.statuses.setdefault(
                agent_id, {"status": "idle", "turns": 0, "last_at": None, "note": None}
            )
            st["status"] = status
            st["last_at"] = time.time()
            if note is not None:
                st["note"] = note
            self._touch()

    def _speak(
        self,
        agent_id: str,
        instruction: str,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> Dict[str, Any]:
        """Run one agent turn: set working status, call the router, persist."""
        agent = AGENT_BY_ID[agent_id]
        self._set_agent(agent_id, "working", note="thinking…")
        time.sleep(TURN_PAUSE_SECONDS)

        content = ""
        synth = False
        provider = ""

        if llm_complete is not None:
            try:
                result = llm_complete(
                    self._build_prompt(agent, instruction),
                    task=agent.get("task", "chat"),
                    max_tokens=max_tokens,
                    temperature=0.5,
                )
                if result.get("ok") and str(result.get("content") or "").strip():
                    content = str(result["content"]).strip()
                    provider = result.get("provider", "")
                else:
                    synth = True
            except Exception as exc:  # noqa: BLE001 - agent turn must never crash the session
                logger.warning("Agent turn %s failed: %s", agent_id, exc)
                synth = True
        else:
            synth = True

        if synth or not content:
            content = content or _fallback_text(agent_id)

        mentions = [a["id"] for a in AGENTS if f"@{a['name'].lower()}" in content.lower().replace("agent", "")]

        with self._lock:
            msg = self._message(
                "agent", agent["name"], agent["title"], content,
                agent_id=agent_id, synth=synth, mentions=mentions,
            )
            self.transcript.append(msg)
            self.statuses[agent_id]["turns"] += 1
            self._set_agent(agent_id, "done", note=f"spoke · {provider or ('template fallback' if synth else 'network')}")

        # CEO verdict parsing: capture the verdict line if present.
        if agent_id == "ceo" and "VERDICT" in content.upper():
            self._parse_verdict(content)

        return msg

    def _parse_verdict(self, content: str) -> None:
        m = VERDICT_RE.search(content)
        level = (m.group(1).lower() if m else _ENV_FALLBACK_VERDICT)
        # Heuristic summary: the sentence(s) right after the verdict tag.
        summary = ""
        idx = content.upper().find("VERDICT")
        if idx >= 0:
            summary = content[idx:].strip()[:280]
        self.verdict = {"level": level, "summary": summary or content[:280], "advice": ""}
        self._touch()

    def _build_prompt(self, agent: Dict[str, Any], instruction: str) -> List[Dict[str, Any]]:
        system = f"{agent['personality']}\n\nTeam roster: {', '.join(a['name'] for a in AGENTS)}."
        with self._lock:
            # Compact context: the request plus the most recent turns so agents hear each other.
            context_lines = [f"USER REQUEST: {self.request}"]
            for m in self.transcript[-LLM_MAX_CONTEXT_MESSAGES:]:
                if m["kind"] == "user":
                    # The initial request already appears above; don't repeat it verbatim.
                    if m["content"] == self.request:
                        continue
                    line = f"You (the user): {m['content']}"
                    atts = m.get("attachments") or []
                    if atts:
                        line += " [attached: " + ", ".join(a.get("name", "") for a in atts) + "]"
                    context_lines.append(line)
                else:
                    line = f"{m['name']} ({m['title']}): {m['content'][:600]}"
                    atts = m.get("attachments") or []
                    if atts:
                        line += " [attached: " + ", ".join(a.get("name", "") for a in atts) + "]"
                    context_lines.append(line)
            context = "\n".join(context_lines)
            plan_note = ""
            if self.plan:
                plan_note = "\nPLAN SO FAR: " + "; ".join(p.get("task", "") for p in self.plan[-6:])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{instruction}\n\n{context}{plan_note}\n\n"
                                        "Speak as your role directly to the team. Keep it under 120 words. "
                                        "Address an agent with @Name when you rely on or challenge them. "},
        ]
        return messages

    def run_round(self, turn_order: List[str], user_reply: str = "") -> None:
        """Execute a full round of agent turns."""
        self._stop.clear()
        self.status = "running"
        self._touch()
        try:
            for i, agent_id in enumerate(turn_order):
                if self._stop.is_set():
                    break
                if i == 0 and agent_id == "ceo":
                    instruction = (
                        f"Lead the team on this new user request. First give your verdict. "
                        f"Start your message with exactly: VERDICT: SAFE, VERDICT: RISK, or VERDICT: BREAK. "
                        f"Then criticise the idea if it could cause issues or break the code, and explain how the team should proceed."
                    )
                    self.phase = "planning" if user_reply else "starting"
                elif i == len(turn_order) - 1 and agent_id == "ceo":
                    instruction = (
                        "Synthesize the team's output. Give the user a crisp final summary: what is agreed, "
                        "what still needs their decision, and exactly who does what next. Close by asking the user "
                        "what they'd like to do next."
                    )
                    self.phase = "summarizing"
                else:
                    instruction = self._turn_instruction(agent_id, i, len(turn_order))
                self._speak(agent_id, instruction)
            self.status = "awaiting_user"
            self.phase = "responding"
            with self._lock:
                self.transcript.append(self._message(
                    "system", "Git-Fix Team", "Panel",
                    "Round complete. The team is waiting for your steer — reply to continue, or start a new request.",
                    agent_id="system",
                ))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent session %s crashed", self.id)
            self.error = str(exc)
            self.status = "error"
            with self._lock:
                self.transcript.append(self._message(
                    "system", "Git-Fix Team", "Panel",
                    f"Session error: {exc}", agent_id="system",
                ))
        finally:
            self._touch()

    def _turn_instruction(self, agent_id: str, index: int, total: int) -> str:
        if agent_id == "planner":
            return "Produce the concrete plan now: ordered steps, milestones, and anything the team must protect."
        if agent_id == "orchestrator":
            return "Assign the plan to the right agents, sequence their work, and flag dependencies or conflicts."
        if agent_id == "lead":
            return "Pin down delivery: definition of done, realistic scope, and any blockers to escalate to the CEO."
        if agent_id == "designer":
            return "Define the complete architecture look and feel: visual language, design tokens, layout architecture, responsive behaviour, accessibility (WCAG AA), and motion. Flag any design decisions that would clash with the plan or hurt usability."
        if agent_id == "coder":
            return "Say exactly which files/functions change, how, and what edge cases you will cover. Flag anything that would break."
        if agent_id == "engineer":
            return "Pressure-test the plan: architecture, performance, data-model integrity, coupling. Push back where needed."
        if agent_id == "devadmin":
            return "Check tooling/build/dev-env impact: new dependencies, CI, config, reproducibility."
        if agent_id == "seo":
            return "Check growth/UX impact: metadata, routing, performance, crawlability. Flag anything that would hurt SEO or UX."
        if agent_id == "qa":
            return "Produce the test plan: happy path, edge cases, regression targets, accessibility, error handling."
        return "Contribute your specialist input and confirm or challenge the plan."

    # ── public API for route handlers ────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "id": self.id,
                "request": self.request,
                "status": self.status,
                "phase": self.phase,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "error": self.error,
                "verdict": dict(self.verdict),
                "plan": [dict(p) for p in self.plan],
                "statuses": {k: dict(v) for k, v in self.statuses.items()},
                "transcript": [dict(m) for m in self.transcript],
            }

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self.status = "done"
            self._touch()


# ── Registry + persistence ───────────────────────────────────────────────────

SESSIONS_PATH = Path.home() / ".gitfix" / "agents" / "sessions.json"
UPLOADS_PATH = Path.home() / ".gitfix" / "agents" / "uploads"

MAX_ATTACHMENTS_PER_MESSAGE = 6
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5MB per file
_INLINE_BLOCKLIST = {"image/svg+xml", "text/html", "application/xhtml+xml", "text/plain"}
_EXT_RE = re.compile(r"[^A-Za-z0-9._-]")


def _classify_attachment_kind(mime: str) -> str:
    mime = (mime or "").lower()
    if mime in _INLINE_BLOCKLIST:
        return "file"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    return "file"


def _safe_ext(filename: str) -> str:
    ext = Path(filename or "").suffix[:16]
    if not ext:
        return ".bin"
    safe = _EXT_RE.sub("", ext)
    return safe or ".bin"


def save_attachments(session_id: str, files) -> List[Dict[str, Any]]:
    """Persist uploaded files to UPLOADS_PATH/<session_id>/ and return metadata.

    Each item in `files` behaves like a Werkzeug FileStorage (filename /
    content_type / read()). Classifies as image | audio | file and refuses
    oversized or over-count payloads. Raises ValueError on policy violations.
    """
    files = list(files or [])
    if not files:
        return []
    if len(files) > MAX_ATTACHMENTS_PER_MESSAGE:
        raise ValueError(
            f"Too many attachments (max {MAX_ATTACHMENTS_PER_MESSAGE} per message)"
        )
    upload_dir = UPLOADS_PATH / session_id
    out: List[Dict[str, Any]] = []
    for f in files:
        raw_name = str(getattr(f, "filename", None) or "").strip()
        if not raw_name:
            continue
        data = getattr(f, "read", lambda: b"")() or b""
        if not data:
            continue
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"{raw_name} is too large (max {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB)"
            )
        mime = str(getattr(f, "content_type", None) or "application/octet-stream").lower()
        kind = _classify_attachment_kind(mime)
        stored = f"{uuid.uuid4().hex[:12]}{_safe_ext(raw_name)}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / stored).write_bytes(data)
        out.append({
            "id": uuid.uuid4().hex[:12],
            "kind": kind,
            "name": raw_name,
            "size": len(data),
            "mime": mime,
            "stored": stored,
            "url": f"/api/v1/agents/sessions/{session_id}/attachments/{stored}",
        })
    return out


def find_attachment_meta(session: TeamSession, stored_name: str) -> Optional[Dict[str, Any]]:
    """Return stored metadata for an uploaded file, or None."""
    for m in session.transcript:
        for att in m.get("attachments") or []:
            if att.get("stored") == stored_name:
                return att
    return None


_registry: Dict[str, TeamSession] = {}
_registry_lock = threading.Lock()
_session_threads: Dict[str, threading.Thread] = {}


def _load_registry() -> None:
    """Restore session metadata (transcript) across restarts (best-effort)."""
    try:
        if not SESSIONS_PATH.exists():
            return
        raw = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        for item in raw.get("sessions", []):
            s = TeamSession(item.get("request", ""), session_id=item.get("id"))
            s.status = item.get("status", "done")
            s.phase = item.get("phase", "done")
            s.verdict = item.get("verdict", {"level": "review", "summary": "", "advice": ""})
            s.transcript = item.get("transcript", [])
            s.created_at = item.get("created_at", time.time())
            s.updated_at = item.get("updated_at", time.time())
            _registry[s.id] = s
    except Exception as exc:  # pragma: no cover - best-effort restore
        logger.warning("Failed to restore agent sessions: %s", exc)


def _persist() -> None:
    try:
        SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        keep = sorted(_registry.values(), key=lambda s: s.updated_at, reverse=True)[:20]
        payload = {"sessions": [s.snapshot() for s in keep]}
        tmp = SESSIONS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SESSIONS_PATH)
    except Exception as exc:  # pragma: no cover - persistence must never crash
        logger.warning("Failed to persist agent sessions: %s", exc)


def start_session(
    request: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
) -> TeamSession:
    """Create a session and kick off the first round in a background thread."""
    s = TeamSession(request, session_id=session_id)
    # Record the user's opening message (with any attachments) in the transcript
    # so the chat UI renders the request as a bubble.
    s.add_user_message(request or "Shared attachments", attachments=attachments)
    with _registry_lock:
        _registry[s.id] = s
    _persist()

    def _work() -> None:
        s.run_round(FULL_TURN_ORDER)
        _persist()

    t = threading.Thread(target=_work, daemon=True, name=f"agent-{s.id}")
    _session_threads[s.id] = t
    t.start()
    return s


def get_session(session_id: str) -> Optional[TeamSession]:
    with _registry_lock:
        s = _registry.get(session_id)
        # Lazily load persisted sessions from disk on first lookup.
        if s is None:
            _load_registry()
            s = _registry.get(session_id)
        return s


def list_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    _load_registry()
    with _registry_lock:
        ordered = sorted(_registry.values(), key=lambda s: s.updated_at, reverse=True)
        return [s.snapshot() for s in ordered[:limit]]


def reply_to_session(
    session_id: str,
    content: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> Optional[TeamSession]:
    """Queue a user reply; if the team is waiting, kick a bounded continuation round."""
    s = get_session(session_id)
    if s is None:
        return None
    s.add_user_message(content, attachments=attachments)
    _persist()

    # Only spawn a new round when the previous one finished (or errored).
    if s.status in ("awaiting_user", "done", "error") and not s._stop.is_set():
        def _work() -> None:
            s.run_round(REPLY_TURN_ORDER, user_reply=content)
            _persist()

        t = threading.Thread(target=_work, daemon=True, name=f"agent-{s.id}-reply")
        _session_threads[s.id] = t
        t.start()
    return s