"""In-process live activity feed.

Bounded in-memory log of pipeline events that backs the Dashboard's live
"Pipeline Events" stream. This is not a WebSocket broker: the Flask worker is
single-threaded and has no socket server, so the UI short-polls
`GET /api/v1/events` instead. Events mirror the frontend PipelineEvent shape
({id, type, status, timestamp, data}).

In production this would be a Redis list + pub/sub; the API contract is the
same regardless of transport.
"""

import secrets
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

ACTIVITY_FEED: deque = deque(maxlen=250)
ACTIVITY_TOTALS: Dict[str, int] = {}
ACTIVITY_LOCK = threading.Lock()

VALID_EVENT_TYPES = frozenset(
    {"webhook", "github", "chat", "auth", "llm", "rag", "critique", "ast", "integration"}
)


def record_event(event_type: str, status: str = "processing",
                 data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Append one event to the feed and bump its per-type counter."""
    if event_type not in VALID_EVENT_TYPES:
        event_type = "integration"
    entry = {
        "id": f"{event_type}-{int(time.time() * 1000)}-{secrets.token_hex(2)}",
        "type": event_type,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "data": data or {},
    }
    with ACTIVITY_LOCK:
        ACTIVITY_FEED.appendleft(entry)
        ACTIVITY_TOTALS[event_type] = ACTIVITY_TOTALS.get(event_type, 0) + 1
    return entry


def snapshot(*, since: Optional[str] = None,
             pipeline: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Serialisable view of recent events + totals (+ optional pipeline counters)."""
    with ACTIVITY_LOCK:
        events = list(ACTIVITY_FEED)
        totals = dict(ACTIVITY_TOTALS)
    if since:
        events = [e for e in events if e["timestamp"] >= since]
    body: Dict[str, Any] = {
        "events": events,
        "totals": totals,
        "server_time": datetime.now(timezone.utc).isoformat() + "Z",
    }
    if pipeline:
        body["pipeline"] = pipeline
    return body


def find_events(**data_kwargs: Any) -> list:
    """Events in the feed whose data matches every provided key/value pair."""
    with ACTIVITY_LOCK:
        return [
            e for e in ACTIVITY_FEED
            if all(e.get("data", {}).get(k) == v for k, v in data_kwargs.items())
        ]


def reset() -> None:
    with ACTIVITY_LOCK:
        ACTIVITY_FEED.clear()
        ACTIVITY_TOTALS.clear()