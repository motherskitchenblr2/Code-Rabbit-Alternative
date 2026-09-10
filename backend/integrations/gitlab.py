# =============================================================================
# Git-Fix GitLab Integration
# =============================================================================
# GitLab API integration for Git-Fix code review platform
# =============================================================================

from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from typing import AsyncGenerator

import httpx
import hashlib
import hmac
import logging
from urllib.parse import quote

from ..integrations.base import (
    PlatformIntegration,
    PlatformType,
    PlatformUser,
    PlatformRepository,
    PlatformPullRequest,
    PlatformComment,
    PlatformWebhookPayload,
    WebhookEventType,
    ReviewComment,
    ReviewResult,
    PlatformRegistry,
    WebhookEventType,
)

logger = logging.getLogger(__name__)


class GitLabIntegration(PlatformIntegration):
    """GitLab API integration."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        base_url: str = "https://gitlab.com",
        api_version: str = "v4",
        timeout: float = 30.0,
        personal_access_token: Optional[str] = None,
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            webhook_secret=webhook_secret,
            base_url=base_url.rstrip("/"),
            api_version=api_version,
            timeout=timeout,
        )
        self.personal_access_token = personal_access_token
        self._gitlab_url = f"{base_url.rstrip('/')}/api/{api_version}"

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.GITLAB

    @property
    def api_base_url(self) -> str:
        return self._gitlab_url

    async def authenticate(self) -> str:
        """Authenticate with GitLab using OAuth2 or personal access token."""
        if self.personal_access_token:
            return self.personal_access_token
        
        if not self._client:
            await self._get_client()
        
        # OAuth2 token exchange
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        response = await self._client.post(
            f"{self.base_url}/oauth/token",
            data=data,
        )
        response.raise_for_status()
        token_data = response.json()
        
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        return token_data["access_token"]

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate GitLab webhook signature."""
        # GitLab uses X-Gitlab-Token header for webhook validation
        # The signature is the token itself
        return hmac.compare_digest(signature, self.webhook_secret)

    async def parse_webhook(self, payload: Dict[str, Any]) -> PlatformWebhookPayload:
        """Parse GitLab webhook payload."""
        event_type = payload.get("object_kind", "")
        
        # Map GitLab events to our event types
        event_mapping = {
            "merge_request": WebhookEventType.PULL_REQUEST_OPENED,
            "push": WebhookEventType.PUSH,
            "note": WebhookEventType.COMMENT_CREATED,
        }
        
        event_type = event_mapping.get(event_type, WebhookEventType.PUSH)
        
        # Extract repository
        repo_data = payload.get("project", {})
        repository = self._parse_repository(repo_data)
        
        # Extract pull request (merge request)
        pr_data = payload.get("merge_request", {})
        pull_request = None
        if pr_data:
            pull_request = self._parse_pull_request(pr_data, payload.get("project", {}))
        
        # Extract comment
        comment_data = payload.get("note", {})
        comment = None
        if comment_data:
            comment = self._parse_comment(comment_data)
        
        # Extract sender
        sender_data = payload.get("user", {})
        sender = self._parse_user(sender_data)
        
        return PlatformWebhookPayload(
            event_type=WebhookEventType(event_type),
            repository=repository,
            pull_request=pull_request,
            comment=comment,
            sender=sender,
            raw_payload=payload,
        )

    def _parse_user(self, data: Dict[str, Any]) -> Optional[PlatformUser]:
        if not data:
            return None
        return PlatformUser(
            id=str(data.get("id", "")),
            username=data.get("username", ""),
            email=data.get("email"),
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            is_bot=data.get("is_bot", False),
        )

    def _parse_repository(self, data: Dict[str, Any]) -> PlatformRepository:
        return PlatformRepository(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            full_name=data.get("path_with_namespace", ""),
            description=data.get("description"),
            private=data.get("visibility") == "private",
            default_branch=data.get("default_branch", "main"),
            html_url=data.get("web_url"),
            clone_url=data.get("http_url_to_repo"),
            ssh_url=data.get("ssh_url_to_repo"),
            language=None,  # GitLab doesn't provide this in project object
            stars_count=data.get("star_count", 0),
            forks_count=data.get("forks_count", 0),
            open_prs_count=data.get("open_issues_count", 0),
            created_at=self._parse_datetime(data.get("created_at")),
            updated_at=self._parse_datetime(data.get("last_activity_at")),
        )

    def _parse_pull_request(
        self,
        data: Dict[str, Any],
        project_data: Dict[str, Any],
    ) -> PlatformPullRequest:
        author_data = data.get("author", {})
        source_project = data.get("source_project", {})
        target_project = data.get("target_project", {})
        
        return PlatformPullRequest(
            id=str(data.get("id", "")),
            number=data.get("iid", 0),
            title=data.get("title", ""),
            description=data.get("description"),
            state=data.get("state", "opened"),
            source_branch=data.get("source_branch", ""),
            target_branch=data.get("target_branch", ""),
            source_sha=data.get("sha", ""),
            target_sha=data.get("target_branch_sha", ""),
            author=self._parse_user(author_data),
            source_repo=self._parse_repository(source_project) if source_project else None,
            target_repo=self._parse_repository(target_project) if target_project else None,
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changes_count", 0),
            mergeable=data.get("mergeable"),
            mergeable_state=data.get("merge_status"),
            created_at=self._parse_datetime(data.get("created_at")),
            updated_at=self._parse_datetime(data.get("updated_at")),
            closed_at=self._parse_datetime(data.get("closed_at")),
            merged_at=self._parse_datetime(data.get("merged_at")),
        )

    def _parse_comment(self, data: Dict[str, Any]) -> PlatformComment:
        return PlatformComment(
            id=str(data.get("id", "")),
            body=data.get("body", ""),
            author=self._parse_user(data.get("author", {})),
            created_at=self._parse_datetime(data.get("created_at")),
            updated_at=self._parse_datetime(data.get("updated_at")),
        )

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> httpx.Response:
        """Make authenticated request to GitLab API."""
        client = await self._get_client()
        headers = await self._get_auth_header()
        headers["Content-Type"] = "application/json"
        
        url = f"{self.api_base_url}{endpoint}"
        
        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
        )
        response.raise_for_status()
        return response

    # Repository operations
    async def get_repository(self, repo_id: str) -> PlatformRepository:
        response = await self._make_request("GET", f"/projects/{quote(repo_id, safe='')}")
        return self._parse_repository(response.json())

    async def list_repositories(
        self,
        user_id: Optional[str] = None,
        organization: Optional[str] = None,
        visibility: Optional[str] = None,
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformRepository, None]:
        params = {
            "per_page": min(per_page, 100),
            "page": 1,
        }
        if visibility:
            params["visibility"] = visibility
        if organization:
            params["namespace"] = organization
        
        while True:
            response = await self._make_request("GET", "/projects", params=params)
            projects = response.json()
            if not projects:
                break
            
            for project in projects:
                yield self._parse_repository(project)
            
            params["page"] += 1
            if len(projects) < params["per_page"]:
                break

    async def get_repository_file(
        self,
        repo_id: str,
        file_path: str,
        ref: str = "main",
    ) -> Optional[str]:
        try:
            response = await self._make_request(
                "GET",
                f"/projects/{quote(repo_id, safe='')}/repository/files/{quote(file_path, safe='')}",
                params={"ref": ref},
            )
            data = response.json()
            import base64
            return base64.b64decode(data["content"]).decode("utf-8")
        except Exception:
            return None

    async def get_repository_tree(
        self,
        repo_id: str,
        ref: str = "main",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/repository/tree",
            params={"ref": ref, "recursive": recursive, "per_page": 100},
        )
        return response.json()

    # Pull Request operations
    async def get_pull_request(
        self,
        repo_id: str,
        pr_number: int,
    ) -> PlatformPullRequest:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}",
        )
        project_data = await self._make_request("GET", f"/projects/{quote(repo_id, safe='')}")
        project_data = project_data.json()
        return self._parse_pull_request(response.json(), project_data)

    async def list_pull_requests(
        self,
        repo_id: str,
        state: str = "opened",
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformPullRequest, None]:
        params = {
            "state": state,
            "per_page": min(per_page, 100),
            "page": 1,
        }
        
        while True:
            response = await self._make_request(
                "GET",
                f"/projects/{quote(repo_id, safe='')}/merge_requests",
                params=params,
            )
            mrs = response.json()
            if not mrs:
                break
            
            project_data = await self._make_request("GET", f"/projects/{quote(repo_id, safe='')}")
            project_data = project_data.json()
            
            for mr in mrs:
                yield self._parse_pull_request(mr, project_data)
            
            params["page"] += 1
            if len(mrs) < params["per_page"]:
                break

    async def get_pull_request_diff(
        self,
        repo_id: str,
        pr_number: int,
    ) -> str:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/diffs",
        )
        diffs = response.json()
        return "\n".join([d.get("diff", "") for d in diffs])

    async def get_pull_request_files(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/changes",
        )
        data = response.json()
        return data.get("changes", [])

    async def get_pull_request_commits(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/commits",
        )
        return response.json()

    # Review operations
    async def create_review(
        self,
        repo_id: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
        event: str = "COMMENT",
    ) -> Dict[str, Any]:
        # GitLab doesn't have a direct review API like GitHub
        # We create individual comments instead
        results = []
        for comment in comments:
            result = await self.create_review_comment(
                repo_id=repo_id,
                pr_number=comments[0].get("pull_request_id", 0),
                file_path=comment.file_path,
                line=comment.line,
                body=f"**{comment.severity.upper()}**: {comment.message}\n\n```suggestion\n{comment.suggested_fix}\n```" if comment.suggested_fix else comment.message,
                commit_id=comment.commit_id,
            )
            results.append(result)
        
        return {"comments_created": len(results), "results": results}

    async def create_review_comment(
        self,
        repo_id: str,
        pr_number: int,
        file_path: str,
        line: int,
        body: str,
        commit_id: Optional[str] = None,
        side: str = "RIGHT",
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/discussions",
            json_data={
                "body": body,
                "position": {
                    "base_sha": "",  # Would need to get from MR
                    "start_sha": "",
                    "head_sha": "",
                    "position_type": "text",
                    "new_path": file_path,
                    "new_line": line,
                } if commit_id else None,
            },
        )
        return response.json()

    async def create_review(
        self,
        repo_id: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
        event: str = "COMMENT",
    ) -> Dict[str, Any]:
        # Post summary as a comment
        await self.create_comment(
            repo_id=repo_id,
            pr_number=pr_number,
            body=f"## Git-Fix Review Summary\n\n{summary}",
        )
        
        # Post individual comments
        results = []
        for comment in comments:
            if comment.confidence >= 0.85:
                result = await self.create_review_comment(
                    repo_id=repo_id,
                    pr_number=pr_number,
                    file_path=comment.file_path,
                    line=comment.line,
                    body=f"**{comment.severity.upper()}**: {comment.message}\n\n```suggestion\n{comment.suggested_fix}\n```" if comment.suggested_fix else comment.message,
                    commit_id=comment.commit_id,
                )
                results.append(result)
        
        return {"comments_created": len(results)}

    async def create_review_comment(
        self,
        repo_id: str,
        pr_number: int,
        file_path: str,
        line: int,
        body: str,
        commit_id: Optional[str] = None,
        side: str = "RIGHT",
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/discussions",
            json_data={
                "body": body,
                "position": {
                    "base_sha": "",  # Would need MR base SHA
                    "start_sha": "",
                    "head_sha": "",
                    "position_type": "text",
                    "new_path": file_path,
                    "new_line": line,
                },
            },
        )
        return response.json()

    async def update_review_comment(
        self,
        repo_id: str,
        comment_id: str,
        body: str,
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "PUT",
            f"/projects/{quote(repo_id, safe='')}/notes/{comment_id}",
            json_data={"body": body},
        )
        return response.json()

    async def delete_review_comment(
        self,
        repo_id: str,
        comment_id: str,
    ) -> bool:
        response = await self._make_request("DELETE", f"/projects/{quote(repo_id, safe='')}/notes/{comment_id}")
        return response.status_code == 204

    async def create_comment(
        self,
        repo_id: str,
        pr_number: int,
        body: str,
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/notes",
            json_data={"body": body},
        )
        return response.json()

    async def get_pull_request_comments(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[PlatformComment]:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/merge_requests/{pr_number}/notes",
        )
        notes = response.json()
        return [self._parse_comment(note) for note in notes]

    # Webhook management
    async def create_webhook(
        self,
        repo_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_mapping = {
            "pull_request_opened": "merge_request_events",
            "pull_request_updated": "merge_request_events",
            "pull_request_closed": "merge_request_events",
            "pull_request_merged": "merge_request_events",
            "push": "push_events",
            "comment_created": "note_events",
            "comment_updated": "note_events",
        }
        
        gitlab_events = [event_mapping.get(e, e) for e in events]
        
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/hooks",
            json_data={
                "url": url,
                "push_events": "push_events" in gitlab_events,
                "merge_requests_events": "merge_request_events" in gitlab_events,
                "note_events": "note_events" in gitlab_events,
                "enable_ssl_verification": True,
                "token": self.webhook_secret,
            },
        )
        return response.json()

    async def list_webhooks(self, repo_id: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", f"/projects/{quote(repo_id, safe='')}/hooks")
        return response.json()

    async def delete_webhook(self, repo_id: str, webhook_id: str) -> bool:
        response = await self._make_request("DELETE", f"/projects/{quote(repo_id, safe='')}/hooks/{webhook_id}")
        return response.status_code == 204

    # Repository operations
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True,
        organization: Optional[str] = None,
    ) -> PlatformRepository:
        data = {
            "name": name,
            "description": description,
            "visibility": "private" if private else "public",
        }
        if organization:
            data["namespace_id"] = organization
        
        response = await self._make_request("POST", "/projects", json_data=data)
        return self._parse_repository(response.json())

    async def update_repository(
        self,
        repo_id: str,
        **kwargs,
    ) -> PlatformRepository:
        response = await self._make_request(
            "PUT",
            f"/projects/{quote(repo_id, safe='')}",
            json_data=kwargs,
        )
        return self._parse_repository(response.json())

    async def delete_repository(self, repo_id: str) -> bool:
        response = await self._make_request("DELETE", f"/projects/{quote(repo_id, safe='')}")
        return response.status_code == 204

    # Branch operations
    async def get_branches(
        self,
        repo_id: str,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        params = {"per_page": min(per_page, 100), "page": 1}
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/repository/branches",
            params=params,
        )
        return response.json()

    async def get_branch(self, repo_id: str, branch_name: str) -> Dict[str, Any]:
        response = await self._make_request(
            "GET",
            f"/projects/{quote(repo_id, safe='')}/repository/branches/{quote(branch_name, safe='')}",
        )
        return response.json()

    async def create_branch(
        self,
        repo_id: str,
        branch_name: str,
        from_branch: str,
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/repository/branches",
            json_data={
                "branch": branch_name,
                "ref": from_branch,
            },
        )
        return response.json()

    async def delete_branch(self, repo_id: str, branch_name: str) -> bool:
        response = await self._make_request(
            "DELETE",
            f"/projects/{quote(repo_id, safe='')}/repository/branches/{quote(branch_name, safe='')}",
        )
        return response.status_code == 204

    # Status checks
    async def create_status(
        self,
        repo_id: str,
        sha: str,
        state: str,
        target_url: Optional[str] = None,
        description: Optional[str] = None,
        context: str = "Git-Fix",
    ) -> Dict[str, Any]:
        state_map = {
            "pending": "pending",
            "success": "success",
            "error": "failed",
            "failure": "failed",
        }
        
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/statuses/{sha}",
            json_data={
                "state": state_map.get(state, "pending"),
                "target_url": target_url,
                "description": description,
                "context": context,
            },
        )
        return response.json()

    async def get_statuses(self, repo_id: str, sha: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", f"/projects/{quote(repo_id, safe='')}/repository/commits/{sha}/statuses")
        return response.json()

    # File operations
    async def create_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        message: str,
        branch: str,
    ) -> Dict[str, Any]:
        import base64
        response = await self._make_request(
            "POST",
            f"/projects/{quote(repo_id, safe='')}/repository/files/{quote(file_path, safe='')}",
            json_data={
                "branch": branch,
                "content": base64.b64encode(content.encode()).decode(),
                "commit_message": message,
            },
        )
        return response.json()

    async def update_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        message: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        import base64
        response = await self._make_request(
            "PUT",
            f"/projects/{quote(repo_id, safe='')}/repository/files/{quote(file_path, safe='')}",
            json_data={
                "branch": branch,
                "content": base64.b64encode(content.encode()).decode(),
                "commit_message": message,
                "last_commit_sha": sha,
            },
        )
        return response.json()

    async def delete_file(
        self,
        repo_id: str,
        file_path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "DELETE",
            f"/projects/{quote(repo_id, safe='')}/repository/files/{quote(file_path, safe='')}",
            json_data={
                "branch": branch,
                "commit_message": message,
                "last_commit_sha": sha,
            },
        )
        return response.json()

    # Search
    async def search_code(
        self,
        query: str,
        repo_id: Optional[str] = None,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        params = {"search": query, "per_page": per_page}
        if repo_id:
            params["project_id"] = repo_id
        
        response = await self._make_request("GET", "/search/code", params=params)
        return response.json()

    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
    ) -> List[PlatformRepository]:
        params = {"search": query, "per_page": per_page}
        response = await self._make_request("GET", "/projects", params=params)
        return [self._parse_repository(p) for p in response.json()]

    # User/Organization
    async def get_user(self, user_id: Optional[str] = None) -> PlatformUser:
        endpoint = f"/users/{quote(user_id, safe='')}" if user_id else "/user"
        response = await self._make_request("GET", endpoint)
        return self._parse_user(response.json())

    async def get_organization(self, org_name: str) -> Dict[str, Any]:
        response = await self._make_request("GET", f"/groups/{quote(org_name, safe='')}")
        return response.json()


# Register the integration
PlatformRegistry.register(PlatformType.GITLAB)(GitLabIntegration)

# Import missing modules
from datetime import timedelta
import base64