from fastapi import APIRouter

from app.trading.event_projection import project_execution_event

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/projection/schema")
async def projection_schema():
    """Describe the websocket/API shared event contract."""
    return {
        "event_id": "string",
        "event_type": "ORDER_EXECUTED",
        "aggregate_id": "order_id",
        "payload": {
            "order": "order snapshot",
            "trade": "trade snapshot",
            "position": "position snapshot",
        },
    }


__all__ = ["project_execution_event", "router"]
