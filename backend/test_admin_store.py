#!/usr/bin/env python3
# =============================================================================
# Admin settings store encryption tests
# =============================================================================
#   python -m pytest backend/test_admin_store.py -q
# =============================================================================
# Verifies secret-at-rest behaviour: Fernet round-trips, tampered blobs are
# retained without leaking (and logged), and the plaintext fallback never
# happens silently.
# =============================================================================

import os
import io
import json
import tempfile
import unittest
import logging
from pathlib import Path
from unittest import mock

os.environ.setdefault("APP_ENV", "development")
os.environ["SECRET_KEY"] = "test-secret-key-for-fern-derivation"


class AdminStoreTestCase(unittest.TestCase):

    def _tmp_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from backend.admin import store as store_mod
        store = store_mod.AdminSettings(Path(tmp.name) / "settings.json")
        return store, Path(tmp.name) / "settings.json"

    def test_secret_encrypted_on_disk_and_round_trips(self):
        from backend.admin import store as store_mod
        store, path = self._tmp_store()
        provider = {"id": "openrouter", "name": "OpenRouter",
                    "base_url": "https://openrouter.ai/api/v1",
                    "model": "openrouter/free", "api_key": "sk-or-v1-real-secret-key"}
        store.upsert_ai_provider(provider)

        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(raw["ai_providers"][0]["api_key"].startswith("enc:"))
        self.assertNotIn("sk-or-v1-real-secret-key", path.read_text(encoding="utf-8"))

        reloaded = store_mod.AdminSettings(path).load()
        self.assertEqual(
            reloaded["ai_providers"][0]["api_key"], "sk-or-v1-real-secret-key")

    def test_tampered_blob_is_kept_and_logged_not_crashed(self):
        from backend.admin import store as store_mod
        store, path = self._tmp_store()
        store.upsert_ai_provider(
            {"id": "openai", "name": "OpenAI", "api_key": "sk-real-key",
             "base_url": "https://api.openai.com/v1"})

        raw_text = path.read_text(encoding="utf-8")
        token = "enc:"
        idx = raw_text.find(token)
        self.assertGreater(idx, -1)
        # Flip characters inside the ciphertext -> Fernet auth must reject it.
        corrupted = raw_text[:idx + 4] + ("A" if raw_text[idx + 4] != "A" else "B") + raw_text[idx + 5:]
        path.write_text(corrupted, encoding="utf-8")

        with self.assertLogs(store_mod.logger, level="WARNING") as cm:
            reloaded = store_mod.AdminSettings(path).load()
        self.assertTrue(any("failed to decrypt" in m for m in cm.output))
        self.assertTrue(reloaded["ai_providers"][0]["api_key"].startswith("enc:"))
        self.assertNotIn("sk-real-key", json.dumps(reloaded))

    def test_plaintext_fallback_warns_loudly(self):
        from backend.admin import store as store_mod
        store, path = self._tmp_store()
        with mock.patch.object(store_mod, "_fernet", return_value=None):
            with self.assertLogs(store_mod.logger, level="WARNING") as cm:
                store.upsert_ai_provider(
                    {"id": "groq", "name": "Groq", "api_key": "gsk-plaintext",
                     "base_url": "https://api.groq.com/openai/v1"})
        self.assertTrue(any("PLAINTEXT" in m for m in cm.output))
        self.assertNotIn("enc:", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()