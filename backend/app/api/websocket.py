from fastapi import APIRouter, WebSocket

from app.market.market_engine import MarketEngine

router = APIRouter()


@router.websocket("/ws/market")
async def market_socket(websocket: WebSocket):
    await websocket.accept()

    engine = MarketEngine()

    async for tick in engine.stream():
        await websocket.send_json(
            {
                "symbol": tick.symbol,
                "price": tick.price,
                "volume": tick.volume,
                "timestamp": tick.timestamp.isoformat(),
            }
        )
