# =============================================================================
# Git-Fix Bitbucket Integration
# =============================================================================
# Bitbucket Cloud API integration for Git-Fix code review platform
# =============================================================================

from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from typing import AsyncGenerator
import logging

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


class BitbucketIntegration(PlatformIntegration):
    """Bitbucket Cloud API integration."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        base_url: str = "https://api.bitbucket.org",
        api_version: str = "2.0",
        timeout: float = 30.0,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            webhook_secret=webhook_secret,
            base_url=base_url.rstrip("/"),
            api_version=api_version,
            timeout=timeout,
        )
        self.username = username
        self.app_password = app_password
        self._bitbucket_url = f"{base_url.rstrip('/')}/{api_version}"

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.BITBUCKET

    @property
    def api_base_url(self) -> str:
        return self._bitbucket_url

    async def authenticate(self) -> str:
        """Authenticate with Bitbucket using OAuth2 or basic auth."""
        if self.username and self.app_password:
            # Use basic auth with app password
            import base64
            credentials = f"{self.username}:{self.app_password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return f"Basic {encoded}"
        
        if not self._client:
            await self._get_client()
        
        # OAuth2 token exchange
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/site/oauth2/access_token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            return token_data["access_token"]

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate Bitbucket webhook signature."""
        # Bitbucket uses X-Hub-Signature header with HMAC-SHA256
        return verify_hmac_signature(payload, signature, self.webhook_secret, "sha256")

    async def parse_webhook(self, payload: Dict[str, Any]) -> PlatformWebhookPayload:
        """Parse Bitbucket webhook payload."""
        event_key = payload.get("eventKey", "")
        
        # Map Bitbucket events to our event types
        event_mapping = {
            "pullrequest:created": WebhookEventType.PULL_REQUEST_OPENED,
            "pullrequest:updated": WebhookEventType.PULL_REQUEST_UPDATED,
            "pullrequest:fulfilled": WebhookEventType.PULL_REQUEST_MERGED,
            "pullrequest:rejected": WebhookEventType.PULL_REQUEST_CLOSED,
            "repo:push": WebhookEventType.PUSH,
            "pullrequest:comment_created": WebhookEventType.COMMENT_CREATED,
            "pullrequest:comment_updated": WebhookEventType.COMMENT_UPDATED,
        }
        
        event_type = event_mapping.get(event_key, WebhookEventType.PUSH)
        
        # Extract repository
        repo_data = payload.get("repository", {})
        repository = self._parse_repository(repo_data)
        
        # Extract pull request
        pr_data = payload.get("pullrequest", {})
        pull_request = None
        if pr_data:
            pull_request = self._parse_pull_request(pr_data, payload.get("repository", {}))
        
        # Extract comment
        comment_data = payload.get("comment", {})
        comment = None
        if comment_data:
            comment = self._parse_comment(comment_data)
        
        # Extract actor
        actor_data = payload.get("actor", {})
        sender = self._parse_user(actor_data)
        
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
            id=str(data.get("uuid", data.get("account_id", ""))),
            username=data.get("username", data.get("nickname", "")),
            email=data.get("email"),
            name=data.get("display_name", data.get("name")),
            avatar_url=data.get("links", {}).get("avatar", {}).get("href"),
            is_bot=False,
        )

    def _parse_repository(self, data: Dict[str, Any]) -> PlatformRepository:
        return PlatformRepository(
            id=str(data.get("uuid", data.get("uuid", ""))),
            name=data.get("name", ""),
            full_name=data.get("full_name", data.get("full_name", "")),
            description=data.get("description"),
            private=data.get("is_private", False),
            default_branch=data.get("mainbranch", {}).get("name", "main"),
            html_url=data.get("links", {}).get("html", {}).get("href"),
            clone_url=None,  # Would need to construct from links
            ssh_url=None,
            language=data.get("language"),
            stars_count=0,  # Bitbucket doesn't have stars
            forks_count=data.get("forks_count", 0),
            open_prs_count=0,  # Would need separate API call
            created_at=self._parse_datetime(data.get("created_on")),
            updated_at=self._parse_datetime(data.get("updated_on")),
        )

    def _parse_pull_request(
        self,
        data: Dict[str, Any],
        repo_data: Dict[str, Any],
    ) -> PlatformPullRequest:
        author_data = data.get("author", {})
        source_repo = data.get("source", {}).get("repository", {})
        dest_repo = data.get("destination", {}).get("repository", {})
        
        return PlatformPullRequest(
            id=str(data.get("id", "")),
            number=data.get("id", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            state=data.get("state", "OPEN").lower(),
            source_branch=data.get("source", {}).get("branch", {}).get("name", ""),
            target_branch=data.get("destination", {}).get("branch", {}).get("name", ""),
            source_sha=data.get("source", {}).get("commit", {}).get("hash", ""),
            target_sha=data.get("destination", {}).get("commit", {}).get("hash", ""),
            author=self._parse_user(author_data),
            source_repo=self._parse_repository(source_repo) if source_repo else None,
            target_repo=self._parse_repository(dest_repo) if dest_repo else None,
            additions=0,  # Would need separate API call
            deletions=0,
            changed_files=0,
            mergeable=None,
            mergeable_state=None,
            created_at=self._parse_datetime(data.get("created_on")),
            updated_at=self._parse_datetime(data.get("updated_on")),
            closed_at=self._parse_datetime(data.get("closed_on")),
            merged_at=None,
        )

    def _parse_comment(self, data: Dict[str, Any]) -> PlatformComment:
        return PlatformComment(
            id=str(data.get("id", "")),
            body=data.get("content", {}).get("raw", ""),
            author=self._parse_user(data.get("author", {})),
            created_at=self._parse_datetime(data.get("created_on")),
            updated_at=self._parse_datetime(data.get("updated_on")),
        )

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            # Bitbucket uses ISO format with Z or +00:00
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
        """Make authenticated request to Bitbucket API."""
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
        # repo_id can be "workspace/repo_slug"
        response = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}")
        return self._parse_repository(response.json())

    async def list_repositories(
        self,
        user_id: Optional[str] = None,
        organization: Optional[str] = None,
        visibility: Optional[str] = None,
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformRepository, None]:
        params = {"pagelen": min(per_page, 100)}
        
        url = "/repositories"
        if organization:
            url = f"/repositories/{organization}"
        
        while True:
            response = await self._make_request("GET", "/repositories", params={"pagelen": min(per_page, 100)})
            data = response.json()
            
            for repo in data.get("values", []):
                yield self._parse_repository(repo)
            
            next_url = data.get("next")
            if not next_url:
                break
            
            # For pagination, we need to extract page from next URL
            # Simplified for now
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
                f"/repositories/{quote(repo_id, safe='')}/src/{quote(ref, safe='')}/{quote(file_path, safe='')}",
            )
            return response.text
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
            f"/repositories/{quote(repo_id, safe='')}/src/{quote(ref, safe='')}",
        )
        data = response.json()
        return data.get("values", [])

    # Pull Request operations
    async def get_pull_request(
        self,
        repo_id: str,
        pr_number: int,
    ) -> PlatformPullRequest:
        response = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}")
        repo_data = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}")
        repo_data = repo_data.json()
        return self._parse_pull_request(response.json(), repo_data)

    async def list_pull_requests(
        self,
        repo_id: str,
        state: str = "OPEN",
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformPullRequest, None]:
        params = {"state": state, "pagelen": min(per_page, 100)}
        
        while True:
            response = await self._make_request(
                "GET",
                f"/repositories/{quote(repo_id, safe='')}/pullrequests",
                params=params,
            )
            data = response.json()
            prs = data.get("values", [])
            if not prs:
                break
            
            repo_data = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}")
            repo_data = repo_data.json()
            
            for pr in prs:
                yield self._parse_pull_request(pr, repo_data)
            
            next_url = data.get("next")
            if not next_url:
                break

    async def get_pull_request_diff(
        self,
        repo_id: str,
        pr_number: int,
    ) -> str:
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/diff",
        )
        return response.text

    async def get_pull_request_files(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/diffstat",
        )
        data = response.json()
        return data.get("values", [])

    async def get_pull_request_commits(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/commits",
        )
        data = response.json()
        return data.get("values", [])

    # Review operations
    async def create_review(
        self,
        repo_id: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
        event: str = "COMMENT",
    ) -> Dict[str, Any]:
        # Bitbucket doesn't have a review API, post comments instead
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
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/comments",
            json_data={
                "content": {"raw": body},
                "inline": {
                    "from": line,
                    "to": line,
                    "path": file_path,
                } if line > 0 else None,
            },
        )
        return response.json()

    async def create_comment(
        self,
        repo_id: str,
        pr_number: int,
        body: str,
    ) -> Dict[str, Any]:
        response = await self._make_request(
            "POST",
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/comments",
            json_data={"content": {"raw": body}},
        )
        return response.json()

    async def get_pull_request_comments(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[PlatformComment]:
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/comments",
        )
        data = response.json()
        return [self._parse_comment(c) for c in data.get("values", [])]

    # Webhook management
    async def create_webhook(
        self,
        repo_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_mapping = {
            "pull_request_opened": "repo:push",
            "pull_request_updated": "pullrequest:updated",
            "pull_request_closed": "pullrequest:rejected",
            "pull_request_merged": "pullrequest:fulfilled",
            "push": "repo:push",
            "comment_created": "pullrequest:comment_created",
        }
        
        bitbucket_events = [{"event": event_mapping.get(e, e)} for e in events]
        
        response = await self._make_request(
            "POST",
            f"/repositories/{quote(repo_id, safe='')}/hooks",
            json_data={
                "description": "Git-Fix Webhook",
                "url": url,
                "active": True,
                "events": [e["event"] for e in bitbucket_events],
            },
        )
        return response.json()

    async def list_webhooks(self, repo_id: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}/hooks")
        data = response.json()
        return data.get("values", [])

    async def delete_webhook(self, repo_id: str, webhook_id: str) -> bool:
        response = await self._make_request("DELETE", f"/repositories/{quote(repo_id, safe='')}/hooks/{webhook_id}")
        return response.status_code == 204

    # Repository operations
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True,
        organization: Optional[str] = None,
    ) -> PlatformRepository:
        workspace = organization or self.username
        response = await self._make_request(
            "POST",
            f"/repositories/{workspace}",
            json_data={
                "name": name,
                "description": description,
                "is_private": private,
            },
        )
        return self._parse_repository(response.json())

    async def update_repository(
        self,
        repo_id: str,
        **kwargs,
    ) -> PlatformRepository:
        response = await self._make_request(
            "PUT",
            f"/repositories/{quote(repo_id, safe='')}",
            json_data=kwargs,
        )
        return self._parse_repository(response.json())

    async def delete_repository(self, repo_id: str) -> bool:
        response = await self._make_request("DELETE", f"/repositories/{quote(repo_id, safe='')}")
        return response.status_code == 204

    # Branch operations
    async def get_branches(
        self,
        repo_id: str,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        params = {"pagelen": min(per_page, 100)}
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/refs/branches",
            params=params,
        )
        data = response.json()
        return data.get("values", [])

    async def get_branch(self, repo_id: str, branch_name: str) -> Dict[str, Any]:
        response = await self._make_request(
            "GET",
            f"/repositories/{quote(repo_id, safe='')}/refs/branches/{quote(branch_name, safe='')}",
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
            f"/repositories/{quote(repo_id, safe='')}/refs/branches",
            json_data={
                "name": branch_name,
                "target": {"hash": from_branch},
            },
        )
        return response.json()

    async def delete_branch(self, repo_id: str, branch_name: str) -> bool:
        response = await self._make_request(
            "DELETE",
            f"/repositories/{quote(repo_id, safe='')}/refs/branches/{quote(branch_name, safe='')}",
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
            "pending": "INPROGRESS",
            "success": "SUCCESSFUL",
            "error": "FAILED",
            "failure": "FAILED",
        }
        
        response = await self._make_request(
            "POST",
            f"/repositories/{quote(repo_id, safe='')}/commit/{sha}/statuses/build",
            json_data={
                "state": state_map.get(state, "INPROGRESS"),
                "url": target_url,
                "description": description or context,
                "key": context,
                "name": context,
            },
        )
        return response.json()

    async def get_statuses(self, repo_id: str, sha: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", f"/repositories/{quote(repo_id, safe='')}/commit/{sha}/statuses")
        data = response.json()
        return data.get("values", [])

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
            "PUT",
            f"/repositories/{quote(repo_id, safe='')}/src/{quote(file_path, safe='')}",
            params={"message": message, "branch": branch},
            content=content.encode(),
            headers={"Content-Type": "application/octet-stream"},
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
        return await self.create_file(repo_id, file_path, content, message, branch)

    async def delete_file(
        self,
        repo_id: str,
        file_path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        # Bitbucket doesn't have a direct delete file API
        # Need to create a commit that removes the file
        return {"message": "File deletion requires commit"}

    # Search
    async def search_code(
        self,
        query: str,
        repo_id: Optional[str] = None,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        params = {"search_query": query, "pagelen": per_page}
        response = await self._make_request("GET", "/snippets", params=params)
        return response.json().get("values", [])

    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
    ) -> List[PlatformRepository]:
        params = {"q": query, "pagelen": per_page}
        response = await self._make_request("GET", "/repositories", params=params)
        data = response.json()
        return [self._parse_repository(p) for p in data.get("values", [])]

    # User/Organization
    async def get_user(self, user_id: Optional[str] = None) -> PlatformUser:
        endpoint = f"/users/{quote(user_id, safe='')}" if user_id else "/user"
        response = await self._make_request("GET", endpoint)
        return self._parse_user(response.json())

    async def get_organization(self, org_name: str) -> Dict[str, Any]:
        response = await self._make_request("GET", f"/workspaces/{quote(org_name, safe='')}")
        return response.json()


# Register the integration
PlatformRegistry.register(PlatformType.BITBUCKET)(BitbucketIntegration)