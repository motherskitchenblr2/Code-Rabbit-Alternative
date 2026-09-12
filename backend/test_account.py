#!/usr/bin/env python3
# =============================================================================
# Account / Security tab tests (password, 2FA, API keys, active sessions)
# =============================================================================
#   python -m pytest backend/test_account.py -q
# =============================================================================
# Exercises the /api/v1/auth account surface end-to-end against the real app:
# TOTP enrollment + login gating, password storage, hashed API keys, and
# per-device session listing/revocation. All state is redirected to a temp
# account file so ~/.gitfix is never touched.
# =============================================================================

import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")
os.environ["GITFIX_ADMIN_USERNAME"] = "admin"
os.environ["GITFIX_ADMIN_PASSWORD"] = "env-pass-123"

from backend.auth import store as store_mod
from backend.auth import totp
from backend import security as sec
from backend.app import app

TEST_SECRET = "test-account-secret"


class AccountTestCase(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="gitfix-test-account-")
        self._orig_file = store_mod.ACCOUNT_FILE
        store_mod.ACCOUNT_FILE = Path(self._tmpdir) / "auth" / "account.json"
        store_mod.reset()
        self.addCleanup(self._restore)
        self._orig_auth = sec.AUTH_ENABLED
        sec.init_security(TEST_SECRET, auth_enabled=True)
        self.addCleanup(setattr, sec, "AUTH_ENABLED", self._orig_auth)
        sec._ratelimit_buckets.clear()
        self.client = app.test_client()
        # Direct signed token for admin-gated calls — avoids registering an
        # extra device session that would skew the sessions tests.
        self._admin_headers = self._auth(sec.create_token("admin", role="admin"))

    def _restore(self):
        store_mod.ACCOUNT_FILE = self._orig_file
        store_mod.reset()

    def _login(self, password="env-pass-123", code=None, username="admin"):
        body = {"username": username, "password": password}
        if code is not None:
            body["code"] = code
        resp = self.client.post("/api/v1/auth/login", json=body)
        return resp

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _enable_2fa(self):
        setup = self.client.post("/api/v1/auth/2fa/setup", headers=self._admin_headers)
        self.assertEqual(setup.status_code, 200)
        secret = setup.get_json()["secret"]
        self._secret = secret
        code = totp.current_code(secret)
        enable = self.client.post("/api/v1/auth/2fa/enable", headers=self._admin_headers, json={"code": code})
        self.assertEqual(enable.status_code, 200)
        return secret

    # ── 2FA ──────────────────────────────────────────────────────────────────

    def test_2fa_setup_returns_secret_and_uri(self):
        resp = self.client.post("/api/v1/auth/2fa/setup", headers=self._admin_headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertFalse(body["enabled"])
        self.assertEqual(len(body["secret"]), 32)
        self.assertIn("otpauth://totp/", body["otpauth_uri"])
        self.assertIn(body["secret"], body["otpauth_uri"])

    def test_2fa_enable_rejects_wrong_code(self):
        self.client.post("/api/v1/auth/2fa/setup", headers=self._admin_headers)
        resp = self.client.post("/api/v1/auth/2fa/enable", headers=self._admin_headers, json={"code": "000000"})
        self.assertEqual(resp.status_code, 400)

    def test_2fa_enable_then_login_requires_code(self):
        self._enable_2fa()
        # Stored password not set yet → env bootstrap password.
        no_code = self._login()
        self.assertEqual(no_code.status_code, 401)
        self.assertTrue(no_code.get_json().get("totp_required"))
        with_code = self._login(password="env-pass-123", code=totp.current_code(self._secret or ""))
        self.assertEqual(with_code.status_code, 200)

    def test_2fa_disable_requires_code(self):
        self._enable_2fa()
        bad = self.client.post("/api/v1/auth/2fa/disable", headers=self._admin_headers, json={"code": "111111"})
        self.assertEqual(bad.status_code, 400)
        good = self.client.post("/api/v1/auth/2fa/disable", headers=self._admin_headers, json={"code": totp.current_code(self._secret or "")})
        self.assertEqual(good.status_code, 200)
        # Code no longer required at login.
        resp = self._login()
        self.assertEqual(resp.status_code, 200)

    def test_2fa_status_reflects_state(self):
        self.assertFalse(self.client.get("/api/v1/auth/2fa/status", headers=self._admin_headers).get_json()["enabled"])
        self._enable_2fa()
        self.assertTrue(self.client.get("/api/v1/auth/2fa/status", headers=self._admin_headers).get_json()["enabled"])

    # ── password ─────────────────────────────────────────────────────────────

    def test_password_first_change_requires_env_password(self):
        bad = self.client.post("/api/v1/auth/password", headers=self._admin_headers, json={
            "current_password": "wrong", "new_password": "fresh-pass-456"})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post("/api/v1/auth/password", headers=self._admin_headers, json={
            "current_password": "env-pass-123", "new_password": "fresh-pass-456"})
        self.assertEqual(ok.status_code, 200)

    def test_password_change_then_login_uses_stored(self):
        self.client.post("/api/v1/auth/password", headers=self._admin_headers, json={
            "current_password": "env-pass-123", "new_password": "fresh-pass-456"})
        # Env password is retired once a stored password exists.
        self.assertEqual(self._login(password="env-pass-123").status_code, 401)
        ok = self._login(password="fresh-pass-456")
        self.assertEqual(ok.status_code, 200)

    def test_password_requires_min_length(self):
        resp = self.client.post("/api/v1/auth/password", headers=self._admin_headers, json={
            "current_password": "env-pass-123", "new_password": "short"})
        self.assertEqual(resp.status_code, 400)

    # ── API keys ─────────────────────────────────────────────────────────────

    def test_api_key_lifecycle(self):
        created = self.client.post("/api/v1/auth/api-keys", headers=self._admin_headers, json={"name": "ci"})
        self.assertEqual(created.status_code, 201)
        body = created.get_json()
        key = body["key"]
        self.assertTrue(key.startswith("gfk_"))
        self.assertEqual(body["record"]["tail"], key[-8:])
        self.assertNotIn("key_hash", body["record"])
        self.assertNotIn(key, body["record"].get("name", ""))

        listed = self.client.get("/api/v1/auth/api-keys", headers=self._admin_headers)
        keys = listed.get_json()["keys"]
        self.assertEqual(len(keys), 1)
        self.assertNotIn("key_hash", keys[0])
        self.assertNotIn("gfk_", str(keys[0]))

        with_code = self.client.get("/api/v1/auth/api-keys", headers={"X-API-Key": key})
        self.assertEqual(with_code.status_code, 200)
        with_query = self.client.get("/api/v1/auth/api-keys?api_key=" + key)
        self.assertEqual(with_query.status_code, 200)
        self.client.delete(f"/api/v1/auth/api-keys/{body['record']['id']}", headers=self._admin_headers)
        self.assertEqual(
            self.client.get("/api/v1/auth/api-keys", headers={"X-API-Key": key}).status_code, 401)

    def test_api_key_unknown_rejected(self):
        resp = self.client.get("/api/v1/auth/api-keys", headers={"X-API-Key": "gfk_bogus"})
        self.assertEqual(resp.status_code, 401)

    # ── sessions ─────────────────────────────────────────────────────────────

    def test_sessions_list_and_revoke(self):
        login_a = self._login()
        login_b = self._login()
        self.assertEqual(login_a.status_code, 200)
        self.assertEqual(login_b.status_code, 200)
        token_a = login_a.get_json()["access_token"]
        token_b = login_b.get_json()["access_token"]
        refresh_b = login_b.get_json()["refresh_token"]

        sessions = self.client.get("/api/v1/auth/sessions", headers=self._auth(token_a)).get_json()["sessions"]
        self.assertEqual(len(sessions), 2)
        current = [s for s in sessions if s["current"]]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["device"].split(" on ")[0], "Browser")
        other = next(s for s in sessions if not s["current"])

        revoke = self.client.post("/api/v1/auth/sessions/revoke", headers=self._auth(token_a), json={"id": other["id"]})
        self.assertEqual(revoke.status_code, 200)

        self.assertEqual(
            self.client.get("/api/v1/auth/api-keys", headers=self._auth(token_b)).status_code, 401)
        self.assertEqual(
            self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_b}).status_code, 401)

        # The surviving session still works.
        self.assertEqual(
            self.client.get("/api/v1/auth/api-keys", headers=self._auth(token_a)).status_code, 200)

    def test_revoke_all_except_current(self):
        token_a = self._login().get_json()["access_token"]
        refresh_b = self._login().get_json()["refresh_token"]

        revoked = self.client.post(
            "/api/v1/auth/sessions/revoke-all", headers=self._auth(token_a)).get_json()
        self.assertEqual(revoked["revoked"], 1)

        self.assertEqual(
            self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_b}).status_code, 401)
        self.assertEqual(
            self.client.get("/api/v1/auth/api-keys", headers=self._auth(token_a)).status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)