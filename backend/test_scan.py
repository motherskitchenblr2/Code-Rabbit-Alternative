#!/usr/bin/env python3
# =============================================================================
# GitHub repositories + deterministic scanner tests (offline)
# =============================================================================
#   python -m pytest backend/test_scan.py -q
# =============================================================================
# Exercises the rule engine and scanner orchestrator without any network: the
# GitHub client and OSV calls are stubbed. Covers secret/security/bug rule
# firing, placeholder filtering, dependency-manifest parsing, repo-health
# heuristics, path skipping, and an end-to-end in-memory scan.
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

from backend.scan import rules as R
from backend.scan import scanner as S
from backend.github import gh as GH


class RuleEngineTestCase(unittest.TestCase):
    def test_flags_high_value_secrets(self):
        code = (
            'import os\n'
            'GITHUB_TOKEN = "ghp_AAAAAAAAAAAA1111BBBB2222CCCC3333DDDD"\n'
            'aws = "AKIAIOSFODNN7EXAMPLE"\n'
            'conn = "postgres://root:s3cret@db.example.com:5432/app"\n'
            '--- -----BEGIN RSA PRIVATE KEY----- ---\n'
        )
        findings = R.scan_text(code, "config.py", "python")
        ids = {f["id"] for f in findings}
        self.assertIn("secret.github_pat", ids)
        self.assertIn("secret.aws_access_key", ids)
        self.assertIn("secret.db_url_password", ids)
        self.assertIn("secret.private_key", ids)

    def test_flags_security_and_bug_smells(self):
        code = (
            'import os, hashlib\n'
            'x = eval(os.environ["X"])\n'
            'os.system("ls")\n'
            'hashlib.md5(b"x")\n'
        )
        findings = R.scan_text(code, "app.py", "python")
        ids = {f["id"] for f in findings}
        self.assertIn("security.eval", ids)
        self.assertIn("security.system_call", ids)
        self.assertIn("security.weak_hash", ids)

    def test_sql_concat_and_inner_html(self):
        py = R.scan_text(
            'conn.execute("SELECT * FROM t WHERE id = " + str(x))\n', "db.py", "python")
        self.assertIn("security.sql_concat", {f["id"] for f in py})
        js = R.scan_text('el.innerHTML = userInput\n', "app.js", "js")
        self.assertIn("security.insecure_html", {f["id"] for f in js})

    def test_placeholders_are_filtered(self):
        code = (
            "password = 'changeme'\n"
            "api_key = 'your-api-key-here'\n"
            "secret = os.environ.get('SECRET_KEY', 'default')\n"
        )
        findings = R.scan_text(code, "app.py", "python")
        ids = [f["id"] for f in findings]
        self.assertNotIn("secret.hardcoded_password", ids)
        self.assertNotIn("secret.hardcoded_key", ids)
        self.assertNotIn("practice.hardcoded_secret_key", ids)

    def test_hardcoded_password_with_prefix(self):
        findings = R.scan_text('admin_password = "ActualS3cret99!"\n', "cfg.py", "python")
        ids = {f["id"] for f in findings}
        self.assertIn("secret.hardcoded_password", ids)

    def test_line_numbers_and_file_are_reported(self):
        findings = R.scan_text('password = "0nlyRealValue!"\n', "cfg.py", "python")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["line"], 1)
        self.assertEqual(findings[0]["file"], "cfg.py")

    def test_repo_health_heuristics(self):
        findings = R.repo_health(["README.md", "LICENSE", ".github/workflows/ci.yml"])
        ids = {f["id"] for f in findings}
        self.assertNotIn("practice.no_readme", ids)
        self.assertNotIn("practice.no_license", ids)
        self.assertNotIn("practice.no_ci", ids)
        self.assertNotIn("practice.no_lockfile", ids)

    def test_skip_path_filters_vendored_and_binary(self):
        self.assertTrue(R._skip_path("node_modules/foo/index.js", 100))
        self.assertTrue(R._skip_path("vendor/jquery.min.js", 100))
        self.assertTrue(R._skip_path("docs/screen.png", 100))
        self.assertTrue(R._skip_path("big.bin", 3_000_000))
        self.assertTrue(R._skip_path(".github/gitleaks.toml", 100))
        self.assertTrue(R._skip_path(".env.example", 100))
        self.assertTrue(R._skip_path(".env.template", 100))
        self.assertFalse(R._skip_path(".env", 100))
        self.assertFalse(R._skip_path("src/app.js", 100))


class ManifestScanTestCase(unittest.TestCase):
    def test_package_json_parsed_and_osv_queried(self):
        manifests = {"package.json": json.dumps({"dependencies": {"lodash": "^4.17.11"}})}
        with mock.patch.object(R, "_osv_vulns", return_value=[{
            "id": "GHSA-1",
            "summary": "Prototype pollution",
            "database_specific": {"severity": "HIGH"},
        }]):
            findings = R.scan_manifests(manifests, osv_queries=True)
        vulns = [f for f in findings if f["id"] == "dependency.osv"]
        self.assertEqual(len(vulns), 1)
        self.assertEqual(vulns[0]["severity"], "high")
        self.assertEqual(vulns[0]["package"], "lodash")

    def test_unpinned_dependencies_flagged(self):
        manifests = {"package.json": json.dumps({"dependencies": {"foo": "latest"}})}
        with mock.patch.object(R, "_osv_vulns", return_value=[]):
            findings = R.scan_manifests(manifests, osv_queries=True)
        ids = {f["id"] for f in findings}
        self.assertIn("dependency.unpinned_npm", ids)

    def test_osv_failure_is_graceful(self):
        manifests = {"requirements.txt": "requests==2.31.0\n"}
        with mock.patch.object(R, "_osv_vulns", side_effect=RuntimeError("offline")):
            findings = R.scan_manifests(manifests, osv_queries=True)
        ids = {f["id"] for f in findings}
        self.assertIn("dependency.osv_unreachable", ids)

    def test_nested_manifests_are_detected(self):
        manifests = {
            "frontend/package.json": json.dumps({"dependencies": {"lodash": "^4.17.21"}}),
            "backend/requirements.txt": "requests==2.31.0\n",
        }
        with mock.patch.object(R, "_osv_vulns", return_value=[{
            "id": "GHSA-npm",
            "aliases": ["CVE-2023-5344"],
            "database_specific": {"severity": "MODERATE"},
        }]):
            findings = R.scan_manifests(manifests, osv_queries=True)
        hits = [(f["id"], f["file"], f["package"], f.get("advisory")) for f in findings]
        self.assertIn(("dependency.osv", "frontend/package.json", "lodash", "GHSA-npm"), hits)
        self.assertIn(("dependency.osv", "backend/requirements.txt", "requests", "GHSA-npm"), hits)


class ScannerTestCase(unittest.TestCase):
    def tearDown(self):
        S._state.clear()

    def test_full_scan_offline(self):
        rec = {"full_name": "demo/demoapp", "default_branch": "main", "private": False}
        tree_entries = [
            {"path": "app.py", "size": 300},
            {"path": "package.json", "size": 120},
            {"path": "README.md", "size": 50},
            {"path": "node_modules/foo/x.js", "size": 10},
            {"path": "logo.png", "size": 20},
        ]
        contents = {
            "app.py": "import os\nSECRET_KEY='hunter2'\nadmin_password = 'ActualS3cret99!'\neval(data)\n",
            "package.json": json.dumps({"dependencies": {"lodash": "*"}}),
            "README.md": "# demoapp\n",
        }

        def fake_fetch_content(token, full_name, path, branch):
            return contents.get(path, "")

        with mock.patch.object(S, "repo_tree", return_value=(tree_entries, False)), \
             mock.patch.object(S, "fetch_content", side_effect=fake_fetch_content), \
             mock.patch.object(R, "_osv_vulns", return_value=[]):
            report = S._scan_repo(rec, "tok")

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["full_name"], "demo/demoapp")
        self.assertTrue(report["files_scanned"] >= 3)
        ids = {f["id"] for f in report["findings"]}
        self.assertIn("security.eval", ids)
        self.assertIn("secret.hardcoded_password", ids)
        self.assertIn("dependency.unpinned_npm", ids)
        self.assertIn("practice.no_lockfile", ids)
        self.assertNotIn("practice.no_readme", ids)
        self.assertIn("dependency", report["summary"]["by_category"])

    def test_persist_and_read_roundtrip(self):
        rec = {"full_name": "demo/demoapp", "default_branch": "main", "private": False}
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(S, "SCAN_DIR", Path(td)):
                with mock.patch.object(
                        S, "_scan_repo",
                        return_value={"status": "completed", "summary": {"total": 0},
                                      "findings": []}):
                    S._persist("demo/demoapp", S._scan_repo(rec, "t"))
                report = S.read_report("demo/demoapp")
                self.assertIsNotNone(report)
                self.assertEqual(report["status"], "completed")

    def test_error_report_is_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(S, "SCAN_DIR", Path(td)):
                S._persist("o/e", S._error_report("o/e", "boom"))
                report = S.read_report("o/e")
                self.assertEqual(report["status"], "error")
                self.assertEqual(report["error"], "boom")

    def test_summary_exposes_flat_severity_keys(self):
        empty = S._empty_summary()
        for sev in ("critical", "high", "medium", "low", "info"):
            self.assertIn(sev, empty, f"_empty_summary must seed flat key {sev}")
            self.assertEqual(empty[sev], 0)
        rec = {"full_name": "demo/demoapp", "default_branch": "main", "private": False}
        tree_entries = [
            {"path": "app.py", "size": 300},
            {"path": "README.md", "size": 50},
        ]
        contents = {"app.py": "SECRET_KEY='hunter2'\nadmin_password = 'ActualS3cret99!'\n"}
        with mock.patch.object(S, "repo_tree", return_value=(tree_entries, False)), \
             mock.patch.object(S, "fetch_content", side_effect=lambda *a, **k: contents.get(a[2], "")), \
             mock.patch.object(R, "_osv_vulns", return_value=[]):
            report = S._scan_repo(rec, "tok")
        s = report["summary"]
        self.assertGreater(s["total"], 0)
        for sev in ("critical", "high", "medium", "low", "info"):
            self.assertEqual(s[sev], s["by_severity"][sev])

    def test_dashboard_payload_aggregates_correctly(self):
        from backend.github.api import _dashboard_payload
        repos = [
            {"full_name": "org/a", "language": "Python", "html_url": "https://g/1", "private": True, "fork": False, "archived": False, "default_branch": "main", "owner": {"login": "org"}},
            {"full_name": "org/b", "language": "TS", "html_url": "https://g/2", "private": False, "fork": False, "archived": False, "default_branch": "main", "owner": {"login": "org"}},
        ]
        summaries = {
            "org/a": {"status": "completed", "scanned_at": "2026-09-12T10:00:00Z", "files_scanned": 50,
                       "summary": {"total": 10, "by_severity": {"high": 3, "medium": 7},
                                   "by_category": {"bug": 4, "secret": 6}}},
            "org/b": {"status": "completed", "scanned_at": "2026-09-12T11:00:00Z", "files_scanned": 20,
                       "summary": {"total": 5, "by_severity": {"critical": 2, "high": 2, "low": 1},
                                   "by_category": {"vulnerability": 5}}},
            "org/uns": None,  # not scanned
        }
        with mock.patch("backend.github.gh.cached_github_repos", return_value=repos), \
             mock.patch("backend.github.api.gh.cached_github_repos", return_value=repos), \
             mock.patch("backend.scan.scanner.latest_summary", side_effect=lambda fn: summaries.get(fn)):
            payload = _dashboard_payload()
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["repos_total"], 2)
        self.assertEqual(payload["repos_scanned"], 2)
        self.assertEqual(payload["repos_with_findings"], 2)
        self.assertEqual(payload["findings_total"], 15)
        self.assertEqual(payload["critical_high_total"], 7)
        self.assertEqual(payload["dependency_vulns"], 5)
        self.assertEqual(payload["by_severity"]["high"], 5)
        self.assertEqual(payload["by_severity"]["critical"], 2)
        self.assertEqual(len(payload["riskiest"]), 2)
        self.assertEqual(payload["riskiest"][0]["full_name"], "org/b")  # critical > high
        self.assertEqual(len(payload["scan_timeline"]), 1)
        self.assertEqual(payload["scan_timeline"][0]["findings"], 15)


class GitHubClientTestCase(unittest.TestCase):
    def test_pagination_and_palette(self):
        pages = [
            [{"full_name": "a/one", "private": False, "default_branch": "main",
              "owner": {"login": "a"}}],
            [{"full_name": "b/two", "private": True, "default_branch": "main",
              "owner": {"login": "b"}}],
        ]
        calls = []

        class FakeResp:
            def __init__(self, items):
                self.status_code = 200
                self._items = items
                self.text = ""
                self.links = {"next": {"url": "x"}} if len(items) >= 100 else {}

            def json(self):
                return self._items

        class FakeHttp:
            def request(self, method, url, **kwargs):
                calls.append(url)
                idx = len(calls) - 1
                return FakeResp(pages[idx] if idx < len(pages) else [])

        with mock.patch.object(GH, "http_client", FakeHttp()):
            repos = GH.list_repos("token")
        self.assertEqual(len(repos), 1)
        self.assertTrue(repos[0]["owner"] == "a" and not repos[0]["private"])


if __name__ == "__main__":
    unittest.main()