import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.v1.market import market_adapter
from app.trading.event_broadcast import trading_event_broadcaster

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


@router.websocket("/trading/events")
async def trading_events_stream(websocket: WebSocket):
    await websocket.accept()
    queue = trading_event_broadcaster.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        trading_event_broadcaster.unsubscribe(queue)
