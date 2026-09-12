# =============================================================================
# GitHub Repositories API blueprint
# =============================================================================
# Exposes the repositories visible to the saved GitHub token (split Public /
# Private by the client) plus the deterministic scanner:
#   GET/POST /api/v1/github/repos          -> list / force-refresh cached repos
#   GET/POST /api/v1/github/repos/<owner>/<name>/scan   -> report / start scan
# The token stays server-side (decrypted in memory only); nothing here depends
# on AI or agents -- scanning is fully rule-based.
# =============================================================================

import logging
import time
from typing import Any, Dict, Optional

from flask import Blueprint, request, jsonify

from backend.github import gh
from backend.github.gh import GitHubAPIError
from backend.scan import scanner
from backend.security import require_admin
from backend.activity import record_event

logger = logging.getLogger(__name__)

github_bp = Blueprint("github", __name__, url_prefix="/api/v1/github")


def init_github(app) -> None:
    app.register_blueprint(github_bp)


def _find_repo(full_name: str) -> Optional[Dict[str, Any]]:
    for repo in gh.cached_github_repos():
        if repo.get("full_name", "").lower() == full_name.lower():
            return repo
    return None


def _synced_payload() -> Dict[str, Any]:
    repos = gh.cached_github_repos()
    payload = {
        "configured": True,
        "synced_at": gh.github_synced_at(),
        "private": sum(1 for r in repos if r.get("private")),
        "public": sum(1 for r in repos if not r.get("private")),
        "total": len(repos),
        "repos": [],
    }
    for repo in repos:
        payload["repos"].append({
            **{k: repo.get(k) for k in (
                "id", "owner", "name", "full_name", "private", "fork", "archived",
                "language", "description", "html_url", "default_branch",
                "updated_at", "pushed_at", "size_kb")},
            "scan": scanner.latest_summary(repo.get("full_name", "")),
        })
    return payload


def _token_or_error():
    rec = gh.github_token_record()
    if rec is None:
        return None, (jsonify({
            "configured": False,
            "detail": "Connect a GitHub token under Settings -> Integrations "
                      "(platform: GitHub) to load repositories.",
            "repos": [], "private": 0, "public": 0, "total": 0,
        }), 200)
    return rec, None


def _dashboard_payload() -> Dict[str, Any]:
    """Aggregate scan stats across every cached repo for the dashboard cards."""
    repos = gh.cached_github_repos()
    by_severity: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    riskiest: list = []
    recent: list = []
    timeline: Dict[str, int] = {}          # date -> findings total
    scanned = 0
    with_findings = 0
    last_scan_at: Optional[str] = None

    for repo in repos:
        full = repo.get("full_name", "")
        summ = scanner.latest_summary(full)
        if not summ or summ.get("status") != "completed":
            continue
        scanned += 1
        s = summ.get("summary") or {}
        total = s.get("total", 0)
        if total > 0:
            with_findings += 1
        for sev, n in (s.get("by_severity") or {}).items():
            by_severity[sev] = by_severity.get(sev, 0) + n
        for cat, n in (s.get("by_category") or {}).items():
            by_category[cat] = by_category.get(cat, 0) + n

        scanned_at = summ.get("scanned_at") or ""
        if scanned_at > (last_scan_at or ""):
            last_scan_at = scanned_at
        date_key = scanned_at[:10] if scanned_at else None
        if date_key:
            timeline[date_key] = timeline.get(date_key, 0) + total

        riskiest.append({
            "full_name": full,
            "critical": s.get("by_severity", {}).get("critical", 0),
            "high": s.get("by_severity", {}).get("high", 0),
            "medium": s.get("by_severity", {}).get("medium", 0),
            "total": total,
            "files_scanned": summ.get("files_scanned", 0),
            "scanned_at": scanned_at,
            "language": repo.get("language"),
            "html_url": repo.get("html_url"),
        })
        recent.append({
            "full_name": full,
            "status": summ.get("status"),
            "files_scanned": summ.get("files_scanned"),
            "findings_total": total,
            "by_severity": s.get("by_severity", {}),
            "scanned_at": scanned_at,
        })

    riskiest.sort(key=lambda r: (r["critical"], r["high"], r["total"]), reverse=True)
    recent.sort(key=lambda r: r.get("scanned_at") or "", reverse=True)
    timeline_series = sorted(
        [{"date": d, "findings": n} for d, n in timeline.items()],
        key=lambda x: x["date"],
    )

    return {
        "configured": True,
        "repos_total": len(repos),
        "repos_scanned": scanned,
        "repos_with_findings": with_findings,
        "findings_total": sum(by_severity.values()),
        "critical_high_total": by_severity.get("critical", 0) + by_severity.get("high", 0),
        "dependency_vulns": by_category.get("vulnerability", 0),
        "by_severity": by_severity,
        "by_category": by_category,
        "last_scan_at": last_scan_at,
        "riskiest": riskiest[:20],
        "recent_scans": recent[:20],
        "scan_timeline": timeline_series,
    }


@github_bp.get("/repos")
@require_admin
def list_repos():
    rec, err = _token_or_error()
    if err:
        return err
    if gh.refresh_needed():
        try:
            gh.store_github_repos(gh.list_repos(rec.get("token", "")))
        except GitHubAPIError as exc:
            return jsonify({"configured": True, "error": exc.detail,
                            "code": exc.status, "repos": []}), 502
    return jsonify(_synced_payload())


@github_bp.get("/dashboard")
@require_admin
def github_dashboard():
    rec, err = _token_or_error()
    if err:
        return err
    if gh.refresh_needed():
        try:
            gh.store_github_repos(gh.list_repos(rec.get("token", "")))
        except GitHubAPIError:
            pass  # stale cache is fine for the dashboard aggregate
    return jsonify(_dashboard_payload())


@github_bp.post("/repos/refresh")
@require_admin
def refresh_repos():
    rec, err = _token_or_error()
    if err:
        return err
    try:
        gh.store_github_repos(gh.list_repos(rec.get("token", "")))
        record_event("github", "success", {"action": "repos_refresh"})
    except GitHubAPIError as exc:
        return jsonify({"configured": True, "error": exc.detail,
                        "code": exc.status, "repos": []}), 502
    return jsonify(_synced_payload())


@github_bp.post("/repos/<owner>/<name>/scan")
@require_admin
def start_scan(owner: str, name: str):
    full_name = f"{owner}/{name}"
    repo = _find_repo(full_name)
    if repo is None:
        return jsonify({"error": "repository not found in cached list; refresh first"}), 404
    rec, err = _token_or_error()
    if err:
        return err
    if not scanner.start_scan(repo, rec.get("token", "")):
        return jsonify({"scanning": True, "detail": "scan already running"}), 409
    record_event("github", "processing", {"action": "scan_start", "repo": full_name})
    return jsonify({"scanning": True, "started_at": time.time()}), 202


@github_bp.get("/repos/<owner>/<name>/scan")
@require_admin
def scan_status(owner: str, name: str):
    full_name = f"{owner}/{name}"
    status = scanner.scan_status(full_name)
    report = scanner.read_report(full_name)
    if report is None:
        return jsonify({**status, "report": None})
    return jsonify({**status, "report": report})