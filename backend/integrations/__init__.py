# =============================================================================
# Git-Fix Integrations Package
# =============================================================================

from .base import (
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
    WebhookValidator,
    verify_hmac_signature,
    generate_webhook_signature,
)

from .gitlab import GitLabIntegration
from .bitbucket import BitbucketIntegration
from .azure_devops import AzureDevOpsIntegration

__all__ = [
    "PlatformIntegration",
    "PlatformType",
    "PlatformUser",
    "PlatformRepository",
    "PlatformPullRequest",
    "PlatformComment",
    "PlatformWebhookPayload",
    "WebhookEventType",
    "ReviewComment",
    "ReviewResult",
    "PlatformRegistry",
    "WebhookValidator",
    "verify_hmac_signature",
    "generate_webhook_signature",
    "GitLabIntegration",
    "BitbucketIntegration",
    "AzureDevOpsIntegration",
]

# Convenience function to create integration
def create_integration(
    platform: str,
    client_id: str,
    client_secret: str,
    webhook_secret: str,
    **kwargs,
):
    """Create a platform integration by name."""
    from .base import PlatformType
    
    platform_map = {
        "github": PlatformType.GITHUB,
        "gitlab": PlatformType.GITLAB,
        "bitbucket": PlatformType.BITBUCKET,
        "azure_devops": PlatformType.AZURE_DEVOPS,
        "ado": PlatformType.AZURE_DEVOPS,
    }
    
    platform_type = platform_map.get(platform.lower())
    if not platform_type:
        raise ValueError(f"Unknown platform: {platform}")
    
    return PlatformRegistry.create(
        platform_type,
        client_id=client_id,
        client_secret=client_secret,
        webhook_secret=webhook_secret,
        **kwargs,
    )