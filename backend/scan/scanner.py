# =============================================================================
# Repository scanner orchestrator
# =============================================================================
# Fetches a repository's file tree + contents via the GitHub API (using the
# saved token), runs the deterministic rule engine, checks pinned dependencies
# against OSV, and persists a portable JSON report under ~/.gitfix/scans/.
# Scans run on a background thread so the API stays responsive; a scan is only
# ever active once per repository, with a small concurrency cap across repos.
# =============================================================================

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.github.gh import repo_tree, fetch_content, GitHubAPIError
from backend.scan import rules as R

logger = logging.getLogger(__name__)

SCAN_DIR = Path.home() / ".gitfix" / "scans"
SCANNER_VERSION = "1.0.0"

MAX_FILES = 350           # files fetched per scan (bounds GitHub usage)
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 900 * 1024
MAX_CONCURRENT_SCANS = 3

_lock = threading.Lock()
_semaphore = threading.Semaphore(MAX_CONCURRENT_SCANS)
_state: Dict[str, Dict[str, Any]] = {}  # full_name -> scan state


def _report_path(full_name: str) -> Path:
    return SCAN_DIR / f"{full_name.replace('/', '__')}.json"


def scan_status(full_name: str) -> Dict[str, Any]:
    """{scanning, started_at} for live progress in the UI."""
    with _lock:
        st = _state.get(full_name)
    if st and st.get("state") == "running":
        return {"scanning": True, "started_at": st.get("started")}
    return {"scanning": False, "started_at": None}


def read_report(full_name: str, *, with_findings: bool = True) -> Optional[Dict[str, Any]]:
    path = _report_path(full_name)
    if not path.exists():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("Failed reading scan %s: %s", path, exc)
        return None
    if not with_findings and isinstance(report.get("findings"), list):
        report = dict(report)
        report["findings"] = report["findings"][:0]
        report["findings_truncated"] = True
    return report


def latest_summary(full_name: str) -> Optional[Dict[str, Any]]:
    report = read_report(full_name, with_findings=False)
    if not report:
        return None
    return {
        "scanned_at": report.get("scanned_at"),
        "status": report.get("status"),
        "summary": report.get("summary"),
        "files_scanned": report.get("files_scanned"),
    }


def start_scan(repo: Dict[str, Any], token: str) -> bool:
    """Start a background scan for a repo. Returns False if already running."""
    full_name = repo.get("full_name") or f"{repo.get('owner')}/{repo.get('name')}"
    with _lock:
        st = _state.get(full_name, {})
        if st.get("state") == "running":
            return False
        _state[full_name] = {
            "state": "running",
            "started": time.time(),
            "owner": repo.get("owner"),
            "name": repo.get("name"),
        }
    threading.Thread(target=_run_scan, args=(full_name, repo, token), daemon=True).start()
    return True


def _run_scan(full_name: str, repo: Dict[str, Any], token: str) -> None:
    try:
        with _semaphore:
            report = _scan_repo(repo, token)
        report["status"] = "completed"
        report["error"] = None
    except GitHubAPIError as exc:
        report = _error_report(full_name, exc.detail, exc.status)
    except Exception as exc:  # never let a scan crash a worker
        logger.exception("Scan failed for %s", full_name)
        report = _error_report(full_name, f"{exc.__class__.__name__}: {exc}")
    finally:
        _persist(full_name, report)
        with _lock:
            _state[full_name]["state"] = "idle"
            _state[full_name]["finished"] = time.time()


def _error_report(full_name: str, message: str, code: int = 0) -> Dict[str, Any]:
    return {
        "full_name": full_name,
        "scanner": SCANNER_VERSION,
        "scanned_at": _now(),
        "duration": 0,
        "status": "error",
        "error": message,
        "error_code": code,
        "files_scanned": 0,
        "truncated": False,
        "summary": _empty_summary(),
        "findings": [],
    }


def _empty_summary() -> Dict[str, Any]:
    summary = {
        "total": 0,
        "by_severity": {s: 0 for s in R.SEVERITIES},
        "by_category": {c: 0 for c in R.CATEGORIES},
    }
    for sev in R.SEVERITIES:
        summary[sev] = 0
    return summary


def _now() -> str:
    return datetime.now(timezone.utc).isoformat() + "Z"


# ── core scan ────────────────────────────────────────────────────────────────

def _scan_repo(repo: Dict[str, Any], token: str) -> Dict[str, Any]:
    start = time.time()
    full_name = repo.get("full_name") or f"{repo.get('owner')}/{repo.get('name')}"
    branch = repo.get("default_branch") or "main"

    entries, truncated = repo_tree(token, full_name, branch)
    entries = [e for e in entries if not R._skip_path(e.get("path", ""), e.get("size", 0))][:MAX_FILES]

    findings: List[Dict[str, Any]] = []
    manifests: Dict[str, str] = {}
    scanned_paths = [e["path"] for e in entries]
    files_scanned = 0
    total_bytes = 0
    seen: set = set()

    for ent in entries:
        path = ent.get("path", "")
        if not path:
            continue
        if total_bytes >= MAX_TOTAL_BYTES:
            break
        if ent.get("size", 0) > MAX_FILE_BYTES:
            continue
        text = fetch_content(token, full_name, path, branch)
        if not text:
            continue
        total_bytes += len(text)
        files_scanned += 1
        lang = R._lang_of(path)
        for f in R.scan_text(text, path, lang):
            key = (f["id"], f["file"], f["line"])
            if key in seen:
                continue
            seen.add(key)
            findings.append(f)
        if R._basename(path) in R.MANIFESTS:
            manifests[path] = text

    findings += R.scan_manifests(manifests)
    findings += R.repo_health(scanned_paths)

    # Truncate pathological outputs but keep severity/category totals honest.
    findings.sort(key=lambda f: (
        R.SEVERITIES.index(f["severity"]) if f["severity"] in R.SEVERITIES else 99,
        f["category"], f["file"]))
    kept = findings[:500]

    summary = _empty_summary()
    for f in kept:
        summary["total"] += 1
        summary["by_severity"][f["severity"]] = summary["by_severity"].get(f["severity"], 0) + 1
        summary["by_category"][f["category"]] = summary["by_category"].get(f["category"], 0) + 1
    for sev, n in summary["by_severity"].items():
        summary[sev] = n

    report = {
        "full_name": full_name,
        "owner": repo.get("owner"),
        "name": repo.get("name"),
        "scanner": SCANNER_VERSION,
        "ref": branch,
        "scanned_at": _now(),
        "duration": round(time.time() - start, 2),
        "status": "completed",
        "error": None,
        "files_scanned": files_scanned,
        "truncated": bool(truncated or len(findings) > len(kept)),
        "summary": summary,
        "findings": kept,
    }
    return report


def _persist(full_name: str, report: Dict[str, Any]) -> None:
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    target = _report_path(full_name)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, target)