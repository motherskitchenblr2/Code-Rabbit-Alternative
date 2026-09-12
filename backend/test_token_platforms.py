#!/usr/bin/env python3
# =============================================================================
# Access-token platform probe tests
# =============================================================================
#   python -m pytest backend/test_token_platforms.py -q
# =============================================================================
# Exercises _probe_token for the token/credential platforms in
# backend/admin/api.py (Vercel, Netlify, Cloudflare, Hugging Face, Codeberg,
# Jira, Linear, Datadog, Sentry, PostgreSQL, Redis, Qdrant, Prometheus, plus
# the original GitHub/GitLab/Bitbucket/Azure DevOps). All HTTP/TCP I/O is
# stubbed so tests are fast and offline.
# =============================================================================

import os
import sys
import base64
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")

from backend.admin import api as admin_api


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


class _FakeClient:
    def __init__(self, get_status: int = 200, post_status: int = 200):
        self.get_status = get_status
        self.post_status = post_status
        self.get_calls = []
        self.post_calls = []

    def get(self, url, headers=None, **kwargs):
        self.get_calls.append((url, headers))
        return _FakeResponse(self.get_status)

    def post(self, url, headers=None, json=None, **kwargs):
        self.post_calls.append((url, headers, json))
        return _FakeResponse(self.post_status)


class _Conn:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TokenPlatformProbeTests(unittest.TestCase):

    def _probe(self, platform, token, endpoint=""):
        return admin_api._probe_token(
            {"platform": platform, "token": token, "endpoint": endpoint})


# ── Original platforms keep working ─────────────────────────────────────────

    def test_github_bearer_auth(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("github", "ghp_secret1234")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://api.github.com/user")
        self.assertEqual(client.get_calls[0][1].get("Authorization"), "Bearer ghp_secret1234")

    def test_gitlab_private_token_header(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("gitlab", "glpat-secret")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][1].get("PRIVATE-TOKEN"), "glpat-secret")

    def test_bitbucket_basic_auth(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("bitbucket", "user:app-password")
        self.assertTrue(res["ok"])
        expected = "Basic " + base64.b64encode(b"user:app-password").decode("ascii")
        self.assertEqual(client.get_calls[0][1].get("Authorization"), expected)

    def test_azure_devops_basic_colon_prefix(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("azure_devops", "azpat")
        self.assertTrue(res["ok"])
        expected = "Basic " + base64.b64encode(b":azpat").decode("ascii")
        self.assertEqual(client.get_calls[0][1].get("Authorization"), expected)

# ── New token platforms ─────────────────────────────────────────────────────

    def test_vercel_bearer(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("vercel", "vercel_secret")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://api.vercel.com/v2/user")
        self.assertEqual(client.get_calls[0][1].get("Authorization"), "Bearer vercel_secret")

    def test_huggingface_invalid_token(self):
        client = _FakeClient(get_status=401)
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("huggingface", "hf_bogus")
        self.assertFalse(res["ok"])
        self.assertIn("Invalid token", res["detail"])
        self.assertEqual(client.get_calls[0][0], "https://huggingface.co/api/whoami-v2")

    def test_codeberg_token_auth(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("codeberg", "cb_secret")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][1].get("Authorization"), "token cb_secret")

    def test_cloudflare_invalid_returns_400(self):
        client = _FakeClient(get_status=400)
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("cloudflare", "cf_secret")
        self.assertFalse(res["ok"])
        self.assertIn("Invalid token", res["detail"])

    def test_netlify_ok(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("netlify", "nf_secret")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://api.netlify.com/api/v1/user")

    def test_jira_requires_endpoint(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("jira", "me@example.com:apitoken")
        self.assertFalse(res["ok"])
        self.assertIn("Set your site URL", res["detail"])
        self.assertEqual(client.get_calls, [])

    def test_jira_endpoint_override_used(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("jira", "me@example.com:apitoken", endpoint="https://acme.atlassian.net/")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://acme.atlassian.net/rest/api/2/myself")
        expected = "Basic " + base64.b64encode(b"me@example.com:apitoken").decode("ascii")
        self.assertEqual(client.get_calls[0][1].get("Authorization"), expected)

    def test_linear_graphql_post(self):
        client = _FakeClient(post_status=200)
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("linear", "lin_key")
        self.assertTrue(res["ok"])
        url, headers, body = client.post_calls[0]
        self.assertEqual(url, "https://api.linear.app/graphql")
        self.assertEqual(headers.get("Authorization"), "Linear lin_key")
        self.assertIn("viewer", body["query"])

    def test_linear_invalid(self):
        client = _FakeClient(post_status=401)
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("linear", "lin_bad")
        self.assertFalse(res["ok"])
        self.assertIn("Invalid token", res["detail"])

    def test_datadog_api_key_header(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("datadog", "DD-KEY")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][1].get("DD-API-KEY"), "DD-KEY")
        self.assertEqual(client.get_calls[0][0], "https://api.datadoghq.com/api/v1/validate")

    def test_datadog_regional_endpoint_override(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("datadog", "DD-KEY", endpoint="https://api.eu.datadoghq.com")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://api.eu.datadoghq.com/api/v1/validate")

    def test_sentry_endpoint_override(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("sentry", "snt_key", endpoint="https://sentry.example.com/")
        self.assertTrue(res["ok"])
        self.assertEqual(client.get_calls[0][0], "https://sentry.example.com/api/0/")

# ── TCP (connection-string) platforms ───────────────────────────────────────

    def test_redis_tcp_reachable(self):
        with mock.patch("socket.create_connection", return_value=_Conn()) as mk:
            res = self._probe("redis", "redis://:pw@myhost.example.com:6379/0")
        mk.assert_called_once_with(("myhost.example.com", 6379), timeout=admin_api.PROBE_TIMEOUT)
        self.assertTrue(res["ok"])
        self.assertIn("myhost.example.com:6379", res["detail"])

    def test_redis_tcp_unreachable(self):
        with mock.patch("socket.create_connection", side_effect=ConnectionRefusedError):
            res = self._probe("redis", "myhost.example.com:6379")
        self.assertFalse(res["ok"])
        self.assertIn("Connection failed", res["detail"])

    def test_postgresql_parse_and_default_port(self):
        with mock.patch("socket.create_connection", return_value=_Conn()) as mk:
            res = self._probe("postgresql", "postgresql://user:pass@dbhost:5433/app")
        mk.assert_called_once_with(("dbhost", 5433), timeout=admin_api.PROBE_TIMEOUT)
        self.assertTrue(res["ok"])

    def test_postgresql_unparseable_string(self):
        with mock.patch("socket.create_connection") as mk:
            res = self._probe("postgresql", "")
        mk.assert_not_called()
        self.assertFalse(res["ok"])
        self.assertIn("No credential", res["detail"])

# ── URL-based HTTP platforms ────────────────────────────────────────────────

    def test_qdrant_get_collections(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("qdrant", "http://localhost:6333")
        self.assertTrue(res["ok"])
        self.assertIn("Endpoint reachable", res["detail"])
        self.assertEqual(client.get_calls[0][0], "http://localhost:6333/collections")

    def test_prometheus_unexpected_status(self):
        client = _FakeClient(get_status=404)
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("prometheus", "http://localhost:9090")
        self.assertFalse(res["ok"])
        self.assertIn("Unexpected HTTP 404", res["detail"])
        self.assertEqual(client.get_calls[0][0], "http://localhost:9090/api/v1/status/buildinfo")

# ── Misc ────────────────────────────────────────────────────────────────────

    def test_missing_credential(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("github", "")
        self.assertFalse(res["ok"])
        self.assertEqual(client.get_calls, [])

    def test_unsupported_platform(self):
        client = _FakeClient()
        with mock.patch.object(admin_api, "http_client", client):
            res = self._probe("totally_unknown", "abc")
        self.assertFalse(res["ok"])
        self.assertIn("Unsupported platform", res["detail"])
        self.assertEqual(client.get_calls, [])


if __name__ == "__main__":
    unittest.main()