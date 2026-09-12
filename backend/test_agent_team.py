#!/usr/bin/env python3
# =============================================================================
# AI Agent Team tests
# =============================================================================
#   python -m pytest backend/test_agent_team.py -q
# =============================================================================
# Verifies the session lifecycle (user request -> full round -> awaiting user),
# verdict parsing, the no-provider synth fallback, reply continuation rounds,
# and the HTTP API surface. LLM calls are mocked so tests are fast & offline.
# =============================================================================

import os
import sys
import time
import json
import io
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")

from backend.agents import team as team_mod


def _wait_for(predicate, timeout: float = 10.0) -> bool:
    """Poll until predicate() is truthy or the timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def _fake_llm(content):
    """Return a fake llm_complete that always produces the given text."""
    def fake(messages, task, max_tokens=420, temperature=0.5):
        return {
            "ok": True,
            "provider": "nvidia",
            "provider_name": "NVIDIA",
            "model": "nemotron-test",
            "content": content,
            "attempts": [],
            "errors": [],
        }
    return fake


class TeamSessionTestCase(unittest.TestCase):

    def setUp(self):
        # Isolated, disposable persistence path.
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self._sessions_path = path
        from pathlib import Path
        patcher_path = mock.patch.object(team_mod, "SESSIONS_PATH", Path(path))
        patcher_path.start()
        self.addCleanup(patcher_path.stop)

        # Isolated uploads directory.
        self._uploads_dir = tempfile.mkdtemp()
        patcher_uploads = mock.patch.object(team_mod, "UPLOADS_PATH", Path(self._uploads_dir))
        patcher_uploads.start()
        self.addCleanup(patcher_uploads.stop)

        # Make turns fast and reset any shared router state.
        patcher_pause = mock.patch.object(team_mod, "TURN_PAUSE_SECONDS", 0.005)
        patcher_pause.start()
        self.addCleanup(patcher_pause.stop)

    def _wait_for_status(self, session, statuses, timeout: float = 15.0) -> bool:
        return _wait_for(lambda: session.status in statuses, timeout)

    def test_lifecycle_verdict_and_rolodex(self):
        # CEO's first message carries a verdict the parser must capture.
        content = (
            "This can be done safely if we keep it behind a flag. "
            "VERDICT: SAFE - proceed in small increments."
        )
        patcher = mock.patch.object(team_mod, "llm_complete", _fake_llm(content))
        patcher.start()
        self.addCleanup(patcher.stop)
        s = team_mod.start_session("Add a dark mode toggle")
        self.assertTrue(self._wait_for_status(s, {"awaiting_user", "done", "error"}, 15.0))

        self.assertEqual(s.status, "awaiting_user")
        self.assertEqual(s.phase, "responding")
        self.assertEqual(s.verdict["level"], "safe")
        self.assertIn("VERDICT: SAFE", s.verdict["summary"])

        agents_spoke = [m["agent_id"] for m in s.transcript if m["kind"] == "agent"]
        self.assertEqual(set(agents_spoke), set(team_mod.AGENT_BY_ID))
        # Every agent finished its turn.
        self.assertTrue(all(st["status"] == "done" for st in s.statuses.values()))
        # A system round-complete marker closes the round.
        self.assertTrue(any(m["kind"] == "system" for m in s.transcript))

    def test_synth_fallback_when_no_llm_configured(self):
        # No provider/LLM available -> agents fall back to templates (synth).
        patcher = mock.patch.object(team_mod, "llm_complete", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        s = team_mod.start_session("Migrate to PostgreSQL")
        self.assertTrue(self._wait_for_status(s, {"awaiting_user", "done", "error"}, 15.0))

        agent_msgs = [m for m in s.transcript if m["kind"] == "agent"]
        self.assertTrue(agent_msgs, "agents should still speak via templates")
        self.assertTrue(all(m["synth"] for m in agent_msgs))
        self.assertTrue(all(m["content"].strip() for m in agent_msgs))
        # The fallback CEO text tags a verdict, so it gets parsed.
        self.assertEqual(s.verdict["level"], "risk")

    def test_verdict_break_parsing(self):
        s = team_mod.TeamSession("test")
        s._parse_verdict("This would rip out the auth layer. VERDICT: BREAK")
        self.assertEqual(s.verdict["level"], "break")

    def test_reply_continuation_spawns_bounded_round(self):
        patcher = mock.patch.object(team_mod, "llm_complete", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        s = team_mod.start_session("Refactor the checkout flow")
        self.assertTrue(self._wait_for_status(s, {"awaiting_user", "done", "error"}, 15.0))
        turns_before = sum(st["turns"] for st in s.statuses.values())

        again = team_mod.reply_to_session(s.id, "Go ahead, I approve the risk")
        self.assertIsNotNone(again)
        self.assertTrue(_wait_for(lambda: s.status == "awaiting_user" and
                                  sum(st["turns"] for st in s.statuses.values()) > turns_before,
                                  15.0))
        # The user message is recorded in the transcript.
        self.assertTrue(any(m["kind"] == "user" and "I approve" in m["content"] for m in s.transcript))

    def test_snapshot_shape(self):
        patcher = mock.patch.object(team_mod, "llm_complete", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        s = team_mod.start_session("hello team")
        self.assertTrue(self._wait_for_status(s, {"awaiting_user", "done", "error"}, 15.0))
        snap = s.snapshot()
        for key in ("id", "request", "status", "phase", "verdict", "statuses",
                    "transcript", "created_at", "updated_at"):
            self.assertIn(key, snap)
        self.assertIn("level", snap["verdict"])
        # Registry persistence round-trips.
        team_mod.list_sessions(limit=5)


class AgentApiTestCase(unittest.TestCase):
    """Full-stack API tests.

    Runs with auth deterministically ENABLED (same approach as
    test_api_security.TestAuthEnforcement) and authenticates via a real
    token, so the tests pass regardless of the ambient .env AUTH_ENABLED
    value and leave the shared security state untouched afterwards.
    """

    def setUp(self):
        from backend import security as sec
        from backend.app import app

        self._prev_auth = sec.AUTH_ENABLED
        os.environ["GITFIX_ADMIN_USERNAME"] = "admin"
        os.environ["GITFIX_ADMIN_PASSWORD"] = "phase2-agent-test"
        sec.init_security("agent-team-test-secret", auth_enabled=True)
        sec.AUTH_ENABLED = True
        self.addCleanup(setattr, sec, "AUTH_ENABLED", self._prev_auth)
        self.addCleanup(os.environ.pop, "GITFIX_ADMIN_PASSWORD", None)

        # Isolated uploads directory for this suite.
        self._uploads_dir = tempfile.mkdtemp()
        from pathlib import Path
        patcher_uploads = mock.patch.object(team_mod, "UPLOADS_PATH", Path(self._uploads_dir))
        patcher_uploads.start()
        self.addCleanup(patcher_uploads.stop)

        app.config["TESTING"] = True
        self.client = app.test_client()
        self.token = self._login()

    def _login(self) -> str:
        resp = self.client.post("/api/v1/auth/login",
                                json={"username": "admin", "password": "phase2-agent-test"})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def test_roster_endpoint(self):
        resp = self.client.get("/api/v1/agents/roster", headers=self._headers())
        self.assertEqual(resp.status_code, 200)
        ids = {a["id"] for a in resp.get_json()["agents"]}
        self.assertIn("ceo", ids)
        self.assertIn("qa", ids)
        self.assertIn("designer", ids)

    def test_session_lifecycle_via_api(self):
        patcher = mock.patch.object(team_mod, "llm_complete", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        resp = self.client.post("/api/v1/agents/sessions",
                                json={"request": "Ship a landing page"},
                                headers=self._headers())
        self.assertEqual(resp.status_code, 201)
        session = resp.get_json()["session"]
        sid = session["id"]

        # Poll until the session settles.
        polled = None
        for _ in range(300):
            snap = self.client.get(f"/api/v1/agents/sessions/{sid}",
                                   headers=self._headers()).get_json()["session"]
            if snap["status"] in ("awaiting_user", "done", "error"):
                polled = snap
                break
            time.sleep(0.05)

        self.assertIsNotNone(polled)
        self.assertEqual(polled["status"], "awaiting_user")
        self.assertTrue(any(m["kind"] == "agent" for m in polled["transcript"]))

        # Reply -> continuation round runs and returns the updated snapshot.
        chat = self.client.post(f"/api/v1/agents/sessions/{sid}/message",
                                json={"message": "Proceed but watch regressions"},
                                headers=self._headers())
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.get_json()["session"]["id"], sid)

    def test_api_validates_request_body(self):
        resp = self.client.post("/api/v1/agents/sessions",
                                json={"request": "  "}, headers=self._headers())
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/v1/agents/sessions", json={},
                                headers=self._headers())
        self.assertEqual(resp.status_code, 400)

    def test_attachment_upload_and_download(self):
        png = b"\x89PNG\r\n\x1a\n" + b"fakepng-data"
        resp = self.client.post(
            "/api/v1/agents/sessions",
            data={"request": "Review this screenshot",
                  "files": (io.BytesIO(png), "wireframe.png")},
            content_type="multipart/form-data",
            headers=self._headers(),
        )
        self.assertEqual(resp.status_code, 201)
        session = resp.get_json()["session"]
        sid = session["id"]

        first_user = next(m for m in session["transcript"] if m["kind"] == "user")
        self.assertEqual(len(first_user["attachments"]), 1)
        att = first_user["attachments"][0]
        self.assertEqual(att["kind"], "image")
        self.assertEqual(att["name"], "wireframe.png")
        self.assertTrue(att["url"].startswith(f"/api/v1/agents/sessions/{sid}/attachments/"))

        # Inline image download round-trips the exact bytes.
        dl = self.client.get(att["url"], headers=self._headers())
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.data, png)

        # Query-param token works too (media tags can't send headers).
        dlq = self.client.get(f"{att['url']}?token={self.token}")
        self.assertEqual(dlq.status_code, 200)
        self.assertEqual(dlq.data, png)
        self.assertEqual(self.client.get(att["url"], headers=self._headers()).status_code, 200)

        # Reply accepts multipart with an audio file.
        audio = {"message": "Listen to this",
                 "files": (io.BytesIO(b"ID3 fake audio"), "note.webm", "audio/webm")}
        chat = self.client.post(f"/api/v1/agents/sessions/{sid}/message",
                                data=audio,
                                content_type="multipart/form-data",
                                headers=self._headers())
        self.assertEqual(chat.status_code, 200)
        user_msgs = [m for m in chat.get_json()["session"]["transcript"] if m["kind"] == "user"]
        self.assertTrue(any(
            len(m.get("attachments", [])) == 1 and m["attachments"][0]["kind"] == "audio"
            for m in user_msgs
        ))

        # Attachment-only messages are allowed; empty messages are not.
        only = {"files": (io.BytesIO(b"plain attachment"), "notes.txt")}
        r2 = self.client.post(f"/api/v1/agents/sessions/{sid}/message", data=only,
                              content_type="multipart/form-data", headers=self._headers())
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.post(f"/api/v1/agents/sessions/{sid}/message", json={},
                              headers=self._headers())
        self.assertEqual(r3.status_code, 400)

        # Files download with attachment disposition and metadata name.
        user_msgs2 = [m for m in r2.get_json()["session"]["transcript"]
                      if m.get("kind") == "user"]
        self.assertTrue(user_msgs2)
        txt = user_msgs2[-1]
        self.assertEqual(txt["attachments"][0]["name"], "notes.txt")
        target = txt["attachments"][0]["url"]

        resp = self.client.get(f"/api/v1/agents/sessions/{sid}/attachments/nope.png",
                               headers=self._headers())
        self.assertEqual(resp.status_code, 404)
        dl2 = self.client.get(target, headers=self._headers())
        self.assertEqual(dl2.status_code, 200)
        self.assertEqual(dl2.data, b"plain attachment")

        # Let background agent turns finish so later tests aren't affected.
        t = team_mod._session_threads.get(sid)
        if t is not None:
            t.join(timeout=10)

    def test_stop_endpoint(self):
        patcher = mock.patch.object(team_mod, "llm_complete", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        resp = self.client.post("/api/v1/agents/sessions",
                                json={"request": "Pause me"}, headers=self._headers())
        sid = resp.get_json()["session"]["id"]
        stop = self.client.post(f"/api/v1/agents/sessions/{sid}/stop",
                                headers=self._headers())
        self.assertEqual(stop.status_code, 200)
        self.assertEqual(stop.get_json()["session"]["status"], "done")


if __name__ == "__main__":
    unittest.main()