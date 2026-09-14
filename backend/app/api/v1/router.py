from fastapi import APIRouter

from app.api.v1 import backtest, market, strategy, trading, ws

api_router = APIRouter()

api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
