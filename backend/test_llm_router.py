#!/usr/bin/env python3
# =============================================================================
# Auto-rotation LLM router tests
# =============================================================================
#   python -m pytest backend/test_llm_router.py -q
# =============================================================================
# Verifies task-aware provider ranking, community-base resolution, circuit
# breaker behaviour, and HTTP failover with a mocked transport layer.
# =============================================================================

import os
import sys
import time
import json
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")
# Use a disposable admin store so tests never touch real settings.
os.environ.setdefault("GITFIX_ADMIN_SETTINGS", "unused")


class RouterTestCase(unittest.TestCase):

    def setUp(self):
        for key in ("NVIDIA_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY",
                    "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            os.environ.setdefault(key, "")
            os.environ[key] = {
                "NVIDIA_API_KEY": "nvapi-test",
                "OPENROUTER_API_KEY": "sk-or-test",
                "GROQ_API_KEY": "gsk-test",
                "GOOGLE_API_KEY": "g-test",
                "ANTHROPIC_API_KEY": "sk-ant-test",
                "OPENAI_API_KEY": "sk-test",
            }[key]

    def tearDown(self):
        from backend.llm import router as llm_router
        llm_router._router = None

    def _router(self):
        from backend.llm.router import get_router
        return get_router()

    def test_task_preference_ranking(self):
        r = self._router()
        snap = r.snapshot()
        code = [c["provider"] for c in snap["routing"]["code_review"]["candidates"]]
        summary = [c["provider"] for c in snap["routing"]["summary"]["candidates"]]
        self.assertEqual(code[0], "nvidia")
        self.assertIn("openrouter", code)
        self.assertEqual(summary[0], "groq")
        self.assertIn("nvidia", summary)

    def test_multimodal_excludes_non_multimodal(self):
        snap = self._router().snapshot()
        multi = [c["provider"] for c in snap["routing"]["multimodal"]["candidates"]]
        self.assertNotIn("groq", multi)  # groq not multimodal -> never a candidate
        self.assertIn("google", multi)

    def test_route_returns_top_healthy_provider(self):
        r = self._router()
        top = r.route("code_review")
        self.assertEqual(top["id"], "nvidia")
        self.assertIn("nemotron", top["model"])

    def test_circuit_breaker_cooldown(self):
        r = self._router()
        r._health_for("nvidia").record_failure("boom")
        r._health_for("nvidia").record_failure("boom")
        r._health_for("nvidia").record_failure("boom")  # >= threshold -> cool down
        top = r.route("code_review")
        # nvidia is now unhealthy; fail over to next candidate.
        self.assertNotEqual(top["id"], "nvidia")
        self.assertIn(top["id"], ("anthropic", "openrouter", "openai"))

    def test_http_failover_rotates_provider(self):
        r = self._router()
        # Only NVIDIA 429s; whichever provider succeeds first is the answer
        # provider, crucially it must NOT be nvidia.
        def fake_post(url, headers=None, json=None, timeout=None):
            if "integrate.api.nvidia.com" in url:
                raise RuntimeError("HTTP 429 rate limited")
            if "anthropic.com" in url:
                body = {"content": [{"type": "text", "text": "hello from anthropic"}]}
            else:
                body = {"choices": [{"message": {"content": "hello from fallback"}}]}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete(
                [{"role": "user", "content": "hi"}], task="code_review", max_tokens=8
            )
        self.assertTrue(result["ok"])
        self.assertNotEqual(result["provider"], "nvidia")
        self.assertTrue(result["content"].startswith("hello from"))
        self.assertEqual(result["attempts"][0]["provider"], "nvidia")
        self.assertEqual(len(result["attempts"]), 2)

    def test_anthropic_protocol_payload(self):
        r = self._router()

        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            if "anthropic.com" in url:
                captured.update({"headers": headers, "body": json})
                body = {"content": [{"type": "text", "text": "anthropic ok"}]}
            else:
                body = {"choices": [{"message": {"content": "fallback ok"}}]}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete(
                [{"role": "system", "content": "be brief"},
                 {"role": "user", "content": "hello"}],
                task="security",
            )
        self.assertTrue(result["ok"])
        if result["provider"] == "anthropic":
            self.assertEqual(captured["headers"].get("x-api-key"), "sk-ant-test")
            self.assertEqual(captured["body"].get("system"), "be brief")
            self.assertEqual(result["content"], "anthropic ok")
        else:
            self.assertIn(result["content"], ("fallback ok", "hello from openrouter"))

    def test_google_gemini_payload(self):
        r = self._router()

        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured.update({"headers": headers or {}, "url": url, "body": json})
            if "generativelanguage" in url:
                body = {"candidates": [{"content": {"parts": [{"text": "gemini ok"}]}}]}
            else:
                body = {"choices": [{"message": {"content": "fallback ok"}}]}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete([{"role": "user", "content": "describe"}], task="multimodal")
        self.assertTrue(result["ok"])
        if result["provider"] == "google":
            self.assertEqual(captured["headers"].get("x-goog-api-key"), "g-test")
            self.assertIn(":generateContent", captured["url"])
            self.assertEqual(result["content"], "gemini ok")
        else:
            self.assertNotEqual(result["provider"], "groq")

    def test_all_providers_fail_returns_ok_false(self):
        r = self._router()

        def fake_post(*args, **kwargs):
            raise RuntimeError("HTTP 500")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete([{"role": "user", "content": "hi"}], task="chat")
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"])

    def test_null_content_falls_back_to_reasoning(self):
        # Free-tier routing can return content=null with only a reasoning
        # field populated (budget spent on chain-of-thought). Callers must
        # never silently receive an empty reply.
        r = self._router()

        def fake_post(url, headers=None, json=None, timeout=None):
            body = {"choices": [{"message": {"role": "assistant", "content": None,
                                             "reasoning": "chain of thought tail"}}]}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete([{"role": "user", "content": "hi"}], task="chat")
        self.assertTrue(result["ok"])
        self.assertEqual(result["content"], "chain of thought tail")
        self.assertNotEqual(result["content"], "")

    def test_openai_content_parts_array_is_joined(self):
        # Some OpenAI-compatible providers return message.content as a list
        # of typed parts; those must be joined into plain text.
        r = self._router()

        def fake_post(url, headers=None, json=None, timeout=None):
            body = {"choices": [{"message": {"role": "assistant", "content": [
                {"type": "text", "text": "hello "},
                {"type": "text", "text": "world"},
            ]}}]}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            result = r.complete([{"role": "user", "content": "hi"}], task="chat")
        self.assertTrue(result["ok"])
        self.assertEqual(result["content"], "hello world")

    def test_ollama_local_no_key_sends_bare_post(self):
        # A local Ollama (no api_key) must keep the legacy no-auth behaviour:
        # base_url differs from the cloud case and no Authorization header.
        r = self._router()
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured.update({"url": url, "headers": headers or {}, "body": json})
            body = {"message": {"role": "assistant", "content": "local ok"}}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        provider = {"id": "ollama", "base_url": "http://localhost:11434", "api_key": ""}
        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            out = r._chat_once(provider, "llama3.2", [{"role": "user", "content": "hi"}], 8, 0.0)
        self.assertEqual(captured["url"], "http://localhost:11434/api/chat")
        self.assertNotIn("Authorization", captured["headers"])
        self.assertFalse(captured["body"]["stream"])
        self.assertEqual(out, "local ok")

    def test_ollama_cloud_with_key_authenticates_and_fixes_path(self):
        # Remote/cloud Ollama is reached via https://ollama.com/api/... (the
        # user sets base_url=https://ollama.com/api). The framework must not
        # double-append /api and must forward the stored API key.
        r = self._router()
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured.update({"url": url, "headers": headers or {}, "body": json})
            body = {"message": {"role": "assistant", "content": "cloud ok"}}
            return mock.MagicMock(status_code=200, json=lambda: body, text="ok")

        provider = {"id": "ollama", "base_url": "https://ollama.com/api", "api_key": "sk-ollama"}
        with mock.patch("backend.llm.router.requests.post", side_effect=fake_post):
            out = r._chat_once(provider, "gemma4:31b-cloud", [{"role": "user", "content": "hi"}], 8, 0.0)
        self.assertEqual(captured["url"], "https://ollama.com/api/chat")
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer sk-ollama")
        self.assertEqual(captured["body"]["model"], "gemma4:31b-cloud")
        self.assertEqual(out, "cloud ok")


if __name__ == "__main__":
    unittest.main()
