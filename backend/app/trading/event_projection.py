"""Trading execution event projection layer.

Keeps API/WebSocket consumers aligned with persisted execution events.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TradingEventProjection:
    event_id: str
    event_type: str
    aggregate_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "payload": self.payload,
        }


def project_execution_event(row: Any) -> dict[str, Any]:
    """Convert persisted execution event rows into realtime event schema."""
    import json

    payload = row.payload
    if isinstance(payload, str):
        payload = json.loads(payload)
    return TradingEventProjection(
        event_id=row.event_id,
        event_type=row.event_type,
        aggregate_id=row.aggregate_id,
        payload=payload,
    ).to_dict()
