from fastapi import APIRouter, WebSocket

from app.websocket.projection_stream import ProjectionStream

router = APIRouter()
stream = ProjectionStream()


@router.websocket("/ws/projections/{aggregate_id}")
async def projection_websocket(websocket: WebSocket, aggregate_id: str):
    await websocket.accept()
    stream.subscribe(websocket)

    try:
        while True:
            await websocket.receive_text()
    finally:
        stream.unsubscribe(websocket)
