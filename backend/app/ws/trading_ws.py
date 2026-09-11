from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.trading.events import TradeEvent

router = APIRouter()


class TradingEventHub:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def publish(self, event: TradeEvent):
        payload = event.model_dump()
        disconnected = []

        for websocket in self.connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


trading_event_hub = TradingEventHub()


@router.websocket("/ws/trading")
async def trading_websocket(websocket: WebSocket):
    await trading_event_hub.connect(websocket)

    try:
        await websocket.send_json({
            "event": "CONNECTED",
            "channel": "trading"
        })

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        trading_event_hub.disconnect(websocket)
