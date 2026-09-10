from fastapi import WebSocket


class MarketWebSocket:
    """Realtime market websocket gateway placeholder."""

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    async def publish_tick(self, websocket: WebSocket, tick: dict):
        await websocket.send_json(tick)
