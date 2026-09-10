# =============================================================================
# Git-Fix Multi-Platform Integration Base Classes
# =============================================================================
# Abstract base classes for Git platform integrations (GitHub, GitLab, Bitbucket, Azure DevOps)
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
from enum import Enum
import httpx
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"


class WebhookEventType(Enum):
    PULL_REQUEST_OPENED = "pull_request_opened"
    PULL_REQUEST_UPDATED = "pull_request_updated"
    PULL_REQUEST_CLOSED = "pull_request_closed"
    PULL_REQUEST_MERGED = "pull_request_merged"
    PUSH = "push"
    COMMENT_CREATED = "comment_created"
    COMMENT_UPDATED = "comment_updated"


@dataclass
class PlatformUser:
    id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_bot: bool = False


@dataclass
class PlatformRepository:
    id: str
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool = False
    default_branch: str = "main"
    html_url: Optional[str] = None
    clone_url: Optional[str] = None
    ssh_url: Optional[str] = None
    language: Optional[str] = None
    stars_count: int = 0
    forks_count: int = 0
    open_prs_count: int = 0
    default_branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PlatformPullRequest:
    id: str
    number: int
    title: str
    description: Optional[str] = None
    state: str = "open"  # open, closed, merged, draft
    source_branch: str = ""
    target_branch: str = ""
    source_sha: str = ""
    target_sha: str = ""
    author: Optional[PlatformUser] = None
    source_repo: Optional[PlatformRepository] = None
    target_repo: Optional[PlatformRepository] = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    mergeable: Optional[bool] = None
    mergeable_state: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None


@dataclass
class PlatformComment:
    id: str
    body: str
    author: Optional[PlatformUser] = None
    pull_request_id: Optional[str] = None
    commit_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_system: bool = False


@dataclass
class PlatformWebhookPayload:
    event_type: WebhookEventType
    repository: PlatformRepository
    pull_request: Optional[PlatformPullRequest] = None
    comment: Optional[PlatformComment] = None
    sender: Optional[PlatformUser] = None
    installation_id: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewComment:
    file_path: str
    line: int
    message: str
    severity: str = "info"  # critical, high, medium, low, info
    category: str = "style"  # security, logic, style, test, performance
    suggested_fix: Optional[str] = None
    confidence: float = 0.0
    commit_id: Optional[str] = None


@dataclass
class ReviewResult:
    pull_request_id: str
    summary: str
    findings: List[ReviewComment]
    overall_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


class PlatformIntegration(ABC):
    """Abstract base class for Git platform integrations."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        base_url: Optional[str] = None,
        api_version: str = "v1",
        timeout: float = 30.0,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_secret = webhook_secret
        self.base_url = base_url
        self.api_version = api_version
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    @abstractmethod
    def platform_type(self) -> PlatformType:
        """Return the platform type."""
        pass

    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """Return the API base URL."""
        pass

    @abstractmethod
    async def authenticate(self) -> str:
        """Authenticate and return access token."""
        pass

    @abstractmethod
    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate webhook signature."""
        pass

    @abstractmethod
    async def parse_webhook(self, payload: Dict[str, Any]) -> PlatformWebhookPayload:
        """Parse webhook payload into standardized format."""
        pass

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "Git-Fix/1.0",
                    "Accept": "application/json",
                }
            )
        return self._client

    async def _get_auth_header(self) -> Dict[str, str]:
        """Get authorization header with valid token."""
        if self._access_token is None or (
            self._token_expires_at and datetime.utcnow() >= self._token_expires_at
        ):
            self._access_token = await self.authenticate()
        
        return {"Authorization": f"Bearer {self._access_token}"}

    # Repository operations
    @abstractmethod
    async def get_repository(self, repo_id: str) -> PlatformRepository:
        """Get repository by ID."""
        pass

    @abstractmethod
    async def list_repositories(
        self,
        user_id: Optional[str] = None,
        organization: Optional[str] = None,
        visibility: Optional[str] = None,
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformRepository, None]:
        """List repositories."""
        pass

    @abstractmethod
    async def get_repository_file(
        self,
        repo_id: str,
        file_path: str,
        ref: str = "main",
    ) -> Optional[str]:
        """Get file content from repository."""
        pass

    @abstractmethod
    async def get_repository_tree(
        self,
        repo_id: str,
        ref: str = "main",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get repository file tree."""
        pass

    # Pull Request operations
    @abstractmethod
    async def get_pull_request(
        self,
        repo_id: str,
        pr_number: int,
    ) -> PlatformPullRequest:
        """Get pull request by number."""
        pass

    @abstractmethod
    async def list_pull_requests(
        self,
        repo_id: str,
        state: str = "open",
        per_page: int = 100,
    ) -> AsyncGenerator[PlatformPullRequest, None]:
        """List pull requests."""
        pass

    @abstractmethod
    async def get_pull_request_diff(
        self,
        repo_id: str,
        pr_number: int,
    ) -> str:
        """Get pull request diff."""
        pass

    @abstractmethod
    async def get_pull_request_files(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        """Get pull request files."""
        pass

    @abstractmethod
    async def get_pull_request_commits(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        """Get pull request commits."""
        pass

    # Review operations
    @abstractmethod
    async def create_review(
        self,
        repo_id: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
        event: str = "COMMENT",  # COMMENT, APPROVE, REQUEST_CHANGES
    ) -> Dict[str, Any]:
        """Create a review on pull request."""
        pass

    @abstractmethod
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
        """Create a review comment on specific line."""
        pass

    @abstractmethod
    async def update_review_comment(
        self,
        repo_id: str,
        comment_id: str,
        body: str,
    ) -> Dict[str, Any]:
        """Update a review comment."""
        pass

    @abstractmethod
    async def delete_review_comment(
        self,
        repo_id: str,
        comment_id: str,
    ) -> bool:
        """Delete a review comment."""
        pass

    # Comment operations
    @abstractmethod
    async def create_comment(
        self,
        repo_id: str,
        pr_number: int,
        body: str,
    ) -> Dict[str, Any]:
        """Create a general comment on PR."""
        pass

    @abstractmethod
    async def get_pull_request_comments(
        self,
        repo_id: str,
        pr_number: int,
    ) -> List[PlatformComment]:
        """Get all comments on a PR."""
        pass

    # Webhook management
    @abstractmethod
    async def create_webhook(
        self,
        repo_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a webhook."""
        pass

    @abstractmethod
    async def list_webhooks(self, repo_id: str) -> List[Dict[str, Any]]:
        """List webhooks for repository."""
        pass

    @abstractmethod
    async def delete_webhook(self, repo_id: str, webhook_id: str) -> bool:
        """Delete a webhook."""
        pass

    # Repository management
    @abstractmethod
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True,
        organization: Optional[str] = None,
    ) -> PlatformRepository:
        """Create a new repository."""
        pass

    @abstractmethod
    async def update_repository(
        self,
        repo_id: str,
        **kwargs,
    ) -> PlatformRepository:
        """Update repository settings."""
        pass

    @abstractmethod
    async def delete_repository(self, repo_id: str) -> bool:
        """Delete a repository."""
        pass

    # Branch operations
    @abstractmethod
    async def get_branches(
        self,
        repo_id: str,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """List branches."""
        pass

    @abstractmethod
    async def get_branch(self, repo_id: str, branch_name: str) -> Dict[str, Any]:
        """Get branch details."""
        pass

    @abstractmethod
    async def create_branch(
        self,
        repo_id: str,
        branch_name: str,
        from_branch: str,
    ) -> Dict[str, Any]:
        """Create a new branch."""
        pass

    @abstractmethod
    async def delete_branch(self, repo_id: str, branch_name: str) -> bool:
        """Delete a branch."""
        pass

    # Status checks
    @abstractmethod
    async def create_status(
        self,
        repo_id: str,
        sha: str,
        state: str,  # pending, success, error, failure
        target_url: Optional[str] = None,
        description: Optional[str] = None,
        context: str = "Git-Fix",
    ) -> Dict[str, Any]:
        """Create a commit status."""
        pass

    @abstractmethod
    async def get_statuses(
        self,
        repo_id: str,
        sha: str,
    ) -> List[Dict[str, Any]]:
        """Get commit statuses."""
        pass

    # File operations
    @abstractmethod
    async def create_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        message: str,
        branch: str,
    ) -> Dict[str, Any]:
        """Create a file."""
        pass

    @abstractmethod
    async def update_file(
        self,
        repo_id: str,
        file_path: str,
        content: str,
        message: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        """Update a file."""
        pass

    @abstractmethod
    async def delete_file(
        self,
        repo_id: str,
        file_path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        """Delete a file."""
        pass

    # Search
    @abstractmethod
    async def search_code(
        self,
        query: str,
        repo_id: Optional[str] = None,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search code."""
        pass

    @abstractmethod
    async def search_repositories(
        self,
        query: str,
        per_page: int = 30,
    ) -> List[PlatformRepository]:
        """Search repositories."""
        pass

    # User/Organization
    @abstractmethod
    async def get_user(self, user_id: Optional[str] = None) -> PlatformUser:
        """Get user info."""
        pass

    @abstractmethod
    async def get_organization(self, org_name: str) -> Dict[str, Any]:
        """Get organization info."""
        pass

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class PlatformRegistry:
    """Registry for platform integrations."""
    
    _integrations: Dict[PlatformType, type] = {}
    
    @classmethod
    def register(cls, platform_type: PlatformType):
        def decorator(cls_impl: type):
            cls._integrations[platform_type] = cls_impl
            return cls_impl
        return decorator
    
    @classmethod
    def get(cls, platform_type: PlatformType) -> Optional[type]:
        return cls._integrations.get(platform_type)
    
    @classmethod
    def create(
        cls,
        platform_type: PlatformType,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        **kwargs,
    ) -> PlatformIntegration:
        integration_class = cls.get(platform_type)
        if not integration_class:
            raise ValueError(f"No integration registered for platform: {platform_type}")
        return integration_class(
            client_id=client_id,
            client_secret=client_secret,
            webhook_secret=webhook_secret,
            **kwargs,
        )
    
    @classmethod
    def list_platforms(cls) -> List[PlatformType]:
        return list(cls._integrations.keys())


# Utility functions
def verify_hmac_signature(payload: bytes, signature: str, secret: str, algorithm: str = "sha256") -> bool:
    """Verify HMAC signature."""
    if not signature:
        return False
    
    expected_algorithm = f"{algorithm}="
    if not signature.startswith(expected_algorithm):
        return False
    
    signature_value = signature[len(expected_algorithm):]
    
    mac = hmac.new(
        secret.encode(),
        msg=payload,
        digestmod=algorithm,
    )
    expected = f"{algorithm}=" + mac.hexdigest()
    
    return hmac.compare_digest(expected, signature)


def generate_webhook_signature(payload: bytes, secret: str, algorithm: str = "sha256") -> str:
    """Generate webhook signature."""
    mac = hmac.new(
        secret.encode(),
        msg=payload,
        digestmod=algorithm,
    )
    return f"{algorithm}=" + mac.hexdigest()


class WebhookValidator:
    """Validates webhook payloads from different platforms."""
    
    @staticmethod
    def validate_github(payload: bytes, signature: str, secret: str) -> bool:
        return verify_hmac_signature(payload, signature, secret, "sha256")
    
    @staticmethod
    def validate_gitlab(payload: bytes, signature: str, secret: str) -> bool:
        return verify_hmac_signature(payload, signature, secret, "sha256")
    
    @staticmethod
    def validate_bitbucket(payload: bytes, signature: str, secret: str) -> bool:
        return verify_hmac_signature(payload, signature, secret, "sha256")
    
    @staticmethod
    def validate_azure_devops(payload: bytes, signature: str, secret: str) -> bool:
        return verify_hmac_signature(payload, signature, secret, "sha256")
    
    @classmethod
    def validate(
        cls,
        platform: PlatformType,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        validators = {
            PlatformType.GITHUB: cls.validate_github,
            PlatformType.GITLAB: cls.validate_gitlab,
            PlatformType.BITBUCKET: cls.validate_bitbucket,
            PlatformType.AZURE_DEVOPS: cls.validate_azure_devops,
        }
        validator = validators.get(platform)
        if not validator:
            return False
        return validator(payload, signature, secret)