import asyncio
from collections import deque
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.v1.market import market_adapter
from app.trading.event_broadcast import trading_event_broadcaster

router = APIRouter()

EVENT_HISTORY = deque(maxlen=500)
HEARTBEAT_INTERVAL = 20


async def send_heartbeat(websocket: WebSocket):
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        await websocket.send_json({"type": "heartbeat"})


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

    last_event_id: Optional[str] = websocket.query_params.get("last_event_id")

    queue = trading_event_broadcaster.subscribe()
    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))

    try:
        if last_event_id:
            for event in EVENT_HISTORY:
                if event.get("event_id") == last_event_id:
                    continue
                await websocket.send_json(event)

        while True:
            event = await queue.get()
            EVENT_HISTORY.append(event)
            await websocket.send_json(event)

    except WebSocketDisconnect:
        trading_event_broadcaster.unsubscribe(queue)
    finally:
        heartbeat_task.cancel()
