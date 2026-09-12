#!/usr/bin/env python3
# =============================================================================
# Core config & background-queue tests (Phase 2)
# =============================================================================
#   python -m pytest backend/test_core.py -q
# =============================================================================

import os
import sys
import time
import threading
import unittest
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("APP_ENV", "development")


class TestMemoryDbPath(unittest.TestCase):

    def setUp(self):
        # Isolate from env that other test modules (.env loading) may set.
        for key in ("GITFIX_MEMORY_PATH", "DATABASE_URL"):
            self._saved = os.environ.pop(key, None)

    def tearDown(self):
        for key in ("GITFIX_MEMORY_PATH", "DATABASE_URL"):
            os.environ.pop(key, None)

    def test_default_fallback(self):
        from backend.config import memory_db_path
        path = memory_db_path()
        self.assertTrue(path.endswith("memory.db"))

    def test_explicit_override_wins(self):
        from backend.config import memory_db_path
        os.environ["GITFIX_MEMORY_PATH"] = "/tmp/custom.db"
        self.assertEqual(memory_db_path(), "/tmp/custom.db")

    def test_sqlite_database_url(self):
        from backend.config import memory_db_path
        os.environ["DATABASE_URL"] = "sqlite:////tmp/from_url.db"
        self.assertEqual(memory_db_path(), "/tmp/from_url.db")

    def test_postgres_database_url_falls_back(self):
        from backend.config import memory_db_path
        os.environ["DATABASE_URL"] = "postgresql://app-user:your-password@dbhost:5432/db"
        path = memory_db_path()
        self.assertTrue(path.endswith("memory.db"))


class TestLoadEnv(unittest.TestCase):
    """GITFIX_SKIP_DOTENV=1 disables .env loading; real env vars never overridden."""

    def test_skip_flag_bypasses_loading(self):
        from backend.config import load_env
        os.environ["GITFIX_SKIP_DOTENV"] = "1"
        # Should return without raising whether or not .env exists.
        load_env("/definitely/not/a/real/path/.env")

    def test_existing_env_not_overridden(self):
        from backend.config import load_env
        os.environ["GITFIX_TRY_VALUE"] = "already-set"
        os.environ.pop("GITFIX_SKIP_DOTENV", None)
        load_env(os.path.join(ROOT, ".env"))
        self.assertEqual(os.environ.get("GITFIX_TRY_VALUE"), "already-set")


class TestFormatter(unittest.TestCase):
    """LOG_FORMAT=json → JSON logs; invalid values never crash boot."""

    def setUp(self):
        self._saved = os.environ.get("LOG_FORMAT")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LOG_FORMAT", None)
        else:
            os.environ["LOG_FORMAT"] = self._saved

    def test_json_format(self):
        from backend.config import formatter
        os.environ["LOG_FORMAT"] = "json"
        fmt = formatter()
        self.assertEqual(fmt.__class__.__name__, "JsonFormatter")

    def test_invalid_format_falls_back(self):
        from backend.config import formatter
        os.environ["LOG_FORMAT"] = "not-a-format>>>"
        fmt = formatter()
        self.assertEqual(fmt.__class__.__name__, "Formatter")

    def test_default_format(self):
        from backend.config import formatter
        os.environ.pop("LOG_FORMAT", None)
        self.assertEqual(formatter().__class__.__name__, "Formatter")


class TestBackgroundQueue(unittest.TestCase):
    """submit() runs work on a background thread pool, never on the caller."""

    def setUp(self):
        from backend import queue
        self.queue = queue

    def test_submit_runs_in_background(self):
        main_tid = threading.get_ident()
        result = {}

        def worker():
            time.sleep(0.05)
            result["tid"] = threading.get_ident()
            result["ran"] = True

        self.queue.submit(worker)
        self.assertNotIn("ran", result)  # not run synchronously
        deadline = time.time() + 5
        while time.time() < deadline and not result.get("ran"):
            time.sleep(0.01)
        self.assertTrue(result.get("ran"))
        self.assertNotEqual(result["tid"], main_tid)

    def test_submit_survives_worker_exception(self):
        def bad():
            raise RuntimeError("boom")

        self.queue.submit(bad)  # must not raise to caller
        time.sleep(0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)