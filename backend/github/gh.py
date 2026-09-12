# =============================================================================
# GitHub data access (server-side)
# =============================================================================
# Reads the GitHub Access Token from the admin settings store -- decrypted in
# memory, never sent to the browser. Used by the Repositories scanner so a
# saved token immediately makes the account's repositories available.
# =============================================================================

import logging
import time
from typing import Any, Dict, List, Optional

try:
    import requests as http_client
except ImportError:  # pragma: no cover - requests is a declared dependency
    http_client = None

from backend.admin.store import get_store

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REPO_SYNC_TTL = 5 * 60  # seconds before the repo list re-syncs against the API


class GitHubAPIError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def github_token_record() -> Optional[Dict[str, Any]]:
    """First enabled GitHub access token saved under Settings -> Integrations."""
    for rec in get_store().list_access_tokens():
        if rec.get("platform") == "github" and rec.get("enabled", True) and rec.get("token"):
            return rec
    return None


def _headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request(method: str, url: str, token: str, *, json=None, params=None, timeout: int = 20):
    if http_client is None:
        raise GitHubAPIError(503, "requests library unavailable")
    try:
        resp = http_client.request(
            method, url, headers=_headers(token), json=json, params=params, timeout=timeout)
    except Exception as exc:
        raise GitHubAPIError(0, f"GitHub request failed: {exc.__class__.__name__}")
    if resp.status_code in (200, 201):
        return resp
    if resp.status_code == 403 and "api_rate_limit" in resp.text:
        raise GitHubAPIError(403, "GitHub rate limit exceeded -- try the scan again later")
    if resp.status_code in (401, 403):
        raise GitHubAPIError(resp.status_code,
                             "GitHub token invalid, expired, or lacks repository access")
    if resp.status_code == 404:
        raise GitHubAPIError(404, "Repository not found or not visible to this token")
    raise GitHubAPIError(resp.status_code, f"GitHub HTTP {resp.status_code}")


def _normalize_repo(item: Dict[str, Any]) -> Dict[str, Any]:
    owner = (item.get("owner") or {}).get("login", "")
    return {
        "id": item.get("id"),
        "owner": owner,
        "name": item.get("name", ""),
        "full_name": item.get("full_name") or f"{owner}/{item.get('name', '')}",
        "private": bool(item.get("private")),
        "fork": bool(item.get("fork")),
        "archived": bool(item.get("archived")),
        "language": item.get("language"),
        "description": (item.get("description") or "").strip() or None,
        "html_url": item.get("html_url"),
        "default_branch": item.get("default_branch") or "main",
        "updated_at": item.get("updated_at"),
        "pushed_at": item.get("pushed_at"),
        "size_kb": item.get("size", 0),
    }


def list_repos(token: str, *, max_pages: int = 5) -> List[Dict[str, Any]]:
    """All repositories the token can see, most recently updated first."""
    repos: List[Dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        resp = _request(
            "GET", f"{GITHUB_API}/user/repos", token,
            params={"per_page": 100, "page": page, "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member"},
        )
        batch = resp.json() or []
        repos.extend(_normalize_repo(item) for item in batch)
        if len(batch) < 100 or not resp.links.get("next"):
            break
        page += 1
    return repos


def repo_tree(token: str, full_name: str, branch: str,
              timeout: int = 20) -> tuple:
    """Recursive git tree for a branch -> (blob entries, truncated)."""
    resp = _request(
        "GET", f"{GITHUB_API}/repos/{full_name}/git/trees/{branch}", token,
        params={"recursive": "1"}, timeout=timeout)
    payload = resp.json() or {}
    tree = payload.get("tree") or []
    entries = [
        {"path": (t.get("path") or ""), "size": t.get("size", 0)}
        for t in tree if t.get("type") == "blob" and t.get("path")
    ]
    return entries, bool(payload.get("truncated"))


def fetch_content(token: str, full_name: str, path: str, branch: str,
                  timeout: int = 20) -> str:
    """UTF-8 text content of one file via the contents API (base64)."""
    import base64
    resp = _request(
        "GET", f"{GITHUB_API}/repos/{full_name}/contents/{path}", token,
        params={"ref": branch}, timeout=timeout)
    payload = resp.json() or {}
    content = payload.get("content") or ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""


def cached_github_repos() -> List[Dict[str, Any]]:
    doc = get_store().get_doc()
    return list(doc.get("github_repos", []) or [])


def github_synced_at() -> float:
    return float(get_store().get_doc().get("github_synced_at", 0) or 0)


def store_github_repos(repos: List[Dict[str, Any]]) -> None:
    st = get_store()
    st._doc["github_repos"] = repos
    st._doc["github_synced_at"] = time.time()
    st.save()


def refresh_needed() -> bool:
    cached = cached_github_repos()
    if not cached:
        return True
    return (time.time() - github_synced_at()) > REPO_SYNC_TTL