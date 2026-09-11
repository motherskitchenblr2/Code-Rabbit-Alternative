# =============================================================================
# LLM aggregation layer
# =============================================================================
# Task-aware auto-rotation router for AI model providers. Reads provider
# configuration from the admin settings store (with .env key fallbacks),
# ranks candidate models per task, and fails over automatically when a
# provider errors, rate-limits, or is marked unhealthy.
# =============================================================================

from .router import (
    AutoRouter,
    TASK_TYPES,
    TASK_LABELS,
    get_router,
    complete,
    status,
)

__all__ = [
    "AutoRouter",
    "TASK_TYPES",
    "TASK_LABELS",
    "get_router",
    "complete",
    "status",
]