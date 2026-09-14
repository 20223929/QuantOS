import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.v1.market import market_adapter

router = APIRouter()


@router.websocket("/market/{symbol}")
async def market_stream(websocket: WebSocket, symbol: str):
    await websocket.accept()
    try:
        if not market_adapter.connected:
            await market_adapter.connect()
        quote = market_adapter.api.get_quote(symbol)
        await websocket.send_json({
            "symbol": symbol,
            "price": float(getattr(quote, "last_price", 0) or 0),
            "source": "tqsdk",
        })
        while True:
            await asyncio.to_thread(market_adapter.api.wait_update)
            tick = await market_adapter.get_tick(symbol)
            tick.pop("quote", None)
            await websocket.send_json(tick)
    except (WebSocketDisconnect, RuntimeError):
        return
