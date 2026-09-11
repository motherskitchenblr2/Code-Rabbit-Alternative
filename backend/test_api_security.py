#!/usr/bin/env python3
# =============================================================================
# API-level security regression tests (Phase 1 hardening)
# =============================================================================
#   python -m pytest backend/test_api_security.py -q
# =============================================================================

import os
import sys
import json
import hmac
import hashlib
import tempfile
import unittest
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")
os.environ["GITFIX_MEMORY_PATH"] = os.path.join(
    tempfile.gettempdir(), f"gitfix-test-api-security-{os.getpid()}.db")

from backend import security as sec
from backend.app import app, GITHUB_WEBHOOK_SECRET


def _webhook_payload(**overrides):
    payload = {
        "event": "pull_request",
        "action": "opened",
        "repository": {"id": 1, "full_name": "org/repo"},
        "pull_request": {
            "number": 1,
            "user": {"type": "User"},
            "head": {"sha": "abc123"},
            "base": {"sha": "def456"},
            "diff_url": "https://example.com/diff",
            "title": "test pr",
        },
        "installation": {"id": 1},
    }
    payload.update(overrides)
    return payload


def _sign(payload_bytes: bytes) -> str:
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


class TestDefaultsAreOpenAndWorking(unittest.TestCase):
    """Auth/rate-limit gates are off by default so nothing regresses."""

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_read_endpoints_work(self):
        self.assertEqual(self.client.get("/api/self-improvement/status").status_code, 200)
        self.assertEqual(self.client.get("/api/self-improvement/snapshot").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/health").status_code, 200)

    def test_me_returns_anonymous_when_auth_disabled(self):
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json().get("role"), "viewer")


class TestWebhookHmacValidation(unittest.TestCase):

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_valid_signature_accepted(self):
        body = json.dumps(_webhook_payload()).encode()
        resp = self.client.post(
            "/api/v1/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": _sign(body)},
        )
        self.assertEqual(resp.status_code, 202)

    def test_invalid_signature_rejected(self):
        body = json.dumps(_webhook_payload()).encode()
        resp = self.client.post(
            "/api/v1/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
        )
        self.assertEqual(resp.status_code, 401)

    def test_missing_signature_rejected(self):
        body = json.dumps(_webhook_payload()).encode()
        resp = self.client.post(
            "/api/v1/webhook",
            data=body,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class TestErrorTypeAllowlist(unittest.TestCase):

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_known_type_works(self):
        resp = self.client.post(
            "/api/self-improvement/errors/handle",
            json={"error_type": "ValueError", "message": "boom"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.get_json().get("recovered"))

    def test_arbitrary_type_falls_back_to_runtime_error(self):
        resp = self.client.post(
            "/api/self-improvement/errors/handle",
            json={"error_type": "eval", "message": "pwn"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data.get("recovered"))
        self.assertTrue(data.get("escalate"))


class TestInputValidation(unittest.TestCase):

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_oversize_message_rejected(self):
        resp = self.client.post(
            "/api/self-improvement/errors/handle",
            json={"error_type": "RuntimeError", "message": "x" * 6000},
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_recovery_strategy_returns_400(self):
        resp = self.client.post(
            "/api/self-improvement/errors/reflexes",
            json={"error_type": "X", "strategy": "nope"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("strategy", resp.get_json().get("error", ""))


class TestStoredXssEscape(unittest.TestCase):

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_dashboard_escapes_html(self):
        evil = "<script>alert(1)</script>"
        self.client.post(
            "/api/self-improvement/goals",
            json={"name": evil, "description": "d", "target_skill": "t",
                  "milestones": ["m1"]},
        )
        resp = self.client.get("/api/self-improvement/dashboard")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", body)


class TestRateLimitingStdlib(unittest.TestCase):

    def setUp(self):
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def test_skills_train_blocks_after_limit(self):
        codes = {}
        for i in range(40):
            r = self.client.post(
                "/api/self-improvement/skills/train", json={"skill": f"s{i}"})
            codes[r.status_code] = codes.get(r.status_code, 0) + 1
        self.assertEqual(codes.get(200, 0), 30)
        self.assertEqual(codes.get(429, 0), 10)


class TestAuthEnforcement(unittest.TestCase):
    """When AUTH_ENABLED=true, write routes require a valid admin token."""

    def setUp(self):
        sec._ratelimit_buckets.clear()
        sec.AUTH_ENABLED = True
        sec.init_security("test-secret-key-for-api-tests")
        self.client = app.test_client()
        os.environ["GITFIX_ADMIN_PASSWORD"] = "phase1-test-pass"
        os.environ["GITFIX_ADMIN_USERNAME"] = "admin"

    def tearDown(self):
        sec.AUTH_ENABLED = False
        os.environ.pop("GITFIX_ADMIN_PASSWORD", None)

    def test_unauthenticated_write_returns_401(self):
        resp = self.client.post(
            "/api/self-improvement/errors/handle",
            json={"error_type": "ValueError"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_and_authed_write(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "phase1-test-pass"},
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.get_json()["access_token"]

        resp = self.client.get("/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["role"], "admin")

        resp = self.client.post(
            "/api/self-improvement/errors/handle",
            json={"error_type": "ValueError"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)

    def test_viewer_token_rejected_on_write(self):
        viewer = sec.create_token("reader", "viewer")
        resp = self.client.post(
            "/api/self-improvement/memory",
            json={"key": "k", "content": "v"},
            headers={"Authorization": f"Bearer {viewer}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_bad_credentials_rejected(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_refresh_cycle(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin", "password": "phase1-test-pass"},
        ).get_json()
        resp = self.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.get_json())


class TestFailLoudProductionSecret(unittest.TestCase):
    """Non-development environments refuse to boot without a webhook secret."""

    def test_missing_secret_raises_in_production(self):
        env = dict(os.environ)
        env["APP_ENV"] = "production"
        env.pop("GITHUB_WEBHOOK_SECRET", None)
        proc = subprocess.run(
            [sys.executable, "-c", "import backend.app"],
            cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=120,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("GITHUB_WEBHOOK_SECRET", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)