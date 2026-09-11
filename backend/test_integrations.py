#!/usr/bin/env python3
# =============================================================================
# Integrations API tests (notification webhook channels)
# =============================================================================
#   python -m pytest backend/test_integrations.py -q
# =============================================================================
# Exercises the /api/v1/integrations/webhooks surface: CRUD, validation, URL
# masking, and live ping probes. The settings file is redirected to a temp dir
# and all outbound HTTP is stubbed so tests are fast and offline.
# =============================================================================

import os
import sys
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")

from backend.admin import store as store_mod
from backend.integrations import api as integrations_api
from backend import security as sec
from backend.app import app

SLACK_URL = "https://hooks.slack.com/services/T000/B000/secret-token-1234567890"


class _FakeResponse:
    def __init__(self, status_code: int = 204):
        self.status_code = status_code


class IntegrationsApiTestCase(unittest.TestCase):

    def setUp(self):
        # Redirect the admin store to an isolated temp file, never ~/.gitfix.
        self._tmpdir = tempfile.mkdtemp(prefix="gitfix-test-integrations-")
        patcher_path = mock.patch.object(
            store_mod, "DEFAULT_SETTINGS_PATH", Path(self._tmpdir) / "settings.json")
        patcher_path.start()
        self.addCleanup(patcher_path.stop)
        patcher_store = mock.patch.object(store_mod, "_store", None)
        patcher_store.start()
        self.addCleanup(patcher_store.stop)

        # Expedite test access to admin-gated routes.
        patcher_auth = mock.patch.object(sec, "AUTH_ENABLED", False)
        patcher_auth.start()
        self.addCleanup(patcher_auth.stop)

        sec._ratelimit_buckets.clear()
        self.client = app.test_client()

    def _stub_ping(self, ok: bool = True, status: int = 204, detail: str = "Webhook ping delivered"):
        return mock.patch.object(
            integrations_api, "_ping_webhook",
            return_value={"ok": ok, "status": status, "detail": detail})

    def _create(self, **overrides):
        body = {"kind": "slack", "name": "Ops", "url": SLACK_URL}
        body.update(overrides)
        return self.client.post("/api/v1/integrations/webhooks", json=body)

    # ── list & create ────────────────────────────────────────────────────────

    def test_list_starts_empty(self):
        resp = self.client.get("/api/v1/integrations/webhooks")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"webhooks": []})

    def test_create_webhook_success(self):
        with self._stub_ping():
            resp = self._create()
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["id"])
        self.assertEqual(data["kind"], "slack")
        self.assertEqual(data["channel"], "Slack")
        self.assertTrue(data["url_set"])
        self.assertTrue(data["probe"]["ok"])
        # URL is masked on read, never echoed in full.
        self.assertNotIn("secret-token", data["url_tail"])
        self.assertTrue(data["url_tail"].endswith("7890"))

        listed = self.client.get("/api/v1/integrations/webhooks").get_json()["webhooks"]
        self.assertEqual(len(listed), 1)
        self.assertNotIn("secret-token", listed[0]["url_tail"])

    def test_create_webhook_requires_http_url(self):
        for url in ("", "ftp://nope", "not a url"):
            with self.subTest(url=url):
                resp = self._create(url=url) if url else self._create(url="")
                self.assertIn(resp.status_code, (400,), msg=url)

    def test_create_webhook_rejects_unknown_kind(self):
        resp = self._create(kind="jira")
        self.assertEqual(resp.status_code, 400)

    def test_create_echoed_masked_url_keeps_secret(self):
        with self._stub_ping():
            created = self._create().get_json()
        stored = store_mod.get_store().get_webhook_config(created["id"])
        self.assertEqual(stored["url"], SLACK_URL)

        # Client echoes the masked tail back: must not overwrite the secret.
        masked = created["url_tail"]
        with self._stub_ping():
            resp = self._create(id=created["id"], url=masked)
        self.assertEqual(resp.status_code, 200)
        stored_after = store_mod.get_store().get_webhook_config(created["id"])
        self.assertEqual(stored_after["url"], SLACK_URL)

    # ── delete & test ────────────────────────────────────────────────────────

    def test_delete_webhook(self):
        with self._stub_ping():
            wid = self._create().get_json()["id"]
        resp = self.client.delete(f"/api/v1/integrations/webhooks/{wid}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["deleted"])
        self.assertEqual(self.client.get("/api/v1/integrations/webhooks").get_json()["webhooks"], [])
        self.assertEqual(self.client.delete(f"/api/v1/integrations/webhooks/{wid}").status_code, 404)

    def test_test_endpoint_missing_record(self):
        self.assertEqual(
            self.client.post("/api/v1/integrations/webhooks/nope/test").status_code, 404)

    def test_ping_delivered(self):
        with self._stub_ping():
            wid = self._create().get_json()["id"]
        fake = mock.MagicMock()
        fake.post.return_value = _FakeResponse(204)
        with mock.patch.object(integrations_api, "http_client", fake):
            resp = self.client.post(f"/api/v1/integrations/webhooks/{wid}/test")
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], 204)
        payload = fake.post.call_args.kwargs["json"]
        self.assertEqual(payload, {"text": "Git-Fix: webhook connected"})

    def test_ping_discord_payload(self):
        with self._stub_ping():
            wid = self._create(kind="discord").get_json()["id"]
        fake = mock.MagicMock()
        fake.post.return_value = _FakeResponse(204)
        with mock.patch.object(integrations_api, "http_client", fake):
            self.client.post(f"/api/v1/integrations/webhooks/{wid}/test")
        payload = fake.post.call_args.kwargs["json"]
        self.assertEqual(payload, {"content": "Git-Fix: webhook connected"})

    def test_ping_rejected_url(self):
        with self._stub_ping():
            wid = self._create().get_json()["id"]
        fake = mock.MagicMock()
        fake.post.return_value = _FakeResponse(404)
        with mock.patch.object(integrations_api, "http_client", fake):
            resp = self.client.post(f"/api/v1/integrations/webhooks/{wid}/test")
        result = resp.get_json()["result"]
        self.assertFalse(result["ok"])
        self.assertIn("not found", result["detail"])

    # ── auth gating ──────────────────────────────────────────────────────────

    def test_admin_auth_required(self):
        patcher = mock.patch.object(sec, "AUTH_ENABLED", True)
        patcher.start()
        self.addCleanup(patcher.stop)
        resp = self.client.get("/api/v1/integrations/webhooks")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)