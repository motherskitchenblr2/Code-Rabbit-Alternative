# =============================================================================
# Git-Fix Azure DevOps Integration
# =============================================================================
# Azure DevOps REST API integration for Git-Fix code review platform
# =============================================================================

from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from typing import AsyncGenerator
import logging
import base64

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


class AzureDevOpsIntegration(PlatformIntegration):
    """Azure DevOps REST API integration."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        base_url: str = "https://dev.azure.com",
        api_version: str = "7.1",
        timeout: float = 30.0,
        organization: Optional[str] = None,
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
        self.organization = organization
        self.personal_access_token = personal_access_token
        self._ado_url = f"{base_url.rstrip('/')}/{organization}" if organization else base_url

    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.AZURE_DEVOPS

    @property
    def api_base_url(self) -> str:
        if self.organization:
            return f"{self._ado_url}/_apis"
        return f"{self.base_url}/{self.api_version}"

    async def authenticate(self) -> str:
        """Authenticate with Azure DevOps using PAT or OAuth2."""
        if self.personal_access_token:
            # Use PAT with basic auth
            import base64
            credentials = f":{self.personal_access_token}"
            encoded = base64.b64encode(f":{self.personal_access_token}".encode()).decode()
            return f"Basic {encoded}"
        
        if not self._client:
            await self._get_client()
        
        # OAuth2 token exchange
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "499b84ac-1321-427f-aa17-267ca6975798/.default",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://login.microsoftonline.com/{self.client_id}/oauth2/v2.0/token",
                data=data,
            )
            response.raise_for_status()
            token_data = response.json()
            
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            return token_data["access_token"]

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate Azure DevOps webhook signature."""
        # Azure DevOps uses SHA256 HMAC
        return verify_hmac_signature(payload, signature, self.webhook_secret, "sha256")

    async def parse_webhook(self, payload: Dict[str, Any]) -> PlatformWebhookPayload:
        """Parse Azure DevOps webhook payload."""
        event_type_str = payload.get("eventType", "")
        
        # Map Azure DevOps events to our event types
        event_mapping = {
            "git.pullrequest.created": WebhookEventType.PULL_REQUEST_OPENED,
            "git.pullrequest.updated": WebhookEventType.PULL_REQUEST_UPDATED,
            "git.pullrequest.mergecompleted": WebhookEventType.PULL_REQUEST_MERGED,
            "git.pullrequest.closed": WebhookEventType.PULL_REQUEST_CLOSED,
            "git.push": WebhookEventType.PUSH,
            "git.pullrequest.comment.created": WebhookEventType.COMMENT_CREATED,
            "git.pullrequest.comment.updated": WebhookEventType.COMMENT_UPDATED,
        }
        
        event_type = event_mapping.get(event_type_str, WebhookEventType.PUSH)
        
        # Extract resource
        resource = payload.get("resource", {})
        resource_containers = payload.get("resourceContainers", {})
        
        # Extract repository
        repo_data = resource_containers.get("repository", {})
        repository = self._parse_repository(resource_containers.get("repository", {}))
        
        # Extract pull request
        pr_data = resource.get("pullRequestId") or resource.get("pullRequest", {})
        pull_request = None
        if isinstance(pr_data, dict) and "pullRequestId" in pr_data:
            pull_request = self._parse_pull_request(pr_data, resource.get("repository", {}))
        elif "pullRequest" in resource:
            pull_request = self._parse_pull_request(resource["pullRequest"], resource.get("repository", {}))
        
        # Extract comment
        comment_data = resource.get("comment", {})
        comment = None
        if comment_data:
            comment = self._parse_comment(comment_data)
        
        # Extract identity
        identity_data = resource.get("createdBy", resource.get("resourceCreatedBy", {}))
        sender = self._parse_user(identity_data)
        
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
            id=data.get("id", data.get("uniqueName", "")),
            username=data.get("uniqueName", data.get("displayName", "")),
            email=data.get("email"),
            name=data.get("displayName", data.get("name")),
            avatar_url=data.get("imageUrl", data.get("avatarUrl")),
            is_bot=data.get("isContainer", False),
        )

    def _parse_repository(self, data: Dict[str, Any]) -> PlatformRepository:
        return PlatformRepository(
            id=data.get("id", ""),
            name=data.get("name", ""),
            full_name=f"{data.get('project', {}).get('name', '')}/{data.get('name', '')}",
            description=data.get("description"),
            private=data.get("isPrivate", False),
            default_branch=data.get("defaultBranch", "main").replace("refs/heads/", ""),
            html_url=data.get("remoteUrl"),
            clone_url=data.get("remoteUrl"),
            ssh_url=data.get("sshUrl"),
            language=None,
            stars_count=0,
            forks_count=0,
            open_prs_count=0,
            created_at=self._parse_datetime(data.get("createdDate")),
            updated_at=self._parse_datetime(data.get("lastUpdateTime")),
        )

    def _parse_pull_request(
        self,
        data: Dict[str, Any],
        repo_data: Dict[str, Any],
    ) -> PlatformPullRequest:
        author_data = data.get("createdBy", {})
        source_ref = data.get("sourceRefName", "").replace("refs/heads/", "")
        target_ref = data.get("targetRefName", "").replace("refs/heads/", "")
        
        return PlatformPullRequest(
            id=str(data.get("pullRequestId", "")),
            number=data.get("pullRequestId", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            state=data.get("status", "active").lower(),
            source_branch=data.get("sourceRefName", "").replace("refs/heads/", ""),
            target_branch=data.get("targetRefName", "").replace("refs/heads/", ""),
            source_sha=data.get("lastMergeSourceCommit", {}).get("commitId", ""),
            target_sha=data.get("lastMergeTargetCommit", {}).get("commitId", ""),
            author=self._parse_user(data.get("createdBy", {})),
            source_repo=None,
            target_repo=None,
            additions=0,
            deletions=0,
            changed_files=0,
            mergeable=None,
            mergeable_state=data.get("status", "active"),
            created_at=self._parse_datetime(data.get("creationDate")),
            updated_at=self._parse_datetime(data.get("lastUpdatedDate")),
            closed_at=self._parse_datetime(data.get("closedDate")),
            merged_at=self._parse_datetime(data.get("completedDate")),
        )

    def _parse_comment(self, data: Dict[str, Any]) -> PlatformComment:
        return PlatformComment(
            id=str(data.get("id", "")),
            body=data.get("content", ""),
            author=self._parse_user(data.get("author", {})),
            created_at=self._parse_datetime(data.get("publishedDate")),
            updated_at=self._parse_datetime(data.get("lastUpdatedDate")),
        )

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            # Azure DevOps uses ISO format
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
        """Make authenticated request to Azure DevOps REST API."""
        client = await self._get_client()
        headers = await self._get_auth_header()
        headers["Content-Type"] = "application/json"
        
        # Azure DevOps API URL format
        if self.organization:
            base = f"{self._ado_url}/_apis"
        else:
            base = self.base_url
        
        url = f"{base}{endpoint}"
        if "api-version" not in (params or {}):
            if params is None:
                params = {}
            params["api-version"] = "7.1"
        
        response = await self._client.request(
            method=method,
            url=f"{base}{endpoint}",
            params=params,
            json=json_data,
            headers=headers,
        )
        response.raise_for_status()
        return response

    # Repository operations
    async def get_repository(self, repo_id: str) -> PlatformRepository:
        # repo_id can be "project/repo" or just repo ID
        if "/" in repo_id:
            project, repo = repo_id.split("/", 1)
            endpoint = f"/git/repositories/{quote(repo, safe='')}"
            params = {"project": repo_id.split("/")[0]}
        else:
            endpoint = f"/git/repositories/{quote(repo_id, safe='')}"
            params = {}
        
        response = await self._make_request("GET", f"/git/repositories/{quote(repo_id, safe='')}", params={"project": self.organization})
        return self._parse_repository(response.json())

    async def list_repositories(
        self,
        user_id: Optional[str] = None,
        organization: Optional[str] = None,
        visibility: Optional[str] = None,
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformRepository, None]:
        params = {"$top": min(per_page, 100)}
        
        if organization:
            project = organization
        elif self.organization:
            project = self.organization
        else:
            # List all projects first
            projects_resp = await self._make_request("GET", "/projects", params={"$top": 100})
            projects = projects_resp.json().get("value", [])
            for project in projects:
                project_name = project["name"]
                async for repo in self.list_repositories(organization=project["name"]):
                    yield repo
            return
        
        continuation_token = None
        while True:
            params_copy = params.copy()
            if continuation_token:
                params_copy["continuationToken"] = continuation_token
            
            response = await self._make_request(
                "GET",
                f"/git/repositories",
                params={**params, "project": self.organization or ""},
            )
            data = response.json()
            
            for repo in data.get("value", []):
                yield self._parse_repository(repo)
            
            continuation_token = data.get("continuationToken")
            if not continuation_token:
                break

    async def get_repository_file(
        self,
        repo_id: str,
        file_path: str,
        ref: str = "main",
    ) -> Optional[str]:
        try:
            params = {"versionDescriptor.version": ref, "path": file_path}
            response = await self._make_request(
                "GET",
                f"/git/repositories/{quote(repo_id, safe='')}/items",
                params={"path": file_path, "versionDescriptor.version": ref, "includeContent": "true"},
            )
            data = response.json()
            if isinstance(data, list) and data:
                return data[0].get("content", "")
            elif isinstance(data, dict):
                return data.get("content", "")
            return None
        except Exception:
            return None

    async def get_repository_tree(
        self,
        repo_id: str,
        ref: str = "main",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        params = {"versionDescriptor.version": ref, "recursionLevel": "full" if recursive else "oneLevel"}
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/items",
            params=params,
        )
        data = response.json()
        return data.get("value", [])

    # Pull Request operations
    async def get_pull_request(
        self,
        repo_id: str,
        pr_number: int,
    ) -> PlatformPullRequest:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}",
        )
        return self._parse_pull_request(response.json(), {})

    async def list_pull_requests(
        self,
        repo_id: str,
        state: str = "active",
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformPullRequest, None]:
        params = {"status": state, "$top": min(per_page, 100)}
        
        while True:
            response = await self._make_request(
                "GET",
                f"/git/repositories/{quote(repo_id, safe='')}/pullrequests",
                params=params,
            )
            data = response.json()
            prs = data.get("value", [])
            if not prs:
                break
            
            for pr in prs:
                yield self._parse_pull_request(pr, {})
            
            continuation_token = data.get("continuationToken")
            if not continuation_token:
                break

    async def get_pull_request_diff(
        self,
        repo_id: str,
        pr_number: int,
    ) -> str:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/iterations/1/files",
        )
        # Would need to construct diff from file changes
        return ""

    async def get_pull_request_files(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/iterations/1/files",
        )
        data = response.json()
        return data.get("value", [])

    async def get_pull_request_commits(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/commits",
        )
        data = response.json()
        return data.get("value", [])

    # Review operations
    async def create_review(
        self,
        repo_id: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
        event: str = "COMMENT",
    ) -> Dict[str, Any]:
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
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/threads",
            json_data={
                "comments": [{
                    "content": body,
                    "commentType": "text",
                }],
                "threadContext": {
                    "filePath": file_path,
                    "rightFileStart": {"line": line, "offset": 1},
                    "rightFileEnd": {"line": line, "offset": 1},
                },
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
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/threads",
            json_data={
                "comments": [{
                    "content": body,
                    "commentType": "text",
                }],
            },
        )
        return response.json()

    async def get_pull_request_comments(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[PlatformComment]:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/pullrequests/{pr_number}/threads",
        )
        data = response.json()
        threads = data.get("value", [])
        comments = []
        for thread in threads:
            for comment in thread.get("comments", []):
                comments.append(self._parse_comment(comment))
        return comments

    # Webhook management
    async def create_webhook(
        self,
        repo_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Azure DevOps uses service hooks
        event_mapping = {
            "pull_request_opened": "git.pullrequest.created",
            "pull_request_updated": "git.pullrequest.updated",
            "pull_request_merged": "git.pullrequest.mergecompleted",
            "pull_request_closed": "git.pullrequest.closed",
            "push": "git.push",
            "comment_created": "git.pullrequest.comment.created",
        }
        
        azdo_events = [{"eventType": event_mapping.get(e, e)} for e in events]
        
        response = await self._make_request(
            "POST",
            f"/servicehooks/subscriptions",
            json_data={
                "publisherId": "tfs",
                "eventType": "git.pullrequest.created",  # Would need multiple subscriptions
                "consumerId": "webHooks",
                "consumerActionId": "httpRequest",
                "consumerInputs": {
                    "url": url,
                    "httpHeaders": "Content-Type: application/json",
                    "resourceDetailsToSend": "all",
                    "messagesToSend": "none",
                    "detailedMessagesToSend": "true",
                },
                "publisherInputs": {
                    "repositoryId": repo_id,
                    "pullRequestId": "0",
                    "branch": "",
                    "branchPattern": "",
                },
            },
        )
        return response.json()

    async def list_webhooks(self, repo_id: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", "/servicehooks/subscriptions")
        data = response.json()
        return data.get("value", [])

    async def delete_webhook(self, repo_id: str, webhook_id: str) -> bool:
        response = await self._make_request("DELETE", f"/servicehooks/subscriptions/{webhook_id}")
        return response.status_code == 204

    # Repository operations
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True,
        organization: Optional[str] = None,
    ) -> PlatformRepository:
        project = organization or self.organization
        response = await self._make_request(
            "POST",
            f"/git/repositories",
            json_data={
                "name": name,
                "project": {"name": organization} if organization else None,
            },
            params={"project": self.organization},
        )
        return self._parse_repository(response.json())

    async def update_repository(
        self,
        repo_id: str,
        **kwargs,
    ) -> PlatformRepository:
        response = await self._make_request(
            "PATCH",
            f"/git/repositories/{quote(repo_id, safe='')}",
            json_data=kwargs,
        )
        return self._parse_repository(response.json())

    async def delete_repository(self, repo_id: str) -> bool:
        response = await self._make_request("DELETE", f"/git/repositories/{quote(repo_id, safe='')}")
        return response.status_code == 204

    # Branch operations
    async def get_branches(
        self,
        repo_id: str,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        params = {"$top": min(per_page, 100)}
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/refs",
            params={"filter": "heads/", "$top": per_page},
        )
        data = response.json()
        return data.get("value", [])

    async def get_branch(self, repo_id: str, branch_name: str) -> Dict[str, Any]:
        response = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/refs",
            params={"filter": f"heads/{branch_name}"},
        )
        data = response.json()
        return data.get("value", [{}])[0] if data.get("value") else {}

    async def create_branch(
        self,
        repo_id: str,
        branch_name: str,
        from_branch: str,
    ) -> Dict[str, Any]:
        # Get the source branch commit
        source_branch = await self._make_request(
            "GET",
            f"/git/repositories/{quote(repo_id, safe='')}/refs",
            params={"filter": f"heads/{from_branch}"},
        )
        source_data = source_branch.json()
        source_ref = source_data.get("value", [{}])[0] if source_data.get("value") else {}
        old_object_id = source_ref.get("objectId", "")
        
        response = await self._make_request(
            "POST",
            f"/git/repositories/{quote(repo_id, safe='')}/refs",
            json_data={
                "name": f"refs/heads/{branch_name}",
                "oldObjectId": "0000000000000000000000000000000000000000",
                "newObjectId": old_object_id,
            },
        )
        return response.json()

    async def delete_branch(self, repo_id: str, branch_name: str) -> bool:
        response = await self._make_request(
            "DELETE",
            f"/git/repositories/{quote(repo_id, safe='')}/refs",
            params={"name": f"refs/heads/{branch_name}"},
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
            "success": "succeeded",
            "error": "failed",
            "failure": "failed",
        }
        
        response = await self._make_request(
            "POST",
            f"/git/repositories/{quote(repo_id, safe='')}/commits/{sha}/statuses",
            json_data={
                "state": state_map.get(state, "pending"),
                "description": description,
                "targetUrl": target_url,
                "context": {"name": context, "genre": "continuous-integration"},
            },
        )
        return response.json()

    async def get_statuses(self, repo_id: str, sha: str) -> List[Dict[str, Any]]:
        response = await self._make_request("GET", f"/git/repositories/{quote(repo_id, safe='')}/commits/{sha}/statuses")
        data = response.json()
        return data.get("value", [])

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
            f"/git/repositories/{quote(repo_id, safe='')}/pushes",
            json_data={
                "refUpdates": [{
                    "name": f"refs/heads/{branch}",
                    "oldObjectId": "0000000000000000000000000000000000000000",
                }],
                "commits": [{
                    "comment": message,
                    "changes": [{
                        "changeType": "add",
                        "item": {"path": f"/{file_path}"},
                        "newContent": {
                            "content": base64.b64encode(content.encode()).decode(),
                            "contentType": "base64encoded",
                        },
                    }],
                }],
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
            "POST",
            f"/git/repositories/{quote(repo_id, safe='')}/pushes",
            json_data={
                "refUpdates": [{
                    "name": f"refs/heads/{branch}",
                    "oldObjectId": sha,
                }],
                "commits": [{
                    "comment": message,
                    "changes": [{
                        "changeType": "edit",
                        "item": {"path": f"/{file_path}"},
                        "newContent": {
                            "content": base64.b64encode(content.encode()).decode(),
                            "contentType": "base64encoded",
                        },
                    }],
                }],
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
            "POST",
            f"/git/repositories/{quote(repo_id, safe='')}/pushes",
            json_data={
                "refUpdates": [{
                    "name": f"refs/heads/{branch}",
                    "oldObjectId": sha,
                }],
                "commits": [{
                    "comment": message,
                    "changes": [{
                        "changeType": "delete",
                        "item": {"path": f"/{file_path}"},
                    }],
                }],
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
        params = {"searchText": query, "$top": per_page}
        if repo_id:
            params["repositoryId"] = repo_id
        
        response = await self._make_request("GET", "/search/code", params=params)
        data = response.json()
        return data.get("value", [])

    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
    ) -> List[PlatformRepository]:
        params = {"searchText": query, "$top": per_page}
        response = await self._make_request("GET", "/git/repositories", params=params)
        data = response.json()
        return [self._parse_repository(p) for p in data.get("value", [])]

    # User/Organization
    async def get_user(self, user_id: Optional[str] = None) -> PlatformUser:
        endpoint = f"/profiles/{quote(user_id, safe='')}" if user_id else "/profile"
        response = await self._make_request("GET", f"/profile/{user_id}" if user_id else "/profile/me")
        return self._parse_user(response.json())

    async def get_organization(self, org_name: str) -> Dict[str, Any]:
        response = await self._make_request("GET", f"/organizations/{quote(org_name, safe='')}")
        return response.json()


# Register the integration
PlatformRegistry.register(PlatformType.AZURE_DEVOPS)(AzureDevOpsIntegration)