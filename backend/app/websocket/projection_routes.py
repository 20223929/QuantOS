import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.projection_stream import ProjectionStream

router = APIRouter()
stream = ProjectionStream()


@router.websocket("/ws/projections/{aggregate_id}")
async def projection_websocket(websocket: WebSocket, aggregate_id: str):
    await websocket.accept()
    stream.subscribe(websocket)

    await websocket.send_json(
        {
            "type": "connected",
            "aggregate_id": aggregate_id,
        }
    )

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        stream.unsubscribe(websocket)
