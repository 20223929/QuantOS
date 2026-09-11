from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/trading")
async def trading_websocket(websocket: WebSocket):
    await websocket.accept()

    await websocket.send_json({
        "event": "CONNECTED",
        "channel": "trading"
    })

    while True:
        data = await websocket.receive_text()
        await websocket.send_json({
            "event": "ACK",
            "message": data
        })
