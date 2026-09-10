from fastapi import APIRouter, WebSocket

from app.ws.market_ws import MarketWebSocket

router = APIRouter()
market_ws = MarketWebSocket()


@router.websocket("/market/{symbol}")
async def market_stream(websocket: WebSocket, symbol: str):
    await market_ws.connect(websocket)
    await market_ws.publish_tick(
        websocket,
        {"symbol": symbol, "price": 0, "source": "tqsdk"},
    )
